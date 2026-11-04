"""Turn an archive file (.docx, .doc, .pdf) into plain UTF-8 text.

.docx is read straight from its XML so that Word "Symbol" font characters
(angle, degree, Greek letters, ...) become real Unicode and equations written
with Office Math keep their text. Equation Editor objects and pictures cannot
be read; they become the markers [formula] and [attēls]. .doc files are
converted to .docx with LibreOffice first. PDFs go through pdftotext.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

# Adobe Symbol font, code points 0x20-0xFF (Word stores them as 0xF0xx).
_SYMBOL = {
    0x22: "∀", 0x24: "∃", 0x27: "∋", 0x2A: "∗", 0x2D: "−", 0x40: "≅",
    0x41: "Α", 0x42: "Β", 0x43: "Χ", 0x44: "Δ", 0x45: "Ε", 0x46: "Φ", 0x47: "Γ",
    0x48: "Η", 0x49: "Ι", 0x4B: "Κ", 0x4C: "Λ", 0x4D: "Μ", 0x4E: "Ν", 0x4F: "Ο",
    0x50: "Π", 0x51: "Θ", 0x52: "Ρ", 0x53: "Σ", 0x54: "Τ", 0x55: "Υ", 0x57: "Ω",
    0x58: "Ξ", 0x59: "Ψ", 0x5A: "Ζ", 0x5C: "∴", 0x5E: "⊥",
    0x61: "α", 0x62: "β", 0x63: "χ", 0x64: "δ", 0x65: "ε", 0x66: "φ", 0x67: "γ",
    0x68: "η", 0x69: "ι", 0x6A: "ϕ", 0x6B: "κ", 0x6C: "λ", 0x6D: "μ", 0x6E: "ν",
    0x6F: "ο", 0x70: "π", 0x71: "θ", 0x72: "ρ", 0x73: "σ", 0x74: "τ", 0x75: "υ",
    0x76: "ϖ", 0x77: "ω", 0x78: "ξ", 0x79: "ψ", 0x7A: "ζ", 0x7E: "∼",
    0xA2: "′", 0xA3: "≤", 0xA4: "⁄", 0xA5: "∞", 0xAB: "↔", 0xAC: "←", 0xAD: "↑",
    0xAE: "→", 0xAF: "↓", 0xB0: "°", 0xB1: "±", 0xB2: "″", 0xB3: "≥", 0xB4: "×",
    0xB5: "∝", 0xB6: "∂", 0xB7: "•", 0xB8: "÷", 0xB9: "≠", 0xBA: "≡", 0xBB: "≈",
    0xBC: "…", 0xC4: "⊗", 0xC5: "⊕", 0xC6: "∅", 0xC7: "∩", 0xC8: "∪", 0xC9: "⊃",
    0xCA: "⊇", 0xCB: "⊄", 0xCC: "⊂", 0xCD: "⊆", 0xCE: "∈", 0xCF: "∉", 0xD0: "∠",
    0xD1: "∇", 0xD5: "∏", 0xD6: "√", 0xD7: "⋅", 0xD8: "¬", 0xD9: "∧", 0xDA: "∨",
    0xDB: "⇔", 0xDE: "⇒", 0xE0: "◊", 0xE5: "∑", 0xF2: "∫",
}


def _symbol(code: int) -> str:
    code &= 0xFF
    return _SYMBOL.get(code, chr(code) if 0x20 <= code < 0x7F else "")


def _run_font(run) -> str:
    rpr = run.find(W + "rPr")
    if rpr is None:
        return ""
    fonts = rpr.find(W + "rFonts")
    return "" if fonts is None else (fonts.get(W + "ascii") or fonts.get(W + "hAnsi") or "")


def _vertical(run) -> str:
    rpr = run.find(W + "rPr")
    va = None if rpr is None else rpr.find(W + "vertAlign")
    return "" if va is None else va.get(W + "val", "")


MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"
_SKIP = {MC + "Fallback", W + "rPr", W + "pPr", W + "instrText", W + "delText", M + "rPr", M + "ctrlPr"}


def _math(node) -> str:
    """Render an Office Math subtree as linear text: fractions as (a)/(b), powers as ^, roots as √."""
    tag = node.tag

    def part(name):
        child = node.find(M + name)
        return "" if child is None else _math(child)

    def wrap(text):
        return text if len(text) <= 1 or text.isalnum() else "(" + text + ")"

    if tag == M + "t":
        return node.text or ""
    if tag == M + "f":
        return wrap(part("num")) + "/" + wrap(part("den"))
    if tag == M + "sSup":
        return part("e") + "^" + wrap(part("sup"))
    if tag == M + "sSub":
        return part("e") + "_" + wrap(part("sub"))
    if tag == M + "sSubSup":
        return part("e") + "_" + wrap(part("sub")) + "^" + wrap(part("sup"))
    if tag == M + "rad":
        deg = part("deg")
        return ("^" + deg if deg else "") + "√" + wrap(part("e"))
    if tag == M + "d":
        pr = node.find(M + "dPr")
        beg, end = "(", ")"
        if pr is not None:
            b, e = pr.find(M + "begChr"), pr.find(M + "endChr")
            beg = b.get(M + "val", "") if b is not None else beg
            end = e.get(M + "val", "") if e is not None else end
        return beg + ", ".join(_math(e) for e in node.findall(M + "e")) + end
    if tag == M + "nary":
        pr = node.find(M + "naryPr")
        chr_ = pr.find(M + "chr") if pr is not None else None
        op = chr_.get(M + "val", "∫") if chr_ is not None else "∫"
        return op + "_" + wrap(part("sub")) + "^" + wrap(part("sup")) + " " + part("e")
    if tag in (M + "rPr", M + "ctrlPr", M + "dPr", M + "fPr", M + "radPr", M + "naryPr"):
        return ""
    return "".join(_math(c) for c in node)


def _inline(node, out: list[str], boxes: list) -> None:
    tag = node.tag
    if tag in _SKIP:
        return
    if tag == W + "r":
        symbol_font = _run_font(node).lower().startswith("symbol")
        va = _vertical(node)
        for child in node:
            if child.tag == W + "t" and child.text:
                text = child.text
                if symbol_font:
                    text = "".join(_symbol(ord(c)) for c in text)
                if va == "superscript":
                    text = "^" + text if len(text) == 1 else "^(" + text + ")"
                elif va == "subscript":
                    text = "_" + text if len(text) == 1 else "_(" + text + ")"
                out.append(text)
            elif child.tag == W + "sym":
                out.append(_symbol(int(child.get(W + "char", "0"), 16)))
            elif child.tag == W + "tab":
                out.append(" ")
            elif child.tag in (W + "br", W + "cr"):
                out.append("\n")
            elif child.tag == W + "object":
                out.append("[formula]")
            elif child.tag in (W + "drawing", W + "pict"):
                found = [b for b in child.iter(W + "txbxContent")]
                if found:
                    boxes.extend(found)
                else:
                    out.append("[attēls]")
            else:
                _inline(child, out, boxes)
        return
    if tag in (M + "oMath", M + "oMathPara"):
        out.append(_math(node))
        return
    if tag == W + "txbxContent":
        boxes.append(node)
        return
    for child in node:
        _inline(child, out, boxes)


def _blocks(node, lines: list[str], numbering) -> None:
    tag = node.tag
    if tag in _SKIP:
        return
    if tag == W + "p":
        out: list[str] = []
        boxes: list = []
        _inline(node, out, boxes)
        lines.append(numbering.label(node) + "".join(out))
        for box in boxes:  # text boxes (figure labels etc.) after their paragraph
            _blocks(box, lines, numbering)
        return
    if tag == W + "tr":
        cells = []
        for tc in node.findall(W + "tc"):
            sub: list[str] = []
            _blocks(tc, sub, numbering)
            cells.append(" ".join(x for x in sub if x.strip()))
        lines.append(" | ".join(cells))
        return
    for child in node:
        _blocks(child, lines, numbering)


def _roman(n: int) -> str:
    vals = [(1000, "m"), (900, "cm"), (500, "d"), (400, "cd"), (100, "c"), (90, "xc"),
            (50, "l"), (40, "xl"), (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for v, r in vals:
        while n >= v:
            out, n = out + r, n - v
    return out


def _format_number(n: int, fmt: str) -> str:
    if fmt in ("lowerLetter",):
        return chr(ord("a") + (n - 1) % 26)
    if fmt == "upperLetter":
        return chr(ord("A") + (n - 1) % 26)
    if fmt == "lowerRoman":
        return _roman(n)
    if fmt == "upperRoman":
        return _roman(n).upper()
    if fmt in ("bullet", "none"):
        return ""
    return str(n)


class _Numbering:
    """Word list numbering (numbering.xml): turns w:numPr into the visible label, e.g. "3." or "b)"."""

    def __init__(self, xml: bytes | None):
        self.levels: dict[str, dict[int, tuple[str, str, int]]] = {}
        self.counters: dict[str, list[int]] = {}
        if not xml:
            return
        root = ET.fromstring(xml)
        abstract = {}
        for a in root.findall(W + "abstractNum"):
            lv = {}
            for l in a.findall(W + "lvl"):
                ilvl = int(l.get(W + "ilvl", "0"))
                fmt = l.find(W + "numFmt")
                txt = l.find(W + "lvlText")
                start = l.find(W + "start")
                lv[ilvl] = (fmt.get(W + "val") if fmt is not None else "decimal",
                            txt.get(W + "val") if txt is not None else "%1.",
                            int(start.get(W + "val")) if start is not None else 1)
            abstract[a.get(W + "abstractNumId")] = lv
        for n in root.findall(W + "num"):
            aid = n.find(W + "abstractNumId")
            if aid is not None:
                self.levels[n.get(W + "numId")] = abstract.get(aid.get(W + "val"), {})
        self.abstract_of = {n.get(W + "numId"): (n.find(W + "abstractNumId").get(W + "val")
                                                 if n.find(W + "abstractNumId") is not None else None)
                            for n in root.findall(W + "num")}

    def label(self, p) -> str:
        ppr = p.find(W + "pPr")
        numpr = None if ppr is None else ppr.find(W + "numPr")
        if numpr is None:
            return ""
        nid = numpr.find(W + "numId")
        lvl = numpr.find(W + "ilvl")
        num_id = nid.get(W + "val") if nid is not None else None
        ilvl = int(lvl.get(W + "val")) if lvl is not None else 0
        levels = self.levels.get(num_id)
        if not levels or ilvl not in levels:
            return ""
        key = self.abstract_of.get(num_id) or num_id  # lists sharing an abstract definition continue
        counters = self.counters.setdefault(key, [0] * 9)
        if counters[ilvl] == 0:
            counters[ilvl] = levels[ilvl][2] - 1
        counters[ilvl] += 1
        for deeper in range(ilvl + 1, 9):
            counters[deeper] = 0
        fmt, text, _ = levels[ilvl]
        if fmt == "bullet":
            return "• "
        for k in range(ilvl + 1):
            f = levels.get(k, ("decimal", "", 1))[0]
            text = text.replace(f"%{k + 1}", _format_number(max(counters[k], 1), f))
        return text + " " if text else ""


def docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
        numbering = z.read("word/numbering.xml") if "word/numbering.xml" in z.namelist() else None
    lines: list[str] = []
    _blocks(root.find(W + "body"), lines, _Numbering(numbering))
    return "\n".join(lines)


def doc_to_docx(path: Path, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (path.stem + ".docx")
    if not target.exists():
        subprocess.run(["soffice", "--headless", "--convert-to", "docx", "--outdir", str(out_dir), str(path)],
                       check=True, capture_output=True, timeout=300)
    return target


def pdf_text(path: Path) -> str:
    return subprocess.run(["pdftotext", "-enc", "UTF-8", str(path), "-"], check=True,
                          capture_output=True, timeout=300).stdout.decode("utf-8", "replace")


def file_text(path: Path, docx_dir: Path | None = None) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = pdf_text(path)
    elif suffix == ".docx":
        text = docx_text(path)
    elif suffix == ".doc":
        text = docx_text(doc_to_docx(path, docx_dir or Path(tempfile.mkdtemp())))
    else:
        raise ValueError(f"unsupported file: {path}")
    return normalize(text)


def normalize(text: str) -> str:
    text = text.replace("﻿", "").replace(" ", " ").replace("\r", "\n").replace("\f", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"
