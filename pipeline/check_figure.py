"""Numerical check of a hand-translated problem.

Draws the figure from scratch several times (different random seeds), without
forcing the goal to hold, and reports for each drawing:
  * whether the figure could be built at all (constructions are consistent),
  * the smallest distance between two points (near 0 = degenerate figure),
  * whether each goal holds numerically.

A correct translation of a true statement gives "goal holds" in every drawing.
"fails in some drawings" usually means a construction picks the wrong branch,
e.g. the other intersection of a line and a circle. "fails in every drawing"
means the translation, or the statement, is wrong.

    python -m pipeline.check_figure -s "a b c = triangle a b c; h = orthocenter h a b c ? perp a h b c"
    python -m pipeline.check_figure -f problems/examples/varignon.txt --seeds 10 --svg /tmp/fig.svg
"""

from __future__ import annotations

import argparse
import itertools
import logging
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FigureCheck:
    seed: int
    built: bool
    error: str | None = None
    min_distance: float | None = None
    goals: dict[str, bool] | None = None


def check_figure(problem: str, seeds: int = 5) -> list[FigureCheck]:
    logging.disable(logging.WARNING)
    from newclid.api import GeometricSolverBuilder, PythonDefault
    from newclid.jgex.formulation import JGEXFormulation
    from newclid.jgex.problem_builder import JGEXProblemBuilder
    from newclid.predicates import predicate_from_construction

    formulation = JGEXFormulation.from_text(problem)
    goals = formulation.goals
    setup_only = JGEXFormulation(name="check", setup_clauses=formulation.setup_clauses, goals=())
    checks = []
    for seed in range(seeds):
        try:
            setup = JGEXProblemBuilder(rng=seed).with_problem(setup_only).build(
                max_attempts_to_satisfy_goals_numerically=1
            )
            state = GeometricSolverBuilder(rng=seed, api_default=PythonDefault()).build(setup).proof_state
        except Exception as e:
            checks.append(FigureCheck(seed, False, f"{type(e).__name__}: {str(e)[:160]}"))
            continue
        xy = [(float(p.num.x), float(p.num.y)) for p in setup.points]
        dmin = min((math.dist(a, b) for a, b in itertools.combinations(xy, 2)), default=None)
        results = {}
        for goal in goals:
            predicate = predicate_from_construction(goal, state.symbols.points)
            results[str(goal)] = predicate is not None and predicate.check_numerical()
        checks.append(FigureCheck(seed, True, min_distance=dmin, goals=results))
    return checks


def summarize(checks: list[FigureCheck]) -> tuple[bool, str]:
    built = [c for c in checks if c.built]
    if not built:
        return False, f"figure could not be built in {len(checks)} tries: {checks[0].error}"
    goal_names = list(built[0].goals or {})
    bad = {g: sum(not c.goals[g] for c in built) for g in goal_names}
    if any(c.min_distance is not None and c.min_distance < 1e-6 for c in built):
        return False, "two points coincide in some drawing (degenerate construction)"
    if all(v == 0 for v in bad.values()):
        return True, f"goal holds in all {len(built)} drawings"
    worst = max(bad, key=bad.get)
    where = "every drawing" if bad[worst] == len(built) else f"{bad[worst]} of {len(built)} drawings"
    return False, f"'{worst}' fails in {where}"


def _read_problem(path: Path) -> str:
    lines = [ln.strip() for ln in path.read_text().splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    return next(ln for ln in lines if "=" in ln)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("-s", "--problem")
    src.add_argument("-f", "--file", type=Path)
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--svg", type=Path, help="also save a drawing (seed 0) to this file")
    args = ap.parse_args()
    problem = args.problem or _read_problem(args.file)

    checks = check_figure(problem, args.seeds)
    for c in checks:
        if not c.built:
            print(f"seed {c.seed}: NOT BUILT  {c.error}")
        else:
            goals = ", ".join(f"{g}: {'ok' if v else 'FALSE'}" for g, v in c.goals.items())
            print(f"seed {c.seed}: min point distance {c.min_distance:.3g}   {goals}")
    ok, message = summarize(checks)
    print(("OK    " if ok else "CHECK ") + message)

    if args.svg:
        import matplotlib

        matplotlib.use("Agg")
        from newclid.api import GeometricSolverBuilder, PythonDefault
        from newclid.jgex.formulation import JGEXFormulation
        from newclid.jgex.problem_builder import JGEXProblemBuilder

        formulation = JGEXFormulation.from_text(problem)
        setup = JGEXProblemBuilder(rng=0).with_problem(formulation).build()
        solver = GeometricSolverBuilder(rng=0, api_default=PythonDefault()).build(setup)
        solver.draw_figure(out_file=args.svg, jgex_problem=formulation)
        print(f"drawing saved to {args.svg}")


if __name__ == "__main__":
    main()
