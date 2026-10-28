"""Hyperparameters for the geometry transformer (all settable from JSON)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


@dataclass
class ModelConfig:
    vocab_size: int = 1024      # must be >= len(tokenizer)
    context_length: int = 256   # max tokens the model sees (prompt + output)
    n_layer: int = 4
    n_head: int = 4
    n_embd: int = 256           # must be divisible by n_head
    dropout: float = 0.1
    bias: bool = False          # biases in Linear/LayerNorm
    tie_weights: bool = True    # share input embedding and output projection

    def __post_init__(self) -> None:
        for name in ("vocab_size", "context_length", "n_layer", "n_head", "n_embd"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                raise ValueError(f"{name} must be a positive integer, got {v!r}")
        if self.n_embd % self.n_head != 0:
            raise ValueError(f"n_embd ({self.n_embd}) must be divisible by n_head ({self.n_head})")
        if not 0.0 <= float(self.dropout) < 1.0:
            raise ValueError(f"dropout must be in [0, 1), got {self.dropout}")

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ModelConfig":
        known = {f.name for f in fields(cls)}
        # keys starting with "_" are treated as comments
        unknown = sorted(k for k in d if k not in known and not k.startswith("_"))
        if unknown:
            raise ValueError(f"unknown model config keys: {unknown}")
        return cls(**{k: v for k, v in d.items() if k in known})

    @classmethod
    def from_json(cls, path: str | Path) -> "ModelConfig":
        """Accepts a bare model config or a larger config with a "model" section."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data.get("model"), dict):
            data = data["model"]
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
