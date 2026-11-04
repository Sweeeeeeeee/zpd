"""Split the text of one olympiad document into individual problems.

The archive uses several layouts over 50 years:

    9. klase                      grade header, then "1." "2." ... per grade
    26.3. Trijstūrī ...           olympiad.problem numbering, grades by header
    7.1. Vai rindā ...            grade.problem numbering (AMO, later years)
    3. uzdevums / 3.uzdevums      selection tests

Problem numbers must follow each other (1, 2, 3, ... within a grade, or a
running number for olympiad.problem), so list items, figure captions and dates
that start with a number are not taken for new problems. In files that also
contain solutions, a statement ends where its solution starts.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

from bench.latvia.extract import _symbol

GRADE_RE = re.compile(r"^(?:uzdevumi\s+)?(\d{1,2})\.\s*(?:(?:–|-|un)\s*(\d{1,2})\.\s*)?klas(?:e|ei|es)\b(.{0,60})$", re.I)
EXTRA_RE = re.compile(r"^papildsacensības\b", re.I)
DAY_RE = re.compile(r"^(?:(\d)\.\s*(?:diena|kārta)\b|(pirmā|otrā|trešā)\s+diena)", re.I)
TWO_LEVEL_RE = re.compile(r"^(\d{1,2})\.\s?(\d{1,3})(?:\.\s*(.*)|\s+(\S.*))$")
ONE_LEVEL_RE = re.compile(r"^(\d{1,2})\s?\.(?!\d)\s*(.*)$")
ALONE_RE = re.compile(r"^(\d{1,2})\.$")
NODOT_RE = re.compile(r"^(\d{1,2}) ([A-ZĀČĒĢĪĶĻŅŠŪŽ].{20,})$")   # "2 Nogriežņa AB garums ..." (dot missing)
UZDEVUMS_RE = re.compile(r"^(\d{1,2})\.\s?uzdevums\.?\s*[:.]?\s*(.*)$", re.I)
SOLUTION_RE = re.compile(
    r"^(atrisinājums|atrisinājumi|risinājums|atbilde|atbildes|solution|answer|komentārs|piezīme par|"
    r"vērtēšanas|1\. atrisinājums|pirmais atrisinājums|uzdevuma autor|autors:)\b", re.I)
FOOTER_RE = re.compile(
    r"^(\d{1,3}|www\.\S+|nms\.lu\.lv|.*\d{4}\.\s*gada\s+\d{1,2}\.\s*\w+\.?|\d{2}\.\d{2}\.\d{4}\.?|"
    r"lu a\. liepas neklātienes matemātikas skola.*|.*matemātikas olimpiādes?\s+\d\.\s*(posm|kārt).*|"
    r"latvijas \d+\. (atklātās )?matemātikas olimpiādes.*|tīrrakstā ir jāraksta.*|katru uzdevumu vērtē.*|"
    r"tiek vērtēti .*|risināšanas laiks.*|jautājumus drīkst.*|atļauts izmantot.*|"
    r"piedaloties olimpiādē.*|atklātā matemātikas olimpiāde|materiāls ņemts no.*)$", re.I)
_DAYWORD = {"pirmā": 1, "otrā": 2, "trešā": 3}


@dataclass
class Problem:
    grade: str | None    # "9", or "8-9" for a problem set shared by two grades
    day: int | None      # None, 2, 3 (separate rounds); "extra" rounds use 9
    number: int          # number within its grade/day (1, 2, ...)
    label: str           # number as printed, e.g. "26.3" or "7.1" or "3"
    text: str


def clean_text(text: str) -> str:
    """Unicode clean-up: math italic letters to ASCII, ligatures and odd spaces away."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("ı̄", "ī").replace("ı", "i").replace("ﬁ", "fi").replace("ﬂ", "fl")
    # Symbol-font characters that PDFs keep in the private use area (U+F020-U+F0FF); the
    # U+F8E5-U+F8FF pieces of tall brackets carry no text.
    text = re.sub("[-]", lambda m: _symbol(ord(m.group(0))), text)
    text = re.sub("[-]", "", text)
    # Some 2008-2010 PDFs use a Baltic font with a broken code page: ņ ļ ķ ģ come out as Ħ Ĝ ė ă.
    return text.translate(_BROKEN_BALTIC)


_BROKEN_BALTIC = str.maketrans({"Ħ": "ņ", "Ĝ": "ļ", "ė": "ķ", "ă": "ģ"})


def _cut_solution(lines: list[str]) -> list[str]:
    for i, line in enumerate(lines):
        if i > 0 and SOLUTION_RE.match(line.strip()):
            return lines[:i]
    return lines


def _strip_footer(lines: list[str]) -> list[str]:
    while lines and (not lines[-1].strip() or FOOTER_RE.match(lines[-1].strip())):
        lines = lines[:-1]
    return lines


def split(text: str, olympiad: int | None = None, combined: bool = False) -> list[Problem]:
    lines = []
    for l in clean_text(text).split("\n"):
        # a figure anchored at the start of a paragraph: "[formula]2. Pieņemsim ..." -> two lines
        m = re.match(r"^((?:\[(?:formula|attēls)\]\s*)+)(\d{1,2}\..*)$", l.strip())
        lines.extend([m.group(1).strip(), m.group(2)] if m else [l.strip()])
    problems: list[tuple[str | None, int | None, int, str, list[str]]] = []
    grade: str | None = None
    day: int | None = None
    last_in_section = 0
    current: list[str] | None = None
    seen: set[tuple] = set()
    in_solution = False
    # Running numbering "P.k." where P is the olympiad number (or, in old preparatory
    # olympiads, the year): the prefix that occurs often and counts past 12.
    prefixes = Counter()
    top = {}
    for l in lines:
        if (m := TWO_LEVEL_RE.match(l)):
            a, b = int(m.group(1)), int(m.group(2))
            prefixes[a] += 1
            top[a] = max(top.get(a, 0), b)
    running = [a for a, n in prefixes.items() if n >= 8 and top[a] > 12]
    if running:
        olympiad = max(running, key=lambda a: prefixes[a])
    expected_global = None
    # Documents numbered "grade.problem" (7.1., 7.2., ...) never use bare "1." for problems.
    two_level_lines = sum(1 for l in lines if (m := TWO_LEVEL_RE.match(l)) and 4 <= int(m.group(1)) <= 12
                          and int(m.group(1)) != olympiad and int(m.group(2)) <= 8)
    allow_one_level = two_level_lines < 5
    # Some files drop the dot after every problem number; then "5. ..." is wrapped text, not a problem.
    nodot_mode = sum(1 for l in lines if NODOT_RE.match(l)) > 2 * sum(1 for l in lines if ONE_LEVEL_RE.match(l))

    def start(g, d, num, label, first):
        nonlocal current, in_solution
        key = (g, d, num)
        if key in seen:          # the same grade printed twice (duplicated pages); keep the first
            current = None
            return
        seen.add(key)
        current = [first] if first else []
        problems.append((g, d, num, label, current))
        in_solution = False

    for i, line in enumerate(lines):
        if not line:
            if current is not None:
                current.append("")
            continue
        if EXTRA_RE.match(line):
            day, last_in_section, current = 9, 0, None
            continue
        m = GRADE_RE.match(line)
        if m and len(line) < 70 and not re.search(r"[?]", line):
            lo = int(m.group(1))
            g = f"{lo}-{int(m.group(2))}" if m.group(2) else str(lo)
            if 4 <= lo <= 12:
                # a repeated header (pages printed twice) restarts the count; the repeated
                # problems are then dropped as already seen
                grade, last_in_section, current = g, 0, None
                continue
        m = DAY_RE.match(line)
        if m and len(line) < 40:
            d = int(m.group(1)) if m.group(1) else _DAYWORD[m.group(2).lower()]
            if d != day:
                day, last_in_section, current = d, 0, None
                if grade is None:
                    pass
            continue
        m = UZDEVUMS_RE.match(line)
        if m:
            num = int(m.group(1))
            if num == last_in_section + 1 or (num == 1):
                if num == 1 and last_in_section > 0:
                    day = (day or 1) + 1
                last_in_section = num
                start(grade, day, num, str(num), m.group(2))
                continue
        m = TWO_LEVEL_RE.match(line)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            rest = m.group(3) if m.group(3) is not None else m.group(4)
            if olympiad is not None and a == olympiad and (expected_global is not None or rest):
                # running number; tolerate one skipped or one repeated number (typos in the source)
                looks_new = len(rest) > 25 and rest[0].isupper()
                if expected_global is None and rest:
                    expected_global = b  # old regional books continue the numbering of earlier rounds
                if b == expected_global or (looks_new and b in (expected_global + 1, expected_global - 1)):
                    expected_global = max(b, expected_global) + 1
                    last_in_section += 1
                    start(grade, day, last_in_section, f"{m.group(1)}.{m.group(2)}", rest)
                    continue
            if 4 <= a <= 12 and (olympiad is None or a != olympiad) and 1 <= b <= 12:
                if str(a) != grade and b == 1:
                    grade, last_in_section = str(a), 0
                if str(a) == grade and b == last_in_section + 1:
                    last_in_section = b
                    start(grade, day, b, f"{m.group(1)}.{m.group(2)}", rest)
                    continue
        if combined and SOLUTION_RE.match(line):
            in_solution = True
        one_level = allow_one_level and not in_solution
        m = ALONE_RE.match(line)
        following = next((l for l in lines[i + 1:] if l), "")
        if one_level and m and int(m.group(1)) == last_in_section + 1 and not re.match(
                r"^(zīm|att|attēls)\b", following, re.I):
            last_in_section = int(m.group(1))
            start(grade, day, last_in_section, m.group(1), "")
            continue
        m = NODOT_RE.match(line)
        if one_level and m and int(m.group(1)) == last_in_section + 1 and (nodot_mode or len(line) > 30):
            last_in_section = int(m.group(1))
            start(grade, day, last_in_section, m.group(1), m.group(2))
            continue
        m = ONE_LEVEL_RE.match(line)
        if one_level and not nodot_mode and m and m.group(2) and not re.match(
                r"^(?:att\.|zīm\.|(?:attēls|klase|kārta|diena|posm|atrisinājum|risinājum|gadījum|veids|solution|case)\b)",
                m.group(2), re.I):
            num = int(m.group(1))
            if num == last_in_section + 1 and num <= 12:
                last_in_section = num
                start(grade, day, num, str(num), m.group(2))
                continue
        if current is not None:
            current.append(line)

    out = []
    for g, d, num, label, body in problems:
        body = _strip_footer(_cut_solution(body) if combined else body)
        body = [l for l in body if not FOOTER_RE.match(l) or len(l) > 80]
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(body)).strip()
        if text:
            out.append(Problem(g, d, num, label, text))
    return out


def problem_score(text: str) -> float:
    """How readable one statement is: its length, minus unreadable formulas and garbage."""
    odd = sum(1 for c in text if unicodedata.category(c) in ("Co", "Cn") or c == "\ufffd")
    short_lines = sum(1 for l in text.split("\n") if 0 < len(l.strip()) <= 3)
    long_lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 25]
    repeated = len(long_lines) - len(set(long_lines))   # a page printed twice runs into the next copy
    return len(text) - 20 * text.count("[formula]") - 10 * odd - 8 * short_lines - 200 * repeated


def merge(readings: list[list[Problem]]) -> list[Problem]:
    """Several readings of one document (e.g. .doc and .pdf): keep the best text of each problem.

    The first reading fixes which problems exist; others only replace a
    statement when they hold the same problem in a more readable form.
    """
    base = readings[0]
    for other in readings[1:]:
        by_key = {(p.grade, p.day, p.number): p for p in other}
        for i, p in enumerate(base):
            q = by_key.get((p.grade, p.day, p.number))
            if q is not None and problem_score(q.text) > problem_score(p.text):
                base[i] = Problem(p.grade, p.day, p.number, p.label, q.text)
    return base


def quality(problems: list[Problem]) -> float:
    """Higher is better: many problems, few unreadable formulas or garbled characters."""
    if not problems:
        return 0.0
    text = "\n".join(p.text for p in problems)
    formulas = text.count("[formula]")
    letters = sum(c.isalpha() for c in text) or 1
    latvian = sum(c in "āēīūčģķļņšžĀĒĪŪČĢĶĻŅŠŽ" for c in text)
    odd = sum(1 for c in text if unicodedata.category(c) in ("Co", "Cn") or c == "�")
    garble = 1.0 if latvian / letters < 0.01 else 0.0
    return len(problems) * (1 - garble) - 0.5 * formulas - 0.2 * odd


TST_START_RE = re.compile(r"^(?:(\d{1,2})\.\s?(?i:uzdevums)\.?|P(\d{1,2})(?=\s+[A-ZĀČĒĢĪĶĻŅŠŪŽ])|(\d{1,2})\.)(?:\s+(.*))?$")
TST_DAY_RE = re.compile(r"(?:^|,\s*)(\d)\.\s?diena\b", re.I)


def split_tst(text: str, combined: bool = False) -> list[Problem]:
    """Selection tests: problems numbered across days (1-8, sometimes restarting at 1 on day 3),
    written "3.uzdevums", "P3" or "3.", with day headers like "2. diena" or "..., 2.diena"."""
    lines = [l.strip() for l in clean_text(text).split("\n")]
    problems: list[Problem] = []
    body: list[str] | None = None
    day, last, in_solution, fresh_day = None, None, False, False
    for line in lines:
        m = TST_DAY_RE.search(line)
        if m and len(line) < 70 and not re.match(r"^\d{1,2}\.\s?uzdevums", line, re.I):
            day, body, fresh_day = int(m.group(1)), None, True
            continue
        if combined and SOLUTION_RE.match(re.sub(r"^P\d+\s+", "", line)):
            in_solution, body = True, None
            continue
        m = TST_START_RE.match(line)
        if m:
            num = int(m.group(1) or m.group(2) or m.group(3))
            bare = m.group(3) is not None
            rest = m.group(4) or ""
            ok = last is None or num == last + 1 or (num == 1 and last >= 3)
            if bare and (in_solution or not rest or not rest[:1].isupper()):
                ok = False     # "3." inside a solution or a wrapped line
            if ok:
                if num == 1 and last and not fresh_day:
                    day = (day or 1) + 1       # numbering restarts on an unlabelled new day
                last, in_solution, fresh_day = num, False, False
                body = [rest] if rest else []
                problems.append(Problem(None, day, num, str(num), ""))
                problems[-1].text = body  # filled below
                continue
        if body is not None and not in_solution:
            body.append(line)
    out = []
    for p in problems:
        lines_ = _strip_footer(p.text)
        lines_ = [l for l in lines_ if not FOOTER_RE.match(l) or len(l) > 80]
        t = re.sub(r"\n{3,}", "\n\n", "\n".join(lines_)).strip()
        if t:
            out.append(Problem(p.grade, p.day, p.number, p.label, t))
    return out
