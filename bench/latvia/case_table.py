"""Render the frozen paired deduction results with corrected official problem labels."""
import csv
import re
from html import escape
from urllib.parse import quote

from bench.latvia.paired_ar import CONFIGS, records
from bench.latvia.paired_results import outcome

COMPETITIONS = {"national": "National", "regional": "Regional", "open": "Open", "school": "Preparatory"}
LABELS = {"proved": "Proved", "saturated": "Exhausted", "timeouts": "Time limit", "errors": "Engine error"}


def render_cases(root):
    research = root / "results/latvia-domains"
    with (root / "problems/latvia/geometry_translated/working_set.csv").open(newline="") as stream:
        selection = {r["id"]: r for r in csv.DictReader(stream)}
    with (root / "problems/latvia/index.csv").open(newline="") as stream:
        sources = {r["id"]: r for r in csv.DictReader(stream)}
    on = records(research / "full-deduction.jsonl", CONFIGS[0])
    off = records(research / "paired-ar/original-full_no_ar-deduction.jsonl", CONFIGS[1])
    if set(on) != set(off):
        raise ValueError("The configurations have different problem sets")
    rows = []
    for name, row in on.items():
        path = selection[name]["path"]
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
        label = " · ".join(parts)
        result = outcome(row)
        proof = row["proof"] or ""
        steps = len(re.findall(r"(?m)^\d+\. \| ", proof.partition("# Appendix:")[0]))
        if row["solved"] and not steps:
            raise ValueError(f"No proof steps found in {name}")
        rows.append(
            f'<tr data-outcome="{result}"><th scope="row"><a href="https://github.com/Sweeeeeeeee/zpd/blob/main/{quote(path)}">'
            f'{escape(label)}</a></th><td>{LABELS[result]}</td><td>{LABELS[outcome(off[name])]}</td>'
            f'<td>{steps or "—"}</td><td>{row["wall_time"]:.1f}</td><td>{row["peak_memory_mb"]:.0f}</td></tr>'
        )
    return "\n".join(rows)
