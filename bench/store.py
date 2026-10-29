"""Problems, result records and running solve() into the store."""

from __future__ import annotations

import json
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


def settings_summary(config_path: str | Path) -> dict:
    """The parameters that matter for interpreting a result."""
    from ddar.rule_config import DDARConfig

    config = json.loads(_resolve(config_path).read_text())
    tools = config.get("tools", {})
    enabled = [n for n, spec in tools.items() if spec.get("enabled", True)]
    summary: dict = {"tools": enabled, "proposer_order": [
        n for n in config.get("proposer_order", enabled) if n in enabled and n != "ddar"]}
    ddar_path = tools.get("ddar", {}).get("options", {}).get("config")
    if "ddar" in enabled and ddar_path:
        ddar = DDARConfig.from_json(_resolve(ddar_path))
        if ddar.engine == "yuclid":  # its rules are compiled in; report those
            from py_yuclid.yuclid_adapter import YUCLID_RULES

            rule_ids = sorted(r.id for r in YUCLID_RULES)
        else:
            rule_ids = ddar.rule_ids()
        summary["ddar"] = {"config": ddar.name, "engine": ddar.engine, "ar": ddar.ar,
                           "n_rules": len(rule_ids), "rules": " ".join(rule_ids)}
    for name in ("transformer", "heuristics"):
        if name in enabled:
            summary[name] = tools[name].get("options", {})
    summary["search"] = config.get("search", {})
    return summary


def make_record(config_name: str, settings: dict, budget: Budget, result) -> dict:
    """What is worth keeping about one solve: settings, resources, outcome."""
    r = asdict(result)
    return {
        "config": config_name,
        "settings": settings,
        "resources": {
            "available": asdict(budget),
            "used": {"wall_time_s": r["wall_time"], "peak_memory_mb": r["peak_memory_mb"],
                     "cpu_time_s": r["cpu_time"], "ddar_calls": r["ddar_calls"]},
        },
        "solved": r["solved"],
        "failure_reason": r["failure_reason"],
        "depth": r["depth"],
        "aux": r["aux"],
        "tools_used": r["tools_used"],
        "rules_in_proof": r["rules_in_proof"],
        "rules_fired": r["rules_fired"],
        "proof": r["proof"],
    }


def run(problems: list[Problem], config_paths: list[str | Path], budget: Budget,
        force: bool = False, on_result=None) -> list[dict]:
    """Solve every problem under every config and store the results.

    A problem keeps one record per (config, available resources); running the
    same combination again is skipped, or replaces the record with --force.
    """
    new_records = []
    for config_path in config_paths:
        name = Path(config_path).stem
        settings = settings_summary(config_path)
        for problem in problems:
            records = load_records(problem)
            same = [r for r in records
                    if r["config"] == name and r["resources"]["available"] == asdict(budget)]
            if same and not force:
                if on_result:
                    on_result(problem, name, same[-1], skipped=True)
                continue
            record = make_record(name, settings, budget, solve(problem.text, _resolve(config_path), budget))
            records = [r for r in records if r not in same] + [record]
            _save_records(problem, records)
            new_records.append(record)
            if on_result:
                on_result(problem, name, record, skipped=False)
    return new_records


def latest_by_config(problem: Problem) -> dict[str, dict]:
    """Last stored record per config name."""
    out: dict[str, dict] = {}
    for r in load_records(problem):
        out[r["config"]] = r
    return out
