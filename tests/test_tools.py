"""Each tool: DDAR, heuristics, transformer, plus the model-format translation."""

import pytest

from pipeline.tools import AuxConstruction, DDARTool, HeuristicsTool, ProofState
from pipeline.translate import UntranslatableAux, aux_to_clauses, problem_to_model_text
from tests.conftest import ORTHOCENTER

TRIANGLE_WITH_MIDPOINT = "a b c = triangle a b c; m = midpoint m b c ? cong m b m c"


@pytest.fixture(scope="module")
def ddar():
    return DDARTool(config="ddar/configs/yuclid.json")


@pytest.fixture(scope="module")
def checked(ddar):
    state = ProofState.from_text(TRIANGLE_WITH_MIDPOINT)
    ddar.run(state)
    return state


def test_ddar_solves_orthocenter_and_records_rules(ddar):
    state = ProofState.from_text(ORTHOCENTER)
    assert ddar.run(state) is None  # DDAR proposes nothing
    assert state.solved and state.error is None
    assert "r43" in state.rules_in_proof
    assert "perp" in state.proof.lower() or "⟂" in state.proof


def test_ddar_reports_unbuildable_figure(ddar):
    state = ProofState.from_text("a b = segment a b; c = on_line c a b, on_line c a b ? cong a c b c")
    ddar.run(state)
    assert not state.solved and state.error


def test_ddar_python_engine_respects_disabled_rule():
    tool = DDARTool(config="ddar/configs/no_orthocenter.json")
    state = ProofState.from_text(ORTHOCENTER)
    tool.run(state)
    assert "r43" not in state.rules_fired


def test_heuristics_propose_deterministic_new_points(checked):
    tool = HeuristicsTool(max_candidates=20)
    first, second = tool.run(checked), tool.run(checked)
    assert first == second
    clauses = [p.clauses[0] for p in first]
    assert all(isinstance(p, AuxConstruction) and p.source == "heuristics" for p in first)
    assert {c.split()[2] for c in clauses} <= {"midpoint", "circle", "foot"}
    # the midpoint of b c already exists as m, so it must not be proposed again
    assert not any(c.endswith("midpoint d b c") for c in clauses)


def test_heuristics_kinds_and_limit(checked):
    proposals = HeuristicsTool(kinds=["foot"], max_candidates=2).run(checked)
    assert len(proposals) == 2 and all(" foot " in p.clauses[0] for p in proposals)
    with pytest.raises(ValueError):
        HeuristicsTool(kinds=["random_point"])


def test_heuristics_need_a_checked_state():
    assert HeuristicsTool().run(ProofState.from_text(ORTHOCENTER)) is None


def test_problem_to_model_text(checked):
    text, to_problem = problem_to_model_text(checked)
    assert text.startswith("a :; b :; c :; d : ")
    assert "? cong" in text
    assert to_problem["d"] == "m"


@pytest.mark.parametrize("aux, expected", [
    ("d : coll a b d, perp a b d c", "on_line d a b, on_tline d c a b"),
    ("d : cong d a d b", "on_bline d a b"),
    ("d : cong a d a b", "on_circle d a b"),
    ("d : cyclic a b c d", "on_circum d a b c"),
    ("d : para a d b c", "on_pline d a b c"),
    ("d : perp d a d b", "on_dia d a b"),
])
def test_aux_translation(aux, expected):
    names = {"a": "a", "b": "b", "c": "c"}
    (clause,) = aux_to_clauses(aux, names)
    assert clause == f"d = {expected}"


def test_aux_translation_renames_new_point_and_rejects_unsupported():
    (clause,) = aux_to_clauses("d : coll a b d", {"a": "p", "b": "q", "c": "d"})
    assert clause == "a = on_line a p q"  # 'd' is taken in the problem, so a fresh name
    with pytest.raises(UntranslatableAux):
        aux_to_clauses("d : eqangle a b a d a d a c", {"a": "a", "b": "b", "c": "c"})
    with pytest.raises(UntranslatableAux):
        aux_to_clauses("d : coll a z d", {"a": "a"})


def test_transformer_tool_runs_untrained_model(tmp_path, checked):
    torch = pytest.importorskip("torch")
    from geo_lm import GeoTokenizer, ModelConfig, create_model, save_checkpoint
    from pipeline.transformer_tool import TransformerTool

    torch.manual_seed(0)
    tok = GeoTokenizer.build(["a :; b :; c : coll a b c ? cong a b a c <aux> d : coll a b d, perp a b d c"])
    model = create_model(ModelConfig(vocab_size=64, context_length=128, n_layer=1, n_head=2, n_embd=32), tok)
    path = tmp_path / "tiny.pt"
    save_checkpoint(path, model, tok)

    tool = TransformerTool(checkpoint=str(path), beam_size=3, max_new_tokens=12)
    first = tool.run(checked)
    assert first is None or all(p.source == "transformer" for p in first)
    assert tool.run(checked) == first  # beam search is deterministic
    assert tool.calls == 2


def test_transformer_tool_missing_checkpoint():
    from pipeline.transformer_tool import TransformerTool

    with pytest.raises(FileNotFoundError):
        TransformerTool(checkpoint="no/such/model.pt")
