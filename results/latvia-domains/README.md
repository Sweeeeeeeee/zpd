# Latvian full-domain benchmark

This is the first complete three-policy comparison in the 18-configuration scan. The 22 November 2026 baseline used revision `c5ae501`, Newclid 3.0.1, numerical seed 0 and Python hash seed 0 on the local Intel Core i7-1355U. The 65 accepted translations are drawn from an 80-problem working set. Ten still await a review decision and five were rejected.

Each JSONL file has one row per accepted problem, including every proof transcript, failure reason, auxiliary construction, rule count and measured resource use. The input manifest binds the problem IDs and texts, solver sources, environment and the [frozen settings](../latvia-domain-plan.json) to their hashes. Each run allowed 60 seconds after loading and 2,048 MiB. A search could add at most one point after the initial formalization. The combined policy tried the 5.1M-parameter mid checkpoint ahead of heuristics.

| Search policy | Proved | Time limit | Line-merge error | Deduction exhausted |
|---|---:|---:|---:|---:|
| Deduction alone | 20 | 31 | 10 | 4 |
| Deduction and heuristics | 20 | 35 | 10 | 0 |
| Deduction, mid model and heuristics | 20 | 35 | 10 | 0 |

All three policies proved the same 20 problem IDs without adding a point. All three encountered the line-merge exception on the same ten IDs. The remaining outcomes apply to the configured time and search budget. A translation can already contain auxiliary points in its initial construction.

The [paired AR comparison](paired-ar/) adds the matching 65 deduction-only records with algebraic reasoning off, a targeted revised-solver repeat, an audit of the printed algebra and a comparison with five official solutions.

## Reproduce and check

At the baseline revision, follow the scan command in [the domain guide](../../docs/domains.md). The three configuration names are `full-deduction`, `full-heuristics` and `full-combined`. To regenerate the published comparison from the JSONL records in this directory, run `python -m bench.publish` at the current revision.

The [merge checks](merge-checks.json) preserve a separate diagnostic with the revised solver. The upstream examples were the three IDs that had the line-merge exception in the archived [full-domain example run](../../ddar/results/examples_python_full.txt). The Latvian diagnostic selected the first four affected IDs in lexical order in the baseline deduction configuration. The baseline row and revised measurement are both supplied for each Latvian case. The full paired retry uses the separate procedure in the domain guide. These diagnostic results do not change the counts in the table.

### Recovered grade 9 proof

In the Latvian national olympiad for 2024–25, grade 9, problem 2, point D divides AB in a 2:1 ratio. The median BE meets CD at F. The goal is BF = FE. Let T be the midpoint of AD. Then AT = TD = DB. In triangle ADC the segment TE joins two midpoints, so TE is parallel to DC. In triangle BTE, D is the midpoint of BT and DF is parallel to TE. Therefore F is the midpoint of BE.

The formalization names the original midpoint E as M and the helper T as E. With the revised solver, deduction alone proved BF = FM. An independent run from the same problem text reproduced the entire proof transcript. The three other Latvian diagnostic cases reached their 60-second limits. On the three historical Newclid examples, the revised solver proved `ar_example_paper_ratio_chasing`, exhausted deduction on `rule_r29_not_found_disguise` and reached the time limit on `b23_may_need_BUILT_IN_FNS`. [Original statement](../../problems/latvia/geometry/national/2024-25_75/grade09/p2.md) · [Formalization](../../problems/latvia/geometry_translated/national/2024-25_75/grade09/p2.txt)

### Auxiliary-point search in the full rule set

Each of the 65 problems has six original measurements with the same 70 rules, a 60-second search budget and a 2,048 MiB memory limit. We join the results by the frozen problem ID. The full scan used revision `c5ae501`. One of these 390 records was produced after scheduling began on two performance cores. The remaining 389 ran sequentially. The two new record files are [heuristics with AR off](full_no_ar-heuristics.jsonl) and [model plus heuristics with AR off](full_no_ar-combined.jsonl). The [earlier deduction comparison](paired-ar/original-full_no_ar-deduction.jsonl) supplies the third AR-off condition.

| Algebraic reasoning | Policy | Proofs | Timed out | Engine errors | Deduction exhausted | Reached depth 1 |
|---|---|---:|---:|---:|---:|---:|
| On | Deduction | 20 | 31 | 10 | 4 | 0 |
| On | Heuristics | 20 | 35 | 10 | 0 | 0 |
| On | Model and heuristics | 20 | 35 | 10 | 0 | 0 |
| Off | Deduction | 0 | 24 | 9 | 32 | 0 |
| Off | Heuristics | 0 | 55 | 9 | 0 | 1 |
| Off | Model and heuristics | 0 | 54 | 9 | 0 | 2 |

With AR enabled, the same 20 problems were proved under every policy, all at depth zero. The four problems on which deduction exhausted its rules reached the time limit under both auxiliary-point policies. With AR disabled, 30 of the 32 problems where deduction exhausted its rules timed out under both search policies. Of the remaining two, one finished the depth-one search under both policies. The other finished it only under the combined policy.

The completed AR-off search records show at least one heuristic call for one problem and at least one model call for two. The parent process records the resource outcome when a run times out. Its empty counters cannot establish how many proposals the child process tried. In the combined condition model and heuristics ran together, so these runs cannot isolate the model's own contribution. The reported coverage applies to the recorded budget and formalizations.

Run `python -m bench.latvia.policy_comparison` to rebuild the six outcome distributions, matched problem profiles and file checksums. Use `--from-scan ORIGINAL_SCAN` to validate the published rows against the frozen runner output. [Comparison code](../../bench/latvia/policy_comparison.py)

### Read a numbered proof

The [proof reader](https://zpd.aniwe.me/#proof-records) links every cited premise to its printed statement and identifies the equation-check outcome on each algebraic step. The 20 original deduction proofs contain 24 goals and 161 numbered deductions, ranging from 3 to 21 per problem (median 7). Every numbered deduction is reachable by following the printed references backward from a goal. The longest such chain has six deductions. Shortest proofs under alternative rule sequences were outside this check. The reader includes assumptions and numerical checks from each construction, so references such as `[C2]` and `[N4]` can also be followed.

Across the 20 transcripts, angle chasing appears 36 times in all 20 problems, and ratio chasing appears 12 times in nine. Among numbered geometric rules, parallel directions from collinearity (`r82`) appears 25 times in nine problems, and the isosceles base-angle rule (`r13`) appears 20 times in seven. The counts use the final proof and are checked against the engine’s own rule counters. [Indexer](../../bench/latvia/proof_catalog.py) · [Per-rule counts](../local-cpu/summary.json)

### Removing similarity rules

We compared the same 65 original deduction-only runs with AR enabled, removing 11 of the 70 rules. All 65 full-rule records ran before parallel scheduling. The 65 reduced-rule runs were scheduled in the subsequent phase. Each solve had a 60-second search budget and a 2,048 MiB limit. We compare coverage under those conditions. Wall-clock and timeout differences can also reflect scheduling. [Original restricted records](no_similarity-deduction.jsonl) · [Retained rules](../../ddar/configs/domains/no_similarity.json)

| Full-rule result | Reduced-rule result | Problems |
|---|---|---:|
| Proved | Proved | 15 |
| Proved | Exhausted deductions | 3 |
| Proved | Time limit | 2 |
| Time limit | Time limit | 31 |
| Exhausted deductions | Exhausted deductions | 4 |
| Engine error | Engine error | 7 |
| Engine error | Time limit | 2 |
| Engine error | Exhausted deductions | 1 |

Of the 20 full-rule proofs, seven cited one or more of the removed rules. Three of those seven still had a restricted proof. All 12 rediscovered proofs originally using only retained rules had identical transcripts. A thirteenth full-rule transcript used only retained rules but the restricted run timed out (open olympiad 2001–02, grade 10, P4). Its existing 21-step transcript uses only allowed rule identifiers. A timeout describes search within a budget and cannot establish a theorem’s necessity.

For the 2021–22 open olympiad grade 9 hexagon (P3), the full-rule transcript uses AA similarity and ratios, taking seven steps. In five steps the reduced solver uses the supplied equality AE = BD, two angle equalities and ASA congruence to obtain AF = CD and BC = EF. This gives a second route on the same input. The two other alternate proofs are the preparatory 1999–2000 grade 10 P4 (15 vs. 17 steps) and preparatory 2010–11 grade 9 P2 (6 vs. 5). [Original seven-step proof](https://zpd.aniwe.me/#proof-open-2021-22_47-grade09-p3) · [Exact reduced transcript and construction](no_similarity-deduction.jsonl)

Run `python -m bench.latvia.restricted_deduction` to reproduce the ID-matched transition counts, allowed rule IDs and proof-specific differences. The command verifies both rule files against the frozen configuration manifest.

### Complete scan

Once both jobs finish, run `python -m bench.latvia.finalize ORIGINAL_SCAN MERGE_RETRIES results/latvia-domains/completed`, then `python -m bench.publish`. The packager verifies every expected case, configuration and paired input digest, exports the original and revised inputs, and computes counts from the individual records. Original coverage and selective retries are reported separately. JSONL records preserve the original field order. For a source record, re-encode the decoded object using `json.dumps(row, indent=2, ensure_ascii=False) + "\n"` to verify its recorded SHA-256.
