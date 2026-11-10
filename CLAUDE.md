# Notes for Claude

Claude keeps its own working notes in `claude/`. The user does not edit them.

**At the start of a session**
1. The SessionStart hook runs `claude/check.sh` (machine, Codespace timeout,
   jobs, running processes, training runs, git, warnings). If its output is not
   in context, run it.
2. Read `claude/STATE.md` (where things are, open problems, next steps).
3. Read `claude/LOG.md` only for the history behind something.
4. Deal with every `WARN:` line, or tell the user about it, before new work.

**During a session**
- Run anything longer than a few minutes through `claude/job.sh <id> <cmd...>`
  (detached: `setsid nohup claude/job.sh ... &`). Never keep results only in `/tmp`.
- If notes and files disagree, trust the files, the session transcripts in
  `~/.claude/projects/-workspaces-zpd/`, and `claude/jobs.log`, and fix the notes.

**At the end of a session** (or before leaving a job running unattended)
1. Add a dated entry at the top of `claude/LOG.md`: what was done, why, what was
   verified, with commit hashes. Short.
2. Rewrite `claude/STATE.md` so it is true now, and set its `Updated:` date.
3. Run `claude/check.sh` again; it should show no warnings that are not in STATE.md.

Project docs are in `docs/` (index in `README.md`); tasks in `docs/tasks.md`.
