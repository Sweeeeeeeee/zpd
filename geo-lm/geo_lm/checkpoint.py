"""Save / load model + tokenizer (+ optional optimizer state) in one file."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import torch

from .config import ModelConfig
from .model import GeoTransformer
from .tokenizer import GeoTokenizer

FORMAT = "geo_lm/v1"


def save_checkpoint(
    path: str | Path,
    model: GeoTransformer,
    tokenizer: GeoTokenizer | None = None,
    optimizer: torch.optim.Optimizer | None = None,
    step: int | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Atomic write: a crash mid-save never corrupts an existing checkpoint."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ckpt: dict[str, Any] = {
        "format": FORMAT,
        "model_config": model.cfg.to_dict(),
        "model_state": model.state_dict(),
        "tokenizer_vocab": tokenizer.vocab if tokenizer is not None else None,
        "step": step,
        "extra": extra or {},
    }
    if optimizer is not None:
        ckpt["optimizer_state"] = optimizer.state_dict()
    tmp = path.with_name(path.name + ".tmp")
    torch.save(ckpt, tmp)
    os.replace(tmp, path)


def _torch_load(path: str | Path, map_location: Any) -> dict[str, Any]:
    try:
        return torch.load(path, map_location=map_location, weights_only=True)
    except TypeError:  # torch < 1.13 has no weights_only
        return torch.load(path, map_location=map_location)


def load_checkpoint(
    path: str | Path, map_location: str | torch.device = "cpu"
) -> tuple[GeoTransformer, GeoTokenizer | None, dict[str, Any]]:
    """Returns (model in eval mode, tokenizer or None, raw checkpoint dict).
    The raw dict holds 'step', 'extra' and 'optimizer_state' (if saved) for resuming."""
    ckpt = _torch_load(path, map_location)
    if ckpt.get("format") != FORMAT:
        raise ValueError(f"{path}: unknown checkpoint format {ckpt.get('format')!r}")
    cfg = ModelConfig.from_dict(ckpt["model_config"])
    model = GeoTransformer(cfg)
    model.load_state_dict(ckpt["model_state"])
    model.eval()
    tok = GeoTokenizer(ckpt["tokenizer_vocab"]) if ckpt.get("tokenizer_vocab") else None
    if tok is not None and len(tok) > cfg.vocab_size:
        raise ValueError(f"{path}: tokenizer larger than model vocab_size")
    return model, tok, ckpt
