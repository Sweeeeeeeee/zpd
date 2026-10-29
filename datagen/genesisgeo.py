"""Build the auxiliary-construction training set from GenesisGeo.

GenesisGeo (arXiv 2509.21896, ZJUVAI) released 21.8M problems generated and
proven with their Newclid fork's DDAR, ~3M of which need an auxiliary
construction: https://huggingface.co/datasets/ZJUVAI/GenesisGeo (Apache-2.0).
This script subsamples those, converts them to geo-lm's training format and
writes train/validation splits.

Source row (abridged):
    question: <problem> a : ; b : ; c : ; d : eqangle a b a d a d a c [000]
              eqangle a b b d b d b c [001] ; e : coll b c e [002] perp b c e d [003]
              ; ... ? cong e d f d </problem>
    solution: <aux> x00 g : coll a b g [006] perp a b g d [007] ; </aux> <proof> ...

Output line (one example per line, `PROBLEM <aux> AUX`):
    a :; b :; c :; d : eqangle a b a d a d a c, eqangle a b b d b d b c; e : coll b c e,
    perp b c e d; ... ? cong e d f d <aux> g : coll a b g, perp a b g d

Each point is defined by the predicates it satisfies (AlphaGeometry-style),
not by a Newclid construction name. Proof steps are dropped.

Usage (from the repo root):
    .venv-newclid/bin/python -m datagen.genesisgeo --size 100000
    .venv-newclid/bin/python -m datagen.genesisgeo --size 2000 --out-dir data/genesisgeo_small
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import re
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HF_BASE = "https://huggingface.co/datasets/ZJUVAI/GenesisGeo/resolve/main/data/"
SHARDS = [f"train0801-{i:05d}-of-00005.parquet" for i in range(5)] + [
    f"train0901-{i:05d}-of-00003.parquet" for i in range(3)
]


def _load_tokenizer_module():
    # geo_lm/__init__ imports torch; the tokenizer itself is pure Python.
    path = ROOT / "geo-lm/geo_lm/tokenizer.py"
    spec = importlib.util.spec_from_file_location("geo_lm_tokenizer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_tok = _load_tokenizer_module()
normalize, pretokenize = _tok.normalize, _tok.pretokenize

_ID_RE = re.compile(r"\[\d+\]")
_AUX_TAG_RE = re.compile(r"^x\d+\s+")


def _clause(text: str) -> str:
    """'d : eqangle ... [000] eqangle ... [001]' -> 'd : eqangle ..., eqangle ...'."""
    points, _, preds = text.partition(":")
    parts = [p.strip() for p in _ID_RE.split(preds) if p.strip()]
    return f"{points.strip()} : {', '.join(parts)}".rstrip()


def convert(question: str, solution: str) -> tuple[str, str, str] | None:
    """(setup, problem, aux) in geo-lm format, or None if the row has no aux."""
    if "<aux>" not in solution:
        return None
    body = question.replace("<problem>", "").replace("</problem>", "").strip()
    setup_txt, sep, goal_txt = body.partition("?")
    if not sep:
        return None
    clauses = [_clause(c) for c in setup_txt.split(";") if c.strip()]
    goal = " ".join(_ID_RE.sub(" ", goal_txt).split())
    aux_txt = solution.split("<aux>", 1)[1].split("</aux>", 1)[0]
    aux = [_clause(_AUX_TAG_RE.sub("", a.strip())) for a in aux_txt.split(";") if a.strip()]
    if not clauses or not goal or not aux:
        return None
    setup = normalize("; ".join(clauses))
    return setup, normalize(f"{setup} ? {goal}"), normalize("; ".join(aux))


def _download(shard: str, raw_dir: Path) -> Path:
    path = raw_dir / shard
    if not path.exists():
        raw_dir.mkdir(parents=True, exist_ok=True)
        print(f"downloading {shard} (~1 GB) ...", flush=True)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(HF_BASE + shard, tmp)
        tmp.rename(path)
    return path


def _is_val(setup: str, val_frac: float) -> bool:
    # Split by figure, so the same setup never appears in both splits.
    h = int(hashlib.sha1(setup.encode()).hexdigest()[:8], 16)
    return h / 2**32 < val_frac


def generate(args: argparse.Namespace) -> dict:
    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    rng = random.Random(args.seed)
    reservoir: list[tuple[str, str, str]] = []
    seen: set[bytes] = set()
    per_setup: dict[bytes, int] = {}
    stats = dict(rows=0, aux_rows=0, too_long=0, unparsed=0, duplicate=0,
                 setup_cap=0, candidates=0)
    t0 = time.time()

    for shard in SHARDS[: args.shards]:
        pf = pq.ParquetFile(_download(shard, args.raw_dir))
        for rg in range(pf.metadata.num_row_groups):
            if args.max_rows and stats["rows"] >= args.max_rows:
                break
            table = pf.read_row_group(rg, columns=["question", "solution"])
            stats["rows"] += table.num_rows
            table = table.filter(pc.match_substring(table["solution"], "<aux>"))
            stats["aux_rows"] += table.num_rows
            for q, s in zip(table["question"].to_pylist(), table["solution"].to_pylist()):
                converted = convert(q, s)
                if converted is None:
                    stats["unparsed"] += 1
                    continue
                setup, problem, aux = converted
                if len(pretokenize(problem)) + len(pretokenize(aux)) + 3 > args.max_tokens:
                    stats["too_long"] += 1
                    continue
                key = hashlib.sha1(f"{problem}<aux>{aux}".encode()).digest()
                if key in seen:
                    stats["duplicate"] += 1
                    continue
                seen.add(key)
                skey = hashlib.sha1(setup.encode()).digest()
                if per_setup.get(skey, 0) >= args.max_per_setup:
                    stats["setup_cap"] += 1
                    continue
                per_setup[skey] = per_setup.get(skey, 0) + 1
                # Reservoir sampling: a uniform sample of everything seen so far.
                n = stats["candidates"]
                stats["candidates"] += 1
                if len(reservoir) < args.size:
                    reservoir.append(converted)
                elif (j := rng.randrange(n + 1)) < args.size:
                    reservoir[j] = converted
            if rg % 200 == 0:
                print(f"  {shard} row group {rg}/{pf.metadata.num_row_groups}: "
                      f"{stats['candidates']} candidates, {time.time() - t0:.0f}s", flush=True)
        if stats["candidates"] >= args.size * args.oversample:
            break

    rng.shuffle(reservoir)
    train = [f"{p} <aux> {a}" for s, p, a in reservoir if not _is_val(s, args.val_frac)]
    val = [f"{p} <aux> {a}" for s, p, a in reservoir if _is_val(s, args.val_frac)]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "train.txt").write_text("\n".join(train) + "\n")
    (args.out_dir / "val.txt").write_text("\n".join(val) + "\n")
    lengths = sorted(len(pretokenize(x)) + 2 for x in train + val)
    meta = {
        "source": "https://huggingface.co/datasets/ZJUVAI/GenesisGeo (Apache-2.0)",
        "format": "PROBLEM <aux> AUX, one per line; model sees <bos> PROBLEM <aux> AUX <eos>",
        "args": {k: str(v) for k, v in vars(args).items()},
        "stats": stats,
        "train": len(train),
        "val": len(val),
        "tokens_median": lengths[len(lengths) // 2] if lengths else 0,
        "tokens_max": lengths[-1] if lengths else 0,
        "seconds": round(time.time() - t0),
    }
    (args.out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", type=int, default=100_000, help="examples in train + val")
    ap.add_argument("--val-frac", type=float, default=0.02)
    ap.add_argument("--max-tokens", type=int, default=512,
                    help="drop examples longer than this (geo-lm context length)")
    ap.add_argument("--max-per-setup", type=int, default=3,
                    help="keep at most this many goals per figure")
    ap.add_argument("--shards", type=int, default=1, choices=range(1, len(SHARDS) + 1),
                    help="how many ~1 GB source shards to use at most")
    ap.add_argument("--oversample", type=float, default=3.0,
                    help="stop reading shards once candidates >= size * this")
    ap.add_argument("--max-rows", type=int, default=0, help="stop after this many rows (0 = all)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--raw-dir", type=Path, default=ROOT / "data/genesisgeo/raw")
    ap.add_argument("--out-dir", type=Path, default=ROOT / "data/genesisgeo")
    args = ap.parse_args()
    meta = generate(args)
    print(json.dumps({k: meta[k] for k in ("stats", "train", "val", "tokens_median", "tokens_max", "seconds")}, indent=2))


if __name__ == "__main__":
    main()
