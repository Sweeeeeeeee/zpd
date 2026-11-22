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

## Audit sample

Six of the 57 translations accepted directly by the automated checks were selected before reviewing their content. The sampling order is the ascending SHA-256 digest of the UTF-8 string `zpd-20261122-audit/` followed by the full problem ID from status.csv. The first six IDs form this audit. The eight acceptances with recorded Claude decisions fall outside this sampling pool. The audit is pending. For each pair, record any constructor points absent from the original, any omitted nondegeneracy or segment condition, and whether both directions of the claim are represented. Search depth starts after the formalization has supplied its points. For example, the 2021–22 national grade 11 problem 2 translation supplies E and F to encode a midpoint constraint before the solver starts.

| Original problem | Construction to check |
|---|---|
| [national/2021-22_72/grade11/p2](../geometry/national/2021-22_72/grade11/p2.md) | [Accepted construction](national/2021-22_72/grade11/p2.txt) |
| [regional/1987-88_38/grade07/p2](../geometry/regional/1987-88_38/grade07/p2.md) | [Accepted construction](regional/1987-88_38/grade07/p2.txt) |
| [national/2008-09_59/grade10/p4](../geometry/national/2008-09_59/grade10/p4.md) | [Accepted construction](national/2008-09_59/grade10/p4.txt) |
| [school/2007-08_58/grade11/p3](../geometry/school/2007-08_58/grade11/p3.md) | [Accepted construction](school/2007-08_58/grade11/p3.txt) |
| [tst/2025_bw/day2/p11](../geometry/tst/2025_bw/day2/p11.md) | [Accepted construction](tst/2025_bw/day2/p11.txt) |
| [regional/2015-16_66/grade11/p3](../geometry/regional/2015-16_66/grade11/p3.md) | [Accepted construction](regional/2015-16_66/grade11/p3.txt) |
