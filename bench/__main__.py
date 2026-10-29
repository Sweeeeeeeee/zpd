"""Command line for the problem store.

    python -m bench run problems/examples --config pipeline/configs/ddar_only.json pipeline/configs/heuristics_only.json
    python -m bench table problems/examples
    python -m bench show problems/examples/varignon
    python -m bench list problems/examples

`run` solves each problem under each config and stores, in
results/<set>/<problem>.json, one record per config and budget: the settings,
the resources available and used, and the outcome with the proof. Stored
combinations are skipped (--force to replace them). Commit the results folder
to keep them on GitHub.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from bench.store import ROOT, latest_by_config, load_problems, load_records, parse_problem_file, run
from pipeline.solve import Budget


def _cell(record: dict) -> str:
    if record["solved"]:
        return f"yes {record['resources']['used']['wall_time_s']:.1f}s d{record['depth']}"
    reason = record["failure_reason"] or ""
    for prefix, label in SHORT_REASONS:
        if reason.startswith(prefix):
            return f"no ({label})"
    return f"no ({reason[:12]})"


SHORT_REASONS = [
    ("time limit", "time"), ("memory limit", "memory"), ("CPU limit", "cpu"),
    ("budget", "budget"), ("problem could not be built", "bad figure"),
    ("not solved within depth", "depth"), ("no usable proposals", "no aux"),
    ("DDAR saturated", "stuck"), ("DDAR tool disabled", "no ddar"), ("crashed", "crash"),
]


def cmd_run(args) -> None:
    problems = load_problems(args.folder)
    budget = Budget(args.time, args.memory, args.cpu)

    def show(problem, config, record, skipped):
        tag = "stored " if skipped else "new    "
        print(f"{tag}{config:20s} {problem.name:28s} {_cell(record)}", flush=True)

    new = run(problems, args.config, budget, force=args.force, on_result=show)
    print(f"\n{len(new)} new record(s) in {ROOT / 'results' / Path(args.folder).name}")


def cmd_table(args) -> None:
    problems = load_problems(args.folder)
    latest = {p.name: latest_by_config(p) for p in problems}
    configs = sorted({c for per in latest.values() for c in per})
    if not configs:
        print("no stored results yet: run `python -m bench run` first")
        return
    width = max(16, *(len(c) for c in configs))
    print(f"{'problem':28s} " + " ".join(f"{c:{width}s}" for c in configs))
    for p in problems:
        cells = [_cell(latest[p.name][c]) if c in latest[p.name] else "-" for c in configs]
        print(f"{p.name:28s} " + " ".join(f"{c:{width}s}" for c in cells))
    solved = [sum(latest[p.name].get(c, {}).get("solved", False) for p in problems)
              for c in configs]
    print(f"{'solved':28s} " + " ".join(f"{f'{s}/{len(problems)}':{width}s}" for s in solved))


def cmd_show(args) -> None:
    path = Path(args.problem)
    path = path if path.suffix else path.with_suffix(".txt")
    problem = parse_problem_file(path if path.is_absolute() else ROOT / path)
    print(f"{problem.id}: {problem.description}")
    for k, v in problem.meta.items():
        print(f"  {k}: {v}")
    print(f"  {problem.text}")
    for r in load_records(problem):
        avail, used = r["resources"]["available"], r["resources"]["used"]
        extra = r["failure_reason"] or ", ".join(sorted(r["rules_in_proof"]))
        print(f"  {r['config']:18s} budget {avail['time_s']:.0f}s/{avail['memory_mb']:.0f} MB: "
              f"{_cell(r):16s} used {used['peak_memory_mb']:.0f} MB, {used['cpu_time_s']:.1f} s CPU, "
              f"{used['ddar_calls']} DDAR calls  tools {','.join(r['tools_used'])}  {extra[:50]}")
    if args.json:
        print(json.dumps(load_records(problem), indent=1))


def cmd_list(args) -> None:
    for p in load_problems(args.folder):
        tags = p.meta.get("tags", "")
        print(f"{p.name:28s} {len(load_records(p)):3d} records  {tags:24s} {p.description[:60]}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="solve problems under configs and store the results")
    r.add_argument("folder")
    r.add_argument("--config", nargs="+", required=True)
    r.add_argument("--time", type=float, default=60.0)
    r.add_argument("--memory", type=float, default=2048.0)
    r.add_argument("--cpu", type=float, default=0.0)
    r.add_argument("--force", action="store_true")
    r.set_defaults(func=cmd_run)
    t = sub.add_parser("table", help="latest result per problem and config")
    t.add_argument("folder")
    t.set_defaults(func=cmd_table)
    s = sub.add_parser("show", help="metadata and every stored result of one problem")
    s.add_argument("problem")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_show)
    li = sub.add_parser("list", help="problems in a folder")
    li.add_argument("folder")
    li.set_defaults(func=cmd_list)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
