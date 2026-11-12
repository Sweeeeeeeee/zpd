"""Attēli un tabulas ZPD darbam no repozitorijā saglabātajiem rezultātiem.

Ievade (viss no repozitorija, nekas netiek skaitīts no jauna):
  results/examples/*.json                         parauga uzdevumi visās konfigurācijās un jomās
  results/{jgex_ag_231,imo,imo_102_requires_aux}/ standarta kopas: DD-AR un modeļi
  results/transformer/*_train_log.jsonl           modeļu apmācības žurnāli
  results/transformer/eval_*_val200.json          modeļu piedāvājumu pārbaude

Izvade:
  zpd_darbs/figures/*.pdf   attēli (\\includegraphics)
  zpd_darbs/tables/*.tex    tabulu rindas (\\input tabulas ķermenī)

    .venv-newclid/bin/python zpd_darbs/scripts/make_figures.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results"
OUT = Path(__file__).resolve().parents[1]
FIG, TAB = OUT / "figures", OUT / "tables"

DOMAINS = ["full", "full_no_ar", "circles", "circles_no_ar", "no_similarity", "no_similarity_no_ar"]
PROBLEM_LV = {
    "orthocenter_reflection": "Ortocentra atspoguļojums",
    "right_triangle_median": "Taisnleņķa trijstūra mediāna",
    "tangent_chord": "Pieskares un hordas leņķis",
    "varignon": "Varinjona teorēma",
    "wrong_translation": "Nepareizs tulkojums",
}

# Vienots stils: Times, melns teksts, viena akcenta krāsa, bez lieka rāmja.
plt.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
    "font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#444444", "axes.grid": True, "grid.color": "#dddddd", "grid.linewidth": 0.6,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})
ACCENT, MUTED = "#1f4e79", "#9db4cc"


def lv(x: float, digits: int = 1) -> str:
    """Skaitlis ar komatu: 2.5 -> 2,5."""
    return f"{x:.{digits}f}".replace(".", ",")


def tex_escape(s: str) -> str:
    return s.replace("_", r"\_")


# ------------------------------------------------------------------ dati
def load_examples() -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {}
    for f in sorted((RES / "examples").glob("*.json")):
        d = json.loads(f.read_text())
        out[f.stem] = {r["config"]: r for r in d["records"]}
    return out


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


# ------------------------------------------------------------------ 1. jomas uz parauga uzdevumiem
def domains_table(ex: dict[str, dict[str, dict]]) -> None:
    rows, solved = [], {d: 0 for d in DOMAINS}
    for name, recs in ex.items():
        cells = []
        for d in DOMAINS:
            r = recs.get(d)
            if r is None:
                cells.append("--")
            elif r["solved"]:
                solved[d] += 1
                cells.append(r"\textbf{jā} " + lv(r["resources"]["used"]["wall_time_s"]) + r"~s")
            else:
                reason = (r.get("failure_reason") or "").lower()
                cells.append("nē (laiks)" if "time" in reason else "nē (zīm.)" if "built" in reason or "figure" in reason
                             else "nē (dziļ.)" if "depth" in reason or "exhaust" in reason or "no proposals" in reason
                             else "nē")
        rows.append(PROBLEM_LV.get(name, tex_escape(name)) + " & " + " & ".join(cells) + r" \\")
    rows.append(r"\midrule")
    rows.append(r"\textbf{Atrisināti} & " + " & ".join(f"{solved[d]}/{len(ex)}" for d in DOMAINS) + r" \\")
    (TAB / "domains_examples.tex").write_text("\n".join(rows) + "\n")

    fig, ax = plt.subplots(figsize=(5.6, 2.4))
    labels = ["full", "circles", "no_similarity"]
    x = range(len(labels))
    ar = [solved[d] for d in labels]
    no_ar = [solved[d + "_no_ar"] for d in labels]
    ax.bar([i - 0.18 for i in x], ar, 0.36, color=ACCENT, label="ar AR")
    ax.bar([i + 0.18 for i in x], no_ar, 0.36, color=MUTED, label="bez AR")
    ax.set_xticks(list(x), labels)
    ax.set_ylabel("Atrisināti uzdevumi")
    ax.set_ylim(0, len(ex))
    ax.grid(axis="x", visible=False)
    ax.legend(frameon=False, loc="upper right", ncols=2)
    fig.savefig(FIG / "domains_examples.pdf")
    plt.close(fig)


# ------------------------------------------------------------------ 2. standarta kopas
# Modeļi, ko darbs salīdzina: (nosaukums, apmācības žurnāls, novērtējums, apmācības laiks).
# Laiki no docs/rezultati.md (žurnālā nav sienas pulksteņa laika).
MODELS = [("mini", "mini_train_log.jsonl", "eval_mini_val200.json", "14 min"),
          ("mini_long", "mini_long_train_log.jsonl", "eval_mini_long_9000_val200.json", r"1,5~h"),
          ("mid", "mid_train_log.jsonl", "eval_mid_val200.json", r"3,4~h")]
BENCH_MODELS = [("mini_long", r"\texttt{mini\_long}"), ("mid", r"\texttt{mid}")]
# AlphaGeometry rezultāti no Trinh u.c. (2024) un oficiālā repozitorija README.
AG1 = {"jgex_ag_231": ("198", "228"), "imo": ("14", "25"), "imo_102_requires_aux": ("--", "--")}
# `imo` kopā 34 uzdevumi; šie 5 nav AG1 etalonā IMO-AG-30 (no tā trūkst 2000_p1).
NOT_IMO_AG_30 = {"1975_p3", "1983_p2", "1995_p1", "2024_p4", "2025_p2"}
SETS = [("jgex_ag_231", "JGEX-AG-231"), ("imo", "IMO-AG-30"), ("imo_102_requires_aux", "IMO, vajag palīgpunktu")]
SHORT = {"JGEX-AG-231": "JGEX", "IMO-AG-30": "IMO-AG-30", "IMO, vajag palīgpunktu": "IMO-aux"}


def short_name(n: str) -> str:
    """JGEX ceļš -> uzdevuma nosaukums kā rezultātos (L058-9, ye_aux_think, ...)."""
    base = n.rsplit("/", 1)[-1].removesuffix(".gex")
    m = re.search(r"(L\d+-\d+|E\d+-\d+|ye_aux_\w+|yL\d+-\d+|GDD_FULL_[\d-]+_\d+)$", base)
    return m.group(1) if m else base


def bench_records(s: str, cfg: str) -> dict[str, dict]:
    rs = {r["name"]: r for r in load_jsonl(RES / s / f"{cfg}.jsonl")}
    if s == "imo":
        rs = {n: r for n, r in rs.items() if n not in NOT_IMO_AG_30}
    return rs


def bench_table() -> None:
    rows, solved_by_model = [], []
    totals = {}
    for s, label in SETS:
        dd = bench_records(s, "ddar_only")
        n_dd = sum(r["solved"] for r in dd.values())
        cells = [str(len(dd)), str(n_dd)]
        best = n_dd
        for m, _ in BENCH_MODELS:
            mr = bench_records(s, f"{m}_model")
            extra = sum(r["solved"] for n, r in mr.items() if n in dd and not dd[n]["solved"])
            cells.append(f"+{extra}")
            best = max(best, n_dd + extra)
            for n, r in mr.items():
                if r["solved"] and n in dd and not dd[n]["solved"]:
                    solved_by_model.append((label, n, m, r))
        cells.append(rf"\textbf{{{best}}}")
        cells += list(AG1[s])
        rows.append(f"{label} & " + " & ".join(cells) + r" \\")
        totals[s] = (len(dd), n_dd, best)
    (TAB / "bench.tex").write_text("\n".join(rows) + "\n")

    # Uzdevumi, kuros DD-AR iestrēgst, bet modelis atrod risinājumu.
    by_problem: dict[tuple[str, str], dict[str, dict]] = {}
    for label, n, m, r in solved_by_model:
        by_problem.setdefault((label, n), {})[m] = r
    rows = []
    for (label, n), rs in by_problem.items():
        cells = []
        for m, _ in BENCH_MODELS:
            r = rs.get(m)
            cells.append(rf"\textbf{{jā}}, {len(r['aux'])} p., {lv(r['wall'])}~s" if r else "nē")
        rows.append(rf"{SHORT[label]} & \texttt{{{tex_escape(short_name(n))}}} & " + " & ".join(cells) + r" \\")
    (TAB / "bench_solved.tex").write_text("\n".join(rows) + "\n")
    one_aux = {m: sum(1 for rs in by_problem.values() if m in rs and len(rs[m]["aux"]) == 1) for m, _ in BENCH_MODELS}

    jg = bench_records("jgex_ag_231", "ddar_only")
    walls = sorted(r["wall"] for r in jg.values() if r["solved"])
    (TAB / "bench_meta.tex").write_text(
        rf"\newcommand{{\jgexTotal}}{{{totals['jgex_ag_231'][0]}}}" "\n"
        rf"\newcommand{{\jgexSolved}}{{{totals['jgex_ag_231'][1]}}}" "\n"
        rf"\newcommand{{\jgexBest}}{{{totals['jgex_ag_231'][2]}}}" "\n"
        rf"\newcommand{{\jgexMedian}}{{{lv(walls[len(walls) // 2])}}}" "\n"
        rf"\newcommand{{\imoSolved}}{{{totals['imo'][1]}}}" "\n"
        rf"\newcommand{{\imoBest}}{{{totals['imo'][2]}}}" "\n"
        rf"\newcommand{{\imoTotal}}{{{totals['imo'][0]}}}" "\n"
        rf"\newcommand{{\auxBest}}{{{totals['imo_102_requires_aux'][2]}}}" "\n"
        rf"\newcommand{{\auxTotal}}{{{totals['imo_102_requires_aux'][0]}}}" "\n"
        rf"\newcommand{{\stuckSolved}}{{{len(by_problem)}}}" "\n"
        rf"\newcommand{{\midOneAux}}{{{one_aux['mid']}}}" "\n")


# ------------------------------------------------------------------ 3. transformera apmācība
def training_figure() -> None:
    fig, ax = plt.subplots(figsize=(5.6, 2.6))
    colors = {"mini": MUTED, "mini_long": "#5a7fa6", "mid": ACCENT}
    rows, meta = [], {}
    for m, log_name, eval_name, hours in MODELS:
        log = load_jsonl(RES / "transformer" / log_name)
        ev = [e for e in log if e["event"] == "eval"]
        start = next(e for e in log if e["event"] == "start")
        ax.plot([e["step"] for e in ev], [e["val_loss"] for e in ev], "o-", color=colors[m], lw=1.4, ms=3.5,
                label=f"{m} ({lv(start['params'] / 1e6)} milj.)")
        d = json.loads((RES / "transformer" / eval_name).read_text())
        rows.append(rf"\texttt{{{tex_escape(m)}}} & {lv(start['params'] / 1e6)} & {ev[-1]['step']} & {hours} & "
                    rf"{lv(min(e['val_loss'] for e in ev), 3)} & {lv(100 * d['translatable_rate'])}\,\% & "
                    rf"{lv(100 * d['exact_at_1'])}\,\% & {lv(100 * d['exact_at_4'])}\,\% \\")
        meta = {"train": start["train"], "problems": d["problems"]}
    ax.set_xlabel("Apmācības solis (32 piemēri solī)")
    ax.set_ylabel("Validācijas zudums")
    ax.set_ylim(0, 1.3)
    ax.legend(frameon=False)
    fig.savefig(FIG / "training_loss.pdf")
    plt.close(fig)
    (TAB / "training_models.tex").write_text("\n".join(rows) + "\n")
    (TAB / "training_meta.tex").write_text(
        rf"\newcommand{{\trainExamples}}{{{meta['train']:,}}}".replace(",", r"\,") + "\n"
        rf"\newcommand{{\evalProblems}}{{{meta['problems']}}}" "\n")


def main() -> None:
    FIG.mkdir(exist_ok=True)
    TAB.mkdir(exist_ok=True)
    domains_table(load_examples())
    bench_table()
    training_figure()
    print("figures:", sorted(p.name for p in FIG.iterdir()))
    print("tables: ", sorted(p.name for p in TAB.iterdir()))


if __name__ == "__main__":
    main()
