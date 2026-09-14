"""
Unit tests para ai_editor/generation/confidence_engine.py -- FASE 44
"Confidence Engine" (plan "AI Change Proposal Engine", 2026-08-11).
"""
from ai_editor.generation.architecture_compliance import check_architectural_compliance
from ai_editor.generation.confidence_engine import compute_composite_confidence
from ai_editor.generation.contract_awareness import check_contract_coverage
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context


def _proposal(llm_score=0.8):
    op = PatchOperation(
        file="core/services/commands.py", symbol=None, operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    return PatchProposal(
        proposal_id="p44", change_id="c", operations=[op],
        reasoning_summary="r", confidence=GenerationConfidence.from_score(llm_score),
    )


def test_with_only_the_proposal_confidence_equals_llm_score():
    proposal = _proposal(llm_score=0.8)
    report = compute_composite_confidence(proposal)
    assert len(report.factors) == 1
    assert report.factors[0].name == "llm_confidence"
    assert report.composite.score == 0.8


def test_real_context_adds_target_certainty_factor():
    intent = ChangeIntent(
        id="test-confidence", request="r", domain="core", intent="x",
        entities=["HomeCardGroupSelector.get_by_name"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    proposal = _proposal(llm_score=0.8)

    report = compute_composite_confidence(proposal, context=context)
    factor_names = {f.name for f in report.factors}
    assert "target_certainty" in factor_names
    target_factor = next(f for f in report.factors if f.name == "target_certainty")
    assert target_factor.score == 1.0  # RESOLVED
    assert report.composite.score == (0.8 + 1.0) / 2


def test_architecture_and_contract_reports_add_their_own_factors():
    intent = ChangeIntent(
        id="test-confidence-2", request="r", domain="renting", intent="x",
        entities=["EquipmentViewSet.check_availability"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    step1 = plan.to_dict()["steps"][0]
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    proposal = PatchProposal(
        proposal_id="p44b", change_id="c", operations=[op],
        reasoning_summary="r", confidence=GenerationConfidence.from_score(1.0),
    )
    arch_report = check_architectural_compliance(proposal)
    contract_report = check_contract_coverage(proposal, context)

    report = compute_composite_confidence(
        proposal, context=context, architecture_report=arch_report, contract_report=contract_report,
    )
    factor_names = {f.name for f in report.factors}
    assert {"llm_confidence", "target_certainty", "architecture_compliance", "contract_coverage"} <= factor_names
    # contract_coverage sera PARTIAL_COVERAGE (propuesta minima) -> score 0.0 para ese factor
    contract_factor = next(f for f in report.factors if f.name == "contract_coverage")
    assert contract_factor.score == 0.0


def test_missing_syntax_result_is_never_fabricated_as_a_factor():
    """`validation_report=None` -> el factor de sintaxis simplemente no
    participa, nunca se inventa un valor neutro."""
    proposal = _proposal()
    report = compute_composite_confidence(proposal, validation_report=None)
    assert "syntax_validation" not in {f.name for f in report.factors}


def test_to_dict_serializes_composite_and_factors():
    proposal = _proposal(llm_score=0.9)
    report = compute_composite_confidence(proposal)
    d = report.to_dict()
    assert d["composite"]["score"] == 0.9
    assert d["factors"][0]["name"] == "llm_confidence"
