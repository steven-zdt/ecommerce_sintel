"""
ADK-02 -- prueba del gate HITL (require_confirmation) con una Tool REAL de
ai_engine que SI lo declara: RequestKycUpgradeTool (side_effects=True,
requires_confirmation=True, ai_engine/tools/kyc_tools.py). Confirma que el
mapeo ToolMetadata.requires_confirmation -> FunctionTool(require_confirmation=)
efectivamente PAUSA la ejecucion antes de llegar a django_internal_post --
no solo que el flag estructural quedo seteado (eso ya lo cubre
test_adk_poc.py::test_function_tool_supports_require_confirmation con una
tool sintetica).
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
async def test_write_tool_with_confirmation_pauses_before_real_write():
    import tools.kyc_tools as kyc_tools
    from tools.registry import get_tool

    registered = get_tool("RequestKycUpgradeTool")
    assert registered is not None
    assert registered.metadata.requires_confirmation is True
    assert registered.metadata.side_effects is True

    with patch(
        "tools.kyc_tools.django_internal_post", new=AsyncMock(return_value={"ok": True}),
    ) as mock_write:
        adk_tool = adapt_sintel_tool(registered)
        assert adk_tool._require_confirmation is True

        agent = LlmAgent(
            name="kyc_agent",
            model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
            instruction=(
                "Eres un asistente que ayuda a clientes a solicitar el upgrade a perfil "
                "profesional TECHNICIAN cuando lo pidan."
            ),
            tools=[adk_tool],
        )
        runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc_hitl")
        user_id, session_id = "poc-user-3", "poc-session-3"
        await runner.session_service.create_session(
            app_name="sintel_adk_poc_hitl", user_id=user_id, session_id=session_id,
            state={
                SINTEL_USER_STATE_KEY: {"id": 7},
                SINTEL_TOKEN_STATE_KEY: "fake-jwt-write",
            },
        )

        message = types.Content(
            role="user",
            parts=[types.Part(text="Quiero solicitar el upgrade a perfil TECHNICIAN.")],
        )
        events = []
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message,
        ):
            events.append(event)
            print(
                f"[POC ADK-02 HITL] event author={event.author} "
                f"requested_confirmations={event.actions.requested_tool_confirmations} "
                f"text={(event.content.parts[0].text if event.content and event.content.parts else None)!r}"
            )

    # El punto central del gate: la escritura real NUNCA debe ejecutarse sin
    # que algo (aqui: nadie) haya confirmado -- el mismo principio estructural
    # que ai_editor.repository.promote_to_workspace() ya exige del lado
    # Sintel (ver AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 4).
    assert not mock_write.called, (
        "La tool de escritura (RequestKycUpgradeTool) se ejecuto SIN "
        "confirmacion -- el gate require_confirmation no esta funcionando"
    )
    pending = [
        e for e in events
        if e.actions and e.actions.requested_tool_confirmations
    ]
    assert pending, (
        "Ningun evento trajo requested_tool_confirmations -- ADK no señalizo "
        "la pausa de confirmacion pendiente"
    )
