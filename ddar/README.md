# Step 1: Running Newclid DDAR on CPU

Newclid 3.0.1 works on CPU. Use it with its C++ engine **yuclid**, though: the
pure-Python engine in this release is broken.

## Setup

```bash
PYTHON=/usr/local/python/3.13.8/bin/python3 ddar/setup_newclid.sh   # Python >= 3.11 required
source .venv-newclid/bin/activate         # needed: yuclid is found through PATH
python ddar/run_examples.py               # 74 example problems, yuclid engine
python ddar/run_examples.py --engine python            # pure-Python DDARN + SymPy AR
python ddar/run_examples.py --file third_party/Newclid/newclid/problems_datasets/imo.txt
```

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
| python (DDARN + SymPy AR, with the `diff` fix below) | 37 | 37 | 0 | ≤ 0.15 s when it works |

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
   reaches those rules crashes. `run_examples.py` patches this at runtime
   (`--no-fix` disables the patch).
2. `ar_predicates.enumerate_lconsts` crashes with `cannot unpack non-iterable Symbol`
   as soon as ratio chasing finds a constant length. This causes most of the
   remaining crashes.
3. The r52/r53 conclusion builder creates degenerate `simtri e a d e a d`, which
   pydantic then rejects.

This code path looks unmaintained since the move to yuclid. **For the rest of the
project, use yuclid as DDAR.** The Python engine is only useful as a reference.

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

## What this means for later steps

* **Step 2 (rule toggling):** with yuclid, rules cannot be switched off inside the
  search. The workable approach is to run yuclid in saturate mode (no goal, so
  `all_deductions` is returned), drop every deduction made by a disabled rule or
  by AR, and propagate the removal. Then check whether the goal is still
  derivable from what remains. This is exact for "which facts follow without
  rule X", because yuclid records the premises of each deduction. The other
  option is the Python engine with all three bugs fixed, which supports true
  in-search toggling, but it is slower and less trusted.
* The "defs.txt predicate" check in step 2 becomes: compare the predicates that
  the 88 construction definitions produce with the premises and conclusions of
  each rule.
* **Step 4 (data):** the Newclid repo includes `ncdgen`, a generator that uses
  `yuclid --mode datagen` and has an option to emit only sub-problems that need
  an auxiliary construction (`emit_only_double_checked_aux_subproblems`). This
  looks directly reusable.
