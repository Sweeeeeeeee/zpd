"""End-to-end smoke test for step 3, CPU-only, ~1 minute.

Builds a tokenizer from a few hand-written problems, trains a tiny model to
memorise their auxiliary constructions, checks greedy decoding and beam search,
then saves, reloads and verifies the reloaded model is identical.

    python scripts/smoke_transformer.py [--config configs/model_tiny.json] [--steps 300]
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
import tempfile
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geo_lm import (GeoTokenizer, ModelConfig, create_model, load_checkpoint,  # noqa: E402
                    pick_device, save_checkpoint)

EXAMPLES = [
    ("a b c = triangle a b c; d = on_tline d b a c, on_tline d c a b ? perp a d b c",
     "e = on_line e a d, on_line e b c"),
    ("a b c = triangle a b c; d = midpoint d b c; e = midpoint e a c ? para d e a b",
     "f = midpoint f a b"),
    ("a b c = triangle a b c; o = circle o a b c ? cong o a o b",
     "d = midpoint d a b"),
    ("a b = segment a b; c = on_circle c a b; d = on_circle d b a ? cong a c b d",
     "e = on_line e a b, on_line e c d"),
    ("a b c = iso_triangle a b c; d = midpoint d b c ? perp a d b c",
     "e = foot e a b c"),
    ("a b c = triangle a b c; d = angle_bisector d b a c ? eqangle a b a d a d a c",
     "e = on_circle e a b, on_line e a d"),
]


def make_batch(tok: GeoTokenizer, examples, device):
    seqs, starts = zip(*(tok.encode_example(p, a) for p, a in examples))
    T = max(map(len, seqs)) - 1
    x = torch.full((len(seqs), T), tok.pad_id, dtype=torch.long)
    y = torch.full((len(seqs), T), -100, dtype=torch.long)
    for i, (s, st) in enumerate(zip(seqs, starts)):
        s = torch.tensor(s)
        x[i, : len(s) - 1] = s[:-1]
        tgt = s[1:].clone()
        tgt[: st - 1] = -100            # loss only on the auxiliary construction + <eos>
        y[i, : len(s) - 1] = tgt
    return x.to(device), y.to(device)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--lr", type=float, default=3e-3)
    ap.add_argument("--device", default="auto")
    args = ap.parse_args()
    torch.manual_seed(0)
    device = pick_device(args.device)

    tok = GeoTokenizer.build([p + " " + a for p, a in EXAMPLES])
    cfg = ModelConfig.from_json(args.config) if args.config else ModelConfig(
        vocab_size=128, context_length=128, n_layer=2, n_head=2, n_embd=64, dropout=0.0)
    if cfg.vocab_size < len(tok):
        cfg = dataclasses.replace(cfg, vocab_size=len(tok))
    model = create_model(cfg, tok).to(device)
    print(f"device={device} vocab={len(tok)} params={model.num_parameters():,}")

    x, y = make_batch(tok, EXAMPLES, device)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.0)
    model.train()
    for step in range(1, args.steps + 1):
        _, loss = model(x, y)
        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()
        if step == 1 or step % 50 == 0:
            print(f"step {step:4d}  loss {loss.item():.4f}")

    correct = 0
    for p, a in EXAMPLES:
        prompt = torch.tensor(tok.encode_prompt(p))
        out = model.generate(prompt, max_new_tokens=32, eos_id=tok.eos_id)[0, len(prompt):]
        pred = tok.decode(out)
        correct += pred == a
        print(f"{'OK ' if pred == a else 'BAD'} {pred!r}")
    print(f"greedy exact match: {correct}/{len(EXAMPLES)}")

    hyps = model.beam_search(tok.encode_prompt(EXAMPLES[0][0]), beam_size=3,
                             max_new_tokens=32, eos_id=tok.eos_id)
    for h in hyps:
        print(f"beam score={h.score:7.3f} finished={h.finished} {tok.decode(h.tokens)!r}")

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "ckpt.pt"
        save_checkpoint(path, model, tok, opt, step=args.steps)
        model2, tok2, ckpt = load_checkpoint(path, map_location=device)
        model2.to(device)
        model.eval()
        same = torch.equal(model(x)[0], model2(x)[0]) and tok2.vocab == tok.vocab
        print(f"save/load identical: {same} (step={ckpt['step']})")

    ok = correct == len(EXAMPLES) and same and hyps[0].tokens == tok.encode(EXAMPLES[0][1])
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
