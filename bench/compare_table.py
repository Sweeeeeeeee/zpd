"""Summarise results/compare/ into one Markdown table (docs/models.md).

Per domain and proposer: problems solved with one auxiliary point among the
DDAR failures, median solve time (after loading), median load time, peak memory.
Rows whose problems crashed or never loaded the model are flagged.

    python bench/compare_table.py            # prints, and writes results/compare/table.md
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
RES = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results/compare"


def rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def med(xs: list[float]) -> str:
    return f"{statistics.median(xs):.1f}" if xs else "–"


def main() -> None:
    lines = ["| Domain | Proposer | Solved / DDAR failures | Median solve s | Median load s | Peak MB | Note |",
             "| --- | --- | --- | --- | --- | --- | --- |"]
    for d in sorted(p for p in RES.iterdir() if p.is_dir()):
        ddar = rows(d / "ddar.jsonl") if (d / "ddar.jsonl").exists() else []
        fails = (d / "ddar_unsolved.txt").read_text().split() if (d / "ddar_unsolved.txt").exists() else []
        solved = sum(r["solved"] for r in ddar)
        lines.append(f"| {d.name} | DDAR alone | {solved} / {len(ddar)} (all) | "
                     f"{med([r['wall'] - r.get('load', 0) for r in ddar])} | {med([r.get('load', 0) for r in ddar])} | "
                     f"{max((r['mem'] for r in ddar), default=0):.0f} | |")
        for f in sorted(d.glob("*.jsonl")):
            if f.stem == "ddar":
                continue
            rs = rows(f)
            ok = [r for r in rs if r["solved"]]
            crashed = sum(1 for r in rs if (r.get("reason") or "").startswith(("crashed", "load limit")))
            idle = sum(1 for r in rs if "no proposer tools" in (r.get("reason") or ""))
            note = "; ".join(x for x in (f"{crashed} crashed" if crashed else "", f"{idle} without model" if idle else "",
                                         f"{len(rs)} of {len(fails)} run" if len(rs) < len(fails) else "") if x)
            lines.append(f"| {d.name} | {f.stem} | **{len(ok)}** / {len(fails)} | "
                         f"{med([r['wall'] - r.get('load', 0) for r in rs])} | {med([r.get('load', 0) for r in rs])} | "
                         f"{max((r['mem'] for r in rs), default=0):.0f} | {note} |")
    table = "\n".join(lines) + "\n"
    print(table)
    (RES / "table.md").write_text(table)


if __name__ == "__main__":
    main()
