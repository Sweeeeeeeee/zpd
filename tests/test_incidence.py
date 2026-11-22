"""Regression cases for line and circle merge proof dependencies in Newclid 3.0.1."""
import pytest
from newclid.jgex.problem_builder import JGEXProblemBuilder
from newclid.problem import predicate_to_construction
from newclid.proof_data import proof_data_from_state

from ddar.engine import build_solver
from ddar.rule_config import DDARConfig


@pytest.mark.parametrize(("construction", "goal", "assumptions", "guard"), [
    ("d = on_line d a b; e = on_line e a d", "coll b d e",
     {"coll a b d", "coll a d e"}, "diff a d"),
    ("d = on_circum d a b c; e = on_circum e a b d", "cyclic a c d e",
     {"cyclic a b c d", "cyclic a b d e"}, "ncoll a b d"),
])
def test_merge_proof_supplies_both_incidence_facts(construction, goal, assumptions, guard):
    problem = f"a b c = triangle a b c; {construction} ? {goal}"
    setup = JGEXProblemBuilder(rng=0).with_problem_from_txt(problem).build()
    config = DDARConfig(name="incidence only", engine="python", ar=False, enabled_rules=[])
    solver = build_solver(setup, config)
    assert solver.run()
    goal_predicate, = solver.proof_state.goals
    proof = proof_data_from_state([predicate_to_construction(goal_predicate)], solver.proof_state)
    step, = proof.proof_steps
    premises = {f"{p.predicate_type.value} {' '.join(p.to_tokens())}" for p in step.justification.premises}
    assert premises == assumptions | {guard}
    assert len(set(step.applied_on_predicates)) == 3
    assert "End of proof." in solver.proof()


@pytest.mark.parametrize(("kind", "names", "goal_names"), [
    ("line", ("abd", "ace"), "bde"),
    ("circle", ("abcd", "abef"), "cdef"),
])
def test_distinct_objects_require_enough_shared_points(kind, names, goal_names):
    from types import SimpleNamespace

    from newclid.justifications._index import JustificationError
    from newclid.predicates.collinearity import Coll
    from newclid.predicates.cyclic import Cyclic
    from ddar.incidence import merge_justification

    setup = JGEXProblemBuilder(rng=0).with_problem_from_txt(
        "a b c = triangle a b c; d = free d; e = free e; f = free f ? diff a b"
    ).build()
    points = {str(p.name): p for p in setup.points}
    predicate = Coll if kind == "line" else Cyclic
    facts = [predicate(points=tuple(points[key] for key in group)) for group in names]
    goal = predicate(points=tuple(points[key] for key in goal_names))
    with pytest.raises(JustificationError, match="No chain"):
        merge_justification(goal, facts, SimpleNamespace(points=set(points.values())))
