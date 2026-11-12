# geo_lm — a small transformer for auxiliary constructions in geometry

`geo_lm` is a small decoder-only transformer, written from scratch in PyTorch, that
proposes **auxiliary constructions** for geometry problems written in Newclid /
AlphaGeometry syntax. It ships with a tokenizer for that syntax, greedy decoding,
deterministic beam search, and checkpoint save/load. No pretrained weights are used.
Everything runs on CPU; a modest GPU is used automatically when present.

It is part of task 2 of a larger project: Newclid's DDAR engine does the deduction, and
this model suggests a new point when DDAR gets stuck.

The code is in `geo-lm/`. Commands in this file run from that folder.

## Install

# CPU-only PyTorch (much smaller download):
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

Requires Python ≥ 3.9 and PyTorch ≥ 2.0 (1.13 works, using a slower attention path).

## Check it works

```bash
python -m pytest -q                      # 24 tests, a few seconds on CPU
python scripts/smoke_transformer.py      # trains a tiny model for ~10 s, must print SMOKE TEST PASSED
```

## Specification

### Sequence format

Every training example and every inference prompt uses one format:

```
<bos> PROBLEM <aux> AUX_CONSTRUCTION <eos>
```

* **PROBLEM** is a Newclid problem, for example
  `a b c = triangle a b c; d = midpoint d b c ? para d e a b`.
* **AUX_CONSTRUCTION** is one or more construction clauses, for example
  `e = on_line e a d, on_line e b c`.
* At inference the model is given `<bos> PROBLEM <aux>` and generates until `<eos>`.

### Tokenizer rules

* `;` `,` `=` `?` are always separate tokens.
* Other words are split into identifiers (`a`, `a1`, `on_tline`), single digits and
  single symbols. Pieces after the first in a word get a `##` prefix:
  `1pi/3` → `1 ##pi ##/ ##3`.
* Special tokens, always ids 0–4: `<pad> <unk> <bos> <eos> <aux>`.
* Decoding gives canonical spacing: `decode(encode(x)) == normalize(x)`.
  Canonical form is `a b c = triangle a b c; d = midpoint d a b ? cong d a d b`.
* The vocabulary is built from your corpus, ordered by frequency and then
  alphabetically, so the same corpus always gives the same vocabulary. Digits, `a`–`z`, `pi` and `/` are
  always included.

## Usage

### Train a model on your own pairs (minimal loop)

```python
import torch
from geo_lm import ModelConfig, GeoTokenizer, create_model, save_checkpoint

pairs = [("a b c = triangle a b c; d = midpoint d b c ? perp a d b c", "e = foot e a b c")]
tok = GeoTokenizer.build(p + " " + a for p, a in pairs)
model = create_model(ModelConfig.from_json("configs/model_tiny.json"), tok)

ids, start = tok.encode_example(*pairs[0])
x = torch.tensor([ids[:-1]])
y = torch.tensor([ids[1:]])
y[0, : start - 1] = -100                       # loss only on the construction
opt = torch.optim.AdamW(model.parameters(), lr=3e-3)
for _ in range(100):
    _, loss = model(x, y)
    opt.zero_grad(); loss.backward(); opt.step()

save_checkpoint("runs/demo.pt", model, tok, opt, step=100)
```
## Training

The first model is `runs/mini` (configs/train_mini.json): validation loss 0.57 after 14 minutes on 2 CPU cores. The current and best model, used by `pipeline/configs/default.json`, is `runs/mini_long` (configs/train_mini_long.json): the same model trained for 9000 steps (~1.5 h, resumed twice from `last.pt`), validation loss 0.27, exact match 33% top-1 / 49.5% top-4 on 200 held-out problems. The larger `runs/mid` (configs/model_mid.json: 6 layers, 4 heads, 256 dims, 5.1M params; 9000 steps, ~3.4 h in two parts) reaches validation loss 0.235 and exact match 39% / 53.5%; `pipeline/configs/mid_model.json` uses it.
Check its proposals on held-out problems with
`../.venv-newclid/bin/python scripts/eval_aux.py runs/mini/best.pt --n 200 --beam 4`
(results in `results/transformer/`, written up in [rezultati.md](rezultati.md)).

```bash
# from geo-lm/, data from datagen.md in ../data/genesisgeo/
python -m geo_lm.train --config configs/train_tiny.json     # end-to-end smoke run, ~1 min CPU
python -m geo_lm.train --config configs/train_mini.json     # ~2M params, 100k examples, 1600 steps in ~14 min CPU (runs/mini)
python -m geo_lm.train --config configs/train_small.json    # ~11M params, 100k examples
python -m geo_lm.train --config configs/train_small.json --lr 1e-3 --batch_size 64 --max_steps 5000
```

Every field of `TrainConfig` (in `geo_lm/train.py`) can be set in the JSON file
and overridden on the command line:

| group | fields |
|---|---|
| data | `train_data`, `val_data`, `max_examples` |
| model | `model_config`, which points to a model JSON: layers, heads, embedding size, context length, vocab, dropout |
| optimisation | `lr`, `min_lr`, `warmup_steps`, `weight_decay`, `grad_clip`, `batch_size`, `grad_accum` |
| run length and logging | `max_steps`, `log_every`, `eval_every`, `ckpt_every`, `eval_generate` |
| hardware and resuming | `device`, `num_threads`, `seed`, `resume` |

Relative paths in the JSON file are resolved against the file's own directory.

* The loss covers only the auxiliary construction and `<eos>`.
* The learning rate warms up linearly, then follows a cosine decay.
* Batches are bucketed by length to reduce padding.
* bf16 autocast is used on GPUs that support it.
* On limited memory, use `grad_accum` to keep the effective batch size.
* `out_dir` gets `last.pt` (resumed automatically), `best.pt` (lowest
  validation loss), `log.jsonl` and `config.json`.
* Evaluation reports validation loss and greedy exact-match accuracy on
  `eval_generate` held-out examples.

The tokenizer is built from the training data on the first run and stored in
the checkpoint. On the GenesisGeo data it has 76 tokens.
