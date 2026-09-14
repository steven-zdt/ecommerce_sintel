"""
Unit tests para ai_editor/generation/promotion_gate.py -- FASE 46
"Promotion Gate" (plan "AI Change Proposal Engine", 2026-08-11).
"""
from ai_editor.generation.models import PatchApplicationResult
from ai_editor.generation.promotion_gate import STATUS_BLOCKED, STATUS_READY, check_promotion_gate
from ai_editor.generation.reconciliation import GraphReconciliationReport
from ai_editor.generation.sandbox_loop import SandboxLoopResult
from ai_editor.validation.engine import ValidationReport


def _loop_result(ready=True):
    apply_result = PatchApplicationResult(proposal_id="p46", applied=ready, apply_results=[], pre_validation_issues=[])
    validation_report = ValidationReport(level_1_syntax={}, level_1_passed=True) if ready else None
    return SandboxLoopResult(
        proposal_id="p46", sandbox=None, apply_result=apply_result,
        validation_report=validation_report, test_report=None, ready_for_approval=ready,
    )


def test_ready_sandbox_with_no_extra_reports_is_ready():
    gate = check_promotion_gate(_loop_result(ready=True))
    assert gate.status == STATUS_READY
    assert gate.blocking_reasons == []
    assert any("Tests pass" in w for w in gate.warnings)


def test_not_ready_sandbox_blocks():
    gate = check_promotion_gate(_loop_result(ready=False))
    assert gate.status == STATUS_BLOCKED
    assert gate.blocking_reasons


def test_failed_reconciliation_blocks():
    recon = GraphReconciliationReport(
        proposal_id="p46", status="FAIL", predicted_files=1, predicted_symbols=1,
        predicted_endpoints=0, actual_files=2, actual_symbols=2, unexpected_impact=["archivo fuera de plan"],
    )
    gate = check_promotion_gate(_loop_result(ready=True), reconciliation_report=recon)
    assert gate.status == STATUS_BLOCKED
    assert any("Graph Reconciliation" in r for r in gate.blocking_reasons)


def test_passed_reconciliation_does_not_block():
    recon = GraphReconciliationReport(
        proposal_id="p46", status="PASS", predicted_files=1, predicted_symbols=1,
        predicted_endpoints=0, actual_files=1, actual_symbols=1,
    )
    gate = check_promotion_gate(_loop_result(ready=True), reconciliation_report=recon)
    assert gate.status == STATUS_READY


def test_partial_contract_coverage_is_a_warning_not_a_block():
    from ai_editor.generation.contract_awareness import ContractCoverageReport

    contract = ContractCoverageReport(
        proposal_id="p46", status="PARTIAL_COVERAGE", affects_contract=True,
        known_frontend_consumers=["a.vue"], missing_frontend_consumers=["a.vue"],
        recommendation="revisar",
    )
    gate = check_promotion_gate(_loop_result(ready=True), contract_report=contract)
    assert gate.status == STATUS_READY
    assert any("Contract Coverage" in w for w in gate.warnings)


def test_to_dict_serializes_gate_result():
    gate = check_promotion_gate(_loop_result(ready=True))
    d = gate.to_dict()
    assert d["status"] == STATUS_READY
    assert "blocking_reasons" in d and "warnings" in d
