# State

Updated: 2026-11-12 ~21:00 UTC (session 51d9920c)

Claude's own notes: overwrite this file at the end of every session so it is
true *now*. History goes to [LOG.md](LOG.md), not here. Facts that a command can
tell (git status, running jobs, timeout) come from `claude/check.sh`; this file
holds what a command cannot tell.

## Where things are

| | |
|---|---|
| Our models | `mid` **finished, 9000 steps** (`geo-lm/runs/mid/best.pt`, 5.1M): val 0.235, exact 39% / 53.5%, JGEX +5/26, IMO 2015 P3 (first IMO-AG-30 gain over DDAR), imo_102 6/101. Step-7500 results kept as `results/*/mid_7500_model.jsonl`. `docs/rezultati.md` and the paper report all three models; `default.json` still uses `mini_long` (switching it to `mid` is open) |
| Done | tasks 1-6, 7.1, 8.2, 8.2a, 12.1-12.3 ([docs/tasks.md](../docs/tasks.md)) |
| Proposer comparison | held-out evaluation done 11-12 for all models (`results/proposers/`, table `bench/proposer_table.py`; big models on small samples, AG1 skipped: killed). Domain comparison: only `full` partly (DDAR 5/60 at 60 s, Python engine too slow; heuristics 0/31). Rest open; resumable with `claude/jobs/stream_b.sh` / `pre_translation.sh` |
| HF models | in `models/hf/` (gitignored, 6.5 GB). Measured 11-12: float32 for SmolLM2 (bf16 2x slower here), bf16 from 0.6B; s/problem 13 / 25 / 28 (GenesisGeo) / 89 (Qwen3) / 464 (Qwen2.5) |
| AG1 | works (`pipeline/ag1_tool.py` + `ag1_server.py`, env `.venv-ag1`, weights `models/ag1/ag_ckpt_vocab/params_only.npz`), verified against the README example. On this Codespace: 40 s load + 75 s JIT + ~23 s/call (beam 2), 2.7 GB, and SIGTERMed in 2 of 5 runs. Not usable within the 60 s budget here; for Kaggle |
| Paper | `zpd_darbs/preliminary` 14 pages: three models, benchmarks with heuristics column vs AG1, proposer comparison, literature comparison, problem-set sorting. Red placeholders left: personal data, rest of 8.4, translation and scan, final conclusions |
| Blocker | the problem set (7.2-7.6): the scan (9-11) cannot start without it. Translation scheme agreed with the user 11-12 and written into docs/tasks.md task 7 (prefilter + agent sorting, pilot of 10 together, two translations + numeric/free-point checks + back-translation, user reviews flagged ones and a 10% audit) |
| Codespace budget | user 11-10: 35 h of 2-core time left this month; ~6 h used since (11-10 evening + 11-12 ~2 h). Free plan 120 core-h/month |
| Disk | ~3.5 GB free after AG1 (env 2.4 GB, checkpoint 1.8 GB incl. npz). `.git` holds 566 MB of unreachable old backup objects |
| Machine | Codespace `glowing-barnacle-69499rgp76525wvr`, 2 cores, 8 GB, idle timeout 240 min |

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
4. AG1, Qwen2.5-1.5B and the full 200 for GenesisGeo / Qwen3: Kaggle (GPU). User asked Claude to do it;
   waiting for the user's Kaggle token (~/.kaggle/kaggle.json, phone-verified account) and OK to push a
   private notebook (plan in the 11-12 transcript: clone the public repo, HF models, AG1 from the HF mirror).
5. Folder restructure from `docs/models.md` (geo-lm -> models/...), full tests.
6. User: personal data for the paper (12.4); 11-09 stop reason; whether
   `default.json` should use `mid`.
7. Sorting check was done by Claude (user delegated); `bench/hf_probe.py` is
   superseded by `bench/eval_proposers.py`.
