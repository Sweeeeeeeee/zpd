"""Any Hugging Face causal LM as an auxiliary-point proposer.

Same contract as pipeline.transformer_tool.TransformerTool: the problem goes in
the GenesisGeo text format (pipeline.translate.problem_to_model_text), the
model writes one new point with its predicates, and pipeline.translate turns
that into JGEX clauses. Only the prompt differs between models:

  prompt="genesisgeo"      ZJUVAI/GenesisGeo (Qwen3-0.6B fine-tuned on the same
                           data as geo-lm). Chat prompt as in their agent
                           (newclid/agent/vllm.py): system "You are a helpful
                           assistant.", user = problem, assistant prefix
                           "<think>\\n\\n</think>\\n\\n<aux> {new} :".
  prompt="genesisgeo_x00"  the same with their newer "<aux> x00 {new} :" prefix.
                           Which one the published checkpoint expects is
                           measured, not assumed (geo-lm/scripts/eval_aux.py style).
  prompt="fewshot"         any general model (e.g. Qwen2.5-0.5B-Instruct): a
                           short instruction and `shots` solved examples from
                           data/genesisgeo/train.txt, then the problem.

Deterministic: beam search, no sampling.

Config example (pipeline/configs/*.json):
    "genesisgeo": {"class": "pipeline.hf_tool:HFLMTool",
                   "options": {"model": "models/hf/GenesisGeo", "prompt": "genesisgeo"}}
"""

from __future__ import annotations

import re
from pathlib import Path

from pipeline.tools import ROOT, AuxConstruction, ProofState, Tool, fresh_point_name
from pipeline.translate import UntranslatableAux, aux_to_clauses, problem_to_model_text

SYSTEM = "You are a helpful assistant."
FEWSHOT_INSTRUCTION = (
    "You propose one auxiliary point for a plane geometry problem. Points are "
    "defined by predicates: coll (collinear), perp, para, cong (equal segments), "
    "cyclic. The goal follows '?'. Answer with exactly one new point in the form "
    "'<name> : <predicate>, <predicate>' and nothing else."
)
_STOPS = (";", "</aux>", "<|", "\n")
_INDEX = re.compile(r"\[\d+\]")


class HFLMTool(Tool):
    """options:
        model:          local folder or Hugging Face id
        prompt:         "genesisgeo", "genesisgeo_x00" or "fewshot"
        name:           tool name in results (default "hf")
        beam_size:      beams; all are returned as candidates (default 4)
        max_candidates: proposals returned (default 4)
        max_new_tokens: generation limit (default 48)
        dtype:          "bfloat16" (default, half the memory) or "float32"
        shots:          examples in the fewshot prompt (default 4)
        threads:        torch threads (default: torch's choice)
    """

    name = "hf"

    def __init__(self, model: str, prompt: str = "genesisgeo", name: str = "hf",
                 beam_size: int = 4, max_candidates: int = 4, max_new_tokens: int = 48,
                 dtype: str = "bfloat16", shots: int = 4, threads: int | None = None) -> None:
        super().__init__(model=model, prompt=prompt, beam_size=beam_size,
                         max_candidates=max_candidates, max_new_tokens=max_new_tokens, dtype=dtype)
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        if prompt not in ("genesisgeo", "genesisgeo_x00", "fewshot"):
            raise ValueError(f"unknown prompt style {prompt!r}")
        path = Path(model)
        if not path.is_absolute() and (ROOT / path).exists():
            path = ROOT / path
        elif model.startswith(("models/", "/", ".")):  # a local folder that is not there
            raise FileNotFoundError(f"model folder not found: {path} (download it first)")
        # otherwise a Hugging Face id, downloaded on first use
        if threads:
            torch.set_num_threads(threads)
        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(str(path))
        self.model = AutoModelForCausalLM.from_pretrained(
            str(path), torch_dtype=getattr(torch, dtype), low_cpu_mem_usage=True).eval()
        self.name = name
        self.prompt_style = prompt
        self.beam_size = beam_size
        self.max_candidates = max_candidates
        self.max_new_tokens = max_new_tokens
        self.shots = _load_shots(shots) if prompt == "fewshot" else []
        self.untranslatable = 0

    def build_prompt(self, problem_text: str, new_point: str) -> str:
        if self.prompt_style.startswith("genesisgeo"):
            aux = "<aux> x00" if self.prompt_style == "genesisgeo_x00" else "<aux>"
            return (f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"
                    f"<|im_start|>user\n{problem_text}<|im_end|>\n"
                    f"<|im_start|>assistant\n<think>\n\n</think>\n\n{aux} {new_point} :")
        messages = [{"role": "system", "content": FEWSHOT_INSTRUCTION}]
        for q, a in self.shots:
            messages += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]
        messages.append({"role": "user", "content": problem_text})
        if self.tok.chat_template:
            text = self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            text = "\n\n".join(f"{m['role']}: {m['content']}" for m in messages) + "\n\nassistant: "
        return text + f"{new_point} :"

    def propose_raw(self, problem_text: str, new_point: str) -> list[tuple[str, float]]:
        """(model output as 'x : preds', score) for each beam, best first."""
        prompt = self.build_prompt(problem_text, new_point)
        ids = self.tok(prompt, return_tensors="pt", add_special_tokens=False)
        n = ids["input_ids"].shape[1]
        with self.torch.no_grad():
            out = self.model.generate(
                **ids, max_new_tokens=self.max_new_tokens, do_sample=False,
                num_beams=self.beam_size, num_return_sequences=self.beam_size,
                early_stopping=True, output_scores=True, return_dict_in_generate=True,
                pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
        scores = out.sequences_scores.tolist() if out.sequences_scores is not None else [0.0] * len(out.sequences)
        res = []
        for seq, score in zip(out.sequences, scores):
            cont = self.tok.decode(seq[n:], skip_special_tokens=False)
            cut = min([cont.find(s) for s in _STOPS if s in cont] or [len(cont)])
            preds = _INDEX.sub("", cont[:cut]).strip()
            res.append((f"{new_point} : {preds}", float(score)))
        return res

    def run(self, state: ProofState) -> list[AuxConstruction] | None:
        self.calls += 1
        if state.builder is None:
            return None
        text, to_problem = problem_to_model_text(state)
        new_point = fresh_point_name(set(to_problem))
        out: list[AuxConstruction] = []
        seen: set[tuple[str, ...]] = set()
        for raw, score in self.propose_raw(text, new_point):
            try:
                clauses = aux_to_clauses(raw, to_problem)
            except UntranslatableAux:
                self.untranslatable += 1
                continue
            if clauses not in seen:
                seen.add(clauses)
                out.append(AuxConstruction(clauses, self.name, score=score, note=raw))
            if len(out) >= self.max_candidates:
                break
        return out or None


def _load_shots(k: int) -> list[tuple[str, str]]:
    """First k short training examples with an auxiliary point, as (problem, answer).
    From train.txt, never val.txt, which the offline evaluation uses."""
    shots = []
    for line in (ROOT / "data/genesisgeo/train.txt").open():
        if "<aux>" not in line or len(line) > 220:
            continue
        q, a = (s.strip() for s in line.split("<aux>", 1))
        shots.append((q, a))
        if len(shots) >= k:
            break
    return shots
