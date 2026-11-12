"""Task 7.2: sort the geometry problems by whether Newclid can state them.

Scheme (docs/tasks.md, task 7, agreed 2026-11-12):
  7.2a  prefilter   keyword hints for every problem (solid geometry, a "prove"
                    verb, a question for a value, a drawing, a missing formula)
  7.2b  batches     problem statements in batch files for the sorting agents;
                    each agent writes one CSV per batch (format in INSTRUCTIONS)
  7.2c  merge       all agent CSVs (+ sorting/corrections.csv, hand corrections
                    from the checks) -> sorting.csv, untranslatable.csv, and a
                    fixed-seed sample of 20 for the check

    python -m bench.latvia.sort_geometry prefilter
    python -m bench.latvia.sort_geometry batches --out DIR --size 190
    python -m bench.latvia.sort_geometry merge DIR

Output in problems/latvia/geometry_translated/sorting/ (kept in git).
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "problems/latvia/geometry"
OUT = ROOT / "problems/latvia/geometry_translated/sorting"
TRANSLATED = ROOT / "problems/latvia/geometry_translated"

# Hints only: the agent decides. "plaknē" (in the plane) is a plane marker, not solid.
SOLID = re.compile(r"telp|tetraedr|piramīd|\bkub[sauoēi]|prizm|\blod[ēeia]|sfēr|konus|cilindr|"
                   r"paralēlskaldn|daudzskaldn|skaldn|šķautn|divplakņu", re.I)
PROVE = re.compile(r"pierād|parād|pamato", re.I)
VALUE = re.compile(r"aprēķin|cik liel|cik ir|atrodi|atrast|nosaki|noteikt|kāds ir|kāda ir|kādu|kāds var", re.I)
INEQ = re.compile(r"nevienādīb|lielāk|mazāk|≤|≥|<|>", re.I)
FIGURE = re.compile(r"zīm\.|zīmējum|attēl", re.I)

CATEGORIES = {
    "prove": "yes",            # plane, goal is a fact Newclid can state (coll, para, perp, cong, cyclic, eqangle, eqratio, midp, simtri)
    "prove_other": "no",       # plane proof, but the goal is not a Newclid predicate (sum of lengths, area, inequality of lengths, tangency count, ...)
    "compute": "no",           # find a length, angle, area, ratio or number
    "inequality": "no",
    "construction": "no",      # construct with ruler and compass
    "find_all": "no",          # find all / locus / determine for which ...
    "existence": "no",         # does there exist / can one ... (yes-no questions)
    "combinatorial": "no",     # counting, colouring, cutting, covering, lattice points, games
    "solid": "no",
    "unreadable": "unsure",    # the statement is broken ([formula] missing, cut off)
}

INSTRUCTIONS = """You sort Latvian olympiad geometry problems for a solver (Newclid) that can only
handle this kind of problem: PLANE geometry, the figure is built point by point from
free points with ruler-and-compass style constructions (lines, circles, intersections,
midpoints, feet, reflections, given equal angles or lengths), and the task is to PROVE
one fact of this form: three points collinear; two lines parallel or perpendicular;
two segments equal; four points concyclic; two (directed) angles equal; two ratios of
segments equal; a point is a midpoint; two triangles similar. A tangency, an angle
bisector, an isosceles triangle or "X lies on circle ABC" count, as they reduce to these.

For every problem in the batch file, choose ONE category:
  prove          plane, prove a fact of the form above  -> statable yes
  prove_other    plane proof, but the goal is something else: a sum of lengths, an area,
                 an inequality between lengths, "the angle is 60 deg" is OK only if it can
                 be an equal-angles statement (then use prove), counting facts, etc.
  compute        find a length, angle, area, ratio or number
  inequality     prove or find an inequality
  construction   construct a figure with ruler and compass
  find_all       find all / locus / for which values
  existence      does there exist / can one / is it possible (yes-no questions)
  combinatorial  counting, colouring, cutting, covering, lattice points, games, point sets
  solid          three-dimensional geometry
  unreadable     the text is broken ([formula] missing so the problem cannot be understood)
If a problem has several parts, judge the main provable part: if one part is a
statable proof, use prove and say which part in the reason.

Write a CSV file (exactly the path given to you) with this header and one row per problem,
in the same order as the batch file:
  id,category,statable,confidence,figure,reason
statable: yes for prove, unsure for unreadable, no otherwise.
confidence: high, medium or low (low when the text is ambiguous or you are guessing).
figure: yes if the statement refers to a drawing ("skat. zīm.", "attēlā"), else no.
reason: at most 15 English words, in double quotes, e.g. "prove AB = CD in triangle with midpoints".
Do not skip any problem. Do not write anything else to the file."""


def statement(path: Path) -> str:
    text = path.read_text()
    return text.split("---", 2)[2].strip() if text.startswith("---") else text.strip()


def header_field(path: Path, key: str) -> str:
    m = re.search(rf"^{key}:[ \t]*(.*)$", path.read_text(), re.M)
    return m.group(1).strip().strip('"') if m else ""


def problems() -> list[tuple[str, Path]]:
    return [(header_field(p, "id") or str(p.relative_to(GEO)), p) for p in sorted(GEO.rglob("*.md"))]


def prefilter() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / "prefilter.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "path", "solid_hint", "prove_verb", "value_question", "inequality_hint",
                    "figure_hint", "needs_review", "chars"])
        for pid, p in problems():
            s = statement(p)
            w.writerow([pid, str(p.relative_to(ROOT)), int(bool(SOLID.search(s))), int(bool(PROVE.search(s))),
                        int(bool(VALUE.search(s))), int(bool(INEQ.search(s))), int(bool(FIGURE.search(s))),
                        header_field(p, "needs_review"), len(s)])
    return out


def batches(out_dir: Path, size: int) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    ps = problems()
    files = []
    for k in range(0, len(ps), size):
        f = out_dir / f"batch_{k // size + 1:02d}.txt"
        f.write_text("\n\n".join(f"### {pid}\n{' '.join(statement(p).split())}" for pid, p in ps[k:k + size]) + "\n")
        files.append(f)
    (out_dir / "INSTRUCTIONS.txt").write_text(INSTRUCTIONS + "\n")
    return files


def merge(in_dir: Path, seed: int = 20261112) -> None:
    ids = [pid for pid, _ in problems()]
    rows: dict[str, dict] = {}
    for f in sorted(in_dir.glob("batch_*.csv")):
        for r in csv.DictReader(f.open()):
            r = {k.strip(): (v or "").strip() for k, v in r.items() if k}
            if r.get("id") in ids:
                cat = r.get("category", "")
                if cat not in CATEGORIES:
                    r["confidence"] = "low"
                    r["reason"] = f"[bad category {cat!r}] " + r.get("reason", "")
                    cat = r["category"] = "unreadable"
                r["statable"] = CATEGORIES[cat]
                rows[r["id"]] = r
    # Hand corrections from the checks (sorting/corrections.csv) win over the agents.
    corr = OUT / "corrections.csv"
    if corr.exists():
        for c in csv.DictReader(corr.open()):
            if c["id"] in rows:
                rows[c["id"]].update(category=c["category"], statable=CATEGORIES[c["category"]],
                                     confidence="checked", reason=c["reason"])
    missing = [i for i in ids if i not in rows]
    hints = {r["id"]: r for r in csv.DictReader((OUT / "prefilter.csv").open())}
    fields = ["id", "category", "statable", "confidence", "figure", "reason", "solid_hint", "prove_verb", "needs_review"]
    with (OUT / "sorting.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for i in ids:
            if i in rows:
                w.writerow({**hints.get(i, {}), **rows[i]})
    with (TRANSLATED / "untranslatable.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "category", "reason"])
        for i in ids:
            if i in rows and rows[i]["statable"] == "no":
                w.writerow([i, rows[i]["category"], rows[i]["reason"]])
    if not (OUT / "check_sample.csv").exists():  # drawn once; a re-merge keeps the reviewed file
        write_check_sample([i for i in ids if i in rows], rows, seed)
    counts: dict[str, int] = {}
    for r in rows.values():
        counts[r["category"]] = counts.get(r["category"], 0) + 1
    print(f"{len(rows)} sorted, {len(missing)} missing", missing[:5])
    for c in CATEGORIES:
        print(f"  {c:14s} {counts.get(c, 0)}")
    print("statable:", sum(r["statable"] == "yes" for r in rows.values()),
          " low confidence:", sum(r.get("confidence") == "low" for r in rows.values()))


def write_check_sample(ids: list[str], rows: dict[str, dict], seed: int) -> None:
    sample = random.Random(seed).sample(ids, min(20, len(ids)))
    paths = dict(problems())
    with (OUT / "check_sample.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "category", "statable", "reason", "statement", "user_agrees (yes/no)", "user_category_if_no"])
        for i in sample:
            w.writerow([i, rows[i]["category"], rows[i]["statable"], rows[i]["reason"],
                        " ".join(statement(paths[i]).split()), "", ""])
    with (OUT / "check_sample.md").open("w") as f:  # the same, easier to read
        f.write("# Sorting check: 20 random problems (task 7.2c)\n\nFor each: is the category right? "
                "Write yes/no (and the right category) in check_sample.csv.\n\n"
                "Categories: " + ", ".join(CATEGORIES) + ". Only `prove` is statable.\n")
        for k, i in enumerate(sample, 1):
            f.write(f"\n## {k}. `{i}`: **{rows[i]['category']}**\n\n{rows[i]['reason']}\n\n> "
                    + " ".join(statement(paths[i]).split()) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prefilter")
    b = sub.add_parser("batches")
    b.add_argument("--out", required=True)
    b.add_argument("--size", type=int, default=190)
    m = sub.add_parser("merge")
    m.add_argument("dir")
    a = ap.parse_args()
    if a.cmd == "prefilter":
        print("wrote", prefilter())
    elif a.cmd == "batches":
        print("\n".join(str(f) for f in batches(Path(a.out), a.size)))
    else:
        merge(Path(a.dir))


if __name__ == "__main__":
    main()
