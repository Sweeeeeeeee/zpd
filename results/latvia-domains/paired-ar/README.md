# What algebraic reasoning contributes

The original scan used 70 Newclid rules on 65 accepted Latvian olympiad translations. It found proofs for 20 problems with algebraic reasoning (AR) enabled. Turning AR off gave zero proofs. Of the 20 original wins, the rule engine exhausted deduction on 16 and timed out on four with AR off. These are outcomes for deduction alone, a fixed seed and a 60-second search budget per problem. The results measure this solver's coverage. Other proofs may be possible for the same problems.

The follow-up revisited **all 20 original wins**, running both settings again with the line and circle merge correction. The [summary](summary.json) reports the original 65 pairs and the selected 20 revised pairs separately. Selection used the original outcome, so this follow-up measures reproducibility on those wins. The other 45 contributed only to the original full-corpus comparison in this study.

At the original 60-second limit, the revised solver reproduced 19 of the 20 original transcripts byte for byte with AR on. The remaining case, the 2001–02 Open Olympiad grade 10 problem 4, timed out. With AR off none were proved, 14 exhausted deduction and six timed out. In a separate 180-second pair on the timed-out case, AR on produced a different 17-step transcript in 69.8 seconds elapsed (including loading). AR off exhausted deduction after 116.2 seconds. This follow-up retains the original 60-second outcome. [Extended-budget records](budget-180.json)

## How much of each transcript can be checked?

All 20 original wins contain an angle-chasing step. Nine also contain a ratio-chasing step. The checker reads each numbered AR appendix entry and compares its printed premises with its printed conclusion.

| Printed step | Follows from the listed equations | Needs additional context | Total |
|---|---:|---:|---:|
| Directed angles | 11 | 25 | 36 |
| Positive length ratios | 3 | 9 | 12 |

Nineteen of the 20 transcripts have at least one algebraic step that needs more context. This measures what a reader can reconstruct from that step's cited equations. The geometric construction, facts proved elsewhere and other deductions can supply missing information. The check covers only AR steps. The [step-level results](ar-steps.jsonl) preserve the transcribed premises and goals.

A second pass added only explicit angle and ratio equations from the original JGEX construction. This supplied sufficient additional premises for two angle steps and eight ratio steps. Each successful repair lists one inclusion-minimal supplement. The remaining 24 steps need evidence beyond the cited equations and these directly stated construction equations. We did not expand midpoint or circle theorems in this second pass. [Construction equations and source predicates](construction-equations.json)

For ratios, take logarithms of the positive segment lengths. An equality of ratios becomes a linear equation, so rational row rank tests implication exactly. For angles, give every named line a direction modulo π. Parallel lines differ by zero and perpendicular lines differ by π/2. The checker tests integer row-lattice membership, retaining the angle period and rational multiples of π. Halving an angle congruence could lose a branch. Reversing the endpoints gives the same undirected line and the same segment length. Other lines or lengths are identified only through explicitly listed equations. [Checker and supported notation](../../../bench/latvia/ar_audit.py)

## Comparison with official solutions

For each competition represented among the 20 wins, we selected its most recent winning year. This gave four problems from four competitions. The fifth case was selected separately because the merge correction recovered it. The comparison uses the solutions from the University of Latvia’s A. Liepa Correspondence Mathematics School and the archived Newclid constructions and transcripts. Grade, stage and problem number identify the source. They do not give a calibrated measure of how difficult the problem was for contestants.

**National, 2016–17, grade 11, problem 3.** The official proof draws RB and RC. Inscribed angles in the three circles give supplementary angles at R, so B, R and C lie on one line. The solver also uses inscribed angles. It derives parallel directions for BR and CR, then concludes collinearity since the lines contain R. Both use the same circle-angle idea. The formalization drops the restriction on the arc containing A. [Official solution, PDF p. 5](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/VOL/2010-2020/vol_67_uzd_atr.pdf#page=5) · [Formalization](../../../problems/latvia/geometry_translated/national/2016-17_67/grade11/p3.txt)

**Open, 2021–22, grade 9, problem 3.** The official proof draws AE and BD. Opposite sides AB and DE are parallel and equal, making ABDE a parallelogram on the convex branch. Thus AE = BD. Two angle equalities and that common length scale prove triangles BCD and EFA congruent. The formalization constructs E as the parallelogram vertex before search. The solver recognizes similarity of the same triangles and prints AE/BD = EF/BC as the sole premise of BC = EF. For example, 2/1 = 4/2 satisfies the printed ratio with EF ≠ BC. Restoring AE = BD gives EF/BC = 1 and establishes the conclusion. [Official solution, PDF p. 8](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/AMO/2020-2030/2022_AMO_uzd_atr.pdf#page=8) · [Formalization](../../../problems/latvia/geometry_translated/open/2021-22_47/grade09/p3.txt)

**Regional, 2021–22, grade 12, problem 3.** Both solutions aim to show that the angles subtended by AD at E and at the bisector intersection F (the solver's X) are equal. The official proof uses the base angles of isosceles triangles BAC and BCD, then the two angle bisectors. The solver's printed algebraic step cites only parallel directions from the diagonal incidences. Those equations place no restriction on AX or DX. The equality needs information from the original side lengths and bisectors. [Official solution, PDF p. 16](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/NOL/nov_72_2021_2022_uzd_atr.pdf#page=16) · [Formalization](../../../problems/latvia/geometry_translated/regional/2021-22_72/grade12/p3.txt)

**Preparatory, 2010–11, grade 9, problem 2.** The official solution names F, where median CE meets bisector AD. In triangle ACE the bisector is also an altitude, so AC = AE. As E bisects AB, this gives AB = 2AC. The formalization relabels the vertices and supplies a point L on the bisector line and the reflected point C₁ before search. The solver obtains parallel lines from two perpendiculars and invokes Thales' theorem twice. It reaches the equivalent goal BM = AB with M the midpoint of BC. The choice of helper points changes the method. [Official solution, PDF p. 3](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/SOL/2010-2020/so61_atr.pdf#page=3) · [Formalization](../../../problems/latvia/geometry_translated/school/2010-11_61/grade09/p2.txt)

**Additional recovered case · National, 2024–25, grade 9, problem 2.** In the first official solution G is the midpoint of CD. A midline gives a parallel and two congruent triangles establish that F bisects BE. The second solution compares areas. In the formalization, trisection of AB has already supplied the midpoint of AD. With this different midpoint the solver uses a midline and Thales' theorem. Both midpoint arguments work, and the choice of midpoint affects the proof. [Official solutions, PDF pp. 1–2](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/VOL/2020-2030/VOL_75_uzd_ATR_9_12_klase.pdf#page=1) · [Independent elementary proof and point labels](../README.md#recovered-grade-9-proof)

## Reproduce

Use the environment and resource limits in the [domain guide](../../../docs/domains.md), including Python hash seed 0. The original measurements used solver revision `c5ae501`. The revised solver sources match `eb03c75`. The runner alternates which condition runs first across the sorted selected IDs. Each result records its own elapsed time and resource outcome. Concurrent CPU work can affect time-limited runs.

```sh
PYTHONHASHSEED=0 python -m bench.latvia.paired_ar /path/to/paired-rerun
python -m bench.latvia.paired_results /path/to/original-scan /path/to/paired-rerun results/latvia-domains/paired-ar
PYTHONHASHSEED=0 python -m bench.latvia.ar_budget /path/to/paired-rerun results/latvia-domains/paired-ar/budget-180.json
python -m bench.publish
```

The [original AR-on records](../full-deduction.jsonl) are shared with the three-policy study. This directory contains the matching source measurements with [AR off](original-full_no_ar-deduction.jsonl), the revised [AR-on](revised-full-deduction.jsonl) and [AR-off](revised-full_no_ar-deduction.jsonl) records, the [selection and baseline digest](selection.json) and the [revised input hashes](revised-inputs.json).
