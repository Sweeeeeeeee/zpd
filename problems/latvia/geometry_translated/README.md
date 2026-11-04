# Newclid translations of the Latvian geometry problems

Task 4.2. Empty for now.

Each translation goes at the same path as its problem in `../geometry/`, with
`.txt` in place of `.md`:

```
../geometry/national/2004-05_55/grade10/p4.md   ->   national/2004-05_55/grade10/p4.txt
```

Use the format from [docs/translation_guide.md](../../../docs/translation_guide.md):
header lines, then one Newclid problem line.

```
# source: latvia/national/2004-05_55/grade10/p4
# tags: circle, isosceles
o = free o; a = free a; b = on_circle b o a; ... ? cong d c c b
```

Then run the numerical check on each folder:

```bash
python -m pipeline.check_figure -f problems/latvia/geometry_translated/national/2004-05_55/grade10/p4.txt
python -m pipeline.run_folder problems/latvia/geometry_translated/national/2004-05_55/grade10 --check
```

Problems that Newclid cannot state (solid geometry, computing a length or an
angle, inequalities, constructions, "find all" questions) get no `.txt`. Add
their id to `untranslatable.csv` in this folder, with the reason.
