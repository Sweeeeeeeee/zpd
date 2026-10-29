"""solve(problem, config, budget): run the pipeline in a child process under limits.

    from pipeline.solve import Budget, solve
    result = solve("a b c = triangle a b c; h = orthocenter h a b c ? perp a h b c",
                   "pipeline/configs/heuristics_only.json",
                   Budget(time_s=60, memory_mb=2000, cpu_s=60))
    print(result.solved, result.failure_reason, result.peak_memory_mb)

    python -m pipeline.solve --config pipeline/configs/ddar_only.json -s "..." --time 30

Limits are enforced from outside the solve: the child runs in its own process
group, and a watchdog polls /proc for the whole process tree (including the
yuclid binary). It kills the group when the wall time, the total RSS, or the
total CPU time (if limited) exceeds the budget. RLIMIT_CPU is also set on the
child as a backstop. Peak memory is the largest total RSS seen by the watchdog (sampled
every 50 ms) or the child's own ru_maxrss, whichever is larger. Linux only.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Budget:
    time_s: float = 60.0  # wall clock
    memory_mb: float = 2048.0  # total RSS of the process tree; 0 = unlimited
    cpu_s: float = 0.0  # total CPU time of the process tree; 0 = unlimited


@dataclass
class SolveResult:
    solved: bool
    proof: str | None
    wall_time: float
    peak_memory_mb: float
    cpu_time: float
    depth: int
    rules_fired: dict[str, int] = field(default_factory=dict)
    rules_in_proof: dict[str, int] = field(default_factory=dict)
    tools_used: list[str] = field(default_factory=list)
    tool_calls: dict[str, int] = field(default_factory=dict)
    aux: list[dict] = field(default_factory=list)
    ddar_calls: int = 0
    failure_reason: str | None = None


def solve(problem: str, config: str | Path | dict, budget: Budget | None = None) -> SolveResult:
    """Solve a JGEX problem with the pipeline config, inside `budget`."""
    budget = budget or Budget()
    if not isinstance(config, dict):
        path = Path(config)
        config = json.loads((path if path.is_absolute() else ROOT / path).read_text())
    cpu_limit = budget.cpu_s
    request = json.dumps({"problem": problem, "config": config})

    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "result.json"
        err_path = Path(tmp) / "stderr.txt"
        t0 = time.time()
        with open(err_path, "w") as err:
            proc = subprocess.Popen(
                [sys.executable, "-m", "pipeline.solve", "--_child", str(out_path)],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=err,
                cwd=ROOT, start_new_session=True,
                preexec_fn=(lambda: _limit_cpu(cpu_limit)) if cpu_limit else None,
            )
            proc.stdin.write(request.encode())
            proc.stdin.close()
            killed, peak_kb, usage, tree_cpu = _watch(proc.pid, budget, cpu_limit, t0)
        wall = time.time() - t0
        peak_mb = max(peak_kb, usage.ru_maxrss) / 1024
        cpu = max(tree_cpu, usage.ru_utime + usage.ru_stime)

        if killed is None and out_path.exists():
            data = json.loads(out_path.read_text())
            return SolveResult(
                solved=data["solved"], proof=data["proof"], wall_time=round(wall, 3),
                peak_memory_mb=round(peak_mb, 1), cpu_time=round(cpu, 2), depth=data["depth"],
                rules_fired=data["rules_fired"], rules_in_proof=data["rules_in_proof"],
                tools_used=data["tools_used"], tool_calls=data["tool_calls"], aux=data["aux"],
                ddar_calls=data["ddar_calls"], failure_reason=data["failure_reason"],
            )
        if killed is None:
            lines = err_path.read_text().strip().splitlines() or ["no output"]
            killed = f"crashed: {lines[-1][:200]}"
        return SolveResult(
            solved=False, proof=None, wall_time=round(wall, 3), peak_memory_mb=round(peak_mb, 1),
            cpu_time=round(cpu, 2), depth=0, failure_reason=killed,
        )


def _limit_cpu(seconds: float) -> None:
    # Backstop for the child itself; the watchdog covers the whole tree.
    limit = int(seconds) + 2
    resource.setrlimit(resource.RLIMIT_CPU, (limit, limit + 1))


def _watch(pid: int, budget: Budget, cpu_limit: float, t0: float):
    """Poll until the child exits; kill its process group if over budget."""
    killed, peak_kb, tree_cpu = None, 0, 0.0
    tick = os.sysconf("SC_CLK_TCK")
    while True:
        done, status, usage = os.wait4(pid, os.WNOHANG)
        if done:
            if killed is None and os.WIFSIGNALED(status):
                sig = os.WTERMSIG(status)
                if sig in (signal.SIGXCPU, signal.SIGKILL):
                    killed = f"CPU limit ({cpu_limit:.0f}s)"
            return killed, peak_kb, usage, tree_cpu
        rss_kb, cpu = _tree_usage(pid, tick)
        peak_kb = max(peak_kb, rss_kb)
        tree_cpu = max(tree_cpu, cpu)
        if killed is None:
            if time.time() - t0 > budget.time_s:
                killed = f"time limit ({budget.time_s:.0f}s)"
            elif budget.memory_mb and rss_kb / 1024 > budget.memory_mb:
                killed = f"memory limit ({budget.memory_mb:.0f} MB)"
            elif cpu_limit and cpu > cpu_limit:
                killed = f"CPU limit ({cpu_limit:.0f}s)"
            if killed:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        time.sleep(0.05)


def _tree_usage(root: int, tick: int) -> tuple[int, float]:
    """(total RSS in kB, total CPU seconds) of `root` and its descendants."""
    rss, cpu, todo, seen = 0, 0.0, [root], set()
    while todo:
        pid = todo.pop()
        if pid in seen:
            continue
        seen.add(pid)
        try:
            with open(f"/proc/{pid}/stat") as f:
                fields = f.read().rsplit(")", 1)[1].split()
            cpu += (int(fields[11]) + int(fields[12])) / tick  # utime + stime
            rss += int(fields[21]) * os.sysconf("SC_PAGE_SIZE") // 1024
            for task in os.listdir(f"/proc/{pid}/task"):
                with open(f"/proc/{pid}/task/{task}/children") as f:
                    todo.extend(int(c) for c in f.read().split())
        except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
            continue
    return rss, cpu


def _child(out_path: str) -> None:
    from pipeline.search import SearchLimits, load_tools, search

    request = json.loads(sys.stdin.read())
    config = request["config"]
    ddar, proposers = load_tools(config)
    result = search(request["problem"], ddar, proposers, SearchLimits(**config.get("search", {})))
    Path(out_path).write_text(json.dumps(asdict(result)))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--_child", help=argparse.SUPPRESS)
    ap.add_argument("--config", default="pipeline/configs/default.json")
    ap.add_argument("-s", "--problem")
    ap.add_argument("--time", type=float, default=60.0, help="wall-clock limit, seconds")
    ap.add_argument("--memory", type=float, default=2048.0, help="memory limit, MB (0 = none)")
    ap.add_argument("--cpu", type=float, default=0.0, help="CPU limit, seconds (0 = none)")
    args = ap.parse_args()
    if args._child:
        _child(args._child)
        return
    if not args.problem:
        ap.error("-s/--problem is required")
    result = solve(args.problem, args.config, Budget(args.time, args.memory, args.cpu))
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    main()
