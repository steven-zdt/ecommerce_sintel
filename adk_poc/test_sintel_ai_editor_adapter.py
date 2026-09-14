"""
ADK-09 -- prueba del HITL adapter de ai_editor.

`review_and_promote()` real SI escribe sobre `WORKSPACE_ROOT` real
(`ecommerce_sintel/`, confirmado leyendo `ai_editor/workspace.py` -- es el
repo Django VIVO, no un sandbox) si sus 4 gates internos lo permiten. Por
eso ESTOS tests nunca lo invocan de verdad -- se mockea, igual criterio que
`test_sintel_adapter_hitl.py` (ADK-02) nunca invoco la escritura real de
`RequestKycUpgradeTool`. `run_autonomous_change_loop()` tampoco se corre
real (ver docstring de `sintel_ai_editor_adapter.py`, limite deliberado de
alcance -- es una cadena larga de llamadas LLM + validacion de sandbox).
"""
import ast
import inspect
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ECOMMERCE_SINTEL_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel"
if str(ECOMMERCE_SINTEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ECOMMERCE_SINTEL_ROOT))

import sintel_ai_editor_adapter as adapter_module
from sintel_ai_editor_adapter import _PENDING_PROPOSALS, build_ai_editor_hitl_tools, propose_code_change


def test_propose_code_change_has_no_confirmation_gate_and_promote_does():
    tools = build_ai_editor_hitl_tools()
    by_name = {t.name: t for t in tools}
    assert by_name["propose_code_change"]._require_confirmation is False
    assert by_name["promote_code_change"]._require_confirmation is True


def test_propose_code_change_function_body_never_references_promotion_code():
    """Chequeo AST (mismo criterio que la regla real ya existente en
    ai_editor: 'verificada por AST' para el boundary de graph_client) --
    confirma ESTRUCTURALMENTE que `propose_code_change` (el Tool SIN gate)
    no puede alcanzar `review_and_promote`/`promote_to_workspace` por
    ningun camino de codigo, no solo "no lo hace hoy"."""
    source = inspect.getsource(propose_code_change)
    tree = ast.parse(source)
    forbidden = {"review_and_promote", "promote_to_workspace", "WORKSPACE_ROOT"}
    found = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and node.id in forbidden
    } | {
        node.attr for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr in forbidden
    }
    assert not found, (
        f"propose_code_change referencia codigo de promocion: {found} -- "
        f"esta Tool NO debe poder alcanzar WORKSPACE_ROOT real."
    )


@pytest.mark.asyncio
async def test_propose_code_change_stores_a_pending_proposal_without_promoting():
    """run_autonomous_change_loop se mockea (ver limite de alcance en el
    docstring del modulo) -- lo que se prueba aqui es el MECANISMO del
    adapter (guardar el resultado, devolver un proposal_id), no el
    pipeline real de generacion."""
    fake_result = MagicMock(
        status="APPROVAL_REQUIRED", human_review_text="Cambio propuesto: X",
        warnings=[],
    )
    with patch("ai_editor.agent.run_autonomous_change_loop", return_value=fake_result) as mock_loop:
        out = propose_code_change("agregar validacion de X")

    mock_loop.assert_called_once_with("agregar validacion de X")
    assert out["status"] == "APPROVAL_REQUIRED"
    assert out["proposal_id"] in _PENDING_PROPOSALS
    assert _PENDING_PROPOSALS[out["proposal_id"]] is fake_result
    _PENDING_PROPOSALS.pop(out["proposal_id"], None)  # limpieza del registro de proceso


@pytest.mark.asyncio
async def test_promote_code_change_e2e_pauses_for_confirmation_and_never_writes_real_workspace():
    """Con Ollama REAL decidiendo: el LLM ve una propuesta pendiente y
    decide promoverla -- ADK debe pausar ANTES de que review_and_promote
    (mockeado, nunca la version real que toca WORKSPACE_ROOT) se ejecute."""
    from google.adk.features._feature_registry import FeatureName, override_feature_enabled
    override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)

    from google.genai import types
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.runners import InMemoryRunner

    proposal_id = "test-prop-001"
    _PENDING_PROPOSALS[proposal_id] = MagicMock(
        sandbox_loop_result=MagicMock(), context=MagicMock(), plan=MagicMock(),
    )

    with patch(
        "ai_editor.generation.promotion.review_and_promote", new=MagicMock(),
    ) as mock_promote:
        agent = LlmAgent(
            name="ai_editor_hitl_agent",
            model=LiteLlm(model="ollama_chat/llama3.1:8b", api_base="http://localhost:11434"),
            instruction=(
                f"Hay una propuesta de cambio de codigo pendiente con "
                f"proposal_id='{proposal_id}'. El usuario quiere aprobarla. "
                f"Usa promote_code_change con decision=APPROVE."
            ),
            tools=build_ai_editor_hitl_tools(),
        )
        runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc_ai_editor_hitl")
        user_id, session_id = "poc-editor-user", "poc-editor-session"
        await runner.session_service.create_session(
            app_name="sintel_adk_poc_ai_editor_hitl", user_id=user_id, session_id=session_id,
        )
        message = types.Content(role="user", parts=[types.Part(text="Aprueba el cambio propuesto.")])
        events = []
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message,
        ):
            events.append(event)

    assert not mock_promote.called, (
        "review_and_promote se ejecuto SIN confirmacion humana -- el gate "
        "require_confirmation no esta funcionando para ai_editor."
    )
    pending = [e for e in events if e.actions and e.actions.requested_tool_confirmations]
    assert pending, "Ningun evento senializo la pausa de confirmacion pendiente"

    _PENDING_PROPOSALS.pop(proposal_id, None)  # limpieza del registro de proceso
