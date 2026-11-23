"""Summarize the published Latvian full-domain runs against their frozen input IDs."""
import json
from collections import Counter
from pathlib import Path

POLICIES = {"deduction": "Deduction alone", "heuristics": "Deduction + heuristics",
            "combined": "Deduction + model and heuristics"}


def full_domain_results(folder: Path):
    inputs = json.loads((folder / "inputs.json").read_text())
    names = set(inputs["problems"])
    policies = {}
    solved_sets = []
    for policy in POLICIES:
        config = "full-" + policy
        path = folder / (config + ".jsonl")
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        if len(rows) != len(names) or {r["name"] for r in rows} != names:
            raise ValueError(f"Missing or duplicate input IDs in {path}")
        counts = Counter()
        proved = set()
        for row in rows:
            if row["config"] != config:
                raise ValueError(f"Wrong configuration in {path}")
            reason = row["failure_reason"] or ""
            if row["solved"]:
                if not row["proof"] or reason:
                    raise ValueError(f"Inconsistent proof for {row['name']}")
                proved.add(row["name"])
                counts["with_aux"] += bool(row["aux"])
            elif reason.startswith("time limit"):
                counts["timeouts"] += 1
            elif reason.startswith(("deduction engine failed:", "crashed:")):
                counts["errors"] += 1
            elif reason == "DDAR saturated and no proposer tools are enabled":
                counts["saturated"] += 1
            else:
                counts["other"] += 1
        policies[policy] = {key: counts[key] for key in ("with_aux", "timeouts", "errors", "saturated", "other")}
        policies[policy]["proved"] = len(proved)
        solved_sets.append(proved)
    return {"cases": len(names), "policies": policies, "proved_by_all": len(set.intersection(*solved_sets)),
            "proved_by_any": len(set.union(*solved_sets))}


def complete_coverage(finished, cases):
    configs = finished["configurations"]
    if len(configs) != 18 or finished["problems"] != cases or finished["runs"] != 18 * cases:
        raise ValueError("Incomplete Latvian study summary")
    domain_names = {"full": "Full", "circles": "Circles", "no_similarity": "Without similarity"}
    table_rows = []
    for config, pair in configs.items():
        domain, policy = config.rsplit("-", 1)
        ar = "Off" if domain.endswith("_no_ar") else "On"
        label = domain_names[domain.removesuffix("_no_ar")]
        original, retry = pair["baseline"], pair["retries"]
        table_rows.append(
            f'<tr><th scope="row">{label}</th><td>{ar}</td><td>{POLICIES[policy]}</td>'
            f'<td>{original.get("proved", 0)}</td><td>{original.get("resource_limit", 0)}</td>'
            f'<td>{original.get("errors", 0)}</td><td>{original.get("other_unproved", 0)}</td>'
            f'<td>{retry.get("proved", 0)}/{sum(retry.values())}</td></tr>'
        )
    table = (
        '<h3>All six domains</h3><p>The original scan covered ' + str(finished["runs"]) +
        ' individual solves. A separate run revisited ' + str(finished["retried"]) +
        ' affected cells with the revised merge handling. The last column gives proved retries over cases retried.</p>'
        '<div class="scroll"><table><caption>Frozen results and targeted retries</caption>'
        '<thead><tr><th>Domain</th><th>Algebraic reasoning</th><th>Policy</th><th>Proved</th>'
        '<th>Resource limit</th><th>Engine or build error</th><th>Other unproved</th><th>Retry proofs</th>'
        '</tr></thead><tbody>' + "".join(table_rows) + '</tbody></table></div>'
        '<p><a href="https://github.com/Sweeeeeeeee/zpd/tree/main/results/latvia-domains/completed">'
        'All original and paired records</a>.</p>'
    )
    complete_paper = (
        f" Kopā sešās jomās un trīs meklēšanas stratēģijās veikti {finished['runs']} mēģinājumi. "
        f"Sākotnējā skenējumā dažādu pierādīto uzdevumu skaits bija {finished['proved_by_any']}. "
        f"Ar laboto dzinēju atsevišķi atkārtoti {finished['retried']} skartie mēģinājumi."
    )
    return table, complete_paper
