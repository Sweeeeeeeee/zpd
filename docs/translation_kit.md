# Translation kit (task 7.5)

What the translating agents get, besides [translation_guide.md](translation_guide.md):
worked examples of the hard cases, the checks every translation must pass,
and the prompts of the four agents. The scheme is in [tasks.md](tasks.md), task 7.

## File format

One file per problem in `problems/latvia/geometry_translated/`, same path as
in `geometry/`, `.txt`:

```
# latvia/national/2024-25_75/grade09/p2
# dof: 2   (any triangle ABC: 2; D fixed by AD:DB = 2:1; E midpoint; F an intersection)
# notes: D is the trisection point nearer B
a b c = triangle a b c; e d = trisegment e d a b; m = midpoint m a c; f = on_line f b m, on_line f c d ? cong b f f m
```

`# dof:` is the number of free shape parameters **of the statement** (up to
similarity), counted from the Latvian text before translating, with the
reason. `python -m pipeline.dof <file>` compares it with the translation.

## Checks (all automatic)

| check | command | catches |
|---|---|---|
| the figure builds, the goal holds in every drawing | `python -m pipeline.check_figure -f <file> --seeds 6` | false goals, wrong branch of an intersection, wrong orientation |
| no hidden specialisation | `python -m pipeline.dof <file>` | a true but easier problem: general triangle made isosceles, a free point put on a special line, a missing condition |
| back-translation agrees | agents 3 and 4 below | a different problem that happens to be true |

"fails in some drawings" almost always means a construction has two
solutions and Newclid picked either one (example 1, 4); "fails in every
drawing" means a wrong goal or a wrong orientation.

## Worked examples (each checked: goal holds in every drawing)

**1. A fixed angle: orientation matters.** Square ABCD, E inside with
∠CBE = 15° and AE = ED; prove AED equilateral (`open/2024-25_50/grade10/p4`).
`s_angle` is a *directed angle between lines*, so a square drawn with either
orientation puts E inside or outside. Fix the orientation with `psquare` /
`nsquare` instead of `isquare`:

```
# dof: 0
a b = segment a b; c = nsquare c b a; d = psquare d a b; e = s_angle c b e 15o, on_bline e a d ? cong a e a d
```
With `isquare` the goal fails in 2 of 5 drawings; with the opposite
`psquare`/`nsquare` pair it fails in all of them (E outside the square).

**2. Replace a two-branch construction with a deterministic one.** Equilateral
ABC; D, E divide the outer semicircle on AB into three equal arcs; prove CD and
CE cut AB into three equal parts (`national/2021-22_72/grade10/p2`). "D on
the circle with ∠AMD = 60°" has two solutions (inside and outside). Instead:
D is the reflection over AB of the midpoint of AC (AMK is equilateral):

```
# dof: 0
a b c = ieq_triangle a b c; k = midpoint k a c; l = midpoint l b c; d = reflect d k a b; e = reflect e l a b; p = on_line p a b, on_line p c d; q = on_line q a b, on_line q c e ? cong a p p q; cong p q q b
```

**3. A ratio on a side.** D on AB with AD : DB = 2 : 1, median BE, F = BE ∩ CD;
prove BF = FE (`national/2024-25_75/grade09/p2`). `trisegment e d a b` gives
both trisection points; D is the one nearer B:

```
# dof: 2
a b c = triangle a b c; e d = trisegment e d a b; m = midpoint m a c; f = on_line f b m, on_line f c d ? cong b f f m
```

**4. Two circles, second intersections, a tangent.** Circles meet at M, N; K on
the first; KM, KN meet the second again at A, B; prove AB ∥ the tangent at K
(`regional/1995-96_46/grade11/p2`). "Parallel to the tangent at K" = "perpendicular
to the radius OK". `on_line a k m, on_circle a q m` picks the intersection other
than M; a drawing where that fails is reported as NOT BUILT and skipped:

```
# dof: 3   (two intersecting circles: 2; K on the first: 1)
o = free o; m = free m; n = on_circle n o m; q = on_bline q m n; k = on_circle k o m; a = on_line a k m, on_circle a q m; b = on_line b k n, on_circle b q m ? perp a b o k
```

**5. Squares outside a triangle, concurrency.** Squares BEFC and ACMN outside an
acute triangle; t1 through B ⟂ AE, t2 through A ⟂ BN, t3 through C ⟂ AB;
prove they concur (`regional/2002-03_53/grade11/p3`). Concurrency = intersect
two lines, prove the point is on the third. "Outside" = `psquare` / `nsquare`
with the orientation that the check confirms:

```
# dof: 2
a b c = acute_triangle a b c; e = psquare e b c; n = nsquare n a c; x = on_tline x b a e, on_tline x a b n ? perp c x a b
```

**6. Equal chords via circles.** Isosceles trapezoid ABCD with AB = BC = CD;
diagonals meet at O; prove the midpoints of AO and BC and the vertices C, D are
concyclic (`open/2003-04_31/grade11/p3`). Equal chords of one circle: each new
vertex is on the circumcircle and on the circle around the previous vertex:

```
# dof: 1
w = free w; a = free a; b = on_circle b w a; c = on_circle c w a, on_circle c b a; d = on_circle d w a, on_circle d c b; o = on_line o a c, on_line o b d; m = midpoint m a o; n = midpoint n b c ? cyclic m n c d
```

**Not statable (sort as `prove_other`, do not translate):** a hypothesis that
is a sum of lengths with no construction (BE + DF = EF), "iff" with an
algebraic condition (R² + r² = d²), areas, perimeters, sums of segments.
"AD = AB + AC" *is* constructible (lay off AC beyond B, then a circle), but say
so in `# notes:`.

## Agent prompts

**Agent A / B (translator, stronger model; A and B do not see each other).**
> Translate the Latvian problem in `<file>` into Newclid syntax, following
> docs/translation_guide.md and the worked examples in docs/translation_kit.md.
> First count the statement's free shape parameters and write `# dof: N (reasons)`.
> Write the file `<out>` in the format of the kit. Run
> `python -m pipeline.check_figure -f <out> --seeds 6` and `python -m pipeline.dof <out>`;
> fix the translation until both pass, or write `# untranslatable: <reason>`.
> Do not simplify the problem: no special shapes the statement does not require.

**Agent C (back-translation, cheap model; sees only the Newclid file).**
> Write in plain English what this Newclid problem says: which points are free,
> how each other point is constructed, and what is to be proved. Do not guess
> what problem it came from.

**Agent D (comparison, cheap model).**
> Here are a Latvian olympiad problem and an English description of a
> formalisation. Are the hypotheses the same, and is the goal the same? Answer
> `same` or `different: <what differs>`. Special cases, missing conditions and
> extra conditions count as different.

A problem is accepted automatically when A and B both pass the checks, D says
`same` for both, and the solver gives the same result for both; otherwise it
goes to the review queue (`status.csv`).
