"""Tokenizer for Newclid / AlphaGeometry problem syntax.

Example input:
    a b c = triangle a b c; d = midpoint d a b ? cong d a d b

Rules:
  * ';' ',' '=' '?' are always their own tokens.
  * Each remaining whitespace-separated word is split into pieces:
    identifiers (point names like 'a', 'a1', predicates like 'on_tline'),
    single digits, and single symbols. Pieces after the first in a word
    carry a '##' prefix, so '1pi/3' -> ['1', '##pi', '##/', '##3'].
  * Special tokens: <pad> <unk> <bos> <eos> <aux>.

Decoding is deterministic and produces canonical text, so
decode(encode(x)) == normalize(x) for any x without unknown tokens.

Training / inference format (shared with step 5 and the pipeline):
    <bos> PROBLEM <aux> AUX_CONSTRUCTION <eos>
The model is prompted with "<bos> PROBLEM <aux>" and must produce the rest.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence

PAD, UNK, BOS, EOS, AUX = "<pad>", "<unk>", "<bos>", "<eos>", "<aux>"
SPECIAL_TOKENS = [PAD, UNK, BOS, EOS, AUX]
_SPECIAL_SET = set(SPECIAL_TOKENS)
CONT = "##"
_ATTACH_LEFT = {";", ","}

_SPECIAL_RE = re.compile("(" + "|".join(re.escape(t) for t in SPECIAL_TOKENS) + ")")
_SEP_RE = re.compile(r"\s*([;,=?])\s*")
_PIECE_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*|\d|[^\sA-Za-z_0-9]")

# Always present so digits, single-letter points and angle constants never become <unk>.
_DIGITS = [str(i) for i in range(10)]
BASE_TOKENS = (
    [";", ",", "=", "?", "/", CONT + "/", "pi", CONT + "pi"]
    + _DIGITS + [CONT + d for d in _DIGITS]
    + [chr(c) for c in range(ord("a"), ord("z") + 1)]
)


def pretokenize(text: str) -> list[str]:
    """Split text into string tokens (vocabulary-independent)."""
    out: list[str] = []
    for seg in _SPECIAL_RE.split(text):
        if not seg:
            continue
        if seg in _SPECIAL_SET:
            out.append(seg)
            continue
        for word in _SEP_RE.sub(r" \1 ", seg).split():
            pieces = _PIECE_RE.findall(word)
            out.append(pieces[0])
            out.extend(CONT + p for p in pieces[1:])
    return out


def detokenize(tokens: Iterable[str]) -> str:
    """Join string tokens back into canonical Newclid-style text."""
    parts: list[str] = []
    for t in tokens:
        if t.startswith(CONT) and len(t) > len(CONT):
            parts.append(t[len(CONT):])
        elif t in _ATTACH_LEFT:
            parts.append(t)
        else:
            if parts:
                parts.append(" ")
            parts.append(t)
    return "".join(parts)


def normalize(text: str) -> str:
    """Canonical spacing, e.g. 'a b c=triangle a b c ;d=...' -> 'a b c = triangle a b c; d = ...'."""
    return detokenize(pretokenize(text))


class GeoTokenizer:
    def __init__(self, vocab: Sequence[str]):
        vocab = list(vocab)
        if vocab[: len(SPECIAL_TOKENS)] != SPECIAL_TOKENS:
            raise ValueError(f"vocab must start with {SPECIAL_TOKENS}")
        if len(set(vocab)) != len(vocab):
            raise ValueError("vocab contains duplicates")
        self.vocab = vocab
        self.stoi = {t: i for i, t in enumerate(vocab)}

    # ids of special tokens
    pad_id = property(lambda self: self.stoi[PAD])
    unk_id = property(lambda self: self.stoi[UNK])
    bos_id = property(lambda self: self.stoi[BOS])
    eos_id = property(lambda self: self.stoi[EOS])
    aux_id = property(lambda self: self.stoi[AUX])

    def __len__(self) -> int:
        return len(self.vocab)

    @classmethod
    def build(cls, texts: Iterable[str], min_freq: int = 1, max_size: int | None = None) -> "GeoTokenizer":
        """Build a vocabulary from a corpus. Deterministic: frequency desc, then alphabetical."""
        counts: Counter[str] = Counter()
        for t in texts:
            counts.update(pretokenize(t))
        vocab = list(SPECIAL_TOKENS) + [t for t in BASE_TOKENS if t not in _SPECIAL_SET]
        seen = set(vocab)
        ranked = sorted(
            (t for t, c in counts.items() if c >= min_freq and t not in seen),
            key=lambda t: (-counts[t], t),
        )
        if max_size is not None:
            ranked = ranked[: max(0, max_size - len(vocab))]
        return cls(vocab + ranked)

    def encode(self, text: str, add_bos: bool = False, add_eos: bool = False) -> list[int]:
        ids = [self.stoi.get(t, self.unk_id) for t in pretokenize(text)]
        if add_bos:
            ids.insert(0, self.bos_id)
        if add_eos:
            ids.append(self.eos_id)
        return ids

    def decode(self, ids: Iterable[int], skip_special: bool = True) -> str:
        toks = []
        for i in ids:
            i = int(i)
            t = self.vocab[i] if 0 <= i < len(self.vocab) else UNK
            if skip_special and t in _SPECIAL_SET:
                continue
            toks.append(t)
        return detokenize(toks)

    def encode_prompt(self, problem: str) -> list[int]:
        """'<bos> problem <aux>' — what the model sees at inference time."""
        return [self.bos_id] + self.encode(problem) + [self.aux_id]

    def encode_example(self, problem: str, aux: str) -> tuple[list[int], int]:
        """Full training sequence and the index where the auxiliary construction starts."""
        prompt = self.encode_prompt(problem)
        return prompt + self.encode(aux) + [self.eos_id], len(prompt)

    def unknown_tokens(self, text: str) -> list[str]:
        """Tokens of `text` missing from the vocabulary (useful for data checks)."""
        return [t for t in pretokenize(text) if t not in self.stoi]

    def save(self, path: str | Path) -> None:
        data = {"type": "GeoTokenizer", "version": 1, "vocab": self.vocab}
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "GeoTokenizer":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if data.get("type") != "GeoTokenizer":
            raise ValueError(f"{path} is not a GeoTokenizer file")
        return cls(data["vocab"])
