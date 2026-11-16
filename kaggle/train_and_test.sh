#!/usr/bin/env bash
# Run from a Kaggle GPU notebook after setup.sh --no-tex --system-site-packages.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT=$PWD
PY=$ROOT/.venv-newclid/bin/python
OUT=${KAGGLE_ARTIFACTS_DIR:-/kaggle/working/zpd-artifacts}

if [ ! -x "$PY" ]; then
  echo "Missing .venv-newclid; first run: bash setup.sh --no-tex --system-site-packages" >&2
  exit 1
fi

"$PY" - <<'PY'
import torch

if not torch.cuda.is_available():
    raise SystemExit("CUDA is unavailable; enable a Kaggle GPU accelerator and rerun.")
print(f"CUDA: {torch.cuda.get_device_name(0)}")
print(f"PyTorch: {torch.__version__}")
PY

mkdir -p "$OUT"
echo "== GPU training smoke test =="
"$PY" -m geo_lm.train \
  --config geo-lm/configs/train_small.json \
  --device cuda \
  --max_steps 2 \
  --eval_generate 0 \
  --resume false \
  --out_dir "$OUT/smoke"

echo "== Full test suite before training =="
"$PY" -m pytest -q

echo "== Train / resume the 11M model =="
"$PY" -m geo_lm.train \
  --config geo-lm/configs/train_small.json \
  --device cuda \
  --eval_generate 0

echo "== Evaluate the best checkpoint on 200 held-out examples =="
"$PY" geo-lm/scripts/eval_aux.py \
  geo-lm/runs/small/best.pt \
  --n 200 \
  --beam 4 \
  --out "$OUT/eval_small_val200.json"

echo "== Full test suite after training =="
"$PY" -m pytest -q

echo "== Copy checkpoints and logs to notebook output =="
mkdir -p "$OUT/small"
cp geo-lm/runs/small/best.pt geo-lm/runs/small/last.pt \
  geo-lm/runs/small/config.json geo-lm/runs/small/log.jsonl "$OUT/small/"
echo "Artifacts saved under $OUT"
