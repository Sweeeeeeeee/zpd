# Sorting check (task 7.2c), 2026-11-12

The user delegated the check to Claude. Claude read 60 problems in full (Latvian
text) against the agents' categories:

| sample | what | result |
|---|---|---|
| 20 random (`check_sample.csv`, seed 20261112) | all categories | 19 / 20 right; 1 wrong: `regional/2009-10_60/grade09/p2` marked `prove`, should be `prove_other` (an "iff" with R² + r² = d²) |
| 20 random `prove` (seed 7) | are they really statable? | 17 clearly right; 2 borderline: `national/1984-85_35/grade08/p2` (four equal circles, needs the figure, has `[formula]`), `open/1982-83_10/grade08/p2` (heptagon with equal angles is regular: statable only with an awkward construction); 1 wrong: `tst/2025_bw/day2/p9` (hypothesis BE + DF = EF is not a ruler-and-compass construction) |
| 20 random `prove_other` (seed 7) | statable problems missed? | 20 / 20 right (areas, sums of lengths, perimeters, vectors, existence) |

So: about 5% wrong overall (1 of 20; 95% interval ~1-24%). The errors lean one
way: the agents are generous with `prove` (about 1 in 7 is not cleanly
statable), and no statable problem was found among `prove_other`. That is the
safe direction: a `prove` problem that cannot be stated is caught at
translation (task 7.5: the construction fails or the free-point check flags it);
a statable problem sorted out would be lost silently.

Data problems seen on the way, for task 7.3:
- a split error: `national/2008-09_59/grade12/p5` also contains the text of
  problems 2 and 3 of that set;
- duplicates across years: `open/2004-05_32/grade10/p2` and
  `open/2005-06_33/grade10/p2` are the same problem.
The working-set script should drop duplicates and flag statements that contain
several problems.
