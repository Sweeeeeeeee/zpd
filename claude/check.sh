#!/usr/bin/env bash
# Facts about the machine and the repo, for Claude at the start of a session.
# Runs automatically (SessionStart hook in .claude/settings.json); safe to rerun.
# Prints plain facts, then WARN lines for anything that needs attention.
# Never changes anything.

cd "$(dirname "$0")/.." || exit 0
ROOT=$PWD
WARN=()
warn() { WARN+=("$1"); }

echo "== claude/check.sh  $(date -u '+%Y-%m-%d %H:%M UTC')"

# --- machine -------------------------------------------------------------
boot=$(uptime -s 2>/dev/null)
echo "machine: up since $boot UTC, $(nproc) cores, $(free -g | awk '/Mem/{print $2" GB RAM, "$7" GB free"}'), disk $(df -h /workspaces | awk 'NR==2{print $4" free"}')"
if [ -n "$CODESPACE_NAME" ]; then
  cs=$(timeout 10 gh api "/user/codespaces/$CODESPACE_NAME" \
        --jq '"\(.idle_timeout_minutes) \(.state) \(.created_at)"' 2>/dev/null)
  read -r idle state created <<<"$cs"
  echo "codespace: $CODESPACE_NAME, idle timeout ${idle:-?} min, created ${created:-?}"
  [ -n "$idle" ] && [ "$idle" -lt 240 ] && warn "idle timeout is $idle min, not 240"
  [ -z "$idle" ] && warn "could not read the idle timeout from the GitHub API"
fi

# --- jobs started with claude/job.sh ---------------------------------------
JL=claude/jobs.log
if [ -f "$JL" ]; then
  echo "jobs (last 5 events in $JL):"
  tail -5 "$JL" | sed 's/^/  /'
  # a job with START but no END was killed together with the machine or by a signal
  for id in $(awk '$3=="START"{print $4}' "$JL"); do
    if ! awk -v id="$id" '$3=="END" && $4==id{f=1} END{exit !f}' "$JL"; then
      if ! pgrep -f "job.sh $id " >/dev/null; then
        hb=$(grep -h "^" "claude/jobs/$id.heartbeat" 2>/dev/null | tail -1)
        warn "job $id never finished; last heartbeat ${hb:-none} (machine stop or kill). See claude/jobs/$id.out"
      fi
    fi
  done
  awk '$3=="END" && $5!="exit=0"{print $4" "$5}' "$JL" | tail -3 | while read -r l; do
    echo "  non-zero exit: $l"; done
fi

# --- anything running ----------------------------------------------------
procs=$(pgrep -af 'python[0-9.]* .*(geo_lm|bench/|pipeline/|eval_aux|newclid)' | grep -v -e pgrep -e check.sh)
if [ -n "$procs" ]; then echo "running:"; echo "$procs" | cut -c1-140 | sed 's/^/  /'
else echo "running: nothing"; fi

# --- training runs -------------------------------------------------------
for log in geo-lm/runs/*/log.jsonl; do
  [ -f "$log" ] || continue
  run=$(basename "$(dirname "$log")")
  python3 - "$log" "$run" <<'EOF'
import json, sys
step = best = None
for line in open(sys.argv[1]):
    try: e = json.loads(line)
    except ValueError: continue
    if e.get("event") == "train": step = e["step"]
    if e.get("event") == "eval": best = (e["step"], e["val_loss"], e.get("exact_match"))
print(f"run {sys.argv[2]}: last step {step}, last eval {best}")
EOF
done

# --- git -----------------------------------------------------------------
timeout 15 git fetch -q 2>/dev/null
br=$(git branch --show-current)
ab=$(git rev-list --left-right --count "origin/$br...HEAD" 2>/dev/null)
echo "git: $br, $(git log -1 --format='%h %ad %s' --date=short), behind/ahead origin: ${ab:-?}"
dirty=$(git status --porcelain)
if [ -n "$dirty" ]; then
  echo "uncommitted:"; echo "$dirty" | sed 's/^/  /'
  echo "$dirty" | grep -q '\.pt$' && warn "trained checkpoints are uncommitted (only copy is this machine)"
fi
set -- ${ab:-0 0}; [ "${1:-0}" -gt 0 ] && warn "local branch is $1 commits behind origin: pull first"
big=$(git status --porcelain | awk '{print $2}' | xargs -r du -m 2>/dev/null | awk '$1>=95{print $2" ("$1" MB)"}')
[ -n "$big" ] && warn "files near GitHub's 100 MB limit: $big"

# --- the notes themselves ------------------------------------------------
st=$(grep -m1 -o 'Updated: [0-9-]*' claude/STATE.md 2>/dev/null | cut -d' ' -f2)
echo "STATE.md updated: ${st:-?}"
last_commit=$(git log -1 --format=%ad --date=short)
[ -n "$st" ] && [[ "$last_commit" > "$st" ]] && warn "STATE.md ($st) is older than the last commit ($last_commit)"

echo
if [ ${#WARN[@]} -eq 0 ]; then echo "no warnings"
else printf 'WARN: %s\n' "${WARN[@]}"; fi
exit 0
