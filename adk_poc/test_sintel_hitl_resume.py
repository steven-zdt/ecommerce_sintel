"""
ADK-11 (ejecucion) -- prueba empirica del flujo de RESUME de una
confirmacion pausada, pendiente desde ADK-02 (nunca se habia probado, solo
la mitad "pausa"). Necesario para construir el /chat real de
ai_engine_adk/ (ChatRequest.confirm debe poder reanudar una escritura real
pendiente).
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
from google.adk.tools.tool_confirmation import ToolConfirmation

from sintel_adapter import SINTEL_TOKEN_STATE_KEY, SINTEL_USER_STATE_KEY, adapt_sintel_tool

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"


@pytest.mark.asyncio
async def test_resume_confirmed_true_actually_executes_the_real_write():
    from tools.registry import get_tool

    registered = get_tool("RequestKycUpgradeTool")
    with patch(
        "tools.kyc_tools.django_internal_post", new=AsyncMock(return_value={"ok": True}),
    ) as mock_write:
        adk_tool = adapt_sintel_tool(registered)
        agent = LlmAgent(
            name="kyc_agent",
            model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
            instruction="Ayuda a solicitar el upgrade a perfil TECHNICIAN cuando lo pidan.",
            tools=[adk_tool],
        )
        runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc_resume")
        user_id, session_id = "poc-resume-user", "poc-resume-session"
        await runner.session_service.create_session(
            app_name="sintel_adk_poc_resume", user_id=user_id, session_id=session_id,
            state={SINTEL_USER_STATE_KEY: {"id": 7}, SINTEL_TOKEN_STATE_KEY: "fake-jwt"},
        )

        # Turno 1: dispara la pausa.
        message = types.Content(role="user", parts=[types.Part(
            text="Quiero solicitar el upgrade a perfil TECHNICIAN.",
        )])
        events = []
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
            events.append(event)
            print(f"[RESUME] evento author={event.author} confirmations={event.actions.requested_tool_confirmations if event.actions else None} long_running={event.long_running_tool_ids} fcs={[(fc.id, fc.name) for fc in event.get_function_calls()]}")

        assert not mock_write.called

        # Hallazgo real (no documentado en el docstring publico, verificado
        # con eventos reales): ADK emite un evento SINTETICO separado
        # ("adk_request_confirmation", generado por
        # functions.py::generate_request_confirmation_event) cuyo PROPIO id
        # queda en `event.long_running_tool_ids` -- ESE id es el que hay que
        # usar en el FunctionResponse de resume, NO la clave (id de la
        # llamada ORIGINAL) del dict `requested_tool_confirmations`.
        long_running_events = [e for e in events if e.long_running_tool_ids]
        assert long_running_events, "Ningun evento trajo long_running_tool_ids"
        confirmation_fc_id = next(iter(long_running_events[-1].long_running_tool_ids))
        print(f"[RESUME] confirmation_fc_id real (evento sintetico): {confirmation_fc_id!r}")

        # Turno 2 (RESUME): FunctionResponse dirigido al FC SINTETICO de
        # confirmacion, con ToolConfirmation(confirmed=True) como payload.
        confirmation = ToolConfirmation(confirmed=True)
        resume_message = types.Content(
            role="user",
            parts=[types.Part(function_response=types.FunctionResponse(
                id=confirmation_fc_id,
                name="adk_request_confirmation",
                response=confirmation.model_dump(),
            ))],
        )
        resume_events = []
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=resume_message,
        ):
            resume_events.append(event)
            print(f"[RESUME] (turno 2) evento author={event.author} text={(event.content.parts[0].text if event.content and event.content.parts and event.content.parts[0].text else None)!r}")

    assert mock_write.called, (
        "El resume con confirmed=True no disparo la escritura real -- "
        "el flujo de RESUME no funciona como se espera"
    )


@pytest.mark.asyncio
async def test_resume_confirmed_false_never_executes_the_real_write():
    """Contraparte de seguridad del test anterior: rechazar la confirmacion
    debe dejar la escritura real SIN ejecutar, no solo "confirmar que
    funciona cuando se aprueba"."""
    from tools.registry import get_tool

    registered = get_tool("RequestKycUpgradeTool")
    with patch(
        "tools.kyc_tools.django_internal_post", new=AsyncMock(return_value={"ok": True}),
    ) as mock_write:
        adk_tool = adapt_sintel_tool(registered)
        agent = LlmAgent(
            name="kyc_agent",
            model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
            instruction="Ayuda a solicitar el upgrade a perfil TECHNICIAN cuando lo pidan.",
            tools=[adk_tool],
        )
        runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc_resume_reject")
        user_id, session_id = "poc-reject-user", "poc-reject-session"
        await runner.session_service.create_session(
            app_name="sintel_adk_poc_resume_reject", user_id=user_id, session_id=session_id,
            state={SINTEL_USER_STATE_KEY: {"id": 7}, SINTEL_TOKEN_STATE_KEY: "fake-jwt"},
        )

        message = types.Content(role="user", parts=[types.Part(
            text="Quiero solicitar el upgrade a perfil TECHNICIAN.",
        )])
        events = []
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
            events.append(event)

        long_running_events = [e for e in events if e.long_running_tool_ids]
        assert long_running_events
        confirmation_fc_id = next(iter(long_running_events[-1].long_running_tool_ids))

        confirmation = ToolConfirmation(confirmed=False)
        resume_message = types.Content(
            role="user",
            parts=[types.Part(function_response=types.FunctionResponse(
                id=confirmation_fc_id, name="adk_request_confirmation",
                response=confirmation.model_dump(),
            ))],
        )
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=resume_message,
        ):
            pass

    assert not mock_write.called, (
        "El resume con confirmed=False SI disparo la escritura real -- "
        "regresion de seguridad grave"
    )
