from bench.publish import construction, score


def test_strict_match_preserves_point_and_argument_roles():
    gold = "x : coll a b x, perp x a b c"
    assert construction(gold) == construction("x : perp x a b c, coll a b x")
    assert construction(gold) != construction("x : coll a b x, perp x b a c")
    assert construction(gold) != construction("j : coll a b x, perp x a b c")


def test_empty_reference_stays_in_denominator():
    rows = [{"gold": "x :", "beams": ["x :"], "exact": [True], "seconds": 0.1}]
    assert score(rows) == {"n": 1, "top1": 0, "top4": 0, "relaxed": 1, "empty": 1, "seconds": 0.1}
