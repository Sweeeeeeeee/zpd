"""Run one problem under several DDAR configs and report which rules fired.

Examples (from the repo root, with .venv-newclid activated):

    python -m ddar.compare_rules -p orthocenter_consequence_aux \\
        ddar/configs/default.json ddar/configs/no_ar.json ddar/configs/no_orthocenter.json

    python -m ddar.compare_rules \\
        -s "a b c = triangle a b c; h = on_tline h b a c, on_tline h c a b ? perp a h b c" \\
        ddar/configs/*.json

"fired" counts every new fact a rule produced during the search; "in proof"
counts only the steps of the final proof.
"""

from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

from ddar.rule_config import load_config
from ddar.runner import solve_in_subprocess

DEFAULT_FILE = (
    Path(__file__).resolve().parents[1]
    / "third_party/Newclid/newclid/problems_datasets/examples.txt"
)


def _fmt(counts: dict[str, int]) -> str:
    return " ".join(f"{k}x{v}" for k, v in counts.items()) or "-"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("-p", "--problem-id", help="problem name in --file")
    src.add_argument("-s", "--problem", help="JGEX problem text")
    ap.add_argument("-f", "--file", type=Path, default=DEFAULT_FILE)
    ap.add_argument("configs", nargs="+", type=Path, help="DDAR config JSON files")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--out", type=Path, help="write results as JSON")
    args = ap.parse_args()

    configs = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        for path in args.configs:
            configs.append(load_config(path))
    for w in caught:
        print(f"WARNING {w.message}")
    if caught:
        print()

    problem = args.problem_id or args.problem
    problems_file = args.file if args.problem_id else None
    results = []
    for config in configs:
        res = solve_in_subprocess(problem, config, args.seed, problems_file, args.timeout)
        results.append(res)

    print(f"problem: {problem}\n")
    print(f"{'config':22s} {'rules':>5s} {'AR':>3s} {'solved':>6s} {'time':>6s}  rules in proof / rules fired")
    for config, res in zip(configs, results):
        ar = "on" if config.ar else "off"
        head = f"{config.name:22s} {len(config.rules()):5d} {ar:>3s}"
        if "error" in res:
            print(f"{head} {'ERR':>6s} {res['wall']:6.2f}  {res['error']}")
            continue
        solved = "yes" if res["success"] else "no"
        print(f"{head} {solved:>6s} {res['run_time']:6.2f}  proof: {_fmt(res['in_proof'])}")
        print(f"{'':45s}  fired: {_fmt(res['fired'])}")

    if args.out:
        args.out.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
