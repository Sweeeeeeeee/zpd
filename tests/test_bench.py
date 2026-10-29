"""The problem store (step 11): problem files, config fingerprints, stored runs."""

import json

import bench.store as store
from pipeline.solve import Budget


def test_problem_file_metadata(tmp_path):
    folder = tmp_path / "myset"
    folder.mkdir()
    (folder / "p1.txt").write_text(
        "# Varignon: midpoints form a parallelogram.\n# source: classical\n# tags: midpoints\n"
        "a b c d = quadrangle a b c d; e = midpoint e a b; f = midpoint f b c; "
        "g = midpoint g c d; h = midpoint h d a ? para e f g h\n"
    )
    (p,) = store.load_problems(folder)
    assert p.id == "myset/p1"
    assert p.meta == {"source": "classical", "tags": "midpoints"}
    assert p.description.startswith("Varignon")


def test_fingerprint_follows_ddar_config(tmp_path):
    def pipeline(ddar):
        path = tmp_path / f"pipe_{ddar.split('/')[-1]}"
        path.write_text(json.dumps({"tools": {"ddar": {"options": {"config": ddar}}}}))
        return path

    _, a = store.config_fingerprint(pipeline("ddar/configs/default.json"))
    _, b = store.config_fingerprint(pipeline("ddar/configs/no_orthocenter.json"))
    assert a != b


def test_run_stores_and_skips_repeats(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "RESULTS_ROOT", tmp_path / "results")
    folder = tmp_path / "set"
    folder.mkdir()
    (folder / "ortho.txt").write_text(
        "a b c = triangle a b c; h = on_tline h b a c, on_tline h c a b ? perp a h b c\n"
    )
    problems = store.load_problems(folder)
    budget = Budget(time_s=60)
    first = store.run(problems, ["pipeline/configs/ddar_only.json"], budget)
    again = store.run(problems, ["pipeline/configs/ddar_only.json"], budget)
    assert len(first) == 1 and again == []
    (record,) = store.load_records(problems[0])
    assert record["config"] == "ddar_only" and record["result"]["solved"]
    assert set(record) >= {"config_sha", "budget", "date", "git_commit", "result"}
