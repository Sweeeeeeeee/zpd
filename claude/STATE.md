# State

Updated: 2026-11-16 (21:45 UTC; Codespace kept running at user's request)

Claude's own notes: overwrite this file at the end of every session so it is
true *now*. History goes to [LOG.md](LOG.md), not here. Facts that a command can
tell (git status, running jobs, timeout) come from `claude/check.sh`; this file
holds what a command cannot tell.

User pause: the translation workflow was intentionally left at 7.4 pending user verification; it is not to be resumed automatically.

Kaggle handoff (2026-11-16): the user wants GPU training/tests. The setup in `kaggle/train_and_test.sh` and `docs/training_setup.md` is committed locally in `d52a8c3` (plus later handoff-note commit `49e1527`) but not pushed; Kaggle execution has not started. Local verification: 90 tests passed and the 11M model completed a 2-step CPU smoke run. To proceed on Kaggle, push the commit, select a GPU accelerator, run `PYTHON="$(which python)" bash setup.sh --no-tex --system-site-packages`, then `bash kaggle/train_and_test.sh`. It checks CUDA before long work, trains/resumes `small`, evaluates 200 held-out examples, runs tests, and copies artifacts to `/kaggle/working/zpd-artifacts`. The API key pasted into chat was not stored or used; user should revoke/rotate it and must not send a replacement through chat. The translation workflow remains paused.

Codespace and disk (2026-11-16 21:43 UTC): user explicitly reversed the earlier stop request and asked to keep this Codespace running. `gh codespace list` reports `glowing-barnacle-69499rgp76525wvr` as Available; do not stop it. Health check found no active jobs and no unaccounted warnings. Workspace disk had 1.4 GB free of 32 GB (96% used); `/tmp` is a separate filesystem with 40 GB free. Inspected sizes: `models/` 8.1 GB (including 6.4 GB HF weights and 1.8 GB AG1 checkpoint), `.venv-newclid` 1.8 GB, `.venv-ag1` 2.6 GB, `.git` 972 MB. Pip/HF caches ~2.2 MB and `.pytest_cache` 36 KB; these are the only obvious caches and too small to materially help, so no files were deleted. Git has ~906 MiB loose objects; prior notes mention unreachable history, but no GC/pruning was run because it may discard recoverable history. Recheck disk before any large downloads or training.

## Where things are

| | |
|---|---|
| Our models | `mid` **finished, 9000 steps** (`geo-lm/runs/mid/best.pt`, 5.1M): val 0.235, exact 39% / 53.5%, JGEX +5/26, IMO 2015 P3 (first IMO-AG-30 gain over DDAR), imo_102 6/101. Step-7500 results kept as `results/*/mid_7500_model.jsonl`. `docs/rezultati.md` and the paper report all three models; `default.json` still uses `mini_long` (switching it to `mid` is open) |
| Done | tasks 1-6, 7.1-7.3, 8.2, 8.2a, 12.1-12.3 ([docs/tasks.md](../docs/tasks.md)) |
| Proposer comparison | held-out evaluation done 11-12 for all models (`results/proposers/`, table `bench/proposer_table.py`; big models on small samples, AG1 skipped: killed). Domain comparison: only `full` partly (DDAR 5/60 at 60 s, Python engine too slow; heuristics 0/31). Rest open; resumable with `claude/jobs/stream_b.sh` / `pre_translation.sh` |
| HF models | in `models/hf/` (gitignored, 6.5 GB). Measured 11-12: float32 for SmolLM2 (bf16 2x slower here), bf16 from 0.6B; s/problem 13 / 25 / 28 (GenesisGeo) / 89 (Qwen3) / 464 (Qwen2.5) |
| AG1 | works (`pipeline/ag1_tool.py` + `ag1_server.py`, env `.venv-ag1`, weights `models/ag1/ag_ckpt_vocab/params_only.npz`), verified against the README example. On this Codespace: 40 s load + 75 s JIT + ~23 s/call (beam 2), 2.7 GB, and SIGTERMed in 2 of 5 runs. Not usable within the 60 s budget here; for Kaggle |
| Paper | `zpd_darbs/preliminary` 14 pages: three models, benchmarks with heuristics column vs AG1, proposer comparison, literature comparison, problem-set sorting. Red placeholders left: personal data, rest of 8.4, translation and scan, final conclusions |
| Blocker | the problem set (7.4-7.6): the scan (9-11) cannot start without it. Translation scheme agreed with the user 11-12 and written into docs/tasks.md task 7 (prefilter + agent sorting, pilot of 10 together, two translations + numeric/free-point checks + back-translation, user reviews flagged ones and a 10% audit) |
| Codespace budget | user 11-10: 35 h of 2-core time left this month; ~6 h used since (11-10 evening + 11-12 ~2 h). Free plan 120 core-h/month |
| Disk | 1.4 GB free at the 2026-11-16 21:43 UTC check (96% used); large consumers are model weights, Python environments, and Git objects. Do not remove those without inspecting/approval |
| Machine | Codespace `glowing-barnacle-69499rgp76525wvr`, 2 cores, 7 GB available RAM, idle timeout 240 min |

## Open problems

1. **SIGTERM under memory pressure.** Processes above ~2.5-3 GB RSS get
   SIGTERM from outside the container (no cgroup limit, no OOM kill recorded,
   no killer process visible inside). Hit: training 11-10 (2.5 GB), AG1 server
   11-12 (3.85 GB full restore; 2.7 GB in 2 of 5 runs). Keep anything long
   below ~2.5 GB here.
2. **Why the Codespace stopped on 11-09** (~09:15 UTC): still unconfirmed,
   likely the free quota; user should check github.com/settings/billing.
3. `git gc --prune=now` (frees ~566 MB in `.git`) was blocked by the permission
   classifier; the user can run `git reflog expire --expire-unreachable=now --all && git gc --prune=now`.

## Rules learned the hard way

- `/tmp` is wiped when the Codespace restarts: run long jobs with `claude/job.sh`.
- The idle timeout counts from the user's last input, not from running jobs.
- A background job started by Claude dies with the session; use `setsid nohup claude/job.sh ...`.
- `run_mid_pipeline.sh` ends by *waiting* for its hard deadline and then stops the
  Codespace: kill its process group when finished interactively.
- `claude/jobs/mid-pipeline.out` is appended across runs: match on the new
  run's start line, not on any line (a false trigger happened 11-12).
- Never `pkill -f <pattern>` that also matches the current shell's command line.
- AG1's `build_problem` loops forever on a numerically false goal: test with true problems.
- `gh codespace create` and the billing API do not work with the Codespace token.
- Session transcripts (`~/.claude/projects/-workspaces-zpd/*.jsonl`) record what an
  earlier session actually ran.

## Next

1. Ask the user before starting: 7.4 pilot of 10 (working_set.csv, kit in
   docs/translation_kit.md), done together with the user.
2. Domain comparison: 60 s is too short for the Python engine here (DDAR 32
   timeouts of 60 in `full`). Decide with the user: bigger budget (e.g. 180 s)
   for domains, fewer problems, or a faster machine. Resume: `DOMAINS=... bench/run_compare.sh`.
3. Heuristics on imo_102 (`LLM=heuristics_only bench/run_benchmarks.sh imo_102_requires_aux`, ~1 h).
4. Kaggle GPU training of the 11M `small` model: see the handoff above. The
   runner/setup changes are committed locally but not pushed; Kaggle execution
   not started.
5. Folder restructure from `docs/models.md` (geo-lm -> models/...), full tests.
6. User: personal data for the paper (12.4); 11-09 stop reason; whether
   `default.json` should use `mid`.
7. Sorting check was done by Claude (user delegated); `bench/hf_probe.py` is
   superseded by `bench/eval_proposers.py`.
