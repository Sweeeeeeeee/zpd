# State

Updated: 2026-11-12 ~17:30 UTC (session 51d9920c)

Claude's own notes: overwrite this file at the end of every session so it is
true *now*. History goes to [LOG.md](LOG.md), not here. Facts that a command can
tell (git status, running jobs, timeout) come from `claude/check.sh`; this file
holds what a command cannot tell.

## Where things are

| | |
|---|---|
| Our models | `mid` **finished, 9000 steps** (`geo-lm/runs/mid/best.pt`, 5.1M): val 0.235, exact 39% / 53.5%, JGEX +5/26, IMO 2015 P3 (first IMO-AG-30 gain over DDAR), imo_102 6/101. Step-7500 results kept as `results/*/mid_7500_model.jsonl`. `docs/rezultati.md` and the paper report all three models; `default.json` still uses `mini_long` (switching it to `mid` is open) |
| Done | tasks 1-6, 7.1, 8.2, 8.2a, 12.1-12.3 ([docs/tasks.md](../docs/tasks.md)) |
| Proposer comparison | [docs/models.md](../docs/models.md) has the table and status. Configs: 11 proposers x 3 domains in `pipeline/configs/compare/` (`bench/compare_configs.py`); list in `models/registry.json`. **Nothing of the comparison has been run yet** |
| HF models | in `models/hf/` (gitignored, 6.5 GB): GenesisGeo, SmolLM2-135M/360M, Qwen3-0.6B-Base, Qwen2.5-1.5B. None probed after the 11-12 fixes (comma split, stop at `;`, 20 tokens). `bench/hf_probe.py` is written, never run |
| AG1 | works (`pipeline/ag1_tool.py` + `ag1_server.py`, env `.venv-ag1`, weights `models/ag1/ag_ckpt_vocab/params_only.npz`), verified against the README example. On this Codespace: 40 s load + 75 s JIT + ~23 s/call (beam 2), 2.7 GB, and SIGTERMed in 2 of 5 runs. Not usable within the 60 s budget here; for Kaggle |
| Paper | `zpd_darbs/preliminary` updated 11-12: mini / mini_long / mid side by side, full JGEX-231 / IMO-AG-30 / IMO-aux benchmarks vs AG1, 12 pages. Red placeholders left: personal data, literature comparison, proposer comparison (8.4), Latvian scan, final conclusions |
| Blocker | the problem set (7.2-7.6): the scan (9-11) cannot start without it |
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

1. Probe the HF models one at a time with `bench/hf_probe.py` (5 problems, beam 2
   and 4): GenesisGeo first (speed after the stop-at-`;` change), then
   Qwen3-0.6B-Base, SmolLM2-135M/360M, Qwen2.5-1.5B. Drop any with ~0 exact
   and ~0 translatable.
2. Run the comparison: `bench/run_compare.sh` (light: heuristics, mini,
   mini_long, mid), then the HF models that passed; `bench/compare_table.py`.
   One domain first to measure the cost.
3. AG1 and any 7B-class model: on Kaggle (GPU), not here.
4. Folder restructure from `docs/models.md` (geo-lm -> models/...), full tests.
5. User: personal data for the paper (12.4); 11-09 stop reason; whether `default.json` should use `mid`.
6. 7.2 Sort the 1499 Latvian geometry problems.
