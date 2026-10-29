# Translating olympiad problems into Newclid syntax

A Newclid (JGEX) problem builds the figure one point at a time, then states the goal:

```
a b c = triangle a b c; h = orthocenter h a b c; d = reflect d h b c ? cyclic a b c d
└── free points ────┘  └── constructed points ───────────────────┘   └── goal ───┘
```

* Clauses are separated by `;`. Each clause is `new points = construction, construction`.
* A construction's first arguments are the new point(s), followed by points that already exist.
* One construction places a point on a locus (a line or a circle). Two constructions
  separated by `,` intersect two loci: `x = on_line x a b, on_circle x o a`.
* Point names are lowercase: `a`, `b`, `h`, `a1`, ...
* The goal comes after `?`. It is a predicate, or several separated by `,`.

## Step by step

1. **Choose the free points.** Usually a triangle (`a b c = triangle a b c`) or a
   circle with points on it (`o = free o; a = free a; b = on_circle b o a; ...`).
   Only use a special shape, such as `r_triangle`, `iso_triangle` or `isquare`,
   when the statement requires it.
2. **Build every other point in the order the statement introduces it.** A
   point can only use points defined before it.
3. **Put each condition into the construction of the point it defines.** "P on BC
   with AP ⟂ BC" becomes `p = foot p a b c`, or `p = on_line p b c, on_tline p a b c`.
4. **State the goal as a predicate** (table below).
5. **Run the numerical check** (below) before solving.

## Common constructions

| statement | construction |
|---|---|
| midpoint M of AB | `m = midpoint m a b` |
| foot of the perpendicular from A to BC | `d = foot d a b c` |
| orthocenter, circumcenter, incenter | `h = orthocenter h a b c`, `o = circle o a b c`, `i = incenter i a b c` |
| X on line AB | `on_line x a b` |
| X on the line through A perpendicular to BC | `on_tline x a b c` |
| X on the line through A parallel to BC | `on_pline x a b c` |
| X on the circle with center O through A | `on_circle x o a` |
| X on the circumcircle of ABC | `on_circum x a b c` |
| X on the circle with diameter AB | `on_dia x a b` |
| X on the perpendicular bisector of AB | `on_bline x a b` |
| intersection of lines AB and CD | `x = on_line x a b, on_line x c d` |
| reflection of A over line BC | `x = reflect x a b c` |
| reflection of A over point B | `x = mirror x a b` |
| X with ∠XAB = ∠EDC | `on_aline x a b c d e` |
| tangent from A to circle (O, B) | `x y = tangent x y a o b` |

All 88 constructions and the hypotheses each one adds are listed by:

```bash
.venv-newclid/bin/python -c "from newclid.jgex.constructions import ALL_JGEX_CONSTRUCTIONS as A; [print(d.name.value, *d.args) for d in A]"
```

## Goals

| statement | goal |
|---|---|
| A, B, C collinear | `coll a b c` |
| AB ∥ CD, AB ⟂ CD | `para a b c d`, `perp a b c d` |
| AB = CD | `cong a b c d` |
| A, B, C, D concyclic | `cyclic a b c d` |
| ∠(AB, CD) = ∠(EF, GH) | `eqangle a b c d e f g h` |
| AB/CD = EF/GH | `eqratio a b c d e f g h` |
| M is the midpoint of AB | `midp m a b` |
| triangles ABC and PQR are similar | `simtri a b c p q r` |

Angles are **directed angles between lines, taken mod π**. `eqangle a b c d e f g h`
means the angle from line AB to line CD equals the angle from line EF to line GH.
If a goal "fails" numerically, first try swapping the two lines on one side.

## Worked examples

Each one is in `problems/examples/`, and each passes the numerical check.

**1. "Let H be the orthocenter of triangle ABC. Prove that the reflection of H
over BC lies on the circumcircle."**
```
a b c = triangle a b c; h = orthocenter h a b c; d = reflect d h b c ? cyclic a b c d
```
The reflection gets its own name (`d`). "Lies on the circumcircle of ABC" becomes `cyclic a b c d`.

**2. "Prove that the midpoints of the sides of any quadrilateral form a parallelogram."**
```
a b c d = quadrangle a b c d; e = midpoint e a b; f = midpoint f b c; g = midpoint g c d; h = midpoint h d a ? para e f g h
```
"Parallelogram" is split into one checkable predicate. For the full statement,
add a second goal: `? para e f g h, para e h f g`.

**3. "The tangent at A to the circumcircle of ABC makes with AB an angle equal to ∠ACB."**
```
a b c = triangle a b c; o = circle o a b c; t = on_tline t a o a ? eqangle a t a b c a c b
```
The tangent at A is the line through A perpendicular to OA, so a second point T
on it is `on_tline t a o a`. The angle is written as directed angles between lines.

**4. "In a right triangle, the midpoint of the hypotenuse is equidistant from the vertices."**
```
a b c = r_triangle a b c; m = midpoint m b c ? cong m a m b
```
`r_triangle a b c` puts the right angle at A, so BC is the hypotenuse.

**A mistake the check catches** (`problems/examples/wrong_translation.txt`):
```
a b c = triangle a b c; h = on_line h b a, on_tline h c a b ? perp a h b c
```
The intended point is the orthocenter, but `on_line h b a` puts H on side AB
instead of on the altitude from B. The check reports
`'perp a h b c' fails in every drawing`.

## Numerical check

```bash
.venv-newclid/bin/python -m pipeline.check_figure -f problems/examples/varignon.txt
.venv-newclid/bin/python -m pipeline.check_figure -s "a b c = triangle a b c; ... ? ..." --seeds 10 --svg fig.svg
```

The check draws the figure with several random seeds, without requiring the goal
to hold, and evaluates the goal in each drawing:

| result | meaning |
|---|---|
| `OK goal holds in all N drawings` | the translation is consistent with a true statement |
| `fails in every drawing` | wrong construction, wrong argument order, or a wrong goal (try swapping the sides of an `eqangle`) |
| `fails in k of N drawings` | the figure depends on a choice, e.g. which intersection of a line and a circle, or the statement needs a condition (acute triangle, point inside a segment) |
| `figure could not be built` | the constructions contradict each other, or a point is used before it is defined |
| `two points coincide` | degenerate construction, e.g. the foot from a point already on the line |

`--svg` saves a drawing so you can compare it with the picture in the original statement.

## Solving a folder of problems

Put one problem per file in a folder: a `# description` line, then the problem line.
Then run:

```bash
.venv-newclid/bin/python -m pipeline.run_folder my_problems/ --config pipeline/configs/default.json --time 120 --memory 3000 --check
```

`--check` skips problems that fail the numerical check. The table shows solved,
time, peak memory, search depth, the tools used, and either the auxiliary
constructions or the failure reason. Full results go to
`my_problems/results_<config>.json`.
