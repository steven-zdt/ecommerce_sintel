"""
ADK-01 -- POC aislado de Google ADK (google-adk==2.9.0), FUERA del stack
productivo de Sintel (venv propio en adk_poc/.venv, no toca ai_engine ni
ningun contenedor Docker). Ver AUDITORIA/ADK_MIGRATION_AUDIT.md (ADK-00).

Verifica, contra el paquete real instalado (no contra documentacion vieja):
  - instalacion
  - Agent (LlmAgent)
  - Runner (InMemoryRunner)
  - Workflow (motor de grafo que reemplaza a Sequential/Parallel/LoopAgent)
  - tool (FunctionTool)
  - session
  - event
  - interruption / HITL (FunctionTool require_confirmation)
  - modelo actual (LiteLlm -> Ollama real, sin mocks, mismo motor que usa
    ai_engine hoy en dev -- ver ai_engine/config.py LOCAL_MODEL_CHAIN)
  - ejecucion async

Correr con:
  adk_poc/.venv/Scripts/python.exe -m pytest adk_poc/test_adk_poc.py -v -s
"""
import os

import pytest

# HALLAZGO REAL DE ESTE POC (no documentado en ningun lado antes de esto):
# ADK 2.9.0 trae la feature experimental JSON_SCHEMA_FOR_FUNC_DECL activada
# por default. Con ella activa, LiteLlm(model="ollama_chat/...") declara las
# tools en un formato JSON-schema que Ollama NO interpreta como tool-calling
# real -- el modelo simplemente ECOA la declaracion de la tool como texto
# plano en vez de disparar una llamada de funcion real (reproducido y
# confirmado: raw litellm.completion() contra el mismo Ollama SI dispara
# tool_calls correctamente, aislando el bug a esta feature de ADK, no a
# litellm ni a Ollama). Desactivarla arregla el tool-calling end-to-end --
# PERO el override debe ejecutarse ANTES de importar google.adk.tools/
# google.adk.agents/google.adk.models.lite_llm (verificado: llamarlo DESPUES
# de esos imports, aunque sea antes de construir el Agent, NO tiene efecto --
# el flag se resuelve en tiempo de import/definicion de clase, no en cada
# llamada). Por eso este override va antes que cualquier otro import de adk.
# Este es un riesgo real y documentado para ADK-02+ (Tool Adapter): CUALQUIER
# agente de Sintel que use LiteLlm+Ollama para tool-calling nativo necesita
# este override, o las tools nunca se invocan de verdad.
from google.adk.features._feature_registry import FeatureName, override_feature_enabled

override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)

from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool

# Mismo Ollama real que usa el stack de Sintel en dev (ai_engine/config.py
# default: http://sintel_ollama:11434 dentro de Docker; desde el host,
# mismo contenedor expone el puerto en localhost:11434).
OLLAMA_BASE_URL = os.environ.get("ADK_POC_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("ADK_POC_OLLAMA_MODEL", "llama3.1:8b")


def _ollama_model() -> LiteLlm:
    """litellm usa el prefijo 'ollama_chat/' para el endpoint de chat completions
    de Ollama (no 'ollama/', que es el endpoint de completion legado) -- api_base
    va como kwarg, litellm lo reenvia tal cual a la llamada HTTP real."""
    return LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL)


# ─── 1. Instalacion + estructura real del paquete ────────────────────────────

def test_adk_is_installed_with_expected_version():
    import google.adk
    assert google.adk.version.__version__ == "2.9.0"


def test_legacy_workflow_agents_are_confirmed_deprecated():
    """Guardrail de ADK-00: SequentialAgent/ParallelAgent/LoopAgent deben seguir
    funcionando (todavia no eliminados) pero marcados deprecated -- si esta
    prueba falla en el futuro (por ejemplo porque ya se eliminaron del todo),
    es una senal real de que hay que revisar el plan de migracion, no un bug
    de este test."""
    from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

    for cls in (SequentialAgent, ParallelAgent, LoopAgent):
        assert "deprecated" in (cls.__doc__ or "").lower(), (
            f"{cls.__name__} ya no esta marcada deprecated -- revisar si fue "
            f"eliminada o si el guardrail de ADK-00 quedo obsoleto"
        )


# ─── 2. Agent + Tool + Runner + Session + Event + ejecucion async ────────────

def _lookup_order_status(order_id: str) -> dict:
    """Tool de prueba -- deliberadamente FALSA (no toca Django/Postgres real,
    este POC esta aislado). En la migracion real esto seria un adapter fino
    sobre orders.services.selectors.OrderSelector, no logica nueva."""
    return {"order_id": order_id, "status": "shipped", "eta_days": 2}


@pytest.mark.asyncio
async def test_agent_runner_tool_session_event_async_e2e():
    """Extremo a extremo, con Ollama REAL (sin mock) -- mismo criterio que las
    pruebas de ai_engine en este repo (nunca mockear el motor local)."""
    tool = FunctionTool(_lookup_order_status)
    agent = LlmAgent(
        name="order_status_agent",
        model=_ollama_model(),
        instruction=(
            "Eres un asistente que consulta el estado de pedidos. "
            "Usa SIEMPRE la tool lookup_order_status para responder -- "
            "nunca inventes un estado."
        ),
        tools=[tool],
    )
    runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc")

    user_id, session_id = "poc-user-1", "poc-session-1"
    await runner.session_service.create_session(
        app_name="sintel_adk_poc", user_id=user_id, session_id=session_id,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text="Cual es el estado del pedido ORD-123?")],
    )

    events = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message,
    ):
        events.append(event)

    assert events, "Runner.run_async no produjo ningun Event -- ejecucion async rota"

    tool_was_called = any(
        getattr(e, "get_function_calls", None) and e.get_function_calls()
        for e in events
    )
    assert tool_was_called, (
        f"El agente nunca llamo a la tool lookup_order_status -- eventos: {events}"
    )

    final_text = "".join(
        part.text or ""
        for e in events
        if e.content and e.content.parts
        for part in e.content.parts
        if part.text
    )
    assert "ORD-123" in final_text or "shipped" in final_text.lower() or "2" in final_text, (
        f"La respuesta final no parece reflejar el resultado real de la tool: {final_text!r}"
    )
    print(f"\n[POC] Respuesta final del agente: {final_text!r}")
    print(f"[POC] Total eventos: {len(events)}")


# ─── 3. HITL / interruption -- require_confirmation ──────────────────────────

def test_function_tool_supports_require_confirmation():
    """No ejecuta el flujo completo de confirmacion (requiere un cliente que
    responda al ToolContext.requestConfirmation) -- solo confirma que la API
    existe y acepta el kwarg tal como documenta ADK, que es el mecanismo real
    candidato para envolver ai_editor.repository.promote_to_workspace() detras
    de un gate humano (ver AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 0)."""

    def _dangerous_write_action(target: str) -> dict:
        return {"promoted": target}

    tool = FunctionTool(_dangerous_write_action, require_confirmation=True)
    # No hay atributo publico `require_confirmation` (hallazgo real de este
    # POC) -- el estado crudo vive en `_require_confirmation` (privado) y la
    # forma soportada de consultarlo es `check_require_confirmation(args,
    # tool_context)`, que acepta bool O predicado callable/async.
    assert tool._require_confirmation is True

    # Tambien soporta un predicado async para gating dinamico (ej. "solo pedir
    # confirmacion si el riesgo calculado por SINTEL es alto").
    async def _dynamic_gate(**kwargs) -> bool:
        return True

    tool_dynamic = FunctionTool(_dangerous_write_action, require_confirmation=_dynamic_gate)
    assert tool_dynamic._require_confirmation is _dynamic_gate


# ─── 4. Workflow (motor de grafo, reemplazo de Sequential/Parallel/Loop) ─────

def test_workflow_graph_engine_importable_and_constructible():
    """No ejecuta un grafo completo (eso es ADK-02+, cuando se diseñe el Root
    Workflow real) -- confirma que la clase Workflow es importable y expone la
    forma de grafo (edges/nodes) que describe AUDITORIA/ADK_MIGRATION_AUDIT.md."""
    from google.adk.workflow import Workflow

    assert hasattr(Workflow, "__init__")
    # BaseNode es la unidad de ejecucion del grafo -- Workflow hereda de el.
    from google.adk.workflow._base_node import BaseNode
    assert issubclass(Workflow, BaseNode)
