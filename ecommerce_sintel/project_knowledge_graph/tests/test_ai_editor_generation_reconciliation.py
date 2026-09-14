"""
Integration tests para ai_editor/generation/reconciliation.py -- FASE 34
"Graph Reconciliation" version SCOPE (plan "AI Change Proposal Engine",
2026-08-11).
"""
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.reconciliation import STATUS_FAIL, STATUS_PASS, reconcile_change_scope
from ai_editor.generation.sandbox_loop import run_sandbox_validation_loop
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file


def _real_plan_and_context(entities=("HomeCardGroupSelector.get_by_name",), scope=("backend",), domain="core"):
    intent = ChangeIntent(
        id="test-reconciliation", request="r", domain=domain, intent="x",
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


def _proposal(operations):
    return PatchProposal(
        proposal_id="p", change_id="c", operations=operations,
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
    )


def test_proposal_within_plan_scope_passes():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    loop_result = run_sandbox_validation_loop(proposal, plan, context)
    try:
        report = reconcile_change_scope(proposal, loop_result, plan, context)
        assert report.status == STATUS_PASS
        assert report.actual_files == 1
        assert report.actual_symbols == 1
        assert report.predicted_files > 0
        assert report.unexpected_impact == []
    finally:
        loop_result.sandbox.cleanup()


def test_proposal_touching_a_file_outside_the_plan_fails_with_unexpected_impact():
    context, plan = _real_plan_and_context()
    op = PatchOperation(
        file="core/models.py", symbol=None, operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    loop_result = run_sandbox_validation_loop(proposal, plan, context)
    try:
        report = reconcile_change_scope(proposal, loop_result, plan, context)
        assert report.status == STATUS_FAIL
        assert report.unexpected_impact
        assert any("core/models.py" in msg for msg in report.unexpected_impact)
    finally:
        loop_result.sandbox.cleanup()


def test_full_graph_rebuild_always_reports_not_implemented():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    loop_result = run_sandbox_validation_loop(proposal, plan, context)
    try:
        report = reconcile_change_scope(proposal, loop_result, plan, context)
        assert report.full_graph_rebuild_status == "NOT_IMPLEMENTED"
        assert "sandbox" in report.full_graph_rebuild_reason.lower()
    finally:
        loop_result.sandbox.cleanup()


def test_predicted_endpoints_counts_real_contract_nodes():
    context, plan = _real_plan_and_context(
        entities=["EquipmentViewSet.check_availability"], domain="renting",
    )
    plan_dict = plan.to_dict()
    step1 = plan_dict["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    exact_old = "".join(lines[step1["line_start"] - 1:step1["line_end"]])
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    loop_result = run_sandbox_validation_loop(proposal, plan, context)
    try:
        report = reconcile_change_scope(proposal, loop_result, plan, context)
        assert report.predicted_endpoints >= 1
    finally:
        loop_result.sandbox.cleanup()


def test_to_dict_serializes_predicted_and_actual():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    loop_result = run_sandbox_validation_loop(proposal, plan, context)
    try:
        report = reconcile_change_scope(proposal, loop_result, plan, context)
        d = report.to_dict()
        assert d["predicted"]["files"] == report.predicted_files
        assert d["actual"]["files"] == 1
    finally:
        loop_result.sandbox.cleanup()
