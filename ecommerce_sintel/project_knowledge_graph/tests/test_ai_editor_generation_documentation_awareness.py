"""
Integration tests para ai_editor/generation/documentation_awareness.py
-- FASE 43 "Documentation-Aware Generation" (plan "AI Change Proposal
Engine", 2026-08-11).
"""
from ai_editor.generation.documentation_awareness import (
    STATUS_FAIL,
    STATUS_PASS,
    check_documentation_awareness,
)
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context


def _real_context(entities, domain="renting"):
    intent = ChangeIntent(
        id="test-doc-awareness", request="r", domain=domain, intent="x",
        entities=list(entities), scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    return resolve_change_context(intent)


def _proposal(operations, documentation_to_update=None):
    return PatchProposal(
        proposal_id="p43", change_id="c", operations=operations,
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
        documentation_to_update=documentation_to_update or [],
    )


def _op(file):
    return PatchOperation(
        file=file, symbol=None, operation="MODIFY", old_content="x", new_content="y",
        old_hash=None, expected_hash=None, reason="r",
    )


def test_real_target_with_known_documentation_reports_undeclared_docs():
    context = _real_context(["EquipmentViewSet.check_availability"])
    plan = build_change_plan(context)
    step1 = plan.to_dict()["steps"][0]
    report = check_documentation_awareness(_proposal([_op(step1["file"])]), context)
    assert report.status == STATUS_PASS
    assert report.known_documentation
    assert report.undeclared_known_docs == report.known_documentation


def test_declaring_known_documentation_clears_undeclared_list():
    context = _real_context(["EquipmentViewSet.check_availability"])
    plan = build_change_plan(context)
    step1 = plan.to_dict()["steps"][0]
    report = check_documentation_awareness(
        _proposal([_op(step1["file"])], documentation_to_update=["IMPLEMENTATION_SUMMARY"]),
        context,
    )
    assert report.status == STATUS_PASS
    assert report.undeclared_known_docs == []


def test_a_proposal_that_directly_writes_a_markdown_file_fails_defense_in_depth():
    """No deberia poder pasar nunca (FASE 38 lo excluye estructuralmente)
    -- esta es la defensa en profundidad, probada en aislamiento."""
    report = check_documentation_awareness(_proposal([_op("Documentacion/x.md")]))
    assert report.status == STATUS_FAIL
    assert report.unexpected_doc_writes == ["Documentacion/x.md"]


def test_works_without_context_only_runs_defense_in_depth():
    report = check_documentation_awareness(_proposal([_op("core/models.py")]), context=None)
    assert report.status == STATUS_PASS
    assert report.known_documentation == []
