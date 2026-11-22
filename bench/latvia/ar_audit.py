"""Check the equations explicitly listed for each Newclid AR appendix step.

Ratios are linear in log lengths. Directed line angles live modulo pi, so
only integer combinations of angle rows preserve congruences. Point and
construction facts elsewhere in a transcript are outside this local check.
"""
import re
from collections import Counter
from fractions import Fraction
from math import lcm

from sympy import Matrix, zeros
from sympy.matrices.normalforms import hermite_normal_form

POINT = r"[A-Z][₀₁₂₃₄₅₆₇₈₉]*"
SEGMENT = re.compile(f"({POINT})({POINT})")
ANGLE = re.compile(r"∠\(([^,()]+),([^,()]+)\)")
CONSTANT = re.compile(r"(-?\d+)pi/(\d+)")
HEADER = re.compile(r"(\d+)\. \| (Angle|Ratio) Chasing to prove (.+):")
PREMISE = re.compile(r"\| Premise (.+) gives a linear equation with coefficients .*")
ENDING = re.compile(r"We are left with a linear equation with coefficients .* that gives (.+)")


def segment(text):
    match = SEGMENT.fullmatch(text)
    if not match or match[1] == match[2]:
        raise ValueError(f"Unsupported segment {text!r}")
    return "".join(sorted(match.groups()))


def equation(kind, text):
    """Return variable coefficients and the right side in units of pi for angles."""
    coeff = Counter()
    rhs = Fraction(0)
    if kind == "Angle" and (" ∥ " in text or " ⟂ " in text):
        left, right = re.split(" [∥⟂] ", text)
        coeff[segment(right)] += 1
        coeff[segment(left)] -= 1
        rhs = Fraction(1, 2) if " ⟂ " in text else Fraction(0)
    else:
        left, right = text.split(" = ")
        for side, sign in ((left, 1), (right, -1)):
            if kind == "Ratio":
                parts = side.split(":")
                if len(parts) > 2:
                    raise ValueError(f"Unsupported ratio {side!r}")
                coeff[segment(parts[0])] += sign
                if len(parts) == 2:
                    coeff[segment(parts[1])] -= sign
            elif kind == "Angle":
                if angle := ANGLE.fullmatch(side):
                    coeff[segment(angle[2])] += sign
                    coeff[segment(angle[1])] -= sign
                elif constant := CONSTANT.fullmatch(side):
                    rhs -= sign * Fraction(int(constant[1]), int(constant[2]))
                else:
                    raise ValueError(f"Unsupported angle {side!r}")
            else:
                raise ValueError(f"Unknown AR kind {kind!r}")
    return coeff, rhs


def implication(kind, premises, goal):
    equations = [equation(kind, s) for s in [*premises, goal]]
    names = sorted(set().union(*(coeff for coeff, _ in equations)))
    rows = [[coeff[name] for name in names] for coeff, _ in equations]
    if kind == "Ratio":
        given = Matrix(rows[:-1]) if premises else zeros(0, len(names))
        return "follows" if given.rank() == Matrix(rows).rank() else "needs_context"

    # The final column is a constant modulo denominator. Include one full
    # turn so, for example, two right angles imply parallel directions.
    denominator = lcm(*(rhs.denominator for _, rhs in equations))
    for row, (_, rhs) in zip(rows, equations):
        row.append(int(-rhs * denominator))
    unit = [0] * len(names)
    basis = hermite_normal_form(Matrix([unit + [denominator], *rows[:-1]]).T)

    def contains(row):
        return hermite_normal_form(basis.row_join(Matrix(row))) == basis

    if any(contains(unit + [k]) for k in range(1, denominator)):
        return "inconsistent_premises"
    return "follows" if contains(rows[-1]) else "needs_context"


def audit_proof(row):
    lines = row["proof"].splitlines()
    steps = []
    for i, line in enumerate(lines):
        header = HEADER.fullmatch(line)
        if not header:
            continue
        number, kind, goal = header.groups()
        premises = []
        i += 1
        while i < len(lines) and (match := PREMISE.fullmatch(lines[i])):
            premises.append(match[1])
            i += 1
        end = ENDING.fullmatch(lines[i]) if i < len(lines) else None
        if not end or end[1] != goal:
            raise ValueError(f"Malformed appendix in {row['name']}, step {number}")
        steps.append({"step": int(number), "kind": kind, "premises": premises,
                      "goal": goal, "outcome": implication(kind, premises, goal)})
    counted = Counter(s["kind"] for s in steps)
    for kind in ("Angle", "Ratio"):
        if counted[kind] != row["rules_in_proof"].get("AR:" + kind.lower(), 0):
            raise ValueError(f"Appendix count differs from {kind} rule count in {row['name']}")
    if len({s["step"] for s in steps}) != len(steps):
        raise ValueError(f"Duplicate appendix step in {row['name']}")
    return steps
