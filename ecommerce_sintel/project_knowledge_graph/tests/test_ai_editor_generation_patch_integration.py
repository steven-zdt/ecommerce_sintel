"""
Integration tests para ai_editor/generation/patch_integration.py --
FASE 31 "Patch Engine Integration" (plan "AI Change Proposal Engine",
2026-08-11).

Todos los casos usan un `ChangePlan`/`ChangeContext`/`Sandbox` REALES
(`create_sandbox(plan)` copia el archivo real del repo) -- confirma que
el checkout real (`WORKSPACE_ROOT`) nunca se toca, solo la copia dentro
del sandbox temporal.
"""
from ai_editor.generation.models import GenerationConfidence, PatchOperation, PatchProposal
from ai_editor.generation.patch_integration import apply_proposal_to_sandbox
from ai_editor.intent.schema import ChangeIntent
from ai_editor.patch.schema import STATUS_APPLIED, STATUS_FINGERPRINT_MISMATCH, STATUS_REJECTED_OUTSIDE_SANDBOX
from ai_editor.planner import build_change_plan
from ai_editor.repository import create_sandbox
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import WORKSPACE_ROOT, resolve_repo_file


def _real_plan_and_context():
    intent = ChangeIntent(
        id="test-patch-integration", request="r", domain="core", intent="x",
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


def test_apply_proposal_applies_a_valid_modify_and_leaves_the_real_repo_untouched():
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    new_content = exact_old + "        # marca de test FASE 31, nunca deberia llegar al repo real\n"
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None, reason="test real",
    )

    real_path = resolve_repo_file(step1["file"])
    real_content_before = real_path.read_text(encoding="utf-8")

    with create_sandbox(plan) as sandbox:
        result = apply_proposal_to_sandbox(sandbox, _proposal([op]), plan, context)

        assert result.applied is True
        assert len(result.apply_results) == 1
        assert result.apply_results[0].status == STATUS_APPLIED
        assert result.pre_validation_issues == []

        sandbox_content = (sandbox.root / step1["file"]).read_text(encoding="utf-8")
        assert "marca de test FASE 31" in sandbox_content

    # el sandbox ya se limpio (context manager) -- lo que importa es que
    # el archivo REAL nunca cambio durante todo el proceso.
    real_content_after = real_path.read_text(encoding="utf-8")
    assert real_content_after == real_content_before
    assert "marca de test FASE 31" not in real_content_after


def test_apply_proposal_rejects_invalid_proposal_before_touching_the_sandbox():
    context, plan = _real_plan_and_context()
    step1, _ = _exact_old_content(plan)
    bad_op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content="esto no es el contenido real", new_content="x",
        old_hash=None, expected_hash=None, reason="r",
    )

    with create_sandbox(plan) as sandbox:
        result = apply_proposal_to_sandbox(sandbox, _proposal([bad_op]), plan, context)

    assert result.applied is False
    assert result.apply_results == []
    assert any(i.code == "OLD_CONTENT_MISMATCH" for i in result.pre_validation_issues)


def test_apply_operation_still_rejects_writing_outside_a_real_sandbox():
    """Defensa en profundidad real: aunque la pre-validacion (FASE 29)
    pasara, `patch.engine.apply_operation()` tiene su PROPIO guardrail
    que rechaza escribir sobre `WORKSPACE_ROOT` -- simulado pasando un
    'sandbox' cuyo root ES el checkout real."""
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=exact_old, old_hash=None, expected_hash=None, reason="r",
    )

    class FakeSandboxPointingAtRealWorkspace:
        root = WORKSPACE_ROOT

    result = apply_proposal_to_sandbox(FakeSandboxPointingAtRealWorkspace(), _proposal([op]), plan, context)

    assert result.applied is False
    assert result.apply_results[0].status == STATUS_REJECTED_OUTSIDE_SANDBOX


def test_apply_proposal_stops_at_first_failed_operation():
    """Una propuesta con 2 operaciones sobre el mismo archivo -- la
    primera queda desactualizada a proposito (fingerprint mismatch
    simulado via old_content correcto en la validacion previa pero un
    segundo op con rango invalido) para confirmar fail-fast: no sigue
    aplicando despues del primer fallo real de apply_operation."""
    context, plan = _real_plan_and_context()
    step1, exact_old = _exact_old_content(plan)
    # Modifica el CONTENIDO existente de las mismas lineas (no agrega una
    # linea nueva despues) -- asi la segunda aplicacion, con el MISMO
    # old_content original, deja de coincidir con lo que realmente hay
    # ahi tras la primera escritura.
    assert "HomeCardGroup" in exact_old
    changed_content = exact_old.replace("HomeCardGroup", "HomeCardGroupCHANGED")
    good_op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=changed_content, old_hash=None, expected_hash=None, reason="r",
    )

    with create_sandbox(plan) as sandbox:
        # Aplicar el mismo op DOS veces: la primera vez cambia el
        # contenido real del sandbox (old_content ya no coincide con lo
        # que hay ahi), la segunda vez el fingerprint ya no coincide --
        # el sandbox cambio entre la pre-validacion (que corrio contra el
        # REPO real, no el sandbox) y el segundo intento de aplicar sobre
        # el sandbox ya modificado por el primero.
        proposal = _proposal([good_op, good_op])
        result = apply_proposal_to_sandbox(sandbox, proposal, plan, context)

    assert result.applied is False
    assert len(result.apply_results) == 2
    assert result.apply_results[0].status == STATUS_APPLIED
    assert result.apply_results[1].status == STATUS_FINGERPRINT_MISMATCH


def test_add_operation_inserts_immediately_after_the_step_line_range():
    """Leccion real de POST-GRAPH 21: un ADD con line_start=N inserta
    ANTES de la linea N -- para insertar DESPUES del rango del step hay
    que pedir line_end + 1. Verificado leyendo el sandbox real."""
    context, plan = _real_plan_and_context()
    step1, _ = _exact_old_content(plan)
    add_op = PatchOperation(
        file=step1["file"], symbol=None, operation="ADD", old_content=None,
        new_content="        # linea agregada por test FASE 31\n",
        old_hash=None, expected_hash=None, reason="r",
    )

    with create_sandbox(plan) as sandbox:
        result = apply_proposal_to_sandbox(sandbox, _proposal([add_op]), plan, context)
        assert result.applied is True

        sandbox_lines = (sandbox.root / step1["file"]).read_text(encoding="utf-8").splitlines()
        # la linea agregada debe aparecer justo en la posicion line_end
        # (0-indexed: line_end es la ULTIMA linea original del step, la
        # nueva linea ocupa exactamente esa posicion, empujando el resto).
        assert "linea agregada por test FASE 31" in sandbox_lines[step1["line_end"]]


def test_cross_stack_proposal_applies_to_two_real_files_since_fase_38():
    """FASE 38 "Cross-Stack Generation" end-to-end real: una unica
    propuesta toca el target principal (MODIFY, backend real) Y un
    consumidor REVIEW real (backend o frontend, segun el grafo) en el
    MISMO sandbox -- ambos se aplican, y el checkout real queda
    intacto en ambos archivos."""
    intent = ChangeIntent(
        id="test-cross-stack", request="r", domain="renting", intent="x",
        entities=["EquipmentViewSet.check_availability"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    plan_dict = plan.to_dict()

    def exact_content(step):
        real_path = resolve_repo_file(step["file"])
        lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
        return "".join(lines[step["line_start"] - 1:step["line_end"]])

    modify_step = plan_dict["steps"][0]
    review_step = next(
        s for s in plan_dict["steps"]
        if s["operation"] == "REVIEW" and s.get("file") and not s["file"].endswith(".md")
        and s["line_start"] is not None and s["file"] != modify_step["file"]
    )

    old_modify = exact_content(modify_step)
    old_review = exact_content(review_step)
    op_modify = PatchOperation(
        file=modify_step["file"], symbol=modify_step["symbol"], operation="MODIFY",
        old_content=old_modify, new_content=old_modify + "        # cross-stack backend test\n",
        old_hash=None, expected_hash=None, reason="r",
    )
    op_review = PatchOperation(
        file=review_step["file"], symbol=review_step["symbol"], operation="MODIFY",
        old_content=old_review, new_content=old_review + "// cross-stack review test\n",
        old_hash=None, expected_hash=None, reason="r",
    )
    proposal = PatchProposal(
        proposal_id="p38-cross", change_id="test-cross-stack", operations=[op_modify, op_review],
        reasoning_summary="r", confidence=GenerationConfidence.from_score(0.9),
    )

    real_modify_path = resolve_repo_file(modify_step["file"])
    real_review_path = resolve_repo_file(review_step["file"])
    real_modify_before = real_modify_path.read_text(encoding="utf-8")
    real_review_before = real_review_path.read_text(encoding="utf-8")

    with create_sandbox(plan) as sandbox:
        result = apply_proposal_to_sandbox(sandbox, proposal, plan, context)

        assert result.applied is True
        assert len(result.apply_results) == 2
        assert all(r.status == STATUS_APPLIED for r in result.apply_results)

        sandbox_modify = (sandbox.root / modify_step["file"]).read_text(encoding="utf-8")
        sandbox_review = (sandbox.root / review_step["file"]).read_text(encoding="utf-8")
        assert "cross-stack backend test" in sandbox_modify
        assert "cross-stack review test" in sandbox_review

    assert real_modify_path.read_text(encoding="utf-8") == real_modify_before
    assert real_review_path.read_text(encoding="utf-8") == real_review_before


def test_apply_proposal_never_calls_promote_to_workspace():
    import ast

    import ai_editor.generation.patch_integration as mod

    with open(mod.__spec__.origin, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    names_used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attrs_used = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    assert "promote_to_workspace" not in names_used
    assert "promote_to_workspace" not in attrs_used
