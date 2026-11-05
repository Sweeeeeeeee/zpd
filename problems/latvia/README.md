# Latvian olympiad problems

Every problem from the olympiad archive of the NMS (Neklātienes matemātikas
skola, [nms.lu.lv](https://www.nms.lu.lv/arhivs-un-materali/uzdevumu-arhivs/olimpiazu-uzdevumu-arhivs/)),
from 1973/74 to 2025/26, plus the Latvian team selection tests for Baltic Way
and the IMO
([international archive](https://www.nms.lu.lv/arhivs-un-materali/uzdevumu-arhivs/starptautisko-sacensibu-uzdevumu-arhivs/)).
There is one file per problem, in Latvian as published. The problems are not
translated into Newclid yet (that is task 7.5).

| folder | what |
|---|---|
| `all/` | every problem: algebra, number theory, combinatorics, geometry |
| `geometry/` | the geometry problems only (plane and solid), same paths as in `all/` |
| `geometry_translated/` | Newclid translations of `geometry/` problems, same paths, `.txt` (task 7.5) |
| `index.csv` | one row per problem: id, path, competition, season, grade, number, geometry tag, review flags, source |
| `geometry_overrides.csv` | hand corrections of the geometry tag; kept across rebuilds |

## Layout

```
all/<competition>/<season>_<olympiad number>/[day2/ | extra/]grade<NN>/p<k>.md
all/tst/<year>_<bw|imo>/[day<N>/]p<k>.md
```

| competition | Latvian name | grades | seasons | problems | geometry |
|---|---|---|---|---|---|
| `national` | Valsts olimpiāde: 3. posms (3. kārta) of the Latvian olympiad | 8/9–12 | 1975/76–2024/25 | 1275 | 375 |
| `regional` | Novada (earlier rajona) olimpiāde: 2. posms | 5–12 | 1974/75–2025/26 | 1847 | 425 |
| `school` | Skolas olimpiāde: 1. posms (earlier "sagatavošanās olimpiāde") | 4/5–12 | 1987/88–2019/20 | 1125 | 227 |
| `open` | Atklātā matemātikas olimpiāde (AMO) | 5–12 | 1973/74–2025/26 | 1956 | 432 |
| `tst` | Atlases sacensības: Baltic Way and IMO selection tests | – | 2021–2025 | 130 | 40 |
| | | | | **6333** | **1499** |

Example: `all/national/2004-05_55/grade10/p4.md` is problem 4 for grade 10 at
the 55th national olympiad (season 2004/05).

* `day2/` is the second day of the national final (since the 65th olympiad, one
  problem set shared by grades 9–12). `extra/` is the "papildsacensības par
  vietu republikas izlasē" round held after the national olympiad in the 1970s–90s.
* `grade08-09/` is a problem set shared by two grades.
* In the selection tests, problems are numbered across the days (Baltic Way
  TST: 1–8 on day 1, 9–16 on day 2). The IMO TST restarts at 1 on its last day.
* International competitions themselves (IMO, EGMO, Baltic Way) are not
  Latvian problems and are left out.

## Problem file

Markdown with a YAML header, followed by the statement:

```
---
id: latvia/national/2004-05_55/grade10/p4
competition: national
title: "Latvijas 55. matemātikas olimpiāde, 3. posms (valsts olimpiāde)"
olympiad: 55
year: 2005
season: "2004/05"
day:
grade: "10"
problem: "4"                    # number as printed ("26.3", "7.1", "4")
geometry: plane                 # plane | solid | no
geometry_keywords: [apvilkt, centru, diametr, riņķ, taisne, trijstūr, vienādsān]
needs_review: []                # e.g. [formula missing, has a figure]
source: https://www.nms.lu.lv/.../55repol_uzd.doc      # file the problem list was read from
originals: [.../55repol_uzd.doc, .../55repol_uzd.pdf]  # every copy of the problems
solutions: [.../55repol_atr.doc, .../55repol_atr.pdf]  # official solutions
---

Uz riņķa līnijas w ar centru O izvēlēti divi punkti A un B tā, ka AB nav diametrs. ...
```

`year` is the calendar year the round was most likely held. `season` is the
school year the archive lists it under, and it is authoritative.

## Text quality: what to check

The statements are extracted automatically from Word and PDF files written
over 50 years. When both a `.doc` and a `.pdf` copy exist, each statement is
taken from whichever one reads better. Known limits:

* **Formulas.** Old Word files store formulas as Equation Editor pictures,
  which cannot be read. They appear as `[formula]`. PDFs keep the formula text
  but often split it over several lines. `needs_review` marks such problems
  (1393 of 6333; 282 of the geometry ones). Open the `originals` link to read
  the formula.
* **Figures** are not copied. `needs_review: [has a figure]` marks statements
  that refer to a drawing ("skat. 1. zīm.").
* **Missing files.** Two archive files are scans with no text layer and are
  not included: the 9–12 grade AMO problems of 1997/98 (`amo25uzd_9-12kl.pdf`)
  and the 1995/96 school olympiad (`so46_uzd.pdf`). The 2023 Baltic Way TST
  day files use a broken font, so their statements come from the solutions file.
* **Geometry tag.** The tag comes from keywords (trijstūris, leņķis, riņķa
  līnija, ∠, ...), minus words that point to a combinatorics board (rūtiņas,
  krāsot, spēlētājs, ...). It catches nearly all geometry. Some combinatorial
  geometry (colouring the vertices of a polygon, cutting a board) is tagged
  too. To correct a tag, add a line `id,geometry` to `geometry_overrides.csv`
  and rebuild.

## Rebuilding

```bash
sudo apt-get install poppler-utils libreoffice-writer-nogui   # pdftotext, and soffice for .doc files
python -m bench.latvia fetch     # downloads the ~710 archive files (240 MB) to ~/.cache/zpd-nms ($NMS_CACHE)
python -m bench.latvia build     # extracts, splits, tags, rewrites all/, geometry/, index.csv
python -m bench.latvia report    # counts, and grades with an unusual number of problems
```

`build` rewrites `all/` and `geometry/` from scratch. It never touches
`geometry_translated/`. The code is in `bench/latvia/`: `catalog.py` maps
archive files to olympiads, `extract.py` turns files into text, `split.py`
cuts the text into problems, `topics.py` tags geometry, and `build.py` runs
the steps. The tests are in `tests/test_latvia.py`.

AoPS (`artofproblemsolving.com/community/c305478_latvia_contests`) refuses
automated downloads, so it is not a source here. Its Latvian collections come
from the same olympiads, and the NMS archive is their original source.
