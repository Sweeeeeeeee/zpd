#!/usr/bin/env bash
# DDAR alone on every problem, then DDAR + mini_long only on the problems DDAR
# alone did not solve (on solved ones the LLM config gives the same result).
# Resumable: bench/sweep.py skips names already in the output file.
# usage: bench/run_benchmarks.sh [dataset ...]   (default: jgex_ag_231 imo imo_102_requires_aux)
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv-newclid/bin/python
D=third_party/Newclid/newclid/problems_datasets
LLM=${LLM:-mini_long_model}
for ds in "${@:-jgex_ag_231 imo imo_102_requires_aux}"; do
  for name in $ds; do
    out=results/$name; mkdir -p "$out"
    echo "== $name: ddar_only $(date -u +%H:%M:%S)"
    $PY bench/sweep.py "$D/$name.txt" pipeline/configs/ddar_only.json "$out/ddar_only.jsonl" --time 60
    $PY -c "import json,sys; [print(r['name']) for r in map(json.loads, open(sys.argv[1])) if not r['solved']]" \
      "$out/ddar_only.jsonl" > "$out/ddar_unsolved.txt"
    echo "== $name: $LLM on $(wc -l < "$out/ddar_unsolved.txt") unsolved $(date -u +%H:%M:%S)"
    $PY bench/sweep.py "$D/$name.txt" "pipeline/configs/$LLM.json" "$out/$LLM.jsonl" --only "$out/ddar_unsolved.txt" --time 60
  done
done
echo "== done $(date -u +%H:%M:%S)"
