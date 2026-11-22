# IMO contestant scores and deduction within the same contest

Six editions had at least two distinct official problems among the 29 local IMO benchmark formalizations. Each of the six supplied two problems. Matching by year and official number gave 12 problems and 13 solver records. Students in each pair competed in the same edition under the same scoring scale. Every participant is included in each mean, including those who earned zero points on that problem.

| IMO | Contestants | First problem, mean and local outcome | Second problem, mean and local outcome | Official score tables |
|---|---:|---|---|---|
| 2004 | 486 | P1 · 4.60 · proved | P5 · 2.51 · proved | [Teams](https://www.imo-official.org/results/team/year/2004/) · [Contestants](https://www.imo-official.org/results/individual/year/2004/) |
| 2008 | 535 | P1 · 4.98 · exhausted | P6 · 0.26 · exhausted | [Teams](https://www.imo-official.org/results/team/year/2008/) · [Contestants](https://www.imo-official.org/results/individual/year/2008/) |
| 2010 | 516 | P2 · 2.58 · exhausted | P4 · 5.34 · proved | [Teams](https://www.imo-official.org/results/team/year/2010/) · [Contestants](https://www.imo-official.org/results/individual/year/2010/) |
| 2012 | 547 | P1 · 5.63 · proved | P5 · 1.66 · exhausted | [Teams](https://www.imo-official.org/results/team/year/2012/) · [Contestants](https://www.imo-official.org/results/individual/year/2012/) |
| 2015 | 577 | P3 · 0.65 · exhausted | P4 · 4.79 · proved | [Teams](https://www.imo-official.org/results/team/year/2015/) · [Contestants](https://www.imo-official.org/results/individual/year/2015/) |
| 2019 | 621 | P2 · 2.40 · exhausted | P6 · 0.40 · exhausted | [Teams](https://www.imo-official.org/results/team/year/2019/) · [Contestants](https://www.imo-official.org/results/individual/year/2019/) |

In 2010, 2012 and 2015 the baseline proved one problem and exhausted deduction on the other. Contestants earned a higher average on the proved problem in all three editions. In 2004 the baseline proved both problems, and in 2008 and 2019 it exhausted its rules on both. The 2008 pair spans 4.98 and 0.26 points while giving the same solver outcome. These results describe six pairs selected by benchmark coverage. Three pairs distinguish the solver outcomes. Different geometry topics and the choice of formalization can affect the comparison.

## Population and scoring

The [29 local formalizations](problems.txt) represent 27 distinct official year–problem combinations. The labels `2002_p2a` and `2002_p2b` map to one official item, and so do `2008_p1a` and `2008_p1b`. The 2002 edition has only one distinct available item, so it contributes no pair. Both local runs for 2008 P1 exhausted deduction. Missing 2000 P1 contributes no observation. The paired analysis uses the [local seed-0 Yuclid deduction records](ddar_only.jsonl) with a 60-second search limit and a 2,048 MiB memory budget. A proved entry means that deduction solved every available encoding of the item.

The [official aggregates](official-paired-scores.json) contain six problem totals per edition from the team table and independent eight-bin score counts from its individual table. On 22 November 2026 we checked all 593 team rows and 3,282 contestant rows across the six editions. For every row, the six problem scores summed to the official total. The item sums agreed across the two tables for all 36 year–problem cells. Every histogram sums to the participant count in the edition record. For example, 30 of 577 contestants earned full marks on 2015 P3 and 351 earned full marks on P4.

## Reproduce

Run `python -m bench.imo_student_scores` from the repository root. It joins the baseline by official problem ID, checks the eligible years and validates the team totals against the independently collected individual distributions.

To check the original tables, export the seven numeric columns (total, P1, P2, P3, P4, P5, P6) from both official tables for the selected year as whitespace-delimited text. Keep every data row, with no header. For example, run `python -m bench.imo_student_scores --check-tables 2015 team.tsv individual.tsv`. [Comparison and source-checking code](../../../bench/imo_student_scores.py)
