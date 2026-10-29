"""Proof state, the Tool interface, and the DDAR and heuristics tools.

A tool looks at the current proof state and returns either nothing (None) or
a list of candidate auxiliary constructions. DDAR is a tool too: it runs the
deduction on the state, records the result in it, and proposes nothing.

Auxiliary constructions are Newclid (JGEX) clauses, e.g. "e = foot e a b c",
appended to the problem before the goal.
"""

from __future__ import annotations

import itertools
import logging
import math
import string
import time
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]



@dataclass(frozen=True)
class AuxConstruction:
    """One proposal: JGEX clauses that add new points, in order."""

    clauses: tuple[str, ...]
    source: str  # name of the tool that proposed it
    score: float = 0.0  # tool-specific; higher is better
    note: str = ""  # e.g. the raw model output it came from


@dataclass
class ProofState:
    """A problem plus the auxiliary constructions added so far."""

    setup: str  # JGEX clauses before '?', e.g. "a b c = triangle a b c; ..."
    goal: str  # JGEX goal(s) after '?'
    aux: tuple[AuxConstruction, ...] = ()
    # Filled by the DDAR tool:
    checked: bool = False
    solved: bool = False
    error: str | None = None  # the figure could not be built, DDAR crashed, ...
    proof: str | None = None
    rules_fired: Counter = field(default_factory=Counter)
    rules_in_proof: Counter = field(default_factory=Counter)
    ddar_time: float = 0.0
    problem_setup: object = None  # newclid ProblemSetup (numeric points)
    builder: object = None  # JGEXProblemBuilder (clause -> predicates)

    @classmethod
    def from_text(cls, text: str) -> ProofState:
        setup, sep, goal = text.partition("?")
        if not sep or not goal.strip():
            raise ValueError("problem needs a goal after '?'")
        return cls(setup=setup.strip().rstrip(";"), goal=goal.strip())

    @property
    def depth(self) -> int:
        return len(self.aux)

    @property
    def aux_clauses(self) -> list[str]:
        return [c for a in self.aux for c in a.clauses]

    def text(self) -> str:
        return "; ".join([self.setup, *self.aux_clauses]) + " ? " + self.goal

    def child(self, aux: AuxConstruction) -> ProofState:
        return ProofState(setup=self.setup, goal=self.goal, aux=self.aux + (aux,))

    def point_names(self) -> list[str]:
        if self.problem_setup is not None:
            return [str(p.name) for p in self.problem_setup.points]
        names: list[str] = []
        for clause in [self.setup, *self.aux_clauses]:
            for part in clause.split(";"):
                if "=" in part:
                    names += part.split("=")[0].split()
        return names

    def goal_points(self) -> set[str]:
        tokens = self.goal.replace(",", " ").split()
        return {t for t in tokens if t in set(self.point_names())}


def fresh_point_name(taken: set[str]) -> str:
    for name in string.ascii_lowercase:
        if name not in taken:
            return name
    for i in itertools.count(1):
        for letter in string.ascii_lowercase:
            if (name := f"{letter}{i}") not in taken:
                return name
    raise AssertionError


class Tool(ABC):
    """Takes the current proof state; returns None or new auxiliary constructions."""

    name: str = "tool"

    def __init__(self, **options) -> None:
        self.options = options
        self.calls = 0

    @abstractmethod
    def run(self, state: ProofState) -> list[AuxConstruction] | None: ...


class DDARTool(Tool):
    """Newclid's deductive engine. Proves what it can and records it in the state.

    options:
        config: path to a DDAR config JSON (step 2), default ddar/configs/yuclid.json
        seed:   RNG seed for drawing the figure (default 0)
    """

    name = "ddar"

    def __init__(self, config: str = "ddar/configs/yuclid.json", seed: int = 0) -> None:
        super().__init__(config=config, seed=seed)
        from ddar.rule_config import DDARConfig

        path = Path(config)
        self.ddar_config = DDARConfig.from_json(path if path.is_absolute() else ROOT / path)
        self.seed = seed

    def run(self, state: ProofState) -> None:
        from ddar.runner import build_solver, justification_label
        from newclid.jgex.problem_builder import JGEXProblemBuilder
        from newclid.problem import predicate_to_construction
        from newclid.proof_data import proof_data_from_state

        self.calls += 1
        logging.disable(logging.WARNING)
        t0 = time.time()
        state.checked = True
        try:
            builder = JGEXProblemBuilder(rng=self.seed).with_problem_from_txt(state.text())
            setup = builder.build()
            solver = build_solver(setup, self.ddar_config, self.seed)
            state.solved = solver.run()
        except Exception as e:  # unbuildable figure, engine error, ...
            state.error = f"{type(e).__name__}: {str(e)[:200]}"
            state.ddar_time = time.time() - t0
            return None
        state.builder, state.problem_setup = builder, setup
        proof = solver.proof_state
        state.rules_fired = Counter(
            lbl for j in proof.graph.hyper_graph.values() if (lbl := justification_label(j))
        )
        if state.solved:
            goals = [predicate_to_construction(g) for g in proof.goals]
            for step in proof_data_from_state(goals, proof).proof_steps:
                if lbl := justification_label(step.justification):
                    state.rules_in_proof[lbl] += 1
            state.proof = solver.proof()
        state.ddar_time = time.time() - t0
        return None


class HeuristicsTool(Tool):
    """Human-style constructions: midpoints, circumcenters, feet of altitudes.

    Deterministic. Candidates touching more goal points come first, then
    alphabetical order. Points that would coincide with an existing point are
    skipped.

    options:
        kinds:          subset of ["midpoint", "circumcenter", "foot"]
        max_candidates: how many proposals to return (default 8)
    """

    name = "heuristics"
    KINDS = ("midpoint", "circumcenter", "foot")

    def __init__(self, kinds: list[str] | None = None, max_candidates: int = 8) -> None:
        super().__init__(kinds=kinds, max_candidates=max_candidates)
        self.kinds = list(kinds or self.KINDS)
        unknown = set(self.kinds) - set(self.KINDS)
        if unknown:
            raise ValueError(f"unknown heuristic kinds {sorted(unknown)}; use {self.KINDS}")
        self.max_candidates = max_candidates

    def run(self, state: ProofState) -> list[AuxConstruction] | None:
        self.calls += 1
        if state.problem_setup is None:
            return None
        pts = {str(p.name): (float(p.num.x), float(p.num.y)) for p in state.problem_setup.points}
        names = sorted(pts)
        scale = max((math.dist(a, b) for a, b in itertools.combinations(pts.values(), 2)), default=1.0)
        eps = 1e-6 * max(scale, 1.0)
        goal = state.goal_points()
        new = fresh_point_name(set(names))

        found: list[tuple[tuple, str, tuple[float, float]]] = []
        if "midpoint" in self.kinds:
            for a, b in itertools.combinations(names, 2):
                xy = ((pts[a][0] + pts[b][0]) / 2, (pts[a][1] + pts[b][1]) / 2)
                found.append(((a, b), f"{new} = midpoint {new} {a} {b}", xy))
        if "circumcenter" in self.kinds:
            for a, b, c in itertools.combinations(names, 3):
                if (xy := _circumcenter(pts[a], pts[b], pts[c], eps)) is not None:
                    found.append(((a, b, c), f"{new} = circle {new} {a} {b} {c}", xy))
        if "foot" in self.kinds:
            for a in names:
                for b, c in itertools.combinations([n for n in names if n != a], 2):
                    if (xy := _foot(pts[a], pts[b], pts[c], eps)) is not None:
                        found.append(((a, b, c), f"{new} = foot {new} {a} {b} {c}", xy))

        kept: list[tuple[tuple, str]] = []
        locations: list[tuple[float, float]] = list(pts.values())
        found.sort(key=lambda f: (-len(goal & set(f[0])), f[1]))
        for args, clause, xy in found:
            if any(math.dist(xy, q) < eps for q in locations):
                continue  # coincides with an existing or already-proposed point
            locations.append(xy)
            kept.append((args, clause))
            if len(kept) >= self.max_candidates:
                break
        return [
            AuxConstruction((clause,), self.name, score=len(goal & set(args)))
            for args, clause in kept
        ] or None


def _circumcenter(a, b, c, eps):
    d = 2 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    if abs(d) < eps:
        return None  # collinear
    sa, sb, sc = a[0] ** 2 + a[1] ** 2, b[0] ** 2 + b[1] ** 2, c[0] ** 2 + c[1] ** 2
    return (
        (sa * (b[1] - c[1]) + sb * (c[1] - a[1]) + sc * (a[1] - b[1])) / d,
        (sa * (c[0] - b[0]) + sb * (a[0] - c[0]) + sc * (b[0] - a[0])) / d,
    )


def _foot(a, b, c, eps):
    dx, dy = c[0] - b[0], c[1] - b[1]
    n = dx * dx + dy * dy
    if n < eps:
        return None
    t = ((a[0] - b[0]) * dx + (a[1] - b[1]) * dy) / n
    return (b[0] + t * dx, b[1] + t * dy)
