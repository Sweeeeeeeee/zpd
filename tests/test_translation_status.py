import csv
import json

from bench.latvia import translation_status as status


def test_solve_cache_matches_configuration_and_budget(tmp_path):
    out = tmp_path / "solve.json"
    record = dict(hash="abc", config="full", time_s=60, solved=False, failure="time limit (60s)")
    out.write_text(json.dumps(record))
    assert status.cached_solve(out, "abc", "full", 60) == record
    assert status.cached_solve(out, "abc", "circles", 60) is None
    assert status.cached_solve(out, "abc", "full", 90) is None
    for changes in ({"solved": None}, {"failure": "worker crashed"}):
        out.write_text(json.dumps({**record, **changes}))
        assert status.cached_solve(out, "abc", "full", 60) is None


def test_filtered_status_preserves_other_records_and_decisions(tmp_path, monkeypatch):
    monkeypatch.setattr(status, "ROOT", tmp_path)
    monkeypatch.setattr(status, "GT", tmp_path)
    monkeypatch.setattr(status, "WORK", tmp_path / "_work")
    (tmp_path / "decisions.csv").write_text("id,reviewer,decision,reason\nb,owner,reject,duplicate\n")
    rows = [dict(id=k, rel=k, pilot="") for k in ("a", "b")]
    status.write_status(rows)
    status.write_status(rows[:1], partial=True)
    with (tmp_path / "status.csv").open() as stream:
        a, b = csv.DictReader(stream)
    assert a["id"] == "a" and b["id"] == "b"
    assert (b["stage"], b["decision"], b["reviewer"]) == ("rejected", "reject", "owner")


def test_sparse_translation_retries_twelve_seeds_and_requires_four_built(monkeypatch):
    from types import SimpleNamespace
    calls = []

    def simulate(argv, **kwargs):
        seeds = int(argv[-1])
        calls.append(seeds)
        built = 1 if seeds == 6 else 3
        text = "\n".join(f"seed {i}: min point distance 2  goal: ok" for i in range(built))
        return SimpleNamespace(stdout=text + f"\nOK    goal holds in all {built} drawings", returncode=0)

    monkeypatch.setattr(status.subprocess, "run", simulate)
    result = status.check_drawings("figure.txt")
    assert calls == [6, 12]
    assert result["built"] == 3 and not result["figure_ok"]
    assert not status.enough_drawings({"figure_ok": True, "figure": "OK    goal holds in all 1 drawings"})
    assert status.enough_drawings({"figure_ok": True, "figure": "OK    goal holds in all 4 drawings"})
