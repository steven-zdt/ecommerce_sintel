"""
Integration tests para ai_editor/generation/proposal_validator.py --
FASE 29 "Patch Proposal Validator" (plan "AI Change Proposal Engine",
2026-08-11).

Todos los casos usan un `ChangePlan`/`ChangeContext` REALES (contra el
grafo/repo real) -- solo la `PatchProposal` bajo prueba es sintetica, a
proposito: el objetivo de esta fase es validar contra el estado REAL,
asi que un fixture 100% sintetico no probaria nada real.
"""
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.proposal_validator import (
    MAX_OPERATIONS_PER_PROPOSAL,
    validate_proposal_against_repo,
)
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file


def _real_plan_and_context(entities, scope=("backend",), domain="core", intent_name="modify_x"):
    intent = ChangeIntent(
        id="test-proposal-validator", request="r", domain=domain, intent=intent_name,
        entities=list(entities), scope=list(scope), confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    return context, plan


def _exact_content_for_step(step: dict) -> str:
    """Contenido REAL exacto del rango `line_start:line_end` de `step`
    -- lo que `_check_file_and_content` compara contra `old_content` via
    fingerprint. Un `old_content` que sea el archivo ENTERO (en vez del
    rango exacto) produciria `OLD_CONTENT_MISMATCH` igual, aunque el
    contenido sea real."""
    real_path = resolve_repo_file(step["file"])
    lines = real_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    return "".join(lines[step["line_start"] - 1:step["line_end"]])


def _real_old_content(plan):
    step1 = plan.to_dict()["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    return step1, "".join(lines[step1["line_start"] - 1:step1["line_end"]])


def _proposal(operations, confidence=0.9):
    return PatchProposal(
        proposal_id="p", change_id="c", operations=operations,
        reasoning_summary="r", confidence=GenerationConfidence.from_score(confidence),
    )


def test_valid_modify_matching_real_content_produces_no_issues():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, exact_old = _real_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert issues == []


def test_old_content_mismatch_against_real_file_is_rejected():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, _ = _real_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content="esto no es el contenido real de esa linea",
        new_content="x", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert any(i.code == "OLD_CONTENT_MISMATCH" and i.severity == "ERROR" for i in issues)


def test_expected_hash_mismatch_is_rejected():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, exact_old = _real_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old,
        old_hash=None, expected_hash="hash-inventado-no-real", reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert any(i.code == "HASH_MISMATCH" for i in issues)


def test_file_outside_change_plan_is_rejected():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    op = PatchOperation(
        file="core/models.py", symbol=None, operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert any(i.code == "FILE_OUTSIDE_PLAN" for i in issues)


def test_sensitive_file_is_always_rejected():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    op = PatchOperation(
        file=".env", symbol=None, operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert any(i.code == "SENSITIVE_FILE" for i in issues)


def test_writing_to_a_non_documentation_review_step_is_allowed_since_fase_38():
    """FASE 38 "Cross-Stack Generation" (2026-08-11, confirmado
    explicitamente por el usuario) relajo esto: un REVIEW step real
    (contrato/frontend consumer/backend dependency, no documentacion)
    YA puede recibir una escritura -- el grafo lo vinculo como
    consumidor/dependencia REAL del target, no es "fuera del plan"."""
    context, plan = _real_plan_and_context(
        ["EquipmentViewSet.check_availability"], scope=("backend",), domain="renting",
    )
    plan_dict = plan.to_dict()
    review_step = next(
        s for s in plan_dict["steps"]
        if s["operation"] == "REVIEW" and s["file"] and not s["file"].endswith(".md")
        and s["line_start"] is not None
    )
    exact_old = _exact_content_for_step(review_step)
    op = PatchOperation(
        file=review_step["file"], symbol=review_step["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert not any(i.code == "OPERATION_NOT_ALLOWED_FOR_STEP" for i in issues)


def test_writing_to_a_documentation_review_step_stays_blocked_after_fase_38():
    """La relajacion de FASE 38 excluye EXPLICITAMENTE documentacion
    (.md) -- FASE 43 "Documentation-Aware Generation" exige que la doc
    quede como propuesta, nunca aplicada automaticamente."""
    context, plan = _real_plan_and_context(
        ["EquipmentViewSet.check_availability"], scope=("backend",), domain="renting",
    )
    plan_dict = plan.to_dict()
    doc_step = next(
        s for s in plan_dict["steps"]
        if s["operation"] == "REVIEW" and s["file"] and s["file"].endswith(".md")
    )
    op = PatchOperation(
        file=doc_step["file"], symbol=doc_step["symbol"], operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert any(i.code == "OPERATION_NOT_ALLOWED_FOR_STEP" for i in issues)


def test_writing_to_a_run_step_test_file_is_allowed_since_fase_38():
    """FASE 38 tambien habilita escribir sobre steps RUN (tests reales
    identificados por el grafo) -- coincide con el ejemplo de cross-stack
    del prompt maestro, que incluye 'Tests' en la cadena."""
    context, plan = _real_plan_and_context(
        ["EquipmentViewSet.check_availability"], scope=("backend",), domain="renting",
    )
    plan_dict = plan.to_dict()
    run_step = next(
        (s for s in plan_dict["steps"] if s["operation"] == "RUN" and s["file"] and s["line_start"] is not None),
        None,
    )
    if run_step is None:
        import pytest
        pytest.skip("este target no tiene un step RUN real con rango de lineas -- nada que probar")
    exact_old = _exact_content_for_step(run_step)
    op = PatchOperation(
        file=run_step["file"], symbol=run_step["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert not any(i.code == "OPERATION_NOT_ALLOWED_FOR_STEP" for i in issues)


def test_too_many_operations_is_rejected():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, _ = _real_old_content(plan)
    ops = [
        PatchOperation(file=step1["file"], symbol=None, operation="ADD", old_content=None,
                        new_content="x = 1\n", old_hash=None, expected_hash=None, reason="r")
        for _ in range(MAX_OPERATIONS_PER_PROPOSAL + 5)
    ]
    issues = validate_proposal_against_repo(_proposal(ops), plan, context)
    assert any(i.code == "TOO_MANY_OPERATIONS" for i in issues)


def test_empty_new_content_for_modify_is_rejected():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, exact_old = _real_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content="   ", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert any(i.code == "EMPTY_NEW_CONTENT" for i in issues)


def test_drastic_shrink_produces_warning_not_error():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, exact_old = _real_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content="x", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    shrink_issues = [i for i in issues if i.code == "POSSIBLE_UNRELATED_DELETION"]
    assert shrink_issues and shrink_issues[0].severity == "WARNING"


def test_add_operation_does_not_require_old_content():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, _ = _real_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=None, operation="ADD", old_content=None,
        new_content="x = 1\n", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context)
    assert not any(i.code in ("OLD_CONTENT_MISMATCH", "MISSING_OLD_CONTENT") for i in issues)


def test_file_not_found_on_real_disk_is_rejected():
    context, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    plan_dict = plan.to_dict()
    plan_dict["steps"][0]["file"] = "this/does/not/exist_anywhere.py"
    op = PatchOperation(
        file="this/does/not/exist_anywhere.py", symbol=None, operation="MODIFY",
        old_content="x", new_content="y", old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan_dict, context)
    assert any(i.code == "FILE_NOT_FOUND" for i in issues)


def test_validate_proposal_without_context_still_checks_scope_and_content():
    """`context` es opcional -- sin el, solo se omite el chequeo de
    contrato no declarado, el resto sigue funcionando."""
    _, plan = _real_plan_and_context(["HomeCardGroupSelector.get_by_name"])
    step1, exact_old = _real_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )
    issues = validate_proposal_against_repo(_proposal([op]), plan, context=None)
    assert issues == []
