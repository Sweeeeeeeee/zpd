"""Train a GeoTransformer on `PROBLEM <aux> AUX` text files.

    python -m geo_lm.train --config configs/train_tiny.json          # ~1 min CPU smoke run
    python -m geo_lm.train --config configs/train_small.json
    python -m geo_lm.train --config configs/train_small.json --lr 1e-3 --max_steps 5000

Every TrainConfig field can be set in the JSON file and overridden on the
command line. Relative paths in the JSON file are resolved against the file's
own directory.

Writes to out_dir:
    last.pt      latest checkpoint (model, tokenizer, optimizer, step); resumed automatically
    best.pt      checkpoint with the lowest validation loss
    log.jsonl    one JSON line per log / eval event
    config.json  the resolved training config

Loss is computed only on the auxiliary construction and <eos>, not the problem.
Evaluation reports validation loss and greedy exact-match accuracy of the
predicted auxiliary construction on held-out examples.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path

import torch

from .checkpoint import load_checkpoint, save_checkpoint
from .config import ModelConfig
from .model import create_model, pick_device
from .tokenizer import AUX, GeoTokenizer, normalize


@dataclass
class TrainConfig:
    model_config: str = "model_small.json"
    train_data: str = "../../data/genesisgeo/train.txt"
    val_data: str = "../../data/genesisgeo/val.txt"
    out_dir: str = "../runs/small"
    lr: float = 3e-4
    min_lr: float = 3e-5
    warmup_steps: int = 200
    weight_decay: float = 0.1
    grad_clip: float = 1.0
    batch_size: int = 32
    grad_accum: int = 1
    max_steps: int = 20000
    log_every: int = 50
    eval_every: int = 1000
    ckpt_every: int = 1000
    eval_generate: int = 200  # val examples decoded greedily for exact-match (0 = skip)
    max_examples: int = 0  # use only the first N training examples (0 = all)
    device: str = "auto"
    num_threads: int = 0  # torch CPU threads (0 = torch default)
    seed: int = 0
    resume: bool = True

    @classmethod
    def load(cls, path: str | None, overrides: dict) -> "TrainConfig":
        data: dict = {}
        base = Path.cwd()
        if path:
            data = json.loads(Path(path).read_text())
            data = {k: v for k, v in data.items() if not k.startswith("_")}
            base = Path(path).resolve().parent
        unknown = set(data) - {f.name for f in dataclasses.fields(cls)}
        if unknown:
            raise ValueError(f"unknown training config keys: {sorted(unknown)}")
        for key in ("model_config", "train_data", "val_data", "out_dir"):
            if key in data:
                data[key] = str((base / data[key]).resolve())
        data.update({k: v for k, v in overrides.items() if v is not None})
        return cls(**data)


def read_pairs(path: str | Path, limit: int = 0) -> list[tuple[str, str]]:
    """Lines of `PROBLEM <aux> AUX` -> [(problem, aux)]."""
    pairs = []
    with open(path) as f:
        for line in f:
            problem, sep, aux = line.strip().partition(AUX)
            if sep and problem.strip() and aux.strip():
                pairs.append((problem.strip(), aux.strip()))
                if limit and len(pairs) >= limit:
                    break
    return pairs


def encode_all(tok: GeoTokenizer, pairs, context: int) -> tuple[list[tuple[list[int], int]], int]:
    """Encode examples; drop those longer than context + 1 (input is seq[:-1])."""
    out, dropped = [], 0
    for problem, aux in pairs:
        seq, start = tok.encode_example(problem, aux)
        if len(seq) - 1 > context:
            dropped += 1
            continue
        out.append((seq, start))
    return out, dropped


def make_batch(examples, pad_id: int, device) -> tuple[torch.Tensor, torch.Tensor]:
    T = max(len(s) for s, _ in examples) - 1
    x = torch.full((len(examples), T), pad_id, dtype=torch.long)
    y = torch.full((len(examples), T), -100, dtype=torch.long)
    for i, (seq, start) in enumerate(examples):
        s = torch.tensor(seq)
        x[i, : len(s) - 1] = s[:-1]
        target = s[1:].clone()
        target[: start - 1] = -100  # loss only on the auxiliary construction + <eos>
        y[i, : len(s) - 1] = target
    return x.to(device), y.to(device)


def batches(examples, batch_size: int, rng: random.Random):
    """Endless length-bucketed batches: shuffle, sort chunks by length, shuffle batches."""
    while True:
        order = list(range(len(examples)))
        rng.shuffle(order)
        chunk = batch_size * 50
        out = []
        for i in range(0, len(order), chunk):
            part = sorted(order[i : i + chunk], key=lambda j: len(examples[j][0]))
            out.extend(part[k : k + batch_size] for k in range(0, len(part), batch_size))
        rng.shuffle(out)
        for b in out:
            yield [examples[j] for j in b]


def lr_at(step: int, cfg: TrainConfig) -> float:
    if step < cfg.warmup_steps:
        return cfg.lr * (step + 1) / cfg.warmup_steps
    progress = min(1.0, (step - cfg.warmup_steps) / max(1, cfg.max_steps - cfg.warmup_steps))
    return cfg.min_lr + 0.5 * (cfg.lr - cfg.min_lr) * (1 + math.cos(math.pi * progress))


@torch.no_grad()
def evaluate(model, tok, val_examples, val_pairs, cfg: TrainConfig, device) -> dict:
    model.eval()
    total, count = 0.0, 0
    for i in range(0, len(val_examples), cfg.batch_size):
        x, y = make_batch(val_examples[i : i + cfg.batch_size], tok.pad_id, device)
        _, loss = model(x, y)
        n = int((y != -100).sum())
        total += loss.item() * n
        count += n
    result = {"val_loss": total / max(count, 1)}
    if cfg.eval_generate and val_pairs:
        hits = 0
        sample = val_pairs[: cfg.eval_generate]
        for problem, aux in sample:
            prompt = torch.tensor(tok.encode_prompt(problem))
            room = model.cfg.context_length - len(prompt)
            if room <= 0:
                continue
            out = model.generate(prompt, max_new_tokens=min(room, 128), eos_id=tok.eos_id)
            pred = tok.decode(out[0, len(prompt) :].tolist())
            hits += pred == normalize(aux)
        result["exact_match"] = hits / len(sample)
    model.train()
    return result


def train(cfg: TrainConfig) -> dict:
    random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)
    if cfg.num_threads:
        torch.set_num_threads(cfg.num_threads)
    device = pick_device(cfg.device)
    out = Path(cfg.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "config.json").write_text(json.dumps(dataclasses.asdict(cfg), indent=2) + "\n")
    log_file = open(out / "log.jsonl", "a")

    def log(event: dict) -> None:
        log_file.write(json.dumps(event) + "\n")
        log_file.flush()
        print(" ".join(f"{k}={v:.4g}" if isinstance(v, float) else f"{k}={v}" for k, v in event.items()), flush=True)

    train_pairs = read_pairs(cfg.train_data, cfg.max_examples)
    val_pairs = read_pairs(cfg.val_data)
    model_cfg = ModelConfig.from_json(cfg.model_config)

    step, best = 0, float("inf")
    ckpt_path = out / "last.pt"
    if cfg.resume and ckpt_path.exists():
        model, tok, ckpt = load_checkpoint(ckpt_path, map_location=device)
        model.to(device).train()
        step = ckpt["step"] or 0
        best = ckpt["extra"].get("best_val_loss", best)
        print(f"resumed from {ckpt_path} at step {step}")
    else:
        tok = GeoTokenizer.build(p + " " + a for p, a in train_pairs)
        model = create_model(model_cfg, tok).to(device)
        ckpt = None

    train_ex, dropped = encode_all(tok, train_pairs, model.cfg.context_length)
    val_ex, val_dropped = encode_all(tok, val_pairs, model.cfg.context_length)
    if not train_ex:
        raise ValueError("no training examples fit the context length")
    unk = sum(s.count(tok.unk_id) for s, _ in val_ex)
    log({"event": "start", "device": str(device), "params": model.num_parameters(),
         "vocab": len(tok), "train": len(train_ex), "val": len(val_ex),
         "dropped_too_long": dropped + val_dropped, "val_unk_tokens": unk, "step": step})

    decay = [p for p in model.parameters() if p.dim() >= 2]
    no_decay = [p for p in model.parameters() if p.dim() < 2]
    opt = torch.optim.AdamW(
        [{"params": decay, "weight_decay": cfg.weight_decay},
         {"params": no_decay, "weight_decay": 0.0}],
        lr=cfg.lr, betas=(0.9, 0.95),
    )
    if ckpt is not None and "optimizer_state" in ckpt:
        opt.load_state_dict(ckpt["optimizer_state"])

    use_amp = device.type == "cuda" and torch.cuda.is_bf16_supported()
    stream = batches(train_ex, cfg.batch_size, random.Random(cfg.seed + step))
    model.train()
    t0, seen_tokens, running = time.time(), 0, 0.0

    def checkpoint(path: Path) -> None:
        save_checkpoint(path, model, tok, opt, step=step, extra={"best_val_loss": best, "train_config": dataclasses.asdict(cfg)})

    while step < cfg.max_steps:
        for group in opt.param_groups:
            group["lr"] = lr_at(step, cfg)
        loss_sum = 0.0
        for _ in range(cfg.grad_accum):
            x, y = make_batch(next(stream), tok.pad_id, device)
            with torch.autocast(device.type, dtype=torch.bfloat16, enabled=use_amp):
                _, loss = model(x, y)
            (loss / cfg.grad_accum).backward()
            loss_sum += loss.item() / cfg.grad_accum
            seen_tokens += int((y != -100).sum())
        if cfg.grad_clip:
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        running = loss_sum if step == 1 else 0.9 * running + 0.1 * loss_sum

        if step % cfg.log_every == 0 or step == cfg.max_steps:
            dt = time.time() - t0
            log({"event": "train", "step": step, "loss": loss_sum, "loss_avg": running,
                 "lr": lr_at(step, cfg), "target_tok_per_s": seen_tokens / max(dt, 1e-9)})
            t0, seen_tokens = time.time(), 0
        if step % cfg.eval_every == 0 or step == cfg.max_steps:
            result = evaluate(model, tok, val_ex, val_pairs, cfg, device)
            if result["val_loss"] < best:
                best = result["val_loss"]
                checkpoint(out / "best.pt")
            log({"event": "eval", "step": step, **result, "best_val_loss": best})
        if step % cfg.ckpt_every == 0 or step == cfg.max_steps:
            checkpoint(ckpt_path)

    log_file.close()
    return {"step": step, "best_val_loss": best}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", help="training config JSON")
    for f in dataclasses.fields(TrainConfig):
        kind = {"bool": lambda s: s.lower() in ("1", "true", "yes")}.get(f.type, None)
        kind = kind or {"int": int, "float": float, "str": str}[f.type]
        ap.add_argument(f"--{f.name}", type=kind, default=None)
    args = vars(ap.parse_args())
    config = args.pop("config")
    cfg = TrainConfig.load(config, args)
    print(json.dumps(train(cfg)))


if __name__ == "__main__":
    main()
