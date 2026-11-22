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
from bench import imo_student_scores
from bench.latvia.case_table import problem_labels, render_cases
from bench.latvia import policy_comparison, proof_catalog, restricted_deduction, student_scores
from bench.latvia.fresh_drawings import frozen_hashes, summarize as summarize_fresh_drawings
from bench.latvia.segment_study import NAME as SEGMENT_CASE, summarize as summarize_segment
from bench.latvia.sample_audit import summarize as summarize_drawings
from bench.latvia.paired_results import budget_followup
from bench.latvia.paired_results import analyze as analyze_paired_ar
from bench.latvia.domain_results import complete_coverage, full_domain_results
from pipeline.hf_tool import normalize_preds
from zpd_darbs.scripts.make_figures import BENCH_MODELS, SETS, bench_records

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
MODELS = {"mini": 200, "mini_long": 200, "mid": 200, "small-6300": 200, "small-final": 200, "GenesisGeo": 50, "SmolLM2-360M-Instruct": 50}
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


def strict_hits(row):
    reference = construction(row["gold"])
    return [reference is not None and construction(beam) == reference for beam in row["beams"]]


def score(rows):
    strict = [strict_hits(row) for row in rows]
    relaxed = sum(any(row["exact"]) for row in rows)
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


def check_replays(path, winners):
    proofs = read_rows(path)
    if (len(proofs) != len(winners) or {r["name"] for r in proofs} != winners
            or any(not r["proof"] for r in proofs)):
        raise ValueError(f"Missing or duplicate proof replay in {path}")


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
    # Historical logs used the same prefix for builder and Yuclid exceptions.
    errors = [row["reason"] or "" for row in rows]
    legacy_engine = "problem could not be built: YuclidError:"
    counts = {
        "n": len(rows),
        "baseline": len(original),
        "current": len(baseline),
        "build_failures": sum(r.startswith("problem could not be built") and not r.startswith(legacy_engine) for r in errors),
        "engine_errors": sum(r.startswith((legacy_engine, "deduction engine failed:")) for r in errors),
        "union": len(original_union),
        "changed": sorted(baseline ^ original),
    }
    failures = set(archived) - baseline
    if suite == "jgex_ag_231":
        failures = set((RESULTS / suite / "ddar_unsolved.txt").read_text().splitlines())
    union = baseline.copy()
    one_point = set()
    gains = {}
    model_winners = set()
    for config, _ in BENCH_MODELS:
        followup = checked_rows(folder / f"{config}.jsonl", failures)
        winners = {row["name"] for row in followup if row["solved"]}
        if suite == "imo_102_requires_aux":
            check_replays(folder / f"{config}_proofs.jsonl", winners)
        if config in ("mini_long_model", "mid_model"):
            model_winners.update(winners)
        gains[config] = len(winners - baseline)
        one_point.update(row["name"] for row in followup if row["solved"] and row["depth"] == 1)
        union.update(winners)
    counts.update(repeat_union=len(union), gains=gains, followup_cases=len(failures),
                  one_aux_gain=len(one_point - baseline), additional_proofs=sorted(union - baseline))
    if suite == "imo_102_requires_aux":
        counts["local_two_model_union"] = len(baseline | model_winners)
        counts["unique_heuristic_gains"] = sorted(union - baseline - model_winners)
        counts["model_union_changed_ids"] = sorted((baseline | model_winners) ^ original_union)
    else:
        paired_interim_winners = set()
        for name in ("small_6300", "small_paired_interim", "small_final"):
            records = checked_rows(folder / f"{name}_model.jsonl", failures)
            winners = {row["name"] for row in records if row["solved"]}
            check_replays(folder / f"{name}_proofs.jsonl", winners)
            counts[name] = {
                "tested": len(records), "proved": len(winners),
                "new_problems": sorted(winners - union), "combined_union": len(union | winners),
            }
            if name == "small_paired_interim":
                paired_interim_winners = winners
            elif name == "small_final":
                counts["paired_checkpoint_proofs"] = {
                    "both": sorted(winners & paired_interim_winners),
                    "interim_only": sorted(paired_interim_winners - winners),
                    "final_only": sorted(winners - paired_interim_winners),
                }
            union.update(winners)
    return counts


def main():
    source = problems(200)
    references = [f"{point} : {gold}" for _, point, gold in source]
    with (ROOT / "data/genesisgeo/train.txt").open() as stream:
        train = {line.partition("<aux>")[0].strip() for line in stream}
    overlaps = sum(problem in train for problem, _, _ in source)
    training_setups = {prompt.partition("?")[0].strip() for prompt in train}
    with (ROOT / "data/genesisgeo/val.txt").open() as stream:
        val_setups = [line.partition("<aux>")[0].partition("?")[0].strip() for line in stream if line.strip()]
    split_audit = {"validation_rows": len(val_setups),
                   "setup_overlaps": sum(setup in training_setups for setup in val_setups)}
    common, full, matched = {}, {}, {}
    for name, n in MODELS.items():
        rows = read_rows(RESULTS / "proposers/local-cpu" / f"{name}.jsonl")
        if ([r["i"] for r in rows] != list(range(n)) or
                [r["gold"] for r in rows] != references[:n]):
            raise ValueError(f"Incomplete or inconsistent sample for {name}")
        common[name], full[name] = score(rows[:50]), score(rows)
        matched[name] = {row["i"] for row in rows if any(strict_hits(row))}

    mid_hits, long_hits = matched["mid"], matched["mini_long"]
    paired = dict(both=len(mid_hits & long_hits), mid_only=len(mid_hits - long_hits),
                  mini_long_only=len(long_hits - mid_hits),
                  neither=len(source) - len(mid_hits | long_hits))

    early, final = matched["small-6300"], matched["small-final"]
    paired_checkpoints = dict(both=len(early & final), interim_only=len(early - final),
                              final_only=len(final - early), neither=len(source) - len(early | final))

    smoke_rows = read_rows(RESULTS / "proposers/local-cpu/ag1-smoke.jsonl")
    if [r["gold"] for r in smoke_rows] != references[:3] or [r["i"] for r in smoke_rows] != [0, 1, 2]:
        raise ValueError("Incomplete AlphaGeometry smoke sample")
    ag1 = score(smoke_rows)
    benchmarks = {suite: proof_counts(suite) for suite, _ in SETS}
    jgex = benchmarks["jgex_ag_231"]
    gains = jgex["gains"]
    aux = benchmarks["imo_102_requires_aux"]
    run = json.loads((RESULTS / "local-cpu/small-final.json").read_text())
    if any(run[key] != full["small-final"][key] for key in ("n", "top1", "top4")):
        raise ValueError("Final prediction counts disagree with the frozen evaluation")
    with (ROOT / "problems/latvia/geometry_translated/status.csv").open() as f:
        corpus = list(csv.DictReader(f))
    translations = Counter(row["stage"] for row in corpus)
    accepted_by_decision = sum(r["stage"] == "accepted" and bool(r["decision"].strip()) for r in corpus)
    accepted_automatically = translations["accepted"] - accepted_by_decision
    latvia = full_domain_results(RESULTS / "latvia-domains")
    pair_folder = RESULTS / "latvia-domains/paired-ar"
    ar_study, checked_steps = analyze_paired_ar(pair_folder)
    if ar_study != json.loads((pair_folder / "summary.json").read_text()) or checked_steps != [
        json.loads(line) for line in (pair_folder / "ar-steps.jsonl").read_text().splitlines()
    ]:
        raise ValueError("Published AR evidence differs from the independently recomputed step audit")
    extra_budget = budget_followup(pair_folder)
    drawings = summarize_drawings(json.loads((RESULTS / "latvia-audit/drawings.json").read_text()))
    fresh_evidence = json.loads((RESULTS / "latvia-audit/fresh-drawings.json").read_text())
    fresh_drawings = summarize_fresh_drawings(fresh_evidence, frozen_hashes())
    segment_evidence = json.loads((RESULTS / "latvia-audit/segment-study.json").read_text())
    segment_case = next(row for row in fresh_evidence["records"] if row["name"] == SEGMENT_CASE)
    segment_blocks = summarize_segment(segment_evidence, segment_case)
    score_comparisons = student_scores.compare(ROOT)
    policy_study = policy_comparison.compare(RESULTS / "latvia-domains")
    restricted = restricted_deduction.compare(ROOT)
    imo_cohorts = imo_student_scores.compare(RESULTS / "local-cpu/imo")
    proofs, catalog_summary = proof_catalog.catalog(pair_folder.parent / "full-deduction.jsonl", checked_steps)
    result = dict(latvia_restricted_deduction=restricted, imo_student_scores=imo_cohorts, latvia_proof_catalog=catalog_summary, latvia_policy_comparison=policy_study, latvia_official_scores=score_comparisons, latvia_segment_comparison=segment_blocks, latvia_fresh_drawings=fresh_drawings, latvia_translation_audit=drawings, latvia_budget_followup=extra_budget, latvia_paired_ar=ar_study, latvia_full_domain=latvia, common50=common, full=full, completed_training=run, paired_mid_mini_long=paired, proofs=benchmarks, ag1_smoke=ag1,
                  training_prompt_overlaps=overlaps, training_split_audit=split_audit,
                  paired_small_checkpoints=paired_checkpoints, translations=translations,
                  accepted_automatically=accepted_automatically, accepted_by_decision=accepted_by_decision)
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
    data = dict(proofs=proof_rows, common=model_rows(common), **paired,
                full=model_rows({k:v for k, v in full.items() if v["n"] == 200}),
                empty50=common["mid"]["empty"], empty200=full["mid"]["empty"], overlaps=overlaps,
                mid=full["mid"]["top4"], ag1=ag1["top4"], agseconds=ag1["seconds"], union=jgex["repeat_union"],
                heuristic=gains["heuristics_only"], longgain=gains["mini_long_model"],
                midgain=gains["mid_model"], failures=jgex["followup_cases"], onepoint=jgex["one_aux_gain"],
                extra=jgex["repeat_union"] - jgex["current"],
                accepted=translations["accepted"], accepted_auto=accepted_automatically,
                accepted_by_decision=accepted_by_decision, rejected=translations["rejected"],
                review=translations["review"], candidates=sum(translations.values()))
    proof_table = []
    for key in ("jgex_ag_231", "imo"):
        for name, label in (("small_6300", "Interim (original)"), ("small_paired_interim", "Interim (fixed seed)"), ("small_final", "Final (fixed seed)")):
            proof = benchmarks[key][name]
            proof_table.append(
                f'<tr><th scope="row">{SUITES[key]}</th><td>{label}</td><td>{proof["tested"]}</td>'
                f'<td>{proof["proved"]}</td><td>{len(proof["new_problems"])}</td>'
                f'<td>{proof["combined_union"]}/{benchmarks[key]["n"]}</td></tr>'
            )
    data.update(final_only=paired_checkpoints["final_only"], interim_only=paired_checkpoints["interim_only"],
                validation_rows=f'{split_audit["validation_rows"]:,}', setup_overlaps=split_audit["setup_overlaps"])
    for suite, label in (("jgex_ag_231", "jgex"), ("imo", "imo")):
        pair = benchmarks[suite]["paired_checkpoint_proofs"]
        data[label + "_lost"] = len(pair["interim_only"])
        data[label + "_gained"] = len(pair["final_only"])
    data.update(latvia_cases=latvia["cases"], latvia_common=latvia["proved_by_all"],
                latvia_any=latvia["proved_by_any"])
    data.update(long_budget=extra_budget["time_s"], timed_repeats=extra_budget["cases"],
                long_on=extra_budget["outcomes"]["full-deduction"].get("proved", 0),
                long_off=extra_budget["outcomes"]["full_no_ar-deduction"].get("proved", 0))
    data.update(drawings_ok=drawings["outcomes"]["all_goals_hold"], drawings_attempted=drawings["attempts"])
    data.update(fresh_attempts=f"{fresh_drawings['attempts']:,}", fresh_passed=f"{fresh_drawings['all_goals_hold']:,}",
                fresh_unbuilt=fresh_drawings["unbuilt"], fresh_failed=fresh_drawings["failed_goals"],
                fresh_degenerate=fresh_drawings["degenerate"], fresh_seeds=fresh_drawings["seeds_per_case"],
                segment_original=segment_blocks[1]["original"]["all_goals_hold"],
                segment_bounded=segment_blocks[1]["bounded"]["all_goals_hold"])
    passed_by_case = {row["name"]: row["all_goals_hold"] for row in fresh_evidence["records"]}
    data.update(imo_cohort_rows=imo_student_scores.render(imo_cohorts), imo_cohort_years=len(imo_cohorts["editions"]),
                imo_cohort_items=imo_cohorts["matched_items"], imo_proved_higher=imo_cohorts["comparisons"]["proved_higher"],
                imo_same_outcome=imo_cohorts["comparisons"]["same_solver_outcome"])
    data.update(reduced_rules=restricted["reduced_rules"], reduced_wins=restricted["reduced_wins"],
                same_transcripts=restricted["identical"], alternate_routes=restricted["regained_with_different_rules"])
    labels = problem_labels(ROOT)
    data["case_rows"] = render_cases(ROOT, passed_by_case, labels=labels, proofs=proofs)
    data["proof_cards"] = "\n".join(proof_catalog.render(name, proof, *labels[name])
                                     for name, proof in proofs.items())
    data.update(proof_total=catalog_summary["proofs"], proof_goals=catalog_summary["goals"],
                printed_steps=catalog_summary["steps"], linked_steps=catalog_summary["steps_reaching_goals"],
                longest_chain=catalog_summary["longest_chain"])
    data["student_score_rows"] = student_scores.render(score_comparisons)
    data["latvia_rows"] = policy_comparison.table(policy_study)
    policy_off = policy_study["domains"]["full_no_ar"]
    off_counts = {k: v["outcomes"] for k, v in policy_off["policies"].items()}
    data.update(policy_runs=policy_study["runs"], off_wins=len(policy_off["any_wins"]),
                off_heur_timeouts=off_counts["heuristics"]["timeouts"], off_comb_timeouts=off_counts["combined"]["timeouts"],
                off_ded_timeouts=off_counts["deduction"]["timeouts"])
    on, off = "full-deduction", "full_no_ar-deduction"
    original = ar_study["outcomes"]["original"]
    revised = ar_study["outcomes"]["revised_wins"]
    step_counts = ar_study["original_appendix_steps"]
    total_steps = sum(sum(counts.values()) for counts in step_counts.values())
    self_contained = sum(counts["follows"] for counts in step_counts.values())
    recovered = sum(ar_study["restored_by_construction_equations"].values())
    data.update(ar_on=original[on].get("proved", 0), ar_off=original[off].get("proved", 0),
                paired_cases=ar_study["selected"], paired_on=revised[on].get("proved", 0),
                paired_off=revised[off].get("proved", 0), ar_total=total_steps, ar_follow=self_contained,
                ar_recovered=recovered, ar_remaining=total_steps-self_contained-recovered)
    finished_path = RESULTS / "latvia-domains/completed/summary.json"
    data["complete_domain_table"] = ""
    complete_paper = ""
    if finished_path.is_file():
        finished = json.loads(finished_path.read_text())
        data["complete_domain_table"], complete_paper = complete_coverage(finished, latvia["cases"])
        schedule_path = RESULTS / "latvia-domains/execution/baseline.json"
        if schedule_path.is_file():
            schedule = json.loads(schedule_path.read_text())
            initial = sum(len(names) for names in schedule["completed_before_parallel"].values())
            workers = schedule["workers"]
            if initial + len(schedule["scheduled_cases"]) != finished["runs"]:
                raise ValueError("The execution schedule does not cover the completed study")
            data["complete_domain_table"] += (
                f"<p>The first {initial} cases ran one at a time. Later, up to {workers} independent cases ran "
                "on separate physical cores while the laptop had external power. Contention can affect elapsed times "
                "and outcomes near the 60-second limit. "
                '<a href="https://github.com/Sweeeeeeeee/zpd/tree/main/results/latvia-domains/execution">'
                "Execution intervals for each case</a>.</p>"
            )
            complete_paper += (
                f" Pirmos {initial} mēģinājumus izpildīja secīgi. Turpmāk, kad dators bija pievienots "
                f"elektrotīklam, vienlaikus izpildīja līdz {workers} mēģinājumiem uz atsevišķiem procesora kodoliem. "
                "Vienlaicīga slodze var ietekmēt izpildes laiku un iznākumu pie 60~s robežas."
            )
    data["checkpoint_proofs"] = "\n".join(proof_table)
    data.update(final_step=f'{run["step"]:,}', final_top1=run["top1"], final_top4=run["top4"],
                aux_local=aux["repeat_union"], aux_models=aux["local_two_model_union"],
                aux_unique=len(aux["unique_heuristic_gains"]), aux_arch=aux["union"], aux_heur=aux["gains"]["heuristics_only"],
                aux_long=aux["gains"]["mini_long_model"], aux_mid=aux["gains"]["mid_model"])
    data["small_matches"] = full["small-6300"]["top4"]
    data["small_first"] = full["small-6300"]["top1"]
    data["mid_first"] = full["mid"]["top1"]
    data["build_failures"] = sum(b["build_failures"] for b in benchmarks.values())
    data["engine_errors"] = sum(b["engine_errors"] for b in benchmarks.values())
    data["changed"] = sum(len(b["changed"]) for b in benchmarks.values())
    template = Template((ROOT / "bench/results-template.html").read_text())
    (page / "index.html").write_text(template.substitute(data))
    full_deduction = latvia["policies"]["deduction"]
    full_heuristics = latvia["policies"]["heuristics"]
    full_combined = latvia["policies"]["combined"]
    paragraph = (
        f"Pilnajā 70 likumu jomā ar algebrisko spriešanu pārbaudīti {latvia['cases']} pieņemtie "
        f"Latvijas olimpiāžu uzdevumu tulkojumi. Visas trīs meklēšanas stratēģijas pierādīja "
        f"vienus un tos pašus {latvia['proved_by_all']} uzdevumus. Visos šajos pierādījumos pietika "
        "ar formalizācijā dotajiem punktiem. Vienā mēģinājumā meklēšanai atvēlēja 60~s. "
        f"Dedukcija vien laika limitu sasniedza {full_deduction['timeouts']} reizi, "
        f"meklēšana ar heiristikām -- {full_heuristics['timeouts']} reizes, bet ar modeli un "
        f"heiristikām -- {full_combined['timeouts']} reizes. Katrā stratēģijā "
        f"{full_deduction['errors']} mēģinājumi apstājās dzinēja kļūdas dēļ, apvienojot taisnes. "
        "Atsevišķā pārbaudē ar laboto dzinēju no četriem šādiem gadījumiem pierādīts viens "
        "-- 2024./25.~gada valsts olimpiādes 9.~klases 2.~uzdevums. Tajā mediānas viduspunktu "
        "iegūst ar trijstūra viduslīnijas teorēmu. Pārējos trīs mēģinājumos sasniegts laika limits.\n"
    )
    paragraph += (
        f"Bez algebriskās spriešanas trīs stratēģijas kopā pierādīja {len(policy_off['any_wins'])} uzdevumus. "
        f"Laika limitu dedukcija sasniedza {off_counts['deduction']['timeouts']} gadījumos, "
        f"meklēšana ar heiristikām -- {off_counts['heuristics']['timeouts']}, ar modeli un heiristikām -- "
        f"{off_counts['combined']['timeouts']}. Šie rezultāti attiecas uz konkrēto meklēšanas budžetu.\n"
    )
    drawing_paper = (
        f"Katram tulkojumam figūru konstruēja ar {fresh_drawings['seeds_per_case']} jaunām nejaušo skaitļu "
        f"ģeneratora sākumvērtībām. Konstruktoram mērķi nebija pieejami. No {fresh_drawings['attempts']} "
        f"mēģinājumiem {fresh_drawings['unbuilt']} gadījumos figūru neizdevās uzbūvēt. "
        f"Visi mērķi izpildījās {fresh_drawings['all_goals_hold']} zīmējumos. "
        "Šī pārbaude raksturo tulkojumu skaitlisko saderību ar mērķiem. "
        "Atbilstība olimpiādes uzdevuma nosacījumiem jāpārbauda pēc pirmavota."
    )
    national, open_contest = score_comparisons
    if [(r["original"], r["revised"]) for r in score_comparisons] != [("proved", "proved"), ("errors", "timeouts")]:
        raise ValueError("The solver outcomes no longer match the text of the score comparison")
    national_mean = f"{national['mean']:.2f}".replace(".", ",")
    open_mean = f"{open_contest['mean']:.2f}".replace(".", ",")
    scores_paper = (
        "Divos 2015./16.~gada 9.~klases uzdevumos salīdzinājām skolēnu rezultātus ar dedukcijas iznākumu. "
        f"Valsts olimpiādes 2.~uzdevumā {national['participants']} dalībnieka vidējais vērtējums bija {national_mean} no 10 punktiem, "
        f"atklātās olimpiādes 3.~uzdevumā {open_contest['participants']} dalībnieku vidējais bija {open_mean}. Pirmo uzdevumu pierādīja "
        "abi dzinēja varianti. Otrajā sākotnējais dzinējs apstājās ar kļūdu, labotais dzinējs sasniedza laika limitu. "
        "Atšķirīgās dalībnieku grupas un mazā izlase neļauj novērtēt sakarību starp skolēnu un risinātāja rezultātiem. "
        r"\href{https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Gramatas/Uzd_krajumi/Mat_Sac_4-9_15-16_2016.pdf\#page=147}"
        r"{(Avotiņa un Šuste, 2016, 147.--148.~lpp.)}"
    )
    ar_paper = (
        f"Bez algebriskās spriešanas ar tiem pašiem 70 likumiem dedukcija pierādīja "
        f"{data['ar_off']} no {latvia['cases']} uzdevumiem, ar to -- {data['ar_on']}. "
        f"Ar laboto dzinēju atkārtoti pārbaudīja visus {data['paired_cases']} sākotnēji pierādītos "
        f"uzdevumus abos režīmos. Ar algebrisko spriešanu pierādīti {data['paired_on']}, "
        f"bez tās -- {data['paired_off']}. Vienīgajā ieilgušajā mēģinājumā, palielinot limitu līdz {extra_budget['time_s']}~s, "
        "ar algebrisko spriešanu pierādījumu atrada, bez tās dedukcija izsmēla likumus.\n\n"
        f"Sākotnējo pierādījumu izdrukās pārbaudīti {total_steps} algebriskie soļi. "
        f"No konkrētajā solī norādītajiem vienādojumiem izrietēja {self_contained} secinājumi. "
        f"Vēl {recovered} soļus varēja pamatot, pievienojot formalizācijas sākotnējos vienādojumus. "
        "Piemēram, 2021./22.~gada atklātās olimpiādes 9.~klases 3.~uzdevumā no trijstūru "
        "līdzības iegūst $AE/BD=EF/BC$. Lai secinātu $EF=BC$, vajadzīga arī "
        "vienādība $AE=BD$. Oficiālajā risinājumā to pierāda ar paralelograma īpašību, "
        "savukārt formalizācijā tā izriet no punkta $E$ konstrukcijas. "
        "Izdrukātajā soļa pamatojumā šī vienādība izlaista. "
        r"\href{https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/AMO/2020-2030/2022_AMO_uzd_atr.pdf\#page=8}"
        r"{(LU NMS, 2022, 8.~lpp.)}"
    )
    transcript_note = (
        f" Izdrukātie {catalog_summary['proofs']} pierādījumi aptver {catalog_summary['goals']} mērķus un "
        f"{catalog_summary['steps']} numurētu secinājumu. Vienā pierādījumā bija no "
        f"{catalog_summary['minimum_steps']} līdz {catalog_summary['maximum_steps']} soļiem "
        f"(mediāna {catalog_summary['median_steps']:g})."
    )
    restricted_note = (
        f" Izslēdzot {len(restricted['removed_rules'])} ar trijstūru līdzību saistītus likumus un saglabājot "
        f"algebrisko spriešanu, dedukcija pierādīja {restricted['reduced_wins']} no {restricted['cases']} "
        f"uzdevumiem. Visi bija pierādīti arī pilnajā jomā. {restricted['identical']} pierādījumu izdrukas "
        f"sakrita, bet trijos iegūta cita pierādījuma gaita. Piemēram, 2021./22.~gada atklātās olimpiādes "
        f"9.~klases 3.~uzdevumā divu trijstūru līdzību aizstāja to vienādība pēc malas un diviem pieleņķiem."
    )
    (ROOT / "zpd_darbs/tables/latvia_full.tex").write_text(paragraph.rstrip() + restricted_note + complete_paper + "\n\n" + drawing_paper + "\n\n" + ar_paper.rstrip() + transcript_note + "\n\n" + scores_paper + "\n")
    imo = benchmarks["imo"]
    s = full["mid"]
    report = (
        r"Atkārtotajā CPU eksperimentā (Intel Core i7-1355U) vērtēti pirmie 200 validācijas piemēri "
        r"ar palīgpunktu. Stingrajā salīdzinājumā saglabāts jaunā punkta vārds un predikātu argumentu "
        r"secība. Predikātu savstarpējā secība rezultātu neietekmē. "
        f"No 200 piemēriem {s['empty']} atsauces bija bez predikātiem. Tās ieskaitītas kā nesakritības. "
        rf"Modelim \texttt{{mid}} pirmais piedāvājums sakrita {s['top1']} gadījumos, vismaz viens "
        f"no četriem -- {s['top4']} gadījumos. Iepriekš lietotais brīvākais kritērijs tajās pašās "
        f"prognozēs deva {s['relaxed']} sakritības no 200. "
        f"Pirmajos 50 piemēros stingrais četru piedāvājumu rādītājs bija {common['mid']['top4']}/50 "
        rf"modelim \texttt{{mid}}, {common['GenesisGeo']['top4']}/50 modelim GenesisGeo un "
        f"{common['SmolLM2-360M-Instruct']['top4']}/50 modelim SmolLM2-360M. "
        f"Atkārtotajā JGEX pārbaudē DD-AR atrisināja {jgex['current']} uzdevumus, bet kopā ar "
        f"atsevišķo palīgpunktu meklējumu rezultātiem pierādīti {jgex['repeat_union']} no {jgex['n']}. "
        f"IMO-AG-30 pieejamajā daļā ar dedukciju pierādīti {imo['current']}, bet pēc papildu "
        f"meklējumiem -- {imo['repeat_union']} no {imo['n']} uzdevumiem."
        "\n\n"
        rf"Modeļa \texttt{{small}} 6300. apmācības solī pirmā prognoze sakrita ar etalonu "
        f"{full['small-6300']['top1']} no 200 piemēriem. Vērtējot visus četrus piedāvājumus, "
        f"sakritību skaits pieauga līdz {full['small-6300']['top4']}. "
        f"Uzdevumos, kurus sākotnējā dedukcija neatrisināja, ar šo modeli pierādīti "
        f"{jgex['small_6300']['proved']} no {jgex['small_6300']['tested']} JGEX un "
        f"{imo['small_6300']['proved']} no {imo['small_6300']['tested']} IMO uzdevumiem. "
        f"Kontrolpunktam ar zemāko validācijas zudumu ({run['step']} soļi) pirmā prognoze sakrita "
        f"ar etalonu {run['top1']} no {run['n']} gadījumiem, bet vismaz viena no četrām -- {run['top4']}. Ar to pierādīti "
        f"{jgex['small_final']['proved']} no 26 sākotnēji neatrisinātajiem JGEX un "
        f"{imo['small_final']['proved']} no 14 IMO uzdevumiem. "
        f"Atsevišķajā 101 uzdevuma palīgkonstrukciju kopā dedukcija vien pierādīja "
        f"{aux['current']} uzdevumus, bet trīs papildu meklējumu rezultātu apvienojums -- "
        f"{aux['repeat_union']}. "
        "Piemēram, 2004. gada atlases kopas uzdevumā G4a heiristika pievienoja trijstūrim "
        "$ABC$ apvilktās riņķa līnijas centru $E$. No rādiusu vienādības $AE=CE$ un "
        "leņķu sakarībām iegūst $\\angle AEP=\\angle PEC$. Trijstūriem ir kopīga mala $EP$. Trijstūri $AEP$ un "
        "$CEP$ ir vienādi pēc divām malām un leņķa starp tām, tātad $AP=CP$. "
        f"AlphaGeometry lokāli pabeidza trīs pārbaudes piemērus (sakritība četros piedāvājumos "
        f"{ag1['top4']}/3). Šī izlase ir par mazu modeļu salīdzināšanai. "
        "Katrā palīgpunkta prognozes uzdevumā bija dota viena etalonkonstrukcija. Iespējami arī citi derīgi risinājumi.\n"
    )
    pair_counts = imo_cohorts["comparisons"]
    report += (
        f"\nStarptautiskās matemātikas olimpiādes dalībnieku rezultātus ar dedukciju salīdzināja "
        f"{len(imo_cohorts['editions'])} gados, kuros vietējā kopā bija vismaz divi dažādi tās pašas olimpiādes "
        f"uzdevumi (kopā {imo_cohorts['matched_items']}). Vidējo vērtējumu aprēķināja visiem dalībniekiem, "
        f"ieskaitot nulles. Trijos pāros dedukcija pierādīja vienu no "
        f"abiem uzdevumiem. Visos {pair_counts['proved_higher']} gadījumos šim uzdevumam dalībnieku vidējais "
        f"vērtējums bija augstāks. Pārējos {pair_counts['same_solver_outcome']} pāros abu uzdevumu "
        r"iznākums sakrita. Piemēram, 2015. gada 3. un 4.~uzdevuma vidējie vērtējumi bija 0,65 un 4,79 "
        r"no septiņiem punktiem, un dedukcija pierādīja otro no šīm formalizācijām. "
        r"\href{https://www.imo-official.org/results/individual/year/2015/}{(Starptautiskā matemātikas olimpiāde, 2015)}."
    )
    (ROOT / "zpd_darbs/tables/local_eval.tex").write_text(report)


if __name__ == "__main__":
    main()
