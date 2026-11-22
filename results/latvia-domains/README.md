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

### Complete scan

Once both jobs finish, run `python -m bench.latvia.finalize ORIGINAL_SCAN MERGE_RETRIES results/latvia-domains/completed`, then `python -m bench.publish`. The packager verifies every expected case, configuration and paired input digest, exports the original and revised inputs, and computes counts from the individual records. Original coverage and selective retries are reported separately. JSONL records preserve the original field order. For a source record, re-encode the decoded object using `json.dumps(row, indent=2, ensure_ascii=False) + "\n"` to verify its recorded SHA-256.
