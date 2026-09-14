"""
ADK-03 -- prueba de la CAPACIDAD `sub_agents`/transfer de ADK (POC, sigue
aislado). Ver AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 8ter -- este mecanismo
quedo confirmado como funcional, pero el usuario decidio explicitamente NO
usarlo para el routing de produccion (ADK-04): el routing real de Sintel es
100% deterministico (`action_graph.detect_business_intents` + `AgentRegistry.
route/apply_escalation`, regex-based, con reglas de seguridad como "una queja
SIEMPRE escala a soporte humano"), y delegar esa decision a un LLM violaria
la regla de la mision "ADK ORQUESTA. SINTEL EJECUTA Y CONTROLA". El runtime
real vive en `sintel_root_workflow.py::resolve_turn_agent()`, que usa el
router deterministico, NO `sub_agents`.

Este archivo se conserva porque prueba algo real y distinto: que
`LlmAgent.sub_agents` + transferencia LLM-driven via `transfer_to_agent`
funciona en ADK 2.9.0 (routing correcto sin cruces de dominio) -- una
capacidad del framework que podria ser util en otro punto de la mision
(ej. dentro de un unico agente de dominio con matices, no como router
principal), documentada aqui para no tener que re-descubrirla despues.

Hallazgo original que motivo este POC: la limitacion real de ADK 2.9.0
"Workflow cannot yet be used as an LlmAgent sub-agent" (ver
AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 0/5) NO aplica a este patron, porque
`sub_agents` es un mecanismo distinto y NO deprecado de `BaseAgent`, separado
del motor de grafo `Workflow` (candidato, sin decidir, para el pipeline mas
rigido de AI Editor en ADK-11, no para routing de negocio).

Construye un Root Agent minimo con 2 sub-agentes de dominio (support, sales)
y confirma que el LLM real (Ollama) delega al sub-agente correcto segun la
intencion del usuario. `support_agent` envuelve la tool REAL OrderStatusTool
via sintel_adapter (mismo mecanismo de ADK-02); `sales_agent` usa una tool
sintetica minima (no existe un dominio "sales"/product-search equivalente en
ai_engine hoy -- ver AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 1, los 9
perfiles reales son AccountAgent/AdminAgent/MarketingAgent/OrderAgent/
PaymentAgent/RentalAgent/SalesAgent/ServiceAgent/SupportAgent, y el
SalesAgent real no tiene busqueda de catalogo -- tiene promos/cotizaciones).
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
from google.adk.tools import FunctionTool

from sintel_adapter import SINTEL_TOKEN_STATE_KEY, SINTEL_USER_STATE_KEY, adapt_sintel_tool

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"


def _search_products(query: str) -> dict:
    """Tool sintetica -- Sales/catalogo NO existe en ai_engine hoy (ver
    AUDITORIA/ADK_MIGRATION_AUDIT.md), asi que a diferencia de ADK-02 (donde
    las 2 tools eran reales) esta es deliberadamente minima -- lo que este
    test verifica es el ROUTING del Root Agent, no una segunda tool real."""
    return {"products": [{"name": "Camara CCTV HD", "price": 250000}]}


def _build_root_agent(order_status_adk_tool):
    support_agent = LlmAgent(
        name="support_agent",
        model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
        description="Atiende consultas sobre pedidos existentes del cliente (estado, envio).",
        instruction="Usa OrderStatusTool para consultar pedidos. Nunca inventes datos.",
        tools=[order_status_adk_tool],
    )
    sales_agent = LlmAgent(
        name="sales_agent",
        model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
        description="Ayuda a clientes a buscar productos nuevos para comprar en el catalogo.",
        instruction="Usa search_products para buscar productos. Nunca inventes datos.",
        tools=[FunctionTool(_search_products)],
    )
    root_agent = LlmAgent(
        name="sintel_root_agent",
        model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
        description="Root agent de Sintel -- enruta al agente especializado correcto.",
        instruction=(
            "Eres el enrutador principal de Sintel. NUNCA respondas preguntas de "
            "negocio tu mismo -- SIEMPRE transfiere la conversacion al sub-agente "
            "apropiado: support_agent para preguntas sobre pedidos existentes, "
            "sales_agent para busqueda de productos nuevos."
        ),
        sub_agents=[support_agent, sales_agent],
    )
    return root_agent


async def _run_turn(root_agent, message_text: str, session_id: str):
    runner = InMemoryRunner(agent=root_agent, app_name="sintel_adk_poc_root")
    user_id = "poc-user-root"
    await runner.session_service.create_session(
        app_name="sintel_adk_poc_root", user_id=user_id, session_id=session_id,
        state={SINTEL_USER_STATE_KEY: {"id": 1}, SINTEL_TOKEN_STATE_KEY: "fake-jwt-root"},
    )
    message = types.Content(role="user", parts=[types.Part(text=message_text)])
    events = []
    async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=message):
        events.append(event)
    return events


@pytest.mark.asyncio
async def test_root_agent_delegates_order_question_to_support_agent():
    import tools.orders_tools as orders_tools
    from tools.registry import get_tool

    with patch(
        "tools.orders_tools.django_internal_get",
        new=AsyncMock(return_value={"results": [{"uuid": "ord-1", "status": "shipped"}]}),
    ):
        adk_tool = adapt_sintel_tool(get_tool("OrderStatusTool"))
        root_agent = _build_root_agent(adk_tool)

        events = await _run_turn(
            root_agent, "Cual es el estado de mi pedido?", session_id="root-session-1",
        )

    authors = [e.author for e in events]
    print(f"\n[POC ADK-03] Autores de los eventos (orden): {authors}")
    assert "support_agent" in authors, (
        f"El Root Agent nunca delego a support_agent -- autores reales: {authors}"
    )
    assert "sales_agent" not in authors, (
        f"El Root Agent delego incorrectamente a sales_agent para una pregunta de pedidos: {authors}"
    )


@pytest.mark.asyncio
async def test_root_agent_delegates_product_question_to_sales_agent():
    from tools.registry import get_tool

    with patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value={})):
        adk_tool = adapt_sintel_tool(get_tool("OrderStatusTool"))
        root_agent = _build_root_agent(adk_tool)

        events = await _run_turn(
            root_agent,
            "Quiero comprar una camara de seguridad nueva, que tienen disponible?",
            session_id="root-session-2",
        )

    authors = [e.author for e in events]
    print(f"[POC ADK-03] Autores de los eventos (orden): {authors}")
    assert "sales_agent" in authors, (
        f"El Root Agent nunca delego a sales_agent -- autores reales: {authors}"
    )
    assert "support_agent" not in authors, (
        f"El Root Agent delego incorrectamente a support_agent para una pregunta de catalogo: {authors}"
    )
