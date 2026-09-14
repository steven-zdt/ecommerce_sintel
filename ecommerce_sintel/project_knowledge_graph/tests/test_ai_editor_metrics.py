"""
Unit tests para ai_editor/audit/metrics.py -- POST-GRAPH 17
"Observability" (rediseno "AI Editor Runtime", 2026-08-11). Aislados:
listas de registros sinteticas. La prueba de que `audit_pipeline_run()`
efectivamente popula los campos que `compute_metrics()` necesita, contra
un pipeline real, vive en test_pipeline_equivalence.py.
"""
from ai_editor.audit import compute_metrics


def test_empty_records_produce_all_zero_counts():
    metrics = compute_metrics([])
    assert metrics["changes_requested"] == 0
    assert metrics["changes_approved"] == 0
    assert metrics["rollback_count"] == 0


def test_counts_each_category_independently():
    records = [
        {"plan_status": "PLANNED", "approval_decision": "APPROVE"},
        {"plan_status": "PLANNED", "approval_decision": "REJECT"},
        {"plan_status": "BLOCKED"},
    ]
    metrics = compute_metrics(records)
    assert metrics["changes_requested"] == 3
    assert metrics["changes_planned"] == 2
    assert metrics["changes_approved"] == 1
    assert metrics["changes_rejected"] == 1


def test_patch_failures_sum_across_records_not_just_count_records():
    records = [
        {"patch_failures": 2},
        {"patch_failures": 0},
        {"patch_failures": 3},
    ]
    metrics = compute_metrics(records)
    assert metrics["patch_failures"] == 5


def test_rollback_count_only_counts_actually_rolled_back():
    records = [
        {"rollback_status": "ROLLED_BACK"},
        {"rollback_status": "NOTHING_TO_ROLLBACK"},
        {},
    ]
    metrics = compute_metrics(records)
    assert metrics["rollback_count"] == 1


def test_not_implemented_metrics_are_none_not_fabricated_zero():
    """Bug de honestidad que esta fase evita a proposito: si estos
    campos fueran 0 en vez de None, parecerian '0 problemas detectados'
    en vez de 'nunca se busco'. Deben quedar explicitamente None."""
    metrics = compute_metrics([])
    assert metrics["graph_mismatches"] is None
    assert metrics["unexpected_impacts"] is None
    assert metrics["timing"] is None


def test_compute_metrics_reads_from_the_real_log_when_no_records_given(tmp_path, monkeypatch):
    from ai_editor.audit import log as audit_log

    temp_log = tmp_path / "CHANGE_AUDIT_LOG.jsonl"
    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", temp_log)
    audit_log.log_change_operation(plan_status="PLANNED", approval_decision="APPROVE")

    metrics = compute_metrics()  # sin argumento -- debe leer el log real (parcheado)

    assert metrics["changes_requested"] == 1
    assert metrics["changes_approved"] == 1
