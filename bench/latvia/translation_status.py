"""Checks, solver runs and the tracking table for the Latvian translations (task 7.5).

Layout (all under problems/latvia/geometry_translated/):
    _work/A/<rel>.txt, _work/B/<rel>.txt   the two independent translations
    _work/C/<rel>.<V>.txt                  back-translation of version V (agent C)
    _work/D/<rel>.<V>.txt                  first line `same` or `different: ...` (agent D)
    _work/checks/<rel>.<V>.json            check_figure + dof result (cached by file hash)
    _work/solve/<rel>.<V>.json             solver result in the full domain (cached by hash)
    status.csv                             one row per working-set problem
    <rel>.txt                              the accepted translation (version A)

    python -m bench.latvia.translation_status checks   # run check_figure and dof where stale
    python -m bench.latvia.translation_status solve    # full domain, 60 s, where stale
    python -m bench.latvia.translation_status status   # write status.csv, copy accepted ones

<rel> is the problem's path under problems/latvia/geometry/ without .md.
Accepted automatically: both versions translated, both pass both checks, D says
`same` for both, and the solver gives the same solved/unsolved result for both.
Everything else is flagged with the reasons; a decision in decisions.csv
(id, reviewer, decision = `accept A` / `accept B` / `reject: ...` / `fix: ...`, reason)
overrides the automatic one.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GT = ROOT / "problems/latvia/geometry_translated"
WORK = GT / "_work"
PY = sys.executable
VERSIONS = ("A", "B")
DEFAULT_CONFIG = "pipeline/configs/domains/full.json"


def working_set() -> list[dict]:
    with open(GT / "working_set.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["rel"] = str(Path(r["path"]).relative_to("problems/latvia/geometry").with_suffix(""))
    return rows


def problem_line(path: Path) -> str | None:
    lines = [ln.strip() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    return lines[0] if len(lines) == 1 else None


def untranslatable(path: Path) -> str | None:
    for ln in path.read_text().splitlines():
        if ln.lower().startswith("# untranslatable"):
            return ln.split(":", 1)[-1].strip()
    return None


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def cached(out: Path, h: str) -> dict | None:
    if out.exists():
        d = json.loads(out.read_text())
        if d.get("hash") == h:
            return d
    return None


def cached_solve(out: Path, source_hash: str, config: str, time_s: float) -> dict | None:
    result = cached(out, source_hash)
    if result and result.get("config") == config and result.get("time_s") == time_s:
        if isinstance(result.get("solved"), bool) and "crash" not in str(result.get("failure")).lower():
            return result
    return None


def versions(rel: str):
    for v in VERSIONS:
        p = WORK / v / f"{rel}.txt"
        if p.exists():
            yield v, p


def run_checks(rows: list[dict]) -> None:
    for r in rows:
        for v, p in versions(r["rel"]):
            out = WORK / "checks" / f"{r['rel']}.{v}.json"
            h = digest(p)
            if cached(out, h) or problem_line(p) is None:
                continue
            fig = subprocess.run([PY, "-m", "pipeline.check_figure", "-f", str(p), "--seeds", "6"],
                                 cwd=ROOT, capture_output=True, text=True, timeout=600)
            dof = subprocess.run([PY, "-m", "pipeline.dof", str(p)], cwd=ROOT, capture_output=True, text=True)
            last = (fig.stdout.strip().splitlines() or ["CHECK no output " + fig.stderr[-200:]])[-1]
            d = {"hash": h, "figure_ok": last.startswith("OK"), "figure": last,
                 "dof_ok": dof.returncode == 0 and dof.stdout.startswith("OK"), "dof": dof.stdout.strip()}
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(d, indent=1))
            print(f"{r['rel']} {v}: figure {'ok' if d['figure_ok'] else 'FAIL'}, dof {'ok' if d['dof_ok'] else 'FAIL'}", flush=True)


def run_solve(rows: list[dict], config: str, time_s: float) -> None:
    from pipeline.solve import Budget, solve

    for r in rows:
        for v, p in versions(r["rel"]):
            out = WORK / "solve" / f"{r['rel']}.{v}.json"
            h = digest(p)
            problem = problem_line(p)
            if cached_solve(out, h, config, time_s) or problem is None:
                continue
            try:
                res = solve(problem, config, Budget(time_s=time_s, memory_mb=2048))
                d = {"solved": res.solved, "wall_time": round(res.wall_time, 1), "depth": res.depth,
                     "failure": getattr(res, "failure_reason", None)}
            except Exception as e:  # noqa: BLE001 - record and go on
                d = {"solved": None, "error": repr(e)[:300]}
            d.update(hash=h, config=config, time_s=time_s)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(d, indent=1))
            print(f"{r['rel']} {v}: solved={d['solved']} {d.get('wall_time', '')}", flush=True)


def verdict(rel: str, v: str) -> str:
    p = WORK / "D" / f"{rel}.{v}.txt"
    return p.read_text().strip().splitlines()[0].strip() if p.exists() and p.read_text().strip() else ""


def write_status(rows: list[dict], config: str = DEFAULT_CONFIG, time_s: float = 60,
                 *, partial: bool = False) -> None:
    out = GT / "status.csv"
    old = {}
    if out.exists():
        with open(out, newline="") as f:
            old = {r["id"]: r for r in csv.DictReader(f)}
    # decisions.csv (id, reviewer, decision, reason): settled disagreements and the user's
    # review; the last row for an id wins and overrides the automatic result
    dec = {}
    if (GT / "decisions.csv").exists():
        with open(GT / "decisions.csv", newline="") as f:
            dec = {r["id"]: r for r in csv.DictReader(f)}
    fields = ["id", "pilot", "stage", "auto", "flags", "dof_A", "dof_B", "solved_A", "solved_B",
              "D_A", "D_B", "reviewer", "decision"]
    table = []
    for r in rows:
        rel, row = r["rel"], {"id": r["id"], "pilot": r["pilot"]}
        flags, have = [], dict(versions(rel))
        for v in VERSIONS:
            p = have.get(v)
            if p is None:
                flags.append(f"{v} missing")
                continue
            if (why := untranslatable(p)) is not None:
                flags.append(f"{v} untranslatable: {why}")
                continue
            c = cached(WORK / "checks" / f"{rel}.{v}.json", digest(p)) or {}
            s = cached_solve(WORK / "solve" / f"{rel}.{v}.json", digest(p), config, time_s) or {}
            row[f"dof_{v}"] = c.get("dof", "").split(": ", 1)[-1]
            row[f"solved_{v}"] = s.get("solved", "")
            row[f"D_{v}"] = verdict(rel, v)
            if not c:
                flags.append(f"{v} not checked")
            elif not (c["figure_ok"] and c["dof_ok"]):
                flags.append(f"{v} check failed")
            if not s:
                flags.append(f"{v} not solved yet")
            if not row[f"D_{v}"]:
                flags.append(f"{v} no back-translation")
            elif not row[f"D_{v}"].lower().startswith("same"):
                flags.append(f"{v} back-translation differs")
        if not flags and row["solved_A"] != row["solved_B"]:
            flags.append("solver results differ")
        row["auto"] = "accept" if not flags else "review"
        row["flags"] = "; ".join(flags)
        prev = old.get(r["id"], {})
        d = dec.get(r["id"], prev)
        row["reviewer"], row["decision"] = d.get("reviewer", ""), d.get("decision", "")
        decision = row["decision"].strip().lower()
        if decision.startswith("accept") or (not decision and row["auto"] == "accept"):
            v = "B" if decision == "accept b" else "A"
            if v in have:
                (GT / f"{rel}.txt").parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(have[v], GT / f"{rel}.txt")
            row["stage"] = "accepted"
        elif decision.startswith("reject"):
            row["stage"] = "rejected"
        elif not have:
            row["stage"] = "to translate"
        else:
            row["stage"] = "review" if row["auto"] == "review" else "accepted"
        table.append(row)
    if partial:
        old.update((r["id"], r) for r in table)
        table = list(old.values())
    with tempfile.NamedTemporaryFile("w", dir=out.parent, newline="", delete=False) as f:
        temp_path = Path(f.name)
        try:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(table)
            f.flush()
            if out.exists():
                temp_path.chmod(stat.S_IMODE(out.stat().st_mode))
            temp_path.replace(out)
        finally:
            temp_path.unlink(missing_ok=True)
    n = {}
    for row in table:
        n[row["stage"]] = n.get(row["stage"], 0) + 1
    print(f"{out.relative_to(ROOT)}: " + ", ".join(f"{k} {v}" for k, v in sorted(n.items())))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", choices=["checks", "solve", "status"])
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--time", type=float, default=60.0)
    ap.add_argument("--only", help="ids containing this text")
    ap.add_argument("--shard", default="0/1", help="i/n: only every n-th problem, starting at i (parallel workers)")
    a = ap.parse_args()
    rows = [r for r in working_set() if not a.only or a.only in r["id"]]
    i, n = map(int, a.shard.split("/"))
    if a.what != "status":
        rows = rows[i::n]
    if a.what == "checks":
        run_checks(rows)
    elif a.what == "solve":
        run_solve(rows, a.config, a.time)
    else:
        partial = bool(a.only)
        if partial and not (GT / "status.csv").exists():
            rows = working_set()
        write_status(rows, a.config, a.time, partial=partial)


if __name__ == "__main__":
    main()
