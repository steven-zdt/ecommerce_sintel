"""
Integration tests para ai_editor/generation/contract_awareness.py --
FASE 41 "Contract-Aware Generation" (plan "AI Change Proposal Engine",
2026-08-11).
"""
from ai_editor.generation.contract_awareness import (
    STATUS_FULL_COVERAGE,
    STATUS_NOT_APPLICABLE,
    STATUS_PARTIAL_COVERAGE,
    check_contract_coverage,
)
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file


def _real_plan_and_context(entities, scope=("backend",), domain="core"):
    intent = ChangeIntent(
        id="test-contract-awareness", request="r", domain=domain, intent="x",
        entities=list(entities), scope=list(scope), confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    return context, plan


def _proposal(operations, tests_to_update=None):
    return PatchProposal(
        proposal_id="p41", change_id="c", operations=operations,
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
        tests_to_update=tests_to_update or [],
    )


def test_target_without_contracts_is_not_applicable():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1 = plan.to_dict()["steps"][0]
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    report = check_contract_coverage(_proposal([op]), context)
    assert report.status == STATUS_NOT_APPLICABLE
    assert report.affects_contract is False


def test_target_with_contract_and_minimal_proposal_reports_partial_coverage():
    """EquipmentViewSet.check_availability afecta un contrato real con
    consumidores frontend/tests conocidos -- una propuesta que solo toca
    el target principal deja esos consumidores/tests sin cubrir."""
    context, plan = _real_plan_and_context(
        ["EquipmentViewSet.check_availability"], domain="renting",
    )
    step1 = plan.to_dict()["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    exact_old = "".join(lines[step1["line_start"] - 1:step1["line_end"]])
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old + "        # x\n",
        old_hash=None, expected_hash=None, reason="r",
    )
    report = check_contract_coverage(_proposal([op]), context)

    assert report.affects_contract is True
    assert report.status == STATUS_PARTIAL_COVERAGE
    assert report.known_frontend_consumers
    assert report.missing_frontend_consumers == report.known_frontend_consumers
    assert report.covered_frontend_consumers == []
    assert "consumidor" in report.recommendation


def test_declaring_all_known_tests_reduces_missing_tests_to_zero():
    context, plan = _real_plan_and_context(
        ["EquipmentViewSet.check_availability"], domain="renting",
    )
    step1 = plan.to_dict()["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    exact_old = "".join(lines[step1["line_start"] - 1:step1["line_end"]])
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    context_dict = context.to_dict()
    resolution = context_dict["resolution"]
    tests = resolution.get("tests") or {}
    all_test_names = [
        t["name"] for t in (tests.get("direct_tests") or []) + (tests.get("indirect_tests") or [])
        if t.get("name")
    ]
    assert all_test_names, "el target real deberia tener al menos un test conocido"

    report = check_contract_coverage(_proposal([op], tests_to_update=all_test_names), context)
    assert report.missing_tests == []
    assert set(report.covered_tests) == set(all_test_names)


def test_to_dict_serializes_nested_coverage_structure():
    context, plan = _real_plan_and_context(
        ["EquipmentViewSet.check_availability"], domain="renting",
    )
    step1 = plan.to_dict()["steps"][0]
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    report = check_contract_coverage(_proposal([op]), context)
    d = report.to_dict()
    assert d["affects_contract"] is True
    assert "frontend_consumers" in d and "tests" in d
    assert "known" in d["frontend_consumers"] and "missing" in d["frontend_consumers"]
