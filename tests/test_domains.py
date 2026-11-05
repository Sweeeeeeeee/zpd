"""Geometry domains and the easy setting (task 6), and the engine fixes they need."""

import json

import pytest

import bench.store as store
from ddar.rule_config import DDARConfig, coverage_warnings
from ddar.runner import solve_jgex
from pipeline.solve import Budget, config_budget
from pipeline.tools import ROOT

DOMAINS = ["full", "circles", "no_similarity"]
SIMILARITY = {"r07", "r34", "r35", "r52", "r53", "r60", "r61", "r62", "r63", "r68", "r69"}
ORTHO_REFLECTION = "a b c = triangle a b c; h = orthocenter h a b c; d = reflect d h b c ? cyclic a b c d"


def ddar_domain(name):
    return DDARConfig.from_json(ROOT / f"ddar/configs/domains/{name}.json")


def test_domains_are_subsets_of_full_and_come_with_and_without_ar():
    full = set(ddar_domain("full").rule_ids())
    assert coverage_warnings(ddar_domain("full")) == []
    circles = set(ddar_domain("circles").rule_ids())
    assert circles < full and {"r03", "r04", "r15", "r49"} <= circles
    assert not circles & (SIMILARITY | {"r36", "r37", "r64", "r65", "r66", "r67", "r85", "r86"})
    assert set(ddar_domain("no_similarity").rule_ids()) == full - SIMILARITY
    for name in DOMAINS:
        with_ar, without = ddar_domain(name), ddar_domain(f"{name}_no_ar")
        assert with_ar.ar and not without.ar and with_ar.rule_ids() == without.rule_ids()
        assert with_ar.engine == "python"   # yuclid cannot switch rules off


@pytest.mark.parametrize("name", DOMAINS + [d + "_no_ar" for d in DOMAINS])
def test_easy_setting(name):
    path = ROOT / f"pipeline/configs/domains/{name}.json"
    config = json.loads(path.read_text())
    assert config["search"]["max_depth"] == 1
    assert config["tools"]["ddar"]["options"]["config"] == f"ddar/configs/domains/{name}.json"
    assert config_budget(path) == Budget(time_s=60, memory_mb=2048, cpu_s=0)
    assert config_budget(path, time_s=120) == Budget(time_s=120, memory_mb=2048, cpu_s=0)
    assert store.settings_summary(path)["budget"] == {"time_s": 60, "memory_mb": 2048, "cpu_s": 0}


def test_config_without_budget_gets_defaults():
    assert config_budget(ROOT / "pipeline/configs/ddar_only.json") == Budget()


def test_store_uses_the_config_budget(tmp_path, monkeypatch):
    folder = tmp_path / "set"
    folder.mkdir()
    (folder / "p.txt").write_text("a b c = triangle a b c; d = midpoint d a b; e = midpoint e a c ? para d e b c\n")
    config = json.loads((ROOT / "pipeline/configs/ddar_only.json").read_text())
    config["budget"] = {"time_s": 30, "memory_mb": 1500, "cpu_s": 0}
    (tmp_path / "small.json").write_text(json.dumps(config))
    monkeypatch.setattr(store, "RESULTS_ROOT", tmp_path / "results")
    (record,) = store.run(store.load_problems(folder), [tmp_path / "small.json"])
    assert record["resources"]["available"] == {"time_s": 30, "memory_mb": 1500, "cpu_s": 0}
    assert record["solved"]


def test_ar_traceback_is_completed_for_the_proof():
    # Newclid alone: "Could not find premises for AR deduction" while writing the proof
    result = solve_jgex(ORTHO_REFLECTION, ddar_domain("circles"))
    assert result["success"]


def test_congruent_triangle_facts_can_be_matched():
    # Newclid alone: "Unknown predicate: PredicateType.CONTRI_REFLECT" when r78 is matched
    result = solve_jgex(ORTHO_REFLECTION, ddar_domain("full"))
    assert result["success"]
