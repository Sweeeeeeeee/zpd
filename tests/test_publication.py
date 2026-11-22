import json

import pytest

from bench.publish import construction, score


def test_strict_match_preserves_point_and_argument_roles():
    gold = "x : coll a b x, perp x a b c"
    assert construction(gold) == construction("x : perp x a b c, coll a b x")
    assert construction(gold) != construction("x : coll a b x, perp x b a c")
    assert construction(gold) != construction("j : coll a b x, perp x a b c")


def test_empty_reference_stays_in_denominator():
    rows = [{"gold": "x :", "beams": ["x :"], "exact": [True], "seconds": 0.1}]
    assert score(rows) == {"n": 1, "top1": 0, "top4": 0, "relaxed": 1, "empty": 1, "seconds": 0.1}


def test_case_table_uses_official_grade_for_the_frozen_altitude_problem():
    from bench.latvia.case_table import render_cases
    from bench.publish import ROOT

    fresh = json.loads((ROOT / "results/latvia-audit/fresh-drawings.json").read_text())
    passed = {row["name"]: row["all_goals_hold"] for row in fresh["records"]}
    table = render_cases(ROOT, passed)
    circles = next(line for line in table.splitlines() if "/national/1998-99_49/grade12/p2.md" in line)
    assert circles.endswith("<td>34</td></tr>")
    assert table.count('<tr data-outcome=') == 65
    assert table.count('<tr data-outcome="proved">') == 20
    assert "/2008-09_59/grade09/p4.md" in table
    assert "/2008-09_59/grade10/p4.md" not in table


def test_fresh_drawing_audit_rejects_repeated_seeds():
    from bench.latvia.fresh_drawings import frozen_hashes, summarize
    from bench.publish import ROOT

    data = json.loads((ROOT / "results/latvia-audit/fresh-drawings.json").read_text())
    hashes = frozen_hashes()
    totals = summarize(data, hashes)
    assert totals["attempts"] == 4160
    assert totals["all_goals_hold"] + totals["unbuilt"] == 4160
    row = next(row for row in data["records"] if row["unbuilt"])
    row["degenerate"].append(row["unbuilt"][0])
    row["all_goals_hold"] -= 1
    with pytest.raises(ValueError, match="Inconsistent seed outcomes"):
        summarize(data, hashes)


def test_student_score_columns_are_joined_to_the_correct_problem_and_solver():
    from bench.latvia.student_scores import compare
    from bench.publish import ROOT

    matches = compare(ROOT)
    assert [(r["mean"], r["rank_by_mean"], r["revised"]) for r in matches] == [
        (3.92, 2, "proved"), (5.69, 1, "timeouts"),
    ]


def test_proof_reader_checks_exact_statements_shared_dependencies_and_audit():
    from bench.latvia.proof_catalog import parse_proof

    text = """# Problem setup:
[C0] : A = B
# Goals
B = C : Proved [1]
B = D : Proved [2]
# Proof:
000. | A = B [C0] =(r01 Rule)> A = C [0]
001. | A = C [0] =(AR Deduction)> B = C [1]
002. | A = C [0] =(r02 Rule)> B = D [2]
# Appendix:
"""
    row = dict(name="example", proof=text, rules_in_proof={"r01": 1, "AR:ratio": 1, "r02": 1})
    audit = [dict(step=1, kind="Ratio", goal="B = C", outcome="needs_context")]
    result = parse_proof(row, audit)
    assert result["chain"] == 2 and result["used_steps"] == 3
    assert result["goals"] == ["1", "2"]
    for before, after, message in (("A = C [0] =(AR", "A = B [0] =(AR", "Incorrect cited fact"),
                                   ("A = B [C0]", "A = B [2]", "Incorrect cited fact"),
                                   ("B = D : Proved [2]", "B = C : Proved [2]", "Goal differs")):
        with pytest.raises(ValueError, match=message):
            parse_proof({**row, "proof": text.replace(before, after)}, audit)
    with pytest.raises(ValueError, match="AR audit"):
        parse_proof(row, [])


def test_imo_pairs_deduplicate_encodings_and_check_both_official_score_sources(tmp_path):
    from bench.imo_student_scores import compare
    from bench.publish import ROOT

    source = ROOT / "results/local-cpu/imo"
    for name in ("problems.txt", "ddar_only.jsonl", "official-paired-scores.json"):
        (tmp_path / name).write_bytes((source / name).read_bytes())
    result = compare(tmp_path)
    assert (result["formalizations"], result["official_items"], result["matched_encodings"], result["matched_items"]) == (29, 27, 13, 12)
    assert result["comparisons"] == {"proved_higher": 3, "same_solver_outcome": 3}
    madrid = next(e for e in result["editions"] if e["year"] == 2008)
    assert madrid["items"][0]["ids"] == ["2008_p1a", "2008_p1b"]
    path = tmp_path / "official-paired-scores.json"
    archive = json.loads(path.read_text())
    archive["editions"][0]["score_counts_0_to_7"][0][1] += 1
    path.write_text(json.dumps(archive))
    with pytest.raises(ValueError, match="Individual and team"):
        compare(tmp_path)
