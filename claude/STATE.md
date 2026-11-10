# State

Updated: 2026-11-10 18:15 UTC (session 32e42808)

Claude's own notes: overwrite this file at the end of every session so it is
true *now*. History goes to [LOG.md](LOG.md), not here. Facts that a command can
tell (git status, running jobs, timeout) come from `claude/check.sh`; this file
holds what a command cannot tell.

## Where things are

| | |
|---|---|
| Bigger model | **RUNNING since 17:30 UTC (2nd start)**: `geo-lm/scripts/run_mid_pipeline.sh` via `setsid -f claude/job.sh mid-pipeline` (own session). Train `runs/mid` (5.1M, 9000 steps) until 20:20, restarts from `last.pt` if killed → eval_aux 200 → `LLM=mid_model bench/run_benchmarks.sh` until 20:55 → commit+push main → `claude/jobs/mid-pipeline.done`. Backups every 30 min to branch `backup-mid`. Hard stop 21:10: backup + `gh codespace stop`. 1st start (17:11) lost to a SIGTERM at 17:19 (sender unknown); its bogus bench output is in `claude/jobs/broken_mid_run_1711/` |
| Done | tasks 1-6, 7.1, 8.2, 8.2a (benchmarks), 12.1-12.3 ([docs/tasks.md](../docs/tasks.md)) |
| Best model | `geo-lm/runs/mini_long/best.pt`: 2.1M params, **step 9000 (finished)**, val loss 0.271, exact 33% top-1 / 49.5% top-4, 90.6% translatable on 200 held-out problems |
| Stuck JGEX problems | `mini_long` solves L058-9 but **not L053-1**; `mini` (1600 steps) solved both. Better exact match did not mean better help here |
| Benchmarks | `bench/run_benchmarks.sh`, results in `results/{jgex_ag_231,imo,imo_102_requires_aux}/`: JGEX 205 DDAR / 210 with `mini_long`; IMO-AG-30 (29) 15 / 15; imo_102 0 / 3. AG1: 198/228 JGEX, 14/25 IMO-AG-30. In `docs/rezultati.md` |
| Docs | `docs/rezultati.md`, `tasks.md`, `geo-lm.md`, `README.md` have the 9000-step numbers |
| Paper | `zpd_darbs/preliminary` still describes only the 1600-step `mini` model and the first 73-JGEX run. Not updated on purpose: ask the user whether the paper should switch to `mini_long` and the 231 benchmark. `make_figures.py` pins the JGEX tables to the first 73 rows (`PAPER_JGEX_N`); change that together with the text |
| Blocker | the problem set (7.2-7.6): the scan (9-11) cannot start without it |
| Other models | Comparison harness ready (`docs/models.md`): `pipeline/hf_tool.py` (any HF model), `bench/compare_configs.py` → `pipeline/configs/compare/<domain>/<proposer>.json` (depth 1, 60 s after loading, strict tools), `bench/run_compare.sh`, `bench/compare_table.py`, sample `bench/compare_problems.txt` (60 JGEX). GenesisGeo in `models/hf/GenesisGeo` (gitignored), **prompt format untested** (test needs free CPU+RAM). Nothing of the comparison has been run yet |
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

1. When the mid run ends (~20:45): check `claude/jobs/mid-pipeline.out`, add the
   mid results to `docs/rezultati.md`, compare with mini_long. If 9000 steps were
   not reached, resume later: `setsid -f claude/job.sh mid-pipeline geo-lm/scripts/run_mid_pipeline.sh "<train end>" "<bench end>" "<hard end>"`.
2. GenesisGeo prompt test (scratchpad script idea: 3 val problems, both prompt
   styles, compare with reference aux), then set the right style in
   `bench/compare_configs.py`.
3. Folder restructure from `docs/models.md` (geo-lm → models/...), full tests.
4. Run the comparison: `bench/run_compare.sh` (light), then GenesisGeo,
   SmolLM2; `bench/compare_table.py`. Measure cost on one domain first.
5. User: why the Codespace stopped on 11-09; paper → mini_long/mid?
6. 7.2 Sort the 1499 Latvian geometry problems.
