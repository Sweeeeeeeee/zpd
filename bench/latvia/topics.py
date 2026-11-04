"""Guess whether a problem statement (in Latvian or English) is a geometry problem.

Keyword based, so it is a first sort, not a verdict: the README says how to
override a wrong guess. Returns "plane", "solid" or "" (not geometry) and the
keywords that decided it.
"""

from __future__ import annotations

import re

# Strong signs of a geometric figure. Stems, matched at word starts.
PLANE = [
    "trijstūr", "četrstūr", "piecstūr", "sešstūr", "daudzstūr", "n-stūr", "astoņstūr", "desmitstūr",
    "leņķ", "riņķ", "aplis", "apļa", "aplim", "apli ", "apvilkt", "ievilkt", "bisektris", "mediān",
    "augstum", "perpendikul", "paralelogram", "trapec", "romb", "hord", "pieskar", "rādius", "diametr",
    "nogrieznis", "nogriež", "viduspunkt", "taisnstūr", "kvadrāt abcd", "kvadrātu abcd", "virsotn",
    "vienādsān", "vienādmal", "katet", "hipotenūz", "centrs", "centru", "simetrāl", "ortocentr",
    "smaguma centr", "viduslīnij", "loks", "loka ", "lokā", "plakn", "taisne", "taisnes", "taisni ",
    "triangle", "angle", "circle", "circum", "incircle", "tangent", "perpendicular", "parallel",
    "quadrilateral", "midpoint", "bisector", "polygon", "segment", "concyclic", "collinear",
]
SOLID = ["kub", "daudzskaldn", "divplakņu", "piramīd", "tetraedr", "prizm", "lode", "lodes", "sfēr", "konus", "cilindr", "šķautn",
         "skaldn", "paralēlskaldn", "telpā", "tetrahedron", "pyramid", "sphere", "cube"]
# Signs that the figure is only the board of a combinatorics problem.
BOARD = ["rūtiņ", "šaha", "krāso", "spēlētāj", "gājien", "tabul", "domino", "kartīt", "monēt", "galdiņ",
         "figūriņ", "turnīr", "board", "colour", "color", "game", "player"]

_POINTS = re.compile(r"\b[A-Z][A-Z]?\d?[A-Z]{1,3}\b")   # ABC, AB, A1B1C1 style names
_ANGLE = re.compile(r"[∠∢]|\d\s?°")


def _hits(text: str, stems: list[str]) -> list[str]:
    low = text.lower()
    return sorted({s.strip() for s in stems if re.search(r"(?<![a-zāčēģīķļņšūž])" + re.escape(s), low)})


def geometry_kind(text: str) -> tuple[str, list[str]]:
    plane = _hits(text, PLANE)
    solid = _hits(text, SOLID)
    board = _hits(text, BOARD)
    angle = bool(_ANGLE.search(text))
    points = len(set(_POINTS.findall(text)))
    # "kub" also matches "kubs" of a number (cube of n): require edges/faces or "kubs" with points
    if solid == ["kub"] and not re.search(r"\bkub(s|a|u|ā|am)\b", text.lower()):
        solid = []
    score = len(plane) + 2 * angle + (1 if points >= 2 else 0)
    if board:
        score -= 2 * len(board)
    if solid and (len(solid) >= 2 or points >= 2 or "šķautn" in solid):
        return "solid", solid + plane
    if score >= 2 and (plane or angle):
        return "plane", plane + (["∠/°"] if angle else [])
    return "", plane
