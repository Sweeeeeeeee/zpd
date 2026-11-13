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

Also: the 10% audit of the auto-accepted ones (pick ~6 at random from status.csv).

Bug found: 6 problems fail to build under every domain config (TypeError: unhashable type 'LineMerge'),
while ddar_only works (e.g. national/2024-25_75/grade09/p2) - to fix before the scan.
