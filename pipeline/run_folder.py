"""Solve every problem in a folder under one config and print a results table.

    python -m pipeline.run_folder problems/examples --config pipeline/configs/heuristics_only.json
    python -m pipeline.run_folder my_problems/ --time 120 --memory 3000 --check

Each `*.txt` file holds one problem: an optional `# comment` line (shown as
the description), then the JGEX problem on one line. The problem name is the
file name. Each problem is solved with pipeline.solve.solve() in its own
subprocess, under the given budget. Results are also written to
<folder>/results_<config>.json.

--check runs the numerical figure check (pipeline.check_figure) first, and
skips problems whose translation fails it.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from pipeline.solve import ROOT, Budget, solve


def read_problem_file(path: Path) -> tuple[str, str]:
    """(problem, description) from a problem file."""
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip()]
    comments = [ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")]
    problems = [ln for ln in lines if not ln.startswith("#")]
    if len(problems) != 1:
        raise ValueError(f"{path}: expected exactly one problem line, found {len(problems)}")
    return problems[0], " ".join(comments)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--config", default="pipeline/configs/default.json")
    ap.add_argument("--time", type=float, default=120.0, help="wall-clock limit per problem, s")
    ap.add_argument("--memory", type=float, default=2048.0, help="memory limit per problem, MB")
    ap.add_argument("--cpu", type=float, default=0.0, help="CPU limit per problem, s (0 = none)")
    ap.add_argument("--check", action="store_true", help="numerically check each figure first")
    args = ap.parse_args()

    files = sorted(args.folder.glob("*.txt"))
    if not files:
        raise SystemExit(f"no *.txt problem files in {args.folder}")
    budget = Budget(args.time, args.memory, args.cpu)
    config_path = Path(args.config)
    rows, results = [], {}

    header = f"{'problem':28s} {'solved':6s} {'time s':>7s} {'mem MB':>7s} {'depth':>5s}  {'tools':22s} details"
    print(header)
    print("-" * len(header))
    for path in files:
        name = path.stem
        try:
            problem, _description = read_problem_file(path)
        except ValueError as e:
            print(f"{name:28s} {'ERROR':6s} {str(e)}")
            continue
        if args.check:
            from pipeline.check_figure import check_figure, summarize

            ok, message = summarize(check_figure(problem, seeds=3))
            if not ok:
                print(f"{name:28s} {'SKIP':6s} figure check: {message}")
                results[name] = {"skipped": message}
                continue
        r = solve(problem, config_path, budget)
        results[name] = asdict(r)
        if r.solved:
            aux = "; ".join(c for a in r.aux for c in a["clauses"])
            details = f"aux: {aux}" if aux else f"rules: {' '.join(sorted(r.rules_in_proof))}"
        else:
            details = r.failure_reason or ""
        tools = ",".join(r.tools_used) or "-"
        print(f"{name:28s} {'yes' if r.solved else 'no':6s} {r.wall_time:7.1f} "
              f"{r.peak_memory_mb:7.0f} {r.depth:5d}  {tools:22s} {details[:70]}", flush=True)
        rows.append(r)

    solved = sum(r.solved for r in rows)
    print("-" * len(header))
    print(f"solved {solved}/{len(files)}   config {config_path.name}   "
          f"budget {budget.time_s:.0f}s / {budget.memory_mb:.0f} MB")
    out = args.folder / f"results_{config_path.stem}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"results written to {out}")


if __name__ == "__main__":
    main()
