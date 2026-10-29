# How to understand and present this project

## The one-minute version

> Olympiad geometry proofs often hinge on a single clever extra point, such as a
> midpoint, a foot of an altitude, or a reflection. AlphaGeometry (DeepMind, 2024)
> showed that a language model can suggest those points while a strict logic
> engine does the actual proving. We rebuilt that setup at a size that runs on a
> laptop. Every ingredient can be switched on or off: individual geometry
> theorems, algebraic reasoning, the model, and the human heuristics. That lets
> us measure what each "piece of knowledge" contributes, which is the
> starting point for comparing curricula.

## Why it is interesting

* **Proofs are checkable.** DDAR only applies known theorems, so every proof it
  outputs is correct. Neither the model nor the heuristics can make a false
  claim; they can only suggest points.
* **Knowledge is modular.** A "curriculum" can be modelled as a set of rules
  (theorems a student knows), whether AR (algebra) is allowed, and which kinds
  of constructions are considered. All three are JSON switches here.
* **It is small.** It runs on a CPU, the data is public, and the model is
  written from scratch, so results are reproducible without a datacenter.

## The picture to draw on the whiteboard

```mermaid
flowchart LR
    P[Problem in Newclid syntax] --> D1[DDAR: apply rules + AR until nothing new]
    D1 -->|goal proven| S[Proof]
    D1 -->|stuck| T{Ask tools for an extra point}
    T --> M[Transformer: beam search]
    T --> H[Heuristics: midpoints, circumcenters, feet]
    M --> A[Add the point]
    H --> A
    A --> D2[DDAR again]
    D2 -->|proven| S
    D2 -->|stuck, depth left| T
```

The search goes breadth-first and has hard limits: depth (how many extra points
in a row), branching (how many suggestions per step), the number of DDAR calls,
and time, memory and CPU for the whole solve. There is no random guessing.

## The parts, in the order they were built

| # | Part | One sentence | Where |
|---|---|---|---|
| 1 | DDAR | Newclid, the open-source AlphaGeometry engine, runs on CPU. Its C++ core (yuclid) solves 60/74 examples in 0.01–0.25 s. | `ddar/README.md` |
| 2 | Rule toggling | A JSON list of enabled rules plus an AR switch, warnings when a rule set can't use some hypotheses, and a side-by-side comparison script. | `ddar/rule_config.py`, `ddar/compare_rules.py` |
| 3 | Transformer | A from-scratch GPT-style decoder with a geometry tokenizer, greedy and beam decoding, and save/load. | `geo-lm/` |
| 4 | Data | 100k problems that need an extra point, subsampled from GenesisGeo's 21.8M (public, Apache-2.0). | `datagen/` |
| 5 | Training | Configurable trainer with checkpoints, resume, logging and held-out evaluation; checked end to end on a tiny run. | `geo-lm/geo_lm/train.py` |
| 6 | Toolbox | One `Tool` interface, three tools (DDAR, model, heuristics), and the DDAR → propose → DDAR search. | `pipeline/` |
| 7 | `solve()` | One call that returns a result with proof, time, memory, depth, rules, tools and failure reason, with limits enforced from a separate process. | `pipeline/solve.py` |
| 8 | Translation | A guide for writing olympiad problems by hand, a numerical check that catches wrong translations, and a runner that prints a results table. | `docs/translation_guide.md` |
| 9 | Docs and tests | README and 64 tests (about 15 s). | `README.md`, `tests/` |
| 11 | Problem store | Problems with metadata, plus every `solve()` result for each config and budget, kept in git and shown as a table. | `bench/`, `results/` |

## Key ideas, explained simply

* **DDAR** = *Deductive Database + Algebraic Reasoning*.
  * The deductive database repeatedly applies about 60 theorems ("if these two
    triangles are similar, these angles are equal") until no new fact appears.
  * Algebraic reasoning treats angles and ratios as linear equations and
    solves them ("angle chasing").
* **Auxiliary construction**: a point that is not in the statement but makes
  the proof possible. DDAR cannot invent points. That is the model's job.
* **Rule**: one named theorem, e.g. `r43` is the orthocenter theorem. Turning a
  rule off is like a student who doesn't know that theorem.
* **The numerical check**: every figure is also drawn with real coordinates.
  Claims are verified on the drawing, which catches translation mistakes
  before any proving starts.

## A 5-minute live demo

Run from the repo root with `.venv-newclid` activated. Each command takes seconds.

```bash
# 1. DDAR alone proves a classic: the reflection of the orthocenter lies on the circumcircle.
python -m pipeline.solve --config pipeline/configs/ddar_only.json \
  -s "a b c = triangle a b c; h = orthocenter h a b c; d = reflect d h b c ? cyclic a b c d"

# 2. Knowledge matters: the same orthocenter problem with and without the orthocenter theorem / AR.
python -m ddar.compare_rules -p orthocenter_consequence_aux ddar/configs/*.json

# 3. Translation mistakes are caught before solving.
python -m pipeline.check_figure -f problems/examples/wrong_translation.txt

# 4. A whole folder, with a results table (time, memory, depth, tools).
python -m pipeline.run_folder problems/examples --config pipeline/configs/heuristics_only.json --check
```

What to point out:
1. The proof is printed step by step, and each step names the rule or the
   algebra that justifies it.
2. Without `r43` or without AR, the same problem becomes unsolvable. Rule sets
   change what can be proved.
3. The wrong translation is reported as `fails in every drawing`.
4. The table reports measurable quantities for each problem. Those are the
   numbers to compare curricula with.

## Numbers worth quoting

* Newclid examples: 60/74 solved by the fast engine. All 7 unsolved ones need
  theorems that engine doesn't include.
* Data: 98,008 training and 1,992 validation examples, 100 tokens at the
  median; split by figure so the test figures are never seen in training.
* Model: about 11M parameters, 76-token vocabulary, 512-token context. A tiny
  0.1M version trains in about 1 minute on a CPU.
* `solve()` overhead: about 2 s and 180 MB per problem, mostly Python start-up.

## Honest limitations (say them before someone asks)

* **The real model is not trained yet.** On this 2-core CPU it would take
  about 14 h (one command, resumable). Until then, the extra points come from
  the heuristics.
* **The model speaks GenesisGeo's language.** It describes points by
  properties (`coll`, `perp`, ...). These are translated into Newclid
  constructions, and suggestions using angle equalities are currently dropped.
* **Two engines.** The fast C++ engine has its theorems compiled in. Rule
  toggling uses Newclid's Python engine, which needed three bug fixes and is
  much slower.
* **Benchmarks are small so far.** The goal is controlled comparisons, not
  state-of-the-art scores (AlphaGeometry and GenesisGeo solve most IMO
  geometry problems with far bigger models).

## How this connects to the research question

The plan (`apraksts.txt`) is to evaluate *educational programs*: which
knowledge, given in which order, lets a solver handle which problems. Here that
becomes concrete:
* a **program** = a DDAR config (rules, AR), a set of enabled tools and heuristic
  kinds, and later, models trained on chosen subsets of the data;
* a **test** = a folder of translated problems run with `pipeline.run_folder`;
* a **score** = solved count plus time, depth and rules used, taken from the
  results JSON.

The next steps are:
1. Train the model.
2. Translate the 10 benchmark problems.
3. Sweep rule subsets, for example "only the original AlphaGeometry rules r00–r42"
   against the defaults, and compare the tables.

## Likely questions

* **"Is the proof trustworthy?"** Yes. Only DDAR proves, and every step cites a
  rule or a linear combination of known facts.
* **"Why not DeepMind's code?"** It depends on the unmaintained Meliad
  framework. Newclid is a maintained open-source rewrite.
* **"Why your own transformer?"** It gives full control over size and data,
  and uses no pretrained knowledge, which matters when we want to measure what
  the training material contributes.
* **"Where does the data come from?"** GenesisGeo's public set, generated and
  checked with a Newclid-based engine. We only subsample and convert it.
