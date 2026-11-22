"""Recover directly stated construction equations omitted from an AR step's citation."""
import hashlib

from newclid.jgex.problem_builder import JGEXProblemBuilder
from newclid.predicates import predicate_from_construction
from newclid.symbols.points_registry import PointsRegisty

from bench.latvia.ar_audit import equation, implication
from bench.latvia.scan import accepted_cases

# Only primitive assumptions already expressed in the checker's algebra.
# In particular, no theorem, midpoint expansion or solver-produced fact is added.
KINDS = {"para": "Angle", "perp": "Angle", "eqangle": "Angle", "aconst": "Angle",
         "cong": "Ratio", "eqratio": "Ratio"}


def construction_equations(names, manifest):
    cases = accepted_cases()
    result = {}
    for name in names:
        text = cases[name]
        if hashlib.sha256(text.encode()).hexdigest() != manifest["problems"][name]:
            raise ValueError(f"The formalization of {name} has changed")
        setup = JGEXProblemBuilder(rng=0).with_problem_from_txt(text).build()
        points = PointsRegisty()
        for point in setup.points:
            points.add_point(point)
        facts = []
        for assumption in setup.assumptions:
            kind = KINDS.get(assumption.predicate_type.value)
            if kind:
                printed = str(predicate_from_construction(assumption, points))
                equation(kind, printed)
                facts.append({"construction_fact": str(assumption), "equation": printed, "kind": kind})
        result[name] = facts
    return result


def supplement(step, facts):
    kind, given, goal = step["kind"], step["premises"], step["goal"]
    candidates = sorted({f["equation"] for f in facts if f["kind"] == kind} - set(given))
    if step["outcome"] != "needs_context" or not candidates:
        return []
    if implication(kind, given + candidates, goal) != "follows":
        return []
    for extra in candidates.copy():
        trial = [s for s in candidates if s != extra]
        if implication(kind, given + trial, goal) == "follows":
            candidates = trial
    return candidates
