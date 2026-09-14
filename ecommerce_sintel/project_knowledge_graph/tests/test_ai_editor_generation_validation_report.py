"""
Integration tests para ai_editor/generation/validation_report.py --
FASE 33 "Automated Test Impact Execution" (plan "AI Change Proposal
Engine", 2026-08-11).
"""
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.sandbox_loop import run_sandbox_validation_loop
from ai_editor.generation.validation_report import (
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_PASS_WITH_WARNINGS,
    build_generation_validation_report,
)
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file


def _real_plan_and_context(entities=("HomeCardGroupSelector.get_by_name",), scope=("backend",), domain="core"):
    intent = ChangeIntent(
        id="test-validation-report", request="r", domain=domain, intent="x",
        entities=list(entities), scope=list(scope), confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    return context, plan


def _exact_old_content(plan):
    step1 = plan.to_dict()["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    return step1, "".join(lines[step1["line_start"] - 1:step1["line_end"]])


def _proposal(operations, proposal_id="p"):
    return PatchProposal(
        proposal_id=proposal_id, change_id="c", operations=operations,
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
    )


def test_valid_proposal_produces_pass_report_with_real_syntax_and_tests():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )
    loop_result = run_sandbox_validation_loop(_proposal([op]), plan, context)
    try:
        report = build_generation_validation_report(loop_result, context)
        assert report.overall_status == STATUS_PASS
        assert report.syntax_passed is True
        assert report.tests_executed is False
        assert "manage.py test" in report.tests_not_executed_reason
        assert report.errors == []
    finally:
        loop_result.sandbox.cleanup()


def test_proposal_that_fails_pre_validation_produces_fail_report_with_errors():
    context, plan = _real_plan_and_context()
    step1, _ = _exact_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content="esto no es el contenido real", new_content="x",
        old_hash=None, expected_hash=None, reason="r",
    )
    loop_result = run_sandbox_validation_loop(_proposal([op]), plan, context)
    try:
        report = build_generation_validation_report(loop_result, context)
        assert report.overall_status == STATUS_FAIL
        assert report.syntax_passed is None
        assert any("old_content" in e.lower() or "OLD_CONTENT" in e for e in report.errors) or report.errors
    finally:
        loop_result.sandbox.cleanup()


def test_report_reflects_undeclared_contract_change_as_error():
    """Un caso real donde la propuesta intenta escribir sobre un
    contrato (Endpoint) que el plan solo declaro para REVIEW -- FASE 29
    lo marca UNDECLARED_CONTRACT_CHANGE/OPERATION_NOT_ALLOWED_FOR_STEP,
    FASE 33 lo refleja en 'errors'."""
    context, plan = _real_plan_and_context(
        entities=["EquipmentViewSet.check_availability"], domain="renting",
    )
    plan_dict = plan.to_dict()
    review_step = next(s for s in plan_dict["steps"] if s["operation"] == "REVIEW" and s["file"])
    op = PatchOperation(
        file=review_step["file"], symbol=review_step["symbol"], operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    loop_result = run_sandbox_validation_loop(_proposal([op]), plan, context)
    try:
        report = build_generation_validation_report(loop_result, context)
        assert report.overall_status == STATUS_FAIL
        assert report.errors
    finally:
        loop_result.sandbox.cleanup()


def test_report_works_without_context_contracts_known_is_empty():
    _, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )
    loop_result = run_sandbox_validation_loop(_proposal([op]), plan, context=None)
    try:
        report = build_generation_validation_report(loop_result, context=None)
        assert report.contracts_known == []
    finally:
        loop_result.sandbox.cleanup()


def test_to_dict_serializes_nested_structure():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )
    loop_result = run_sandbox_validation_loop(_proposal([op], proposal_id="p33-dict"), plan, context)
    try:
        report = build_generation_validation_report(loop_result, context)
        d = report.to_dict()
        assert d["proposal_id"] == "p33-dict"
        assert d["syntax"]["passed"] is True
        assert "tests" in d and "contracts" in d
    finally:
        loop_result.sandbox.cleanup()
