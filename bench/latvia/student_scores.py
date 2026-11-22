"""Join published 2015–16 grade 9 item means to their frozen and revised deduction runs."""
import json
from html import escape

from bench.latvia.paired_ar import records
from bench.latvia.paired_results import outcome

LABELS = {"proved": "Proved", "errors": "Engine error", "timeouts": "Time limit", "saturated": "Exhausted"}


def compare(root):
    audit = root / "results/latvia-audit"
    results = root / "results/latvia-domains"
    book = json.loads((audit / "official-scores.json").read_text())
    config = "full-deduction"
    original = records(results / "full-deduction.jsonl", config)
    revised = records(results / "paired-ar/revised-full-deduction.jsonl", config)
    extra = json.loads((audit / "grade9-open-retest.json").read_text())
    if extra["config"] != config or extra["name"] in revised:
        raise ValueError("Unexpected revised run in the official score comparison")
    revised[extra["name"]] = extra
    comparisons = []
    for item in book["cases"]:
        name = item["name"]
        n = item["problem_number"]
        if not name.endswith(f"/grade09/p{n}") or len(item["item_means"]) != 5:
            raise ValueError(f"Score column or grade does not match {name}")
        mean = item["item_means"][n - 1]
        comparisons.append({
            "name": name, "label": item["label"], "participants": item["participants"],
            "mean": mean, "rank_by_mean": 1 + sum(m > mean for m in item["item_means"]),
            "full_marks_percent": item["full_marks_percent"], "unattempted_percent": item["unattempted_percent"],
            "original": outcome(original[name]), "revised": outcome(revised[name]),
            "source": f"{book['source']}#page={item['scores_page']}",
        })
    return comparisons


def render(rows):
    return "\n".join(
        f'<tr><th scope="row"><a href="{escape(r["source"])}">{escape(r["label"])}</a></th>'
        f'<td>{r["participants"]}</td><td>{r["mean"]:.2f}</td><td>{r["full_marks_percent"]}%</td>'
        f'<td>{LABELS[r["original"]]}</td><td>{LABELS[r["revised"]]}</td></tr>'
        for r in rows
    )
