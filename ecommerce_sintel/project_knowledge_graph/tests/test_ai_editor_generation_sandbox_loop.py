"""
Integration tests para ai_editor/generation/sandbox_loop.py -- FASE 32
"Sandbox Generation Loop" (plan "AI Change Proposal Engine", 2026-08-11).

Todos los casos usan un `ChangePlan`/`ChangeContext` reales -- confirma
el flujo completo del prompt maestro: PatchProposal -> Sandbox -> Apply
-> Syntax Validation -> Tests, con el checkout real (`WORKSPACE_ROOT`)
intacto en todos los casos (valido, sintaxis rota, pre-validacion
fallida).
"""
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.sandbox_loop import run_sandbox_validation_loop
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file


def _real_plan_and_context():
    intent = ChangeIntent(
        id="test-sandbox-loop", request="r", domain="core", intent="x",
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


def _proposal(operations, proposal_id="p"):
    return PatchProposal(
        proposal_id=proposal_id, change_id="c", operations=operations,
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
    )


def test_valid_proposal_is_applied_passes_syntax_and_is_ready_for_approval():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )

    real_path = resolve_repo_file(step1["file"])
    real_content_before = real_path.read_text(encoding="utf-8")

    result = run_sandbox_validation_loop(_proposal([op]), plan, context)
    try:
        assert result.apply_result.applied is True
        assert result.validation_report is not None
        assert result.validation_report.level_1_passed is True
        assert result.ready_for_approval is True
        assert result.test_report is not None
        assert "required_count" in result.test_report
    finally:
        result.sandbox.cleanup()

    assert real_path.read_text(encoding="utf-8") == real_content_before


def test_broken_syntax_is_applied_but_fails_validation_and_is_not_ready():
    """Aplicar no falla (el Patch Engine solo escribe texto, no valida
    sintaxis) -- la sintaxis rota se detecta en el paso SIGUIENTE
    (run_validation), exactamente como paso en la ejecucion real de
    POST-GRAPH 21."""
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    broken_content = "def esto_es_sintaxis_python_invalida(((\n"
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=broken_content, old_hash=None, expected_hash=None, reason="r",
    )

    result = run_sandbox_validation_loop(_proposal([op]), plan, context)
    try:
        assert result.apply_result.applied is True
        assert result.validation_report is not None
        assert result.validation_report.level_1_passed is False
        assert result.ready_for_approval is False
    finally:
        result.sandbox.cleanup()


def test_proposal_that_fails_pre_validation_never_reaches_syntax_validation():
    context, plan = _real_plan_and_context()
    step1, _ = _exact_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content="esto no es el contenido real", new_content="x",
        old_hash=None, expected_hash=None, reason="r",
    )

    result = run_sandbox_validation_loop(_proposal([op]), plan, context)
    try:
        assert result.apply_result.applied is False
        assert result.validation_report is None
        assert result.ready_for_approval is False
    finally:
        result.sandbox.cleanup()


def test_sandbox_loop_works_without_context_test_report_is_none():
    _, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )

    result = run_sandbox_validation_loop(_proposal([op]), plan, context=None)
    try:
        assert result.ready_for_approval is True
        assert result.test_report is None
    finally:
        result.sandbox.cleanup()


def test_result_to_dict_serializes_nested_objects():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="r",
    )

    result = run_sandbox_validation_loop(_proposal([op], proposal_id="p32-dict"), plan, context)
    try:
        d = result.to_dict()
        assert d["proposal_id"] == "p32-dict"
        assert d["ready_for_approval"] is True
        assert d["validation_report"]["level_1_passed"] is True
        assert "sandbox_root" in d
    finally:
        result.sandbox.cleanup()
