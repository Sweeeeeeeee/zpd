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

    table = render_cases(ROOT)
    assert table.count('<tr data-outcome=') == 65
    assert table.count('<tr data-outcome="proved">') == 20
    assert "/2008-09_59/grade09/p4.md" in table
    assert "/2008-09_59/grade10/p4.md" not in table
