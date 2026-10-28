"""Decoder-only transformer, written from scratch. No pretrained weights."""
from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import ModelConfig


def pick_device(prefer: str = "auto") -> torch.device:
    if prefer != "auto":
        return torch.device(prefer)
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


class LayerNorm(nn.Module):
    """LayerNorm with optional bias (nn.LayerNorm only got bias=False in torch 2.1)."""

    def __init__(self, dim: int, bias: bool):
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))
        self.bias = nn.Parameter(torch.zeros(dim)) if bias else None

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.layer_norm(x, self.weight.shape, self.weight, self.bias, 1e-5)


class CausalSelfAttention(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.n_head = cfg.n_head
        self.head_dim = cfg.n_embd // cfg.n_head
        self.qkv = nn.Linear(cfg.n_embd, 3 * cfg.n_embd, bias=cfg.bias)
        self.proj = nn.Linear(cfg.n_embd, cfg.n_embd, bias=cfg.bias)
        self.attn_dropout = cfg.dropout
        self.resid_drop = nn.Dropout(cfg.dropout)
        self.use_sdpa = hasattr(F, "scaled_dot_product_attention")  # torch >= 2.0
        if not self.use_sdpa:
            n = cfg.context_length
            mask = torch.tril(torch.ones(n, n, dtype=torch.bool)).view(1, 1, n, n)
            self.register_buffer("mask", mask, persistent=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(C, dim=2)
        q = q.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        k = k.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        v = v.view(B, T, self.n_head, self.head_dim).transpose(1, 2)
        p = self.attn_dropout if self.training else 0.0
        if self.use_sdpa:
            y = F.scaled_dot_product_attention(q, k, v, dropout_p=p, is_causal=True)
        else:
            att = (q @ k.transpose(-2, -1)) / math.sqrt(self.head_dim)
            att = att.masked_fill(~self.mask[:, :, :T, :T], float("-inf"))
            att = F.dropout(F.softmax(att, dim=-1), p, self.training)
            y = att @ v
        y = y.transpose(1, 2).contiguous().view(B, T, C)
        return self.resid_drop(self.proj(y))


class MLP(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.fc_in = nn.Linear(cfg.n_embd, 4 * cfg.n_embd, bias=cfg.bias)
        self.fc_out = nn.Linear(4 * cfg.n_embd, cfg.n_embd, bias=cfg.bias)
        self.drop = nn.Dropout(cfg.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.drop(self.fc_out(F.gelu(self.fc_in(x))))


class Block(nn.Module):
    """Pre-LayerNorm transformer block."""

    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.ln1 = LayerNorm(cfg.n_embd, cfg.bias)
        self.attn = CausalSelfAttention(cfg)
        self.ln2 = LayerNorm(cfg.n_embd, cfg.bias)
        self.mlp = MLP(cfg)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.ln1(x))
        return x + self.mlp(self.ln2(x))


@dataclass
class Hypothesis:
    tokens: list[int]   # generated ids (prompt and <eos> excluded)
    logprob: float      # sum of token log-probabilities (including <eos> if finished)
    score: float        # length-normalised logprob used for ranking
    finished: bool      # True if the model emitted <eos>


class GeoTransformer(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.tok_emb = nn.Embedding(cfg.vocab_size, cfg.n_embd)
        self.pos_emb = nn.Embedding(cfg.context_length, cfg.n_embd)
        self.drop = nn.Dropout(cfg.dropout)
        self.blocks = nn.ModuleList(Block(cfg) for _ in range(cfg.n_layer))
        self.ln_f = LayerNorm(cfg.n_embd, cfg.bias)
        self.lm_head = nn.Linear(cfg.n_embd, cfg.vocab_size, bias=False)
        if cfg.tie_weights:
            self.lm_head.weight = self.tok_emb.weight
        self.apply(self._init_weights)
        # GPT-2 style: scale residual projections by depth
        for name, p in self.named_parameters():
            if name.endswith("attn.proj.weight") or name.endswith("mlp.fc_out.weight"):
                nn.init.normal_(p, mean=0.0, std=0.02 / math.sqrt(2 * cfg.n_layer))

    @staticmethod
    def _init_weights(m: nn.Module) -> None:
        if isinstance(m, nn.Linear):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)
            if m.bias is not None:
                nn.init.zeros_(m.bias)
        elif isinstance(m, nn.Embedding):
            nn.init.normal_(m.weight, mean=0.0, std=0.02)

    def num_parameters(self, exclude_embeddings: bool = False) -> int:
        n = sum(p.numel() for p in self.parameters())  # shared (tied) params counted once
        if exclude_embeddings:
            n -= self.pos_emb.weight.numel() + self.tok_emb.weight.numel()
        return n

    @property
    def device(self) -> torch.device:
        return next(self.parameters()).device

    def forward(
        self,
        idx: torch.Tensor,
        targets: torch.Tensor | None = None,
        ignore_index: int = -100,
        last_only: bool = False,
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        """idx: (B, T) token ids. targets: (B, T), positions equal to ignore_index are skipped.
        Returns logits (B, T, V) — or (B, 1, V) with last_only — and the mean loss."""
        B, T = idx.shape
        if T > self.cfg.context_length:
            raise ValueError(f"sequence length {T} > context_length {self.cfg.context_length}")
        pos = torch.arange(T, device=idx.device)
        x = self.drop(self.tok_emb(idx) + self.pos_emb(pos))
        for block in self.blocks:
            x = block(x)
        x = self.ln_f(x)
        if last_only:
            x = x[:, -1:, :]
        logits = self.lm_head(x)
        loss = None
        if targets is not None:
            if last_only:
                raise ValueError("targets cannot be combined with last_only")
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)), targets.reshape(-1), ignore_index=ignore_index
            )
        return logits, loss

    def _crop(self, idx: torch.Tensor) -> torch.Tensor:
        n = self.cfg.context_length
        return idx if idx.size(1) <= n else idx[:, -n:]

    @torch.no_grad()
    def generate(
        self,
        idx: torch.Tensor,
        max_new_tokens: int,
        temperature: float = 0.0,
        top_k: int | None = None,
        eos_id: int | None = None,
        pad_id: int | None = None,
        generator: torch.Generator | None = None,
    ) -> torch.Tensor:
        """Autoregressive decoding. idx: (T,) or (B, T); rows must have equal length (no padding).
        temperature == 0 -> greedy (deterministic). Rows that emitted eos_id are filled with
        pad_id (or eos_id). Returns prompt + generated tokens, shape (B, T + n)."""
        was_training = self.training
        self.eval()
        try:
            if idx.dim() == 1:
                idx = idx.unsqueeze(0)
            idx = idx.to(self.device)
            finished = torch.zeros(idx.size(0), dtype=torch.bool, device=idx.device)
            fill = pad_id if pad_id is not None else eos_id
            for _ in range(max_new_tokens):
                logits, _ = self(self._crop(idx), last_only=True)
                logits = logits[:, -1, :].float()
                if temperature <= 0:
                    nxt = logits.argmax(dim=-1)
                else:
                    logits = logits / temperature
                    if top_k is not None:
                        v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                        logits = logits.masked_fill(logits < v[:, [-1]], float("-inf"))
                    probs = F.softmax(logits, dim=-1)
                    nxt = torch.multinomial(probs, 1, generator=generator).squeeze(-1)
                if eos_id is not None:
                    nxt = torch.where(finished, torch.full_like(nxt, fill), nxt)
                    finished |= nxt == eos_id
                idx = torch.cat([idx, nxt[:, None]], dim=1)
                if eos_id is not None and bool(finished.all()):
                    break
            return idx
        finally:
            self.train(was_training)

    @torch.no_grad()
    def beam_search(
        self,
        prompt: list[int] | torch.Tensor,
        beam_size: int,
        max_new_tokens: int,
        eos_id: int,
        length_penalty: float = 1.0,
    ) -> list[Hypothesis]:
        """Deterministic beam search for one prompt. Returns up to beam_size hypotheses,
        best first, ranked by logprob / length**length_penalty. Use this to get
        several candidate auxiliary constructions (the branching factor of the search)."""
        if beam_size < 1:
            raise ValueError("beam_size must be >= 1")
        if isinstance(prompt, torch.Tensor):
            prompt = prompt.view(-1).tolist()
        was_training = self.training
        self.eval()
        try:
            dev = self.device
            P = len(prompt)
            seqs = torch.tensor([prompt], dtype=torch.long, device=dev)  # (k, T)
            scores = torch.zeros(1, device=dev)
            done: list[tuple[list[int], float]] = []
            for _ in range(max_new_tokens):
                logits, _ = self(self._crop(seqs), last_only=True)
                logp = F.log_softmax(logits[:, -1, :].float(), dim=-1)
                V = logp.size(-1)
                total = (scores[:, None] + logp).view(-1)
                top_s, top_i = total.topk(min(2 * beam_size, total.numel()))
                new_seqs, new_scores = [], []
                for s, flat in zip(top_s.tolist(), top_i.tolist()):
                    b, tok = divmod(flat, V)
                    if tok == eos_id:
                        done.append((seqs[b, P:].tolist(), s))
                    else:
                        new_seqs.append(torch.cat([seqs[b], seqs.new_tensor([tok])]))
                        new_scores.append(s)
                        if len(new_seqs) == beam_size:
                            break
                if len(done) >= beam_size or not new_seqs:
                    seqs = None
                    break
                seqs = torch.stack(new_seqs)
                scores = torch.tensor(new_scores, device=dev)

            def norm(lp: float, n: int) -> float:
                return lp / (max(n, 1) ** length_penalty)

            hyps = [Hypothesis(t, lp, norm(lp, len(t) + 1), True) for t, lp in done]
            if seqs is not None and len(hyps) < beam_size:  # ran out of tokens: keep unfinished beams
                for row, lp in zip(seqs.tolist(), scores.tolist()):
                    t = row[P:]
                    hyps.append(Hypothesis(t, lp, norm(lp, len(t)), False))
            hyps.sort(key=lambda h: h.score, reverse=True)
            return hyps[:beam_size]
        finally:
            self.train(was_training)


def create_model(cfg: ModelConfig, tokenizer=None) -> GeoTransformer:
    """Build a randomly initialised model, checking the vocabulary fits."""
    if tokenizer is not None and len(tokenizer) > cfg.vocab_size:
        raise ValueError(
            f"tokenizer has {len(tokenizer)} tokens but vocab_size is {cfg.vocab_size}; "
            f"raise vocab_size in the model config"
        )
    return GeoTransformer(cfg)
