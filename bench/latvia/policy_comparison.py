"""Compare the three frozen 70-rule policies by problem ID, with and without AR."""
import argparse
from collections import Counter
import json
from pathlib import Path
from statistics import median

from bench.latvia.domain_results import POLICIES
from bench.latvia.finalize import as_line
from bench.latvia.paired_ar import records
from bench.latvia.paired_results import outcome
from bench.latvia.scan_plan import ROOT, sha256

FOLDER = ROOT / "results/latvia-domains"
DOMAINS = ("full", "full_no_ar")
OUTCOMES = ("proved", "timeouts", "errors", "saturated", "depth_limit")


def record_path(folder, domain, policy):
    if domain == "full_no_ar" and policy == "deduction":
        return folder / "paired-ar/original-full_no_ar-deduction.jsonl"
    return folder / f"{domain}-{policy}.jsonl"


def search_outcome(row):
    if not row["solved"] and not row["proof"] and row["failure_reason"] == "not solved within depth 1":
        return "depth_limit"
    return outcome(row)


def compare(folder):
    names = set(json.loads((folder / "inputs.json").read_text())["problems"])
    comparison = {}
    for domain in DOMAINS:
        policies, outcomes, winners = {}, {}, []
        for policy in POLICIES:
            path = record_path(folder, domain, policy)
            rows = records(path, f"{domain}-{policy}")
            if set(rows) != names:
                raise ValueError(f"Problem IDs differ from the frozen set in {path}")
            results = {name: search_outcome(row) for name, row in rows.items()}
            counts = Counter(results.values())
            outcomes[policy] = results
            won = {name for name, status in results.items() if status == "proved"}
            winners.append(won)
            policies[policy] = {
                "outcomes": {key: counts[key] for key in OUTCOMES},
                "proved_with_added_point": sum(bool(rows[name]["aux"]) for name in won),
                "median_peak_mib": median(r["peak_memory_mb"] for r in rows.values()),
                "elapsed_seconds_total": round(sum(r["wall_time"] for r in rows.values()), 3),
                "source": str(path.relative_to(folder)), "sha256": sha256(path),
            }
        profiles = Counter(tuple(outcomes[policy][name] for policy in POLICIES) for name in names)
        comparison[domain] = {
            "policies": policies,
            "common_wins": sorted(set.intersection(*winners)),
            "any_wins": sorted(set.union(*winners)),
            "profiles": [{**dict(zip(POLICIES, profile)), "cases": count}
                         for profile, count in sorted(profiles.items())],
        }
    return {"cases": len(names), "runs": len(names) * len(DOMAINS) * len(POLICIES), "domains": comparison}


def table(study):
    body = []
    for domain, label in (("full", "On"), ("full_no_ar", "Off")):
        for policy, description in POLICIES.items():
            row = study["domains"][domain]["policies"][policy]
            counts = row["outcomes"]
            body.append(
                f'<tr><th scope="row">{description}</th><td>{label}</td><td>{counts["proved"]}</td>'
                f'<td>{row["proved_with_added_point"]}</td><td>{counts["timeouts"]}</td><td>{counts["errors"]}</td>'
                f'<td>{counts["saturated"]}</td><td>{counts["depth_limit"]}</td></tr>'
            )
    return "\n".join(body)


def export_configs(scan, folder, configs):
    inputs = json.loads((folder / "inputs.json").read_text())
    if inputs != json.loads((scan / "inputs.json").read_text()):
        raise ValueError("The original scan has a different frozen input manifest")
    pending = []
    for domain, policy in configs:
        cfg = f"{domain}-{policy}"
        read = {}
        record_dir = scan / "records" / cfg
        for item in record_dir.rglob("*.json"):
            row = json.loads(item.read_text())
            name = row["name"]
            relative_name = item.relative_to(record_dir).as_posix()
            if row["config"] != cfg or name in read or relative_name != name + ".json":
                raise ValueError(f"Misidentified record in {cfg}")
            search_outcome(row)
            read[name] = row
        if set(read) != set(inputs["problems"]):
            raise ValueError(f"Incomplete 65-case configuration: {cfg}")
        path = record_path(folder, domain, policy)
        if path.exists():
            if records(path, cfg) != read:
                raise ValueError(f"Conflicting archived evidence at {path}")
        else:
            pending.append((path, "".join(as_line(read[n]) for n in sorted(read))))
    for path, body in pending:
        temp = path.with_suffix(".tmp")
        temp.write_text(body)
        temp.replace(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-scan", type=Path, help="Verify or import the six complete original configurations")
    args = parser.parse_args()
    if args.from_scan:
        export_configs(args.from_scan, FOLDER, ((d, p) for d in DOMAINS for p in POLICIES))
    print(json.dumps(compare(FOLDER), ensure_ascii=False, indent=2))
