"""The first pipeline: DDAR until it stops, ask for constructions, DDAR again.

    python -m pipeline.search --config pipeline/configs/default.json \\
        -s "a b c = triangle a b c; d = on_tline d b a c, on_tline d c a b ? perp a d b c"

Search is breadth-first over auxiliary constructions:
  depth 0: run DDAR on the problem.
  depth k: for each unsolved state of depth k-1 (at most `max_frontier`), ask
           the proposer tools in config order, keep the first `branching`
           distinct proposals, add each one and run DDAR. Stop at the first
           solved state.
Limits: max_depth, branching, max_frontier, max_ddar_calls, time_limit.
Every step is deterministic; nothing is guessed at random.

Config (JSON):
    {
      "tools": {
        "ddar":        {"enabled": true, "options": {"config": "ddar/configs/yuclid.json"}},
        "transformer": {"enabled": true, "options": {"checkpoint": "geo-lm/runs/small/best.pt"}},
        "heuristics":  {"enabled": true, "options": {"kinds": ["midpoint", "circumcenter", "foot"]}}
      },
      "proposer_order": ["transformer", "heuristics"],
      "search": {"max_depth": 2, "branching": 6, "max_frontier": 6, "max_ddar_calls": 60, "time_limit": 0}
    }
Any tool entry may set "class": "package.module:ClassName" to swap in another
implementation of the Tool interface.
"""

from __future__ import annotations

import argparse
import sys
import importlib
import json
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.tools import ROOT, DDARTool, HeuristicsTool, ProofState, Tool

DEFAULT_CLASSES = {
    "ddar": "pipeline.tools:DDARTool",
    "heuristics": "pipeline.tools:HeuristicsTool",
    "transformer": "pipeline.transformer_tool:TransformerTool",
}


@dataclass
class SearchLimits:
    max_depth: int = 2
    branching: int = 6
    max_frontier: int = 6
    max_ddar_calls: int = 60
    time_limit: float = 0.0  # seconds; 0 = no limit


@dataclass
class SearchResult:
    solved: bool
    proof: str | None
    depth: int
    aux: list[dict]  # constructions on the solving path: clauses + source tool
    rules_fired: dict[str, int]  # rules that produced facts in the final DDAR run
    rules_in_proof: dict[str, int]
    tool_calls: dict[str, int]
    tools_used: list[str]  # tools that contributed to the result
    ddar_calls: int
    wall_time: float
    failure_reason: str | None = None
    rejected: dict[str, int] = field(default_factory=dict)  # proposals that broke the figure


def load_tool(name: str, spec: dict) -> Tool:
    module_name, _, class_name = spec.get("class", DEFAULT_CLASSES.get(name, "")).partition(":")
    if not class_name:
        raise ValueError(f"tool '{name}' needs a 'class' entry (module:Class)")
    cls = getattr(importlib.import_module(module_name), class_name)
    tool = cls(**spec.get("options", {}))
    if not isinstance(tool, Tool):
        raise TypeError(f"{cls} is not a pipeline.tools.Tool")
    return tool


def load_tools(config: dict) -> tuple[Tool | None, list[Tool]]:
    """(deductive tool or None, proposer tools in order) from a pipeline config."""
    specs = config.get("tools", {})
    enabled = {n: s for n, s in specs.items() if s.get("enabled", True)}
    ddar = load_tool("ddar", enabled["ddar"]) if "ddar" in enabled else None
    order = config.get("proposer_order") or [n for n in enabled if n != "ddar"]
    unknown = set(order) - set(specs)
    if unknown:
        raise ValueError(f"proposer_order names unknown tools {sorted(unknown)}")
    proposers = []
    for n in order:
        if n not in enabled:
            continue
        try:
            proposers.append(load_tool(n, enabled[n]))
        except FileNotFoundError as e:  # e.g. a model that has not been trained yet
            print(f"warning: tool '{n}' switched off: {e}", file=sys.stderr)
    return ddar, proposers


def search(problem: str, ddar: Tool | None, proposers: list[Tool], limits: SearchLimits) -> SearchResult:
    t0 = time.time()
    rejected: Counter = Counter()

    explored = 0  # deepest search level that was run
    tools = ([ddar] if ddar else []) + proposers

    def finish(state: ProofState, reason: str | None) -> SearchResult:
        if state.solved:  # tools on the solving path
            used = sorted({a.source for a in state.aux} | {ddar.name})
        else:  # report the search as a whole, not an arbitrary unsolved branch
            state = ProofState(setup=root.setup, goal=root.goal, rules_fired=root.rules_fired)
            used = [t.name for t in tools if t.calls]
        return SearchResult(
            solved=state.solved, proof=state.proof,
            depth=state.depth if state.solved else explored,
            aux=[{"clauses": list(a.clauses), "source": a.source, "note": a.note} for a in state.aux],
            rules_fired=dict(state.rules_fired), rules_in_proof=dict(state.rules_in_proof),
            tool_calls={t.name: t.calls for t in tools},
            tools_used=used, ddar_calls=ddar.calls if ddar else 0,
            wall_time=round(time.time() - t0, 3), failure_reason=None if state.solved else reason,
            rejected=dict(rejected),
        )

    root = ProofState.from_text(problem)
    if ddar is None:
        return finish(root, "DDAR tool disabled: nothing can be proven")
    ddar.run(root)
    if root.error:
        return finish(root, f"problem could not be built: {root.error}")
    if root.solved:
        return finish(root, None)
    if not proposers:
        return finish(root, "DDAR saturated and no proposer tools are enabled")

    frontier = [root]

    def out_of_budget() -> str | None:
        if limits.max_ddar_calls and ddar.calls >= limits.max_ddar_calls:
            return f"budget: {limits.max_ddar_calls} DDAR calls"
        if limits.time_limit and time.time() - t0 >= limits.time_limit:
            return f"budget: {limits.time_limit:.0f}s"
        return None

    for depth in range(1, limits.max_depth + 1):
        explored = depth
        children: list[ProofState] = []
        for state in frontier:
            proposals, seen = [], set()
            for tool in proposers:
                for p in tool.run(state) or []:
                    if p.clauses not in seen:
                        seen.add(p.clauses)
                        proposals.append(p)
            for proposal in proposals[: limits.branching]:
                if reason := out_of_budget():
                    return finish(root, reason)
                child = state.child(proposal)
                ddar.run(child)
                if child.error:
                    rejected[proposal.source] += 1
                    continue
                if child.solved:
                    return finish(child, None)
                children.append(child)
        if not children:
            return finish(root, "no usable proposals")
        frontier = children[: limits.max_frontier]
    return finish(root, f"not solved within depth {limits.max_depth}")


def load_config(path: str | Path) -> dict:
    return json.loads(Path(path).read_text())


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", default=str(ROOT / "pipeline/configs/default.json"))
    ap.add_argument("-s", "--problem", required=True, help="JGEX problem text")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = ap.parse_args()

    config = load_config(args.config)
    ddar, proposers = load_tools(config)
    result = search(args.problem, ddar, proposers, SearchLimits(**config.get("search", {})))
    if args.json:
        print(json.dumps(result.__dict__, indent=2))
        return
    print(f"solved: {result.solved}   depth: {result.depth}   DDAR calls: {result.ddar_calls}   "
          f"time: {result.wall_time}s")
    for a in result.aux:
        print(f"  aux from {a['source']}: {'; '.join(a['clauses'])}")
    if result.failure_reason:
        print(f"  failure: {result.failure_reason}")
    print(f"  rules in proof: {result.rules_in_proof}")
    if result.proof:
        print(result.proof)


if __name__ == "__main__":
    main()
