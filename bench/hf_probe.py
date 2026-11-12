"""Quick check of a Hugging Face proposer before the comparison run.

Loads one model through pipeline.hf_tool.HFLMTool and asks it for the first
auxiliary point of N held-out problems (data/genesisgeo/val.txt, never seen in
training of geo-lm or in the few-shot prompt). Reports load time, seconds per
call, peak memory, exact match of the first point (any beam / top beam) and
how many outputs translate to JGEX clauses.

    python bench/hf_probe.py models/hf/GenesisGeo --prompt genesisgeo --n 5
    python bench/hf_probe.py models/hf/SmolLM2-360M-Instruct --prompt fewshot --n 5 --beam 2

Never run it next to training (memory).
"""

from __future__ import annotations

import argparse
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.hf_tool import HFLMTool, normalize_preds  # noqa: E402
from pipeline.translate import UntranslatableAux, aux_to_clauses  # noqa: E402


def canon(preds: str) -> set[str]:
    """Predicates as a set, each with sorted arguments (order inside a predicate
    and between predicates does not change the point)."""
    out = set()
    for p in normalize_preds(preds).split(","):
        t = p.split()
        if t:
            out.add(t[0] + " " + " ".join(sorted(t[1:])))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--prompt", default="genesisgeo")
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--beam", type=int, default=4)
    ap.add_argument("--max-new-tokens", type=int, default=20)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--out", default=None, help="write the per-problem results as JSON")
    a = ap.parse_args()

    t0 = time.time()
    tool = HFLMTool(a.model, prompt=a.prompt, beam_size=a.beam,
                    max_new_tokens=a.max_new_tokens, threads=a.threads)
    load_s = time.time() - t0
    print(f"loaded {a.model} in {load_s:.1f} s", flush=True)

    rows, done = [], 0
    for line in (ROOT / "data/genesisgeo/val.txt").open():
        if "<aux>" not in line:
            continue
        problem, aux = (s.strip() for s in line.split("<aux>", 1))
        first = aux.split(";")[0]
        new_point, _, gold = (s.strip() for s in first.partition(":"))
        t = time.time()
        beams = tool.propose_raw(problem, new_point)
        dt = time.time() - t
        names = {}
        for clause in problem.split("?")[0].split(";"):
            if clause.split(":")[0].strip():
                p = clause.split(":")[0].strip()
                names[p] = p
        ok = []
        for raw, _ in beams:
            try:
                aux_to_clauses(raw, names)
                ok.append(True)
            except UntranslatableAux:
                ok.append(False)
        hits = [canon(raw.split(":", 1)[1]) == canon(gold) for raw, _ in beams]
        rows.append({"gold": first, "beams": [r for r, _ in beams], "seconds": round(dt, 1),
                     "exact_top1": hits[0], "exact_any": any(hits), "translatable": ok})
        print(f"[{done + 1}] {dt:5.1f} s  gold '{first}'  top '{beams[0][0]}'  "
              f"exact top1={hits[0]} any={any(hits)} translatable={sum(ok)}/{len(ok)}", flush=True)
        done += 1
        if done >= a.n:
            break

    rss_gb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
    n = len(rows)
    summary = {
        "model": a.model, "prompt": a.prompt, "beam": a.beam, "max_new_tokens": a.max_new_tokens,
        "n": n, "load_s": round(load_s, 1),
        "s_per_call_median": sorted(r["seconds"] for r in rows)[n // 2],
        "exact_top1": sum(r["exact_top1"] for r in rows), "exact_any": sum(r["exact_any"] for r in rows),
        "translatable_beams": f"{sum(sum(r['translatable']) for r in rows)}/{sum(len(r['translatable']) for r in rows)}",
        "peak_rss_gb": round(rss_gb, 2),
    }
    print(json.dumps(summary))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
