"""
Integration tests para ai_editor/generation/code_quality.py -- FASE 36
"Code Quality Validation" (plan "AI Change Proposal Engine", 2026-08-11).

Usa `bandit` REAL (1.9.4, verificado instalado en este entorno antes de
escribir el modulo) -- no mockeado. Si `bandit` no esta disponible en el
entorno donde corre esta suite, los tests que dependen de un hallazgo
real se saltan explicitamente (`pytest.skip`), nunca fingen un resultado.
"""
import shutil

import pytest

from ai_editor.generation.code_quality import (
    STATUS_FAIL,
    STATUS_NOT_CONFIGURED,
    STATUS_PASS,
    run_code_quality_checks,
)
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.sandbox_loop import run_sandbox_validation_loop
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file

_BANDIT_AVAILABLE = shutil.which("bandit") is not None


def _real_plan_and_context():
    intent = ChangeIntent(
        id="test-code-quality", request="r", domain="core", intent="x",
        entities=["HomeCardGroupSelector.get_by_name"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
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


@pytest.mark.skipif(not _BANDIT_AVAILABLE, reason="bandit no esta instalado en este entorno")
def test_clean_python_change_passes_real_bandit_scan():
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
        report = run_code_quality_checks(loop_result.sandbox, proposal)
        assert report.overall_status == STATUS_PASS
        assert report.checks[0].tool == "bandit"
        assert report.checks[0].status == STATUS_PASS
    finally:
        loop_result.sandbox.cleanup()


@pytest.mark.skipif(not _BANDIT_AVAILABLE, reason="bandit no esta instalado en este entorno")
def test_eval_call_is_caught_by_real_bandit_scan():
    """Hallazgo REAL de bandit (B307, eval), no simulado -- prueba que
    el subprocess realmente corre y realmente detecta."""
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    risky_content = exact_old + '        eval("1+1")\n'
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=risky_content, old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    loop_result = run_sandbox_validation_loop(proposal, plan, context)
    try:
        report = run_code_quality_checks(loop_result.sandbox, proposal)
        assert report.overall_status == STATUS_FAIL
        assert report.checks[0].status == STATUS_FAIL
        assert "eval" in report.checks[0].detail.lower() or "B307" in report.checks[0].detail
    finally:
        loop_result.sandbox.cleanup()


def test_no_operations_produces_not_configured_overall_status():
    context, plan = _real_plan_and_context()
    proposal = _proposal([])
    loop_result = run_sandbox_validation_loop(proposal, plan, context)
    try:
        report = run_code_quality_checks(loop_result.sandbox, proposal)
        assert report.overall_status == STATUS_NOT_CONFIGURED
        assert report.checks == []
    finally:
        loop_result.sandbox.cleanup()


def test_vue_file_reports_not_configured_never_fabricated():
    """No hay eslint/prettier instalados en este proyecto (verificado
    real antes de escribir el modulo) -- un archivo .vue/.js siempre
    reporta NOT_CONFIGURED, nunca un resultado inventado."""
    import tempfile
    from pathlib import Path

    from ai_editor.repository.sandbox import Sandbox

    tmp = Path(tempfile.mkdtemp())
    (tmp / "Component.vue").write_text("<template></template>", encoding="utf-8")
    sandbox = Sandbox(root=tmp, copied_files=["Component.vue"], original_fingerprints={})

    op = PatchOperation(
        file="Component.vue", symbol=None, operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    report = run_code_quality_checks(sandbox, proposal)

    assert report.overall_status == STATUS_NOT_CONFIGURED
    assert report.checks[0].tool == "eslint"
    assert report.checks[0].status == STATUS_NOT_CONFIGURED


def test_path_traversal_operation_file_is_rejected_never_scanned_outside_sandbox():
    """FASE 49 "Security Hardening" -- gap real encontrado en la propia
    auditoria: `run_code_quality_checks()` no revalidaba que `op.file`
    siguiera dentro del sandbox antes de construir `real_path`, a
    diferencia de `patch.engine.apply_operation()` (POST-GRAPH 6) que si
    lo hace. En la practica `op.file` ya esta constreñido aguas arriba
    (FASE 29 `find_matching_step()` exige que matchee un `PlanStep.file`
    real, derivado del grafo, nunca del LLM directo) -- este test prueba
    la defensa en profundidad de ESTE modulo en aislamiento, sin esa capa
    previa, igual que `test_vue_file_reports_not_configured_never_fabricated`
    de arriba construye su propio Sandbox directo."""
    import tempfile
    from pathlib import Path

    from ai_editor.repository.sandbox import Sandbox

    tmp = Path(tempfile.mkdtemp())
    (tmp / "app.py").write_text("x = 1\n", encoding="utf-8")
    sandbox = Sandbox(root=tmp, copied_files=["app.py"], original_fingerprints={})

    op = PatchOperation(
        file="../../../etc/passwd", symbol=None, operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    proposal = _proposal([op])
    report = run_code_quality_checks(sandbox, proposal)

    assert report.overall_status == STATUS_FAIL
    assert report.checks[0].status == STATUS_FAIL
    assert "fuera del sandbox" in report.checks[0].detail
