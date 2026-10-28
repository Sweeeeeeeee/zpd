"""Run Newclid's DDAR on every problem in a JGEX problems file, on CPU.

Each problem runs in its own subprocess with a timeout, so one slow problem
cannot stall the batch. For every problem we record success, wall time, the
number of DDAR levels, and which rules (and AR reasons) produced new facts.

Usage (from the repo root, with .venv-newclid activated so `yuclid` is on PATH):
    python -m ddar.run_examples [--config ddar/configs/yuclid.json] [--file PATH]
                                [--timeout 60] [--seed 0] [--only NAME ...]
                                [--out results.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ddar.rule_config import load_config
from ddar.runner import solve_in_subprocess

HERE = Path(__file__).resolve().parent
DEFAULT_FILE = HERE.parent / "third_party/Newclid/newclid/problems_datasets/examples.txt"


def problem_names(problems_file: Path) -> list[str]:
    lines = [ln.strip() for ln in problems_file.read_text().splitlines() if ln.strip()]
    return lines[0::2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, default=HERE / "configs/yuclid.json")
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    config = load_config(args.config)
    names = args.only or problem_names(args.file)
    results = []
    print(f"{'problem':42s} {'ok':>4s} {'time':>7s} {'lvl':>4s} {'facts':>6s}  fired")
    for name in names:
        res = solve_in_subprocess(name, config, args.seed, args.file, args.timeout)
        res["name"] = name
        results.append(res)
        if "error" in res:
            print(f"{name:42s} {'ERR':>4s} {res['wall']:7.2f}  {res['error']}", flush=True)
        else:
            fired = " ".join(f"{k}x{v}" for k, v in res["fired"].items())
            print(f"{name:42s} {'yes' if res['success'] else 'no':>4s} "
                  f"{res['run_time']:7.2f} {str(res['levels'] or '-'):>4s} "
                  f"{res['facts']:6d}  {fired}", flush=True)

    solved = sum(r["success"] for r in results)
    print(f"\nsolved {solved}/{len(results)}  (config {config.name}, seed {args.seed})")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
