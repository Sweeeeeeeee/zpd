#!/usr/bin/env bash
# Unattended mid-model run: train -> offline eval -> benchmarks -> commit, with
# periodic backups and a hard stop before the Codespace idle timeout.
#
#   setsid nohup claude/job.sh mid-pipeline geo-lm/scripts/run_mid_pipeline.sh \
#       TRAIN_END BENCH_END HARD_END &        # times as "YYYY-MM-DD HH:MM" UTC
#
# Every stage is resumable: training restarts from runs/mid/last.pt and
# bench/sweep.py skips problems already in its output, so rerunning the script
# continues where it stopped.
# Backups: runs/mid + results + claude/ are pushed as one commit to the branch
# backup-mid (force-pushed, the branch only ever holds the latest backup; main
# and the working tree are not touched). At the end everything is committed to main.
set -uo pipefail
cd "$(dirname "$0")/../.."
ROOT=$PWD
PY=$ROOT/.venv-newclid/bin/python
TRAIN_END=$(date -ud "$1" +%s); BENCH_END=$(date -ud "$2" +%s); HARD_END=$(date -ud "$3" +%s)
RUN=geo-lm/runs/mid
DONE=claude/jobs/mid-pipeline.done
log() { echo "[$(date -u +%H:%M:%S)] $*"; }
left() { echo $(( $1 - $(date +%s) )); }

backup() {
  local idx; idx=$(mktemp)
  GIT_INDEX_FILE=$idx git read-tree HEAD
  GIT_INDEX_FILE=$idx git add -f $RUN results claude geo-lm/configs pipeline/configs geo-lm/scripts 2>/dev/null
  local tree commit
  tree=$(GIT_INDEX_FILE=$idx git write-tree) &&
  commit=$(git commit-tree "$tree" -p HEAD -m "backup: mid run $(date -u '+%Y-%m-%d %H:%M') UTC") &&
  git push -q -f origin "$commit:refs/heads/backup-mid" && log "backup pushed $commit"
  rm -f "$idx"
}

# Hard deadline, independent of the stages: back up and stop the Codespace.
(
  sleep "$(left "$HARD_END")"
  log "HARD deadline: final backup and Codespace stop"
  backup
  gh codespace stop -c "$CODESPACE_NAME"
) &
WATCH=$!
# Backup every 30 min while the run goes.
( while sleep 1800; do backup; done ) &
PERIODIC=$!

log "1/4 train until $(date -ud @"$TRAIN_END" +%H:%M)"
( cd geo-lm/configs && timeout "$(left "$TRAIN_END")" "$PY" -m geo_lm.train --config train_mid.json )
log "train exit=$?"
cp $RUN/log.jsonl results/transformer/mid_train_log.jsonl
backup

log "2/4 offline eval on 200 held-out problems"
( cd geo-lm && timeout 1200 "$PY" scripts/eval_aux.py runs/mid/best.pt --n 200 --beam 4 \
    --out ../results/transformer/eval_mid_val200.json )
log "eval exit=$?"

log "3/4 benchmarks on DDAR failures until $(date -ud @"$BENCH_END" +%H:%M)"
LLM=mid_model timeout "$(left "$BENCH_END")" bench/run_benchmarks.sh
log "bench exit=$?"

log "4/4 summary and commit"
for ds in jgex_ag_231 imo imo_102_requires_aux; do
  f=results/$ds/mid_model.jsonl
  [ -f "$f" ] && log "$ds: mid solved $(grep -c '"solved": true' "$f") of $(wc -l < "$f") run (of $(wc -l < results/$ds/ddar_unsolved.txt) DDAR failures)"
done
kill $PERIODIC 2>/dev/null
git add -f $RUN/config.json $RUN/log.jsonl $RUN/best.pt $RUN/last.pt \
  results/transformer/mid_train_log.jsonl results/transformer/eval_mid_val200.json \
  results/*/mid_model.jsonl claude/jobs.log 2>/dev/null
git commit -q -m "mid model (5.1M params): training, offline eval, benchmarks on DDAR failures (unattended run)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q && log "committed $(git rev-parse --short HEAD)"
backup
date -u '+%Y-%m-%d %H:%M:%S' > "$DONE"
log "done; waiting for the hard deadline to stop the Codespace (Claude stops it earlier if finished)"
wait $WATCH
