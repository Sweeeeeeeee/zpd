"""Solve one JGEX problem under a DDARConfig and report which rules fired.

`solve_jgex` runs in the current process. `solve_in_subprocess` runs it in a
child process with a timeout, so a runaway problem cannot stall a batch.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from ddar.engine import build_solver  # noqa: F401  (re-exported)
from ddar.rule_config import DDARConfig


def justification_label(justification) -> str | None:
    from newclid.justifications.justification import ARDeduction, RuleApplication

    if isinstance(justification, RuleApplication):
        return justification.rule.id
    if isinstance(justification, ARDeduction):
        return "AR:" + justification.ar_reason.value.split()[0].lower()  # AR:angle / AR:ratio
    return None


def solve_jgex(
    problem: str,
    config: DDARConfig,
    seed: int = 0,
    problems_file: Path | None = None,
) -> dict:
    """Solve a problem given as JGEX text, or as a name in `problems_file`.

    Returns success, timings, DDAR levels, `fired` (rule id -> number of new
    facts it produced) and `in_proof` (rule id -> uses in the final proof).
    """
    logging.disable(logging.WARNING)
    from newclid.jgex.problem_builder import JGEXProblemBuilder
    from newclid.problem import predicate_to_construction
    from newclid.proof_data import proof_data_from_state

    t0 = time.time()
    builder = JGEXProblemBuilder(rng=seed)
    if problems_file is not None:
        builder.with_problem_from_file(problems_path=problems_file, problem_name=problem)
    else:
        builder.with_problem_from_txt(problem)
    setup = builder.build()
    build_time = time.time() - t0

    solver = build_solver(setup, config, seed)
    success = solver.run()
    infos = solver.run_infos
    state = solver.proof_state

    fired = Counter(
        label for j in state.graph.hyper_graph.values() if (label := justification_label(j))
    )
    in_proof: Counter[str] = Counter()
    if success:
        goals = [predicate_to_construction(g) for g in state.goals]
        for step in proof_data_from_state(goals, state).proof_steps:
            if label := justification_label(step.justification):
                in_proof[label] += 1

    return {
        "config": config.name,
        "success": success,
        "build_time": round(build_time, 3),
        "run_time": round(infos.runtime, 3),
        "levels": getattr(infos.agent_stats, "max_level", None),
        "facts": len(state.graph.hyper_graph),
        "rules_enabled": len(config.rules()),
        "fired": dict(sorted(fired.items())),
        "in_proof": dict(sorted(in_proof.items())),
    }


def solve_in_subprocess(
    problem: str,
    config: DDARConfig,
    seed: int = 0,
    problems_file: Path | None = None,
    timeout: float = 60.0,
) -> dict:
    """`solve_jgex` in a child process; errors and timeouts become results."""
    request = {
        "problem": problem,
        "config": asdict(config),
        "seed": seed,
        "problems_file": str(problems_file) if problems_file else None,
    }
    root = Path(__file__).resolve().parents[1]
    t0 = time.time()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "ddar.runner"],
            input=json.dumps(request),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=root,
        )
        line = next(
            (ln for ln in proc.stdout.splitlines() if ln.startswith("RESULT ")), None
        )
        if line is None:
            error = (proc.stderr.strip().splitlines() or ["no output"])[-1]
            result = {"config": config.name, "success": False, "error": error[:160]}
        else:
            result = json.loads(line[len("RESULT ") :])
    except subprocess.TimeoutExpired:
        result = {"config": config.name, "success": False, "error": f"timeout {timeout:.0f}s"}
    result["wall"] = round(time.time() - t0, 2)
    return result


def _child() -> None:
    request = json.loads(sys.stdin.read())
    config = DDARConfig.from_dict(request["config"])
    problems_file = Path(request["problems_file"]) if request["problems_file"] else None
    result = solve_jgex(request["problem"], config, request["seed"], problems_file)
    print("RESULT " + json.dumps(result))


if __name__ == "__main__":
    _child()
