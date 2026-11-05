"""Attēli un tabulas ZPD darbam no repozitorijā saglabātajiem rezultātiem.

Ievade (viss no repozitorija, nekas netiek skaitīts no jauna):
  results/examples/*.json                     parauga uzdevumi visās konfigurācijās un jomās
  results/jgex_ag_231/*.jsonl                 JGEX uzdevumi: DD-AR, heiristikas, modeļi
  results/transformer/mini_train_log.jsonl    transformera apmācības žurnāls
  results/transformer/eval_mini_val200.json   modeļa piedāvājumu pārbaude

Izvade:
  zpd_darbs/figures/*.pdf   attēli (\\includegraphics)
  zpd_darbs/tables/*.tex    tabulu rindas (\\input tabulas ķermenī)

    .venv-newclid/bin/python zpd_darbs/scripts/make_figures.py
"""

from __future__ import annotations

import json
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


# ------------------------------------------------------------------ 2. JGEX: kur DD-AR iestrēgst
def jgex_table() -> None:
    cfgs = [("ddar_only", "Tikai DD-AR"), ("heuristics_only", "Heiristikas"),
            ("quick_model", "Modelis, 200 soļi"), ("mini_model", "Modelis, 1600 soļi")]
    data = {c: {r["name"]: r for r in load_jsonl(RES / "jgex_ag_231" / f"{c}.jsonl")} for c, _ in cfgs}
    stuck = [n for n, r in data["ddar_only"].items() if not r["solved"]]
    rows = []
    for name in stuck:
        short = name.rsplit("_", 1)[-1].removesuffix(".gex")
        cells = []
        for c, _ in cfgs:
            r = data[c].get(name)
            if r is None:
                cells.append("--")
            elif r["solved"]:
                n_aux = len(r["aux"])
                cells.append(rf"\textbf{{jā}}, {n_aux} p., {lv(r['wall'])}~s")
            else:
                cells.append("nē")
        rows.append(rf"\texttt{{{short}}} & " + " & ".join(cells) + r" \\")
    (TAB / "jgex_stuck.tex").write_text("\n".join(rows) + "\n")

    dd = list(data["ddar_only"].values())
    s = [r for r in dd if r["solved"]]
    walls = sorted(r["wall"] for r in s)
    summary = {"total": len(dd), "solved": len(s), "median_wall": walls[len(walls) // 2] if walls else 0}
    (TAB / "jgex_ddar_summary.tex").write_text(
        rf"\newcommand{{\jgexTotal}}{{{summary['total']}}}" "\n"
        rf"\newcommand{{\jgexSolved}}{{{summary['solved']}}}" "\n"
        rf"\newcommand{{\jgexMedian}}{{{lv(summary['median_wall'])}}}" "\n")


# ------------------------------------------------------------------ 3. transformera apmācība
def training_figure() -> None:
    log = load_jsonl(RES / "transformer" / "mini_train_log.jsonl")
    train = [e for e in log if e["event"] == "train"]
    ev = [e for e in log if e["event"] == "eval"]
    fig, ax = plt.subplots(figsize=(5.6, 2.6))
    ax.plot([e["step"] for e in train], [e["loss_avg"] for e in train], color=ACCENT, lw=1.6, label="apmācības zudums")
    ax.plot([e["step"] for e in ev], [e["val_loss"] for e in ev], "o--", color="#c0504d", lw=1.2, ms=4,
            label="validācijas zudums")
    ax.set_xlabel("Apmācības solis (32 piemēri solī)")
    ax.set_ylabel("Zudums")
    ax.set_ylim(0, 3.5)
    ax.legend(frameon=False)
    fig.savefig(FIG / "training_loss.pdf")
    plt.close(fig)
    rows = [rf"{e['step']} & {lv(e['val_loss'], 2)} & {round(100 * e['exact_match'])}\,\% \\" for e in ev]
    (TAB / "training_eval.tex").write_text("\n".join(rows) + "\n")
    start = next(e for e in log if e["event"] == "start")
    (TAB / "training_meta.tex").write_text(
        rf"\newcommand{{\modelParams}}{{{lv(start['params'] / 1e6)}}}" "\n"
        rf"\newcommand{{\trainExamples}}{{{start['train']:,}}}".replace(",", r"\,") + "\n"
        rf"\newcommand{{\trainSteps}}{{{train[-1]['step']}}}" "\n"
        rf"\newcommand{{\bestValLoss}}{{{lv(min(e['val_loss'] for e in ev), 2)}}}" "\n")


# ------------------------------------------------------------------ 4. piedāvājumu pārbaude
def proposals_figure() -> None:
    p = RES / "transformer" / "eval_mini_val200.json"
    if not p.exists():
        return
    d = json.loads(p.read_text())
    k = d["beam"]
    items = [("Pabeigtas hipotēzes", d["finished_rate"]),
             ("Pārvēršamas Newclid konstrukcijās", d["translatable_rate"]),
             ("Uzdevumi ar derīgu piedāvājumu", d["problems_with_translatable"]),
             (f"Precīza sakritība, {k} piedāvājumi", d[f"exact_at_{k}"]),
             ("Precīza sakritība, 1. piedāvājums", d["exact_at_1"])]
    fig, ax = plt.subplots(figsize=(5.6, 2.3))
    names = [n for n, _ in items][::-1]
    vals = [100 * v for _, v in items][::-1]
    bars = ax.barh(names, vals, color=[MUTED, MUTED, ACCENT, ACCENT, ACCENT])
    for b, v in zip(bars, vals):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.0f} %".replace(".", ","), va="center", fontsize=9)
    ax.set_xlim(0, 110)
    ax.set_xlabel(f"% no {d['problems']} uzdevumiem / {d['hypotheses']} hipotēzēm")
    ax.grid(axis="y", visible=False)
    fig.savefig(FIG / "proposals.pdf")
    plt.close(fig)
    (TAB / "proposals_meta.tex").write_text(
        rf"\newcommand{{\evalProblems}}{{{d['problems']}}}" "\n"
        rf"\newcommand{{\evalTranslatable}}{{{lv(100 * d['translatable_rate'])}}}" "\n"
        rf"\newcommand{{\evalExactOne}}{{{round(100 * d['exact_at_1'])}}}" "\n"
        rf"\newcommand{{\evalExactK}}{{{round(100 * d[f'exact_at_{k}'])}}}" "\n")


def main() -> None:
    FIG.mkdir(exist_ok=True)
    TAB.mkdir(exist_ok=True)
    domains_table(load_examples())
    jgex_table()
    training_figure()
    proposals_figure()
    print("figures:", sorted(p.name for p in FIG.iterdir()))
    print("tables: ", sorted(p.name for p in TAB.iterdir()))


if __name__ == "__main__":
    main()
