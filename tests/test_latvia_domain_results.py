import json

import pytest

from bench.latvia.domain_results import POLICIES, full_domain_results
from bench.latvia.retry_merges import affected


def test_frozen_domain_report_checks_ids_and_outcomes(tmp_path):
    (tmp_path / "inputs.json").write_text(json.dumps({"problems": {"a": "x", "b": "y"}}))
    for policy in POLICIES:
        config = "full-" + policy
        rows = [
            {"config": config, "name": "a", "solved": True, "proof": "proof", "failure_reason": None, "aux": []},
            {"config": config, "name": "b", "solved": False, "proof": None, "failure_reason": "deduction engine failed: TypeError", "aux": []},
        ]
        (tmp_path / (config + ".jsonl")).write_text("".join(json.dumps(r) + "\n" for r in rows))
    result = full_domain_results(tmp_path)
    assert result["proved_by_all"] == result["proved_by_any"] == 1
    assert result["policies"]["deduction"]["errors"] == 1
    path = tmp_path / "full-deduction.jsonl"
    path.write_text(path.read_text().splitlines()[0] + "\n")
    with pytest.raises(ValueError, match="input IDs"):
        full_domain_results(tmp_path)


def test_retry_selects_affected_errors_and_old_proofs():
    assert affected({"failure_reason": "deduction engine failed: TypeError: unhashable type: 'LineMerge'", "proof": None})
    assert affected({"failure_reason": None, "proof": "A B C D =(Circle merge)> A C D E"})
    assert not affected({"failure_reason": "time limit (60s)", "proof": None})
    assert not affected({"failure_reason": None, "proof": "ordinary deduction"})


def test_completed_package_preserves_source_hashes_and_rejects_unpaired_records(tmp_path):
    import hashlib
    from bench.latvia.finalize import finalize

    def put(path, obj):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")
        return hashlib.sha256(path.read_bytes()).hexdigest()

    old, new, output = (tmp_path / n for n in ("original", "revised", "public"))
    cfg = "full-deduction"
    manifest = put(old / "configs/manifest.json", {"configs": {cfg + ".json": "hash"}})
    inputs = {"configuration_manifest_sha256": manifest, "problems": {"p": "text hash"}, "solver_sources": {"a": "v1"}}
    base_sha = put(old / "inputs.json", inputs)
    put(new / "inputs.json", {**inputs, "solver_sources": {"a": "v2"}})
    put(new / "baseline.json", {"input_sha256": base_sha})
    put(old / "summary.json", {"problems": 1, "configurations": {cfg: {"unproved": 1}}})
    put(new / "complete.json", {"expected": 1, "eligible": 1, "retried": 1, "baseline_records": 1})
    rel = f"records/{cfg}/p.json"
    row = {"name": "p", "config": cfg, "solved": False, "proof": None,
           "failure_reason": "deduction engine failed: TypeError: unhashable type: 'LineMerge'"}
    checksum = put(old / rel, row)
    with pytest.raises(ValueError, match="missing retry"):
        finalize(old, new, output)
    fixed = {**row, "solved": True, "failure_reason": None, "proof": "proof", "baseline_record_sha256": checksum}
    put(new / rel, fixed)
    result = finalize(old, new, output)
    assert finalize(old, new, output) == result
    assert result["configurations"][cfg] == {"baseline": {"errors": 1}, "retries": {"proved": 1}}
    encoded = json.dumps(json.loads((output / (cfg + ".jsonl")).read_text()), indent=2, ensure_ascii=False) + "\n"
    assert hashlib.sha256(encoded.encode()).hexdigest() == checksum
    put(new / rel, {**fixed, "baseline_record_sha256": "different"})
    with pytest.raises(ValueError, match="does not match"):
        finalize(old, new, output)


def test_only_the_full_study_renders_the_final_table():
    from bench.latvia.domain_results import complete_coverage

    configs = {domain + ar + "-" + policy: {"baseline": {"proved": 1}, "retries": {}}
               for domain in ("full", "circles", "no_similarity") for ar in ("", "_no_ar") for policy in POLICIES}
    study = {"configurations": configs, "runs": 18, "problems": 1, "retried": 0, "proved_by_any": 1}
    html, paragraph = complete_coverage(study, 1)
    assert html.count('<tr><th scope="row">') == 18 and "Without similarity" in html
    assert "18 mēģinājumi" in paragraph
    with pytest.raises(ValueError, match="Incomplete"):
        complete_coverage({**study, "runs": 17}, 1)


@pytest.mark.parametrize("reason", ["time limit (60s)", "load limit (120s)", "memory limit (2048 MB)", "CPU limit (60s)"])
def test_solver_limits_are_resource_outcomes(reason):
    from bench.latvia.finalize import category

    assert category({"solved": False, "failure_reason": reason}) == "resource_limit"


def test_policy_comparison_counts_by_problem_and_rejects_duplicate_or_missing_rows(tmp_path):
    from bench.latvia.policy_comparison import DOMAINS, compare, record_path

    (tmp_path / "inputs.json").write_text(json.dumps({"problems": {"p": "a", "q": "b"}}))
    for domain in DOMAINS:
        for policy in POLICIES:
            cfg = domain + "-" + policy
            winning = "p" if policy == "deduction" else "q"
            rows = []
            for name in ("p", "q"):
                solved = name == winning and domain == "full"
                reason = "time limit (60s)" if policy == "deduction" else "not solved within depth 1"
                rows.append(dict(config=cfg, name=name, solved=solved, proof="A = B" if solved else None,
                                 failure_reason=None if solved else reason, aux=[], wall_time=0.5, peak_memory_mb=10))
            path = record_path(tmp_path, domain, policy)
            path.parent.mkdir(exist_ok=True)
            path.write_text("".join(json.dumps(row) + "\n" for row in rows))

    report = compare(tmp_path)
    assert report["runs"] == 12
    assert report["domains"]["full"]["common_wins"] == []
    assert report["domains"]["full"]["any_wins"] == ["p", "q"]
    assert report["domains"]["full_no_ar"]["policies"]["combined"]["outcomes"]["depth_limit"] == 2
    path = record_path(tmp_path, "full_no_ar", "combined")
    row = path.read_text().splitlines()[0] + "\n"
    path.write_text(row * 2)
    with pytest.raises(ValueError, match="Duplicate"):
        compare(tmp_path)
    path.write_text(row)
    with pytest.raises(ValueError, match="Problem IDs"):
        compare(tmp_path)


def test_rule_removal_preserves_alternate_proofs_and_resource_outcomes():
    from bench.latvia.restricted_deduction import compare
    from bench.latvia.scan_plan import ROOT

    results = compare(ROOT)
    assert (results["full_rules"], results["reduced_rules"], results["cases"]) == (70, 59, 65)
    assert (results["full_wins"], results["retained"], results["identical"]) == (20, 15, 12)
    hexagon = results["proof_cases"]["latvia/open/2021-22_47/grade09/p3"]
    assert hexagon["removed_rules"] == ["r34", "r52"] and hexagon["reduced"] == "proved"
    assert (hexagon["full_steps"], hexagon["reduced_steps"]) == (7, 5)
    budget = results["proof_cases"]["latvia/open/2001-02_29/grade10/p4"]
    assert budget["removed_rules"] == [] and budget["reduced"] == "timeouts"
    assert sum(r["cases"] for r in results["outcomes"]) == 65
