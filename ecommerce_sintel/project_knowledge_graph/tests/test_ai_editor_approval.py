"""
Unit tests para ai_editor/approval/ -- POST-GRAPH 11 "Human Approval
Gate" (rediseno "AI Editor Runtime", 2026-08-11). Aislados: context/plan
sinteticos. La prueba de un CHANGE SUMMARY real sobre el caso Renting
vive en test_pipeline_equivalence.py.
"""
import pytest

from ai_editor.approval import (
    DECISION_APPROVE,
    build_change_summary,
    record_decision,
)


def _context(risk="MEDIUM"):
    return {
        "intent": {"request": "agregar X", "intent": "add_field", "domain": "shop", "confidence": 0.8},
        "resolution": {
            "risk": risk,
            "contracts": [{"name": "api/v1/shop/x"}],
            "frontend_consumers": [{"name": "XView"}],
            "backend_dependencies": [],
            "documentation": {"architecture_docs": [{"name": "DOC_A"}], "implementation_docs": [], "audit_docs": []},
        },
    }


def _plan(steps=None):
    return {"steps": steps or [
        {"file": "shop/models.py", "symbol": "Product.save", "operation": "MODIFY"},
        {"file": "shop/serializers.py", "symbol": None, "operation": "REVIEW"},
    ]}


def test_build_change_summary_extracts_files_symbols_and_contracts():
    summary = build_change_summary(_context(), _plan())

    assert summary.files == ["shop/models.py", "shop/serializers.py"]
    assert summary.symbols == ["Product.save"]
    assert summary.contracts == ["api/v1/shop/x"]
    assert summary.documentation == ["DOC_A"]


def test_build_change_summary_counts_only_modify_steps_as_patch_operations():
    summary = build_change_summary(_context(), _plan())
    assert summary.patch_operations == 1  # solo el step MODIFY, no el REVIEW


def test_build_change_summary_total_affected_sums_the_three_real_buckets():
    summary = build_change_summary(_context(), _plan())
    assert summary.total_affected == 2  # 1 contract + 1 frontend_consumer + 0 backend


def test_build_change_summary_defaults_validation_to_not_run_when_omitted():
    summary = build_change_summary(_context(), _plan())
    assert summary.validation_status == "NOT_RUN"
    assert summary.validation_issues == []


def test_build_change_summary_reflects_validation_report_failures():
    class _FakeValidationReport:
        def to_dict(self):
            return {
                "level_1_passed": False,
                "level_1_syntax": {"shop/models.py": {"ok": False, "detail": "SyntaxError: x"}},
            }

    summary = build_change_summary(_context(), _plan(), validation_report=_FakeValidationReport())

    assert summary.validation_status == "FAIL"
    assert summary.validation_issues == ["shop/models.py: SyntaxError: x"]


def test_change_summary_render_text_includes_all_required_fields():
    summary = build_change_summary(_context(), _plan())
    text = summary.render_text()

    for expected in ("Request:", "Interpretation:", "Files:", "Symbols:", "Contracts:",
                      "Impact:", "Risk:", "Patch:", "Tests:", "Documentation:",
                      "Unexpected changes:"):
        assert expected in text


def test_change_summary_always_flags_unexpected_changes_as_unverified():
    summary = build_change_summary(_context(), _plan())
    assert "NOT_IMPLEMENTED" in summary.unexpected_changes_note


def test_record_decision_accepts_the_four_valid_options():
    for decision in ("APPROVE", "REJECT", "MODIFY_PLAN", "REQUEST_EXPLANATION"):
        record = record_decision(decision)
        assert record.decision == decision
        assert record.timestamp


def test_record_decision_rejects_invalid_decision():
    with pytest.raises(ValueError):
        record_decision("MAYBE_LATER")


def test_record_decision_stores_reviewer_note():
    record = record_decision(DECISION_APPROVE, reviewer_note="se ve bien")
    assert record.reviewer_note == "se ve bien"
