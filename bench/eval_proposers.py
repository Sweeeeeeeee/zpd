"""Every proposer model on the same held-out problems, scored the same way.

The first N problems with an auxiliary point in data/genesisgeo/val.txt (never
in geo-lm's training data or in the few-shot prompts). Each model proposes the
first auxiliary point with beam search; per problem we record its beams and:

  exact@1 / exact@k   the top / any beam's first point has exactly the
                      reference's predicates (as a set, arguments sorted:
                      order does not change the point)
  translatable        the beam maps onto Newclid constructions
                      (pipeline.translate, the same check the solver uses)
  seconds             time of the call (after loading)

Rows go to <out>.jsonl as they are made, so a killed run resumes where it
stopped; the summary goes to <out>.json at the end.

    python bench/eval_proposers.py geolm geo-lm/runs/mid/best.pt --out results/proposers/val200/mid
    python bench/eval_proposers.py hf models/hf/GenesisGeo --prompt genesisgeo --out ...
    python bench/eval_proposers.py ag1 models/ag1/ag_ckpt_vocab --out ...

AG1 gets the problem in its own prompt format (codes C, D, T, P, ^, numbered
premises; built here as AG1's problem.setup_str_from_problem does) and its
output is turned back into predicate names before scoring.
"""

from __future__ import annotations

import argparse
import json
import re
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "geo-lm"))

from pipeline.hf_tool import normalize_preds  # noqa: E402
from pipeline.translate import UntranslatableAux, aux_to_clauses  # noqa: E402


def canon(preds: str) -> frozenset[str]:
    out = set()
    for p in normalize_preds(preds).split(","):
        t = p.split()
        if t:
            out.add(t[0] + " " + " ".join(sorted(t[1:])))
    return frozenset(out)


def problems(n: int) -> list[tuple[str, str, str]]:
    """(problem text, new point, reference predicates of the first aux point)."""
    out = []
    for line in (ROOT / "data/genesisgeo/val.txt").open():
        if "<aux>" not in line:
            continue
        problem, aux = (s.strip() for s in line.split("<aux>", 1))
        point, _, gold = (s.strip() for s in aux.split(";")[0].partition(":"))
        out.append((problem, point, gold))
        if len(out) >= n:
            break
    return out


# ---------------------------------------------------------------- AG1 format
AG_CODE = {"coll": "C", "cong": "D", "perp": "T", "para": "P", "cyclic": "O", "midp": "M",
           "eqangle": "^", "aconst": "^", "eqratio": "/", "rconst": "/", "circle": "I",
           "simtri": "S", "contri": "="}
AG_NAME = {"C": "coll", "D": "cong", "T": "perp", "P": "para", "O": "cyclic", "M": "midp",
           "I": "circle", "S": "simtri", "=": "contri", "F": "foot"}


def _pretty2(a, b, c, d):  # AG1 pretty.pretty2a / pretty2r
    if b in (c, d):
        a, b = b, a
    if a == d:
        c, d = d, c
    return [a, b, c, d]


def _ag_pred(name: str, args: list[str]) -> str:
    if name in ("eqangle", "eqratio") and len(args) == 8:
        args = _pretty2(*args[:4]) + _pretty2(*args[4:])
    elif name in ("aconst", "rconst"):
        m, _, n = args[4].partition("/")
        return f"{AG_CODE[name]} {' '.join(_pretty2(*args[:4]))} {m}. pi / {n or 1}."
    return f"{AG_CODE[name]} {' '.join(args)}"


def ag1_prompt(problem: str) -> str:
    setup, _, goal = problem.partition("?")
    parts, ref = [], 0
    for clause in setup.split(";"):
        if not clause.strip():
            continue
        pts, _, body = clause.partition(":")
        deps = []
        for pred in normalize_preds(body).split(","):
            t = pred.split()
            if t:
                deps.append(f"{_ag_pred(t[0], t[1:])} {ref:02}")
                ref += 1
        parts.append(f"{pts.strip()} : {' '.join(deps)}".strip())
    g = goal.split()
    return "{S} " + " ; ".join(parts) + " ? " + _ag_pred(g[0], g[1:]) + " {F1} x00"


def from_ag1(raw: str) -> str:
    """'j : C a b j 15 T a b j d 16' -> 'j : coll a b j, perp a b j d'."""
    point, _, body = raw.partition(":")
    preds, cur = [], []
    for tok in body.replace(";", " ").split():
        if re.fullmatch(r"\d\d", tok):  # premise number ends a predicate
            if cur:
                preds.append(cur)
            cur = []
        else:
            cur.append(tok)
    if cur:
        preds.append(cur)
    out = []
    for p in preds:
        code, args = p[0], p[1:]
        if code in ("^", "/"):
            if "pi" in args:  # ^ a b c d 1. pi / 4.
                i = args.index("pi")
                m, n = args[i - 1].rstrip("."), args[i + 2].rstrip(".") if len(args) > i + 2 else "1"
                out.append(f"{'aconst' if code == '^' else 'rconst'} {' '.join(args[:4])} {m}/{n}")
            else:
                out.append(f"{'eqangle' if code == '^' else 'eqratio'} {' '.join(args)}")
        else:
            out.append(f"{AG_NAME.get(code, code)} {' '.join(args)}")
    return f"{point.strip()} : {', '.join(out)}"


# ---------------------------------------------------------------- proposers
class GeoLM:
    def __init__(self, ckpt: str, beam: int):
        import torch

        from geo_lm import load_checkpoint
        torch.manual_seed(0)
        self.torch, self.beam = torch, beam
        self.model, self.tok, _ = load_checkpoint(ckpt, map_location="cpu")
        self.model.eval()

    def __call__(self, problem: str, point: str) -> list[str]:
        prompt = self.tok.encode_prompt(problem)
        room = self.model.cfg.context_length - len(prompt)
        with self.torch.no_grad():
            hyps = self.model.beam_search(prompt, beam_size=self.beam, max_new_tokens=min(room, 64),
                                          eos_id=self.tok.eos_id)
        return [self.tok.decode(h.tokens).split(";")[0].strip() for h in hyps]


class HF:
    def __init__(self, path: str, beam: int, prompt: str, dtype: str):
        from pipeline.hf_tool import HFLMTool
        self.tool = HFLMTool(path, prompt=prompt, beam_size=beam, max_new_tokens=20, dtype=dtype)

    def __call__(self, problem: str, point: str) -> list[str]:
        return [r for r, _ in self.tool.propose_raw(problem, point)]


class AG1:
    def __init__(self, ckpt: str, beam: int):
        from pipeline.ag1_tool import AG1Tool
        self.tool = AG1Tool(beam_size=beam, ckpt=ckpt, log=str(ROOT / "claude/jobs/ag1_server_eval.log"))

    def __call__(self, problem: str, point: str) -> list[str]:
        return [from_ag1(r) for r, _ in self.tool.raw(ag1_prompt(problem))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["geolm", "hf", "ag1"])
    ap.add_argument("model", help="checkpoint / HF folder / AG1 checkpoint folder")
    ap.add_argument("--out", required=True, help="path without extension")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--beam", type=int, default=4)
    ap.add_argument("--prompt", default="genesisgeo", help="HF prompt style")
    ap.add_argument("--dtype", default="float32", help="HF weights dtype (bfloat16 is slow on this CPU)")
    a = ap.parse_args()

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows_path = out.with_suffix(".jsonl")
    done = [json.loads(l) for l in rows_path.read_text().splitlines()] if rows_path.exists() else []
    probs = problems(a.n)

    t0 = time.time()
    if len(done) < len(probs):
        model = {"geolm": lambda: GeoLM(a.model, a.beam), "hf": lambda: HF(a.model, a.beam, a.prompt, a.dtype),
                 "ag1": lambda: AG1(a.model, a.beam)}[a.kind]()
        load_s = time.time() - t0
        print(f"loaded {a.model} in {load_s:.1f} s; {len(done)} of {len(probs)} done", flush=True)
        with rows_path.open("a") as f:
            for i in range(len(done), len(probs)):
                problem, point, gold = probs[i]
                names = {c.split(":")[0].strip(): c.split(":")[0].strip()
                         for c in problem.split("?")[0].split(";") if c.split(":")[0].strip()}
                t = time.time()
                beams = model(problem, point)
                dt = time.time() - t
                ok, hit = [], []
                for raw in beams:
                    try:
                        aux_to_clauses(raw, names)
                        ok.append(True)
                    except (UntranslatableAux, Exception):  # noqa: BLE001 - any malformed output counts as not translatable
                        ok.append(False)
                    hit.append(":" in raw and canon(raw.split(":", 1)[1]) == canon(gold))
                row = {"i": i, "gold": f"{point} : {gold}", "beams": beams, "translatable": ok,
                       "exact": hit, "seconds": round(dt, 2), "load_s": round(load_s, 1)}
                f.write(json.dumps(row) + "\n")
                f.flush()
                done.append(row)
                print(f"[{i + 1}] {dt:5.1f} s exact@1={bool(hit[:1] and hit[0])} any={any(hit)} "
                      f"transl={sum(ok)}/{len(ok)} top={beams[0] if beams else ''!r}", flush=True)
        if a.kind == "ag1":
            model.tool.close()  # so its peak memory shows in RUSAGE_CHILDREN

    n = len(done)
    beams_total = sum(len(r["beams"]) for r in done)
    secs = sorted(r["seconds"] for r in done)
    rss = max(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss) / 1e6
    summary = {
        "kind": a.kind, "model": a.model, "prompt": a.prompt if a.kind == "hf" else None, "dtype": a.dtype if a.kind == "hf" else None,
        "beam": a.beam, "problems": n, "beams": beams_total,
        "translatable_rate": round(sum(sum(r["translatable"]) for r in done) / max(beams_total, 1), 3),
        "problems_with_translatable": round(sum(any(r["translatable"]) for r in done) / max(n, 1), 3),
        "exact_at_1": round(sum(bool(r["exact"]) and r["exact"][0] for r in done) / max(n, 1), 3),
        f"exact_at_{a.beam}": round(sum(any(r["exact"]) for r in done) / max(n, 1), 3),
        "seconds_median": secs[n // 2] if secs else None,
        "seconds_total": round(sum(secs), 1),
        "load_s": done[-1]["load_s"] if done else None,
        "peak_rss_gb_last_part": round(rss, 2),
    }
    out.with_suffix(".json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
