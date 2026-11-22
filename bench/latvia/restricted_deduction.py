"""Compare original full and no-similarity deduction records with algebraic reasoning on."""
import argparse
from collections import Counter
import json
from pathlib import Path

from bench.latvia.paired_ar import records
from bench.latvia.policy_comparison import export_configs, search_outcome
from bench.latvia.scan_plan import ROOT, sha256

FOLDER = ROOT / "results/latvia-domains"
CONFIGS = (("full", "deduction"), ("no_similarity", "deduction"))


def compare(root):
    folder = root / "results/latvia-domains"
    plan_path = root / "results/latvia-domain-plan.json"
    frozen = json.loads((folder / "inputs.json").read_text())
    if sha256(plan_path) != frozen["configuration_manifest_sha256"]:
        raise ValueError("The rule manifest differs from the frozen benchmark")
    plan = json.loads(plan_path.read_text())
    allowed = {}
    runs = {}
    for domain, policy in CONFIGS:
        file = f"ddar/configs/domains/{domain}.json"
        if sha256(root / file) != plan["sources"][file]:
            raise ValueError(f"The rule set differs from the frozen input: {file}")
        rule_set = json.loads((root / file).read_text())
        if rule_set["ar"] is not True:
            raise ValueError(f"Algebraic reasoning must be enabled for {domain}")
        allowed[domain] = set(rule_set["enabled_rules"])
        cfg = f"{domain}-{policy}"
        runs[domain] = records(folder / (cfg + ".jsonl"), cfg)
        if set(runs[domain]) != set(frozen["problems"]):
            raise ValueError(f"Incomplete matched records in {cfg}")
        for name, row in runs[domain].items():
            if set(row["rules_in_proof"]) - allowed[domain] - {"AR:angle", "AR:ratio"}:
                raise ValueError(f"Transcript uses a rule outside its domain in {name}")
    full, reduced = runs["full"], runs["no_similarity"]
    if not allowed["no_similarity"] < allowed["full"]:
        raise ValueError("The reduced rule set must be a strict subset")
    removed = allowed["full"] - allowed["no_similarity"]
    transition = Counter()
    proof_cases = {}
    for name, old in sorted(full.items()):
        new = reduced[name]
        old_status, new_status = search_outcome(old), search_outcome(new)
        transition[old_status, new_status] += 1
        if old["solved"] or new["solved"]:
            proof_cases[name] = dict(full=old_status, reduced=new_status,
                                     removed_rules=sorted(removed.intersection(old["rules_in_proof"])),
                                     full_steps=sum(old["rules_in_proof"].values()),
                                     reduced_steps=sum(new["rules_in_proof"].values()),
                                     same_transcript=bool(old["proof"] and old["proof"] == new["proof"]))
    return dict(cases=len(full), full_rules=len(allowed["full"]), reduced_rules=len(allowed["no_similarity"]),
                removed_rules=sorted(removed), full_wins=sum(r["solved"] for r in full.values()),
                reduced_wins=sum(r["solved"] for r in reduced.values()),
                retained=transition["proved","proved"], identical=sum(c["same_transcript"] for c in proof_cases.values()),
                regained_with_different_rules=sum(bool(c["removed_rules"]) and c["reduced"] == "proved" for c in proof_cases.values()),
                outcomes=[dict(full=a, reduced=b, cases=n) for (a,b), n in sorted(transition.items())],
                proof_cases=proof_cases)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-scan", type=Path)
    args = parser.parse_args()
    if args.from_scan:
        export_configs(args.from_scan, FOLDER, CONFIGS)
    print(json.dumps(compare(ROOT), indent=2))
