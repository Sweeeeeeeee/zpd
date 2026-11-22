"""Export and audit the paired 70-rule deduction experiments."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from bench.latvia.ar_audit import audit_proof
from bench.latvia.ar_context import construction_equations, supplement
from bench.latvia.finalize import as_line
from bench.latvia.paired_ar import CONFIGS, SOURCE, records
from bench.latvia.scan_plan import sha256


def read_json(path):
    return json.loads(path.read_text())


def equivalent_inputs(original, revised):
    return {k: v for k, v in original.items() if k != "solver_sources"} == {
        k: v for k, v in revised.items() if k != "solver_sources"}


def outcome(row):
    reason = row["failure_reason"] or ""
    if row["solved"] and row["proof"] and not reason:
        return "proved"
    if not row["solved"] and not row["proof"]:
        if reason.startswith("time limit"):
            return "timeouts"
        if reason.startswith(("deduction engine failed:", "crashed:")):
            return "errors"
        if reason == "DDAR saturated and no proposer tools are enabled":
            return "saturated"
    raise ValueError(f"Unknown outcome for {row['name']} in {row['config']}: {reason}")


def export(original, revised, output):
    output.mkdir(exist_ok=True, parents=True)

    def save(name, content):
        target = output / name
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f"Conflicting existing evidence in {target}")
        if not target.exists():
            temp = target.with_suffix(".tmp")
            temp.write_bytes(content)
            temp.replace(target)

    frozen = read_json(SOURCE / "inputs.json")
    updated = read_json(revised / "inputs.json")
    selection = read_json(revised / "selection.json")
    baseline = records(SOURCE / "full-deduction.jsonl", CONFIGS[0])
    wins = sorted(k for k, row in baseline.items() if row["solved"])
    if frozen != read_json(original / "inputs.json") or not equivalent_inputs(frozen, updated):
        raise ValueError("Input manifest differs from the frozen experiment")
    if selection["names"] != wins or selection["baseline_sha256"] != sha256(SOURCE / "full-deduction.jsonl"):
        raise ValueError("The selected cases differ from the frozen wins")
    if read_json(revised / "complete.json") != {"problems": len(wins), "runs": len(wins) * 2}:
        raise ValueError("The paired experiment has not finished")
    save("revised-inputs.json", (revised / "inputs.json").read_bytes())
    save("selection.json", (revised / "selection.json").read_bytes())
    facts = construction_equations(wins, frozen)
    save("construction-equations.json", (json.dumps(facts, indent=2, ensure_ascii=False) + "\n").encode())
    for label, source, names in (("original", original, sorted(frozen["problems"])), ("revised", revised, wins)):
        for config in CONFIGS:
            lines = []
            for name in names:
                row = read_json(source / "records" / config / (name + ".json"))
                if (row["name"], row["config"]) != (name, config):
                    raise ValueError(f"Misidentified record for {label}/{config}/{name}")
                outcome(row)
                if label == "original" and config == CONFIGS[0] and row != baseline[name]:
                    raise ValueError(f"Frozen source differs for {name}")
                lines.append(as_line(row))
            if label != "original" or config != CONFIGS[0]:
                save(f"{label}-{config}.jsonl", "".join(lines).encode())


def analyze(folder):
    original_inputs = read_json(folder.parent / "inputs.json")
    if not equivalent_inputs(original_inputs, read_json(folder / "revised-inputs.json")):
        raise ValueError("Study inputs differ beyond solver sources")
    baseline_path = folder.parent / (CONFIGS[0] + ".jsonl")
    selection = read_json(folder / "selection.json")
    if sha256(baseline_path) != selection["baseline_sha256"]:
        raise ValueError("Baseline checksum differs from selection manifest")
    baseline = {}
    revised = {}
    cases = set(original_inputs["problems"])
    wins = set(selection["names"])
    for config in CONFIGS:
        path = baseline_path if config == CONFIGS[0] else folder / f"original-{config}.jsonl"
        baseline[config] = records(path, config)
        revised[config] = records(folder / f"revised-{config}.jsonl", config)
        if set(baseline[config]) != cases or set(revised[config]) != wins:
            raise ValueError(f"Unexpected input ID set for {config}")
    on, off = CONFIGS
    if sorted(n for n in cases if baseline[on][n]["solved"]) != selection["names"]:
        raise ValueError("Selected IDs differ from the baseline AR wins")
    details = []
    tally = {}
    for label, rows, names in (("original", baseline, cases), ("original_wins", baseline, wins),
                               ("revised_wins", revised, wins)):
        tally[label] = {cfg: dict(sorted(Counter(outcome(rows[cfg][n]) for n in names).items()))
                        for cfg in CONFIGS}
    facts = read_json(folder / "construction-equations.json")
    if set(facts) != wins:
        raise ValueError("Construction facts differ from the selected IDs")
    repaired = Counter()
    steps = Counter()
    rule_cases = Counter()
    dependent = 0
    for name in sorted(wins):
        row = baseline[on][name]
        audit = audit_proof(row)
        for step in audit:
            extras = supplement(step, facts[name])
            if extras:
                step["additional_construction_equations"] = extras
                repaired[step["kind"]] += 1
        counts = Counter((s["kind"], s["outcome"]) for s in audit)
        steps.update(counts)
        rule_cases.update({k: 1 for k in ("Angle", "Ratio") if any(s["kind"] == k for s in audit)})
        dependent += any(s["outcome"] != "follows" for s in audit)
        details.append({"name": name, "steps": audit})
    audit_counts = {kind: {status: steps[kind, status] for status in ("follows", "needs_context", "inconsistent_premises")}
                    for kind in ("Angle", "Ratio")}
    return {"cases": len(cases), "selected": len(wins), "outcomes": tally, "rule_cases": dict(rule_cases),
            "identical_revised_transcripts": sum(baseline[on][n]["proof"] == revised[on][n]["proof"] for n in wins),
            "restored_by_construction_equations": dict(repaired),
            "original_wins_needing_context": dependent, "original_appendix_steps": audit_counts}, details


def budget_followup(folder):
    study = read_json(folder / "budget-180.json")
    if sha256(folder / "revised-inputs.json") != study["revised_inputs_sha256"]:
        raise ValueError("The budget follow-up uses different inputs")
    revised = {c: records(folder / f"revised-{c}.jsonl", c) for c in CONFIGS}
    timeouts = {n for n, row in revised[CONFIGS[0]].items() if outcome(row) == "timeouts"}
    expected = {(n, c) for n in timeouts for c in CONFIGS}
    rows = study["rows"]
    if len(rows) != len(expected) or {(r["name"], r["config"]) for r in rows} != expected:
        raise ValueError("Missing or unexpected budget follow-up cases")
    outcomes = {c: Counter() for c in CONFIGS}
    for row in rows:
        original = revised[row["config"]][row["name"]]
        encoded = json.dumps(original, ensure_ascii=False, indent=2) + "\n"
        if hashlib.sha256(encoded.encode()).hexdigest() != row["prior_record_sha256"]:
            raise ValueError(f"Budget follow-up source record changed for {row['name']}")
        outcomes[row["config"]][outcome(row)] += 1
    return {"cases": len(timeouts), "time_s": study["time_s"], "memory_mib": study["memory_mib"],
            "outcomes": {c: dict(counts) for c, counts in outcomes.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path, help="Frozen domain scan directory")
    parser.add_argument("revised", type=Path, help="Finished paired rerun directory")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    export(args.original, args.revised, args.output)
    summary, details = analyze(args.output)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (args.output / "ar-steps.jsonl").write_text("".join(as_line(row) for row in details))
