#!/usr/bin/env bash
# Run a long command so that its trace survives a machine stop.
#
#   claude/job.sh <id> <command...>          # e.g. claude/job.sh train-ml-1 python -m geo_lm.train ...
#   setsid nohup claude/job.sh <id> ... &    # detached from the Claude session
#
# Writes, all under claude/ on the persistent disk (never /tmp, which a restart wipes):
#   jobs.log              START / END lines with UTC time, exit code and duration
#   jobs/<id>.out         the command's stdout and stderr
#   jobs/<id>.heartbeat   a UTC timestamp every 60 s while the job runs
# If the machine stops, there is a START with no END, and the last heartbeat tells
# when it went down to within a minute. claude/check.sh reports that.

[ $# -ge 2 ] || { echo "usage: $0 <id> <command...>" >&2; exit 2; }
id=$1; shift
dir=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$dir/jobs"
log=$dir/jobs.log
ts() { date -u '+%Y-%m-%d %H:%M:%S'; }

echo "$(ts) START $id pid=$$ cwd=$PWD cmd=$*" >>"$log"
( while sleep 60; do ts >"$dir/jobs/$id.heartbeat"; done ) &
hb=$!
ts >"$dir/jobs/$id.heartbeat"
t0=$(date +%s)
"$@" >>"$dir/jobs/$id.out" 2>&1 &
child=$!
# A signal to this wrapper (e.g. the Codespace shutting down) is passed on and logged.
on_signal() {
  kill -"$1" "$child" 2>/dev/null; wait "$child"
  echo "$(ts) END $id exit=signal-$1 dur=$(( ($(date +%s)-t0)/60 ))min" >>"$log"
  kill "$hb" 2>/dev/null; exit "$2"
}
trap 'on_signal TERM 143' TERM
trap 'on_signal INT 130' INT
trap 'on_signal HUP 129' HUP
wait $child
rc=$?
kill $hb 2>/dev/null
echo "$(ts) END $id exit=$rc dur=$(( ($(date +%s)-t0)/60 ))min" >>"$log"
exit $rc
