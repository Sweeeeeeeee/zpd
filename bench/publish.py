"""Build the results page and paper insert from recorded per-problem evidence.

Run from the repository root with python -m bench.publish.
"""
import csv
import json
from collections import Counter
from html import escape
from pathlib import Path
from statistics import median
from string import Template

from bench.eval_proposers import problems
from pipeline.hf_tool import normalize_preds
from zpd_darbs.scripts.make_figures import BENCH_MODELS, SETS, bench_records

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MODELS = {"mini": 200, "mini_long": 200, "mid": 200, "GenesisGeo": 50, "SmolLM2-360M-Instruct": 50}
SUITES = {"jgex_ag_231": "JGEX-AG-231", "imo": "IMO-AG-30", "imo_102_requires_aux": "IMO auxiliary set"}


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def construction(text):
    """Keep the point name, predicate multiplicity and each argument position."""
    point, sep, body = text.partition(":")
    predicates = normalize_preds(body)
    if sep and point.strip() and predicates:
        return point.strip(), tuple(sorted(p.strip() for p in predicates.split(",")))
    return None


def score(rows):
    strict = []
    relaxed = 0
    for row in rows:
        reference = construction(row["gold"])
        hits = [reference is not None and construction(beam) == reference for beam in row["beams"]]
        strict.append(hits)
        relaxed += any(row["exact"])
    return dict(n=len(rows), top1=sum(bool(h) and h[0] for h in strict),
                top4=sum(any(h) for h in strict), relaxed=relaxed,
                empty=sum(construction(r["gold"]) is None for r in rows),
                seconds=round(median(r["seconds"] for r in rows), 2))


def checked_rows(path, expected_names):
    rows = read_rows(path)
    if len(rows) != len(expected_names) or {row["name"] for row in rows} != expected_names:
        raise ValueError(f"Problem IDs differ in {path}")
    if any("crash" in (row["reason"] or "").lower() for row in rows):
        raise ValueError(f"Solver crash in {path}")
    return rows


def proof_counts(suite):
    archived = bench_records(suite, "ddar_only")
    original = {name for name, row in archived.items() if row["solved"]}
    original_union = original.copy()
    for config, _ in BENCH_MODELS:
        records = bench_records(suite, config)
        original_union.update(name for name, row in records.items() if name in archived and row["solved"])

    folder = RESULTS / "local-cpu" / suite
    rows = checked_rows(folder / "ddar_only.jsonl", set(archived))
    baseline = {row["name"] for row in rows if row["solved"]}
    counts = {
        "n": len(rows),
        "baseline": len(original),
        "current": len(baseline),
        "build_failures": sum((r["reason"] or "").startswith("problem could not be built") for r in rows),
        "union": len(original_union),
        "changed": sorted(baseline ^ original),
    }
    if suite == "imo_102_requires_aux":
        return counts

    failures = set(archived) - baseline
    if suite == "jgex_ag_231":
        failures = set((RESULTS / suite / "ddar_unsolved.txt").read_text().splitlines())
    union = baseline.copy()
    one_point = set()
    gains = {}
    for config, _ in BENCH_MODELS:
        followup = checked_rows(folder / f"{config}.jsonl", failures)
        winners = {row["name"] for row in followup if row["solved"]}
        gains[config] = len(winners - baseline)
        one_point.update(row["name"] for row in followup if row["solved"] and row["depth"] == 1)
        union.update(winners)
    counts.update(repeat_union=len(union), gains=gains, followup_cases=len(failures),
                  one_aux_gain=len(one_point - baseline), additional_proofs=sorted(union - baseline))
    return counts


def main():
    source = problems(200)
    references = [f"{point} : {gold}" for _, point, gold in source]
    with (ROOT / "data/genesisgeo/train.txt").open() as stream:
        train = {line.partition("<aux>")[0].strip() for line in stream}
    overlaps = sum(problem in train for problem, _, _ in source)
    common, full = {}, {}
    for name, n in MODELS.items():
        rows = read_rows(RESULTS / "proposers/local-cpu" / f"{name}.jsonl")
        if ([r["i"] for r in rows] != list(range(n)) or
                [r["gold"] for r in rows] != references[:n]):
            raise ValueError(f"Incomplete or inconsistent sample for {name}")
        common[name], full[name] = score(rows[:50]), score(rows)

    smoke_rows = read_rows(RESULTS / "proposers/local-cpu/ag1-smoke.jsonl")
    if [r["gold"] for r in smoke_rows] != references[:3] or [r["i"] for r in smoke_rows] != [0, 1, 2]:
        raise ValueError("Incomplete AlphaGeometry smoke sample")
    ag1 = score(smoke_rows)
    benchmarks = {suite: proof_counts(suite) for suite, _ in SETS}
    jgex = benchmarks["jgex_ag_231"]
    gains = jgex["gains"]
    with (ROOT / "problems/latvia/geometry_translated/status.csv").open() as f:
        translations = Counter(row["stage"] for row in csv.DictReader(f))
    result = dict(common50=common, full=full, proofs=benchmarks, ag1_smoke=ag1,
                  training_prompt_overlaps=overlaps, translations=translations)
    (RESULTS / "local-cpu/summary.json").write_text(json.dumps(result, indent=2) + "\n")

    def model_rows(scores):
        return "\n".join(f'<tr><th scope="row">{escape(name)}</th><td>{s["n"]}</td>'
                         f'<td>{s["top1"]}</td><td><strong>{s["top4"]}</strong></td>'
                         f'<td>{s["relaxed"]}</td><td>{s["seconds"]:.2f}</td></tr>'
                         for name, s in scores.items())
    proof_rows = "\n".join(f'<tr><th scope="row">{SUITES[k]}</th><td>{b["n"]}</td>'
                           f'<td>{b["baseline"]}</td><td>{b["current"]}</td><td>{b["union"]}</td><td>{b.get("repeat_union", "—")}</td></tr>'
                           for k, b in benchmarks.items())
    page = ROOT / "docs/results"
    page.mkdir(exist_ok=True)
    data = dict(proofs=proof_rows, common=model_rows(common),
                full=model_rows({k:v for k, v in full.items() if v["n"] == 200}),
                empty50=common["mid"]["empty"], empty200=full["mid"]["empty"], overlaps=overlaps,
                mid=full["mid"]["top4"], ag1=ag1["top4"], agseconds=ag1["seconds"], union=jgex["repeat_union"],
                heuristic=gains["heuristics_only"], longgain=gains["mini_long_model"],
                midgain=gains["mid_model"], failures=jgex["followup_cases"], onepoint=jgex["one_aux_gain"],
                extra=jgex["repeat_union"] - jgex["current"],
                accepted=translations["accepted"], rejected=translations["rejected"],
                review=translations["review"], candidates=sum(translations.values()))
    data["build_failures"] = sum(b["build_failures"] for b in benchmarks.values())
    data["changed"] = sum(len(b["changed"]) for b in benchmarks.values())
    template = Template((ROOT / "bench/results-template.html").read_text())
    (page / "index.html").write_text(template.substitute(data))
    imo = benchmarks["imo"]
    s = full["mid"]
    report = (
        r"Atkārtotajā CPU eksperimentā (Intel Core i7-1355U) vērtēti pirmie 200 validācijas piemēri "
        r"ar palīgpunktu. Stingrajā salīdzinājumā saglabāts jaunā punkta vārds un predikātu argumentu "
        r"secība; predikātu savstarpējā secība neietekmē rezultātu. "
        f"No 200 piemēriem {s['empty']} atsauces bija bez predikātiem; tās ieskaitītas kā nesakritības. "
        rf"Modelim \texttt{{mid}} pirmais piedāvājums sakrita {s['top1']} gadījumos, vismaz viens "
        f"no četriem -- {s['top4']} gadījumos. Iepriekš lietotais brīvākais kritērijs tajās pašās "
        f"prognozēs deva {s['relaxed']} sakritības no 200. "
        f"Pirmajos 50 piemēros stingrais četru piedāvājumu rādītājs bija {common['mid']['top4']}/50 "
        rf"modelim \texttt{{mid}}, {common['GenesisGeo']['top4']}/50 modelim GenesisGeo un "
        f"{common['SmolLM2-360M-Instruct']['top4']}/50 modelim SmolLM2-360M. "
        f"Atkārtotajā JGEX pārbaudē DD-AR atrisināja {jgex['current']} uzdevumus, bet kopā ar "
        f"atsevišķo palīgpunktu meklējumu rezultātiem pierādīti {jgex['repeat_union']} no {jgex['n']}. "
        f"IMO-AG-30 pieejamajā daļā ar dedukciju pierādīti {imo['current']}, bet pēc papildu "
        f"meklējumiem -- {imo['repeat_union']} no {imo['n']} uzdevumiem. "
        f"AlphaGeometry lokāli pabeidza trīs pārbaudes piemērus (stingrā sakritība četros piedāvājumos: "
        f"{ag1['top4']}/3); šī izlase ir par mazu modeļu salīdzināšanai. "
        "Katrā palīgpunkta prognozes uzdevumā bija dota viena etalonkonstrukcija; iespējami arī citi derīgi risinājumi.\n"
    )
    (ROOT / "zpd_darbs/tables/local_eval.tex").write_text(report)


if __name__ == "__main__":
    main()
