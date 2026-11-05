# Tasks

## Tools (done)

- [x] 1. DD-AR engine and domains. Newclid's DDAR runs on CPU; how rules and AR load is documented. A domain is a JSON config of enabled rules plus an AR switch, with warnings when the rule set cannot use or prove a predicate. (docs/ddar.md, docs/rules.md)
- [x] 2. Sources of auxiliary points. Human heuristics (midpoints, circumcenters, feet of altitudes) and a small transformer written from scratch, with a tokenizer, training script and 100k training examples from GenesisGeo. (docs/geo-lm.md, docs/datagen.md)
- [x] 3. Solver. Search "DD-AR, then an auxiliary point, then DD-AR again" with depth and branching limits and no random guessing; tools switched and swapped in JSON. solve(problem, config, budget) runs in a separate process under time, memory and CPU limits and returns the proof, resources used, rules, tools and failure reason. (docs/pipeline.md)
- [x] 4. Translation guide and problem store. Guide for translating olympiad problems into Newclid syntax, with a numerical check of the figure. Problem store with per-problem results for each config and budget, and a scanner table. (docs/translation_guide.md, docs/README.md)
- [x] 5. Documentation, tests, presentation. (docs/README.md, tests/, docs/present.md)

## Research setup

- [x] 6. Define domains. Three domains, each with and without AR: full (Newclid's default rules plus the circle rules it leaves out and the midline theorem), circles (circles and inscribed angles only) and no_similarity (full without similar triangles). Each comes with the "easy" setting: search depth at most 1, auxiliary points from the heuristics, budget 60 s and 2 GB, stored in the config. (docs/domains.md, ddar/configs/domains/, pipeline/configs/domains/)

### 7. Problem set (use agent scheme - make a guide with eamples and givi it to an agent so token credits werent used that much)
- [x] 7.1. Collect Latvian olympiad problems. Pull every problem (all topics) from the NMS archive (nms.lu.lv: national, regional, school and open olympiads since 1973/74, and the Baltic Way and IMO selection tests) into problems/latvia/: all/ holds every problem, one file per problem, under <competition>/<season>_<olympiad>/grade<NN>/; geometry/ holds the geometry problems with the same paths; geometry_translated/ is ready for the translations. AoPS (Latvia contests) blocks automated downloads and draws on the same olympiads, so it is not used. 6333 problems, 1499 of them geometry. (problems/latvia/README.md, bench/latvia/)
- [ ] 7.2. Sort the geometry problems. For each of the 1499, decide whether Newclid can state it: plane geometry with a provable goal (yes), or solid geometry, computing a length or angle, inequality, construction, "find all" (no). Record the untranslatable ones with the reason in geometry_translated/untranslatable.csv.
- [ ] 7.3. Pick the working set. From the statable problems choose 50-100 to translate first, spread over competitions, grades and decades (start with the national olympiad and the selection tests). List them in a file so the choice is reproducible.
- [ ] 7.4. Translate a pilot batch of about 10 and scan it in the full domain. Fix the translation guide where translations went wrong (bad figures, wrong goals) before translating the rest.
- [ ] 7.5. Translate the rest of the working set in batches (one competition at a time); every file passes the numerical check.
- [ ] 7.6. Metadata. For each translated problem record source, year, grade, topic (tags) and official difficulty (grade and problem number as a proxy, plus scores where published), and whether an official solution exists.

### 8. Transformer (independent of 7; can run in the background meanwhile)
- [ ] 8.1. Full training run on the 100k examples (about 14 h on CPU); keep the log and the best checkpoint. Short run done: 2.1M-param model (configs/train_mini.json), 1600 steps in 14 min, val loss 0.57; loss still falling.
- [x] 8.2. Offline check: validation loss, and how often its proposals parse into valid Newclid constructions on held-out GenesisGeo problems. (geo-lm/scripts/eval_aux.py; mini model: 92% translatable, exact match 6% top-1, 21% top-4; results/transformer/)
- [ ] 8.3. Pipeline configs with the transformer switched on for each domain; measure on the examples and the pilot batch how often its points are usable and help prove the goal.

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
- [ ] 11.2. Update the presentation (docs/present.md) with real numbers.
- [ ] 11.3. Final check: tests pass, the scan can be reproduced from the README, results committed.

## Paper

### 12. ZPD paper in LaTeX (zpd_darbs/)
- [x] 12.1. Template matching the VIAA guidelines (zpd_darbs/vadlinijas/): A4, 2.5 cm margins, Times 12 pt, 16/14 pt headings, title page from appendix 3, abstracts, contents, unnumbered introduction and conclusions, captions, references and sources list from appendices 4-5, appendices; guidelines logo on the title page. (zpd_darbs/template/)
- [x] 12.2. Preliminary paper filled with the project's content, red labels saying what each part is, red placeholders for what is still missing. (zpd_darbs/preliminary/)
- [x] 12.3. Scripts that build the paper's figures and tables from results/. (zpd_darbs/scripts/make_figures.py, make)
- [ ] 12.4. Fill in personal data (school, author, supervisor, city) and the literature comparison in chapter 1.
- [ ] 12.5. After tasks 9-10: replace the placeholders with the scan results, write the final conclusions (one per task), check the 16-page limit, build with nolabels.

