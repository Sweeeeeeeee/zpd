# Proposer models: comparison plan

Status 2026-11-10. The scanner looks for **fast solutions in one domain**:
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
| light, ours | `mid` (7500 steps) | 5.1M | `geo-lm/runs/mid` | done 11-10 (exact@4 52%, JGEX +6/26, IMO-aux 5/101) |
| light, general | SmolLM2-360M-Instruct, few-shot | 0.36B | Hugging Face | planned |
| big, specialist | GenesisGeo (Qwen3-0.6B fine-tuned on the same data) | 0.6B | `ZJUVAI/GenesisGeo`, downloaded to `models/hf/` | adapter written; prompt `genesisgeo` checked 11-10, ~40 s per call on CPU |
| big, general | Qwen2.5-1.5B-Instruct, few-shot | 1.5B | Hugging Face | optional |

All Hugging Face models go through one adapter, `pipeline/hf_tool.py`
(`HFLMTool`, prompt styles `genesisgeo`, `genesisgeo_x00`, `fewshot`).
Which GenesisGeo prompt style the published checkpoint expects is to be
measured on a few held-out problems (their repo has moved to a newer format).

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
