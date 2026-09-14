"""
Tests para ai_editor/generation/pipeline_states.py -- FASE 50 "Failure
Recovery" (plan "AI Change Proposal Engine", 2026-08-11).

`classify_pipeline_state()` es una funcion de CLASIFICACION sobre
objetos reales ya producidos por cada etapa del pipeline (nunca fabrica
un estado que el dato no respalde) -- estos tests verifican, para cada
uno de los 15 estados, que el objeto real correspondiente (construido
con el mismo shape que usan los demas tests de `generation/`) produce
la clasificacion esperada, y que la PRECEDENCIA (el estado mas
avanzado gana cuando se pasan varios objetos a la vez) es correcta.
"""
from ai_editor.approval.schema import ApprovalRecord, ChangeSummary
from ai_editor.generation.models import (
    GenerationConfidence,
    GenerationResult,
    PatchApplicationResult,
    STATUS_ERROR,
    STATUS_PROPOSED,
    STATUS_REJECTED,
)
from ai_editor.generation.pipeline_states import (
    ALL_STATES,
    APPROVAL_REQUIRED,
    FAILED,
    GENERATING,
    PLANNED,
    PROMOTED,
    PROPOSED,
    RECEIVED,
    REJECTED,
    RESOLVED,
    ROLLED_BACK,
    TESTING,
    classify_pipeline_state,
)
from ai_editor.generation.promotion import PromotionOutcome
from ai_editor.generation.sandbox_loop import SandboxLoopResult
from ai_editor.repository.promote import PromoteResult
from ai_editor.repository.rollback import RollbackResult
from ai_editor.repository.sandbox import Sandbox


def test_all_states_constant_matches_the_15_named_states_from_the_master_prompt():
    assert len(ALL_STATES) == 15
    assert len(set(ALL_STATES)) == 15


def test_nothing_passed_is_received():
    status = classify_pipeline_state()
    assert status.state == RECEIVED


def test_intent_only_is_received():
    status = classify_pipeline_state(intent={"id": "i1", "request": "r"})
    assert status.state == RECEIVED


def test_context_resolved_is_resolved():
    status = classify_pipeline_state(context={"status": "RESOLVED"})
    assert status.state == RESOLVED


def test_context_unresolved_is_failed():
    status = classify_pipeline_state(context={"status": "UNRESOLVED"})
    assert status.state == FAILED


def test_plan_planned_is_planned():
    status = classify_pipeline_state(context={"status": "RESOLVED"}, plan={"status": "PLANNED"})
    assert status.state == PLANNED


def test_plan_blocked_is_failed():
    status = classify_pipeline_state(context={"status": "RESOLVED"}, plan={"status": "BLOCKED"})
    assert status.state == FAILED


def test_generation_result_proposed_is_proposed():
    result = GenerationResult(status=STATUS_PROPOSED, proposal=None)
    status = classify_pipeline_state(generation_result=result)
    assert status.state == PROPOSED


def test_generation_result_rejected_is_failed():
    result = GenerationResult(status=STATUS_REJECTED, proposal=None)
    status = classify_pipeline_state(generation_result=result)
    assert status.state == FAILED


def test_generation_result_error_is_failed():
    result = GenerationResult(status=STATUS_ERROR, proposal=None)
    status = classify_pipeline_state(generation_result=result)
    assert status.state == FAILED


def _fake_sandbox_loop_result(ready, applied=True):
    from pathlib import Path

    sandbox = Sandbox(root=Path("."), copied_files=[], original_fingerprints={})
    apply_result = PatchApplicationResult(proposal_id="p", applied=applied, apply_results=[], pre_validation_issues=[])
    return SandboxLoopResult(
        proposal_id="p", sandbox=sandbox, apply_result=apply_result,
        validation_report=None, test_report=None, ready_for_approval=ready,
    )


def test_sandbox_loop_ready_for_approval_is_approval_required():
    status = classify_pipeline_state(sandbox_loop_result=_fake_sandbox_loop_result(ready=True))
    assert status.state == APPROVAL_REQUIRED


def test_sandbox_loop_applied_but_not_ready_is_testing():
    status = classify_pipeline_state(sandbox_loop_result=_fake_sandbox_loop_result(ready=False, applied=True))
    assert status.state == TESTING


def test_sandbox_loop_not_applied_is_failed():
    status = classify_pipeline_state(sandbox_loop_result=_fake_sandbox_loop_result(ready=False, applied=False))
    assert status.state == FAILED


def _fake_change_summary():
    return ChangeSummary(request="r", interpretation={}, risk="LOW", files=["app.py"])


def test_promotion_outcome_promoted_is_promoted():
    outcome = PromotionOutcome(
        proposal_id="p", promoted=True, change_summary=_fake_change_summary(),
        approval=None, promote_result=None, blocked_reason=None,
    )
    status = classify_pipeline_state(promotion_outcome=outcome)
    assert status.state == PROMOTED


def test_promotion_outcome_rejected_decision_is_rejected():
    approval = ApprovalRecord(decision="REJECT", reviewer_note=None)
    outcome = PromotionOutcome(
        proposal_id="p", promoted=False, change_summary=_fake_change_summary(),
        approval=approval, promote_result=None, blocked_reason="Decision humana registrada: REJECT",
    )
    status = classify_pipeline_state(promotion_outcome=outcome)
    assert status.state == REJECTED


def test_promotion_outcome_blocked_reason_without_reject_is_failed():
    outcome = PromotionOutcome(
        proposal_id="p", promoted=False, change_summary=_fake_change_summary(),
        approval=None, promote_result=None, blocked_reason="no ready_for_approval",
    )
    status = classify_pipeline_state(promotion_outcome=outcome)
    assert status.state == FAILED


def test_rollback_result_rolled_back_wins_over_everything_else():
    """Precedencia: si hubo rollback, ese ES el estado final, sin
    importar que tambien se haya pasado un promotion_outcome
    'promoted=True' (el estado ANTERIOR a revertir)."""
    promoted_outcome = PromotionOutcome(
        proposal_id="p", promoted=True, change_summary=_fake_change_summary(),
        approval=None, promote_result=PromoteResult(status="PROMOTED", files_promoted=["app.py"],
                                                      files_before={"app.py": "old"}, detail="ok"),
        blocked_reason=None,
    )
    rollback_result = RollbackResult(status="ROLLED_BACK", files_restored=["app.py"], detail="ok")

    status = classify_pipeline_state(promotion_outcome=promoted_outcome, rollback_result=rollback_result)

    assert status.state == ROLLED_BACK


def test_generation_result_wins_over_earlier_context_and_plan():
    status = classify_pipeline_state(
        context={"status": "RESOLVED"}, plan={"status": "PLANNED"},
        generation_result=GenerationResult(status=STATUS_PROPOSED, proposal=None),
    )
    assert status.state == PROPOSED


def test_status_to_dict_has_state_and_detail_keys():
    status = classify_pipeline_state()
    d = status.to_dict()
    assert set(d.keys()) == {"state", "detail"}
    assert d["state"] == RECEIVED
