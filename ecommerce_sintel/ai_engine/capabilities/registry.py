"""
Capability Registry (Componente 1 del plan, Fases 2 y 8).

El LLM NUNCA conoce una Tool concreta -- solo capacidades declaradas en
lenguaje de negocio. Cada capability apunta a su implementacion actual
(una Tool del ToolRegistry); cambiar la implementacion detras de una
capability nunca requiere tocar el prompt del LLM, solo re-registrarla aqui.

Versionado (Componente 12): una capability deprecated sigue respondiendo
(compatibilidad hacia atras) pero list_active() la excluye.
"""
from pydantic import BaseModel


class Capability(BaseModel):
    capability_id: str
    description_for_llm: str
    tool_name: str
    apps: list[str]
    version: str = "v1"
    status: str = "active"


_CAPABILITIES: dict[str, Capability] = {
    c.capability_id: c
    for c in [
        # -- Fase 2: lectura --------------------------------------------------
        Capability(
            capability_id="buscar_pedido",
            description_for_llm="Buscar las ordenes de compra del cliente y su estado de envio.",
            tool_name="OrderStatusTool",
            apps=["orders"],
        ),
        Capability(
            capability_id="buscar_alquiler",
            description_for_llm="Buscar las solicitudes de alquiler de equipos del cliente y su estado.",
            tool_name="RentalStatusTool",
            apps=["renting"],
        ),
        Capability(
            capability_id="verificar_disponibilidad",
            description_for_llm="Verificar si un equipo de alquiler esta disponible en un rango de fechas.",
            tool_name="RentalAvailabilityTool",
            apps=["renting"],
        ),
        Capability(
            capability_id="consultar_pago",
            description_for_llm="Consultar el estado de los pagos del cliente (aprobado, rechazado, pendiente).",
            tool_name="PaymentStatusTool",
            apps=["payment"],
        ),
        Capability(
            capability_id="consultar_servicio",
            description_for_llm="Consultar el estado de un servicio tecnico contratado (tecnico, fecha, avance).",
            tool_name="ServiceStatusTool",
            apps=["technical_services", "orders"],
        ),
        Capability(
            capability_id="consultar_kyc",
            description_for_llm="Consultar el estado de la verificacion de identidad del cliente.",
            tool_name="KycStatusTool",
            apps=["kyc"],
        ),
        Capability(
            capability_id="buscar_equipos",
            description_for_llm="Buscar equipos disponibles para alquilar, con variantes y precios.",
            tool_name="EquipmentSearchTool",
            apps=["renting"],
        ),
        Capability(
            capability_id="consultar_stock",
            description_for_llm="Consultar el stock actual de un producto, equipo o servicio.",
            tool_name="StockCheckTool",
            apps=["inventory"],
        ),
        Capability(
            capability_id="consultar_promociones",
            description_for_llm="Listar las ofertas y promociones activas en este momento.",
            tool_name="ActivePromosTool",
            apps=["marketing"],
        ),
        # -- Fase 4: escritura (Policy Layer + confirmacion) ------------------
        Capability(
            capability_id="crear_alquiler",
            description_for_llm="Crear una solicitud de alquiler de equipo (queda pendiente de pago).",
            tool_name="CreateRentalRequestTool",
            apps=["renting"],
        ),
        Capability(
            capability_id="cancelar_alquiler",
            description_for_llm="Cancelar una solicitud de alquiler aun no pagada (irreversible).",
            tool_name="CancelRentalTool",
            apps=["renting"],
        ),
        Capability(
            capability_id="consultar_plantillas_cotizacion",
            description_for_llm="Listar las plantillas disponibles para solicitar una cotizacion.",
            tool_name="QuoteTemplatesTool",
            apps=["quotes"],
        ),
        Capability(
            capability_id="iniciar_cotizacion",
            description_for_llm="Crear una solicitud de cotizacion para que un asesor la valore.",
            tool_name="StartQuotationTool",
            apps=["quotes"],
        ),
        Capability(
            capability_id="solicitar_upgrade_profesional",
            description_for_llm="Solicitar el upgrade del cliente a perfil profesional (reabre su verificacion KYC).",
            tool_name="RequestKycUpgradeTool",
            apps=["kyc"],
        ),
        Capability(
            capability_id="abrir_ticket_soporte",
            description_for_llm="Abrir un caso de soporte para que un agente humano atienda (reclamos, cambios de fechas de alquiler, casos no resolubles).",
            tool_name="OpenSupportTicketTool",
            apps=["support"],
        ),
        # -- Fase 8: AI Business Automation -----------------------------------
        Capability(
            capability_id="ver_dashboard_marketing",
            description_for_llm="Ver el dashboard consolidado del negocio: revenue, ordenes, tasa de conversion y resumen por dominio (shop, renting, servicios).",
            tool_name="MarketingDashboardTool",
            apps=["marketing"],
        ),
        Capability(
            capability_id="alertas_stock_inactivo",
            description_for_llm="Consultar alertas de stock inactivo (productos, equipos o servicios sin movimiento) para identificar que necesita una campana de reactivacion.",
            tool_name="StaleStockAlertsTool",
            apps=["marketing"],
        ),
        Capability(
            capability_id="targets_campana",
            description_for_llm="Obtener la lista de usuarios objetivo para una campana de reactivacion (clientes que interactuaron con productos ahora inactivos).",
            tool_name="CampaignTargetsTool",
            apps=["marketing"],
        ),
        Capability(
            capability_id="recomendar_al_cliente",
            description_for_llm="Obtener el perfil de compras del cliente y una recomendacion personalizada basada en su historial (cross-selling y up-selling).",
            tool_name="PersonalRecommendationTool",
            apps=["marketing"],
        ),
        Capability(
            capability_id="verificar_mantenimiento",
            description_for_llm="Verificar los bloqueos de mantenimiento activos de un equipo de alquiler (equipos fuera de servicio o en mantenimiento preventivo).",
            tool_name="MaintenanceCheckTool",
            apps=["renting"],
        ),
        Capability(
            capability_id="ver_config_home",
            description_for_llm="Ver la configuracion actual de la pagina de inicio: banners activos/inactivos y modulos de home.",
            tool_name="CoreHomeTool",
            apps=["core"],
        ),
        Capability(
            capability_id="ver_navbar",
            description_for_llm="Ver los enlaces de la barra de navegacion del sitio.",
            tool_name="CoreNavbarTool",
            apps=["core"],
        ),
        Capability(
            capability_id="ver_footer",
            description_for_llm="Ver los grupos y enlaces del footer del sitio.",
            tool_name="CoreFooterTool",
            apps=["core"],
        ),
        Capability(
            capability_id="ver_brand_slider",
            description_for_llm="Ver los items del slider de marcas del sitio.",
            tool_name="CoreBrandSliderTool",
            apps=["core"],
        ),
        Capability(
            capability_id="editar_banner",
            description_for_llm="Actualizar titulo, subtitulo, enlace o visibilidad de un banner existente del home.",
            tool_name="CoreBannerUpdateTool",
            apps=["core"],
        ),
        Capability(
            capability_id="crear_banner",
            description_for_llm="Crear un nuevo banner de texto en la pagina de inicio.",
            tool_name="CoreBannerCreateTool",
            apps=["core"],
        ),
        Capability(
            capability_id="editar_navbar",
            description_for_llm="Actualizar un enlace de la barra de navegacion (label, url, visibilidad, orden).",
            tool_name="CoreNavbarLinkUpdateTool",
            apps=["core"],
        ),
        Capability(
            capability_id="crear_navbar_link",
            description_for_llm="Agregar un nuevo enlace a la barra de navegacion del sitio.",
            tool_name="CoreNavbarLinkCreateTool",
            apps=["core"],
        ),
        Capability(
            capability_id="editar_brand_slider",
            description_for_llm="Actualizar nombre, sitio web, orden o visibilidad de un item del slider de marcas.",
            tool_name="CoreBrandSliderUpdateTool",
            apps=["core"],
        ),
        # -- Meta Business FASE 11 (camino corto, 2026-09-15): READ-only, sin MCP/OAuth --
        Capability(
            capability_id="consultar_campanas_meta",
            description_for_llm="Listar las campanas de Meta Ads (Facebook/Instagram) de la cuenta publicitaria configurada.",
            tool_name="MetaCampaignsTool",
            apps=["marketing"],
        ),
        Capability(
            capability_id="consultar_detalle_campana_meta",
            description_for_llm="Ver el detalle de una campana especifica de Meta Ads (adsets e insights).",
            tool_name="MetaCampaignDetailTool",
            apps=["marketing"],
        ),
        Capability(
            capability_id="consultar_insights_meta",
            description_for_llm="Consultar metricas de rendimiento (insights) de una cuenta, campana, adset o anuncio de Meta Ads.",
            tool_name="MetaInsightsTool",
            apps=["marketing"],
        ),
        Capability(
            capability_id="consultar_resumen_cuenta_meta",
            description_for_llm="Ver el resumen de la cuenta publicitaria de Meta Ads (gasto, alcance, resultados) en un rango de fechas.",
            tool_name="MetaAccountSummaryTool",
            apps=["marketing"],
        ),
        # "analizar_impacto_arquitectura" (GraphImpactAnalysisTool) retirada 2026-08-10
        # (FASE 0, desacoplamiento ai_engine <-> project_knowledge_graph) -- era una
        # capacidad de arquitectura/ingenieria expuesta al chat de soporte, no algo que
        # un cliente (ni siquiera un admin via el chat) deba poder disparar; ai_engine ya
        # no debe importar project_knowledge_graph en absoluto. Ver AI Editor Runtime
        # (futuro, no construido) para donde debe vivir esto.
    ]
}


class CapabilityRegistry:

    @staticmethod
    def get(capability_id: str) -> Capability | None:
        return _CAPABILITIES.get(capability_id)

    @staticmethod
    def list_all() -> list[Capability]:
        return list(_CAPABILITIES.values())

    @staticmethod
    def list_active() -> list[Capability]:
        return [c for c in _CAPABILITIES.values() if c.status == "active"]

    @staticmethod
    def resolve_tool_name(capability_id: str) -> str | None:
        capability = _CAPABILITIES.get(capability_id)
        return capability.tool_name if capability else None
