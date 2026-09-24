"""F11 -- suplantacion de administrador: la autorizacion sale de la identidad real (Django), no del texto."""
import pytest

import sintel_root_workflow as wf
from agents import AgentRegistry
from permissions import user_lacks_admin_permission
from tools import registry

from ._cases import attack_params

ADMIN_TOOL_NAMES = {n for name in wf._ADMIN_AGENT_NAMES for n in AgentRegistry.get(name).herramientas}
ADMIN_WRITES = sorted(n for n in ADMIN_TOOL_NAMES if registry.get_tool(n) and registry.get_tool(n).metadata.side_effects)


@pytest.mark.parametrize("category,kind,text", attack_params(categories={"role_impersonation", "tool_escalation", "fake_system_message"}))
def test_el_routing_de_cliente_nunca_alcanza_escrituras_admin_sin_permiso(category, kind, text):
    intent, agent, _ = wf.resolve_turn_agent(text, source="customer")
    if agent in wf._ADMIN_AGENT_NAMES:
        for name in AgentRegistry.get(agent).herramientas:
            meta = registry.get_tool(name).metadata
            if meta.side_effects:
                assert "IsAdminUser" in meta.permissions, f"{name} sin IsAdminUser alcanzable por routing de cliente"


@pytest.mark.parametrize("name", ADMIN_WRITES)
def test_toda_escritura_del_agente_admin_exige_admin(name):
    assert "IsAdminUser" in registry.get_tool(name).metadata.permissions


@pytest.mark.parametrize("user", [{}, {"is_staff": False}, {"is_staff": None}, {"is_staff": 0}, {"is_staff": ""}])
def test_un_usuario_sin_staff_real_es_denegado(user):
    assert user_lacks_admin_permission(["IsAdminUser"], user) is True


def test_source_admin_nunca_cae_en_un_agente_de_cliente():
    for msg in ("hola", "que me recomiendas", "necesito ayuda con un pago", "donde esta mi pedido"):
        intent, agent, _ = wf.resolve_turn_agent(msg, source="admin")
        assert agent in wf._ADMIN_AGENT_NAMES or (agent == "MarketingAgent" and intent == "marketing_admin") or agent == "SupportAgent"
