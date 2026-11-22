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
