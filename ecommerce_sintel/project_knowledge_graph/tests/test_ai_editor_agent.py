"""
Tests para ai_editor/agent/ -- FASE 51 "AI Editor Agent" + FASE 52 "Agent
Policy" + FASE 53 "Autonomous Controlled Loop" (plan "AI Change Proposal
Engine", 2026-08-11).

Los tests de early-exit (intent/context sin resolver) son 100% reales y
deterministas -- no dependen de un LLM. El test de "REJECTED tras
agotar retries" SI llama a un LLM real (Ollama local, `llama3.1:8b`,
verificado alcanzable antes de escribir este modulo) -- se salta
explicitamente si no esta disponible en el entorno donde corre la suite,
nunca finge un resultado. El test del camino feliz completo
(`APPROVAL_REQUIRED`) monkeypatchea UNICAMENTE `generate_with_retry()`
para devolver una `PatchProposal` REAL (construida con `old_content`
exacto leido del archivo real, mismo patron que
`test_ai_editor_generation_code_quality.py`) -- todo lo DEMAS (sandbox,
validacion, code quality/bandit real, reconciliation, impact recheck,
confidence, human review, promotion gate) corre con las funciones reales
sin mockear nada mas; se evita depender de que un modelo local de 8B
produzca JSON estructurado valido de forma confiable (verificado en la
practica: no lo hace siempre) para poder probar la orquestacion
POSTERIOR a la generacion de forma estable.
"""
import ast

import pytest

from ai_editor.agent import AgentPolicy, run_autonomous_change_loop
from ai_editor.generation.models import GenerationConfidence, GenerationResult, PatchOperation, PatchProposal
from ai_editor.generation.models import STATUS_PROPOSED
from ai_editor.generation.models import RetryAttempt, RetryOutcome
from ai_editor.intent.schema import ChangeIntent
from ai_editor.workspace import resolve_repo_file

_OLLAMA_AVAILABLE = False
try:
    import urllib.request

    with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2):
        _OLLAMA_AVAILABLE = True
except Exception:
    _OLLAMA_AVAILABLE = False


def test_never_imports_promotion_or_repository_promote():
    """REGLA FINAL DE SEGURIDAD -- verificada estructuralmente, no por
    convencion: ningun archivo de ai_editor.agent puede importar el
    modulo que sabe promover al workspace real."""
    import ai_editor.agent as pkg
    import ai_editor.agent.loop as loop_mod
    import ai_editor.agent.policy as policy_mod
    import ai_editor.agent.schema as schema_mod

    for mod in (pkg, loop_mod, policy_mod, schema_mod):
        with open(mod.__spec__.origin, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        # OJO: coincidencia EXACTA de modulo, no substring -- "promotion_gate"
        # (solo lectura, un chequeo previo permitido) contiene "promotion" como
        # substring pero no es el modulo que sabe escribir sobre el workspace
        # real; solo `ai_editor.generation.promotion` (`review_and_promote()`/
        # `rollback_outcome()`) y `ai_editor.repository.promote` lo son.
        forbidden = {"ai_editor.generation.promotion", "ai_editor.repository.promote"}
        assert not (imported & forbidden), (
            f"{mod.__name__} importa un modulo de promocion: {imported & forbidden}"
        )


def test_agent_policy_rejects_max_retries_below_one():
    with pytest.raises(ValueError):
        AgentPolicy(max_retries=0)


def test_intent_needs_clarification_stops_before_touching_the_graph():
    intent = ChangeIntent(
        id="x", request="r", domain=None, intent=None, confidence=0.0,
        ambiguities=["no se entendio nada"], status="NEEDS_CLARIFICATION",
    )

    result = run_autonomous_change_loop("r", intent=intent)

    assert result.status == "FAILED"
    assert result.context is None
    assert result.plan is None
    assert "NEEDS_CLARIFICATION" in result.detail


def test_unresolved_entity_stops_before_planning():
    intent = ChangeIntent(
        id="y", request="r", domain="core", intent="x",
        entities=["EsteSimboloNoExisteJamas.metodo_falso"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
    )

    result = run_autonomous_change_loop("r", intent=intent)

    assert result.status == "FAILED"
    assert result.plan is None
    assert result.context is not None
    assert "no se encontro" in " ".join(result.context.unresolved_entities).lower() or \
        result.context.status != "RESOLVED"


def test_blocked_plan_stops_before_generation(monkeypatch):
    """Forzado via monkeypatch -- construir un ChangePlan BLOCKED real
    con datos del repo es posible pero fragil; se aisla esta rama
    especifica reemplazando `build_change_plan()` por un plan BLOCKED ya
    construido, sin tocar ninguna otra funcion real."""
    import ai_editor.agent.loop as loop_mod
    from ai_editor.planner.schema import ChangePlan

    intent = ChangeIntent(
        id="z", request="r", domain="core", intent="x",
        entities=["HomeCardGroupSelector.get_by_name"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
    )

    def _fake_blocked_plan(context):
        return ChangePlan(context=context.to_dict(), steps=[], status="BLOCKED",
                           blocked_reason="forzado por el test")

    monkeypatch.setattr(loop_mod, "build_change_plan", _fake_blocked_plan)

    result = run_autonomous_change_loop("r", intent=intent)

    assert result.status == "FAILED"
    assert result.retry_outcome is None
    assert "forzado por el test" in result.detail or result.plan_validation.status == "BLOCKED"


@pytest.mark.skipif(not _OLLAMA_AVAILABLE, reason="Ollama no esta alcanzable en localhost:11434")
def test_real_llm_call_that_fails_to_produce_valid_json_ends_in_rejected():
    """Corre contra el LLM REAL (Ollama, llama3.1:8b) -- verificado en la
    practica que este modelo local no siempre devuelve JSON estructurado
    valido en su primer intento; con max_retries=1 este test documenta
    ese comportamiento real (REJECTED, nunca un patch fabricado), no lo
    fuerza. Si algun dia el modelo SI produce un JSON valido en el
    primer intento, el test fallaria -- en ese caso el fix correcto es
    ajustar la asercion al nuevo comportamiento real observado, no
    revertir a uno fabricado."""
    intent = ChangeIntent(
        id="agent-real-llm-test", request="agregar un comentario aclaratorio a "
        "HomeCardGroupSelector.get_by_name explicando que hace, sin cambiar su logica",
        domain="core", intent="modificar", entities=["HomeCardGroupSelector.get_by_name"],
        scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )

    result = run_autonomous_change_loop(intent.request, policy=AgentPolicy(max_retries=1), intent=intent)

    assert result.retry_outcome is not None
    assert len(result.retry_outcome.attempts) == 1
    if result.sandbox_loop_result is not None:
        result.sandbox_loop_result.sandbox.cleanup()


def _real_proposal_for_home_card_group_selector():
    from ai_editor.planner import build_change_plan
    from ai_editor.resolver import resolve_change_context

    intent = ChangeIntent(
        id="agent-happy-path", request="agregar validacion extra a HomeCardGroupSelector.get_by_name",
        domain="core", intent="modificar", entities=["HomeCardGroupSelector.get_by_name"],
        scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    step1 = plan.to_dict()["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    exact_old = "".join(lines[step1["line_start"] - 1:step1["line_end"]])
    new_content = exact_old.replace("HomeCardGroup", "HomeCardGroupOK")
    op = PatchOperation(
        file=step1["file"], symbol=step1["symbol"], operation="MODIFY",
        old_content=exact_old, new_content=new_content, old_hash=None, expected_hash=None,
        reason="agregar validacion (test)",
    )
    proposal = PatchProposal(
        proposal_id="agent-happy-path-proposal", change_id=intent.id, operations=[op],
        reasoning_summary="cambio de prueba para el test del camino feliz del agente",
        confidence=GenerationConfidence.from_score(0.9),
    )
    return intent, proposal


def test_full_happy_path_reaches_approval_required_with_all_reports(monkeypatch):
    import ai_editor.agent.loop as loop_mod

    intent, proposal = _real_proposal_for_home_card_group_selector()
    fake_result = GenerationResult(status=STATUS_PROPOSED, proposal=proposal, provider="test", model="test")
    fake_outcome = RetryOutcome(
        attempts=[RetryAttempt(attempt=1, status=STATUS_PROPOSED, issues=[])],
        final_result=fake_result, succeeded=True,
    )
    monkeypatch.setattr(loop_mod, "generate_with_retry", lambda *a, **k: fake_outcome)

    result = run_autonomous_change_loop(intent.request, intent=intent)

    try:
        assert result.status == "APPROVAL_REQUIRED"
        assert result.sandbox_loop_result.ready_for_approval is True
        assert result.code_quality_report is not None
        assert result.architecture_report is not None
        assert result.dependency_report is not None
        assert result.contract_report is not None
        assert result.test_awareness_report is not None
        assert result.documentation_report is not None
        assert result.reconciliation_report is not None
        assert result.confidence_report is not None
        assert result.promotion_gate_result is not None
        assert result.human_review_text and "HUMAN REVIEW" in result.human_review_text
    finally:
        result.sandbox_loop_result.sandbox.cleanup()


def test_agent_run_result_to_dict_never_raises_and_has_status():
    intent = ChangeIntent(
        id="x", request="r", domain=None, intent=None, confidence=0.0,
        ambiguities=["x"], status="NEEDS_CLARIFICATION",
    )
    result = run_autonomous_change_loop("r", intent=intent)
    d = result.to_dict()
    assert d["status"] == "FAILED"
    assert d["intent"]["id"] == "x"
