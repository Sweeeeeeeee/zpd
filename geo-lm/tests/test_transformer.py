import json

import pytest
import torch

from geo_lm import (GeoTokenizer, ModelConfig, create_model, load_checkpoint, normalize,
                    save_checkpoint)
from geo_lm.tokenizer import SPECIAL_TOKENS, pretokenize

PROBLEMS = [
    "a b c = triangle a b c; d = midpoint d b c ? para d e a b",
    "a b c = triangle a b c; d = on_tline d b a c, on_tline d c a b ? perp a d b c",
    "a b c = triangle a b c; d = aconst a b a c 1pi/3 ? cong a1 b c d",
]


@pytest.fixture
def tok():
    return GeoTokenizer.build(PROBLEMS + ["e = foot e a b c"])


@pytest.fixture
def model(tok):
    torch.manual_seed(0)
    cfg = ModelConfig(vocab_size=len(tok) + 3, context_length=64, n_layer=2, n_head=2,
                      n_embd=32, dropout=0.0)
    return create_model(cfg, tok)


# ---------- config ----------
def test_config_json_roundtrip(tmp_path):
    cfg = ModelConfig(n_layer=3, n_head=2, n_embd=64)
    cfg.to_json(tmp_path / "m.json")
    assert ModelConfig.from_json(tmp_path / "m.json") == cfg


def test_config_nested_and_comments(tmp_path):
    (tmp_path / "c.json").write_text(json.dumps({"model": {"_comment": "x", "n_layer": 1}}))
    assert ModelConfig.from_json(tmp_path / "c.json").n_layer == 1


@pytest.mark.parametrize("bad", [{"n_embd": 30, "n_head": 4}, {"dropout": 1.0},
                                 {"n_layer": 0}, {"unknown_key": 1}])
def test_config_rejects_bad_values(bad):
    with pytest.raises(ValueError):
        ModelConfig.from_dict(bad)


# ---------- tokenizer ----------
def test_pretokenize_examples():
    assert pretokenize("d = aconst a b a c 1pi/3") == \
        ["d", "=", "aconst", "a", "b", "a", "c", "1", "##pi", "##/", "##3"]
    assert pretokenize("<bos>a b<aux>c;d") == ["<bos>", "a", "b", "<aux>", "c", ";", "d"]


def test_normalize_is_canonical():
    assert normalize("a b c=triangle a b c ;d=midpoint d a b?cong d a d b") == \
        "a b c = triangle a b c; d = midpoint d a b ? cong d a d b"


@pytest.mark.parametrize("text", PROBLEMS)
def test_roundtrip(tok, text):
    assert tok.decode(tok.encode(text)) == text
    assert tok.unknown_tokens(text) == []


def test_unknown_token(tok):
    ids = tok.encode("zzz_never_seen a b")
    assert ids[0] == tok.unk_id


def test_example_format(tok):
    ids, start = tok.encode_example(PROBLEMS[0], "e = foot e a b c")
    assert ids[0] == tok.bos_id and ids[start - 1] == tok.aux_id and ids[-1] == tok.eos_id
    assert ids[:start] == tok.encode_prompt(PROBLEMS[0])
    assert tok.decode(ids[start:]) == "e = foot e a b c"


def test_tokenizer_save_load(tok, tmp_path):
    tok.save(tmp_path / "t.json")
    assert GeoTokenizer.load(tmp_path / "t.json").vocab == tok.vocab
    assert tok.vocab[: len(SPECIAL_TOKENS)] == SPECIAL_TOKENS


# ---------- model ----------
def test_forward_shapes_and_loss(model, tok):
    x = torch.randint(0, len(tok), (3, 10))
    logits, loss = model(x, x)
    assert logits.shape == (3, 10, model.cfg.vocab_size)
    assert loss.ndim == 0 and torch.isfinite(loss)
    assert model(x, last_only=True)[0].shape == (3, 1, model.cfg.vocab_size)


def test_causality(model, tok):
    model.eval()
    x = torch.randint(0, len(tok), (1, 12))
    y = x.clone()
    y[0, 8:] = (y[0, 8:] + 1) % len(tok)
    assert torch.allclose(model(x)[0][:, :8], model(y)[0][:, :8], atol=1e-6)


def test_context_length_enforced(model):
    with pytest.raises(ValueError):
        model(torch.zeros(1, model.cfg.context_length + 1, dtype=torch.long))


def test_vocab_too_small(tok):
    with pytest.raises(ValueError):
        create_model(ModelConfig(vocab_size=len(tok) - 1, n_embd=32, n_head=2), tok)


def test_learns(model, tok):
    ids, _ = tok.encode_example(PROBLEMS[1], "e = foot e a b c")
    x = torch.tensor([ids[:-1]]); y = torch.tensor([ids[1:]])
    opt = torch.optim.AdamW(model.parameters(), lr=1e-2)
    first = None
    for _ in range(60):
        _, loss = model(x, y)
        first = first if first is not None else loss.item()
        opt.zero_grad(); loss.backward(); opt.step()
    assert loss.item() < first * 0.2


def test_greedy_generate_deterministic(model, tok):
    p = torch.tensor(tok.encode_prompt(PROBLEMS[0]))
    a = model.generate(p, 10, eos_id=tok.eos_id)
    b = model.generate(p, 10, eos_id=tok.eos_id)
    assert torch.equal(a, b) and a.shape[1] <= len(p) + 10
    assert torch.equal(a[0, : len(p)], p)


def test_generate_crops_long_context(model, tok):
    p = torch.randint(5, len(tok), (model.cfg.context_length + 5,))
    out = model.generate(p, 3)
    assert out.shape[1] == len(p) + 3


def test_sampling_with_seed(model, tok):
    p = torch.tensor(tok.encode_prompt(PROBLEMS[0]))
    g1, g2 = torch.Generator().manual_seed(1), torch.Generator().manual_seed(1)
    a = model.generate(p, 8, temperature=1.0, top_k=5, generator=g1)
    b = model.generate(p, 8, temperature=1.0, top_k=5, generator=g2)
    assert torch.equal(a, b)


def test_beam_search(model, tok):
    hyps = model.beam_search(tok.encode_prompt(PROBLEMS[0]), beam_size=4,
                             max_new_tokens=6, eos_id=tok.eos_id)
    assert 1 <= len(hyps) <= 4
    assert [h.score for h in hyps] == sorted((h.score for h in hyps), reverse=True)
    assert len({tuple(h.tokens) for h in hyps}) == len(hyps)
    greedy = model.generate(torch.tensor(tok.encode_prompt(PROBLEMS[0])), 6, eos_id=tok.eos_id)
    one = model.beam_search(tok.encode_prompt(PROBLEMS[0]), 1, 6, tok.eos_id)[0]
    n = len(tok.encode_prompt(PROBLEMS[0]))
    g = [t for t in greedy[0, n:].tolist() if t != tok.eos_id]
    assert one.tokens == g          # beam size 1 == greedy


def test_save_load(model, tok, tmp_path):
    opt = torch.optim.AdamW(model.parameters())
    save_checkpoint(tmp_path / "c.pt", model, tok, opt, step=7, extra={"note": "x"})
    m2, t2, ck = load_checkpoint(tmp_path / "c.pt")
    model.eval()
    x = torch.randint(0, len(tok), (2, 9))
    assert torch.equal(model(x)[0], m2(x)[0])
    assert t2.vocab == tok.vocab and ck["step"] == 7 and ck["extra"]["note"] == "x"
    assert "optimizer_state" in ck
    assert m2.lm_head.weight is m2.tok_emb.weight   # tying survives reload
