"""
ADK-05 -- auditoria sistematica del adapter contra el REGISTRO COMPLETO real
de ai_engine.tools (29 tools, confirmado con tools.list_tools() en vivo).

ADK-04 ya demostro que los 9 perfiles reales construyen su LlmAgent sin
excepciones (33 instancias de tool, con reuso entre perfiles). Lo que
faltaba -- y es el alcance real de ADK-05 dado que "migrar tools 1 a 1" ya
esta cubierto por construccion -- es verificar, para CADA una de las 29
tools registradas, que la superficie que el wrapper expone al LLM coincide
EXACTAMENTE con `ToolMetadata.args_schema.properties` (ni de mas, ni de
menos), no solo que "no truena".

Esto importa por un hallazgo real (no hipotetico) encontrado auditando
`OpenSupportTicketTool`: su funcion real tiene un parametro `history: list |
None = None` que EXISTE en Python pero DELIBERADAMENTE no esta en
args_schema -- lo inyecta el grafo (Human Handoff), "el LLM jamas lo
controla" (comentario real de support_tools.py). Antes del fix de
`sintel_adapter.py` (ver commit de ADK-05), el adapter exponia CUALQUIER
parametro real con nombre fijo al LLM, sin cruzarlo contra args_schema --
eso habria expuesto `history` como un campo rellenable por el LLM, violando
un boundary de seguridad real y ya deliberado del sistema.

Esta suite generaliza esa verificacion a las 29 tools reales, para que
cualquier otra asimetria similar (parametro real oculto al LLM, o -- el
caso inverso -- un campo de args_schema que no corresponde a ningun
parametro real invocable) se detecte aqui, no en produccion.
"""
import sys
from pathlib import Path

import pytest

AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel" / "ai_engine"
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))

from sintel_adapter import adapt_sintel_tool


def _import_all_tool_modules():
    """Mismos imports que hace get_domain_agent() al recorrer los 9
    perfiles -- se listan aqui explicitamente para no depender del orden en
    que otros tests ya los hayan importado."""
    import tools.core_tools          # noqa: F401
    import tools.inventory_tools     # noqa: F401
    import tools.kyc_tools           # noqa: F401
    import tools.marketing_tools     # noqa: F401
    import tools.orders_tools        # noqa: F401
    import tools.payment_tools       # noqa: F401
    import tools.quotes_tools        # noqa: F401
    import tools.renting_tools       # noqa: F401
    import tools.services_tools      # noqa: F401
    import tools.support_tools       # noqa: F401


def _all_registered_tools():
    _import_all_tool_modules()
    import tools as tool_registry
    return tool_registry.list_tools()


def test_registry_has_the_expected_real_tool_count():
    """Ancla de regresion simple: si este numero cambia, alguien agrego o
    quito una tool real -- revisar el resto de esta suite antes de asumir
    que sigue cubierta."""
    metadatas = _all_registered_tools()
    assert len(metadatas) == 29, (
        f"El registro real tiene {len(metadatas)} tools, se esperaban 29 -- "
        "revisar si esta suite y ADK-04/05 siguen cubriendo el registro completo."
    )


@pytest.mark.parametrize("tool_name", [
    "CoreHomeTool", "CoreNavbarTool", "CoreFooterTool", "CoreBrandSliderTool",
    "CoreBannerUpdateTool", "CoreBannerCreateTool", "CoreNavbarLinkUpdateTool",
    "CoreNavbarLinkCreateTool", "CoreBrandSliderUpdateTool", "StockCheckTool",
    "KycStatusTool", "RequestKycUpgradeTool", "ActivePromosTool",
    "MarketingDashboardTool", "StaleStockAlertsTool", "CampaignTargetsTool",
    "PersonalRecommendationTool", "OrderStatusTool", "PaymentStatusTool",
    "QuoteTemplatesTool", "StartQuotationTool", "RentalStatusTool",
    "RentalAvailabilityTool", "EquipmentSearchTool", "CreateRentalRequestTool",
    "CancelRentalTool", "MaintenanceCheckTool", "ServiceStatusTool",
    "OpenSupportTicketTool",
])
def test_adapted_tool_exposes_exactly_the_declared_args_schema_fields(tool_name):
    """Para cada una de las 29 tools reales: adapt_sintel_tool() no truena,
    y la firma expuesta al LLM (menos tool_context) es EXACTAMENTE
    args_schema.properties.keys() -- ni un campo real oculto de mas (como
    `history`), ni un campo del schema que no llegue a existir."""
    import inspect
    import tools as tool_registry

    registered = tool_registry.get_tool(tool_name)
    assert registered is not None, f"{tool_name} no esta registrada -- import faltante?"

    adk_tool = adapt_sintel_tool(registered)
    exposed_names = set(inspect.signature(adk_tool.func).parameters) - {"tool_context"}

    schema_props = set((registered.metadata.args_schema or {}).get("properties") or {})

    assert exposed_names == schema_props, (
        f"{tool_name}: el wrapper expone {sorted(exposed_names)} al LLM, pero "
        f"args_schema declara {sorted(schema_props)} -- asimetria real entre "
        f"lo expuesto y lo declarado (ver docstring del modulo, caso "
        f"OpenSupportTicketTool.history)."
    )


def test_open_support_ticket_tool_hides_the_graph_injected_history_param():
    """Caso concreto que motivo esta suite: `history` es un parametro REAL
    de open_support_ticket_tool, con default propio, pero jamas debe
    quedar expuesto al LLM."""
    import inspect
    import tools as tool_registry

    registered = tool_registry.get_tool("OpenSupportTicketTool")
    real_sig = inspect.signature(registered.func)
    assert "history" in real_sig.parameters, (
        "Este test asume que open_support_ticket_tool sigue teniendo "
        "`history` como parametro real -- si ya no lo tiene, este test "
        "y su motivo quedaron obsoletos, revisar."
    )

    adk_tool = adapt_sintel_tool(registered)
    exposed_names = set(inspect.signature(adk_tool.func).parameters)
    assert "history" not in exposed_names, (
        "El wrapper expuso 'history' al LLM -- ese parametro lo inyecta el "
        "grafo (Human Handoff), nunca el LLM (ver support_tools.py)."
    )
    assert "message" in exposed_names  # el unico campo requerido real, si debe verse
