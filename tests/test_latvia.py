"""Latvian olympiad import (task 4.1): text extraction, problem splitting, geometry tags, catalogue."""

import zipfile

from bench.latvia.catalog import classify, group
from bench.latvia.extract import docx_text
from bench.latvia.split import clean_text, merge, split, split_tst
from bench.latvia.topics import geometry_kind

URL = "https://www.nms.lu.lv/x"


def _keys(problems):
    return [(p.grade, p.day, p.number) for p in problems]


def test_grade_headers_and_numbering():
    text = """Latvijas 55. matemātikas olimpiādes 3. kārtas uzdevumi
9. klase
1. Trijstūrī ABC novilkta bisektrise AD. Pierādīt, ka AB > BD.
2. Dots, ka x un y ir reāli skaitļi.
a) atrast x,
1. att.
3. Cik ir tādu skaitļu?
10. klase
1. Pierādīt, ka 7 dalās ar 7.
2005. gada 10. marts
"""
    ps = split(text, olympiad=55)
    assert _keys(ps) == [("9", None, 1), ("9", None, 2), ("9", None, 3), ("10", None, 1)]
    assert "a) atrast x," in ps[1].text and "1. att." in ps[1].text
    assert ps[3].text == "Pierādīt, ka 7 dalās ar 7."     # footer date dropped


def test_running_olympiad_numbers_and_extra_round():
    text = """8. klase
26.1. Pirmais uzdevums ir garš teksts par skaitļiem.
26.2. Otrais uzdevums.
9. klase
26.3.Trijstūrī ABC dots, ka ∠A = 2∠B. Aprēķināt BC.
PAPILDSACENSĪBAS PAR VIETU REPUBLIKAS IZLASĒ
8. un 9. klases
26.4. Punkti A un B atrodas uz vienas upes un plosts peld.
"""
    ps = split(text, olympiad=26)
    assert _keys(ps) == [("8", None, 1), ("8", None, 2), ("9", None, 1), ("8-9", 9, 1)]
    assert ps[2].label == "26.3" and ps[2].text.startswith("Trijstūrī")


def test_grade_prefixed_numbers_cut_solutions_in_combined_files():
    text = """9.-12. klase
9.1.
Atrisināt vienādojumu x + 1 = 2.
Atrisinājums. Atņemam 1.
1. gadījums. Ja x > 0.
2. Otrais solis ar garu tekstu par to.
9.2. Dots trijstūris ABC ar mediānu AM.
Atbilde: nav.
10.1. Pierādīt nevienādību a + b ≥ 2√(ab).
"""
    ps = split(text, combined=True)
    assert _keys(ps) == [("9", None, 1), ("9", None, 2), ("10", None, 1)]
    assert ps[0].text == "Atrisināt vienādojumu x + 1 = 2."
    assert ps[1].text == "Dots trijstūris ABC ar mediānu AM."


def test_number_without_dot_and_duplicate_pages():
    text = """5. klase
1 Trīs meitenēm kopā bija 120 konfektes un vēl citas lietas.
2 Jānītis vēlas sadalīt figūru četrās vienādās daļās šodien.
5. klase
1 Trīs meitenēm kopā bija 120 konfektes un vēl citas lietas.
"""
    ps = split(text)
    assert _keys(ps) == [("5", None, 1), ("5", None, 2)]
    assert ps[0].text.count("konfektes") == 1


def test_selection_test_days_and_restart():
    text = """Atlases sacensības uz IMO 2022, 1.diena
1.uzdevums Taisnleņķa trijstūrī ABC, kurā ∠C = 90°, novilkta bisektrise.
Atrisinājums Pieņemsim, ka ∠CAB = 2α.
1. Tas ir solis.
2.uzdevums Zaļajā jūrā ir 20 ostas.
Atlases sacensības uz IMO 2022, 2.diena
3.uzdevums Atrast visas funkcijas f.
"""
    ps = split_tst(text, combined=True)
    assert [(p.day, p.number) for p in ps] == [(1, 1), (1, 2), (2, 3)]
    assert ps[0].text.endswith("novilkta bisektrise.")


def test_merge_takes_the_more_readable_statement():
    doc = split("9. klase\n1. Atrisināt [formula] reālos skaitļos.\n2. Otrais.\n")
    pdf = split("9. klase\n1. Atrisināt x^2 + 1 = 2x reālos skaitļos.\n2. Otrais.\n")
    (p1, p2) = merge([doc, pdf])
    assert "x^2" in p1.text and p2.text == "Otrais."


def test_clean_text_fixes_fonts():
    assert clean_text("rūėīši viĦiem skaitĜi ăeometrija") == "rūķīši viņiem skaitļi ģeometrija"
    assert clean_text("ABC = 60") == "∠ABC = 60°"
    assert clean_text("𝐴𝐵𝐶") == "ABC"


def test_geometry_kind():
    assert geometry_kind("Trijstūrī ABC novilkta bisektrise AD. Pierādīt, ka ∠BAD = 30°.")[0] == "plane"
    assert geometry_kind("Kubam ABCDA1B1C1D1 novilkta šķautne AA1 un plakne.")[0] == "solid"
    assert geometry_kind("Atrast visus naturālos skaitļus n, kuriem n^2 + 1 dalās ar 5.")[0] == ""
    assert geometry_kind("Rūtiņu tabulā 8 × 8 spēlētāji pēc kārtas krāso rūtiņas.")[0] == ""


def test_docx_symbol_font_numbering_and_math(tmp_path):
    w = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    m = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'
    body = (
        '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        '<w:r><w:sym w:font="Symbol" w:char="f0d0"/></w:r><w:r><w:t>A = 60</w:t></w:r>'
        '<w:r><w:sym w:font="Symbol" w:char="f0b0"/></w:r></w:p>'
        '<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>'
        '<w:r><w:t xml:space="preserve">Apēda </w:t></w:r>'
        '<m:oMath><m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>3</m:t></m:r></m:den></m:f></m:oMath>'
        '</w:p>'
    )
    doc = f'<w:document {w} {m}><w:body>{body}</w:body></w:document>'
    numbering = (f'<w:numbering {w}><w:abstractNum w:abstractNumId="0"><w:lvl w:ilvl="0"><w:start w:val="1"/>'
                 '<w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/></w:lvl></w:abstractNum>'
                 '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num></w:numbering>')
    path = tmp_path / "t.docx"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("word/document.xml", doc)
        z.writestr("word/numbering.xml", numbering)
    assert docx_text(path).split("\n") == ["1. ∠A = 60°", "2. Apēda 1/3"]


def test_catalog_classifies_archive_files():
    s = classify("VOL/2000-2010/55repol_uzd.doc", URL, "2004/05")
    assert (s.competition, s.number, s.season, s.role, s.part) == ("national", 55, "2004/05", "problems", "")
    assert classify("VOL/2010-2020/vol_65_2diena_uzd.pdf", URL).part == "day2"
    assert classify("NOL/ro_30_atr.doc", URL).role == "solutions"
    assert classify("AMO/2020-2030/2022_AMO_uzd_atr.docx", URL).role == "combined"
    assert classify("AMO/2010-2020/AMO_42_invarianti_teorija_AMO.pdf", URL) is None
    assert classify("INTL/2019_lav_IMO.pdf", URL) is None            # the IMO itself is not Latvian
    tst = classify("INTL/BW_2024_atlase_1_diena.pdf", URL)
    assert (tst.competition, tst.year, tst.part) == ("tst", 2024, "bw/day1")
    insts = group([s, classify("VOL/2000-2010/55repol_atr.pdf", URL, "2004/05")])
    assert len(insts) == 1 and insts[0].key == "2004-05_55"
