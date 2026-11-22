"""Repeat deduction with and without algebraic reasoning on the original full-domain wins."""
import argparse
import fcntl
import json
from pathlib import Path

from bench.latvia.scan import prepare, run_case, write_json
from bench.latvia.scan_plan import ROOT, sha256

CONFIGS = ("full-deduction", "full_no_ar-deduction")
SOURCE = ROOT / "results/latvia-domains"


def records(path, config):
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    indexed = {row["name"]: row for row in rows}
    if len(rows) != len(indexed) or any(row["config"] != config for row in rows):
        raise ValueError(f"Duplicate ID or incorrect configuration in {path}")
    return indexed


def run(output):
    problems, paths = prepare(output)
    configs = {path.stem: path for path in paths}
    source_inputs = json.loads((SOURCE / "inputs.json").read_text())
    current_inputs = json.loads((output / "inputs.json").read_text())
    if any(source_inputs[key] != current_inputs[key] for key in source_inputs if key != "solver_sources"):
        raise ValueError("The corpus, configuration or environment does not match the original study")
    baseline = records(SOURCE / "full-deduction.jsonl", CONFIGS[0])
    if set(baseline) != problems.keys():
        raise ValueError("Incomplete original deduction data")
    names = sorted(name for name, row in baseline.items() if row["solved"])
    selection = {"baseline_sha256": sha256(SOURCE / "full-deduction.jsonl"), "names": names,
                 "order": "Lexical problem ID, alternating which configuration runs first."}
    selection_path = output / "selection.json"
    if selection_path.exists() and json.loads(selection_path.read_text()) != selection:
        raise ValueError("Baseline selection changed; choose a new output directory")
    write_json(selection_path, selection)
    for i, name in enumerate(names):
        order = CONFIGS if i % 2 == 0 else reversed(CONFIGS)
        for config in order:
            path = output / "records" / config / (name + ".json")
            run_case(path, name, problems[name], configs[config])
    write_json(output / "complete.json", {"problems": len(names), "runs": len(names) * len(CONFIGS)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        run(output)


if __name__ == "__main__":
    main()
