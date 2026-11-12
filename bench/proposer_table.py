"""Tables of the proposer evaluation and comparison, from what is stored.

  results/proposers/val200/<model>.jsonl   bench/eval_proposers.py rows (held-out problems)
  results/compare/<domain>/<proposer>.jsonl bench/run_compare.sh (one aux point, 60 s)

Works on partial runs: each model is summarised over the problems it finished,
with a 95% Wilson interval, so small samples show their uncertainty.

    python bench/proposer_table.py        # Markdown, also written to results/proposers/table.md
"""

from __future__ import annotations

import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "results/proposers/val200"
CMP = ROOT / "results/compare"

# (file stem, display name, size, kind)
MODELS = [
    ("mini", "mini", "2,1M", "mūsu"),
    ("mini_long", "mini_long", "2,1M", "mūsu"),
    ("mid", "mid", "5,1M", "mūsu"),
    ("smollm2_135m", "SmolLM2-135M", "135M", "vispārīgs, few-shot"),
    ("smollm2_360m", "SmolLM2-360M", "360M", "vispārīgs, few-shot"),
    ("qwen3_0_6b_base", "Qwen3-0.6B-Base", "0,6B", "vispārīgs, few-shot"),
    ("qwen25_1_5b", "Qwen2.5-1.5B", "1,5B", "vispārīgs, few-shot"),
    ("genesisgeo", "GenesisGeo", "0,6B", "ģeometrijas, gatavs"),
    ("ag1", "AlphaGeometry", "152M", "ģeometrijas, gatavs"),
]


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def wilson(k: int, n: int) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def val_summaries() -> list[dict]:
    out = []
    for stem, name, size, kind in MODELS:
        rows = load(VAL / f"{stem}.jsonl")
        skipped = (VAL / f"{stem}.skipped").read_text().strip() if (VAL / f"{stem}.skipped").exists() else None
        n = len(rows)
        if not n:
            out.append({"stem": stem, "name": name, "size": size, "kind": kind, "n": 0, "skipped": skipped})
            continue
        beams = sum(len(r["beams"]) for r in rows)
        e1 = sum(bool(r["exact"]) and r["exact"][0] for r in rows)
        e4 = sum(any(r["exact"]) for r in rows)
        out.append({
            "stem": stem, "name": name, "size": size, "kind": kind, "n": n, "skipped": skipped,
            "translatable": sum(sum(r["translatable"]) for r in rows) / max(beams, 1),
            "exact1": e1 / n, "exact4": e4 / n, "exact4_ci": wilson(e4, n),
            "sec": statistics.median(r["seconds"] for r in rows),
            "load": rows[-1].get("load_s"),
        })
    return out


def compare_summaries() -> list[dict]:
    out = []
    for d in sorted(p for p in CMP.iterdir() if p.is_dir()) if CMP.exists() else []:
        dd = load(d / "ddar.jsonl")
        if not dd:
            continue
        fails = {r["name"] for r in dd if not r["solved"]}
        out.append({"domain": d.name, "proposer": "ddar", "n": len(dd), "solved": sum(r["solved"] for r in dd),
                    "sec": statistics.median([r["wall"] for r in dd]), "timeouts": sum("time" in (r.get("reason") or "") for r in dd)})
        for f in sorted(d.glob("*.jsonl")):
            if f.stem in ("ddar", "ag1_trial"):
                continue
            rs = [r for r in load(f) if r["name"] in fails]
            if not rs:
                continue
            out.append({"domain": d.name, "proposer": f.stem, "n": len(rs), "of": len(fails),
                        "solved": sum(r["solved"] for r in rs),
                        "sec": statistics.median(r["wall"] for r in rs),
                        "load": statistics.median(r.get("load", 0) or 0 for r in rs),
                        "mem": max(r.get("mem", 0) or 0 for r in rs),
                        "timeouts": sum("time" in (r.get("reason") or "") for r in rs)})
    return out


def pct(x: float) -> str:
    return f"{100 * x:.1f}%".replace(".0%", "%")


def markdown() -> str:
    L = ["### Held-out problems (GenesisGeo val, first auxiliary point, beam 4)", "",
         "| Model | Size | Kind | Problems | Translatable beams | Exact@1 | Exact@4 (95% CI) | s / problem | Load s |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in val_summaries():
        if not s["n"]:
            L.append(f"| {s['name']} | {s['size']} | {s['kind']} | 0 | – | – | – | – | {s['skipped'] or 'not run'} |")
            continue
        lo, hi = s["exact4_ci"]
        L.append(f"| {s['name']} | {s['size']} | {s['kind']} | {s['n']} | {pct(s['translatable'])} | {pct(s['exact1'])} | "
                 f"{pct(s['exact4'])} ({pct(lo)}–{pct(hi)}) | {s['sec']:.1f} | {s['load'] or 0:.0f} |")
    L += ["", "### Comparison (DDAR failures per domain, one auxiliary point, 60 s after loading)", "",
          "| Domain | Proposer | Solved | Of | Median s | Median load s | Peak MB | Timeouts |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for c in compare_summaries():
        if c["proposer"] == "ddar":
            L.append(f"| {c['domain']} | DDAR alone | {c['solved']} | {c['n']} | {c['sec']:.1f} | – | – | {c['timeouts']} |")
        else:
            part = "" if c["n"] == c["of"] else f" (run on {c['n']})"
            L.append(f"| {c['domain']} | {c['proposer']} | {c['solved']} | {c['of']}{part} | {c['sec']:.1f} | "
                     f"{c['load']:.1f} | {c['mem']:.0f} | {c['timeouts']} |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    md = markdown()
    (ROOT / "results/proposers").mkdir(parents=True, exist_ok=True)
    (ROOT / "results/proposers/table.md").write_text(md)
    print(md)
