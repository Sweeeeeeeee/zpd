# Olympiad geometry scanner: easy solutions in one geometry domain

This tool scans a folder of olympiad geometry problems and finds the ones with
an easy solution in a chosen geometry domain. A domain is a set of theorems,
with or without algebraic reasoning. An easy solution uses only those theorems
and at most one auxiliary point, within a small time and memory budget. For
each problem, the tool stores the proof, the key auxiliary point, the rules
used, and the resources used. The project description is in
[apraksts.md](apraksts.md).

Under the hood it is a small, CPU-friendly reimplementation of the
AlphaGeometry idea. A deductive engine (Newclid's DDAR) proves everything it
can. When it gets stuck, other tools propose auxiliary points (a transformer
written from scratch, or simple human heuristics), and DDAR tries again. Every
part can be switched off or swapped from JSON configs, including individual
deduction rules.

| folder | what | task ([tasks.md](tasks.md)) |
|---|---|---|
| `ddar/` | Newclid setup, example runner, rule toggling (`rule_config.py`), solver construction (`engine.py`) | 1 |
| `geo-lm/` | the transformer, its tokenizer, training script and evaluation (`scripts/eval_aux.py`) | 2, 8 |
| `datagen/` | 100k training examples subsampled from GenesisGeo | 2 |
| `pipeline/` | tools, search, `solve()`, figure check, folder runner | 3 |
| `ddar/configs/domains/`, `pipeline/configs/domains/` | geometry domains (rule sets, with and without AR) in the easy setting ([domains.md](domains.md)); `pipeline/configs/domains_transformer/` adds the transformer | 6, 8 |
| `docs/` | all documentation (this file, one file per part, references) | all |
| `problems/examples/` | worked example problems | 4 |
| `problems/latvia/` | all Latvian olympiad problems from the NMS archive, the geometry subset, and its translations ([README](../problems/latvia/README.md)); built by `bench/latvia/` | 7 |
| `tests/` | tests for config loading, each tool, `solve()`, domains and the Latvian import | 5 |
| `bench/`, `results/` | problem store and sweeps, with every stored `solve()` result kept in git | 4, 9 |
| `zpd_darbs/` | the written ZPD paper: LaTeX template after the guidelines, preliminary version, figure scripts ([README](../zpd_darbs/README.md)) | 12 |

## Installation (CPU only, Linux, Python ≥ 3.11)

In a new Codespace this happens automatically (`.devcontainer/` runs
`setup.sh`); elsewhere run `bash setup.sh` once. It does the steps below,
unpacks the training split from `data/genesisgeo/*.txt.gz`, installs TeX Live
and runs the tests. By hand:

```bash
PYTHON=python3.13 ddar/setup_newclid.sh       # .venv-newclid with newclid[yuclid] 3.0.1 + pyyaml,
                                              # and the Newclid repo in third_party/ (example problems)
.venv-newclid/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv-newclid/bin/pip install -e geo-lm pyarrow pytest
source .venv-newclid/bin/activate             # every command below runs from the repo root
```

Nothing is compiled: yuclid, Newclid's C++ engine, comes as a prebuilt wheel. A
GPU is optional and only used for training.

```bash
python -m pytest -q          # 85 tests (project + model), about 30 s
```

## Solve a problem

```bash
python -m pipeline.solve --config pipeline/configs/heuristics_only.json --time 60 --memory 2000 \
    -s "a b c = triangle a b c; h = orthocenter h a b c; d = reflect d h b c ? cyclic a b c d"
```

```python
from pipeline.solve import Budget, solve
r = solve(problem_text, "pipeline/configs/default.json", Budget(time_s=60, memory_mb=2000, cpu_s=0))
r.solved, r.proof, r.wall_time, r.peak_memory_mb, r.depth, r.rules_fired, r.tools_used, r.failure_reason
```

`solve()` runs the search in a child process. A watchdog kills the whole
process tree when the wall time, memory (RSS) or CPU time goes over the budget.
The failure reason then says which limit was hit.

For a folder of problems, one per `*.txt` file, see
[translation_guide.md](translation_guide.md):

```bash
python -m pipeline.check_figure -f problems/examples/varignon.txt     # numerical check of a translation
python -m pipeline.run_folder problems/examples --config pipeline/configs/default.json --check
```

## Problem collection and stored results (`bench/`)

Problems live in `problems/<set>/<name>.txt`. Each file has optional header
lines (`# description`, `# source: ...`, `# tags: ...`) followed by the
problem line. Each problem's `solve()` results are stored in
`results/<set>/<name>.json`, and that folder is committed to GitHub.

```bash
python -m bench run problems/examples --config pipeline/configs/ddar_only.json pipeline/configs/heuristics_only.json --time 60
python -m bench table problems/examples        # latest result per problem and config
python -m bench show problems/examples/varignon
python -m bench list problems/examples
```

Each problem file keeps one record per config and budget, with:
* **settings:** the enabled tools and their order, the DDAR engine, rule list
  and AR switch, the model and heuristic options, and the search limits;
* **resources:** available (time, memory, CPU budget) and used (wall time,
  peak memory, CPU time, DDAR calls);
* **outcome:** solved, failure reason, depth, auxiliary points, tools used,
  rules in the proof, rules fired, and the proof text.

Nothing about the particular run (date, commit, machine) is stored. A
combination that is already stored is skipped; `--force` replaces it. After
running, commit `results/`.

## Configs

**Pipeline** (`pipeline/configs/*.json`): which tools run, in what order, and the search limits.

```json
{
  "tools": {
    "ddar":        {"enabled": true,  "options": {"config": "ddar/configs/yuclid.json"}},
    "transformer": {"enabled": true,  "options": {"checkpoint": "geo-lm/runs/mini_long/best.pt", "beam_size": 4}},
    "heuristics":  {"enabled": true,  "options": {"kinds": ["midpoint", "circumcenter", "foot"], "max_candidates": 8}}
  },
  "proposer_order": ["transformer", "heuristics"],
  "search": {"max_depth": 2, "branching": 8, "max_frontier": 6, "max_ddar_calls": 80, "time_limit": 0}
}
```

Provided configs:
* `ddar_only.json`, `heuristics_only.json`
* `default.json`: heuristics + `mini_long` (the best model)
* `mini_model.json`, `mini_long_model.json`: the model without heuristics
  (`runs/mini`, 1600 steps; `runs/mini_long`, 9000 steps), both in git
* `quick_model.json`, `tiny_model.json`: need `runs/quick` (200 steps) or the
  smoke-test `runs/tiny`, which are not in git; retrain to use them

**DDAR** (`ddar/configs/*.json`): which rules are on, and whether AR is on.

```json
{"name": "no_orthocenter", "engine": "python", "enabled_rules": "default", "disabled_rules": ["r43"], "ar": true}
```

**Training** (`geo-lm/configs/train_*.json`): see "How to train" below.

## How to disable a rule

1. Copy a DDAR config and list the rule in `disabled_rules`, or give an explicit
   `enabled_rules` list. Rule ids and descriptions are in
   `.venv-newclid/lib/python3.13/site-packages/newclid/all_rules.py`.
2. Use `"engine": "python"`. Rules are compiled into the yuclid engine, so it
   only accepts the stock set.
3. Point the pipeline's `ddar` tool at the new config:
   `"options": {"config": "ddar/configs/my_rules.json"}`.
4. Loading the config warns if the remaining rules can no longer use hypotheses
   that constructions produce, or can no longer prove some predicate. To compare
   rule sets on one problem:

```bash
python -m ddar.compare_rules -p orthocenter_consequence_aux ddar/configs/*.json
```

## How to add a tool

```python
# my_tools.py
from pipeline.tools import AuxConstruction, Tool

class ReflectionTool(Tool):
    name = "reflections"
    def __init__(self, max_candidates: int = 4):
        super().__init__(max_candidates=max_candidates)
    def run(self, state):                      # state: pipeline.tools.ProofState
        if state.problem_setup is None:        # DDAR has not drawn this state yet
            return None
        return [AuxConstruction(("x = mirror x a b",), self.name)]
```

Then register it in a pipeline config and add its name to `proposer_order`:

```json
"reflections": {"enabled": true, "class": "my_tools:ReflectionTool", "options": {"max_candidates": 4}}
```

To replace a built-in tool, set `class` on its entry.

## How to train

```bash
python -m datagen.genesisgeo --size 100000                          # data: data/genesisgeo/{train,val}.txt
                                                                    # (already in git as .txt.gz; setup.sh unpacks it)
cd geo-lm
python -m geo_lm.train --config configs/train_tiny.json             # 1-minute end-to-end check
python -m geo_lm.train --config configs/train_small.json            # ~11M params
python -m geo_lm.train --config configs/train_small.json --max_steps 5000 --batch_size 64 --lr 5e-4
```

* Every setting can be overridden on the command line.
* Checkpoints are saved to `geo-lm/runs/<name>/` as `last.pt` and `best.pt`,
  and a stopped run resumes when you rerun the same command.
* Each evaluation prints validation loss and exact-match accuracy.
* On the 2-core CPU used here, the small model runs at about 2.6 s per step,
  so 20k steps take about 14 h. A modest GPU does it in well under an hour.
* `pipeline/configs/default.json` uses `geo-lm/runs/mini_long/best.pt`
  (the best model, 9000 steps). The planned `small` run was never trained.

## Known limitations

* Newclid 3.0.1's Python engine has bugs. Three are handled in `ddar/engine.py`
  (without modifying Newclid); others remain (see [ddar.md](ddar.md)). It is
  also much slower than yuclid.
* The model speaks GenesisGeo's predicate format.
  * Its outputs are converted to Newclid constructions for `coll`, `perp`,
    `para`, `cong` and `cyclic`.
  * Proposals that use `eqangle` or `aconst` are dropped.
* The full model has not been trained yet. The 2.1M-parameter checkpoints
  `runs/mini` (1600 steps) and `runs/mini_long` (9000 steps, val loss 0.27) are in git (25 MB each, force-added past `geo-lm/.gitignore`);
  other runs, such as the 134 MB `runs/quick`, are not.
* A Codespace stops after its idle timeout (counted from your last input, not
  from running jobs), and the timeout is fixed when the Codespace is created.
  Long training belongs on Kaggle or in several resumed sessions.
* The figure for each solve is drawn with one fixed seed (the `seed` option of
  the `ddar` tool, default 0). Use `pipeline.check_figure` to test several
  drawings.
* `pipeline/configs/default.json` needs `geo-lm/runs/mini_long/best.pt`
  (committed). Without it the transformer tool is switched off with a warning.

## Documentation

All documents are in `docs/`:

| file | content |
|---|---|
| [README.md](README.md) | this overview |
| [ddar.md](ddar.md) | task 1: Newclid on CPU, how rules and AR load, rule toggling, engine fixes |
| [rules.md](rules.md) | every rule with premises and conclusions, and where rules are stored |
| [geo-lm.md](geo-lm.md) | task 2: the transformer, tokenizer and training |
| [datagen.md](datagen.md) | task 2: the GenesisGeo training data |
| [pipeline.md](pipeline.md) | task 3: tools, search and `solve()` |
| [translation_guide.md](translation_guide.md) | task 4: writing problems in Newclid syntax |
| [domains.md](domains.md) | task 6: the geometry domains and the easy setting |
| [rezultati.md](rezultati.md) | current results in Latvian: domains, auxiliary point sources, transformer training and evaluation |
| [atsauces.md](atsauces.md) | references |
| [apraksts.md](apraksts.md), [tasks.md](tasks.md) | project description (Latvian) and task list |
| [../problems/latvia/README.md](../problems/latvia/README.md) | task 7: the Latvian olympiad problems |
| [../zpd_darbs/README.md](../zpd_darbs/README.md) | task 12: the written ZPD paper (LaTeX template, preliminary version, figures) |
