"""Offline check of a geo_lm checkpoint on held-out GenesisGeo problems (task 8.2).

For each validation problem, beam search proposes auxiliary constructions.
Reported:
  finished      the hypothesis ended with <eos> within the token limit
  exact@1/@k    the top / any hypothesis equals the reference construction
  translatable  the proposal maps onto Newclid constructions (pipeline.translate)

    python geo-lm/scripts/eval_aux.py geo-lm/runs/mini/best.pt --n 100 --beam 4
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "geo-lm"))

import torch  # noqa: E402

from geo_lm import load_checkpoint  # noqa: E402
from pipeline.translate import UntranslatableAux, aux_to_clauses  # noqa: E402


def norm(s: str) -> str:
    return " ".join(s.replace(";", " ; ").replace(",", " , ").split())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("checkpoint")
    ap.add_argument("--val", default=str(ROOT / "data/genesisgeo/val.txt"))
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--beam", type=int, default=4)
    ap.add_argument("--max_new_tokens", type=int, default=64)
    ap.add_argument("--out", default=None, help="write the summary as JSON here")
    args = ap.parse_args()

    torch.manual_seed(0)
    model, tok, _ = load_checkpoint(args.checkpoint, map_location="cpu")
    model.eval()
    lines = [l for l in Path(args.val).read_text().splitlines() if "<aux>" in l][: args.n]

    hyps_total = finished = translatable = 0
    exact1 = exactk = any_translatable = 0
    reasons: dict[str, int] = {}
    t0 = time.time()
    for line in lines:
        problem, _, target = line.partition("<aux>")
        problem, target = problem.strip(), norm(target)
        points = {p.split(":")[0].strip() for p in problem.split("?")[0].split(";")}
        identity = {p: p for p in points if p}
        prompt = tok.encode_prompt(problem)
        room = model.cfg.context_length - len(prompt)
        with torch.no_grad():
            hyps = model.beam_search(prompt, beam_size=args.beam,
                                     max_new_tokens=min(room, args.max_new_tokens), eos_id=tok.eos_id)
        texts = []
        ok_here = False
        for h in hyps:
            hyps_total += 1
            if not h.finished:
                reasons["unfinished"] = reasons.get("unfinished", 0) + 1
                continue
            finished += 1
            raw = tok.decode(h.tokens)
            texts.append(norm(raw))
            try:
                aux_to_clauses(raw, identity)
                translatable += 1
                ok_here = True
            except UntranslatableAux as e:
                msg = str(e)
                key = next((k for k in ("unknown point", "already exists", "no construction for",
                                        "does not involve", "expected one new point", "empty construction",
                                        "degenerate", "no predicates") if k in msg), msg[:40])
                reasons[key] = reasons.get(key, 0) + 1
        exact1 += bool(texts) and texts[0] == target
        exactk += target in texts
        any_translatable += ok_here

    n = len(lines)
    summary = {
        "checkpoint": args.checkpoint, "problems": n, "beam": args.beam,
        "hypotheses": hyps_total,
        "finished_rate": round(finished / max(hyps_total, 1), 3),
        "translatable_rate": round(translatable / max(hyps_total, 1), 3),
        "problems_with_translatable": round(any_translatable / max(n, 1), 3),
        "exact_at_1": round(exact1 / max(n, 1), 3),
        f"exact_at_{args.beam}": round(exactk / max(n, 1), 3),
        "rejected": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
        "seconds": round(time.time() - t0, 1),
    }
    print(json.dumps(summary, indent=2))
    if args.out:
        Path(args.out).write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
