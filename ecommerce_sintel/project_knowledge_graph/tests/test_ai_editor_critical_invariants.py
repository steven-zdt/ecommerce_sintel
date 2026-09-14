"""
Los 5 invariantes CRITICOS que pide POST-GRAPH 20 "Test Suite" (rediseno
"AI Editor Runtime", 2026-08-11), en un solo archivo para que sean
faciles de encontrar/auditar juntos -- cada uno ya tenia cobertura
dispersa en otros archivos de test salvo el invariante 4, que era un gap
real encontrado auditando esta misma lista.
"""
import ast
from pathlib import Path

import pytest

from ai_editor.approval.schema import ApprovalRecord, DECISION_APPROVE
from ai_editor.patch import (
    OPERATION_MODIFY,
    PatchOperation,
    apply_operation,
)
from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.repository import STATUS_VALIDATION_FAILED, promote_to_workspace
from ai_editor.workspace import WORKSPACE_ROOT, WorkspaceViolation, resolve_workspace_path

AI_EDITOR_DIR = Path(__file__).resolve().parents[2] / "ai_editor"


def test_invariant_1_ai_editor_never_imports_ai_engine():
    """Invariante 1: AI Editor NO importa ai_engine."""
    offenders = []
    for py_file in AI_EDITOR_DIR.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split(".")[0]]
            if "ai_engine" in names:
                offenders.append(str(py_file.relative_to(AI_EDITOR_DIR)))
    assert not offenders


def test_invariant_2_ai_editor_never_writes_outside_the_workspace():
    """Invariante 2: AI Editor NO modifica fuera del workspace."""
    with pytest.raises(WorkspaceViolation):
        resolve_workspace_path("../../../etc/passwd")

    real_path = resolve_workspace_path("ai_editor/workspace.py")
    real_path.relative_to(WORKSPACE_ROOT)  # no lanza -- confirma que esta DENTRO


def test_invariant_3_patch_never_applies_on_fingerprint_mismatch(tmp_path):
    """Invariante 3: Patch NO se aplica si el hash esperado no coincide."""
    sample = tmp_path / "sample.py"
    sample.write_text("original\n", encoding="utf-8")

    op = PatchOperation(
        file="sample.py", operation=OPERATION_MODIFY, line_start=1, line_end=1,
        old_fingerprint="fingerprint-incorrecto-a-proposito",
        new_content="modificado\n", reason="test",
    )
    result = apply_operation(tmp_path, op)

    assert result.status == "FINGERPRINT_MISMATCH"
    assert sample.read_text(encoding="utf-8") == "original\n"  # intacto


def test_invariant_4_patch_never_promotes_if_validation_failed(tmp_path):
    """Invariante 4: Patch NO se promociona si la validacion falla.

    **Gap real encontrado en POST-GRAPH 20**: hasta esta fase,
    `promote_to_workspace()` no tenia forma de saber si la validacion de
    sintaxis habia pasado -- dependia enteramente de que el humano no
    aprobara un cambio con sintaxis rota, sin ningun guardrail de codigo.
    Corregido agregando el parametro opcional `validation_report`: si se
    pasa y `level_1_passed` es `False`, la promocion se rechaza
    ESTRUCTURALMENTE, incluso con `ApprovalRecord(APPROVE)` y
    `confirm=True` -- ambos presentes en este test, y aun asi bloquea."""
    fake_workspace = tmp_path / "fake_workspace"
    fake_workspace.mkdir()
    (fake_workspace / "app.py").write_text("x = 1\n", encoding="utf-8")

    class _FakeSandbox:
        root = fake_workspace
        copied_files: list = []
        original_fingerprints: dict = {}

    approved = ApprovalRecord(decision=DECISION_APPROVE)
    failed_validation = {"level_1_passed": False, "level_1_syntax": {"app.py": {"ok": False, "detail": "x"}}}

    result = promote_to_workspace(
        _FakeSandbox(), approved, fake_workspace, confirm=True,
        validation_report=failed_validation,
    )

    assert result.status == STATUS_VALIDATION_FAILED
    assert result.files_promoted == []


def test_invariant_4_promotes_normally_when_validation_passed_or_omitted(tmp_path):
    """Complemento del invariante 4 -- confirma que el guardrail nuevo no
    rompe el caso normal (retrocompatible: sin `validation_report`, o con
    uno que paso, sigue promoviendo)."""
    fake_workspace = tmp_path / "fake_workspace"
    fake_workspace.mkdir()
    (fake_workspace / "app.py").write_text("x = 1\n", encoding="utf-8")

    class _FakeSandbox:
        root = fake_workspace
        copied_files: list = []
        original_fingerprints: dict = {}

    approved = ApprovalRecord(decision=DECISION_APPROVE)

    result_no_report = promote_to_workspace(_FakeSandbox(), approved, fake_workspace, confirm=True)
    assert result_no_report.status == "PROMOTED"

    passed_validation = {"level_1_passed": True, "level_1_syntax": {}}
    result_passed = promote_to_workspace(
        _FakeSandbox(), approved, fake_workspace, confirm=True, validation_report=passed_validation,
    )
    assert result_passed.status == "PROMOTED"


def test_invariant_5_unexpected_impact_reconciliation_status():
    """Invariante 5: Unexpected Impact -> BLOCK.

    No verificable con datos reales todavia: Graph Reconciliation
    (POST-GRAPH 9) es `NOT_IMPLEMENTED` -- no hay generacion de codigo
    real que pueda producir un impacto inesperado que bloquear. Este test
    documenta el estado real en vez de omitir el invariante en
    silencio: confirma que `reconcile_graph()` reporta su estado
    honestamente (no finge un `BLOCK`/`OK` que no calculo)."""
    from ai_editor.validation import reconcile_graph

    result = reconcile_graph(plan=None)

    assert result.status == "NOT_IMPLEMENTED"
    assert "reconciliar" in result.reason.lower() or "reconciliation" in result.reason.lower()
