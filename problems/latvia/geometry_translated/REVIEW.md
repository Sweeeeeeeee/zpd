# For the user to review (2026-11-13)

Open status.csv (stage = review), write decisions in decisions.csv
(id, reviewer, decision = accept A / accept B / reject: ..., reason), then run
`python -m bench.latvia.translation_status status`. A = Adam, B = Eve; files in _work/A, _work/B.

Policy questions (each decides several problems):
1. Shape fixed by the conditions (no point to build): allow building from a derived fact, or reject?
   national/2009-10_60/grade11/p3 (Eve built it, Adam refused), national/1990-91_41/extra/grade11/p4,
   national/2016-17_67/grade10/p3, open/1985-86_13/grade07/p2 (reformulations in `# notes:`)
2. "Iff": keep only the buildable direction? national/2005-06_56/grade12/p4 (both translated the forward
   direction), regional/2005-06_56/grade10/p4 (forward direction only in notes)
3. Typo in the statement fixed by the translators: accept? national/1979-80_30/grade09/p4 (CD -> DG),
   open/2001-02_29/grade12/p3 (MNK -> MKN)
4. Hard to build: national/2024-25_75/grade12/p2, tst/2024_bw/day2/p9: reject or keep trying?

## Cases awaiting a decision

The first link opens the original Latvian statement. A and B are the two proposed formalizations. Their source files include notes when the translator could represent only part of a statement.

| Original problem | First translation | Second translation |
|---|---|---|
| [tst/2024_bw/day2/p9](../geometry/tst/2024_bw/day2/p9.md) | [Version A](_work/A/tst/2024_bw/day2/p9.txt) | [Version B](_work/B/tst/2024_bw/day2/p9.txt) |
| [national/1990-91_41/extra/grade11/p4](../geometry/national/1990-91_41/extra/grade11/p4.md) | [Version A](_work/A/national/1990-91_41/extra/grade11/p4.txt) | [Version B](_work/B/national/1990-91_41/extra/grade11/p4.txt) |
| [national/1979-80_30/grade09/p4](../geometry/national/1979-80_30/grade09/p4.md) | [Version A](_work/A/national/1979-80_30/grade09/p4.txt) | [Version B](_work/B/national/1979-80_30/grade09/p4.txt) |
| [national/2016-17_67/grade10/p3](../geometry/national/2016-17_67/grade10/p3.md) | [Version A](_work/A/national/2016-17_67/grade10/p3.txt) | [Version B](_work/B/national/2016-17_67/grade10/p3.txt) |
| [national/2009-10_60/grade11/p3](../geometry/national/2009-10_60/grade11/p3.md) | [Version A](_work/A/national/2009-10_60/grade11/p3.txt) | [Version B](_work/B/national/2009-10_60/grade11/p3.txt) |
| [national/2024-25_75/grade12/p2](../geometry/national/2024-25_75/grade12/p2.md) | [Version A](_work/A/national/2024-25_75/grade12/p2.txt) | [Version B](_work/B/national/2024-25_75/grade12/p2.txt) |
| [national/2005-06_56/grade12/p4](../geometry/national/2005-06_56/grade12/p4.md) | [Version A](_work/A/national/2005-06_56/grade12/p4.txt) | [Version B](_work/B/national/2005-06_56/grade12/p4.txt) |
| [open/2001-02_29/grade12/p3](../geometry/open/2001-02_29/grade12/p3.md) | [Version A](_work/A/open/2001-02_29/grade12/p3.txt) | [Version B](_work/B/open/2001-02_29/grade12/p3.txt) |
| [open/1985-86_13/grade07/p2](../geometry/open/1985-86_13/grade07/p2.md) | [Version A](_work/A/open/1985-86_13/grade07/p2.txt) | [Version B](_work/B/open/1985-86_13/grade07/p2.txt) |
| [regional/2005-06_56/grade10/p4](../geometry/regional/2005-06_56/grade10/p4.md) | [Version A](_work/A/regional/2005-06_56/grade10/p4.txt) | [Version B](_work/B/regional/2005-06_56/grade10/p4.txt) |

The 2024 Baltic Way selection problem 9 remains in review. Version A built only two of twelve goal-blind drawings. The translation guide requires four. The previous six-seed check had recorded a pass based on one drawing. All 65 accepted translations already met the minimum in their archived checks. [Twelve-seed result](_work/checks/tst/2024_bw/day2/p9.A.json)

## Audit sample

Six of the 57 translations accepted directly by the automated checks were selected before reviewing their content. The sampling order is the ascending SHA-256 digest of the UTF-8 string `zpd-20261122-audit/` followed by the full problem ID from status.csv. The first six IDs form this audit. The eight acceptances with recorded Claude decisions fall outside this sampling pool. The source comparisons and numerical replays below were completed with Codex on 22 November 2026. Independent human review remains open. For each pair, record any constructor points absent from the original, any omitted nondegeneracy or segment condition, and whether both directions of the claim are represented. Search depth starts after the formalization has supplied its points. For example, the 2021–22 national grade 11 problem 2 translation supplies E and F to encode a midpoint constraint before the solver starts.

| Original problem | Construction to check |
|---|---|
| [national/2021-22_72/grade11/p2](../geometry/national/2021-22_72/grade11/p2.md) | [Accepted construction](national/2021-22_72/grade11/p2.txt) |
| [regional/1987-88_38/grade07/p2](../geometry/regional/1987-88_38/grade07/p2.md) | [Accepted construction](regional/1987-88_38/grade07/p2.txt) |
| [national/2008-09_59/grade09/p4](../geometry/national/2008-09_59/grade09/p4.md) | [Accepted construction](national/2008-09_59/grade10/p4.txt) |
| [school/2007-08_58/grade11/p3](../geometry/school/2007-08_58/grade11/p3.md) | [Accepted construction](school/2007-08_58/grade11/p3.txt) |
| [tst/2025_bw/day2/p11](../geometry/tst/2025_bw/day2/p11.md) | [Accepted construction](tst/2025_bw/day2/p11.txt) |
| [regional/2015-16_66/grade11/p3](../geometry/regional/2015-16_66/grade11/p3.md) | [Accepted construction](regional/2015-16_66/grade11/p3.txt) |

### Findings for the six selected translations

Each original is a one-direction proof problem. We compared its hypotheses, constructed points and goals with the accepted translation. We also drew each construction with seeds 0–31 after removing the goals from the builder. Six of 192 drawings could not be built. All 186 remaining drawings were nondegenerate at the checker's threshold and satisfied every goal. Numerical agreement supplements the source comparison. It does not establish equivalence for every possible configuration. [Per-seed results](../../../results/latvia-audit/drawings.json) · [Reproduction script](../../../bench/latvia/sample_audit.py)

| Official problem | Drawings built / 32 | What changed in the formalization |
|---|---:|---|
| 2021–22 national, grade 11, no. 2 | 32 | O names the concurrency point in the statement. Extra midpoints E and F construct the circle of possible midpoints N. Reflecting D in N gives C. The circle centered at E is the image of the circle centered at O under the dilation of factor ½ about D, so the construction enforces OB = OC. M and N remain the prescribed midpoints. [Official problem 11.2, p. 5](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/VOL/2020-2030/VOL_72_uzd_atrisinajumi.pdf#page=5) |
| 1987–88 regional, grade 7, no. 2 | 32 | The four named midpoints give the order M–P–N–K and both pairs of parallel sides. Convexity and the explicit condition that no three midpoints are collinear are absent. Their omission matters if the two parallelism goals are read as a nondegenerate parallelogram in every drawing. [Official problem 38.17, p. 3](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/NOL/ro_38_uzd.pdf#page=3) |
| 2008–09 national, **grade 9**, no. 4 | 30 | All named points correspond to the acute triangle, its feet, orthocenter and three midpoints. The three side equalities implement the printed triangle correspondence by SSS. The PDF places the problem in the left, grade 9 column. Grade 10 problem 4 in the right column asks about an algebraic expression. The historical study ID ends in `grade10/p4`. Only the grade 9 statement is represented in the 65 formalizations. [Official problem, left column, p. 1](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/VOL/2000-2010/59repol_uzd.pdf#page=1) |
| 2007–08 preparatory, grade 11, no. 3 | 31 | The PDF visibly prints DH perpendicular to CE. Extra point K is the diagonal intersection. A parallel through K determines E with the given side ratio in the original convex trapezoid. The foot construction enforces the perpendicular but allows H outside segment CE. The initial construction also allows D on either side along its parallel line. [Official problem, p. 8](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/SOL/2000-2010/so58_uzd.pdf#page=8) |
| 2025 Baltic Way selection, day 2, no. 11 | 29 | M and N occur in the statement. Extra points Z (antipode of M), V (on the circle with diameter BC) and T (projection of V on BC) restrict A to the intended arc. The ray from Z through an interior point of chord BC meets the minor arc BC, so the inscribed angle at A is 120°. Endpoints and coincident tangents are degenerate. The goal is the stated perpendicularity. [Official problem, p. 1](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/baltic_way_2013/BW_problems_solutions/BW_atlase_2025_otra_diena__1_.pdf#page=1) |
| 2015–16 regional, grade 11, no. 3 | 32 | E and F are already statement points. The two circumcircles select their intersection other than E. Triangle similarity uses the correspondence A↔C, B↔D and F↔F. The translation omits convexity of ABCD and allows the diagonals to meet outside their segments. [Official problem, p. 7](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/NOL/NOV_66_uzd.pdf#page=7) |

To repeat the numerical check, run `PYTHONHASHSEED=0 python -m bench.latvia.sample_audit /tmp/latvia-drawings.json` at the repository root with the project environment active.
