"""AlphaGeometry (AG1) language model as an auxiliary-point proposer.

AG1 needs its own environment (Python 3.10, JAX 0.4.6, TF 2.13, meliad), so
the model runs in a child process, pipeline/ag1_server.py, started once when
the tool loads and talked to over stdin/stdout. The child is in the same
process group, so pipeline.solve counts its memory and kills it with the rest.

Setup (docs/models.md): third_party/alphageometry (+ meliad at e8af054),
.venv-ag1 from its requirements.txt, checkpoint in models/ag1/ag_ckpt_vocab.

Config example:
    "ag1": {"class": "pipeline.ag1_tool:AG1Tool", "options": {"beam_size": 4}}
"""

from __future__ import annotations

import json
import re
import select
import subprocess
import time
from pathlib import Path

from pipeline.tools import ROOT, AuxConstruction, ProofState, Tool, fresh_point_name


class AG1Tool(Tool):
    """options:
        beam_size:      AG1 beams (= its batch size); all valid ones are returned (default 4)
        max_candidates: proposals returned (default 4)
        python:         interpreter of AG1's environment (default .venv-ag1/bin/python)
        ag_dir:         AG1 code (default third_party/alphageometry)
        ckpt:           checkpoint folder (default models/ag1/ag_ckpt_vocab)
        max_tokens:     decode limit per proposal (default 32; AG1's own is 512)
        timeout_s:      per-call limit; the solve budget usually stops it first (default 300)
        log:            file for the server's stderr (default: discarded)
    """

    name = "ag1"

    def __init__(self, beam_size: int = 4, max_candidates: int = 4,
                 python: str = ".venv-ag1/bin/python", ag_dir: str = "third_party/alphageometry",
                 ckpt: str = "models/ag1/ag_ckpt_vocab", timeout_s: float = 300.0,
                 log: str | None = None, name: str = "ag1", max_tokens: int = 32) -> None:
        super().__init__(beam_size=beam_size, max_candidates=max_candidates)
        paths = {k: (Path(v) if Path(v).is_absolute() else ROOT / v)
                 for k, v in (("python", python), ("ag_dir", ag_dir), ("ckpt", ckpt))}
        for k, p in paths.items():
            if not p.exists():
                raise FileNotFoundError(f"AG1 {k} not found: {p} (see docs/models.md)")
        self.name = name
        self.max_candidates = max_candidates
        self.timeout_s = timeout_s
        self.untranslatable = 0
        self.errors = 0
        self.last_error: str | None = None
        self._stderr = open(log, "a") if log else subprocess.DEVNULL
        self.proc = subprocess.Popen(
            [str(paths["python"]), str(ROOT / "pipeline/ag1_server.py"),
             str(paths["ag_dir"]), str(paths["ckpt"]), str(beam_size), str(max_tokens)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self._stderr,
            text=True, bufsize=1, env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home()),
                                       "TF_CPP_MIN_LOG_LEVEL": "2", "JAX_PLATFORMS": "cpu",
                                       "MPLBACKEND": "Agg"})
        line = self._readline(timeout_s)
        if not line.startswith("READY"):
            self.close()
            raise RuntimeError(f"AG1 server did not start: {line!r}")
        self.load_s = float(line.split()[1])

    def _readline(self, timeout: float) -> str:
        end = time.time() + timeout
        while time.time() < end:
            if self.proc.poll() is not None:
                return f"server exited with {self.proc.returncode}"
            ready, _, _ = select.select([self.proc.stdout], [], [], 1.0)
            if ready:
                line = self.proc.stdout.readline()
                if line:
                    return line.strip()
                self.proc.wait(5)
                return f"server exited with {self.proc.returncode} (stderr: options.log)"
        return "timeout"

    def run(self, state: ProofState) -> list[AuxConstruction] | None:
        self.calls += 1
        setup = "; ".join([state.setup, *state.aux_clauses])
        self.proc.stdin.write(json.dumps({"setup": setup, "goal": state.goal}) + "\n")
        self.proc.stdin.flush()
        line = self._readline(self.timeout_s)
        try:
            reply = json.loads(line)
        except json.JSONDecodeError:
            raise RuntimeError(f"AG1 server: {line!r}") from None
        if not reply["ok"]:
            self.errors += 1  # e.g. a construction AG1's defs.txt does not know
            self.last_error = reply["error"]
            return None
        taken = {t for c in [state.setup, *state.aux_clauses] for t in c.replace(",", " ").replace(";", " ").split()}
        new = fresh_point_name(taken)
        out, seen = [], set()
        for c in reply["candidates"]:
            if c["clause"] is None:
                self.untranslatable += 1
                continue
            clause = re.sub(r"\bNEW\b", new, c["clause"])
            if clause not in seen:
                seen.add(clause)
                out.append(AuxConstruction((clause,), self.name, score=c["score"], note=c["raw"]))
            if len(out) >= self.max_candidates:
                break
        return out or None

    def raw(self, prompt: str) -> list[tuple[str, float]]:
        """AG1's beams for a ready AG1 prompt ('{S} ... ? ... {F1} x00'), best first."""
        self.proc.stdin.write(json.dumps({"prompt": prompt}) + "\n")
        self.proc.stdin.flush()
        line = self._readline(self.timeout_s)
        try:
            reply = json.loads(line)
        except json.JSONDecodeError:
            raise RuntimeError(f"AG1 server: {line!r}") from None
        if not reply["ok"]:
            raise RuntimeError(f"AG1 server: {reply['error']}")
        return [(c["raw"], c["score"]) for c in reply["candidates"]]

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass
