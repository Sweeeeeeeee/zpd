#!/usr/bin/env bash
# Proposer comparison (docs/models.md): per domain, DDAR alone on the 60-problem
# JGEX sample (bench/compare_problems.txt: the 26 that yuclid DDAR fails + 34 spread
# over the rest), then each proposer only on the problems DDAR failed in that domain
# (on the others every proposer gives the same result: DDAR runs first).
# Configs: pipeline/configs/compare/<domain>/<proposer>.json (bench/compare_configs.py),
# budget from the config (60 s after loading, one aux point).
# Resumable: bench/sweep.py skips problems already in its output.
#
#   bench/run_compare.sh                         # light proposers, all domains
#   bench/run_compare.sh genesisgeo              # chosen proposers
#   DOMAINS="circles" bench/run_compare.sh mini  # chosen domains
# Then: python bench/compare_table.py
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv-newclid/bin/python
DATA=${DATA:-bench/compare_problems.txt}
OUT=${OUT:-results/compare}
DOMAINS=${DOMAINS:-"full no_similarity circles"}
PROPOSERS=${*:-"heuristics mini mini_long mid"}
for d in $DOMAINS; do
  out=$OUT/$d; mkdir -p "$out"
  echo "== $d: ddar on all $(date -u +%H:%M:%S)"
  $PY bench/sweep.py "$DATA" "pipeline/configs/compare/$d/ddar.json" "$out/ddar.jsonl"
  $PY -c "import json,sys; [print(r['name']) for r in map(json.loads, open(sys.argv[1])) if not r['solved']]" \
    "$out/ddar.jsonl" > "$out/ddar_unsolved.txt"
  for p in $PROPOSERS; do
    echo "== $d: $p on $(wc -l < "$out/ddar_unsolved.txt") DDAR failures $(date -u +%H:%M:%S)"
    $PY bench/sweep.py "$DATA" "pipeline/configs/compare/$d/$p.json" "$out/$p.jsonl" --only "$out/ddar_unsolved.txt"
  done
done
echo "== done $(date -u +%H:%M:%S)"
