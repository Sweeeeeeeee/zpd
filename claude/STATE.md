# State

Updated: 2026-11-10 (session ac55cba9)

Claude's own notes: overwrite this file at the end of every session so it is
true *now*. History goes to [LOG.md](LOG.md), not here. Facts that a command can
tell (git status, running jobs, timeout) come from `claude/check.sh`; this file
holds what a command cannot tell.

## Where things are

| | |
|---|---|
| Done | tasks 1-6, 7.1, 8.2, 12.1-12.3 ([docs/tasks.md](../docs/tasks.md)) |
| Best model | `geo-lm/runs/mini_long/best.pt`: 2.1M params, **step 4500**, val loss 0.406, exact 16% (on the 100 val examples the training loop checks) |
| Paper / docs numbers | still the **step-3000** checkpoint (val loss 0.49, top-1 11.5%, top-4 32% on 200 problems). Not yet re-evaluated at 4500 |
| `mini_long` | stopped at step 5000 of 9000; `last.pt` = step 5000 with optimizer, resumable (~45 min left at ~110 steps/min) |
| Blocker | the problem set (7.2-7.6): the scan (9-11) cannot start without it |
| Machine | Codespace `glowing-barnacle-69499rgp76525wvr`, 2 cores, 8 GB, idle timeout 240 min |

## Open problems

1. **The Codespace stopped by itself on 2026-11-09 at ~09:15 UTC**, 20 min after
   the last input. Not the idle timeout (240). Signs: SIGTERM to the training at
   09:09:37, Claude gone at 09:10, machine down after 09:14:30, nothing in the
   VS Code logs after the browser disconnect at 08:55:32. The API gives no stop
   reason. Most likely the free Codespaces quota ran out (120 core-hours/month,
   $0 spending limit stops the Codespace), restarting with the billing cycle on
   11-10; or a manual stop. **Unconfirmed**: the user should check
   github.com/settings/billing. Until then, no job here is safe for more than a
   few minutes unattended.
2. The step-3000 → step-4500 checkpoint, the run log and the setup fixes of
   11-09 are uncommitted (check.sh warns while this is true).

## Rules learned the hard way

- `/tmp` is wiped when the Codespace restarts: job output there is lost (that is
  why the 11-09 stop had to be reconstructed from the session transcript).
  Run long jobs with `claude/job.sh`, which keeps output and heartbeats in `claude/jobs/`.
- The idle timeout counts from the user's last input, not from running jobs, and
  is fixed when a Codespace is created.
- A background job started by Claude dies with the Claude session; use
  `setsid nohup claude/job.sh ...` for anything that must outlive it.
- `gh codespace create` and the billing API do not work with the Codespace token.
- Session transcripts (`~/.claude/projects/-workspaces-zpd/*.jsonl`) record what an
  earlier session actually ran. Read them when LOG.md and the files disagree.

## Next

1. Commit the 11-09 work and this logging system.
2. User: confirm why the Codespace stopped (billing page, email).
3. **7.2** Sort the 1499 Latvian geometry problems into statable / not statable.
4. 7.3-7.4 Pick the working set, translate and scan a pilot batch of ~10.
5. Evaluate `mini_long` step 4500 (`eval_aux.py`, 200 problems, ~10 min) and
   update docs/paper numbers; optionally finish the run to 9000 once (1) of Open
   problems is understood, or on Kaggle.
