"""Replay the preselected translation review sample using 32 goal-blind drawings per case."""
import argparse
import csv
from collections import Counter
import hashlib
import json
from pathlib import Path

from bench.latvia.scan import accepted_cases
from bench.latvia.translation_status import GT
from pipeline.check_figure import check_figure

SEEDS = 32
SALT = "zpd-20261122-audit/"


def audit():
    with (GT / "status.csv").open(newline="") as stream:
        pool = [r["id"] for r in csv.DictReader(stream) if r["stage"] == "accepted" and not r["decision"].strip()]
    ranked = sorted(pool, key=lambda name: hashlib.sha256((SALT + name).encode()).digest())
    cases = accepted_cases()
    samples = []
    for name in ranked[:6]:
        rows = check_figure(cases[name], seeds=SEEDS)
        observations = []
        for row in rows:
            status = "unbuilt"
            if row.built:
                if row.min_distance is not None and row.min_distance < 1e-6:
                    status = "degenerate"
                elif row.goals and all(row.goals.values()):
                    status = "all_goals_hold"
                else:
                    status = "goal_failed"
            observations.append({"seed": row.seed, "outcome": status, "goals": row.goals})
        samples.append({"name": name, "formalization_sha256": hashlib.sha256(cases[name].encode()).hexdigest(),
                        "drawings": observations})
    return {"pool": len(pool), "sampling_salt": SALT, "seeds": list(range(SEEDS)), "cases": samples}


def summarize(evidence):
    seeds = evidence["seeds"]
    ids = [r["name"] for r in evidence["cases"]]
    if len(ids) != len(set(ids)) or sorted(set(seeds)) != seeds:
        raise ValueError("Duplicate case or seed in the figure audit")
    counts = Counter()
    for case in evidence["cases"]:
        if [d["seed"] for d in case["drawings"]] != seeds:
            raise ValueError(f"Missing or reordered seeds for {case['name']}")
        for drawing in case["drawings"]:
            status, goals = drawing["outcome"], drawing["goals"]
            if status not in ("unbuilt", "degenerate", "all_goals_hold", "goal_failed"):
                raise ValueError(f"Unknown drawing outcome {status!r}")
            if status == "all_goals_hold" and not (goals and all(goals.values())):
                raise ValueError(f"Passing drawing lacks matching goals for {case['name']}")
            counts[status] += 1
    return {"cases": len(ids), "attempts": sum(counts.values()), "outcomes": dict(counts)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(audit(), ensure_ascii=False, indent=2) + "\n")
