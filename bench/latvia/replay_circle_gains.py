"""Replay the point constructions that extended deduction in the completed circle-rule scan."""
import argparse
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory

from bench.latvia.scan import prepare, write_json
from bench.latvia.scan_plan import sha256
from pipeline.solve import solve
from pipeline.tools import AuxConstruction, ProofState


def read_rows(folder, policy):
    config = "circles-" + policy
    rows = [json.loads(line) for line in (folder / (config + ".jsonl")).read_text().splitlines()]
    indexed = {row["name"]: row for row in rows}
    if len(rows) != len(indexed) or any(row["config"] != config for row in rows):
        raise ValueError(f"Unexpected original record in {config}")
    return indexed


def original_gains(folder):
    deduction = read_rows(folder, "deduction")
    sources = {}
    for policy in ("heuristics", "combined"):
        rows = read_rows(folder, policy)
        if rows.keys() != deduction.keys():
            raise ValueError("Policy inputs differ from deduction")
        for name, row in rows.items():
            if deduction[name]["solved"] or not row["solved"] or not row["aux"]:
                continue
            point, = row["aux"]
            key = (name, point["source"], tuple(point["clauses"]))
            sources.setdefault(key, {})[policy] = row["proof"]

    return sources


def replay(folder, output):
    sources = original_gains(folder)
    with TemporaryDirectory() as tmp:
        work = Path(tmp)
        cases, _ = prepare(work)
        manifest = folder / "original-inputs.json"
        if (work / "inputs.json").read_bytes() != manifest.read_bytes() or cases.keys() != json.loads(manifest.read_text())["problems"].keys():
            raise ValueError("Use the frozen original solver and corpus")
        config = work / "configs/circles-deduction.json"
        measurements = []
        for (name, tool, clauses), proofs in sorted(sources.items()):
            state = ProofState.from_text(cases[name]).child(AuxConstruction(clauses, tool))
            result = solve(state.text(), config)
            measurements.append(dict(name=name, original_policies=list(proofs), source=tool,
                                     clauses=list(clauses), problem_with_point=state.text(),
                                     same_transcript={p: bool(result.proof and result.proof == proof)
                                                      for p, proof in proofs.items()},
                                     result=asdict(result)))
        write_json(output, dict(input_sha256=sha256(manifest), config_sha256=sha256(config),
                                measurements=measurements))


def verify(folder, report):
    from bench.latvia.scan import accepted_cases

    manifest = folder / "original-inputs.json"
    plan = folder.parents[1] / "latvia-domain-plan.json"
    frozen = json.loads(plan.read_text())["configs"]["circles-deduction.json"]
    if (sha256(plan) != json.loads(manifest.read_text())["configuration_manifest_sha256"]
            or report["config_sha256"] != frozen or report["input_sha256"] != sha256(manifest)):
        raise ValueError("Replay evidence differs from the original configuration")
    sources = original_gains(folder)
    cases = accepted_cases()
    seen = set()
    repeated = 0
    for row in report["measurements"]:
        key = (row["name"], row["source"], tuple(row["clauses"]))
        if key not in sources or key in seen:
            raise ValueError("Unexpected or duplicate replayed construction")
        seen.add(key)
        proofs = sources[key]
        state = ProofState.from_text(cases[key[0]]).child(AuxConstruction(key[2], key[1]))
        result = row["result"]
        matches = {policy: bool(result["proof"] and result["proof"] == proof)
                   for policy, proof in proofs.items()}
        if (row["problem_with_point"] != state.text() or list(proofs) != row["original_policies"]
                or row["same_transcript"] != matches):
            raise ValueError("Replay differs from the archived problem or transcript")
        if (not result["solved"] or not result["proof"] or result["failure_reason"] or result["aux"]
                or result["tools_used"] != ["ddar"] or result["ddar_calls"] != 1 or result["depth"] != 0):
            raise ValueError("Replay lacks a proof using deduction alone")
        repeated += sum(matches.values())
    if seen != sources.keys():
        raise ValueError("Missing replay for an added point")
    return {"constructions": len(seen), "matching_transcripts": repeated}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("completed", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    replay(args.completed, args.output)
