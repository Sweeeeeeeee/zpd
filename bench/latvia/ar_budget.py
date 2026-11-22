"""Repeat the 60-second AR-on timeouts in both settings with a 180-second budget."""
import argparse
from dataclasses import asdict
from pathlib import Path

from bench.latvia.paired_ar import CONFIGS
from bench.latvia.paired_results import read_json
from bench.latvia.scan import prepare, write_json
from bench.latvia.scan_plan import sha256
from pipeline.solve import Budget, solve


def run(source, output):
    problems, configs = prepare(source)
    configs = {p.stem: p for p in configs}
    selection = read_json(source / "selection.json")["names"]
    if read_json(source / "complete.json")["runs"] != len(selection) * 2:
        raise ValueError("The original pair is incomplete")
    result = {"revised_inputs_sha256": sha256(source / "inputs.json"), "selection": "Every revised AR-on timeout",
              "time_s": 180, "memory_mib": 2048, "rows": []}
    for name in selection:
        old = source / "records" / CONFIGS[0] / (name + ".json")
        if not (read_json(old)["failure_reason"] or "").startswith("time limit"):
            continue
        for config in CONFIGS:
            previous = source / "records" / config / (name + ".json")
            measurement = solve(problems[name], configs[config], Budget(time_s=180, memory_mb=2048))
            result["rows"].append({"name": name, "config": config, "prior_record_sha256": sha256(previous), **asdict(measurement)})
    write_json(output, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.source, args.output)
