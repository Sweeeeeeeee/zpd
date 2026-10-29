# Geometry prover toolbox: DDAR + small transformer + heuristics

This is a small, CPU-friendly reimplementation of the AlphaGeometry idea. A
deductive engine (Newclid's DDAR) proves everything it can. When it gets stuck,
other tools propose auxiliary points (a transformer written from scratch, or
simple human heuristics), and DDAR tries again. Every part can be switched off
or swapped from JSON configs, including individual deduction rules.

| folder | what | step |
|---|---|---|
| `ddar/` | Newclid setup, example runner, rule toggling (`rule_config.py`), Newclid fixes | 1, 2 |
| `geo-lm/` | the transformer, its tokenizer, and the training script | 3, 5 |
| `datagen/` | 100k training examples subsampled from GenesisGeo | 4 |
| `pipeline/` | tools, search, `solve()`, figure check, folder runner | 6, 7, 8 |
| `docs/translation_guide.md` | how to write olympiad problems in Newclid syntax | 8 |
| `problems/examples/` | worked example problems | 8 |
| `tests/` | tests for config loading, each tool, and `solve()` | 9 |
| `present.md` | a guide for explaining the project to others | 10 |
| `bench/`, `results/` | problem collection, with every stored `solve()` result kept in git | 11 |

## Installation (CPU only, Linux, Python ≥ 3.11)

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
python -m pytest -q          # 39 tests, about 15 s
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
[docs/translation_guide.md](docs/translation_guide.md):

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

Each record holds:
* the full `solve()` result;
* the config name and a hash of its contents, including the DDAR rule file it
  uses and the model checkpoint's timestamp;
* the budget, the date and the git commit.

A combination that is already stored is skipped, unless you pass `--force`.
After running, commit `results/` to keep the history.

## Configs

**Pipeline** (`pipeline/configs/*.json`): which tools run, in what order, and the search limits.

```json
{
  "tools": {
    "ddar":        {"enabled": true,  "options": {"config": "ddar/configs/yuclid.json"}},
    "transformer": {"enabled": true,  "options": {"checkpoint": "geo-lm/runs/small/best.pt", "beam_size": 4}},
    "heuristics":  {"enabled": true,  "options": {"kinds": ["midpoint", "circumcenter", "foot"], "max_candidates": 8}}
  },
  "proposer_order": ["transformer", "heuristics"],
  "search": {"max_depth": 2, "branching": 8, "max_frontier": 6, "max_ddar_calls": 80, "time_limit": 0}
}
```

Provided configs:
* `ddar_only.json`, `heuristics_only.json`
* `default.json`, which needs a trained model
* `tiny_model.json`, which uses the smoke-test model

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
* Once `geo-lm/runs/small/best.pt` exists, `pipeline/configs/default.json`
  uses it.

## Known limitations

* Newclid 3.0.1's Python engine needed three runtime fixes (`ddar/patches.py`).
  It is also much slower than yuclid.
* The model speaks GenesisGeo's predicate format.
  * Its outputs are converted to Newclid constructions for `coll`, `perp`,
    `para`, `cong` and `cyclic`.
  * Proposals that use `eqangle` or `aconst` are dropped.
* The real model has not been trained yet; only the smoke-test checkpoint exists.

Details for each step are in `ddar/README.md`, `datagen/README.md`,
`pipeline/README.md` and `geo-lm/README.md`.
