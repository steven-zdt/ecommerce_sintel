"""
ADK-02 -- prueba del SINTEL Tool Adapter contra una Tool REAL de ai_engine
(OrderStatusTool, ai_engine/tools/orders_tools.py), importada via sys.path
(NO copiada, NO reescrita) desde este venv aislado.

`tools.http_bridge.django_internal_get` se mockea (mismo criterio que la
propia suite de ai_engine, ver ai_engine/tests/test_dynamic_llm_config.py --
"httpx.AsyncClient se mockea, no hay respx instalado") para no depender de un
Django real corriendo; todo lo demas (ToolMetadata, ToolContext, ToolRegistry,
la funcion order_status_tool en si) es codigo real de ai_engine, sin mocks.

Correr con:
  adk_poc/.venv/Scripts/python.exe -m pytest adk_poc/test_sintel_adapter.py -v -s
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
async def test_adapted_real_sintel_tool_is_actually_invoked_via_adk():
    """Extremo a extremo real: LLM (Ollama) -> ADK FunctionTool -> adapter ->
    tools.orders_tools.order_status_tool REAL -> tools.http_bridge.
    django_internal_get (mockeado, unico punto no-real) -- confirma que el
    adapter no duplica logica, delega en el codigo real de ai_engine."""
    import tools.orders_tools as orders_tools
    from tools.registry import get_tool

    registered = get_tool("OrderStatusTool")
    assert registered is not None, "OrderStatusTool no se registro -- el import real fallo"
    assert registered.func is orders_tools.order_status_tool, (
        "El adapter debe envolver la funcion REAL, no una copia"
    )

    mock_response = {
        "results": [{"uuid": "ord-real-123", "status": "shipped", "total": "150000.00"}],
    }
    # Se parchea donde SE USA (tools.orders_tools), no donde se define
    # (tools.http_bridge) -- orders_tools.py hace `from tools.http_bridge
    # import django_internal_get`, asi que tiene su propia referencia local
    # vinculada en tiempo de import; parchear el modulo origen no la afecta
    # (gotcha real de mocking en Python, no un bug del adapter -- confirmado
    # en la primera corrida de este test: sin este fix, la tool SI se
    # invocaba de verdad y llegaba a intentar una llamada de red real a
    # http://django:8000, que fallo con gracia -- prueba independiente de que
    # el adapter invoca el codigo real).
    with patch(
        "tools.orders_tools.django_internal_get",
        new=AsyncMock(return_value=mock_response),
    ) as mock_bridge:
        adk_tool = adapt_sintel_tool(registered)

        agent = LlmAgent(
            name="orders_agent",
            model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
            instruction=(
                "Eres un asistente que consulta pedidos. Usa SIEMPRE la tool "
                "OrderStatusTool para responder, nunca inventes datos."
            ),
            tools=[adk_tool],
        )
        runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc_adapter")

        user_id, session_id = "poc-user-2", "poc-session-2"
        await runner.session_service.create_session(
            app_name="sintel_adk_poc_adapter",
            user_id=user_id,
            session_id=session_id,
            state={
                SINTEL_USER_STATE_KEY: {"id": 42, "email": "cliente@sintel.dev"},
                SINTEL_TOKEN_STATE_KEY: "fake-jwt-para-el-poc",
            },
        )

        message = types.Content(
            role="user", parts=[types.Part(text="Cual es el estado de mis pedidos?")],
        )
        events = []
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message,
        ):
            events.append(event)

    # La tool REAL de ai_engine SI se invoco (no un stand-in del adapter).
    assert mock_bridge.called, "django_internal_get nunca se llamo -- el adapter no invoco la tool real"
    call_args = mock_bridge.call_args
    token_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("token")
    assert token_arg == "fake-jwt-para-el-poc", (
        f"El token de ToolContext.state de ADK no llego a la tool real de Sintel: {call_args}"
    )
    assert call_args.args[1] == "/orders/" or call_args.kwargs.get("path") == "/orders/"

    final_text = "".join(
        part.text or ""
        for e in events
        if e.content and e.content.parts
        for part in e.content.parts
        if part.text
    )
    print(f"\n[POC ADK-02] Respuesta final: {final_text!r}")
    print(f"[POC ADK-02] django_internal_get llamado con: {call_args}")
    assert final_text, "El agente no genero respuesta final"
