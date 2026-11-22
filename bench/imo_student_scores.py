"""Match official IMO scores to the local deduction baseline within each eligible edition."""
import argparse
from collections import Counter, defaultdict
from html import escape
from itertools import combinations
from pathlib import Path
import json
import re

ID = re.compile(r"(\d{4})_p([1-6])([ab]?)")
LABELS = {"proved": "Proved", "exhausted": "Exhausted", "mixed": "Mixed"}


def compare(folder):
    frozen = (folder / "problems.txt").read_text().splitlines()
    rows = [json.loads(line) for line in (folder / "ddar_only.jsonl").read_text().splitlines()]
    if set(frozen) != {r["name"] for r in rows} or len(rows) != len(set(frozen)) or len(frozen) != len(rows):
        raise ValueError("IMO baseline and manifest have different IDs")
    groups = defaultdict(lambda: defaultdict(list))
    for row in rows:
        match = ID.fullmatch(row["name"])
        if not match:
            raise ValueError(f"Unrecognized IMO formalization: {row['name']}")
        if row["solved"] is True and row["reason"] is None:
            outcome = "proved"
        elif row["solved"] is False and row["reason"] == "DDAR saturated and no proposer tools are enabled":
            outcome = "exhausted"
        else:
            raise ValueError(f"Unclassified baseline outcome in {row['name']}")
        groups[int(match[1])][int(match[2])].append((row["name"], outcome))
    eligible = {year for year, problems in groups.items() if len(problems) >= 2}
    archive = json.loads((folder / "official-paired-scores.json").read_text())
    editions = archive["editions"]
    if {e["year"] for e in editions} != eligible or len(editions) != len(eligible):
        raise ValueError("Official score tables differ from the eligible editions")
    result = []
    comparisons = Counter()
    for edition in editions:
        year, n = edition["year"], edition["contestants"]
        totals = edition["item_totals"]
        if (len(totals) != 6 or not 0 < edition["teams"] <= n or sum(totals) != edition["score_sum"]
                or any(type(t) is not int or not 0 <= t <= 7 * n for t in totals)):
            raise ValueError(f"Inconsistent official score totals in {year}")
        histograms = edition["score_counts_0_to_7"]
        if len(histograms) != 6:
            raise ValueError(f"Missing official score histogram in {year}")
        for histogram, total in zip(histograms, totals):
            if (len(histogram) != 8 or any(type(v) is not int or v < 0 for v in histogram)
                    or sum(histogram) != n or sum(k * v for k, v in enumerate(histogram)) != total):
                raise ValueError(f"Individual and team scores disagree in {year}")
        items = []
        for number, variants in sorted(groups[year].items()):
            statuses = {outcome for _, outcome in variants}
            items.append(dict(number=number, total=totals[number - 1], mean=round(totals[number - 1] / n, 4),
                              full_marks=histograms[number - 1][7],
                              outcome=next(iter(statuses)) if len(statuses) == 1 else "mixed",
                              ids=sorted(name for name, _ in variants)))
        for a, b in combinations(items, 2):
            if a["outcome"] == b["outcome"]:
                comparisons["same_solver_outcome"] += 1
            elif "mixed" in (a["outcome"], b["outcome"]):
                comparisons["mixed_encodings"] += 1
            else:
                proved, unproved = (a, b) if a["outcome"] == "proved" else (b, a)
                difference = proved["total"] - unproved["total"]
                label = {1: "proved_higher", -1: "proved_lower", 0: "equal_means"}[(difference > 0) - (difference < 0)]
                comparisons[label] += 1
        result.append(dict(year=year, contestants=n, team_results=edition["team_results"],
                           individual_results=edition["individual_results"], items=items))
    return dict(formalizations=len(rows), official_items=sum(len(g) for g in groups.values()),
                matched_items=sum(len(e["items"]) for e in result),
                matched_encodings=sum(len(i["ids"]) for e in result for i in e["items"]),
                comparisons=dict(sorted(comparisons.items())), editions=result)


def render(study):
    output = []
    for edition in study["editions"]:
        url = escape(edition["team_results"], quote=True)
        cells = []
        for item in edition["items"]:
            mean = item["total"] / edition["contestants"]
            cells.append(f'P{item["number"]} · {mean:.2f} · {LABELS[item["outcome"]]}')
        output.append(f'<tr><th scope="row"><a href="{url}">{edition["year"]}</a></th>'
                      f'<td>{edition["contestants"]}</td><td>{"<br>".join(cells)}</td></tr>')
    return "\n".join(output)

def verify_score_columns(edition, team_path, individual_path):
    """Check copied public table columns ordered as total, P1, P2, P3, P4, P5, P6."""
    for path, key in ((team_path, "teams"), (individual_path, "contestants")):
        rows = [list(map(int, line.split())) for line in path.read_text().splitlines() if line.strip()]
        if len(rows) != edition[key] or any(len(row) != 7 or sum(row[1:]) != row[0] for row in rows):
            raise ValueError(f"Invalid {key} table in {path}")
        if [sum(column) for column in zip(*rows)][1:] != edition["item_totals"]:
            raise ValueError(f"Point totals differ in {path}")
        if key == "contestants":
            if any(not 0 <= value <= 7 for row in rows for value in row[1:]):
                raise ValueError(f"Invalid individual score in {path}")
            counts = [[column.count(score) for score in range(8)] for column in list(zip(*rows))[1:]]
            if counts != edition["score_counts_0_to_7"]:
                raise ValueError(f"Score distributions differ in {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-tables", nargs=3, metavar=("YEAR", "TEAM_TSV", "INDIVIDUAL_TSV"))
    args = parser.parse_args()
    folder = Path(__file__).resolve().parents[1] / "results/local-cpu/imo"
    study = compare(folder)
    if args.check_tables:
        year, team_file, individual_file = args.check_tables
        data = json.loads((folder / "official-paired-scores.json").read_text())
        edition = next(e for e in data["editions"] if e["year"] == int(year))
        verify_score_columns(edition, Path(team_file), Path(individual_file))
        print(f"Verified both official score tables for IMO {year}.")
    else:
        print(json.dumps(study, indent=2))
