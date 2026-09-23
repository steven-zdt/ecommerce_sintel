"""
AgentRegistry.apply_escalation (agents/__init__.py) -- handoff agente-a-agente
dentro del mismo turno (Fase 6 / Componente del plan). Cada agente no-Support
declara reglas_escalamiento propias en su profiles/*.yaml; SupportAgent es el
unico sin reglas (destino terminal).
"""
from agents import AgentRegistry


def test_sales_agent_escala_a_support_por_queja():
    sales = AgentRegistry.get("SalesAgent")
    assert sales is not None
    escalated = AgentRegistry.apply_escalation(sales, "estoy muy molesto, esto es inaceptable")
    assert escalated.name == "SupportAgent"


def test_rental_agent_escala_a_support_por_reclamo():
    rental = AgentRegistry.get("RentalAgent")
    assert rental is not None
    escalated = AgentRegistry.apply_escalation(rental, "es la segunda vez que me pasa esto, otra vez no")
    assert escalated.name == "SupportAgent"


def test_admin_agent_escala_a_support_por_eliminar():
    admin = AgentRegistry.get("AdminAgent")
    assert admin is not None
    escalated = AgentRegistry.apply_escalation(admin, "quiero eliminar todos los banners")
    assert escalated.name == "SupportAgent"


def test_catalog_agent_escala_a_support_por_eliminar():
    catalog = AgentRegistry.get("CatalogAgent")
    assert catalog is not None
    escalated = AgentRegistry.apply_escalation(catalog, "quiero eliminar este producto")
    assert escalated.name == "SupportAgent"


def test_catalog_agent_no_escala_por_publicar():
    """CatalogProductSetPublishedStateTool (Nivel 3) ya existe con
    requires_confirmation=True -- publicar ahora es HITL real via ADK
    (ver test_tool_policy_matrix.py para la cobertura de esa confirmacion),
    no una derivacion a un humano."""
    catalog = AgentRegistry.get("CatalogAgent")
    assert catalog is not None
    result = AgentRegistry.apply_escalation(catalog, "ya publica el producto que acabamos de crear")
    assert result.name == "CatalogAgent"


def test_agente_sin_match_no_escala():
    """Un mensaje neutral no debe disparar ninguna regla de escalamiento."""
    order = AgentRegistry.get("OrderAgent")
    assert order is not None
    result = AgentRegistry.apply_escalation(order, "cual es el estado de mi pedido")
    assert result.name == "OrderAgent"


def test_support_agent_es_terminal_no_escala_mas():
    """SupportAgent tiene reglas_escalamiento=[] -- es el destino final, nunca
    reenvia a otro agente aunque el mensaje matchee el patron de otro perfil."""
    support = AgentRegistry.get("SupportAgent")
    assert support is not None
    assert support.reglas_escalamiento == []
    result = AgentRegistry.apply_escalation(support, "estoy muy molesto, quiero un reclamo")
    assert result.name == "SupportAgent"


def test_los_10_agentes_estan_registrados():
    """CatalogAgent se agrego en la Fase 3 del Admin AI Assistant (2026-09-16,
    vertical piloto Catalogo) -- 10 perfiles desde entonces, antes 9."""
    nombres = {a.name for a in AgentRegistry.list_all()}
    assert nombres == {
        "SupportAgent", "AccountAgent", "AdminAgent", "CatalogAgent", "MarketingAgent",
        "OrderAgent", "PaymentAgent", "RentalAgent", "SalesAgent", "ServiceAgent",
    }
