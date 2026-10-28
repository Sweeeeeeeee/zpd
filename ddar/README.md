# Step 1: Running Newclid DDAR on CPU

Newclid 3.0.1 works on CPU. Use it with its C++ engine **yuclid**, though: the
pure-Python engine in this release is broken.

## Setup

```bash
PYTHON=/usr/local/python/3.13.8/bin/python3 ddar/setup_newclid.sh   # Python >= 3.11 required
source .venv-newclid/bin/activate         # needed: yuclid is found through PATH
python -m ddar.run_examples               # 74 example problems, yuclid engine
python -m ddar.run_examples --config ddar/configs/default.json   # pure-Python DDARN + SymPy AR
python -m ddar.run_examples --file third_party/Newclid/newclid/problems_datasets/imo.txt
```

Run these from the repo root.

Each problem runs in its own subprocess with a timeout (`--timeout`, default 60 s).
Results are saved to `ddar/results/`.

Install notes:
* `pip install newclid` alone does not import: `pyyaml` is missing from the
  package metadata, so install it separately.
* `pip install newclid[yuclid]` installs a prebuilt `yuclid` binary
  (`py-yuclid` 3.0.0, manylinux, cp313). Nothing is compiled.
* `py_yuclid` finds the binary with `shutil.which("yuclid")`, then
  `$UV_PROJECT_ENVIRONMENT/bin`, then a hardcoded `../../../.venv/bin`. If the venv
  is not activated, `import newclid` still works, but the yuclid import fails.

## Results on `examples.txt` (74 problems, seed 0, 2-core CPU)

| engine | solved | crashed | unsolved | typical time |
|---|---|---|---|---|
| yuclid (default) | **60** | 7 | 7 | 0.01–0.25 s per problem |
| python (DDARN + SymPy AR, with only fix 1 below) | 37 | 37 | 0 | ≤ 0.15 s when it works |

Full tables: `results/examples_yuclid.txt` and `results/examples_python.txt`.

**Yuclid failures:**
* 4 problems (`breaking_cc_*`) fail on both engines. Their figures cannot be built
  numerically after 100 attempts. These are intended negative tests.
* 3 problems ask for a goal that yuclid does not accept: `npara`, `ncoll` and
  `acompute` give `Unknown statement`.
* 7 are unsolved: `pappus`, the 3 `menelaus_*` problems, `pyt_*` (×2) and
  `test_l2const`. They need rules that are only in the Python set (r44 Pappus,
  r81+ Menelaus) or Pythagoras/equation handling that the adapter switches off
  (see the flags below).

**Python-engine bugs in 3.0.1** (also present on GitHub `main`, commit `ac65507`):
1. `predicate_from_construction` builds `diff` with exactly 2 points, but rules
   r34–r37, r52, r53 and r60–r63 have `diff A B C` premises. Every problem that
   reaches those rules crashes.
2. `ar_predicates.enumerate_lconsts` crashes with `cannot unpack non-iterable Symbol`
   as soon as ratio chasing finds a constant length. This causes most of the
   remaining crashes.
3. The r52/r53 conclusion builder creates degenerate `simtri e a d e a d`, which
   pydantic then rejects.

All three are fixed at runtime in `ddar/patches.py` (step 2). The step 1 table
above was measured with only fix 1 applied. This code path looks unmaintained
since the move to yuclid, but it is the only engine that can switch rules off,
so step 2 uses it.

## How rules are loaded

There are two separate rule sets, and only the Python one is configurable.

**Python engine** (`newclid/all_rules.py`, `newclid/rule.py`)
* Each rule is a Python constant `Rule(id="r34", description=..., premises_txt=(...),
  conclusions_txt=(...))`. There are 87 rules in `ALL_RULES`.
* The default set is hardcoded as
  `DEFAULT_RULES = ALL_RULES − DEACTIVATED_RULES − TRIAGE_NO_RULE_NEEDED − TRIAGE_LEAVE_RULE_OUT`.
  That gives **58 rules**. r57 Pythagoras is deactivated, and 29 rules are dropped
  as redundant with AR or with other rules.
* `GeometricSolverBuilder` sorts them by id. You can replace them with
  `.with_rules(list)` or `.with_rules_from_file(path)`, which accepts `.yaml`
  (list of Rule dicts) or `.txt` (lines of the form
  `"<id> <description>"` / `"premises => conclusions"`).
* `DDARN` (breadth-first search) applies every rule in list order at each level,
  then runs the deductors (AR). It stops when the goal is proven or a level adds
  nothing new. There is no limit on depth or time.

**Yuclid engine** (`py_yuclid/yuclid_adapter.py`, C++ binary)
* The rules are compiled into the binary. The Python side only maps their ids
  back with `YUCLID_RULES`, a hardcoded set of **37 rules**.
* The two sets overlap but differ:
  * Rules in yuclid but not in Python's default set: r13, r14, r55, r72, r73.
  * Rules in Python's default set but not in yuclid: r07, r20, r25–r27, r36, r37,
    r44, r58, r59, r64–r67, r70, r79, r81, r83–r90, r92.
* **`GeometricSolverBuilder.with_rules(...)` has no effect with yuclid.**
  `FollowDeductions.step()` ignores its `rules` argument. Yuclid saturates the
  problem once in a subprocess, and Python replays the deductions that lead to
  the goal (`deductions_for_goal`), or all of them when there is no goal.
* The binary has no option for choosing rules (`yuclid --help`).

## How AR is loaded

* **Python:** `PythonDefault(use_sympy_ar=True)` adds a `SympyARDeductor`. It holds
  an angle table and a ratio table, which are Gaussian elimination over SymPy
  `Fraction`s. Each table has 4 hardcoded enumerators (aconst / perp / para /
  eqangle and lconst / cong / rconst / eqratio). `use_sympy_ar=False` disables AR
  completely. This is the only on/off switch.
* **Yuclid:** AR runs inside the binary. The adapter always passes these flags:
  `--mode ddar --disable-ar-dist --disable-ar-squared --disable-eqn-statements --disable-ar-sin`.
  As a result, angle chasing and ratio chasing are always on, while length
  chasing, squared-length chasing, sine-based AR and equation statements are
  always off. None of these settings are exposed in Python.

## Other hardcoded values

| What | Where | Value |
|---|---|---|
| Numerical tolerance | `numerical/__init__.py` | `ATOM = 1e-7`, `REL_TOL = 1e-3` |
| Fraction denominator cap | `tools.py` | `MAX_DENOMINATOR = 1_000_000` |
| Figure sampling: retries per clause | `JGEXProblemBuilder(max_attempts_per_clause=5)` | 5 |
| Figure sampling: retries until goal holds numerically | `JGEXProblemBuilder.build(max_attempts_to_satisfy_goals_numerically=100)` | 100 |
| Engine choice | `api._load_api_default()` | yuclid if `py_yuclid` imports, otherwise Python. Selected silently |
| Yuclid AR flags | `YuclidAdapter._run_yuclid` | see above |
| Rule order | `GeometricSolverBuilder.__init__` | sorted by id |
| DDARN limits | `agent/ddarn.py` | none: runs until saturation |
| Constructions ("defs.txt") | `jgex/constructions/*.py` | **There is no defs.txt in 3.x.** All 88 constructions are Python `JGEXDefinition` objects, which can be swapped with `JGEXProblemBuilder.with_defs(...)` |
| Predicates | `predicates/_index.py` | 33 predicate types (`coll`, `cong`, `eqangle`, `simtri`, ...) |
| RNG | `JGEXProblemBuilder(rng=...)` | random coordinates; pass a seed for reproducible runs |

## Step 2: Rule toggling

A DDAR config is a small JSON file (`ddar/configs/*.json`):

```json
{
  "name": "no_similarity",
  "engine": "python",
  "enabled_rules": "default",
  "disabled_rules": ["r34", "r35", "r52", "r53", "r60", "r61", "r62", "r63", "r68", "r69"],
  "ar": true
}
```

| key | meaning |
|---|---|
| `enabled_rules` | list of rule ids, or `"default"` (Newclid's 58) or `"all"` (all 87) |
| `disabled_rules` | optional; removed from `enabled_rules` afterwards |
| `ar` | angle and ratio chasing on or off |
| `engine` | `"python"` (honours every setting) or `"yuclid"` (stock rules and AR only, otherwise the config is rejected) |

Rules are filtered at load time (`DDARConfig.rules()` is passed to
`GeometricSolverBuilder.with_rules`), so the engine never sees disabled rules.
Unknown rule ids are an error.

**Warnings.** `load_config` compares the config with what it would give without
disabling anything (Newclid's defaults plus any extra rules it lists), and warns
(`RuleCoverageWarning`) when:
* a predicate that constructions put into hypotheses (e.g. `simtri` from the
  `simtri` construction, `midp` from `midpoint`) is no longer a premise of any
  enabled rule, so those hypotheses become dead weight;
* a predicate can no longer be concluded by any enabled rule, so goals of that
  type can only be proven if they are hypotheses;
* AR is off.

Predicates handled by AR (`coll para perp eqangle aconst cong eqratio rconst lconst`,
when AR is on) or checked numerically (`diff ncoll sameclock ...`) are not
reported. The check is static: it says a predicate cannot be used, not that a
particular problem becomes unsolvable.

**Comparing configs on one problem:**

```bash
python -m ddar.compare_rules -p orthocenter_consequence_aux ddar/configs/*.json
python -m ddar.compare_rules -s "a b c = triangle a b c; h = on_tline h b a c, on_tline h c a b ? perp a h b c" ddar/configs/*.json
```

```
config                 rules  AR solved   time  rules in proof / rules fired
alphageometry_r00_r42     38  on     no   3.23  proof: -
                                               fired: AR:anglex246 r34x1
default                   58  on    yes   1.12  proof: AR:anglex1 r43x1
                                               fired: AR:anglex246 r34x1 r43x1
no_ar                     58 off     no   0.04  proof: -
                                               fired: r43x1 r82x6
no_orthocenter            57  on     no   3.69  proof: -
                                               fired: AR:anglex246 r34x1 r52x3
no_similarity             48  on    yes   0.99  proof: AR:anglex1 r43x1
                                               fired: AR:anglex246 r43x1
yuclid                    58  on    yes   0.01  proof: AR:anglex1 r43x1
                                               fired: AR:anglex1 r43x1
```

"fired" counts every new fact a rule produced during the search; "proof" counts
the steps of the final proof. Each config runs in its own subprocess
(`--timeout`, default 60 s). For `yuclid`, the rules column shows the configured
58, but the binary actually uses its own 37 rules.

Code: `rule_config.py` (config, filtering, warnings), `patches.py` (Newclid
fixes), `runner.py` (solve one problem, count fired rules, subprocess wrapper),
`compare_rules.py` (the script above).

## What this means for later steps

* **Rule-toggling experiments** use the patched Python engine (done in step 2).
  It is much slower than yuclid (1.1 s vs 0.01 s on the example above), so large runs with
  stock rules should still use yuclid.
* **Step 4 (data):** the Newclid repo includes `ncdgen`, a generator that uses
  `yuclid --mode datagen` and has an option to emit only sub-problems that need
  an auxiliary construction (`emit_only_double_checked_aux_subproblems`). This
  looks directly reusable.
