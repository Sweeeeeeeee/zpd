"""Task 7.3: the working set of Latvian problems to translate first.

From the statable problems (sorting.csv, category `prove`):
  1. Duplicates are MERGED, not deleted: the same problem set again in another
     year or olympiad becomes one entry that keeps every id, title, season and
     source (duplicates.csv lists the groups). The archive files stay as they
     are; the first id (oldest season) is the entry's name.
  2. Statements that look like several problems glued together (a split error
     in the archive extraction) and statements with a missing formula are
     flagged and left out of the working set until fixed.
  3. Problems that depend on a drawing are kept but marked; the translator
     needs the original file (link in the problem header).
  4. A fixed-seed sample spread over competitions, decades and grades:
     every selection test (tst) and national problem first in proportion,
     then the others.

    python -m bench.latvia.working_set            # writes problems/latvia/geometry_translated/working_set.csv
"""

from __future__ import annotations

import argparse
import csv
import random
import re
from collections import defaultdict
from pathlib import Path

from bench.latvia.sort_geometry import GEO, OUT, TRANSLATED, header_field, problems, statement

SEED = 20261112
# Share of the working set per competition (selection tests and the national olympiad first).
QUOTA = {"tst": 0.15, "national": 0.40, "open": 0.20, "regional": 0.15, "school": 0.10}


def norm(text: str) -> str:
    t = text.lower()
    t = re.sub(r"lu a\.\s*liepas neklātienes matemātikas skola|eiropas sociālā fonda.*$", " ", t)
    t = re.sub(r"\(?skat\.?[^)]*zīm\.?\)?|\d+\.\s*zīm\.?|\d+\.\s*att\.?", " ", t)
    return " ".join(re.findall(r"[a-zāčēģīķļņšūž0-9]+", t))


def shingles(t: str, k: int = 4) -> set[str]:
    w = t.split()
    return {" ".join(w[i:i + k]) for i in range(max(1, len(w) - k + 1))}


def glued(text: str) -> bool:
    """Several problems in one statement: a later problem number starting a new sentence."""
    return bool(re.search(r"[.?!]\s+[2-9]\.\s+[A-ZĀČĒĢĪĶĻŅŠŪŽ]", text)) or len(text) > 1500


def decade(season: str) -> str:
    y = int(season[:4]) if season[:4].isdigit() else 0
    return f"{y // 10 * 10}s"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=80)
    ap.add_argument("--pilot", type=int, default=10)
    a = ap.parse_args()

    sorting = {r["id"]: r for r in csv.DictReader((OUT / "sorting.csv").open())}
    paths = dict(problems())
    info = {}
    for pid, p in paths.items():
        s = " ".join(statement(p).split())
        info[pid] = {"id": pid, "path": str(p.relative_to(GEO.parents[2])), "text": s, "norm": norm(s),
                     "competition": pid.split("/")[1], "season": header_field(p, "season"),
                     "grade": header_field(p, "grade"), "title": header_field(p, "title"),
                     "source": header_field(p, "source"), "needs_review": header_field(p, "needs_review")}

    # 1. duplicate groups over ALL geometry problems (a duplicate may be sorted differently)
    ids = sorted(info, key=lambda i: (info[i]["season"], i))
    sh = {i: shingles(info[i]["norm"]) for i in ids}
    parent = {i: i for i in ids}

    def find(i: str) -> str:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_first = defaultdict(list)  # cheap blocking: same first 6 words or same last 6 words
    for i in ids:
        w = info[i]["norm"].split()
        by_first[("f", " ".join(w[:6]))].append(i)
        by_first[("l", " ".join(w[-6:]))].append(i)
    for group in by_first.values():
        for x in range(len(group)):
            for y in range(x + 1, len(group)):
                i, j = group[x], group[y]
                inter = len(sh[i] & sh[j])
                if inter and inter / len(sh[i] | sh[j]) >= 0.8:
                    parent[find(j)] = find(i)
    groups = defaultdict(list)
    for i in ids:
        groups[find(i)].append(i)
    dups = {g: m for g, m in groups.items() if len(m) > 1}
    with (TRANSLATED / "duplicates.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entry", "ids", "titles", "seasons", "sources", "categories"])
        for g, m in sorted(dups.items()):
            w.writerow([m[0], " | ".join(m), " | ".join(info[i]["title"] for i in m),
                        " | ".join(info[i]["season"] for i in m), " | ".join(info[i]["source"] for i in m),
                        " | ".join(sorting.get(i, {}).get("category", "?") for i in m)])

    # 2-3. candidates: statable, one entry per duplicate group, clean text
    entries = []
    for g, m in groups.items():
        cats = [sorting.get(i, {}).get("category") for i in m]
        if "prove" not in cats:
            continue
        e = dict(info[m[0]])
        e["also"] = m[1:]
        e["figure"] = any(sorting.get(i, {}).get("figure") == "yes" for i in m) or bool(
            re.search(r"zīm\.|zīmējum|attēl|\d+\.\s*att", e["text"], re.I))
        e["glued"] = glued(e["text"])
        e["formula_missing"] = "[formula]" in e["text"] or "formula" in e["needs_review"]
        e["low_conf"] = any(sorting.get(i, {}).get("confidence") == "low" for i in m)
        entries.append(e)
    clean = [e for e in entries if not (e["glued"] or e["formula_missing"] or e["low_conf"])]

    # 4. stratified, fixed seed: per competition quota, spread over decades and grades
    rng = random.Random(SEED)
    chosen = []
    for comp, share in QUOTA.items():
        pool = [e for e in clean if e["competition"] == comp]
        rng.shuffle(pool)
        pool.sort(key=lambda e: e["figure"])  # stable: problems without a drawing first
        want = round(share * a.size)
        strata = defaultdict(list)
        for e in pool:
            strata[(decade(e["season"]), e["grade"])].append(e)
        keys = sorted(strata)
        rng.shuffle(keys)
        picked = []
        while len(picked) < want and any(strata[k] for k in keys):  # round-robin over strata
            for k in keys:
                if strata[k] and len(picked) < want:
                    picked.append(strata[k].pop(0))
        chosen += picked
    order = list(range(len(chosen)))
    rng.shuffle(order)
    pilot = set()
    for comp in QUOTA:  # the pilot: spread over competitions, no drawings
        for k in order:
            e = chosen[k]
            if len(pilot) < a.pilot and e["competition"] == comp and not e["figure"] and \
                    sum(chosen[j]["competition"] == comp for j in pilot) < max(1, round(QUOTA[comp] * a.pilot)):
                pilot.add(k)
    with (TRANSLATED / "working_set.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "pilot", "competition", "season", "grade", "figure", "also_appears_as", "title", "path"])
        for k, e in enumerate(chosen):
            w.writerow([e["id"], "yes" if k in pilot else "", e["competition"], e["season"], e["grade"],
                        "yes" if e["figure"] else "", " | ".join(e["also"]), e["title"], e["path"]])
    per = defaultdict(int)
    for e in chosen:
        per[e["competition"]] += 1
    print(f"duplicate groups: {len(dups)} ({sum(len(m) for m in dups.values())} files); "
          f"statable entries: {len(entries)}; clean: {len(clean)} "
          f"(left out: glued {sum(e['glued'] for e in entries)}, formula missing "
          f"{sum(e['formula_missing'] for e in entries)}, low confidence {sum(e['low_conf'] for e in entries)})")
    print(f"working set {len(chosen)}: {dict(per)}; with a drawing {sum(e['figure'] for e in chosen)}; "
          f"pilot {len(pilot)}")


if __name__ == "__main__":
    main()
