#!/usr/bin/env bash
# Every proposer on the same held-out problems (bench/eval_proposers.py), one model
# at a time, results in results/proposers/val<N>/<name>.{jsonl,json}.
#
# Kill rule (user, 2026-11-12): a run that dies (SIGTERM from outside, see
# claude/STATE.md) is restarted and resumes where it stopped; a model is skipped
# when, after at least 3 attempts, more than 60% of its attempts were killed.
# Then <name>.skipped records the counts. At most 5 attempts.
# dtype: float32 for the small models (bfloat16 is ~2x slower on this CPU), bfloat16
# from 0.6B up (float32 would pass the ~2.5-3 GB at which processes here get killed).
#
#   bench/run_eval_proposers.sh                    # all models, 200 problems
#   N=5 bench/run_eval_proposers.sh smollm2_360m   # chosen models, first 5 problems
set -uo pipefail
cd "$(dirname "$0")/.."
N=${N:-200}
OUT=results/proposers/val200   # same folder for any N: a later, larger N resumes the rows
mkdir -p "$OUT"
declare -A ARGS=(
  [mini]="geolm geo-lm/runs/mini/best.pt"
  [mini_long]="geolm geo-lm/runs/mini_long/best.pt"
  [mid]="geolm geo-lm/runs/mid/best.pt"
  [smollm2_135m]="hf models/hf/SmolLM2-135M-Instruct --prompt fewshot"
  [smollm2_360m]="hf models/hf/SmolLM2-360M-Instruct --prompt fewshot"
  [genesisgeo]="hf models/hf/GenesisGeo --prompt genesisgeo --dtype bfloat16"
  [qwen3_0_6b_base]="hf models/hf/Qwen3-0.6B-Base --prompt fewshot --dtype bfloat16"
  [qwen25_1_5b]="hf models/hf/Qwen2.5-1.5B-Instruct --prompt fewshot --dtype bfloat16"
  [ag1]="ag1 models/ag1/ag_ckpt_vocab"
)
MODELS=${*:-"mini mini_long mid smollm2_135m smollm2_360m genesisgeo ag1 qwen3_0_6b_base qwen25_1_5b"}
for m in $MODELS; do
  [ -e "$OUT/$m.skipped" ] && { echo "== $m: skipped earlier ($(cat "$OUT/$m.skipped"))"; continue; }
  attempts=0; kills=0
  while [ $attempts -lt 5 ]; do
    attempts=$((attempts + 1))
    echo "== $m attempt $attempts, n=$N $(date -u +%H:%M:%S)"
    .venv-newclid/bin/python bench/eval_proposers.py ${ARGS[$m]} --n "$N" --out "$OUT/$m"
    rc=$?
    [ $rc -eq 0 ] && { echo "== $m done $(date -u +%H:%M:%S)"; break; }
    kills=$((kills + 1))
    echo "== $m died rc=$rc ($kills of $attempts attempts) $(date -u +%H:%M:%S)"
    if [ $attempts -ge 3 ] && [ $((kills * 100)) -gt $((attempts * 60)) ]; then
      echo "killed $kills of $attempts attempts (rc $rc), $(wc -l < "$OUT/$m.jsonl" 2>/dev/null || echo 0) problems done" > "$OUT/$m.skipped"
      echo "== $m skipped: $(cat "$OUT/$m.skipped")"; break
    fi
    sleep 20   # let memory settle before the restart
  done
done
echo "== all done $(date -u +%H:%M:%S)"
