# Local PC and Kaggle training setup

This note captures the training setup that is safe to run on a stronger machine without restarting the pending translation workflow.

## Current status

The translation workflow is intentionally paused at 7.4 pending user verification. The repo is ready for training and comparison work, but the pilot / translation batch in 7.5 must not be started until the user explicitly approves it.

The training assets already in the repo are:

- `geo-lm/configs/train_mid.json` — 5.1M model, 9000 steps, the best-performing CPU run already produced in this repo.
- `geo-lm/configs/train_small.json` — 11M model, intended for GPU / stronger machine.
- `geo-lm/runs/mid/best.pt` — committed checkpoint from the completed run.
- `geo-lm/runs/mini_long/best.pt` — the default model used by the pipeline.

The repo also already contains the exact GenesisGeo data split and the pipeline config needed to evaluate and benchmark a trained model.

## Local PC setup (easy loading on a stronger machine)

### 1) Clone and prepare the environment

```bash
git clone https://github.com/Sweeeeeeeee/zpd.git
cd zpd
bash setup.sh --no-tex
```

`setup.sh` creates and uses `.venv-newclid`, installs the repo-specific Newclid tooling and training dependencies, unpacks the committed data split, and runs the test suite. It supports Python 3.11–3.13.

### 2) Pick a training target

Use the smaller `mid` model for a good balance of quality and runtime, or the `small` model if your machine has a GPU and you want the larger checkpoint.

```bash
source .venv-newclid/bin/activate
python -m geo_lm.train --config geo-lm/configs/train_mid.json
# or
python -m geo_lm.train --config geo-lm/configs/train_small.json
```

The training script resumes automatically from `last.pt` when you rerun the same config in the same output directory.

### 3) Faster local runs on a GPU

If the machine has CUDA, first confirm it is available with `python -c "import torch; print(torch.cuda.is_available())"`, then use an explicit device override and a short smoke run:

```bash
python -m geo_lm.train --config geo-lm/configs/train_small.json --device cuda --max_steps 50 --eval_generate 0 --resume false
```

Then continue with the full run:

```bash
python -m geo_lm.train --config geo-lm/configs/train_small.json --device cuda
```

The config is already wired for the repo layout; no extra path editing is needed beyond a clean git checkout.

### 4) Offline validation

Once a model exists, evaluate it on the held-out set:

```bash
python geo-lm/scripts/eval_aux.py geo-lm/runs/mid/best.pt --n 200 --beam 4 --out results/transformer/eval_mid_val200.json
```

Then benchmark the solver:

```bash
LLM=mid_model bench/run_benchmarks.sh
```

## Kaggle setup checklist

The repo is already set up for Kaggle usage, and the relevant notes from the project are consistent with the following workflow:

### Required items

- A phone-verified Kaggle account.
- A Kaggle notebook with a GPU runtime.
- A working `kaggle.json` in `~/.kaggle/`.
- The repo cloned into the notebook or mounted via the workspace.

### Kaggle setup

Use a Kaggle notebook with a GPU accelerator enabled. The training venv must see
Kaggle's preinstalled CUDA-enabled PyTorch; use `--system-site-packages` so the
venv inherits it rather than installing a separate CPU-only PyTorch.

```bash
!git clone https://github.com/Sweeeeeeeee/zpd.git
%cd /kaggle/working/zpd
!PYTHON="$(which python)" bash setup.sh --no-tex --system-site-packages
```

`setup.sh` runs the full test suite. The checked-in runner then verifies CUDA,
does a two-step training smoke test, trains/resumes the 11M `small` model,
evaluates the best checkpoint on 200 held-out problems, and runs tests again.
Checkpoints and evaluation output are copied under `/kaggle/working/zpd-artifacts`
so they appear in the notebook's output files.

```bash
!bash kaggle/train_and_test.sh
```

The runner is intentionally limited to training and validation; it does not
start the paused translation pipeline or the separate AG1 / large-proposer
comparison.

Do not put Kaggle API keys in the notebook or repository. If notebook upload or
artifact transfer via the Kaggle API is later needed, configure credentials
through Kaggle's own secret mechanism on a trusted machine.

## Verified repo facts

The repo has already been checked for the following:

- `setup.sh` installs the Newclid environment and training dependencies.
- `geo-lm/train.py` supports resuming from `last.pt` automatically.
- The training configs are present and consistent with the repo paths.
- The project already has a working `mid` checkpoint and a default mini-long checkpoint.
- The local one-step validation command succeeds with the repo's existing environment.
- A two-step CPU smoke run using the Kaggle model config succeeds locally; the
  Kaggle runner additionally requires CUDA and verifies it before training.
- `kaggle/train_and_test.sh` checks CUDA before doing any long work and copies
  final checkpoints and evaluation output into the Kaggle notebook output area.

## Do not start yet

The following remain intentionally deferred until the user explicitly approves the next phase:

- task 7.4 pilot
- task 7.5 translation batch run
- full Latvian scan / problem translation pipeline
- additional AG1 and large-model comparison work on Kaggle

This note is meant to make the training setup portable and reproducible on a better machine without reopening the translation workflow.
