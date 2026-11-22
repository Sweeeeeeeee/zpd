"""Repeat the three alternate reduced-rule proofs on two new numerical drawing seeds."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory


def deduced_part(proof):
    """Compare printed deductions and their algebra appendix, omitting the drawing section."""
    return proof.partition("# Proof:\n")[2].strip() if proof else None


def run(evidence, output):
    from bench.latvia.scan import prepare, write_json
    from bench.latvia.scan_plan import sha256
    from pipeline.solve import solve

    def records(cfg):
        path = evidence / (cfg + ".jsonl")
        items = [json.loads(s) for s in path.read_text().splitlines()]
        index = {i["name"]: i for i in items}
        if len(index) != len(items) or any(r["config"] != cfg for r in items):
            raise ValueError(f"Unexpected record in {cfg}")
        return index

    full, reduced = (records(cfg) for cfg in ("full-deduction", "no_similarity-deduction"))
    with TemporaryDirectory() as temporary:
        work = Path(temporary)
        problems, frozen = prepare(work)
        if (work / "inputs.json").read_bytes() != (evidence / "inputs.json").read_bytes():
            raise ValueError("Use the frozen baseline solver and environment")
        if set(full) != set(problems) or set(reduced) != set(problems):
            raise ValueError("Problem IDs differ from the frozen cohort")
        names = [n for n in sorted(problems) if full[n]["solved"] and reduced[n]["solved"]
                 and full[n]["proof"] != reduced[n]["proof"]]
        original = next(p for p in frozen if p.stem == "no_similarity-deduction")
        report = dict(input_sha256=sha256(evidence / "inputs.json"), original_config_sha256=sha256(original),
                      selected=names, seeds=[1, 2], cpu_affinity=sorted(os.sched_getaffinity(0)), measurements=[])
        for seed in report["seeds"]:
            cfg = json.loads(original.read_text())
            cfg["tools"]["ddar"]["options"]["seed"] = seed
            path = work / f"seed-{seed}.json"
            write_json(path, cfg)
            for name in names:
                result = solve(problems[name], path)
                same = bool(result.proof and deduced_part(result.proof) == deduced_part(reduced[name]["proof"]))
                report["measurements"].append(dict(name=name, seed=seed, config_sha256=sha256(path),
                                                   same_printed_deductions=same, **asdict(result)))
                print(seed, name, result.failure_reason or "proved", "same printed deductions:", same, flush=True)
        write_json(output, report)


def verify(evidence, report):
    import hashlib
    from bench.latvia.restricted_budget import archive_rows
    from bench.latvia.scan_plan import freeze, sha256

    original = archive_rows(evidence / "full-deduction.jsonl")
    reduced = archive_rows(evidence / "no_similarity-deduction.jsonl")
    names = sorted(n for n in original if original[n]["solved"] and reduced[n]["solved"]
                   and original[n]["proof"] != reduced[n]["proof"])
    if (report["selected"] != names or report["seeds"] != [1, 2]
            or report["input_sha256"] != sha256(evidence / "inputs.json")):
        raise ValueError("Seed study differs from the frozen alternate-proof cohort")
    hashes = {}
    with TemporaryDirectory() as tmp:
        configs = Path(tmp) / "configs"
        freeze(configs)
        template = configs / "no_similarity-deduction.json"
        if sha256(template) != report["original_config_sha256"]:
            raise ValueError("Seed study references a different base configuration")
        cfg = json.loads(template.read_text())
        for seed in report["seeds"]:
            cfg["tools"]["ddar"]["options"]["seed"] = seed
            raw = (json.dumps(cfg, indent=2, ensure_ascii=False) + "\n").encode()
            hashes[seed] = hashlib.sha256(raw).hexdigest()
    rows = report["measurements"]
    if [(r["seed"], r["name"]) for r in rows] != [(s,n) for s in report["seeds"] for n in names]:
        raise ValueError("Missing or repeated seeded measurements")
    total_wins = same_deductions = same_context = changed_drawings = 0
    for row in rows:
        previous = reduced[row["name"]]["proof"]
        proof = row["proof"]
        if row["config_sha256"] != hashes[row["seed"]] or row["solved"] != bool(proof):
            raise ValueError("Inconsistent seeded configuration or proof")
        if row["solved"] == bool(row["failure_reason"]) or (proof and "# Proof:\n" not in proof):
            raise ValueError("Inconsistent seeded outcome")
        same = bool(proof and deduced_part(proof) == deduced_part(previous))
        if same != row["same_printed_deductions"]:
            raise ValueError("Reported deduction match differs from the transcripts")
        same_deductions += same
        if proof:
            total_wins += 1
            setup, divider, rest = proof.partition("## Assumptions:")
            old, _, old_rest = previous.partition("## Assumptions:")
            if not divider:
                raise ValueError("Missing initial assumptions in seeded transcript")
            same_context += rest == old_rest
            changed_drawings += setup != old
    return dict(problems=len(names), runs=len(rows), proved=total_wins, same_deductions=same_deductions,
                same_including_assumptions=same_context, changed_drawings=changed_drawings)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.evidence.absolute(), args.output.absolute())
