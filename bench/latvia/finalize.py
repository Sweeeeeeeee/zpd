"""Package the completed frozen scan and its paired merge retries for publication."""
import argparse
import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from bench.latvia.retry_merges import affected
from bench.latvia.scan_plan import sha256


def category(row):
    if row["solved"]:
        if not row["proof"] or row["failure_reason"]:
            raise ValueError(f"Missing or inconsistent proof for {row['name']}")
        return "proved"
    reason = row["failure_reason"] or ""
    if reason.startswith(("time limit", "CPU limit", "load time limit", "memory limit")):
        return "resource_limit"
    if reason.startswith(("deduction engine failed:", "crashed:", "problem could not be built:")):
        return "errors"
    return "other_unproved"


def as_line(record):
    line = json.dumps(record, ensure_ascii=False)
    if "/home/" in line or "/tmp/" in line:
        raise ValueError(f"Private filesystem path in {record['name']}. Review before publishing.")
    return line + "\n"


def finalize(original, revised, output):
    baseline = json.loads((original / "inputs.json").read_text())
    updated = json.loads((revised / "inputs.json").read_text())
    baseline_end = json.loads((original / "summary.json").read_text())
    retry_end = json.loads((revised / "complete.json").read_text())
    if json.loads((revised / "baseline.json").read_text())["input_sha256"] != sha256(original / "inputs.json"):
        raise ValueError("The retries belong to another baseline")
    if {k: v for k, v in baseline.items() if k != "solver_sources"} != {k: v for k, v in updated.items() if k != "solver_sources"}:
        raise ValueError("The corpus, plan or environment differs between studies")
    plans = original / "configs/manifest.json"
    if sha256(plans) != baseline["configuration_manifest_sha256"]:
        raise ValueError("Frozen configuration manifest changed")
    configs = [Path(name).stem for name in json.loads(plans.read_text())["configs"]]
    cases = sorted(baseline["problems"])
    if set(baseline_end["configurations"]) != set(configs) or baseline_end["problems"] != len(cases):
        raise ValueError("Original scan is incomplete")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / "completed"
        stage.mkdir()
        data = {}
        affected_rows = 0
        all_proved = set()
        with (stage / "retries.jsonl").open("w") as repairs:
            for cfg in configs:
                counts, retried = Counter(), Counter()
                with (stage / (cfg + ".jsonl")).open("w") as evidence:
                    for case in cases:
                        rel = Path("records") / cfg / (case + ".json")
                        path = original / rel
                        row = json.loads(path.read_text())
                        if (row["name"], row["config"]) != (case, cfg):
                            raise ValueError(f"Wrong record in {rel}")
                        counts[category(row)] += 1
                        if row["solved"]:
                            all_proved.add(case)
                        evidence.write(as_line(row))
                        new = revised / rel
                        if new.exists() != affected(row):
                            raise ValueError(f"Unexpected or missing retry: {rel}")
                        if new.exists():
                            retry = json.loads(new.read_text())
                            if (retry["name"], retry["config"]) != (case, cfg) or retry["baseline_record_sha256"] != sha256(path):
                                raise ValueError(f"Retry does not match {rel}")
                            retried[category(retry)] += 1
                            affected_rows += 1
                            repairs.write(as_line(retry))
                if counts["proved"] != baseline_end["configurations"][cfg].get("proved", 0):
                    raise ValueError(f"Baseline proof count mismatch for {cfg}")
                data[cfg] = {"baseline": dict(counts), "retries": dict(retried)}
        expected = len(cases) * len(configs)
        if (retry_end["expected"],retry_end["baseline_records"],retry_end["eligible"],retry_end["retried"]) != (expected, expected, affected_rows, affected_rows):
            raise ValueError("Retry completion counts disagree with the paired evidence")
        summary = {"problems": len(cases), "runs": expected, "proved_by_any": len(all_proved),
                   "retried": affected_rows, "configurations": data}
        for label, manifest in (("original", baseline), ("revised", updated)):
            (stage / (label + "-inputs.json")).write_text(json.dumps(manifest, indent=2) + "\n")
        (stage / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        if output.exists():
            old = {f.name: sha256(f) for f in output.iterdir()}
            new = {f.name: sha256(f) for f in stage.iterdir()}
            if old != new:
                raise ValueError("Existing publication differs. Choose a new output directory.")
        else:
            stage.rename(output)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "revised", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = finalize(args.original, args.revised, args.output)
    print(f"Verified {result['runs']} baseline and {result['retried']} paired records.")
