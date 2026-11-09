# Work log

What was done in each working session with Claude Code, why things are the way
they are, and where to pick up. Newest first. Times are UTC.

**Current state (2026-11-09)**

| | |
|---|---|
| Done | tasks 1-6, 7.1, 8.2, 12.1-12.3 ([docs/tasks.md](../docs/tasks.md)) |
| Best model | `geo-lm/runs/mini_long/best.pt`, 2.1M params, step 3000, val loss 0.49, top-4 exact 32% |
| Blocker | the problem set (7.2-7.6): nothing in the scan (9-11) can start without it |
| Machine | moving to a new Codespace (the old one has a fixed 30-min idle timeout) |

---

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

---

## Next

1. Switch Codespace (above).
2. **7.2** Sort the 1499 geometry problems into statable / not statable,
   with an agent and a short guide, as `docs/tasks.md` suggests.
3. 7.3-7.4 Pick the working set, translate and scan a pilot batch of ~10.
4. In the background, if wanted: resume `mini_long`
   (`cd geo-lm && ../.venv-newclid/bin/python -m geo_lm.train --config configs/train_mini_long.json`,
   ~60 min left) or do the full run (8.1) on Kaggle.
5. Rerun `mini_long` on the two stuck JGEX problems
   (`bench/sweep.py … pipeline/configs/mini_long_model.json`).
