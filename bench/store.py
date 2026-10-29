"""Problems, result records and running solve() into the store."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pipeline.solve import ROOT, Budget, solve

RESULTS_ROOT = ROOT / "results"


@dataclass
class Problem:
    set: str
    name: str
    text: str
    description: str = ""
    meta: dict[str, str] = field(default_factory=dict)  # source, tags, ...
    path: Path | None = None

    @property
    def id(self) -> str:
        return f"{self.set}/{self.name}"

    @property
    def results_path(self) -> Path:
        return RESULTS_ROOT / self.set / f"{self.name}.json"


def parse_problem_file(path: Path, set_name: str | None = None) -> Problem:
    description, meta, lines = [], {}, []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            body = line.lstrip("#").strip()
            key, sep, value = body.partition(":")
            key = key.strip()
            if sep and key.isidentifier() and key.islower():  # "# source: IMO 2004"
                meta[key] = value.strip()
            else:
                description.append(body)
        else:
            lines.append(line)
    if len(lines) != 1:
        raise ValueError(f"{path}: expected exactly one problem line, found {len(lines)}")
    return Problem(set_name or path.parent.name, path.stem, lines[0], " ".join(description), meta, path)


def load_problems(folder: str | Path) -> list[Problem]:
    folder = Path(folder)
    folder = folder if folder.is_absolute() else ROOT / folder
    return [parse_problem_file(p, folder.name) for p in sorted(folder.glob("*.txt"))]


def load_records(problem: Problem) -> list[dict]:
    path = problem.results_path
    return json.loads(path.read_text())["records"] if path.exists() else []


def _save_records(problem: Problem, records: list[dict]) -> None:
    path = problem.results_path
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {"problem": problem.id, "text": problem.text, "description": problem.description,
           "meta": problem.meta, "records": records}
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def _resolve(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def config_fingerprint(config_path: str | Path) -> tuple[dict, str]:
    """(config dict, short hash of it and of the DDAR config file it uses)."""
    config = json.loads(_resolve(config_path).read_text())
    parts = [json.dumps(config, sort_keys=True)]
    ddar = config.get("tools", {}).get("ddar", {}).get("options", {}).get("config")
    if ddar and _resolve(ddar).exists():
        parts.append(json.dumps(json.loads(_resolve(ddar).read_text()), sort_keys=True))
    checkpoint = config.get("tools", {}).get("transformer", {})
    if checkpoint.get("enabled", True) and (ck := checkpoint.get("options", {}).get("checkpoint")):
        if _resolve(ck).exists():  # a retrained model is a different setting
            parts.append(str(_resolve(ck).stat().st_mtime_ns))
    return config, hashlib.sha1("\n".join(parts).encode()).hexdigest()[:10]


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, timeout=10)
        commit = out.stdout.strip()
        if not commit:
            return None
        # Uncommitted code changes (stored results themselves don't count).
        dirty = subprocess.run(["git", "status", "--porcelain", "--", ".", ":!results"],
                               cwd=ROOT, capture_output=True, text=True, timeout=10)
        return commit + ("+dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.TimeoutExpired):
        return None


def run(problems: list[Problem], config_paths: list[str | Path], budget: Budget,
        force: bool = False, on_result=None) -> list[dict]:
    """Solve every problem under every config; append new records to the store."""
    commit = _git_commit()
    new_records = []
    for config_path in config_paths:
        config, sha = config_fingerprint(config_path)
        name = Path(config_path).stem
        for problem in problems:
            records = load_records(problem)
            same = [r for r in records if r["config_sha"] == sha and r["budget"] == asdict(budget)]
            if same and not force:
                if on_result:
                    on_result(problem, name, same[-1], skipped=True)
                continue
            result = solve(problem.text, config, budget)
            record = {
                "config": name, "config_sha": sha, "budget": asdict(budget),
                "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "git_commit": commit, "result": asdict(result),
            }
            records.append(record)
            _save_records(problem, records)
            new_records.append(record)
            if on_result:
                on_result(problem, name, record, skipped=False)
    return new_records


def latest_by_config(problem: Problem) -> dict[str, dict]:
    """Most recent record per config name."""
    out: dict[str, dict] = {}
    for r in load_records(problem):
        out[r["config"]] = r
    return out
