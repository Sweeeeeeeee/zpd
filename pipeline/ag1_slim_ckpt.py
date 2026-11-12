"""AG1 checkpoint -> weights only (drops the optimizer state).

The published checkpoint (models/ag1/ag_ckpt_vocab/checkpoint_10999999, 1.2 GB,
flax msgpack) holds the weights and the optimizer state. Inference uses only
the weights (TrainState.optimizer.target), but meliad's restore reads all of
it: the server peaked at 3.85 GB while loading and was killed on 2026-11-12.
This writes the weights as an .npz that pipeline/ag1_server.py loads after
building the model without a restore.

Run once in AG1's environment, with nothing big next to it (~2.5 GB peak):
    .venv-ag1/bin/python pipeline/ag1_slim_ckpt.py models/ag1/ag_ckpt_vocab
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from flax import serialization
from flax.traverse_util import flatten_dict


def main() -> None:
    d = Path(sys.argv[1])
    raw = (d / "checkpoint_10999999").read_bytes()
    state = serialization.msgpack_restore(raw)
    del raw
    print("top level:", list(state), "optimizer:", list(state["optimizer"]))
    target = state["optimizer"]["target"]
    step = int(state["optimizer"]["state"]["step"])
    del state
    flat = {"/".join(k): np.asarray(v) for k, v in flatten_dict(target).items()}
    n = sum(v.size for v in flat.values())
    print(f"step {step}: {len(flat)} arrays, {n / 1e6:.1f}M parameters, "
          f"dtypes {sorted({str(v.dtype) for v in flat.values()})}")
    out = d / "params_only.npz"
    np.savez(out, **flat)
    print("wrote", out, f"{out.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
