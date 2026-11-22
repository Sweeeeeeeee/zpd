"""Rerun frozen scan cells affected by Newclid's line or circle merge handling."""
import argparse
import fcntl
import json
from collections import Counter
from pathlib import Path

from bench.latvia.scan import prepare, run_case, write_json
from bench.latvia.scan_plan import sha256


def affected(row):
    reason = row["failure_reason"] or ""
    if "TypeError: unhashable type: 'LineMerge'" in reason:
        return True
    proof = row["proof"] or ""
    return "=(Circle merge)>" in proof or "=(Line merge)>" in proof


def outcome(row):
    if row["solved"]:
        return "proved"
    reason = row["failure_reason"] or ""
    if reason.startswith("time limit"):
        return "time limit"
    if reason.startswith(("deduction engine failed", "crashed:")):
        return "engine error"
    return reason or "unknown"


def retry(baseline, output, limit=None):
    cases, configs = prepare(output)
    original_inputs = json.loads((baseline / "inputs.json").read_text())
    revised_inputs = json.loads((output / "inputs.json").read_text())
    if original_inputs.pop("solver_sources") == revised_inputs.pop("solver_sources"):
        raise ValueError("Baseline and retry have identical solver sources")
    if original_inputs != revised_inputs:
        raise ValueError("The corpus, environment or frozen configurations differ")
    reference = {"input_sha256": sha256(baseline / "inputs.json")}
    source = output / "baseline.json"
    if source.exists() and json.loads(source.read_text()) != reference:
        raise ValueError("This retry directory belongs to a different baseline")
    write_json(source, reference)
    seen = eligible = new = 0
    counts = Counter()
    for config in configs:
        for name, text in sorted(cases.items()):
            relative = Path("records") / config.stem / (name + ".json")
            old = baseline / relative
            if not old.is_file():
                continue
            row = json.loads(old.read_text())
            if (row["config"], row["name"]) != (config.stem, name):
                raise ValueError(f"Incorrect source record at {old}")
            seen += 1
            if not affected(row):
                continue
            eligible += 1
            path = output / relative
            if not path.exists():
                if limit is not None and new >= limit:
                    continue
                new += 1
            record = run_case(path, name, text, config)
            original_sha = sha256(old)
            if "baseline_record_sha256" in record:
                if original_sha != record["baseline_record_sha256"]:
                    raise ValueError(f"Baseline record changed at {old}")
            else:
                record["baseline_record_sha256"] = original_sha
                write_json(path, record)
            counts[outcome(record)] += 1
    report = {"baseline_records": seen, "expected": len(cases) * len(configs),
              "eligible": eligible, "retried": sum(counts.values()), "outcomes": dict(counts)}
    write_json(output / "report.json", report)
    if seen == report["expected"] and eligible == report["retried"]:
        write_json(output / "complete.json", report)
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--limit", type=int, help="maximum new solves in this invocation")
    args = parser.parse_args()
    if args.baseline.resolve() == args.output.resolve():
        parser.error("Choose a separate output directory for the revised solver")
    if args.limit is not None and args.limit < 0:
        parser.error("The limit must be nonnegative")
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        retry(args.baseline, args.output, args.limit)


if __name__ == "__main__":
    main()
