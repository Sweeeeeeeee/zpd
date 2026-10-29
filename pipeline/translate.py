"""Translate between Newclid (JGEX) problems and the model's text format.

The model (trained on GenesisGeo, step 4) reads problems where each point is
defined by the predicates it satisfies, with points named a, b, c, ... in
construction order:

    a :; b :; c :; d : coll a c d, cong a d c d ? perp b d a c

and writes auxiliary points the same way:

    e : coll a b e, perp a b e d

`problem_to_model_text` builds that input from a DDAR-checked ProofState.
`aux_to_clauses` turns the model's output back into JGEX clauses that Newclid
can draw, by mapping each predicate on the new point to a one-locus
construction (coll -> on_line, perp -> on_tline / on_dia, para -> on_pline,
cong -> on_circle / on_bline / eqdistance, cyclic -> on_circum). Points with a
predicate that has no such mapping (eqangle, aconst, ...) are rejected.
"""

from __future__ import annotations

from ddar.rule_config import NUMERICAL_PREDICATES
from pipeline.tools import ProofState, fresh_point_name


class UntranslatableAux(ValueError):
    pass


def _expand(pred: list[str]) -> list[list[str]]:
    """Rewrite predicates GenesisGeo never uses into the forms it does."""
    name, args = pred[0], pred[1:]
    if name == "midp":  # midp m a b
        m, a, b = args
        return [["coll", a, b, m], ["cong", a, m, b, m]]
    if name == "circle":  # circle o a b c
        o, a, b, c = args
        return [["cong", o, a, o, b], ["cong", o, a, o, c]]
    return [pred]


def problem_to_model_text(state: ProofState) -> tuple[str, dict[str, str]]:
    """Model input for a DDAR-checked state, and the map model name -> problem name."""
    from newclid.jgex.formulation import JGEXFormulation

    if state.builder is None:
        raise ValueError("run the DDAR tool on the state first")
    formulation = JGEXFormulation.from_text(state.text())
    consequences = state.builder.clauses_consequences

    to_model: dict[str, str] = {}
    for clause in formulation.setup_clauses:
        for p in clause.points:
            to_model[str(p)] = fresh_point_name(set(to_model.values()))

    parts = []
    for clause in formulation.setup_clauses:
        preds: list[str] = []
        for pc in consequences[clause].to_assumptions():
            if pc.predicate_type.value in NUMERICAL_PREDICATES:
                continue
            for pred in _expand([pc.predicate_type.value, *map(str, pc.args)]):
                preds.append(" ".join(to_model.get(t, t) for t in pred))
        points = [to_model[str(p)] for p in clause.points]
        if preds:
            parts.append(f"{' '.join(points)} : {', '.join(preds)}")
        else:  # free points are listed one by one in the training data: "a :; b :"
            parts.extend(f"{p} :" for p in points)
    goals = []
    for goal in formulation.goals:
        goals.append(" ".join([goal.predicate_type.value, *(to_model.get(str(a), str(a)) for a in goal.args)]))
    text = "; ".join(parts) + " ? " + ", ".join(goals)
    return text, {m: o for o, m in to_model.items()}


def aux_to_clauses(aux_text: str, to_problem: dict[str, str]) -> tuple[str, ...]:
    """Model output -> JGEX clauses in the problem's point names.

    `to_problem` maps model point names to problem names; it is extended with
    fresh names for the new points.
    """
    names = dict(to_problem)
    clauses = []
    for part in aux_text.split(";"):
        if not part.strip():
            continue
        points_txt, sep, preds_txt = part.partition(":")
        new_points = points_txt.split()
        if not sep or len(new_points) != 1:
            raise UntranslatableAux(f"expected one new point per clause: {part.strip()!r}")
        model_x = new_points[0]
        if model_x in names:
            raise UntranslatableAux(f"point {model_x} already exists")
        x = fresh_point_name(set(names.values()))
        names[model_x] = x
        constructions = []
        for pred_txt in preds_txt.split(","):
            tokens = pred_txt.split()
            if not tokens:
                continue
            try:
                args = [names[t] for t in tokens[1:]]
            except KeyError as e:
                raise UntranslatableAux(f"unknown point {e.args[0]} in {pred_txt.strip()!r}") from None
            constructions.append(_locus(tokens[0], args, x))
        if not constructions:
            raise UntranslatableAux(f"no predicates for {model_x}")
        if len(constructions) > 2:
            constructions = constructions[:2]  # two loci already fix the point
        clauses.append(f"{x} = {', '.join(constructions)}")
    if not clauses:
        raise UntranslatableAux("empty construction")
    return tuple(clauses)


def _locus(name: str, args: list[str], x: str) -> str:
    """One predicate on the new point x -> a JGEX construction placing x on a locus."""
    if x not in args:
        raise UntranslatableAux(f"{name} {' '.join(args)} does not involve the new point")
    others = [a for a in args if a != x]
    if name == "coll" and len(args) == 3 and len(others) == 2:
        return f"on_line {x} {others[0]} {others[1]}"
    if name in ("perp", "para") and len(args) == 4:
        l1, l2 = args[:2], args[2:]
        if x in l1 and x in l2:
            if name == "perp":  # x a perp x b: x on the circle with diameter ab
                return f"on_dia {x} {_other(l1, x)} {_other(l2, x)}"
            raise UntranslatableAux("para with the new point on both lines")
        mine, other = (l1, l2) if x in l1 else (l2, l1)
        if x in other:
            raise UntranslatableAux(f"bad {name}")
        through = _other(mine, x)
        kind = "on_tline" if name == "perp" else "on_pline"
        return f"{kind} {x} {through} {other[0]} {other[1]}"
    if name == "cong" and len(args) == 4:
        s1, s2 = args[:2], args[2:]
        if x in s1 and x in s2:  # x a = x b
            return f"on_bline {x} {_other(s1, x)} {_other(s2, x)}"
        mine, other = (s1, s2) if x in s1 else (s2, s1)
        center = _other(mine, x)
        if center in other:  # center x = center r: circle around center
            return f"on_circle {x} {center} {_other(other, center)}"
        return f"eqdistance {x} {center} {other[0]} {other[1]}"
    if name == "cyclic" and len(args) == 4 and len(others) == 3:
        return f"on_circum {x} {' '.join(others)}"
    raise UntranslatableAux(f"no construction for '{name} {' '.join(args)}'")


def _other(pair: list[str], x: str) -> str:
    a, b = pair
    if a == b:
        raise UntranslatableAux("degenerate segment")
    return b if a == x else a
