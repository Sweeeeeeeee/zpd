# State

Updated: 2026-11-10 16:50 UTC (session 32e42808)

Claude's own notes: overwrite this file at the end of every session so it is
true *now*. History goes to [LOG.md](LOG.md), not here. Facts that a command can
tell (git status, running jobs, timeout) come from `claude/check.sh`; this file
holds what a command cannot tell.

## Where things are

| | |
|---|---|
| Uncommitted | 11-10 cleanup: `make_figures.py` fix, `default.json` → `mini_long`, docs (rezultati AG1 note, README, pipeline.md, geo-lm.md, tasks.md), `sweep.py` resume fix, these notes |
| Done | tasks 1-6, 7.1, 8.2, 8.2a (benchmarks), 12.1-12.3 ([docs/tasks.md](../docs/tasks.md)) |
| Best model | `geo-lm/runs/mini_long/best.pt`: 2.1M params, **step 9000 (finished)**, val loss 0.271, exact 33% top-1 / 49.5% top-4, 90.6% translatable on 200 held-out problems |
| Stuck JGEX problems | `mini_long` solves L058-9 but **not L053-1**; `mini` (1600 steps) solved both. Better exact match did not mean better help here |
| Benchmarks | `bench/run_benchmarks.sh`, results in `results/{jgex_ag_231,imo,imo_102_requires_aux}/`: JGEX 205 DDAR / 210 with `mini_long`; IMO-AG-30 (29) 15 / 15; imo_102 0 / 3. AG1: 198/228 JGEX, 14/25 IMO-AG-30. In `docs/rezultati.md` |
| Docs | `docs/rezultati.md`, `tasks.md`, `geo-lm.md`, `README.md` have the 9000-step numbers |
| Paper | `zpd_darbs/preliminary` still describes only the 1600-step `mini` model and the first 73-JGEX run. Not updated on purpose: ask the user whether the paper should switch to `mini_long` and the 231 benchmark. `make_figures.py` pins the JGEX tables to the first 73 rows (`PAPER_JGEX_N`); change that together with the text |
| Blocker | the problem set (7.2-7.6): the scan (9-11) cannot start without it |
| Codespace budget | user, 2026-11-10 ~16:50 UTC: **35 h left** on 2 cores (70 core-h) this billing month. Free plan 120 core-h/month. Stop the Codespace when idle; no long training here (use Kaggle) |
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
2. On 11-10 the Codespace ran 08:12-08:55 unattended with no stop (training
   33 min via `claude/job.sh`), so the 11-09 stop did not repeat. A safety stop
   (`gh codespace stop` after 7000 s) was armed; the session stopped the
   Codespace itself at the end.

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

1. User: confirm why the Codespace stopped on 11-09 (billing page, email).
2. Ask: should the paper use `mini_long` (9000) instead of `mini` (1600)?
   (AG1 numbers 198/228, 14/25 verified against the official AG1 README on 11-10.)
3. **7.2** Sort the 1499 Latvian geometry problems into statable / not statable.
4. 7.3-7.4 Pick the working set, translate and scan a pilot batch of ~10.
5. Same benchmark with `heuristics_only` and `mini_model` (1600 steps) on the
   DDAR failures (`results/*/ddar_unsolved.txt`, 26 + 17 + 101): ~15 min each.
   `LLM=mini_model bench/run_benchmarks.sh` does the model part.
