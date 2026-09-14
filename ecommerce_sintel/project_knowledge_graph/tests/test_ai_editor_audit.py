"""
Unit tests para ai_editor/audit/ -- POST-GRAPH 13 "Change Audit"
(rediseno "AI Editor Runtime", 2026-08-11). Aislados: monkeypatchean
`AUDIT_LOG_PATH` a un archivo temporal. La prueba de auditoria sobre un
pipeline real vive en test_pipeline_equivalence.py.
"""
import json

import pytest

from ai_editor.audit import log as audit_log
from ai_editor.audit import audit_pipeline_run, log_change_operation, read_recent_operations


@pytest.fixture()
def temp_log_path(tmp_path, monkeypatch):
    path = tmp_path / "CHANGE_AUDIT_LOG.jsonl"
    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", path)
    return path


def test_log_change_operation_writes_a_real_jsonl_line(temp_log_path):
    log_change_operation(request="hola", domain="renting")

    record = json.loads(temp_log_path.read_text(encoding="utf-8").strip())
    assert record["request"] == "hola"
    assert record["domain"] == "renting"
    assert "timestamp" in record


def test_top_level_secret_keys_are_never_persisted(temp_log_path):
    """Bug real encontrado en la propia verificacion de esta fase: la
    primera version solo sanitizaba VALORES via un dict-comprehension
    manual, nunca las CLAVES de primer nivel -- `api_key=...` pasado
    directo como kwarg de primer nivel se colaba integro al log."""
    log_change_operation(request="algo", api_key="sk-secreto-no-debe-aparecer", password="tampoco")

    raw = temp_log_path.read_text(encoding="utf-8")
    assert "sk-secreto-no-debe-aparecer" not in raw
    assert "tampoco" not in raw
    record = json.loads(raw.strip())
    assert "api_key" not in record
    assert "password" not in record


def test_nested_secret_keys_are_never_persisted(temp_log_path):
    log_change_operation(request="algo", nested={"credential": "no-debe-aparecer", "ok": "esto si"})

    record = json.loads(temp_log_path.read_text(encoding="utf-8").strip())
    assert "credential" not in record["nested"]
    assert record["nested"]["ok"] == "esto si"


def test_long_string_values_are_truncated(temp_log_path):
    log_change_operation(request="x" * 1000)

    record = json.loads(temp_log_path.read_text(encoding="utf-8").strip())
    assert len(record["request"]) < 1000
    assert record["request"].endswith("...(truncado)")


def test_log_change_operation_is_best_effort_on_write_failure(monkeypatch):
    class _UnwritablePath:
        def __init__(self):
            self.parent = self

        def mkdir(self, **kwargs):
            pass

        def open(self, *a, **k):
            raise OSError("disco lleno (simulado)")

    monkeypatch.setattr(audit_log, "AUDIT_LOG_PATH", _UnwritablePath())
    # No debe lanzar.
    log_change_operation(request="x")


def test_read_recent_operations_respects_limit_and_skips_corrupt_lines(temp_log_path):
    lines = [json.dumps({"request": f"r{i}"}) for i in range(5)]
    lines.insert(2, "{no valido")
    temp_log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    records = read_recent_operations(limit=3)

    assert len(records) == 3
    assert [r["request"] for r in records] == ["r2", "r3", "r4"]


def test_read_recent_operations_returns_empty_list_when_no_log_file(temp_log_path):
    assert read_recent_operations() == []


def test_audit_pipeline_run_extracts_real_fields_from_synthetic_objects(temp_log_path):
    intent = {"id": "i1", "request": "r", "domain": "shop", "status": "RESOLVED"}
    context = {"status": "RESOLVED", "primary_target": {"name": "Product"}, "unresolved_entities": []}
    plan = {"status": "PLANNED", "steps": [{"file": "shop/models.py", "symbol": "Product.save"}]}

    audit_pipeline_run(intent, context, plan)

    record = json.loads(temp_log_path.read_text(encoding="utf-8").strip())
    assert record["intent_id"] == "i1"
    assert record["primary_target"] == "Product"
    assert record["files"] == ["shop/models.py"]
    assert record["symbols"] == ["Product.save"]


def test_audit_pipeline_run_fase_48_records_generation_and_proposal_metadata_never_raw_content(temp_log_path):
    """FASE 48 "Generation Audit" -- registra provider/model/proposal_id/
    archivos/confianza, pero NUNCA `old_content`/`new_content` ni
    `raw_llm_text`."""
    from ai_editor.generation.models import (
        GenerationConfidence, GenerationResult, PatchOperation, PatchProposal, STATUS_PROPOSED,
    )

    intent = {"id": "i1", "request": "r", "domain": "shop", "status": "RESOLVED"}
    context = {"status": "RESOLVED", "primary_target": {"name": "Product"}, "unresolved_entities": []}
    operation = PatchOperation(
        file="shop/models.py", symbol="Product.save", operation="MODIFY",
        old_content="SECRETO_VIEJO_NO_DEBE_APARECER", new_content="SECRETO_NUEVO_NO_DEBE_APARECER",
        old_hash=None, expected_hash=None, reason="ajustar precio",
    )
    proposal = PatchProposal(
        proposal_id="p1", change_id="i1", operations=[operation],
        reasoning_summary="resumen", confidence=GenerationConfidence.from_score(0.9),
    )
    generation_result = GenerationResult(
        status=STATUS_PROPOSED, proposal=proposal, raw_llm_text="TEXTO_CRUDO_NO_DEBE_APARECER",
        provider="anthropic", model="claude-sonnet-5",
    )

    audit_pipeline_run(intent, context, proposal=proposal, generation_result=generation_result)

    raw = temp_log_path.read_text(encoding="utf-8")
    assert "SECRETO_VIEJO_NO_DEBE_APARECER" not in raw
    assert "SECRETO_NUEVO_NO_DEBE_APARECER" not in raw
    assert "TEXTO_CRUDO_NO_DEBE_APARECER" not in raw

    record = json.loads(raw.strip())
    assert record["generation_status"] == "PROPOSED"
    assert record["generation_provider"] == "anthropic"
    assert record["generation_model"] == "claude-sonnet-5"
    assert record["proposal_id"] == "p1"
    assert record["proposal_confidence"] == 0.9
    assert record["proposal_files"] == ["shop/models.py"]
    assert record["proposal_operations_count"] == 1
