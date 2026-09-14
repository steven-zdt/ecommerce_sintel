"""
ADK-05 -- prueba end-to-end (Ollama real) de que el fix de seguridad del
adapter funciona en la practica, no solo a nivel de firma.

Motivo (ver test_adk05_tool_registry_audit.py para el detalle completo):
`open_support_ticket_tool` tiene un parametro real `history` que
DELIBERADAMENTE no debe llegar al LLM -- lo inyecta el grafo (Human
Handoff), nunca el usuario/LLM. Esta prueba confirma que, incluso con
Ollama real decidiendo que argumentos pasar, la tool se ejecuta
correctamente sin `history` -- el LLM ni siquiera sabe que existe.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel" / "ai_engine"
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))

from google.adk.features._feature_registry import FeatureName, override_feature_enabled

override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)

from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner

from sintel_adapter import SINTEL_TOKEN_STATE_KEY, SINTEL_USER_STATE_KEY, adapt_sintel_tool

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"


@pytest.mark.asyncio
async def test_open_support_ticket_tool_e2e_never_receives_llm_supplied_history():
    import tools.support_tools as support_tools
    from tools.registry import get_tool

    registered = get_tool("OpenSupportTicketTool")
    assert registered is not None
    assert registered.func is support_tools.open_support_ticket_tool

    with patch(
        "tools.support_tools.django_internal_post",
        new=AsyncMock(return_value={"room_uuid": "room-1", "ok": True}),
    ) as mock_post:
        adk_tool = adapt_sintel_tool(registered)

        agent = LlmAgent(
            name="support_agent",
            model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
            instruction=(
                "Eres un agente de soporte. El cliente tiene una queja. Usa "
                "OpenSupportTicketTool para abrir un ticket con un resumen "
                "breve del caso."
            ),
            tools=[adk_tool],
        )
        runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc_hidden_param")
        user_id, session_id = "poc-user-hidden", "poc-session-hidden"
        await runner.session_service.create_session(
            app_name="sintel_adk_poc_hidden_param", user_id=user_id, session_id=session_id,
            state={
                SINTEL_USER_STATE_KEY: {"id": 9},
                SINTEL_TOKEN_STATE_KEY: "fake-jwt-hidden",
            },
        )

        message = types.Content(
            role="user",
            parts=[types.Part(text=(
                "Estoy muy molesto, mi pedido llego danado y nadie me ha "
                "respondido. Necesito hablar con un humano."
            ))],
        )
        events = []
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message,
        ):
            events.append(event)

    print(f"\n[ADK-05] mock_post.called={mock_post.called}")
    assert mock_post.called, "OpenSupportTicketTool nunca ejecuto -- el LLM no llamo la tool"

    call_args = mock_post.call_args
    body = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("body")
    print(f"[ADK-05] body real enviado a Django: {body}")
    assert "message" in body, "El campo real requerido 'message' no llego"
    assert "history" not in body, (
        "'history' llego al body real -- el LLM pudo haberlo inventado porque "
        "el wrapper se lo expuso, violando el boundary real del sistema "
        "(history solo lo inyecta el grafo, nunca el LLM)"
    )
