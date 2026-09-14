"""
Unit tests para ai_editor/workspace.py y ai_editor/planner/validator.py --
POST-GRAPH 5 "Change Plan Validator" (rediseno "AI Editor Runtime",
2026-08-11). Aislados: usan `tmp_path`/planes sinteticos, no tocan el
grafo real. La prueba de que `resolve_repo_file()` efectivamente
encuentra un archivo real de frontend (el defecto real que motivo esta
fase) vive en test_pipeline_equivalence.py.
"""
import pytest

from ai_editor.planner.schema import ChangePlan
from ai_editor.planner.validator import STATUS_APPROVED, STATUS_BLOCKED, validate_plan
from ai_editor.workspace import (
    REPO_ROOT,
    WORKSPACE_ROOT,
    WorkspaceViolation,
    resolve_repo_doc_path,
    resolve_workspace_path,
)


def test_resolve_workspace_path_rejects_path_traversal():
    with pytest.raises(WorkspaceViolation):
        resolve_workspace_path("../../../etc/passwd")


def test_resolve_workspace_path_accepts_real_relative_path():
    resolved = resolve_workspace_path("ai_editor/workspace.py")
    assert resolved == (WORKSPACE_ROOT / "ai_editor" / "workspace.py").resolve()
    assert resolved.exists()


def _plan_dict(steps, status="PLANNED", blocked_reason=None, unresolved=None):
    return {
        "context": {"unresolved_entities": unresolved or []},
        "steps": steps,
        "status": status,
        "blocked_reason": blocked_reason,
    }


def _step(step=1, file=None, symbol=None, line_start=None, line_end=None,
          operation="MODIFY", dependencies=None, risk="LOW"):
    return {
        "step": step, "file": file, "symbol": symbol, "line_start": line_start,
        "line_end": line_end, "operation": operation, "reason": "r",
        "dependencies": dependencies or [], "risk": risk, "validation": "v",
    }


def test_blocked_plan_input_stays_blocked():
    plan = _plan_dict([], status="BLOCKED", blocked_reason="sin resolucion real")
    result = validate_plan(plan)
    assert result.status == STATUS_BLOCKED
    assert "sin resolucion real" in result.issues[0]


def test_unresolved_entities_from_context_block_the_plan():
    plan = _plan_dict(
        [_step(file="ai_editor/workspace.py")],
        unresolved=["'Foo': no se encontro ningun nodo en el grafo"],
    )
    result = validate_plan(plan)
    assert result.status == STATUS_BLOCKED
    assert any("Foo" in issue for issue in result.issues)


def test_dependency_referencing_nonexistent_step_blocks():
    plan = _plan_dict([_step(step=1, dependencies=[99])])
    result = validate_plan(plan)
    assert result.status == STATUS_BLOCKED
    assert any("step 99" in issue for issue in result.issues)


def test_nonexistent_file_blocks_with_clear_message():
    plan = _plan_dict([_step(file="this/file/does/not/exist_anywhere.py")])
    result = validate_plan(plan)
    assert result.status == STATUS_BLOCKED
    assert any("no existe en disco" in issue for issue in result.issues)


def test_line_range_exceeding_real_file_blocks():
    # ai_editor/workspace.py es corto -- pedir hasta la linea 999999 fuerza el mismatch real.
    plan = _plan_dict([_step(file="ai_editor/workspace.py", symbol="X", line_start=1, line_end=999999)])
    result = validate_plan(plan)
    assert result.status == STATUS_BLOCKED
    assert any("excede el archivo real" in issue for issue in result.issues)


def test_valid_plan_with_real_small_file_is_approved():
    plan = _plan_dict([_step(file="ai_editor/workspace.py", symbol="X", line_start=1, line_end=5, risk="LOW")])
    result = validate_plan(plan)
    assert result.status == STATUS_APPROVED
    assert result.issues == []


def test_high_risk_primary_step_produces_warning_not_block():
    plan = _plan_dict([_step(file="ai_editor/workspace.py", line_start=1, line_end=5, risk="HIGH")])
    result = validate_plan(plan)
    assert result.status == STATUS_APPROVED
    assert any("HIGH" in w for w in result.warnings)


def test_no_run_steps_produces_warning():
    plan = _plan_dict([_step(file="ai_editor/workspace.py", line_start=1, line_end=5, operation="MODIFY")])
    result = validate_plan(plan)
    assert any("ningun test real" in w for w in result.warnings)


def test_step_without_file_is_skipped_not_blocked():
    plan = _plan_dict([_step(file=None)])
    result = validate_plan(plan)
    assert result.status == STATUS_APPROVED


# ---- FASE 24 (plan "AI Change Proposal Engine", 2026-08-11) ---------------
# Bug real encontrado corriendo el baseline: `project_knowledge_graph.
# knowledge_graph.enrichers.documentation` guarda `Documentation.file`
# relativo al repo GIT completo (REPO_ROOT), no a WORKSPACE_ROOT -- un plan
# real de renting (scope backend+frontend) queda BLOCKED porque el paso de
# documentacion `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md`
# nunca resuelve contra WORKSPACE_ROOT, aunque el archivo SI existe (un
# nivel de directorio arriba). Ver docstring de REPO_ROOT en workspace.py.

_REAL_REPO_DOC = "Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md"


def test_repo_root_is_the_parent_of_workspace_root():
    assert REPO_ROOT == WORKSPACE_ROOT.parent


def test_resolve_repo_doc_path_finds_a_real_doc_outside_workspace_root():
    resolved = resolve_repo_doc_path(_REAL_REPO_DOC)
    assert resolved is not None
    assert resolved.exists()
    assert not str(resolved).startswith(str(WORKSPACE_ROOT))


def test_resolve_repo_doc_path_returns_none_for_missing_doc():
    assert resolve_repo_doc_path("Documentacion/no/existe/nunca.md") is None


def test_resolve_repo_doc_path_rejects_traversal_outside_repo_root():
    # A diferencia de resolve_repo_file() (que propaga WorkspaceViolation),
    # este helper de solo-lectura devuelve None -- es un chequeo diagnostico,
    # nunca la base de una escritura, asi que "fuera de limites" y "no
    # existe" comparten el mismo resultado seguro (None).
    assert resolve_repo_doc_path("../../../../etc/passwd") is None


def test_documentation_review_step_outside_workspace_root_warns_not_blocks():
    """El defecto real: antes de este fix, este step dejaba el plan entero
    BLOCKED aunque el .md referenciado SI existe -- solo vive fuera de
    WORKSPACE_ROOT (ai_editor nunca lo escribe, es un REVIEW step)."""
    plan = _plan_dict([
        _step(file="ai_editor/workspace.py", symbol="X", line_start=1, line_end=5, risk="LOW"),
        _step(step=2, file=_REAL_REPO_DOC, operation="REVIEW", dependencies=[1]),
    ])
    result = validate_plan(plan)
    assert result.status == STATUS_APPROVED
    assert any("fuera de WORKSPACE_ROOT" in w for w in result.warnings)
    assert result.issues == []


def test_documentation_review_step_for_missing_doc_still_blocks():
    plan = _plan_dict([
        _step(file="Documentacion/no/existe/nunca.md", operation="REVIEW"),
    ])
    result = validate_plan(plan)
    assert result.status == STATUS_BLOCKED
    assert any("no existe en disco" in issue for issue in result.issues)
