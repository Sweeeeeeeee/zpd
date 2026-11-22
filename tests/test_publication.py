import json

import pytest

from bench.publish import construction, score


def test_strict_match_preserves_point_and_argument_roles():
    gold = "x : coll a b x, perp x a b c"
    assert construction(gold) == construction("x : perp x a b c, coll a b x")
    assert construction(gold) != construction("x : coll a b x, perp x b a c")
    assert construction(gold) != construction("j : coll a b x, perp x a b c")


def test_empty_reference_stays_in_denominator():
    rows = [{"gold": "x :", "beams": ["x :"], "exact": [True], "seconds": 0.1}]
    assert score(rows) == {"n": 1, "top1": 0, "top4": 0, "relaxed": 1, "empty": 1, "seconds": 0.1}


def test_case_table_uses_official_grade_for_the_frozen_altitude_problem():
    from bench.latvia.case_table import render_cases
    from bench.publish import ROOT

    fresh = json.loads((ROOT / "results/latvia-audit/fresh-drawings.json").read_text())
    passed = {row["name"]: row["all_goals_hold"] for row in fresh["records"]}
    table = render_cases(ROOT, passed)
    circles = next(line for line in table.splitlines() if "/national/1998-99_49/grade12/p2.md" in line)
    assert circles.endswith("<td>34</td></tr>")
    assert table.count('<tr data-outcome=') == 65
    assert table.count('<tr data-outcome="proved">') == 20
    assert "/2008-09_59/grade09/p4.md" in table
    assert "/2008-09_59/grade10/p4.md" not in table


def test_fresh_drawing_audit_rejects_repeated_seeds():
    from bench.latvia.fresh_drawings import frozen_hashes, summarize
    from bench.publish import ROOT

    data = json.loads((ROOT / "results/latvia-audit/fresh-drawings.json").read_text())
    hashes = frozen_hashes()
    totals = summarize(data, hashes)
    assert totals["attempts"] == 4160
    assert totals["all_goals_hold"] + totals["unbuilt"] == 4160
    row = next(row for row in data["records"] if row["unbuilt"])
    row["degenerate"].append(row["unbuilt"][0])
    row["all_goals_hold"] -= 1
    with pytest.raises(ValueError, match="Inconsistent seed outcomes"):
        summarize(data, hashes)


def test_student_score_columns_are_joined_to_the_correct_problem_and_solver():
    from bench.latvia.student_scores import compare
    from bench.publish import ROOT

    matches = compare(ROOT)
    assert [(r["mean"], r["rank_by_mean"], r["revised"]) for r in matches] == [
        (3.92, 2, "proved"), (5.69, 1, "timeouts"),
    ]
