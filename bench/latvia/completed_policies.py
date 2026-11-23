"""Compare original policy wins by problem ID after all 18 scan configurations finish."""
from collections import Counter
import json

from bench.latvia.domain_results import POLICIES
from bench.latvia.finalize import category
from bench.latvia.paired_ar import records

RULES = {"full": "Full", "no_similarity": "Without similarity", "circles": "Circle rules"}


def analyze(folder, summary, expected_problems):
    inputs = json.loads((folder / "original-inputs.json").read_text())
    names = set(inputs["problems"])
    if inputs["problems"] != expected_problems or summary["problems"] != len(names):
        raise ValueError("Complete and published studies have different problem texts")
    settings = [domain + suffix for domain in RULES for suffix in ("", "_no_ar")]
    configs = {setting + "-" + policy for setting in settings for policy in POLICIES}
    if set(summary["configurations"]) != configs or summary["runs"] != len(configs) * len(names):
        raise ValueError("Missing configurations from the paired search comparison")
    comparisons = {}
    all_wins = set()
    for setting in settings:
        winners = {}
        added = set()
        for policy in POLICIES:
            config = setting + "-" + policy
            rows = records(folder / (config + ".jsonl"), config)
            if set(rows) != names:
                raise ValueError(f"Unexpected original problem IDs in {config}")
            counts = Counter(category(row) for row in rows.values())
            if counts != Counter(summary["configurations"][config]["baseline"]):
                raise ValueError(f"Original outcomes differ from the completed summary for {config}")
            proved = {n for n, row in rows.items() if row["solved"]}
            winners[policy] = proved
            added.update(n for n in proved if rows[n]["aux"])
        deduction = winners["deduction"]
        union = set.union(*winners.values())
        gains = union - deduction
        all_wins.update(union)
        comparisons[setting] = {
            "deduction": sorted(deduction), "any_policy": sorted(union),
            "all_policies": sorted(set.intersection(*winners.values())),
            "beyond_deduction": sorted(gains), "with_added_point": sorted(gains & added),
            "combined_only": sorted(winners["combined"] - deduction - winners["heuristics"]),
        }
    if len(all_wins) != summary["proved_by_any"]:
        raise ValueError("The union of the matched problem IDs differs from the reported total")
    return comparisons


def render(comparisons):
    rows = []
    for domain, label in RULES.items():
        for suffix, ar in (("", "On"), ("_no_ar", "Off")):
            group = comparisons[domain + suffix]
            cells = ("deduction", "all_policies", "any_policy", "beyond_deduction", "with_added_point", "combined_only")
            counts = "".join(f"<td>{len(group[key])}</td>" for key in cells)
            rows.append(f'<tr><th scope="row">{label}</th><td>{ar}</td>{counts}</tr>')
    return (
        '<h3 id="complete-search-overlap">Which problems did the search policies add?</h3>'
        '<p>Each row pairs original outcomes on the same problem IDs. A gain is a problem proved by a search '
        'policy after deduction alone missed it. The added-point column counts gains with at least one '
        'winning transcript that actually introduced a point. Combined-only means that only the policy '
        'running the model and heuristics proved the problem.</p><div class="scroll"><table>'
        '<caption>Original frozen solver · distinct problems in each rule and algebra setting</caption>'
        '<thead><tr><th>Rule set</th><th>AR</th><th>Deduction</th><th>All three</th><th>Any policy</th>'
        '<th>Gains over deduction</th><th>Gains with added point</th><th>Combined only</th></tr></thead>'
        '<tbody>' + "".join(rows) + '</tbody></table></div>'
    )


def retry_coverage(folder, summary, comparisons):
    originals = {name for group in comparisons.values() for name in group["any_policy"]}
    rows = [json.loads(line) for line in (folder / "retries.jsonl").read_text().splitlines()]
    keys = {(row["config"], row["name"]) for row in rows}
    if len(keys) != len(rows) or len(rows) != summary["retried"]:
        raise ValueError("Incomplete or duplicate retry evidence")
    counts = Counter((row["config"], category(row)) for row in rows)
    expected = Counter({(config, outcome): n for config, group in summary["configurations"].items()
                        for outcome, n in group["retries"].items()})
    if counts != expected:
        raise ValueError("Retry outcomes differ from the completed summary")
    proved = [row["name"] for row in rows if row["solved"]]
    return {"runs": len(rows), "proved_runs": len(proved), "additional_problems": sorted(set(proved) - originals),
            "original_problems": len(originals), "across_versions": len(originals.union(proved))}
