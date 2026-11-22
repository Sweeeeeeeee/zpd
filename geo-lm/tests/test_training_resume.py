"""An interrupted CPU run recovers its shuffled batches, dropout and optimizer."""
import dataclasses
import json

import pytest
import torch

from geo_lm import train as training
from geo_lm.checkpoint import load_checkpoint


def test_interrupted_training_matches_uninterrupted(tmp_path, monkeypatch):
    data = tmp_path / "data.txt"
    data.write_text("".join(f"a b c {n} <aux> d : foot d a b c\n" for n in range(9)))
    model = tmp_path / "model.json"
    model.write_text(json.dumps(dict(n_layer=1, n_head=2, n_embd=16, context_length=32,
                                     vocab_size=64, dropout=0.2)))
    cfg = training.TrainConfig(model_config=str(model), train_data=str(data),
                               val_data=str(data), out_dir=str(tmp_path / "full"),
                               batch_size=2, grad_accum=2, max_steps=5, ckpt_every=2,
                               eval_every=2, eval_generate=0, num_threads=1, device="cpu")
    training.train(cfg)
    split = dataclasses.replace(cfg, out_dir=str(tmp_path / "split"))
    save = training.save_checkpoint

    def interrupt(path, *args, **kwargs):
        save(path, *args, **kwargs)
        if path.name == "last.pt" and kwargs["step"] == 2:
            raise InterruptedError

    with monkeypatch.context() as patch:
        patch.setattr(training, "save_checkpoint", interrupt)
        with pytest.raises(InterruptedError):
            training.train(split)
    training.train(split)
    full = load_checkpoint(tmp_path / "full/last.pt")[2]
    resumed = load_checkpoint(tmp_path / "split/last.pt")[2]
    for key, weights in full["model_state"].items():
        assert torch.equal(weights, resumed["model_state"][key])
    for key in ("batches_consumed", "loss_avg", "best_val_loss"):
        assert full["extra"][key] == resumed["extra"][key]
