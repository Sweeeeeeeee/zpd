# Local CPU replication · 22 November 2026

The replication used an Intel Core i7-1355U on Linux x86-64, Python 3.12.1, PyTorch 2.15.0+cpu, Transformers 4.52.4, Newclid 3.0.1 and py-yuclid 3.0.0. The Newclid dataset checkout was at `ac6550732a95`. All weights came from the migrated local files. Timings were collected with concurrent low-priority jobs on a live host.

## Proof outcomes

Each JSONL row is one input problem. In build-failure messages, the local executable path is abbreviated to `yuclid`. The baseline used the project's seed-0 Yuclid configuration, a 60-second limit and a 2,048 MiB budget. The IMO experiment used the 29 available IDs in [problems.txt](imo/problems.txt). The other two suites used their complete dataset files. The JGEX follow-up evaluated heuristics, mini_long and mid separately on the 26 archived baseline failures. For IMO, the same three configurations ran on the 14 local baseline failures. The 101-problem auxiliary set received a fresh baseline only. Deduplicate by problem ID when combining wins. A depth-two proof can contribute to the combined benchmark even though the restricted-domain definition of an easy proof permits at most one auxiliary point.

## First-point prediction

The three Geo-LM checkpoints each saw the first 200 GenesisGeo validation cases with an auxiliary marker. GenesisGeo and SmolLM2-360M each saw the first 50 of those cases, using their respective geometry and few-shot prompts. All used beam width four. HF generation was capped at 20 new tokens and Geo-LM at 64; timings and match rates depend on these settings.

**Strict top 4** counts a case when at least one prediction matches the declared point and the reference predicates, keeping argument order and multiplicity. Predicate order and formatting are normalized. Empty reference predicates count as misses. This can undercount geometrically equivalent proposals. **Legacy top 4** uses the original evaluator’s unordered argument sets and ignores the declared point. Neither score tests whether a construction yields a proof.

[Prediction rows](../proposers/local-cpu/) include all four beams. [summary.json](summary.json) contains the numerator, denominator, timing median and baseline agreement for the published tables. Model source and weight locations are listed in the [registry](../../models/registry.json).

The separate AlphaGeometry smoke run completed the first three cases under a 4 GiB memory limit and two cores of CPU quota. An initial attempt stopped before the third prediction when the adapter encountered the reverse-congruence predicate `contrir`. After the adapter fix, the first two prompt strings were checked against the original code and the third case resumed. The stored rows include the model-loading time for each part. This sample checks compatibility only.

## Reproduce

From the repository root, activate the project Python environment. Unpack the committed GenesisGeo data using setup.sh and obtain any external weights needed for inference. To regenerate the page and paper insert from existing records:

```sh
python -m bench.publish
```

To repeat inference, choose a new output directory. The runners resume existing files. For example:

```sh
mkdir -p /tmp/zpd-repeat
export OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 HF_HUB_OFFLINE=1
for model in mini mini_long mid; do
  python bench/eval_proposers.py geolm "geo-lm/runs/$model/best.pt" \
    --n 200 --beam 4 --out "/tmp/zpd-repeat/$model"
done
python bench/eval_proposers.py hf models/hf/GenesisGeo --prompt genesisgeo \
  --dtype float32 --n 50 --out /tmp/zpd-repeat/GenesisGeo
python bench/eval_proposers.py hf models/hf/SmolLM2-360M-Instruct --prompt fewshot \
  --dtype float32 --n 50 --out /tmp/zpd-repeat/SmolLM2-360M-Instruct
```

For example, reproduce the IMO proofs and one JGEX follow-up with the solver environment's `yuclid` executable on PATH:

```sh
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
sets=third_party/Newclid/newclid/problems_datasets
python bench/sweep.py "$sets/imo.txt" pipeline/configs/ddar_only.json \
  /tmp/zpd-repeat/imo.jsonl --only results/local-cpu/imo/problems.txt --time 60
python bench/sweep.py "$sets/jgex_ag_231.txt" pipeline/configs/mid_model.json \
  /tmp/zpd-repeat/jgex-mid.jsonl --only results/jgex_ag_231/ddar_unsolved.txt --time 60
```
