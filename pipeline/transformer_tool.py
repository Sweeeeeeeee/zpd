"""The step 3 transformer as a tool: beam search for auxiliary constructions.

Deterministic: beam search, no sampling. Each beam hypothesis is translated
into JGEX clauses (pipeline.translate); hypotheses that cannot be translated
are dropped.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.tools import ROOT, AuxConstruction, ProofState, Tool
from pipeline.translate import UntranslatableAux, aux_to_clauses, problem_to_model_text


class TransformerTool(Tool):
    """options:
        checkpoint:     path to a geo_lm checkpoint (e.g. geo-lm/runs/small/best.pt)
        beam_size:      hypotheses kept by beam search (default 4)
        max_candidates: proposals returned (default 4)
        max_new_tokens: generation limit (default 96)
        device:         "auto", "cpu" or "cuda"
    """

    name = "transformer"

    def __init__(
        self,
        checkpoint: str,
        beam_size: int = 4,
        max_candidates: int = 4,
        max_new_tokens: int = 96,
        device: str = "cpu",
    ) -> None:
        super().__init__(checkpoint=checkpoint, beam_size=beam_size,
                         max_candidates=max_candidates, max_new_tokens=max_new_tokens)
        from geo_lm import load_checkpoint, pick_device

        path = Path(checkpoint)
        path = path if path.is_absolute() else ROOT / path
        if not path.exists():
            raise FileNotFoundError(f"transformer checkpoint not found: {path} (train one with geo_lm.train)")
        self.model, self.tokenizer, _ = load_checkpoint(path, map_location=pick_device(device))
        if self.tokenizer is None:
            raise ValueError(f"{path} has no tokenizer")
        self.beam_size = beam_size
        self.max_candidates = max_candidates
        self.max_new_tokens = max_new_tokens
        self.untranslatable = 0  # hypotheses dropped, for diagnostics

    def run(self, state: ProofState) -> list[AuxConstruction] | None:
        self.calls += 1
        if state.builder is None:
            return None
        text, to_problem = problem_to_model_text(state)
        tok = self.tokenizer
        prompt = tok.encode_prompt(text)
        room = self.model.cfg.context_length - len(prompt)
        if room <= 0:
            return None
        hyps = self.model.beam_search(
            prompt, beam_size=self.beam_size,
            max_new_tokens=min(room, self.max_new_tokens), eos_id=tok.eos_id,
        )
        out: list[AuxConstruction] = []
        seen: set[tuple[str, ...]] = set()
        for h in hyps:
            if not h.finished:
                continue
            raw = tok.decode(h.tokens)
            try:
                clauses = aux_to_clauses(raw, to_problem)
            except UntranslatableAux:
                self.untranslatable += 1
                continue
            if clauses not in seen:
                seen.add(clauses)
                out.append(AuxConstruction(clauses, self.name, score=h.score, note=raw))
            if len(out) >= self.max_candidates:
                break
        return out or None
