"""Download the NMS olympiad archive and build problems/latvia/.

    python -m bench.latvia fetch            # download every archive file into the cache (~240 MB)
    python -m bench.latvia build            # extract, split, tag and write problems/latvia/
    python -m bench.latvia report           # problems found per olympiad, and the odd ones

The cache (default ~/.cache/zpd-nms, or $NMS_CACHE) is not committed; the
problem tree it produces is. Needs pdftotext (poppler-utils) and, for .doc
files, LibreOffice (soffice).
"""

from __future__ import annotations

import csv
import html
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from bench.latvia.catalog import ARCHIVE_PAGES, COMPETITIONS, SITE, Instance, Source, classify, group
from bench.latvia.extract import file_text
from bench.latvia.split import Problem, merge, quality, split, split_tst
from bench.latvia.topics import geometry_kind

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "problems" / "latvia"
CACHE = Path(os.environ.get("NMS_CACHE", Path.home() / ".cache" / "zpd-nms"))
AGENT = "zpd-olympiad-archive/1.0 (research project; polite single-threaded download)"


def _local_name(url: str) -> str:
    path = urllib.parse.unquote(url.split("nms.lu.lv/", 1)[-1])
    for prefix, short in (("Arhivs/Olimpiades/", ""), ("Arhivs/IMO/", "INTL/"),
                          ("baltic_way_2013/BW_problems_solutions/", "INTL/")):
        if prefix in path:
            return short + path.split(prefix, 1)[1]
    return "OTHER/" + path.rsplit("/", 1)[-1]


def archive_urls() -> dict[str, str]:
    """Every file linked from the archive pages, with the school year it is listed under ("" if none)."""
    urls: dict[str, str] = {}
    for page in ARCHIVE_PAGES:
        req = urllib.request.Request(page, headers={"User-Agent": AGENT})
        text = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        season = ""
        for m in re.finditer(r'(\d{4})\./\s*(\d{4})\.|href="(/fileadmin/[^"]+)"', text):
            if m.group(1):
                season = f"{m.group(1)}/{m.group(2)[2:]}"
            else:
                urls.setdefault(SITE + html.unescape(m.group(3)), season if page == ARCHIVE_PAGES[0] else "")
    return dict(sorted(urls.items()))


def fetch() -> None:
    urls = archive_urls()
    (CACHE / "raw").mkdir(parents=True, exist_ok=True)
    (CACHE / "urls.txt").write_text("".join(f"{u}\t{s}\n" for u, s in urls.items()))
    for i, url in enumerate(urls, 1):
        target = CACHE / "raw" / _local_name(url)
        if target.exists() and target.stat().st_size:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(urllib.parse.quote(url, safe=":/%"), headers={"User-Agent": AGENT})
        try:
            target.write_bytes(urllib.request.urlopen(req, timeout=120).read())
        except Exception as e:  # keep going; report at the end
            print(f"failed {url}: {e}", file=sys.stderr)
        time.sleep(0.2)
        if i % 50 == 0:
            print(f"{i}/{len(urls)}")
    print(f"{len(urls)} files in {CACHE / 'raw'}")


def _text(source: Source) -> str:
    cached = CACHE / "text" / (source.file + ".txt")
    if cached.exists():
        return cached.read_text()
    text = file_text(CACHE / "raw" / source.file, docx_dir=CACHE / "docx" / Path(source.file).parent)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(text)
    return text


def sources() -> list[Source]:
    out = []
    for line in (CACHE / "urls.txt").read_text().splitlines():
        url, _, season = line.partition("\t")
        s = classify(_local_name(url), url, season or None)
        if s is not None and (CACHE / "raw" / s.file).exists():
            out.append(s)
    return out


def _read(inst: Instance) -> tuple[list[Problem], Source | None, float]:
    """Parse every problem-bearing source of an instance; keep the best reading.

    The reading with the most problems sets the problem list, and each
    statement is then taken from whichever file (.doc/.docx/.pdf) renders it best.
    """
    lv = any(o.lang == "lv" for o in inst.sources)
    scored = []
    for s in inst.sources:
        if s.role == "solutions" or (s.lang != "lv" and lv):
            continue
        if inst.competition == "tst":
            problems = split_tst(_text(s), combined=s.role == "combined")
        else:
            problems = split(_text(s), olympiad=inst.number, combined=s.role == "combined")
        scored.append((quality(problems) + (0.5 if s.role == "problems" else 0), len(problems), s, problems))
    if not scored:
        return [], None, 0.0
    # most problems first (a reading that misses a grade header loses problems), then readability
    scored.sort(key=lambda t: (-t[1], -t[0]))
    q, n, src, problems = scored[0]
    if q <= 0:
        return [], None, 0.0
    others = [t[3] for t in scored[1:] if t[2].role == src.role]
    return merge([problems] + others), src, q


def _slug(p: Problem, inst: Instance) -> str:
    parts = []
    if p.day == 9:
        parts.append("extra")
    elif p.day and (p.day > 1 or inst.competition == "tst"):
        parts.append(f"day{p.day}")
    if p.grade:
        parts.append("grade" + "-".join(f"{int(g):02d}" for g in p.grade.split("-")))
    return "/".join(parts + [f"p{p.number}"])


def _front_matter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if isinstance(v, list):
            v = "[" + ", ".join(v) + "]"
        elif v is None:
            v = ""
        elif isinstance(v, str) and k in ("problem", "grade", "season", "title"):
            v = '"' + v.replace('"', "'") + '"'   # keep "26.3" and "8-9" strings in YAML
        lines.append(f"{k}: {v}")
    return "\n".join(lines + ["---", ""])


def needs_review(text: str) -> list[str]:
    """Reasons a statement may not be complete: lost formulas or pictures, very short text, odd characters."""
    why = []
    if "[formula]" in text:
        why.append("formula missing")
    if "[attēls]" in text or re.search(r"\b(zīm|att)\.", text):
        why.append("has a figure")
    if len(text) < 60:
        why.append("very short")
    lines = [l for l in text.split("\n") if l.strip()]
    if lines and sum(len(l.strip()) <= 3 for l in lines) > max(3, len(lines) // 4):
        why.append("broken formula layout")
    return why


OVERRIDES = OUT / "geometry_overrides.csv"


def _overrides() -> dict[str, str]:
    """Hand corrections of the geometry tag: id,geometry (plane | solid | no) per line."""
    if not OVERRIDES.exists():
        return {}
    with open(OVERRIDES) as f:
        return {r["id"]: r["geometry"] for r in csv.DictReader(f) if r.get("id")}


def build() -> list[dict]:
    insts = group(sources())
    # Selection tests: per-day problem files beat the combined problems+solutions file, unless unreadable.
    readings: dict[int, tuple] = {id(i): _read(i) for i in insts}
    for i in insts:
        if i.competition == "tst" and "/" not in i.part:
            days = [d for d in insts if d.competition == "tst" and d.year == i.year and d.part.startswith(i.part + "/")]
            day_ok = [d for d in days if readings[id(d)][2] >= 2]
            if day_ok:
                readings[id(i)] = ([], None, 0.0)
                for d in day_ok:
                    d.sources.extend(s for s in i.sources if s.role != "problems")
            else:
                for d in days:
                    readings[id(d)] = ([], None, 0.0)
                    i.sources.extend(d.sources)

    for sub in ("all", "geometry"):
        shutil.rmtree(OUT / sub, ignore_errors=True)
    overrides = _overrides()
    rows = []
    for inst in insts:
        problems, src, _ = readings[id(inst)]
        if not problems:
            continue
        solutions = [s.url for s in inst.sources if s.role in ("solutions", "combined")]
        originals = [s.url for s in inst.sources if s.role in ("problems", "combined")]
        kind = inst.part.partition("/")[0] if inst.competition == "tst" else ""
        base = f"{inst.competition}/{inst.year}_{kind}" if kind else f"{inst.competition}/{inst.key}"
        for p in problems:
            rel = f"{base}/{_slug(p, inst)}"
            geo, keys = geometry_kind(p.text)
            if f"latvia/{rel}" in overrides:
                geo = {"no": ""}.get(overrides[f"latvia/{rel}"], overrides[f"latvia/{rel}"])
                keys = ["(set by hand)"]
            review = needs_review(p.text)
            day = "extra" if p.day == 9 else p.day or (2 if inst.part.endswith("day2") else None)
            title = COMPETITIONS[inst.competition]
            if inst.number:
                title = title.replace("Latvijas", f"Latvijas {inst.number}.", 1)
            if kind:
                title += f" — {'Baltijas ceļa' if kind == 'bw' else 'IMO'} atlase"
            meta = {
                "id": f"latvia/{rel}",
                "competition": inst.competition,
                "title": title,
                "olympiad": inst.number,
                "year": inst.year,
                "season": inst.season,
                "day": day,
                "grade": p.grade,
                "problem": p.label,
                "geometry": geo or "no",
                "geometry_keywords": keys[:8],
                "needs_review": review,
                "source": src.url,
                "originals": originals,
                "solutions": solutions,
            }
            body = _front_matter(meta) + "\n" + p.text.strip() + "\n"
            for sub in ("all",) + (("geometry",) if geo else ()):
                path = OUT / sub / (rel + ".md")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body)
            rows.append({"id": meta["id"], "path": f"all/{rel}.md", "competition": inst.competition,
                         "olympiad": inst.number or "", "year": inst.year, "season": inst.season,
                         "day": day or "", "grade": p.grade or "", "problem": p.label, "geometry": geo or "no",
                         "chars": len(p.text), "needs_review": "; ".join(review), "source": src.url})
    with open(OUT / "index.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def report(rows: list[dict] | None = None) -> None:
    if rows is None:
        with open(OUT / "index.csv") as f:
            rows = list(csv.DictReader(f))
    per = Counter((r["competition"], r["season"], r["olympiad"]) for r in rows)
    geo = Counter(r["geometry"] for r in rows)
    comp = Counter(r["competition"] for r in rows)
    print(f"{len(rows)} problems; geometry: plane {geo['plane']}, solid {geo['solid']}")
    for c, n in sorted(comp.items()):
        print(f"  {c:9s} {n:5d} problems in {sum(1 for k in per if k[0] == c)} olympiads")
    grades = Counter((r["competition"], r["season"], r["olympiad"], r["day"], r["grade"]) for r in rows)
    odd = [(k, n) for k, n in grades.items() if k[4] and not 3 <= n <= 7]
    for k, n in sorted(odd):
        print("  unusual count:", k, n)
    tiny = [r for r in rows if int(r["chars"]) < 40]
    for r in tiny:
        print("  very short:", r["id"])


def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "build"
    if cmd == "fetch":
        fetch()
    elif cmd == "build":
        report(build())
    elif cmd == "report":
        report()
    else:
        print(__doc__)

