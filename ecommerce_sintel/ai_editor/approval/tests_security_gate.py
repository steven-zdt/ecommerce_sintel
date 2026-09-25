"""
HARDENING F22 (2026-09-25) -- tests del security impact gate del AI Editor (escritos; no ejecutados por instruccion del usuario).
Sin red ni LLM ni git: sandbox simulado con SimpleNamespace.
"""
from types import SimpleNamespace

from ai_editor.approval.gate import build_change_summary, record_decision
from ai_editor.approval.schema import DECISION_APPROVE
from ai_editor.approval.security_gate import classify_security_impact, security_review_required
from ai_editor.repository.promote import (
    STATUS_NOT_CONFIRMED, STATUS_SECURITY_REVIEW_REQUIRED, promote_to_workspace,
)


def test_archivos_de_negocio_no_requieren_revision():
    assert not security_review_required(["shop/models.py", "frontend/src/views/Home.vue", "renting/services/commands.py"])


def test_superficies_de_seguridad_se_clasifican():
    got = classify_security_impact([
        "docker-compose.prod.yml", "nginx.prod.conf", "ai_engine/tools/classification.py", "ai_engine/config.py",
        "accounts/permissions.py", "ai_knowledge/services/ingest.py", "customer_memory/services/policy.py",
        "deploy/backup.sh", "ai_editor\\repository\\promote.py",
    ])
    assert {"production_config", "ai_tool_policy", "kill_switches_and_model_endpoints", "authentication_authorization",
            "rag_policy", "memory_policy", "backup_config", "ai_editor_boundary"} <= set(got)


def test_rutas_con_backslash_y_prefijo_relativo():
    assert security_review_required([".\\ai_engine_adk\\sintel_adapter.py"])


def _sandbox(files):
    return SimpleNamespace(copied_files=files, original_fingerprints={}, root=".")


def test_promote_exige_revision_elevada():
    approval = record_decision(DECISION_APPROVE)
    result = promote_to_workspace(_sandbox(["ai_engine/config.py"]), approval, workspace_root=".", confirm=True)
    assert result.status == STATUS_SECURITY_REVIEW_REQUIRED


def test_promote_con_revision_elevada_pasa_la_compuerta():
    approval = record_decision(DECISION_APPROVE, security_review_acknowledged=True)
    result = promote_to_workspace(_sandbox(["ai_engine/config.py"]), approval, workspace_root=".", confirm=False)
    assert result.status == STATUS_NOT_CONFIRMED  # sigue exigiendo confirm=True; la compuerta de seguridad ya no bloquea


def test_resumen_marca_security_review_required():
    ctx = {"intent": {"request": "x"}, "resolution": {}}
    plan = {"steps": [{"file": "docker-compose.prod.yml", "operation": "MODIFY"}]}
    summary = build_change_summary(ctx, plan)
    assert summary.security_review_required and "SECURITY_REVIEW_REQUIRED" in summary.render_text()
    assert summary.to_dict()["security_review_required"] is True
