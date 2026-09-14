"""
detect_business_intents (action_graph.py) + AgentRegistry.route (agents/__init__.py).

Vocabulario y mapeo verificados manualmente contra BUSINESS_INTENT_PATTERNS/
INTENT_CAPABILITIES el 2026-08-08 (ver SUPPORT_AGENT_SPEC.md seccion 4) --
estos tests fijan ese vocabulario para que un cambio futuro que lo rompa
falle aqui, no en produccion. El caso "architecture_impact" (GraphImpactAnalysisTool)
se retiro 2026-08-10, FASE 0 -- ai_engine ya no importa project_knowledge_graph.
"""
import pytest

from action_graph import detect_business_intents
from agents import AgentRegistry


@pytest.mark.parametrize("message, expected_intent", [
    ("quiero cambiar la fecha de mi alquiler", "rental_change"),
    ("necesito cancelar mi solicitud de alquiler", "rental_cancel"),
    ("tengo una queja, quiero hablar con un agente", "support"),
    ("quiero una cotizacion para 5 camaras", "quote"),
    ("como hago para ser profesional en la plataforma", "kyc_upgrade"),
    ("donde esta mi pedido, cual es el tracking", "order_status"),
    ("cuales son mis alquileres activos", "rental_status"),
    ("quiero alquilar un equipo para el fin de semana", "renting_search"),
    ("mi tarjeta fue rechazada al pagar", "payment"),
    ("cuando llega el tecnico a mi visita de servicio", "service_status"),
    ("cual es el estado de mi verificacion de identidad", "kyc"),
    ("hay stock de ese producto", "stock"),
    ("tienen alguna promocion activa", "promos"),
    ("como funciona la garantia de los productos", "knowledge"),
    ("dame las metricas de ventas del dashboard", "marketing_admin"),
    ("que me recomiendas para mi perfil", "personal_recommendation"),
    ("ese equipo esta bloqueado por mantenimiento", "maintenance_check"),
    ("quiero editar el banner del home", "core_content"),
    ("hola buenas tardes", "unknown"),
])
def test_detect_business_intents_vocabulario(message, expected_intent):
    intents = detect_business_intents(message)
    assert expected_intent in intents


@pytest.mark.parametrize("intent, expected_agent", [
    ("support", "SupportAgent"),
    ("rental_change", "SupportAgent"),
    ("unknown", "SupportAgent"),
    ("kyc", "AccountAgent"),
    ("kyc_upgrade", "AccountAgent"),
    ("core_content", "AdminAgent"),
    ("maintenance_check", "AdminAgent"),
    ("marketing_admin", "MarketingAgent"),
    ("personal_recommendation", "MarketingAgent"),
    ("order_status", "OrderAgent"),
    ("payment", "PaymentAgent"),
    ("rental_status", "RentalAgent"),
    ("renting_search", "RentalAgent"),
    ("rental_cancel", "RentalAgent"),
    ("stock", "RentalAgent"),
    ("promos", "SalesAgent"),
    ("quote", "SalesAgent"),
    ("knowledge", "SalesAgent"),
    ("service_status", "ServiceAgent"),
])
def test_agent_registry_route(intent, expected_agent):
    agent = AgentRegistry.route(intent)
    assert agent.name == expected_agent


def test_intent_desconocido_cae_a_unknown():
    """Un mensaje que no matchea ningun regex nunca debe quedar sin intent."""
    intents = detect_business_intents("asdkjhaskjdh contenido sin sentido 12345")
    assert intents == ["unknown"]
