"""
Integration tests para ai_editor/generation/human_review.py -- FASE 45
"Human Review UI/CLI" (plan "AI Change Proposal Engine", 2026-08-11).
"""
from ai_editor.generation.human_review import render_full_review
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal


def _proposal():
    op = PatchOperation(
        file="core/services/commands.py", symbol="X.get_by_name", operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="razon real",
    )
    return PatchProposal(
        proposal_id="p45", change_id="c", operations=[op],
        reasoning_summary="resumen de prueba", confidence=GenerationConfidence.from_score(0.9),
        risks=["riesgo 1"], assumptions=["supuesto 1"],
    )


def test_render_with_only_the_proposal_includes_patch_and_reasoning():
    text = render_full_review(_proposal())
    assert "HUMAN REVIEW" in text
    assert "core/services/commands.py" in text
    assert "resumen de prueba" in text
    assert "riesgo 1" in text
    assert "APPROVE / REJECT / MODIFY_PLAN / REQUEST_EXPLANATION" in text


def test_render_never_fabricates_sections_for_missing_reports():
    text = render_full_review(_proposal())
    assert "CONFIDENCE:" not in text
    assert "GRAPH DIFF" not in text
    assert "IMPACT RECHECK" not in text
    assert "ARCHITECTURE COMPLIANCE" not in text


def test_render_includes_confidence_section_when_report_provided():
    from ai_editor.generation.confidence_engine import compute_composite_confidence

    proposal = _proposal()
    confidence_report = compute_composite_confidence(proposal)
    text = render_full_review(proposal, confidence_report=confidence_report)
    assert "CONFIDENCE: HIGH" in text
    assert "llm_confidence: 0.90" in text


def test_render_includes_architecture_issues_when_present():
    from ai_editor.generation.architecture_compliance import check_architectural_compliance

    op = PatchOperation(
        file="core/services/selectors.py", symbol=None, operation="MODIFY",
        old_content="x", new_content="obj.save()\n", old_hash=None, expected_hash=None, reason="r",
    )
    proposal = PatchProposal(
        proposal_id="p45b", change_id="c", operations=[op],
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
    )
    arch_report = check_architectural_compliance(proposal)
    text = render_full_review(proposal, architecture_report=arch_report)
    assert "ARCHITECTURE COMPLIANCE: FAIL" in text
    assert "selectors_no_side_effects" not in text  # el rule code no se imprime, el message si
    assert "Selector" in text
