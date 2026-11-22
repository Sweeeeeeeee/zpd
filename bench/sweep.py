"""Run solve() over a Newclid dataset file with one config; append JSON lines.

usage: python bench/sweep.py DATASET CONFIG OUT.jsonl [--only names.txt] [--time 60]
(without --time: the config's own budget block)
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.dataset import read_problems
from bench.jsonl import resume_rows
from pipeline.solve import Budget, config_budget, solve

ap = argparse.ArgumentParser()
ap.add_argument("dataset"); ap.add_argument("config"); ap.add_argument("out")
ap.add_argument("--only"); ap.add_argument("--time", type=float, default=None, help="seconds, 2 GB; default: the config's own budget")
a = ap.parse_args()

problems = read_problems(Path(a.dataset))
if a.only:
    keep = set(Path(a.only).read_text().split())
    missing = keep - problems.keys()
    if missing:
        ap.error(f"unknown IDs in {a.only}: {', '.join(sorted(missing))}")
    problems = {name: text for name, text in problems.items() if name in keep}
done = {row["name"] for row in resume_rows(Path(a.out))}

budget = Budget(time_s=a.time, memory_mb=2048, cpu_s=0) if a.time is not None else config_budget(a.config)
with open(a.out, "a") as f:
    for i, (name, text) in enumerate(problems.items()):
        if name in done:
            continue
        r = solve(text, a.config, budget)
        rec = {"name": name, "solved": r.solved, "wall": r.wall_time, "load": r.load_time, "mem": r.peak_memory_mb,
               "depth": r.depth, "aux": r.aux, "ddar_calls": r.ddar_calls,
               "tool_calls": r.tool_calls, "reason": r.failure_reason,
               "n_rules": sum(r.rules_in_proof.values())}
        f.write(json.dumps(rec) + "\n"); f.flush()
        print(i, name.split("/")[-1], r.solved, f"{r.wall_time:.1f}s", (r.failure_reason or "")[:50], flush=True)
