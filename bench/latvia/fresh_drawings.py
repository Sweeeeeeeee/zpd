"""Draw each frozen Latvian translation with seeds 32 through 95, without supplying its goals."""
import argparse
import hashlib
import json
from pathlib import Path

from bench.latvia.scan import accepted_cases
from bench.latvia.scan_plan import ROOT
from pipeline.check_figure import check_figure

FIRST, END = 32, 96
MIN_DISTANCE = 1e-6


def frozen_hashes():
    return json.loads((ROOT / "results/latvia-domains/inputs.json").read_text())["problems"]


def measure():
    frozen = frozen_hashes()
    problems = accepted_cases()
    if {name: hashlib.sha256(text.encode()).hexdigest() for name, text in problems.items()} != frozen:
        raise ValueError("Accepted problem IDs or texts differ from the frozen set")
    records = []
    for name, text in sorted(problems.items()):
        # The checker takes a prefix of seeds. Earlier seeds belong to the acceptance and sample checks.
        rows = check_figure(text, seeds=END)[FIRST:]
        if [row.seed for row in rows] != list(range(FIRST, END)):
            raise ValueError(f"Incomplete drawing set for {name}")
        failed_goals, unbuilt, degenerate = [], [], []
        for row in rows:
            if not row.built:
                unbuilt.append(row.seed)
            elif row.min_distance is not None and row.min_distance < MIN_DISTANCE:
                degenerate.append(row.seed)
            elif not row.goals:
                raise ValueError(f"No goals for {name} at seed {row.seed}")
            elif failed := [goal for goal, ok in row.goals.items() if not ok]:
                failed_goals.append({"seed": row.seed, "goals": failed})
        records.append({
            "name": name, "formalization_sha256": frozen[name], "unbuilt": unbuilt,
            "degenerate": degenerate, "failed_goals": failed_goals,
            "all_goals_hold": len(rows) - len(unbuilt) - len(degenerate) - len(failed_goals),
        })
    return {"first_seed": FIRST, "exclusive_end_seed": END, "degenerate_distance": MIN_DISTANCE, "records": records}


def summarize(evidence, hashes):
    seeds = range(FIRST, END)
    if (evidence["first_seed"], evidence["exclusive_end_seed"], evidence["degenerate_distance"]) != (FIRST, END, MIN_DISTANCE):
        raise ValueError("Unexpected seed block or degeneracy threshold")
    records = evidence["records"]
    if len(records) != len(hashes) or {r["name"]: r["formalization_sha256"] for r in records} != hashes:
        raise ValueError("Drawing records differ from the frozen case manifest")
    totals = {"all_goals_hold": 0, "unbuilt": 0, "degenerate": 0, "failed_goals": 0}
    for row in records:
        failures = row["failed_goals"]
        if any(not f["goals"] for f in failures):
            raise ValueError(f"Missing failed goal for {row['name']}")
        exceptions = row["unbuilt"] + row["degenerate"] + [f["seed"] for f in failures]
        if (len(set(exceptions)) != len(exceptions) or any(s not in seeds for s in exceptions)
                or row["all_goals_hold"] != len(seeds) - len(exceptions)):
            raise ValueError(f"Inconsistent seed outcomes for {row['name']}")
        totals["all_goals_hold"] += row["all_goals_hold"]
        for key in ("unbuilt", "degenerate", "failed_goals"):
            totals[key] += len(row[key])
    return {"cases": len(records), "seeds_per_case": len(seeds), "attempts": len(records) * len(seeds), **totals}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = measure()
    summarize(result, frozen_hashes())
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
