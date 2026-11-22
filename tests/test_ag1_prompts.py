from bench.eval_proposers import _ag_pred, ag1_prompt, from_ag1


def test_triangle_prompt_keeps_vertex_correspondence_in_both_orientations():
    assert ag1_prompt("a :; b : ? contrir a d f c d f").endswith("? = a d f c d f {F1} x00")
    assert _ag_pred("simtrir", "a b c p q r".split()) == "S a b c p q r"
    assert _ag_pred("eqratio3", "a b c d o o".split()) == "S o a b o c d"


def test_ratio_and_angle_constants_use_different_units():
    args = "a b a c 1/2".split()
    assert _ag_pred("rconst", args) == "/ a b a c 1/2"
    assert _ag_pred("aconst", args) == "^ a b a c 1. pi / 2."
    assert _ag_pred("aconst", args, goal=True) == "^ a b a c 1pi/2"
    assert from_ag1("j : / a b a j 1/2 01") == "j : rconst a b a j 1/2"
