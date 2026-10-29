"""Run solve() over a Newclid dataset file with one config; append JSON lines.

usage: python bench/sweep.py DATASET CONFIG OUT.jsonl [--only names.txt] [--time 60]
"""
import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.solve import Budget, solve

ap = argparse.ArgumentParser()
ap.add_argument("dataset"); ap.add_argument("config"); ap.add_argument("out")
ap.add_argument("--only"); ap.add_argument("--time", type=float, default=60)
a = ap.parse_args()

lines = [l.strip() for l in Path(a.dataset).read_text().splitlines() if l.strip()]
problems = list(zip(lines[0::2], lines[1::2]))
if a.only:
    keep = set(Path(a.only).read_text().split())
    problems = [p for p in problems if p[0] in keep]
done = set()
if Path(a.out).exists():
    done = {json.loads(l)["name"] for l in Path(a.out).read_text().splitlines()}

with open(a.out, "a") as f:
    for i, (name, text) in enumerate(problems):
        if name in done:
            continue
        r = solve(text, a.config, Budget(time_s=a.time, memory_mb=2048, cpu_s=0))
        rec = {"name": name, "solved": r.solved, "wall": r.wall_time, "mem": r.peak_memory_mb,
               "depth": r.depth, "aux": r.aux, "ddar_calls": r.ddar_calls,
               "tool_calls": r.tool_calls, "reason": r.failure_reason,
               "n_rules": sum(r.rules_in_proof.values())}
        f.write(json.dumps(rec) + "\n"); f.flush()
        print(i, name.split("/")[-1], r.solved, f"{r.wall_time:.1f}s", (r.failure_reason or "")[:50], flush=True)
