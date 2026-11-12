# Proposer models: comparison plan

Status 2026-11-12. The scanner looks for **fast solutions in one domain**:
DDAR with that domain's rules, at most **one** auxiliary point, a small time
and memory budget. A proposer model is only useful if it finds that one point
quickly. So models are compared on that task, not on IMO-level search.

## What is compared

Everything except the proposer stays fixed: DDAR (yuclid), the domain's rules,
search depth 1 (one aux point), beam 4, the same problems, the same budget.

| Group | Model | Size | Source | Status |
|---|---|---|---|---|
| baseline | DDAR alone | – | – | done (`ddar_only`) |
| baseline | heuristics (midpoint, circumcenter, foot) | – | `pipeline/tools.py` | done |
| light, ours | `mini` (1600 steps) | 2.1M | `geo-lm/runs/mini` | done |
| light, ours | `mini_long` (9000 steps) | 2.1M | `geo-lm/runs/mini_long` | done |
| light, ours | `mid` (9000 steps) | 5.1M | `geo-lm/runs/mid` | done 11-12 (exact@4 53.5%, JGEX +5/26, IMO 2015 P3, IMO-aux 6/101) |
| light, general | SmolLM2-135M-Instruct, few-shot | 0.135B | `models/hf/` | downloaded, not probed |
| light, general | SmolLM2-360M-Instruct, few-shot | 0.36B | `models/hf/` | downloaded, not probed |
| control | Qwen3-0.6B-Base, few-shot (GenesisGeo before fine-tuning) | 0.6B | `models/hf/` | downloaded, not probed |
| big, specialist | GenesisGeo (Qwen3-0.6B fine-tuned on the same data) | 0.6B | `models/hf/GenesisGeo` | prompt `genesisgeo` checked 11-10; comma-less output fixed and stop at `;` (11-12), speed not re-measured |
| big, specialist | AlphaGeometry (AG1) LM | 152M | `models/ag1/` (own env `.venv-ag1`) | works 11-12, verified on the README example; too slow and memory-tight for this Codespace (below) |
| big, general | Qwen2.5-1.5B-Instruct, few-shot | 1.5B | `models/hf/` | downloaded, not probed |

The list with paths and sources is `models/registry.json`. `bench/hf_probe.py`
checks one HF model on N held-out problems (load time, s/call, peak memory,
exact match, translatable) before it goes into the comparison.

All Hugging Face models go through one adapter, `pipeline/hf_tool.py`
(`HFLMTool`, prompt styles `genesisgeo`, `genesisgeo_x00`, `fewshot`).
Which GenesisGeo prompt style the published checkpoint expects is to be
measured on a few held-out problems (their repo has moved to a newer format).

## AlphaGeometry (AG1)

AG1 runs in its own environment because it pins Python 3.10, JAX 0.4.6,
TF 2.13 and meliad. `pipeline/ag1_tool.py` starts `pipeline/ag1_server.py` in
that env once per process and talks to it over stdin/stdout. The server is in
the same process group, so the solve watchdog counts its memory and kills it.

Setup (done 11-12, ~4 GB disk):
- `third_party/alphageometry` (git main 6777cb5) and meliad pinned to
  `e8af054`, the 2022 version AG1 was released with (meliad's 2025 commit
  is a different model).
- `pipeline/setup_ag1.sh`: conda Python 3.10.9 plus AG1's `requirements.txt`
  with `--require-hashes`. `jaxlib==0.4.6` is no longer on PyPI; the same
  wheel (hash in requirements.txt) comes from
  `storage.googleapis.com/jax-releases/nocuda/`. Also `setuptools==69.5.1`,
  because `pkg_resources`, which tensorflow_hub needs, was removed later.
- Checkpoint from the official Drive folder (gdown 4.7.1 is refused; Drive's
  `drive.usercontent.google.com/download?id=...&confirm=t` works). Its sha256
  `02d6728b...` equals the HF mirror `Wauplin/alphageometry`.
- `pipeline/ag1_slim_ckpt.py` writes `params_only.npz` (the 608 MB of
  weights, without optimizer state). A full meliad restore peaked at 3.85 GB
  and the server was killed (SIGTERM, see STATE); weights-only peaks at ~2.7 GB.

Adapter details: AG1's `matplotlib.use('TkAgg')` is made a no-op (headless);
the jitted step donates its state, so the server keeps the state each step
returns; decoding is capped at 32 tokens (AG1: 512; one aux point is ~12).
AG1's `Graph.build_problem` retries forever if the goal is numerically false;
the solve watchdog is the guard.

Verified: on AG1's `orthocenter` example with 2 beams the tool returns the
README's two proposals in the same order (`e = on_line e a c, on_line e b d`
-1.110 vs README -1.102; `e = eqdistance e c a b, eqdistance e b a c`).

On this Codespace (2 cores): load ~40 s, first call ~75 s (JIT), then ~23 s
per call with beam 2, ~2.7 GB RSS; the server was still SIGTERMed in 2 of 5
runs. That is over the 60 s budget, so AG1 is for a bigger machine (Kaggle).

## Fitting the models to the requirement

- **Depth 1**: `search.max_depth = 1` in every comparison config.
- **Budget**: 60 s after loading and 2 GB per problem for light models; big
  models get 3-4 GB (a 0.6B model in bfloat16 is ~1.2 GB) and are reported
  separately. 60 s, not 30: domains need Newclid's Python DDAR engine, 10-100x
  slower than yuclid (a 30 s test on 11-10 timed out even without a model).
- **Load time** (decided 11-10): each problem still runs in a fresh child
  process (reliable limits), but the time limit starts when the tools are
  loaded. Loading has its own cap (`Budget.load_s`, 120 s) and is reported as
  `load_time` / `load` in results. A scanner loads a model once and solves
  many problems, so solve time after loading is the fair measure.
- **No silent fallback**: comparison configs set `"strict_tools": true`, so a
  missing model is an error, not a run of DDAR alone.
- **CPU only here**: big models on Kaggle (free GPU) or on a small subset.
- **Memory next to training**: never load a big model while training runs
  (on 11-10 that got the training killed).

## Problems

Not IMO. In order:
1. A fixed 60-problem JGEX sample (`bench/compare_problems.txt`): the 26
   that yuclid DDAR fails on plus 34 spread over the rest. Per domain
   (full, no_similarity, circles), DDAR alone first, then each proposer only
   on that domain's DDAR failures.
2. `problems/examples/`.
3. The Latvian pilot batch (task 7.4), when translated: the real target.

Output: one table, model x domain: solved with one aux point, median solve
time, median load time, peak memory (`results/compare/table.md`).

```bash
python bench/compare_configs.py                  # (re)writes pipeline/configs/compare/<domain>/<proposer>.json
bench/run_compare.sh                             # light: heuristics mini mini_long mid, all 3 domains
bench/run_compare.sh genesisgeo smollm2_360m     # chosen proposers
python bench/compare_table.py                    # results/compare/table.md
```

Cost estimate (not yet measured without training running): DDAR alone on 60
problems x 3 domains, up to 60 s each; then each proposer on the failures.
Run with `claude/job.sh`, never next to training.

## Folder restructure (after the mid run finishes; it uses the current paths)

| now | after |
|---|---|
| `geo-lm/` (code, configs, scripts, tests) | `models/geo_lm/` |
| `geo-lm/runs/<name>/` | `models/checkpoints/<name>/` |
| downloaded HF models | `models/hf/<name>/` (gitignored) |
| model list scattered over configs and docs | `models/registry.json`: name, size, source, pipeline config |
| `pipeline/configs/*_model.json` | `pipeline/configs/proposers/<name>.json` |

Needs: `pip install -e` from the new path, checkpoint paths in configs, docs
links, `setup.sh`, tests. About 30 min, then the full test suite.
