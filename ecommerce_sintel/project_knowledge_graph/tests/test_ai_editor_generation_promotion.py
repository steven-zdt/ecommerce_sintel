"""
Integration tests para ai_editor/generation/promotion.py --
`review_and_promote()`, encadena generation/ (FASE 24-32) con
approval/ (POST-GRAPH 11) y repository.promote_to_workspace()
(POST-GRAPH 12).

Mismo patron que `test_ai_editor_commit_control.py`: opera SOLO sobre
`fake_workspace` (`tmp_path`, un directorio temporal), NUNCA sobre
`ai_editor.workspace.WORKSPACE_ROOT` real -- promover contra el
checkout real de este proyecto requiere una instruccion explicita
separada del usuario en el momento, no una consecuencia de tener esta
funcion implementada y testeada.
"""
import pytest

from ai_editor.generation.models import PatchApplicationResult
from ai_editor.generation.promotion import review_and_promote, rollback_outcome
from ai_editor.generation.sandbox_loop import SandboxLoopResult
from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.repository.sandbox import Sandbox
from ai_editor.validation.engine import ValidationReport


@pytest.fixture
def fake_workspace(tmp_path):
    root = tmp_path / "fake_workspace"
    root.mkdir()
    (root / "app.py").write_text("line1\nline2\n", encoding="utf-8")
    return root


def _fake_sandbox(fake_workspace, tmp_path, new_content="line1\nCHANGED\n"):
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    (sandbox_dir / "app.py").write_text(new_content, encoding="utf-8")
    original_fp = compute_fingerprint((fake_workspace / "app.py").read_text(encoding="utf-8"))
    return Sandbox(root=sandbox_dir, copied_files=["app.py"], original_fingerprints={"app.py": original_fp})


def _fake_context_and_plan():
    context = {
        "intent": {"request": "cambio de prueba", "intent": "x", "domain": "d", "confidence": 0.9},
        "resolution": {"risk": "LOW", "contracts": [], "frontend_consumers": [],
                        "backend_dependencies": [], "documentation": {}},
    }
    plan = {"steps": [{"file": "app.py", "symbol": None, "operation": "MODIFY"}]}
    return context, plan


def _loop_result(sandbox, ready=True, level_1_passed=True):
    apply_result = PatchApplicationResult(proposal_id="p", applied=ready, apply_results=[], pre_validation_issues=[])
    validation_report = ValidationReport(level_1_syntax={}, level_1_passed=level_1_passed) if ready else None
    return SandboxLoopResult(
        proposal_id="p", sandbox=sandbox, apply_result=apply_result,
        validation_report=validation_report, test_report=None, ready_for_approval=ready,
    )


def test_blocks_when_sandbox_loop_was_not_ready_for_approval(fake_workspace, tmp_path):
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox, ready=False)

    outcome = review_and_promote(loop_result, context, plan, fake_workspace, decision="APPROVE", confirm=True)

    assert outcome.promoted is False
    assert outcome.approval is None
    assert outcome.promote_result is None
    assert "FASE 32" in outcome.blocked_reason
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_blocks_on_reject_decision_never_calls_promote(fake_workspace, tmp_path):
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox)

    outcome = review_and_promote(loop_result, context, plan, fake_workspace, decision="REJECT")

    assert outcome.promoted is False
    assert outcome.approval.decision == "REJECT"
    assert outcome.promote_result is None
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_blocks_when_approved_but_not_confirmed(fake_workspace, tmp_path):
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox)

    outcome = review_and_promote(loop_result, context, plan, fake_workspace, decision="APPROVE", confirm=False)

    assert outcome.promoted is False
    assert outcome.promote_result.status == "NOT_CONFIRMED"
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_succeeds_when_approved_and_confirmed_writes_to_fake_workspace_only(fake_workspace, tmp_path):
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox)

    outcome = review_and_promote(
        loop_result, context, plan, fake_workspace, decision="APPROVE", confirm=True, reviewer_note="ok",
    )

    assert outcome.promoted is True
    assert outcome.promote_result.status == "PROMOTED"
    assert outcome.approval.reviewer_note == "ok"
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nCHANGED\n"


def test_invalid_decision_string_raises_same_as_record_decision(fake_workspace, tmp_path):
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox)

    with pytest.raises(ValueError):
        review_and_promote(loop_result, context, plan, fake_workspace, decision="MAYBE", confirm=True)


def test_promote_to_workspace_guardrail_still_blocks_a_failed_validation_report(fake_workspace, tmp_path):
    """Defensa en profundidad: aunque `ready_for_approval` fuera
    (incorrectamente) `True`, `promote_to_workspace()` tiene su PROPIO
    guardrail (POST-GRAPH 20) que rechaza si `validation_report.
    level_1_passed` es `False` -- simulado con un SandboxLoopResult
    inconsistente a proposito."""
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    apply_result = PatchApplicationResult(proposal_id="p", applied=True, apply_results=[], pre_validation_issues=[])
    inconsistent_loop_result = SandboxLoopResult(
        proposal_id="p", sandbox=sandbox, apply_result=apply_result,
        validation_report=ValidationReport(level_1_syntax={}, level_1_passed=False),
        test_report=None, ready_for_approval=True,  # inconsistente a proposito
    )

    outcome = review_and_promote(
        inconsistent_loop_result, context, plan, fake_workspace, decision="APPROVE", confirm=True,
    )

    assert outcome.promoted is False
    assert outcome.promote_result.status == "VALIDATION_FAILED"
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_change_summary_reflects_the_plan_and_context_passed_in(fake_workspace, tmp_path):
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox)

    outcome = review_and_promote(loop_result, context, plan, fake_workspace, decision="APPROVE", confirm=True)

    assert outcome.change_summary.files == ["app.py"]
    assert outcome.change_summary.request == "cambio de prueba"
    assert outcome.change_summary.risk == "LOW"


def test_rollback_outcome_restores_the_fake_workspace_file_after_a_real_promotion(fake_workspace, tmp_path):
    """FASE 47 "Rollback" -- `rollback_outcome()` debe revertir un
    `PromotionOutcome` YA promovido usando el `promote_result.
    files_before` capturado por `promote_to_workspace()`, sin volver a
    tocar nada de `generation/`."""
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox)

    outcome = review_and_promote(loop_result, context, plan, fake_workspace, decision="APPROVE", confirm=True)
    assert outcome.promoted is True
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nCHANGED\n"

    result = rollback_outcome(fake_workspace, outcome)

    assert result.status == "ROLLED_BACK"
    assert "app.py" in result.files_restored
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_rollback_outcome_on_a_never_promoted_outcome_is_a_noop(fake_workspace, tmp_path):
    """Si la propuesta nunca se promovio (`promoted=False`,
    `promote_result=None`), no hay nada que revertir -- mismo
    `NOTHING_TO_ROLLBACK` que ya devuelve `rollback_promotion()` para
    ese caso, sin lanzar excepcion."""
    sandbox = _fake_sandbox(fake_workspace, tmp_path)
    context, plan = _fake_context_and_plan()
    loop_result = _loop_result(sandbox, ready=False)

    outcome = review_and_promote(loop_result, context, plan, fake_workspace, decision="APPROVE", confirm=True)
    assert outcome.promote_result is None

    result = rollback_outcome(fake_workspace, outcome)

    assert result.status == "NOTHING_TO_ROLLBACK"
    assert (fake_workspace / "app.py").read_text(encoding="utf-8") == "line1\nline2\n"


def test_never_imports_ai_editor_llm_or_generation_llm_dependent_modules():
    """`promotion.py` opera sobre resultados YA generados/validados --
    no deberia tener ninguna dependencia del LLM."""
    import ast

    import ai_editor.generation.promotion as mod

    with open(mod.__spec__.origin, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any(m == "ai_editor.llm" or m.startswith("ai_editor.llm.") for m in imported_modules)
