"""Render the frozen paired deduction results with corrected official problem labels."""
import csv
import json
from html import escape
from urllib.parse import quote

from bench.latvia.paired_ar import CONFIGS, records
from bench.latvia.paired_results import outcome
from bench.latvia.proof_catalog import anchor, catalog

COMPETITIONS = {"national": "National", "regional": "Regional", "open": "Open", "school": "Preparatory"}
LABELS = {"proved": "Proved", "saturated": "Exhausted", "timeouts": "Time limit", "errors": "Engine error"}


def problem_labels(root):
    with (root / "problems/latvia/geometry_translated/working_set.csv").open(newline="") as stream:
        selection = {r["id"]: r for r in csv.DictReader(stream)}
    with (root / "problems/latvia/index.csv").open(newline="") as stream:
        sources = {r["id"]: r for r in csv.DictReader(stream)}
    labels = {}
    for name, selected in selection.items():
        path = selected["path"]
        key = "latvia/" + path.removeprefix("problems/latvia/geometry/").removesuffix(".md")
        source = sources[key]
        group = source["competition"]
        if group == "tst":
            competition = "Baltic Way selection" if "_bw/" in key else "IMO selection"
        else:
            competition = COMPETITIONS[group]
        parts = [competition, source["season"]]
        if source["day"]:
            parts.append("extra round" if source["day"] == "extra" else "day " + source["day"])
        if source["grade"]:
            parts.append("grade " + source["grade"])
        parts.append("problem " + source["problem"])
        labels[name] = (" · ".join(parts), path)
    return labels


def render_cases(root, passed_drawings, *, labels=None, proofs=None):
    research = root / "results/latvia-domains"
    if labels is None:
        labels = problem_labels(root)
    if proofs is None:
        audit = (research / "paired-ar/ar-steps.jsonl").read_text().splitlines()
        proofs, _ = catalog(research / "full-deduction.jsonl", [json.loads(line) for line in audit])
    on = records(research / "full-deduction.jsonl", CONFIGS[0])
    off = records(research / "paired-ar/original-full_no_ar-deduction.jsonl", CONFIGS[1])
    if set(on) != set(off) or set(on) != set(passed_drawings):
        raise ValueError("The deduction and drawing records have different problem sets")
    rows = []
    for name, row in on.items():
        label, path = labels[name]
        result = outcome(row)
        step_link = "—"
        if row["solved"]:
            steps = len(proofs[name]["steps"])
            step_link = f'<a href="#{escape(anchor(name))}" aria-label="Read {steps} steps for {escape(label)}">{steps}</a>'
        rows.append(
            f'<tr data-outcome="{result}"><th scope="row"><a href="https://github.com/Sweeeeeeeee/zpd/blob/main/{quote(path)}">'
            f'{escape(label)}</a></th><td>{LABELS[result]}</td><td>{LABELS[outcome(off[name])]}</td>'
            f'<td>{step_link}</td><td>{row["wall_time"]:.1f}</td><td>{row["peak_memory_mb"]:.0f}</td><td>{passed_drawings[name]}</td></tr>'
        )
    return "\n".join(rows)
