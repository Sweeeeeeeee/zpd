import pytest

from bench.latvia.ar_audit import audit_proof, implication


def test_hexagon_ratio_requires_unit_scale():
    ratio = "AE:BD = EF:BC"
    assert implication("Ratio", [ratio], "BC = EF") == "needs_context"
    assert implication("Ratio", [ratio, "AE = BD"], "BC = EF") == "follows"


def test_angle_chase_uses_integer_combinations_modulo_pi():
    assert implication("Angle", ["AB ⟂ BC", "BC ⟂ CD"], "AB ∥ CD") == "follows"
    assert implication("Angle", ["∠(AB,BC) = ∠(BC,AB)"], "AB ∥ BC") == "needs_context"
    assert implication("Angle", ["∠(AB,BC) = 1pi/3"], "∠(BC,AB) = 2pi/3") == "follows"
    assert implication("Angle", ["AB ⟂ BC", "AB ∥ BC"], "CD ∥ EF") == "inconsistent_premises"


def test_identity_segment_orientation_and_subscripts():
    assert implication("Ratio", [], "O₁A = AO₁") == "follows"
    assert implication("Angle", [], "O₁A ∥ AO₁") == "follows"
    assert implication("Angle", [], "O₁A ∥ AO₂") == "needs_context"


def test_malformed_or_uncounted_appendix_cannot_pass_silently():
    row = {"name": "sample", "rules_in_proof": {"AR:angle": 1}, "proof": ""}
    with pytest.raises(ValueError, match="Appendix count"):
        audit_proof(row)
    row["proof"] = "000. | Angle Chasing to prove AB ∥ CD:"
    with pytest.raises(ValueError, match="Malformed"):
        audit_proof(row)


def test_supplement_requires_an_explicit_sufficient_construction_fact():
    from bench.latvia.ar_context import supplement

    step = {"kind": "Ratio", "premises": ["AE:BD = EF:BC"], "goal": "BC = EF", "outcome": "needs_context"}
    facts = [{"equation": "AB = DE", "kind": "Ratio"}, {"equation": "AE = BD", "kind": "Ratio"},
             {"equation": "AB ∥ DE", "kind": "Angle"}]
    assert supplement(step, facts[:1]) == []
    assert supplement(step, facts) == ["AE = BD"]


def test_missing_seed_or_unsupported_drawing_pass_rejected():
    from bench.latvia.sample_audit import summarize

    case = {"name": "a", "drawings": [{"seed": 0, "goals": {"goal": True}, "outcome": "all_goals_hold"}]}
    data = {"seeds": [0], "cases": [case]}
    assert summarize(data)["outcomes"]["all_goals_hold"] == 1
    case["drawings"][0]["goals"]["goal"] = False
    with pytest.raises(ValueError, match="Passing drawing"):
        summarize(data)
    case["drawings"].clear()
    with pytest.raises(ValueError, match="Missing"):
        summarize(data)
