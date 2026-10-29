"""solve(): result fields and enforcement of the time and memory limits."""

from pipeline.solve import Budget, solve
from tests.conftest import ORTHOCENTER

DDAR_ONLY = "pipeline/configs/ddar_only.json"


def test_solve_returns_full_result():
    r = solve(ORTHOCENTER, DDAR_ONLY, Budget(time_s=60, memory_mb=2000))
    assert r.solved and r.failure_reason is None
    assert r.proof and len(r.proof) > 20
    assert r.depth == 0
    assert r.tools_used == ["ddar"]
    assert "r43" in r.rules_in_proof and r.rules_fired
    assert r.wall_time > 0 and r.peak_memory_mb > 10 and r.cpu_time > 0


def test_solve_with_heuristics_config():
    r = solve(ORTHOCENTER, "pipeline/configs/heuristics_only.json", Budget(time_s=60))
    assert r.solved and r.ddar_calls == 1


def test_unsolved_problem_reports_reason():
    # Without its orthocenter rule (r43) and with no proposers, DDAR cannot finish.
    config = {
        "tools": {"ddar": {"options": {"config": "ddar/configs/no_orthocenter.json"}}},
        "proposer_order": [],
        "search": {"max_depth": 0},
    }
    r = solve(ORTHOCENTER, config, Budget(time_s=60))
    assert not r.solved and r.failure_reason and r.proof is None


def test_time_limit_is_enforced():
    r = solve(ORTHOCENTER, DDAR_ONLY, Budget(time_s=0.3))
    assert not r.solved
    assert r.failure_reason.startswith("time limit")
    assert r.wall_time < 5


def test_memory_limit_is_enforced():
    r = solve(ORTHOCENTER, DDAR_ONLY, Budget(time_s=60, memory_mb=30))
    assert not r.solved
    assert r.failure_reason.startswith("memory limit")


def test_cpu_limit_is_enforced():
    r = solve(ORTHOCENTER, DDAR_ONLY, Budget(time_s=60, cpu_s=0.2))
    assert not r.solved
    assert r.failure_reason.startswith("CPU limit")
