"""Config loading: DDAR rule configs (step 2) and pipeline tool configs (step 6)."""

import json

import pytest

from ddar.rule_config import DDARConfig, RuleCoverageWarning, coverage_warnings, load_config
from pipeline.search import load_tools
from pipeline.tools import ROOT, AuxConstruction, DDARTool, HeuristicsTool, Tool


def write(tmp_path, data, name="cfg.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return path


def test_default_config_has_58_rules_and_no_warnings():
    config = load_config(ROOT / "ddar/configs/default.json")
    assert len(config.rules()) == 58
    assert config.ar is True
    assert coverage_warnings(config) == []


def test_disabled_rules_are_removed_at_load_time(tmp_path):
    config = DDARConfig.from_json(write(tmp_path, {"enabled_rules": "default", "disabled_rules": ["r43"]}))
    ids = [r.id for r in config.rules()]
    assert "r43" not in ids and len(ids) == 57


def test_explicit_rule_list(tmp_path):
    config = DDARConfig.from_json(write(tmp_path, {"enabled_rules": ["r43", "r03"], "ar": False}))
    assert [r.id for r in config.rules()] == ["r03", "r43"]
    assert config.ar is False


@pytest.mark.parametrize("data, message", [
    ({"enabled_rules": ["r999"]}, "unknown rule ids"),
    ({"disabled_rules": ["nope"]}, "unknown rule ids"),
    ({"enabled_rules": "some"}, "enabled_rules must be"),
    ({"engine": "yuclid", "disabled_rules": ["r43"]}, "compiled in"),
    ({"rules": []}, "Unknown config keys"),
])
def test_invalid_configs_are_rejected(tmp_path, data, message):
    with pytest.raises(ValueError, match=message):
        DDARConfig.from_json(write(tmp_path, data))


def test_disabling_similarity_warns_about_simtri():
    with pytest.warns(RuleCoverageWarning, match="simtri"):
        load_config(ROOT / "ddar/configs/no_similarity.json")


def test_ar_off_warns(tmp_path):
    with pytest.warns(RuleCoverageWarning, match="AR is off"):
        load_config(write(tmp_path, {"ar": False}))


def test_every_shipped_ddar_config_loads():
    for path in sorted((ROOT / "ddar/configs").glob("*.json")):
        assert DDARConfig.from_json(path).rules()


class DummyTool(Tool):
    name = "dummy"

    def run(self, state):
        return [AuxConstruction(("x = midpoint x a b",), self.name)]


def test_pipeline_config_enables_disables_and_swaps_tools():
    config = {
        "tools": {
            "ddar": {"enabled": True, "options": {"config": "ddar/configs/yuclid.json"}},
            "transformer": {"enabled": False},
            "heuristics": {"enabled": True, "options": {"kinds": ["foot"]}},
            "mine": {"enabled": True, "class": "tests.test_config:DummyTool"},
        },
        "proposer_order": ["mine", "transformer", "heuristics"],
    }
    ddar, proposers = load_tools(config)
    assert isinstance(ddar, DDARTool)
    assert [type(t) for t in proposers] == [DummyTool, HeuristicsTool]
    assert proposers[1].kinds == ["foot"]


def test_pipeline_config_rejects_unknown_tool_in_order():
    with pytest.raises(ValueError, match="unknown tools"):
        load_tools({"tools": {"ddar": {}}, "proposer_order": ["ghost"]})


def test_shipped_pipeline_configs_parse():
    for path in sorted((ROOT / "pipeline/configs").glob("*.json")):
        config = json.loads(path.read_text())
        assert "ddar" in config["tools"]
