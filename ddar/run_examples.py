"""Run Newclid's DDAR on every problem in a JGEX problems file, on CPU.

Each problem runs in its own subprocess with a timeout, so one slow problem
cannot stall the batch. For every problem we record success, wall time, the
number of DDAR levels, and which rules (and AR reasons) produced new facts.

Engines:
    yuclid  Newclid's default when py-yuclid is installed: the C++ `yuclid` binary
            runs the whole DDAR, Python replays its deductions. Rule list ignored.
    python  Newclid's pure-Python DDARN + SymPy AR. Honours the rule list and the
            AR switch. Newclid 3.0.1 crashes here on rules with 3-point `diff`
            premises; --no-fix keeps that bug, otherwise it is patched at runtime.

Usage (activate the venv first so the `yuclid` binary is on PATH):
    python ddar/run_examples.py [--engine yuclid|python] [--file PATH] [--timeout 60]
                                [--no-ar] [--no-fix] [--seed 0] [--only NAME ...]
                                [--out results.json]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

DEFAULT_FILE = (
    Path(__file__).resolve().parents[1]
    / "third_party/Newclid/newclid/problems_datasets/examples.txt"
)


def patch_multi_point_diff() -> None:
    """Fix Newclid 3.0.1: predicate_from_construction assumes `diff` has 2 points,
    but rules r34-r37, r52, r53, ... use `diff A B C`. Diff itself accepts any
    number of points, so build it directly for that case."""
    import sys

    import newclid.predicates as preds
    from newclid.predicates._index import PredicateType
    from newclid.predicates.different import Diff

    original = preds.predicate_from_construction

    def fixed(construction, points_registry):
        if construction.predicate_type == PredicateType.DIFFERENT:
            args = tuple(sorted(construction.args))
            return Diff(points=tuple(points_registry.names2points(args)))
        return original(construction, points_registry)

    for mod in list(sys.modules.values()):
        if getattr(mod, "predicate_from_construction", None) is original:
            mod.predicate_from_construction = fixed


def solve_one(
    problems_file: Path, name: str, seed: int, use_ar: bool, engine: str, fix: bool
) -> dict:
    """Solve one problem in this process and return a JSON-able summary."""
    import logging

    logging.disable(logging.WARNING)

    from newclid.api import GeometricSolverBuilder, PythonDefault
    from newclid.justifications.justification import RuleApplication
    from newclid.deductors.deductor_interface import ARDeduction
    from newclid.jgex.problem_builder import JGEXProblemBuilder

    if engine == "python":
        api_default = PythonDefault(use_sympy_ar=use_ar)
        if fix:
            patch_multi_point_diff()
    else:
        from py_yuclid.api_default import HEDefault

        api_default = HEDefault()

    t0 = time.time()
    setup = (
        JGEXProblemBuilder(rng=seed)
        .with_problem_from_file(problems_path=problems_file, problem_name=name)
        .build()
    )
    build_time = time.time() - t0
    solver = GeometricSolverBuilder(rng=seed, api_default=api_default).build(setup)
    success = solver.run()
    infos = solver.run_infos

    fired: Counter[str] = Counter()
    for just in solver.proof_state.graph.hyper_graph.values():
        if isinstance(just, RuleApplication):
            fired[just.rule.id] += 1
        elif isinstance(just, ARDeduction):
            fired[f"AR:{just.ar_reason.value}"] += 1

    return {
        "name": name,
        "success": success,
        "build_time": round(build_time, 3),
        "run_time": round(infos.runtime, 3),
        "levels": getattr(infos.agent_stats, "max_level", None),
        "facts": len(solver.proof_state.graph.hyper_graph),
        "fired": dict(sorted(fired.items())),
        "rules_loaded": len(solver.rules),
    }


def problem_names(problems_file: Path) -> list[str]:
    lines = [ln.strip() for ln in problems_file.read_text().splitlines() if ln.strip()]
    return lines[0::2]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", type=Path, default=DEFAULT_FILE)
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--engine", choices=["yuclid", "python"], default="yuclid")
    ap.add_argument("--no-ar", action="store_true", help="python engine only")
    ap.add_argument("--no-fix", action="store_true", help="keep the diff bug")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--_child", nargs=1, help=argparse.SUPPRESS)
    args = ap.parse_args()

    if args._child:
        res = solve_one(args.file, args._child[0], args.seed, not args.no_ar,
                        args.engine, not args.no_fix)
        print("RESULT " + json.dumps(res))
        return

    names = args.only or problem_names(args.file)
    results = []
    print(f"{'problem':42s} {'ok':>4s} {'time':>7s} {'lvl':>4s} {'facts':>6s}  fired")
    for name in names:
        cmd = [sys.executable, __file__, "--file", str(args.file), "--seed",
               str(args.seed), "--engine", args.engine, "--_child", name]
        cmd += ["--no-ar"] * args.no_ar + ["--no-fix"] * args.no_fix
        t0 = time.time()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
            line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT ")), None)
            if line is None:
                err = (p.stderr.strip().splitlines() or ["no output"])[-1]
                res = {"name": name, "success": False, "error": err[:120]}
            else:
                res = json.loads(line[len("RESULT "):])
        except subprocess.TimeoutExpired:
            res = {"name": name, "success": False, "error": f"timeout {args.timeout:.0f}s"}
        res["wall"] = round(time.time() - t0, 2)
        results.append(res)
        if "error" in res:
            print(f"{name:42s} {'ERR':>4s} {res['wall']:7.2f}  {res['error']}")
        else:
            fired = " ".join(f"{k}x{v}" for k, v in res["fired"].items())
            print(f"{name:42s} {'yes' if res['success'] else 'no':>4s} "
                  f"{res['run_time']:7.2f} {str(res['levels'] or '-'):>4s} {res['facts']:6d}  {fired}")

    solved = sum(r["success"] for r in results)
    ar = "off" if args.no_ar and args.engine == "python" else "on"
    print(f"\nsolved {solved}/{len(results)}  (engine {args.engine}, AR {ar}, seed {args.seed})")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
