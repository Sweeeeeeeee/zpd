"""Check the interior-of-segment hypothesis in the 1998–99 national problem 49.17."""
import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path

from newclid.jgex.formulation import JGEXFormulation
from newclid.jgex.problem_builder import JGEXProblemBuilder

from bench.latvia.scan import accepted_cases
from bench.latvia.scan_plan import ROOT, sha256
from pipeline.check_figure import check_figure
from pipeline.solve import solve

NAME = "latvia/national/1998-99_49/grade12/p2"
ORIGINAL = "m = on_line m a b"
BOUNDED = "m = between_bound m a b"
FIRST, END = 32, 160


def position(prefix, seed):
    setup = JGEXProblemBuilder(rng=seed).with_problem(prefix).build(max_attempts_to_satisfy_goals_numerically=1)
    coords = {point.name: complex(point.num.x, point.num.y) for point in setup.points}
    t = (coords["m"] - coords["a"]) / (coords["b"] - coords["a"])
    if abs(t.imag) > 1e-7:
        raise ValueError(f"M is off line AB at seed {seed}")
    return t.real


def outcome(row):
    if not row.built:
        return "unbuilt"
    if row.min_distance is None or row.min_distance < 1e-6:
        return "degenerate"
    if not row.goals:
        raise ValueError(f"No goals at seed {row.seed}")
    return "all_goals_hold" if all(row.goals.values()) else "goal_failed"


def constructions():
    text = accepted_cases()[NAME]
    if text.count(ORIGINAL) != 1:
        raise ValueError("Frozen M construction changed")
    return text, text.replace(ORIGINAL, BOUNDED)


def measure():
    text, candidate = constructions()
    original_rows = check_figure(text, seeds=END)
    bounded_rows = check_figure(candidate, seeds=END)
    original_prefix = text.split(ORIGINAL)[0] + ORIGINAL
    prefix = JGEXFormulation.from_text(original_prefix)
    records = []
    for seed in range(FIRST, END):
        t = position(prefix, seed)
        records.append({"seed": seed, "original_segment_parameter": t,
                        "original": outcome(original_rows[seed]), "bounded": outcome(bounded_rows[seed])})
    return {"name": NAME, "original_clause": ORIGINAL, "replacement_clause": BOUNDED,
            "records": records}


def compare_deduction(config):
    manifest = json.loads((ROOT / "results/latvia-domain-plan.json").read_text())
    if sha256(config) != manifest["configs"]["full-deduction.json"] or os.getenv("PYTHONHASHSEED") != "0":
        raise ValueError("Use the frozen full-deduction configuration and PYTHONHASHSEED=0")
    original, bounded = constructions()
    runs = []
    for label, text in (("original", original), ("bounded", bounded)):
        result = solve(text, config.resolve())
        runs.append({"construction": label, "formalization_sha256": hashlib.sha256(text.encode()).hexdigest(),
                     **asdict(result)})
    return {"name": NAME, "configuration_sha256": sha256(config), "runs": runs}


def summarize(evidence, frozen_drawings):
    rows = evidence["records"]
    if (evidence["name"], evidence["original_clause"], evidence["replacement_clause"]) != (NAME, ORIGINAL, BOUNDED):
        raise ValueError("Unexpected problem or construction in segment comparison")
    if [r["seed"] for r in rows] != list(range(FIRST, END)):
        raise ValueError("Incomplete seed blocks in segment comparison")
    expected = {seed: "all_goals_hold" for seed in range(32, 96)}
    expected.update(dict.fromkeys(frozen_drawings["unbuilt"], "unbuilt"))
    expected.update(dict.fromkeys(frozen_drawings["degenerate"], "degenerate"))
    expected.update({fail["seed"]: "goal_failed" for fail in frozen_drawings["failed_goals"]})
    if any(row["original"] != expected[row["seed"]] for row in rows[:64]):
        raise ValueError("Segment replay differs from the frozen construction audit")
    blocks = []
    for start in (32, 96):
        block = [r for r in rows if start <= r["seed"] < start + 64]
        blocks.append({key: dict(Counter(r[key] for r in block)) for key in ("original", "bounded")})
    return blocks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--deduction-config", type=Path, help="Run the matched proof search using full-deduction.json")
    args = parser.parse_args()
    result = compare_deduction(args.deduction_config) if args.deduction_config else measure()
    args.output.write_text(json.dumps(result, indent=2) + "\n")
