# Drawing checks for the Latvian translations

All 65 accepted translations were drawn on 64 fresh seeds each (32–95). The figure builder saw only the setup. After each successful construction, the checker evaluated every goal and measured the minimum distance between named points.

| Outcome | Drawings |
|---|---:|
| Attempted | 4,160 |
| Built and satisfied every goal | 3,940 |
| Could not be built | 220 |
| Built with two points closer than 0.000001 | 0 |
| Built and failed a goal | 0 |

Every problem produced at least 34 passing drawings. The 220 construction failures occurred across 38 problems. Each record gives the frozen translation hash and the seeds for each exception. The six-problem source review used seeds 0–31 and separately checked the original hypotheses and goals. Finite drawings test sampled configurations. Translation fidelity also depends on the match to the source, including its segment, arc and nondegeneracy conditions. [All 65 records](fresh-drawings.json) · [Six-problem source review](../../problems/latvia/geometry_translated/REVIEW.md#findings-for-the-six-selected-translations)

## Why the two-circle construction failed most often

In national problem 49.17 (1998–99, grade 12), two circles meet at A and B. M must lie inside segment AB and differ from its midpoint. The two chords through M perpendicular to the lines O₁M and O₂M form the diagonals of a rectangle. The official proof uses intersecting chords to show that each of the four half-chords has length √(MA × MB). The two diagonals are distinct diameters of a common circle. [Official statement, p. 3](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/VOL/1990-2000/49repol_uzd.pdf#page=3) · [Official solution, pp. 6–7](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Arhivs/Olimpiades/VOL/1990-2000/49repol_atr.pdf#page=6)

The frozen translation samples M on the entire line AB. A sampled M outside the common chord is outside both circles. A line through that M perpendicular to the radius line misses the corresponding circle. We replayed the setup through the placement of M and measured its directed position along AB. On seeds 32–95 all 30 failed drawings placed M outside the segment. All 34 interior placements built successfully. [Frozen construction](../../problems/latvia/geometry_translated/national/1998-99_49/grade12/p2.txt)

We tested a one-clause replacement, `m = between_bound m a b`, then evaluated it on 64 further seeds. The replacement supplies the segment-interior condition. The formalization still lacks an explicit exclusion of the midpoint. The original benchmark uses its published translation.

| Seeds | Original passed / attempted | Segment-bounded passed / attempted |
|---|---:|---:|
| 32–95, where the issue was identified | 34 / 64 | 56 / 64 |
| 96–159, follow-up | 32 / 64 | 62 / 64 |

Every built figure in both blocks met all three encoded goals. In the follow-up block, 30 of the 32 original construction failures had M outside AB. The other two had M inside, and the builder rejected nearby points. The segment-bounded construction had two failures on that block, both rejected for nearby points. [Matched outcomes and segment positions for all 128 seeds](segment-study.json)

With the revised solver, both translations reached the 60-second limit in full-domain deduction with algebraic reasoning. The change improved the construction success rate. The proof search still reached its time budget in both cases. [Deduction measurements](segment-deduction.json)

## Official item scores for two grade 9 problems

Maruta Avotiņa and Agnese Šuste published the aggregate grade 9 scores for the 2015–16 national final and open olympiad. We matched the problem statements on pages 55 and 58 to the frozen translations and used the mean points per problem, including those who left the problem unattempted. The book reports full-mark and unattempted percentages rounded to whole percentages. [Official publication, pp. 147–148](https://www.nms.lu.lv/fileadmin/user_upload/lu_portal/projekti/nms.lu.lv/Gramatas/Uzd_krajumi/Mat_Sac_4-9_15-16_2016.pdf#page=147)

| Same season and grade | Students | Mean / 10 | Full marks | Unattempted | Rank by mean among the five problems |
|---|---:|---:|---:|---:|---:|
| National final, problem 2 | 81 | 3.92 | 21% | 12% | 2nd highest |
| Open olympiad, problem 3 | 395 | 5.69 | 16% | 5% | Highest |

The original solver proved the national final problem and encountered a line-merge error on the open problem. The revised solver proved the national problem again. Its separate 60-second retest of the open problem timed out. These two contests drew different student populations. Two problems cannot establish a relationship between contestant scores and solver difficulty. [Transcribed aggregate scores](official-scores.json) · [Matched national run](../latvia-domains/paired-ar/revised-full-deduction.jsonl) · [Open problem retest](grade9-open-retest.json)

## Reproduce

From the repository root with the project environment active, run:

```sh
export PYTHONHASHSEED=0
python -m bench.latvia.fresh_drawings /tmp/latvia-fresh.json
python -m bench.latvia.segment_study /tmp/latvia-segment.json
cmp /tmp/latvia-fresh.json results/latvia-audit/fresh-drawings.json
cmp /tmp/latvia-segment.json results/latvia-audit/segment-study.json
python -m bench.latvia.scan_plan /tmp/latvia-configs
python -m bench.latvia.segment_study /tmp/latvia-segment-proofs.json --deduction-config /tmp/latvia-configs/full-deduction.json
```
