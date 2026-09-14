"""
ADK-07 -- Knowledge Graph adapter, probado contra el grafo REAL del repo
(sin mocks -- son operaciones de solo lectura, cero riesgo de escritura).

`get_graph_status()` real confirma que el grafo esta construido y poblado
(9575 nodos, 20335 aristas, 23 apps) -- estos tests consultan ese grafo tal
cual esta hoy, no una version sintetica.
"""
import inspect
import sys
from pathlib import Path

import pytest

ECOMMERCE_SINTEL_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel"
if str(ECOMMERCE_SINTEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ECOMMERCE_SINTEL_ROOT))

from sintel_graph_adapter import _ENGINEERING_QA_OPERATIONS, adapt_graph_operation, build_engineering_qa_tools


def test_adapted_tool_names_match_the_canonical_graph_client_operation_names():
    """Hallazgo real: el __name__ propio de la funcion real de graph_sdk no
    siempre coincide con el alias que graph_client exporta (ej.
    calculate_impact.__name__ == 'calculate_change_impact'). El wrapper debe
    normalizar esto -- si no, el LLM veria un nombre de tool distinto al
    documentado."""
    tools = build_engineering_qa_tools()
    names = {t.name for t in tools}
    assert names == set(_ENGINEERING_QA_OPERATIONS)


def test_adapt_graph_operation_rejects_operations_outside_the_readonly_subset():
    """resolve_change/build_change_plan (pipeline de PROPUESTA de cambio, no
    de consulta ad-hoc) NO deben quedar disponibles via este adapter -- ese
    flujo ya lo cubre ai_editor.agent.run_autonomous_change_loop."""
    with pytest.raises(ValueError):
        adapt_graph_operation("resolve_change")
    with pytest.raises(ValueError):
        adapt_graph_operation("build_change_plan")


def test_calculate_impact_tool_queries_the_real_graph_for_a_real_model():
    """Sin mocks: consulta el grafo real para el modelo Order (orders/models.py,
    confirmado real via get_app_summary en la investigacion de ADK-07).
    Cero riesgo de escritura -- calculate_impact es de solo lectura."""
    tool = adapt_graph_operation("calculate_impact")
    result = tool.func(target="Order")
    assert result["found"] is True
    assert result["target"]["name"] == "Order"
    assert result["target"]["app"] == "orders"


def test_get_graph_status_tool_never_returns_the_full_graph_only_a_summary():
    """Verifica en vivo la afirmacion del docstring del adapter: incluso la
    operacion mas 'amplia' de las 9 nunca serializa el grafo completo --
    devuelve conteos/resumen, no los 9575 nodos reales uno por uno."""
    tool = adapt_graph_operation("get_graph_status")
    result = tool.func()
    assert result["kg_nodes"] > 1000  # el grafo real es grande...
    assert "kg_node_types" not in result or isinstance(result["kg_node_types"], dict)
    # ...pero la respuesta en si es un resumen acotado, no una lista de nodos:
    assert not any(isinstance(v, list) and len(v) > 50 for v in result.values())


@pytest.mark.asyncio
async def test_engineering_agent_e2e_answers_a_real_question_from_the_real_graph():
    """POC de un futuro EngineeringAgent (propuesto por el usuario, no un
    perfil real todavia -- a diferencia de los 9 Support Agent profiles de
    ADK-04/05): con Ollama REAL, responde una pregunta de ingenieria ad-hoc
    usando las tools del grafo real, sin mocks -- cero riesgo, son consultas
    de solo lectura contra datos ya construidos del repo."""
    from google.adk.features._feature_registry import FeatureName, override_feature_enabled
    override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)

    from google.genai import types
    from google.adk.agents import LlmAgent
    from google.adk.models.lite_llm import LiteLlm
    from google.adk.runners import InMemoryRunner

    agent = LlmAgent(
        name="engineering_agent",
        model=LiteLlm(model="ollama_chat/llama3.1:8b", api_base="http://localhost:11434"),
        instruction=(
            "Eres un asistente de ingenieria que responde preguntas sobre el "
            "codigo real de Sintel. Usa SIEMPRE get_app_summary para resumir "
            "una app cuando te pregunten que contiene -- nunca inventes "
            "modelos o endpoints que no vengan de la tool."
        ),
        tools=build_engineering_qa_tools(),
    )
    runner = InMemoryRunner(agent=agent, app_name="sintel_adk_poc_engineering")
    user_id, session_id = "poc-eng-user", "poc-eng-session"
    await runner.session_service.create_session(
        app_name="sintel_adk_poc_engineering", user_id=user_id, session_id=session_id,
    )

    message = types.Content(
        role="user",
        parts=[types.Part(text="Que modelos reales tiene la app orders?")],
    )
    events = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=message,
    ):
        events.append(event)

    final_text = "".join(
        part.text or "" for e in events if e.content and e.content.parts
        for part in e.content.parts if part.text
    )
    print(f"\n[ADK-07] respuesta: {final_text!r}")
    assert "Order" in final_text or "Coupon" in final_text or "Shipment" in final_text, (
        f"La respuesta no menciona ningun modelo real de la app orders "
        f"(Order/Coupon/Shipment) -- posible alucinacion en vez de datos "
        f"reales del grafo: {final_text!r}"
    )
