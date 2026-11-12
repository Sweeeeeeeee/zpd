"""AlphaGeometry (AG1) language model as a line-based server.

Runs in AG1's own environment (.venv-ag1: Python 3.10, JAX 0.4.6, TF 2.13,
meliad), started by pipeline.ag1_tool.AG1Tool; not imported by the pipeline.

    .venv-ag1/bin/python pipeline/ag1_server.py <alphageometry dir> <ckpt dir> <beam> [max tokens, 32]

Protocol (stdout carries only protocol lines; all logging goes to stderr):
    -> READY <load seconds>
    <- {"setup": "a b c = triangle a b c; ...", "goal": "perp a h b c"}
       or {"prompt": "{S} a : ; b : ; ... ? T a b c d {F1} x00"} (decode only)
    -> {"ok": true, "candidates": [{"raw": ..., "clause": ..., "score": ...}, ...]}
       or {"ok": false, "error": "..."}

What it does per problem is AG1's own first search step
(alphageometry.run_alphageometry, depth 0): rename points to a, b, c, ...
like AG1's training data, build the AG1 graph, prompt
`setup_str_from_problem + ' {F1} x00'`, beam-decode until ';', and translate
each output with AG1's try_translate_constrained_to_construct. A valid
translation is returned in the problem's own point names, the new point
written as the placeholder NEW (the caller picks a free name).
"""

from __future__ import annotations

import json
import os
import sys
import time


def main() -> None:
    ag_dir, ckpt_dir, beam = sys.argv[1], sys.argv[2], int(sys.argv[3])
    max_len = int(sys.argv[4]) if len(sys.argv) > 4 else 32
    # Keep stdout for the protocol: everything else (TF, JAX, absl) to stderr.
    proto = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)
    sys.stdout = sys.stderr

    t0 = time.time()
    meliad = os.path.join(ag_dir, "meliad_lib", "meliad")
    sys.path[:0] = [ag_dir, meliad]
    # AG1's numericals.py calls matplotlib.use('TkAgg'), which fails without a
    # display. It only draws figures, which the server never does: keep Agg.
    import matplotlib

    matplotlib.use("Agg")
    matplotlib.use = lambda *a, **k: None
    from absl import flags

    import alphageometry as ag  # defines absl flags; parse them with defaults
    import graph as gh
    import lm_inference as lm
    import problem as pr

    flags.FLAGS(["ag1_server"])
    # AG1 decodes up to 512 tokens (models.py) until no live beam can beat the
    # finished ones; on CPU (~1 s per token here) that can take minutes. One aux
    # point is ~12 tokens ("e : C a c e 02 C b d e 03 ;"), so cap it.
    import beam_search

    full_beam_search = beam_search.beam_search_flat
    beam_search.beam_search_flat = lambda *a, **k: full_beam_search(*a, **{**k, "max_decode_len": max_len})
    ag.DEFINITIONS = pr.Definition.from_txt_file(os.path.join(ag_dir, "defs.txt"), to_dict=True)
    ag.RULES = pr.Theorem.from_txt_file(os.path.join(ag_dir, "rules.txt"), to_dict=True)
    gins = ["base_htrans.gin", "size/medium_150M.gin", "options/positions_t5.gin",
            "options/lr_cosine_decay.gin", "options/seq_1024_nocache.gin",
            "geometry_150M_generate.gin"]
    params = ["DecoderOnlyLanguageModelGenerate.output_token_losses=True",
              f"TransformerTaskConfig.batch_size={beam}",  # = number of beams
              "TransformerTaskConfig.sequence_length=128",
              "Trainer.restore_state_variables=False"]
    lm.parse_gin_configuration(gins, params, gin_paths=[os.path.join(meliad, "transformer", "configs"), ag_dir])
    vocab = os.path.join(ckpt_dir, "geometry.757.model")
    slim = os.path.join(ckpt_dir, "params_only.npz")
    if os.path.exists(slim) and os.environ.get("AG1_FULL_RESTORE") != "1":
        # Weights only (pipeline/ag1_slim_ckpt.py): build without a restore,
        # then put the published weights in. Every array must match by name and shape.
        model = lm.LanguageModelInference(vocab, "", mode="beam_search")
        model.tstate = with_weights(model.tstate, slim)
        keep_returned_state(model)
        how = "weights-only"
    else:  # meliad's own restore of the whole 1.2 GB checkpoint (~3.9 GB peak)
        model = lm.LanguageModelInference(vocab, ckpt_dir, mode="beam_search")
        how = "full restore"
    print(f"AG1 loaded ({how}) in {time.time() - t0:.1f} s", file=sys.stderr, flush=True)
    proto.write(f"READY {time.time() - t0:.1f}\n")

    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            req = json.loads(line)
            proto.write(json.dumps({"ok": True, "candidates": propose(req, ag, gh, pr, model)}) + "\n")
        except Exception as e:  # noqa: BLE001 - one bad problem must not stop the server
            proto.write(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"[:500]}) + "\n")


def with_weights(tstate, npz_path: str):
    import jax.numpy as jnp
    import numpy as np
    from flax.core import freeze, unfreeze
    from flax.traverse_util import flatten_dict, unflatten_dict

    target = flatten_dict(unfreeze(tstate.optimizer.target))
    saved = np.load(npz_path)
    names = {"/".join(k) for k in target}
    if names != set(saved.files):
        raise ValueError(f"weights do not match the model: missing {sorted(names - set(saved.files))[:5]}, "
                         f"extra {sorted(set(saved.files) - names)[:5]}")
    new = {}
    for k, v in target.items():
        w = saved["/".join(k)]
        if w.shape != v.shape:
            raise ValueError(f"shape of {'/'.join(k)}: saved {w.shape}, model {v.shape}")
        new[k] = jnp.asarray(w, dtype=v.dtype)
    params = unflatten_dict(new)
    if not isinstance(tstate.optimizer.target, dict):  # FrozenDict: keep the same pytree type
        params = freeze(params)
    return tstate.replace(optimizer=tstate.optimizer.replace(target=params))


def keep_returned_state(model) -> None:
    """meliad's jitted step donates its state argument (training_loop:
    donate_argnums=(0,)), so device arrays passed in are deleted after a call,
    and LanguageModelInference.call throws the returned state away. A full
    restore hides this by passing host (numpy) arrays that are copied in every
    call; holding the state twice is what got the server killed. Instead keep
    the state the step returns (in inference: the same weights)."""
    run_step = model.task.run_step

    def run_and_keep(tstate, x, step, sub_step=0):
        new_tstate, metrics = run_step(tstate, x, step, sub_step)
        model.tstate = new_tstate
        return new_tstate, metrics

    model.task.run_step = run_and_keep


def propose(req: dict, ag, gh, pr, model) -> list[dict]:
    if "prompt" in req:  # raw AG1 prompt (bench/eval_proposers.py): decode only, no graph
        out = model.beam_decode(req["prompt"], eos_tokens=[";"])
        return [{"raw": raw, "score": float(score)}
                for raw, score in reversed(list(zip(out["seqs_str"], out["scores"])))]
    setup ="; ".join(" ".join(c.split()) for c in req["setup"].split(";") if c.strip())
    goal = " ".join(req["goal"].split(";")[0].split())  # AG1 takes one goal
    p = pr.Problem.from_txt(f"{setup} ? {goal}", translate=True)  # names -> a, b, c, ...
    back = {v: k for k, v in p.mapping.items()}
    g, _ = gh.Graph.build_problem(p, ag.DEFINITIONS)
    prompt = p.setup_str_from_problem(ag.DEFINITIONS) + " {F1} x00"
    out = model.beam_decode(prompt, eos_tokens=[";"])
    cands = []
    for raw, score in reversed(list(zip(out["seqs_str"], out["scores"]))):  # best first, as AG1
        clause = ag.try_translate_constrained_to_construct(raw, g)
        if clause.startswith("ERROR:"):
            cands.append({"raw": raw, "clause": None, "error": clause[:200], "score": float(score)})
            continue
        new = clause.split(" = ")[0].strip()
        toks = clause.replace(",", " , ").split()
        mapped = " ".join("NEW" if t == new else back.get(t, t) for t in toks).replace(" ,", ",")
        cands.append({"raw": raw, "clause": mapped, "score": float(score)})
    return cands


if __name__ == "__main__":
    main()
