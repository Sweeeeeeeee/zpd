"""Repeat all reduced-domain timeouts among the original full-rule deduction wins."""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory


def archive_rows(path):
    rows = [json.loads(s) for s in path.read_text().splitlines()]
    data = {r["name"]: r for r in rows}
    if len(data) != len(rows) or any(r["config"] != path.stem for r in rows):
        raise ValueError(f"Duplicate or misidentified record in {path}")
    return data


def selected(folder):
    full = archive_rows(folder / "full-deduction.jsonl")
    reduced = archive_rows(folder / "no_similarity-deduction.jsonl")
    if full.keys() != reduced.keys():
        raise ValueError("Full and reduced problem IDs differ")
    return {name: reduced[name] for name in sorted(full) if full[name]["solved"]
            and (reduced[name]["failure_reason"] or "") == "time limit (60s)"}


def digest(row):
    return hashlib.sha256((json.dumps(row, indent=2, ensure_ascii=False) + "\n").encode()).hexdigest()


def run(folder, output):
    # Import from the frozen solver checkout selected in PYTHONPATH.
    from bench.latvia.scan import prepare, write_json
    from bench.latvia.scan_plan import sha256
    from pipeline.solve import Budget, solve

    with TemporaryDirectory() as tmp:
        work = Path(tmp)
        problems, configs = prepare(work)
        if (work / "inputs.json").read_bytes() != (folder / "inputs.json").read_bytes():
            raise ValueError("Use the baseline solver checkout and environment")
        cfg = next(p for p in configs if p.stem == "no_similarity-deduction")
        report = dict(input_sha256=sha256(folder / "inputs.json"), config=cfg.stem, time_s=180,
                      memory_mib=2048, cpu_affinity=sorted(os.sched_getaffinity(0)), rows=[])
        for name, prior in selected(folder).items():
            result = solve(problems[name], cfg, Budget(time_s=report["time_s"], memory_mb=report["memory_mib"]))
            row = dict(name=name, config=cfg.stem, prior_sha256=digest(prior), **asdict(result))
            report["rows"].append(row)
            print(name, result.failure_reason or "proved", flush=True)
        write_json(output, report)


def check(folder, report):
    wanted = selected(folder)
    inputs = hashlib.sha256((folder / "inputs.json").read_bytes()).hexdigest()
    if (report["input_sha256"] != inputs or report["config"] != "no_similarity-deduction"
            or report["time_s"] != 180 or report["memory_mib"] != 2048):
        raise ValueError("Unexpected baseline or retest budget")
    rows = report["rows"]
    if [r["name"] for r in rows] != list(wanted):
        raise ValueError("Retest selection differs from the original timeouts among full-rule wins")
    for row in rows:
        if row["prior_sha256"] != digest(wanted[row["name"]]) or row["config"] != report["config"]:
            raise ValueError("Retest row does not match its paired original")
        if row["solved"] != bool(row["proof"]) or row["solved"] == bool(row["failure_reason"]):
            raise ValueError("Inconsistent retest outcome")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.evidence.absolute(), args.output.absolute())
