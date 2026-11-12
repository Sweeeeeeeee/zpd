"""Degrees of freedom of a Newclid problem: the hidden-specialisation check.

A translation can be true and still easier than the original: a general
triangle quietly made isosceles, a free point put on a special line. Then the
translated figure has fewer free parameters than the statement. The
translator writes the statement's count in the problem file,

    # dof: 3   (triangle: 2 shape parameters; P on side BC: 1)

and this module counts the translation's:
  every construction gives its new points some freedom (on_line: 1 per point,
  foot / midpoint / intersection: 0, triangle: 6, ...); a clause with several
  constructions intersects them (each one removes 2 per new point minus its
  freedom); the whole figure is counted up to similarity (minus 4: position,
  rotation, scale) when it has at least two free points.

    python -m pipeline.dof problems/latvia/geometry_translated/...txt   # checks "# dof:"
    python -m pipeline.dof -s "a b c = triangle a b c; d = on_line d b c ? ..."
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Freedom of a construction's new points, when used alone in a clause.
SHAPES = {  # no input points: the figure starts here
    "free": 2, "segment": 4, "between": 5, "triangle": 6, "acute_triangle": 6, "r_triangle": 5,
    "iso_triangle": 5, "iso_triangle0": 5, "ieq_triangle": 4, "triangle12": 5, "risos": 4,
    "quadrangle": 8, "pentagon": 10, "rectangle": 5, "isquare": 4, "trapezoid": 7, "r_trapezoid": 6,
    "iso_trapezoid": 6, "eq_quadrangle": 7, "eqdia_quadrangle": 7,
}
ONE = {  # one condition on a point: it moves on a line or circle
    "on_line", "on_pline", "on_pline0", "on_tline", "on_aline", "on_aline0", "on_bline", "on_circle",
    "on_circum", "on_dia", "eqangle2", "eqangle3", "eqratio", "eqratio6", "lconst", "l2const", "rconst",
    "rconst2", "r2const", "aconst", "s_angle", "eqdistance", "angle_bisector", "angle_mirror",
    "between_bound", "lc_tangent", "iso_triangle_vertex",
}
# Everything else in Newclid (foot, midpoint, intersections, circle, incenter, square, tangent, ...)
# fixes its new points: freedom 0.
ZERO = {
    "intersection_ll", "intersection_lp", "intersection_pp", "intersection_lt", "intersection_tt",
    "intersection_lc", "intersection_cc", "tangent", "cc_tangent", "cc_itangent", "iso_triangle_vertex_angle",
    "eq_triangle", "iso_trapezoid2", "parallelogram", "square", "circle", "circumcenter", "psquare", "nsquare",
    "centroid", "simtri", "simtrir", "contri", "contrir", "2l1c", "e5128", "3peq", "foot", "incenter",
    "incenter2", "excenter", "excenter2", "midpoint", "mirror", "orthocenter", "reflect", "shift", "trisect",
    "trisegment",
}
# Constructions whose first arguments are not all new points (the new one comes later).
NEW_POSITION = {"aconst": 3, "rconst": 3, "r2const": 3, "s_angle": 2}


def construction_freedom(name: str, n_new: int) -> int | None:
    if name in SHAPES:
        return SHAPES[name]
    if name in ONE:
        return n_new  # one free parameter per new point (in practice one point)
    if name in ZERO:
        return 0
    return None


def count(problem: str) -> dict:
    """{'total', 'shape', 'free_points', 'unknown': [...], 'clauses': [(text, dof), ...]}"""
    setup = problem.split("?")[0]
    total, unknown, clauses = 0, [], []
    for clause in setup.split(";"):
        if "=" not in clause:
            continue
        pts, body = clause.split("=", 1)
        new = pts.split()
        dof_clause, removed, shape = 2 * len(new), 0, None
        for cons in body.split(","):
            toks = cons.split()
            if not toks:
                continue
            name = toks[0]
            f = construction_freedom(name, len(new))
            if f is None:
                unknown.append(name)
                continue
            if name in SHAPES:
                shape = f
            else:
                removed += 2 * len(new) - f
        d = shape if shape is not None else max(0, dof_clause - removed)
        total += d
        clauses.append((" ".join(clause.split()), d))
    shape_dof = total - 4 if total >= 4 else total
    return {"total": total, "shape": shape_dof, "unknown": unknown, "clauses": clauses}


def check_file(path: Path) -> tuple[bool | None, str]:
    text = path.read_text()
    m = re.search(r"^#\s*dof:\s*(\d+)", text, re.M)
    lines = [l for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        return None, "no problem line"
    c = count(lines[0])
    if c["unknown"]:
        return None, f"unknown constructions {c['unknown']}: count by hand"
    if not m:
        return None, f"translation has {c['shape']} shape parameters; no '# dof:' line to compare"
    want = int(m.group(1))
    ok = want == c["shape"]
    return ok, (f"statement {want}, translation {c['shape']}" +
                ("" if ok else "  <- MISMATCH: hidden specialisation or a missing condition"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("-s", "--problem")
    a = ap.parse_args()
    if a.problem:
        c = count(a.problem)
        for cl, d in c["clauses"]:
            print(f"{d:2d}  {cl}")
        print(f"total {c['total']}, up to similarity {c['shape']}" + (f", unknown {c['unknown']}" if c["unknown"] else ""))
    bad = 0
    for f in a.files:
        ok, msg = check_file(Path(f))
        bad += ok is False
        print(f"{'OK ' if ok else '?? ' if ok is None else 'BAD'} {f}: {msg}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
