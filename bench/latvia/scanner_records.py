"""Compact, provenance-checked original scan records for the browser inspector."""
import hashlib
import json

from bench.latvia.scan import accepted_cases
from bench.latvia.finalize import category


def browser_records(folder, labels):
    if not (folder / "summary.json").exists():
        return []
    frozen = json.loads((folder / "original-inputs.json").read_text())["problems"]
    inputs = accepted_cases()
    if {name: hashlib.sha256(text.encode()).hexdigest() for name, text in inputs.items()} != frozen:
        raise ValueError("Scanner inputs differ from the original measured formalizations")
    cases = {name: {"id": name, "label": labels[name][0], "input": text, "runs": {}}
             for name, text in sorted(inputs.items())}
    for config in json.loads((folder / "summary.json").read_text())["configurations"]:
        seen = set()
        for line in (folder / f"{config}.jsonl").read_text().splitlines():
            row = json.loads(line)
            name = row["name"]
            if name in seen or row["config"] != config:
                raise ValueError(f"Unexpected scanner row in {config}")
            seen.add(name)
            cases[name]["runs"][config] = {
                "outcome": category(row), "seconds": round(row["wall_time"], 2),
                "memory": round(row["peak_memory_mb"]), "reason": row["failure_reason"],
                "proof": row["proof"], "aux": row["aux"],
            }
        if seen != cases.keys():
            raise ValueError(f"Incomplete scanner records in {config}")
    return list(cases.values())
