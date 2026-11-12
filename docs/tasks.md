# Tasks

## Tools (done)

- [x] 1. DD-AR engine and domains. Newclid's DDAR runs on CPU; how rules and AR load is documented. A domain is a JSON config of enabled rules plus an AR switch, with warnings when the rule set cannot use or prove a predicate. (docs/ddar.md, docs/rules.md)
- [x] 2. Sources of auxiliary points. Human heuristics (midpoints, circumcenters, feet of altitudes) and a small transformer written from scratch, with a tokenizer, training script and 100k training examples from GenesisGeo. (docs/geo-lm.md, docs/datagen.md)
- [x] 3. Solver. Search "DD-AR, then an auxiliary point, then DD-AR again" with depth and branching limits and no random guessing; tools switched and swapped in JSON. solve(problem, config, budget) runs in a separate process under time, memory and CPU limits and returns the proof, resources used, rules, tools and failure reason. (docs/pipeline.md)
- [x] 4. Translation guide and problem store. Guide for translating olympiad problems into Newclid syntax, with a numerical check of the figure. Problem store with per-problem results for each config and budget, and a scanner table. (docs/translation_guide.md, docs/README.md)
- [x] 5. Documentation, tests, presentation. (docs/README.md, tests/; the presentation draft docs/present.md was dropped and is redone in 11.2)

## Research setup

### 6. Domains
- [x] 6. Define domains. Three domains, each with and without AR: full (Newclid's default rules plus the circle rules it leaves out and the midline theorem), circles (circles and inscribed angles only) and no_similarity (full without similar triangles). Each comes with the "easy" setting: search depth at most 1, auxiliary points from the heuristics, budget 60 s and 2 GB, stored in the config. (docs/domains.md, ddar/configs/domains/, pipeline/configs/domains/)

### 7. Problem set
Scheme agreed with the user 2026-11-12: agents do the bulk work, automatic checks catch errors, the user reviews only flagged problems, a pilot and a random audit. Scripts write a tracking CSV (problems/latvia/geometry_translated/status.csv: problem, stage, translations A/B, check results, flags, reviewer, decision).
- [x] 7.1. Collect Latvian olympiad problems. Pull every problem (all topics) from the NMS archive (nms.lu.lv: national, regional, school and open olympiads since 1973/74, and the Baltic Way and IMO selection tests) into problems/latvia/: all/ holds every problem, one file per problem, under <competition>/<season>_<olympiad>/grade<NN>/; geometry/ holds the geometry problems with the same paths; geometry_translated/ is ready for the translations. AoPS (Latvia contests) blocks automated downloads and draws on the same olympiads, so it is not used. 6333 problems, 1499 of them geometry. (problems/latvia/README.md, bench/latvia/)
- [ ] 7.2. Sort the 1499 geometry problems (no translation yet): can Newclid state it? Plane geometry with a provable goal (yes), or solid geometry, computing a length or angle, inequality, construction, "find all", locus (no).
  - [x] 7.2a. Keyword prefilter (script; done 2026-11-12 as hints only, because "plaknē" = in the plane makes keyword rules unsafe; sorting/prefilter.csv): Latvian markers such as telpā, tetraedrs, aprēķini, atrast visus, nevienādība, konstruē remove the obvious "no" cases.
  - [x] 7.2b. Agent classification (cheap model, 8 batches, all 1499; done 2026-11-12): category, reason, confidence; problems that depend on a drawing are flagged. Result: 422 prove (statable), 209 prove_other, 182 compute, 63 inequality, 41 construction, 27 find_all, 76 existence, 302 combinatorial, 140 solid, 37 unreadable; 68 low confidence. (bench/latvia/sort_geometry.py, problems/latvia/geometry_translated/sorting/)
  - [x] 7.2c. Check of the sorting (the user delegated it to Claude, 2026-11-12): 60 problems read; 19/20 random right, prove 17/20 clearly right (2 borderline, 1 wrong), prove_other 20/20 right. Errors lean to generous `prove`, caught at translation. Also found a split error and cross-year duplicates (handle in 7.3). (sorting/REVIEW.md): error rate of the sorting. Untranslatable ones with the reason in geometry_translated/untranslatable.csv.
- [x] 7.3. Working set (2026-11-12, bench/latvia/working_set.py, seed 20261112): duplicates merged, not deleted (55 groups, 116 files, problems/latvia/geometry_translated/duplicates.csv; one entry keeps every id, title, season and source); glued statements (10), missing formulas (53) and low-confidence sorting (14) left out until fixed; 80 problems (tst 12, national 32, open 16, regional 12, school 8) spread over decades and grades, pilot of 10 marked (geometry_translated/working_set.csv).
- [ ] 7.4. Pilot, about 10 problems, done together with the user (~1 h): run the whole pipeline of 7.5 on them, scan in the full domain, fix the translation guide and its worked examples (about 10 tricky constructions) before scaling.
- [ ] 7.5. Translate the rest in batches of ~10 problems from one competition. Per problem:
  - [ ] two independent translations (agents A and B, stronger model) with docs/translation_guide.md and the worked examples;
  - [ ] automatic checks on each: the figure builds, the goal holds numerically on 5 random drawings (pipeline.check_figure, different seeds), and no hidden specialisation: the number of free points and parameters matches the statement (catches a true but easier problem, e.g. a general triangle made isosceles);
  - [ ] back-translation: a third agent writes the Newclid text back in plain words without the original; a fourth compares it with the Latvian statement (same hypotheses, same goal);
  - [ ] accepted automatically if both translations pass, agree after back-translation and give the same solver result; otherwise flagged for review (expected 15-25%, ~3 min each for the user). Claude settles disagreements and fixes recurring errors in the guide;
  - [ ] random audit: the user checks 10% of the automatically accepted ones; the paper reports the measured translation error rate with its confidence bound.
- [ ] 7.6. Metadata, filled by the same agents in the same pass: source, year, grade, problem number, topic (tags), official difficulty (grade and problem number as a proxy, plus scores where published), whether an official solution exists.

### 8. Transformer (independent of 7; can run in the background meanwhile)
- [ ] 8.1. Full training run on the 100k examples (about 14 h on CPU); keep the log and the best checkpoint. Short run done: 2.1M-param model (configs/train_mini.json), 1600 steps in 14 min, val loss 0.57; loss still falling. Longer run (configs/train_mini_long.json): 9000 steps (~1.5 h in three resumed parts), val loss 0.27, 91% translatable, exact 33% top-1 / 49.5% top-4; solves 1 of the 2 stuck JGEX problems (the 1600-step model solved both). Checkpoint runs/mini_long/best.pt (in git). Larger model `mid` (5.1M params, configs/train_mid.json), 9000 steps (~3.4 h, 2026-11-10 and 11-12): val loss 0.235, exact 39% / 53.5%, JGEX +5 of 26, IMO 2015 P3 (IMO-AG-30 16 vs 15), imo_102 6 of 101; runs/mid/best.pt (in git). The 11M `small` run is still open (GPU / Kaggle).
- [x] 8.2. Offline check: validation loss, and how often its proposals parse into valid Newclid constructions on held-out GenesisGeo problems. (geo-lm/scripts/eval_aux.py; mini model: 92% translatable, exact match 6% top-1, 21% top-4; results/transformer/)
- [x] 8.2a. Standard benchmarks (added 2026-11-10): DDAR alone and DDAR + mini_long on Newclid's jgex_ag_231, imo, imo_102_requires_aux, compared with AG1. JGEX 205 / 210 (AG1 198 / 228), IMO-AG-30 15 / 15 (AG1 14 / 25), imo_102 0 / 3. (bench/run_benchmarks.sh, results/, docs/rezultati.md)
- [ ] 8.3. Pipeline configs with the transformer switched on for each domain; measure on the examples and the pilot batch how often its points are usable and help prove the goal. Examples done 11-12 with `mid` (configs domains_transformer/*_transformer.json): same problems solved as without the model, ~5 s slower; the pilot batch is still to do.
- [ ] 8.4. Proposer comparison (added 2026-11-10): which model finds the one auxiliary point fastest in a domain. Done 11-12 (2-hour run): all models on the same held-out problems (bench/eval_proposers.py; ours on 200, the big ones on 3-50): mid 51.5% exact first point in 0.7 s, general models 0-2% in 13-464 s, GenesisGeo ~53% (may have seen the data), AG1 killed by memory here. Comparison in domains: full domain only, DDAR (Python engine) times out on 32 of 60 at 60 s, heuristics 0 of 31. Open: the other domains and models, a bigger budget or a faster engine for domains, AG1 and the big models on Kaggle. (docs/models.md, docs/rezultati.md section 4)

## Research

### 9. Scan
- [ ] 9.1. Freeze the scan: list the configs (6 domains x aux sources: none, heuristics, heuristics + transformer), the budget and the engine version.
- [ ] 9.2. Run every working-set problem in every config and store the results.
- [ ] 9.3. Rerun crashes and timeouts; classify the remaining failures (engine bug, translation error, budget) and fix what can be fixed.

### 10. Analysis
- [ ] 10.1. Per domain: which problems have an easy solution, the key auxiliary point, and how easy it is (proof steps, rules used, time, memory).
- [ ] 10.2. Compare domains: which theorem or AR makes which problems easy.
- [ ] 10.3. Compare sources of auxiliary points: none, heuristics, transformer.
- [ ] 10.4. Compare with official difficulty and, for a sample, with the official solutions (same key construction or not).
- [ ] 10.5. Problems with no easy solution found: why (missing rule, needs depth 2, budget, translation).

### 11. Report
- [ ] 11.1. Write up the method and results (docs/apraksts.md, docs/rezultati.md) with the tables and examples of easy solutions.
- [ ] 11.2. Write the presentation with real numbers.
- [ ] 11.3. Final check: tests pass, the scan can be reproduced from the README, results committed.

## Paper

### 12. ZPD paper in LaTeX (zpd_darbs/)
- [x] 12.1. Template matching the VIAA guidelines (zpd_darbs/vadlinijas/): A4, 2.5 cm margins, Times 12 pt, 16/14 pt headings, title page from appendix 3, abstracts, contents, unnumbered introduction and conclusions, captions, references and sources list from appendices 4-5, appendices; guidelines logo on the title page. (zpd_darbs/template/)
- [x] 12.2. Preliminary paper filled with the project's content, red labels saying what each part is, red placeholders for what is still missing. (zpd_darbs/preliminary/)
- [x] 12.3. Scripts that build the paper's figures and tables from results/. (zpd_darbs/scripts/make_figures.py, make)
- [ ] 12.4. Fill in personal data (school, author, supervisor, city) and the literature comparison in chapter 1.
- [ ] 12.5. After tasks 9-10: replace the placeholders with the scan results, write the final conclusions (one per task), check the 16-page limit, build with nolabels.

