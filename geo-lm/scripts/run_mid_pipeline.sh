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

MAX_STEPS=$("$PY" -c "import json; print(json.load(open('geo-lm/configs/train_mid.json'))['max_steps'])")
step_now() { "$PY" -c "import json,sys
s=0
for l in open(sys.argv[1]):
    try: s=max(s, json.loads(l).get('step', 0))
    except Exception: pass
print(s)" $RUN/log.jsonl 2>/dev/null || echo 0; }

# Training restarts from last.pt if it is killed early (on 11-10 a stray SIGTERM
# stopped it at step 350), until max_steps or the deadline.
log "1/4 train until $(date -ud @"$TRAIN_END" +%H:%M)"
for attempt in $(seq 1 20); do
  ( cd geo-lm/configs && timeout "$(left "$TRAIN_END")" "$PY" -m geo_lm.train --config train_mid.json )
  rc=$?; s=$(step_now)
  log "train attempt $attempt exit=$rc step=$s"
  [ "$s" -ge "$MAX_STEPS" ] && break
  [ "$(left "$TRAIN_END")" -le 60 ] && { log "training deadline reached at step $s"; break; }
  sleep 10
done
cp $RUN/log.jsonl results/transformer/mid_train_log.jsonl
backup
if [ ! -f $RUN/best.pt ]; then
  log "no best.pt (no evaluation reached): skipping eval and benchmarks"
  echo "FAILED: no best.pt $(date -u '+%Y-%m-%d %H:%M:%S')" > "$DONE"
  kill $PERIODIC 2>/dev/null; wait $WATCH; exit 1
fi

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
