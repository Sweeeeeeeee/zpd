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
| light, ours | `mid` (9000 steps) | 5.1M | `geo-lm/runs/mid` | training 11-10 |
| light, general | SmolLM2-360M-Instruct, few-shot | 0.36B | Hugging Face | planned |
| big, specialist | GenesisGeo (Qwen3-0.6B fine-tuned on the same data) | 0.6B | `ZJUVAI/GenesisGeo`, downloaded to `models/hf/` | adapter written, untested |
| big, general | Qwen2.5-1.5B-Instruct, few-shot | 1.5B | Hugging Face | optional |

All Hugging Face models go through one adapter, `pipeline/hf_tool.py`
(`HFLMTool`, prompt styles `genesisgeo`, `genesisgeo_x00`, `fewshot`).
Which GenesisGeo prompt style the published checkpoint expects is to be
measured on a few held-out problems (their repo has moved to a newer format).

## Fitting the models to the requirement

- **Depth 1**: `search.max_depth = 1` in every comparison config.
- **Budget**: 30 s and 2 GB per problem for light models. Big models get
  3 GB (a 0.6B model in bfloat16 is ~1.2 GB) and are reported separately.
- **Load time**: `solve()` runs each problem in a fresh child process, so a
  model is loaded once per problem (mini: ~1 s, GenesisGeo: ~5-10 s). For
  the comparison either load time is subtracted and reported apart, or one
  process serves all problems. To decide before the big-model runs.
- **CPU only here**: big models on Kaggle (free GPU) or on a small subset.
- **Memory next to training**: never load a big model while training runs
  (on 11-10 that got the training killed).

## Problems

Not IMO. In order:
1. JGEX-231 problems DDAR fails on (26), per domain config
   (`pipeline/configs/domains/`), depth 1.
2. `problems/examples/`.
3. The Latvian pilot batch (task 7.4), when translated: the real target.

Output: one table, model x domain: solved with one aux point, median time,
peak memory, model size.

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
