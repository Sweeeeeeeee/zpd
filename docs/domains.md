# Step 6: Geometry domains and the easy setting

A **domain** is a set of theorems: a DDAR rule list, with algebraic reasoning
(AR: angle and ratio chasing) on or off. A problem has an **easy solution** in
a domain if the pipeline proves it with that domain's rules, at most one
auxiliary point, 60 s and 2 GB.

There are three domains, each with and without AR:

| domain | DDAR config | rules | what it allows |
|---|---|---|---|
| `full` | `ddar/configs/domains/full.json` | 70 | Newclid's 58 default rules plus 12 more (below). The reference: every other domain is a subset of it. |
| `circles` | `ddar/configs/domains/circles.json` | 29 | Circles and inscribed angles: cyclic quadrilaterals, inscribed and central angles, tangents, chords, isosceles triangles, and midpoint and collinearity bookkeeping. No similar or congruent triangles, no Thales ratios, no length equations. |
| `no_similarity` | `ddar/configs/domains/no_similarity.json` | 59 | `full` without similar triangles: the AA, SSS and SAS tests (r34, r35, r60–r63, r68, r69), their properties (r52, r53) and Thales I (r07), which concludes a similarity. |
| `*_no_ar` | `ddar/configs/domains/<domain>_no_ar.json` | same | The same rules without AR. Every fact must then come from a rule. |

Each domain has a pipeline config of the same name in
`pipeline/configs/domains/`, so results are stored under the domain's name:
`full`, `circles_no_ar`, and so on.

## Why `full` is more than Newclid's default set

Newclid's default set drops 29 rules that AR usually makes redundant. Some of
them are the circle theorems themselves: r13/r14 (isosceles triangle), r15/r16
(tangent and inscribed angle), r17/r18 (central and inscribed angle), r21,
r24, r55, r72 and r73. Without them, the default set cannot prove the
tangent–chord angle (`problems/examples/tangent_chord.txt`), while the smaller
circles domain can. A domain that is "smaller" yet proves more would make the
comparison meaningless. So `full` adds those 11 rules, plus r06 (the midline
theorem, needed for Varignon). Then `circles ⊂ full` and
`no_similarity = full − similarity` both hold as sets of rules.

The circles rules are r03, r04, r13–r21, r24, r28, r49–r51, r54–r56, r58,
r59, r72–r74, r80–r82, r91 and r92 (descriptions in [rules.md](rules.md)).
Loading the config prints what the circles domain cannot do: it cannot use or
prove `simtri`/`contri` facts or `lequation`/`aequation` goals. That is the
point of the domain.

## The easy setting

Every config in `pipeline/configs/domains/` uses the same search and budget:

```json
"tools": {"ddar": ..., "transformer": {"enabled": false},
          "heuristics": {"enabled": true, "options": {"kinds": ["midpoint", "circumcenter", "foot"], "max_candidates": 8}}},
"search": {"max_depth": 1, "branching": 8, "max_frontier": 8, "max_ddar_calls": 20},
"budget": {"time_s": 60, "memory_mb": 2048, "cpu_s": 0}
```

* **Depth at most 1.** DDAR runs on the problem as stated. If that fails, it
  runs once more for each proposed auxiliary point (up to 8).
* **Auxiliary points** come from the human heuristics only, until the
  transformer is trained (task 8). To compare sources of points, copy a config
  and switch `transformer` on.
* **Budget.** The `budget` block is new: a pipeline config can now carry its
  own limits. `python -m bench run` and `python -m pipeline.solve` use it
  unless `--time`, `--memory` or `--cpu` are given. A config without a
  `budget` block keeps the old defaults (60 s, 2048 MB, no CPU limit).

## Engine

Domains need the Python engine, because yuclid has its rules compiled in and
cannot switch any off. The Python engine is slower: about 0.1–5 s per DDAR
run on the examples, against 0.01 s for yuclid. Two more Newclid 3.0.1 bugs
showed up with these rule sets. Both are handled in `ddar/engine.py`, again
without changing Newclid (fixes 1–3 are in [ddar.md](ddar.md)):

4. AR facts are cached without their premises. Writing the proof then fails
   with `Could not find premises for AR deduction`, even though the goal was
   proven. `complete_ar_traceback` fills the premises in when the proof
   looks them up.
5. Rules with a congruent-triangle premise (r77, r78) crash the rule matcher
   (`Unknown predicate: CONTRI_REFLECT`) as soon as a `contri` fact exists.
   The mapper now matches those rules itself, with each stored fact under the
   6 relabellings of both triangles.

## Running a scan

```bash
python -m bench run problems/examples --config pipeline/configs/domains/*.json
python -m bench table problems/examples
```

## First results

**The 5 example problems** (`problems/examples/`, easy setting; stored in `results/examples/`):

| problem | full | full_no_ar | circles | circles_no_ar | no_similarity | no_similarity_no_ar |
|---|---|---|---|---|---|---|
| orthocenter_reflection | yes 5.4 s | no (time) | yes 2.7 s | no (depth) | yes 5.9 s | no (time) |
| right_triangle_median | yes 2.0 s | yes 2.4 s | yes 2.5 s | yes 2.2 s | yes 2.3 s | yes 2.1 s |
| tangent_chord | yes 2.4 s | yes 2.2 s | yes 2.4 s | yes 2.1 s | yes 2.5 s | yes 2.0 s |
| varignon | yes 2.0 s | no (time) | no (time) | no (depth) | yes 2.4 s | no (time) |
| wrong_translation | bad figure | bad figure | bad figure | bad figure | bad figure | bad figure |
| **solved** | 4/5 | 2/5 | 3/5 | 2/5 | 4/5 | 2/5 |

The domains separate the problems as expected. Varignon needs the midline
theorem, which is not a circle theorem. The orthocenter reflection and
Varignon both need angle chasing, so they fail without AR. All solved
problems are solved at depth 0, with no auxiliary point. The times include
about 2 s of process start-up.

**Newclid's 74 engine examples** (DDAR alone, 60 s each; tables in `ddar/results/examples_python_*.txt`):

| rules | solved | crashed | unsolved |
|---|---|---|---|
| Newclid default, Python engine, step 1 (fix 1 only) | 37 | 37 | 0 |
| Newclid default, Python engine, fixes 1–5 | 50 | 10 | 14 |
| `full` | 54 | 10 | 10 |
| `no_similarity` | 54 | 10 | 10 |
| `circles` | 46 | 8 | 20 |
| yuclid (for reference) | 60 | 7 | 7 |

No problem solved by the old Python run is lost. `full` loses one problem
that the default rules solve (`ar_example_paper_angle_chasing`): with 12 more
rules it hits the 60 s limit. The remaining crashes are the 4 intended
unbuildable figures (`breaking_cc_*`), 3–4 problems that hit another Newclid
bug (`unhashable type: 'LineMerge'` when a proof step is a line merge; not
fixed), `acompute_test` (a goal type the Python AR cannot justify), and
timeouts.
