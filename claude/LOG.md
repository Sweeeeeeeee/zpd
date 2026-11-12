# Work log

What was done in each working session with Claude Code, why, and what was
verified. Newest first. Times are UTC. The current state and next steps are in
[STATE.md](STATE.md); this file is history.

---

## 2026-11-12 (session 51d9920c)

- `mid` resumed 7700 -> 9000 (14:59-15:31, `run_mid_pipeline.sh`; 7500 results
  kept as `mid_7500_*`, 71fdb86). Val loss 0.235, exact 39% / 53.5%. Bench:
  JGEX 5/26 (7500: 6), IMO set 1/17 = **IMO 2015 P3** (first IMO-AG-30 gain),
  imo_102 6/101. Lost JGEX problems ended in 21 s / 8 s (not time limit).
  Committed by the pipeline 64e1fab; its 18:30 Codespace stop cancelled (killed
  the job's process group -> jobs.log END signal-TERM, expected).
  Bench timings overlap AG1 install/tests (noted in rezultati.md).
- HF proposers (4104a06): GenesisGeo comma-less output split by predicate
  name (+test), generation stops at ';', 20 new tokens (p99 of one aux point
  = 13 Qwen tokens). Downloaded SmolLM2-360M, Qwen2.5-1.5B, SmolLM2-135M,
  Qwen3-0.6B-Base (control for GenesisGeo) to `models/hf/`; `models/registry.json`,
  `bench/hf_probe.py` (not yet run). No HF model probed this session.
- AG1 (ece3c69): see docs/models.md "AlphaGeometry (AG1)". Env, checkpoint
  (sha256 = HF mirror), server/tool, weights-only npz, decode cap. Verified on
  the README orthocenter proposals. ~40 s load + 75 s JIT + 23 s/call, 2.7 GB,
  SIGTERM in 2 of 5 runs: not usable here within 60 s.
- Cleanup: pip cache, npm cache, pycache (1 GB). `git gc --prune` of 566 MB old
  backup objects was blocked by the permission classifier: left to the user.
- Tests 86 passed.

## 2026-11-10 (session 32e42808, evening)

- `mid` model (5.1M) trained unattended 17:30-20:20 via `run_mid_pipeline.sh`
  after two kills (17:19 SIGTERM unknown; 17:34 memory pressure → mallopt fix in
  `geo_lm/train.py`, b2506a4). Reached step 7700; best.pt = step 7500, val 0.252.
  Eval 200: exact 37.5% / 52% (mini_long 33 / 49.5). Bench: JGEX +6/26,
  imo_102 5/101, IMO-AG-30 +0. Pipeline committed 3dba999; backups on `backup-mid`.
- Comparison harness (e66e54d): HF adapter, strict tool loading, load time apart
  from the solve limit, 24 configs, runner, table. Nothing run yet.
- `docs/rezultati.md` mid section + headline, `docs/models.md` status.
- Codespace stopped by Claude after the commit.

## 2026-11-10 ~16:55 · rezultati.md restructured; bigger-model speed measured

- Committed the cleanup (`1cfdddb`, pushed). User: 35 h of 2-core time left.
- `docs/rezultati.md` reorganised, no numbers changed: summary table + two
  benchmark charts first, then 1. standard sets, 2. transformer (new
  `mini_long` val-loss chart), 3. early experiments, conclusions rewritten.
- Mid run prepared: `model_mid.json`, `train_mid.json` (lr 1e-3, eval_generate 50),
  `pipeline/configs/mid_model.json`, `geo-lm/scripts/run_mid_pipeline.sh`.
  Tested: backup push to `backup-mid`, eval_aux and pipeline with the 40-step
  scratch checkpoint. Started ~17:15, deadlines 20:12 / 20:45 / 21:00
  (idle timeout ~21:08 from the user's last input at ~17:08).
- 1st mid start 17:11: training got SIGTERM at 17:19:00 (exit 143, sender not
  found; not timeout, no kernel OOM). The script then ran eval (no best.pt) and the
  benchmark with the model switched off: those outputs moved to
  `claude/jobs/broken_mid_run_1711/`, not used. Script fixed (train retry loop,
  no eval/bench without best.pt); restarted 17:30 with `setsid -f` from step 250.
- 2nd kill 17:34 (while a GenesisGeo test loaded 1.2 GB). Cause found: training
  RSS grew 1.9 -> 2.5 GB (glibc keeps freed tensor buffers); under memory
  pressure something sends SIGTERM (no cgroup OOM, no daemon visible). Fix in
  `geo_lm/train.py`: mallopt mmap/trim threshold 4 MB -> RSS ~0.9 GB, speed
  ~370 tok/s (was ~440). 128 KB threshold + batch 16x2 was tried 17:43-17:47
  (295 tok/s, too slow), reverted. `train_mid.json` ckpt_every 250 -> 100.
  Lesson: nothing memory-heavy next to training (no model loading).
- User wants several proposer models compared, lightweight + 1-2 big, judged on
  fast one-domain solutions (not IMO). Added `pipeline/hf_tool.py`; GenesisGeo
  weights in `models/hf/` (gitignored); transformers 4.52.4 installed.
- Speed of 40 training steps (scratchpad, not kept): mini 2.1M ~1000 target
  tok/s; mid (6 layers, 256 dim) 5.1M ~440; small 11.2M ~200. Estimates in
  STATE. **Bigger model not started: user must approve.**

## 2026-11-10 16:32-16:50 · Cleanup and correctness check (15 min, user asked)

- `check.sh`: no warnings, nothing running. Tests: 85 passed (86 s).
- Recounted every `results/*/*.jsonl` against `docs/rezultati.md`: JGEX 205/231
  +5, `imo` 34 problems = 29 IMO-AG-30 (15 solved) + 5 others (2), imo_102 3/101.
  No duplicates. Docs match. Markdown links: none broken.
- AG1 numbers verified: 198/228 JGEX, 14/25 IMO-AG-30 match the results table
  in the official google-deepmind/alphageometry README. Note in rezultati.md updated.
- **Bug fixed:** `make` in `zpd_darbs/` regenerated the paper's tables from the
  full 231-problem `ddar_only.jsonl` (205/231 and 24 empty "--" rows in the
  stuck table), while the paper text describes the first 73-problem run.
  `make_figures.py` now uses the first `PAPER_JGEX_N = 73` rows; rebuild gives
  byte-identical tables. Figure PDFs differed only in timestamps: reverted.
- Paper builds (latexmk exit 0, no undefined refs in the final pass).
- **Bug fixed:** `pipeline/configs/default.json` (default for `solve.py`,
  `run_folder.py`, `search.py`) pointed at `geo-lm/runs/small/best.pt`, which
  was never trained, so default runs silently dropped the model. Now
  `mini_long`; docs/README.md updated. Smoke solve with default config: solved,
  no warning. Tests 85 passed after the change.
- Second 10 min: docs/README.md and docs/pipeline.md config lists now match
  the configs (`mini*`, `quick`/`tiny` need checkpoints not in git).
  `bench/sweep.py` resume no longer crashes on a line cut off by a killed job
  (drops it, reruns that problem); tested with a truncated file.
- `docs/geo-lm.md`: `mini_long` is the current model. `docs/tasks.md`: added
  done item 8.2a for the 11-10 standard benchmarks.
- Not committed (user did not ask).

## 2026-11-10 10:24-11:05 · Standard benchmarks: DDAR vs DDAR + mini_long, vs AG1

- User asked for DDAR and DDAR+LLM on the standard sets, estimate first,
  compare with AG1. Timed 7 samples (DDAR ~2 s, LLM 4-37 s); estimated
  ~1.3 h, worst ~3 h. Actual: 23 min (job `bench-ddar-llm`, exit 0).
- New `bench/run_benchmarks.sh`: `ddar_only` on all, then `mini_long_model`
  only on DDAR failures. 60 s, 2 GB per problem.
- JGEX-231: DDAR 205, +5 with the model = 210 (AG1: DD+AR 198, AG 228).
  IMO-AG-30 (29 of 30 in `imo.txt`, `2000_p1` missing): DDAR 15, +0 (AG1 14 / 25).
  `imo_102_requires_aux`: DDAR 0, model 3 of 101. Only 4 of the 8 model
  solves use one aux point; no problem hit the time limit (proposal quality
  is the limit). L053-1 still unsolved.
- Written into `docs/rezultati.md` (new section "Standarta kopas"). AG1 JGEX
  numbers (198, 228) are from memory of the paper: verify before citing.
- User left; safety stop armed (`sleep 16200; gh codespace stop`), session
  stops the Codespace itself at the end.

## 2026-11-10 08:10-08:55 · `mini_long` finished, evaluated (unattended)

- Committed the 11-09 work and the notes system (`8f00776`).
- Training resumed 08:12 from step 5000 with `claude/job.sh` (detached), ended
  08:45 at step 9000, exit 0, 33 min. Evals: 6000 → 0.342, 7500 → 0.292,
  9000 → 0.271 val loss. No machine stop this time.
- `eval_aux.py` on 200 problems: translatable 90.6%, exact 33% top-1, 49.5%
  top-4 (step 3000: 94.3%, 11.5%, 32%). More rejects with "no predicates" (33).
  Commit `3d77363`.
- JGEX stuck pair with `mini_long_model.json`: L058-9 solved (3.8 s, 1 aux);
  L053-1 not (search exhausted at depth 2, 4.8 s). `mini` solved both.
- Docs updated (rezultati, tasks 8.1, geo-lm, README); paper left as is (asks
  the user). Codespace stopped by the session at the end.

## 2026-11-10 08:00 · Why the 11-09 run stopped; logging system

- The 11-09 run was not covered in this log. From the session transcript
  (`~/.claude/projects/-workspaces-zpd/66ffca9c-….jsonl`): `mini_long` resumed at
  08:55 from step 3000; SIGTERM at 09:09:37 (step ~4600); restarted detached from
  `last.pt` (4500) at 09:10; the Claude session ended at 09:10; last log line and
  checkpoint step 5000 at 09:14:30; machine down until 11-10 06:17. Step-4500
  eval: val loss 0.406, exact 16% (best so far, saved as `best.pt`).
- Not the idle timeout: the API says 240 min, the stop came 20 min after the
  last input. Cause unknown (no stop reason in the API, no logs after the browser
  disconnect at 08:55:32); likely the free quota. Billing API returns 403 to
  this token. Details in STATE.md, Open problems.
- The job output of that run was in `/tmp` and was lost with the restart.
- New: `CLAUDE.md` (session rules), `claude/STATE.md` (current state, replaces
  the state table and "Next" list that were in this file), `claude/check.sh`
  (facts + warnings, run by a SessionStart hook in `.claude/settings.json`),
  `claude/job.sh` (long jobs with START/END lines and heartbeats on the
  persistent disk). Tested: normal exit, SIGTERM, and a job with no END line.

## 2026-11-09 08:30 · New Codespace set up

- New Codespace `glowing-barnacle-69499rgp76525wvr`, idle timeout **240 min**
  (checked with `gh api /user/codespaces/$CODESPACE_NAME`). 2 cores, 8 GB RAM.
- The automatic `setup.sh` failed halfway: the universal image's Yarn apt repo
  has an expired key, so `apt-get update` exits 100 (Python env was already
  done; TeX Live and tests were not). `setup.sh` now disables
  `/etc/apt/sources.list.d/yarn.list` before `apt-get update`. Rerun: 85 passed.
- The image has TeX Live 2019, whose titlesec 2.13 reads `\c@chapter` under
  `article` ("Undefined control sequence" at the first `\section`).
  `zpd.cls` now defines a zero `\c@chapter` if it is missing; `make` in
  `zpd_darbs/` builds both PDFs, numbering checked.
- Verified: `git pull` up to date; figure check on `varignon` OK; `run_folder`
  with `mini_long_model.json` solves 4/5 examples (the 5th is the deliberate
  `wrong_translation`); `eval_aux.py` on 20 val problems: exact 10% top-1,
  40% top-4 (in line with the 200-problem numbers). LaTeX aux files and caches
  removed.
- `gh api /user/codespaces` lists only the new Codespace; the old
  `cold-hobgoblin-…` is gone or not visible to this token. Check github.com/codespaces.

## 2026-11-09 · Switch to a new Codespace

**Why.** The 2 h training run on 11-05 died after exactly 30 minutes. This
Codespace (`cold-hobgoblin-q7q7jwp4w7qj29rxw`, created 2026-10-28) reports
`idle_timeout_minutes: 30`. The idle-timeout setting on
github.com/settings/codespaces is copied into a Codespace **only when it is
created**; there is no way to change it afterwards (web UI, `gh codespace edit`
and the REST API all lack it). So the only fix is a new Codespace.

`gh codespace create` cannot be run from inside a Codespace: its built-in
`GITHUB_TOKEN` is not allowed to create Codespaces ("you cannot create
codespaces with that repository"). It has to be done in the browser.

**What was made so that nothing is lost in the switch**

| Added | Purpose |
|---|---|
| `setup.sh` | one command for a fresh machine: `.venv-newclid` (Python 3.13, newclid 3.0.1, torch CPU, geo-lm), Newclid repo in `third_party/`, training data, TeX Live, then the 85 tests. Rerunnable. `--no-tex`, `--extract` |
| `.devcontainer/devcontainer.json` | default Codespace image + runs `setup.sh` on creation, so a new Codespace is ready without typing anything |
| `data/genesisgeo/{train,val}.txt.gz` | the exact 100k training split (seed 0) as 3.2 MB in git, instead of a 1 GB Hugging Face download and a regeneration |
| `geo-lm/runs/mini/`, `geo-lm/runs/mini_long/` | trained checkpoints, logs and configs in git (25 MB per `.pt`, force-added). `mini_long/last.pt` includes the optimizer, so training resumes from step 3000 |

Also cleaned up: the `mini_long` results are written into
[docs/rezultati.md](../docs/rezultati.md), [docs/tasks.md](../docs/tasks.md)
(8.1) and [docs/geo-lm.md](../docs/geo-lm.md); the empty
`results/jgex_ag_231/mini_long_model.jsonl` from the interrupted rerun was
deleted; the leftover links to the dropped `docs/present.md` were removed.
`setup.sh` was run here and passes (85 tests).

**Not carried over** (not in git, not needed): the 1 GB raw Parquet shard,
`runs/quick` (134 MB, over GitHub's 100 MB limit) and `runs/tiny`, both
superseded by `mini`.

### How to switch

1. github.com/settings/codespaces → **Default idle timeout**: as high as
   possible (240 min). Already set to 120.
2. github.com/Sweeeeeeeee/zpd → **Code → Codespaces → +** (branch `main`).
3. Wait for the "postCreateCommand" to finish (about 5-10 min: torch and
   TeX Live are the slow parts). Check with
   `.venv-newclid/bin/python -m pytest -q` → 85 passed.
4. Delete the old Codespace at github.com/codespaces (… → Delete), after
   checking that the new one works. Everything worth keeping is pushed.

**Remember.** The timeout counts from your last input, not from running jobs.
With 120 min, a job started right after your last message has a little under
2 h. Training that takes longer (the full run, 8.1, about 14 h) belongs on
Kaggle or in several sessions resumed from `last.pt`.

---

## 2026-11-05 13:04 · Evaluate the step-3000 checkpoint, commit, stop

- Decided not to resume `mini_long`; evaluate the checkpoint as it is.
- `eval_aux.py` on 200 held-out problems: 94.3% translatable, exact 11.5% top-1,
  32% top-4 (the 14-min `mini`: 91.6%, 6%, 21%).
- The rerun on the two stuck JGEX problems was interrupted and left an empty file.
- Commit `dc8b8e5`, pushed; Codespace stopped.

## 2026-11-05 ~12:00 · Status reports only

Two reports, nothing run or changed. Found that the run had stopped at step
3200 at 10:02, 30 min after the last input.

## 2026-11-05 09:25 · The 2 h unattended run

- Plan: ~75 min training of the 2.1M model for 9000 steps (checkpoint every
  250), evaluation, JGEX rerun, write-up, push, `gh codespace stop`.
- Training started 09:32:49, last log line 10:02:13 (step 3200): the Codespace
  idle timeout, still 30 min although 120 min had just been set in the
  settings. None of the later steps ran.

## 2026-11-05 07:45-09:21 · Tasks, short training, paper

- Task list split into smaller steps (`825b294`); one branch, `main`.
- 14-min training of the 2.1M model (`mini`, 1600 steps, val loss 0.57) and
  its evaluation; with it the pipeline solves both JGEX problems DD-AR gets
  stuck on (`fe49269`).
- ZPD paper: LaTeX template after the VIAA guidelines, RTU IZV styling, a
  preliminary version filled with project content (`15bcf14`, `4d617d1`).
- Repo tidy-up: one task numbering, complete docs index (`22a40e1`).

## 2026-11-04 · Latvian problems, domains

- 6333 problems from the NMS archive, 1499 geometry (`a0f9bcd`, task 7.1).
- Three domains with and without AR, plus the "easy" setting (`48f2175`, task 6).

## 2026-10-28/29 · Tools

DD-AR on CPU, rule toggling, transformer and training script, GenesisGeo
data, `solve()`, translation guide, problem store, tests, Latvian write-up
(tasks 1-5, `5682171` … `3478d84`).

