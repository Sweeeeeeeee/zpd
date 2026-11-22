"""Run the frozen Latvian domain scan and preserve proof traces, restarting after interruption."""
import argparse
import csv
import fcntl
import hashlib
import json
import os
import platform
import tempfile
from collections import Counter
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

from bench.latvia.scan_plan import ROOT, freeze, sha256
from bench.latvia.translation_status import GT, problem_line, working_set
from pipeline.solve import solve


def accepted_cases():
    with (GT / "status.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    status = {r["id"]: r["stage"] for r in rows}
    candidates = working_set()
    if len(status) != len(rows) or {r["id"] for r in candidates} != status.keys() or len(candidates) != len(rows):
        raise ValueError("Working-set IDs and review IDs must agree and be unique")
    cases = {}
    for candidate in candidates:
        name = candidate["id"]
        if status[name] != "accepted":
            continue
        text = problem_line(GT / (candidate["rel"] + ".txt"))
        if not text:
            raise ValueError(f"Missing accepted problem text for {name}")
        cases[name] = text
    if not cases:
        raise ValueError("The working set contains no accepted problems")
    return cases


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def prepare(output):
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise ValueError("Run with PYTHONHASHSEED=0 to fix Newclid predicate ordering")
    cases = accepted_cases()
    configs = output / "configs"
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        generated = Path(temporary) / "configs"
        freeze(generated)
        frozen = ROOT / "results/latvia-domain-plan.json"
        if (generated / "manifest.json").read_bytes() != frozen.read_bytes():
            raise ValueError("The generated configuration manifest differs from the frozen plan")
        if configs.exists():
            for path in generated.iterdir():
                if (configs / path.name).read_bytes() != path.read_bytes():
                    raise ValueError(f"Stored scan configuration changed: {path.name}")
        else:
            generated.rename(configs)
    plan = configs / "manifest.json"
    source_dirs = [ROOT / name for name in ("pipeline", "ddar", "geo-lm/geo_lm")]
    source_files = sorted(p for folder in source_dirs for p in folder.rglob("*.py"))
    source_files += [Path(__file__), ROOT / "bench/latvia/scan_plan.py"]
    manifest = {
        "configuration_manifest_sha256": sha256(plan),
        "python": platform.python_version(),
        "python_hash_seed": 0,
        "packages": {p: version(p) for p in ("newclid", "torch", "numpy", "sympy", "pydantic")},
        "solver_sources": {str(p.relative_to(ROOT)): sha256(p) for p in source_files},
        "problems": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in cases.items()},
    }
    previous = output / "inputs.json"
    if previous.exists() and json.loads(previous.read_text()) != manifest:
        raise ValueError("Inputs changed since this scan started. Use a new output directory.")
    write_json(previous, manifest)
    return cases, [configs / name for name in json.loads(plan.read_text())["configs"]]


def run_case(path, name, problem, config):
    if path.exists():
        row = json.loads(path.read_text())
    else:
        result = solve(problem, config)
        row = {"name": name, "config": config.stem, **asdict(result)}
    if (row["name"], row["config"]) != (name, config.stem):
        raise ValueError(f"Mismatched stored record at {path}")
    if row["solved"] and not (row["proof"] or "").strip():
        raise ValueError(f"Missing proof text for {name} under {config.stem}")
    if not path.exists():
        write_json(path, row)
        print(f"{config.stem}  {name}  {row['failure_reason'] or 'proved'}", flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    with (out / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        problems, configs = prepare(out)
        print(f"{len(problems)} problems × {len(configs)} configurations", flush=True)
        if args.prepare_only:
            return
        counts = {}
        for config in configs:
            outcomes = Counter()
            for name, text in problems.items():
                path = out / "records" / config.stem / (name + ".json")
                row = run_case(path, name, text, config)
                outcomes["proved" if row["solved"] else "unproved"] += 1
                if row["failure_reason"] and row["failure_reason"].startswith("crashed:"):
                    outcomes["crashes"] += 1
            counts[config.stem] = dict(outcomes)
        write_json(out / "summary.json", {"problems": len(problems), "configurations": counts})


if __name__ == "__main__":
    main()
