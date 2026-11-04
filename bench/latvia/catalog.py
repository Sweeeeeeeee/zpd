"""Which archive file belongs to which olympiad.

Every downloaded file is mapped to an *instance*: competition, olympiad
number, school year, and (for the multi-day ones) day. Its role says whether
it holds the problems, the problems with solutions, or only solutions.

Competitions (folder name: Latvian name):
    national  Valsts olimpiāde (Latvijas matemātikas olimpiādes 3. posms / kārta)
    regional  Novada / rajona olimpiāde (2. posms)
    school    Skolas olimpiāde (1. posms; until the 2000s "sagatavošanās olimpiāde")
    open      Atklātā matemātikas olimpiāde (AMO)
    tst       Latvian selection tests for Baltic Way and the IMO

International competitions themselves (IMO, EGMO, Baltic Way) are not
Latvian problems and are skipped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

ARCHIVE_PAGES = [
    "https://www.nms.lu.lv/arhivs-un-materali/uzdevumu-arhivs/olimpiazu-uzdevumu-arhivs/",
    "https://www.nms.lu.lv/arhivs-un-materali/uzdevumu-arhivs/starptautisko-sacensibu-uzdevumu-arhivs/",
]
SITE = "https://www.nms.lu.lv"

COMPETITIONS = {
    "national": "Latvijas matemātikas olimpiāde, 3. posms (valsts olimpiāde)",
    "regional": "Latvijas matemātikas olimpiāde, 2. posms (novada / rajona olimpiāde)",
    "school": "Latvijas matemātikas olimpiāde, 1. posms (skolas / sagatavošanās olimpiāde)",
    "open": "Latvijas atklātā matemātikas olimpiāde (AMO)",
    "tst": "Latvijas izlases atlases sacensības (Baltijas ceļš, IMO)",
}


@dataclass
class Source:
    url: str
    file: str            # path inside the local download folder
    competition: str     # key of COMPETITIONS
    number: int | None   # olympiad number (None for selection tests)
    year: int            # calendar year the contest was (most likely) held
    season: str          # school year, e.g. "2004/05", as listed on the archive page
    part: str = ""       # "" or "day1"/"day2"/"day3" or "bw"/"imo" for tst
    role: str = "problems"   # problems | combined | solutions
    lang: str = "lv"
    note: str = ""


def _season(end_year: int) -> str:
    return f"{end_year - 1}/{end_year % 100:02d}"


# AMO numbers 47-51 moved to autumn; earlier ones were held in spring.
_AMO_LATE = {47: (2022, "2021/22"), 48: (2022, "2022/23"), 49: (2023, "2023/24"),
             50: (2024, "2024/25"), 51: (2025, "2025/26")}

_AMO_FILES = {
    "_2022_AMO_uzdevumi": 47, "2022_AMO_uzd_atr": 47,
    "2022-rudens_AMO_uzdevumi": 48, "AMO_uzd_atr_2022_rudens": 48,
    "AMO2425_uzd": 50, "AMO2425_uzd_eng": 50, "AMO2425_atr": 50,
}

# Selection tests: file stem -> (year, part, role)
_TST_FILES = {
    "BW_2021_atlase_uzd_atr": (2021, "bw", "combined"),
    "BW_TST_2022_solutions": (2022, "bw", "combined"),
    "BW_atlase_2023_uzd_1_diena": (2023, "bw/day1", "problems"),
    "BW_atlase_2023_uzd_2_diena": (2023, "bw/day2", "problems"),
    "BW_atlase_2023_atr": (2023, "bw", "combined"),
    "BW_2024_atlase_1_diena": (2024, "bw/day1", "problems"),
    "BW_2024_atlase_2_diena": (2024, "bw/day2", "problems"),
    "BW_2024_atlase_atrisinajumi": (2024, "bw", "combined"),
    "BW_atlase_2025_pirma_diena__1_": (2025, "bw/day1", "problems"),
    "BW_atlase_2025_otra_diena__1_": (2025, "bw/day2", "problems"),
    "BW_TST_2025_atrisinajumi__4_": (2025, "bw", "combined"),
    "IMO_2022_atlase": (2022, "imo", "combined"),
    "IMO_2023_atlase_atr": (2023, "imo", "combined"),
    "IMO_2024_atlases_uzd_atr": (2024, "imo", "combined"),
    "IMO_TST_2025_solutions__1_": (2025, "imo", "combined"),
}


def _role(stem: str) -> str:
    s = stem.lower()
    if "vert" in s or "kriter" in s and "uzd" not in s:
        return "criteria"
    has_problems = bool(re.search(r"uzd|_u$", s))
    has_solutions = bool(re.search(r"atr|atris", s))
    if has_problems and has_solutions:
        return "combined"
    if has_solutions:
        return "solutions"
    return "problems"


def classify(rel: str, url: str, season: str | None = None) -> Source | None:
    """Map a downloaded file (path relative to the download folder) to its Source, or None to skip it.

    `season` is the school year the archive page lists the file under ("1987/88");
    without it, the season is worked out from the olympiad number.
    """
    family, *_, name = rel.split("/")
    stem = name.rsplit(".", 1)[0]
    s = stem.lower()
    if "teorija" in s or "teor_" in s or "invarianti" in s or "magiska" in s or "vida_vidg" in s:
        return None  # theory handouts, not problems
    role = _role(stem)
    if role == "criteria":
        return None
    lang = "en" if re.search(r"eng", s) else "lv"

    if family == "INTL":
        if stem not in _TST_FILES:
            return None  # IMO / EGMO / Baltic Way themselves
        year, part, role = _TST_FILES[stem]
        return Source(url, rel, "tst", None, year, _season(year + 1) if part.startswith("bw") else _season(year),
                      part, role, lang)

    if family == "AMO":
        if stem in _AMO_FILES:
            n = _AMO_FILES[stem]
        else:
            m = re.search(r"amo_?(\d+)|(\d+)ao", s)
            n = int(m.group(1) or m.group(2))
        year, guess = _AMO_LATE.get(n, (1973 + n, _season(1973 + n)))
        season = season or guess
        part = ""
        if "5-8kl" in s:
            part = "grades5-8"
        elif "9-12kl" in s:
            part = "grades9-12"
        return Source(url, rel, "open", n, year, season, part, role, lang)

    comp = {"VOL": "national", "NOL": "regional", "SOL": "school"}[family]
    if stem.startswith("sag_olimp_2014_15"):
        n = 65
    elif stem.startswith("so1516"):
        n = 66
    else:
        m = re.search(r"(\d{2})", s)
        n = int(m.group(1))
    # The national final has, since the 65th olympiad, a second day common to grades 9-12.
    part = "day2" if re.search(r"_2_?diena", s) else ""
    season = season or _season(1950 + n)
    year = int(season[:4]) + (0 if comp == "school" else 1)
    return Source(url, rel, comp, n, year, season, part, role, lang)


@dataclass
class Instance:
    competition: str
    number: int | None
    year: int
    season: str
    part: str
    sources: list[Source] = field(default_factory=list)

    @property
    def key(self) -> str:
        if self.competition == "tst":
            kind, _, day = self.part.partition("/")
            return f"{self.year}_{kind}" + (f"/{day}" if day else "")
        base = f"{self.season.replace('/', '-')}_{self.number:02d}"
        return base + (f"/{self.part}" if self.part else "")


def group(sources: list[Source]) -> list[Instance]:
    """Group sources into instances. Combined files for a split contest (tst day files) are shared."""
    out: dict[tuple, Instance] = {}
    for s in sources:
        k = (s.competition, s.number, s.year if s.competition == "tst" else None, s.part)
        if k not in out:
            out[k] = Instance(s.competition, s.number, s.year, s.season, s.part)
        out[k].sources.append(s)
    return sorted(out.values(), key=lambda i: (i.competition, i.year, i.number or 0, i.part))
