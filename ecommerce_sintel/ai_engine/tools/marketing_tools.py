"""Tools del dominio marketing (Fase 2 y Fase 8 AI Core).

Fase 2: ActivePromosTool (cualquier usuario activo).
Fase 8 (automatizacion comercial y de campanas):
  - MarketingDashboardTool   -- dashboard consolidado (admin)
  - StaleStockAlertsTool     -- alertas de stock inactivo (admin)
  - CampaignTargetsTool      -- usuarios objetivo para campanas (admin)
  - PersonalRecommendationTool -- perfil + recomendacion personalizada (usuario)
"""
from tools.http_bridge import django_internal_get
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

ACTIVE_PROMOS_METADATA = ToolMetadata(
    name="ActivePromosTool",
    description="Lista las ofertas flash activas en este momento (nombre, descuento, vigencia, item).",
    owner="marketing",
    capabilities=["consultar_promociones"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Maximo de ofertas (default 10)"},
        },
    },
)


@register_tool(ACTIVE_PROMOS_METADATA)
async def active_promos_tool(ctx: ToolContext, limit: int = 10) -> dict:
    """Envuelve MarketingSelector.list_active_flash_offers(). PersonalOffer fuera (gap #5)."""
    return await django_internal_get(
        ctx.token, "/marketing/promos/", {"limit": limit},
        timeout_ms=ACTIVE_PROMOS_METADATA.timeout_ms,
    )


# --- Fase 8: automatizacion comercial y de campanas --------------------------

MARKETING_DASHBOARD_METADATA = ToolMetadata(
    name="MarketingDashboardTool",
    description="Dashboard consolidado del negocio: revenue, ordenes, tasa de conversion, resumen de shop/renting/servicios. Solo admin.",
    owner="marketing",
    capabilities=["ver_dashboard_marketing"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(MARKETING_DASHBOARD_METADATA)
async def marketing_dashboard_tool(ctx: ToolContext) -> dict:
    """Envuelve MarketingSelector.get_consolidated_dashboard()."""
    return await django_internal_get(
        ctx.token, "/marketing/dashboard/",
        timeout_ms=MARKETING_DASHBOARD_METADATA.timeout_ms,
    )


STALE_STOCK_ALERTS_METADATA = ToolMetadata(
    name="StaleStockAlertsTool",
    description="Alertas de stock inactivo por dominio (shop, renting, servicios). Solo admin.",
    owner="marketing",
    capabilities=["alertas_stock_inactivo"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "days": {"type": "integer", "description": "Dias sin movimiento para considerar inactivo (default 30)."},
        },
    },
)


@register_tool(STALE_STOCK_ALERTS_METADATA)
async def stale_stock_alerts_tool(ctx: ToolContext, days: int = 30) -> dict:
    """Envuelve MarketingSelector.get_stale_stock_alerts()."""
    return await django_internal_get(
        ctx.token, "/marketing/stale-stock/", {"days": days},
        timeout_ms=STALE_STOCK_ALERTS_METADATA.timeout_ms,
    )


CAMPAIGN_TARGETS_METADATA = ToolMetadata(
    name="CampaignTargetsTool",
    description="Lista los usuarios objetivo para una campana de reactivacion (interactuaron con productos ahora inactivos). Solo admin.",
    owner="marketing",
    capabilities=["targets_campana"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(CAMPAIGN_TARGETS_METADATA)
async def campaign_targets_tool(ctx: ToolContext) -> dict:
    """Envuelve MarketingSelector.get_campaign_targets_for_stale_products()."""
    return await django_internal_get(
        ctx.token, "/marketing/campaign-targets/",
        timeout_ms=CAMPAIGN_TARGETS_METADATA.timeout_ms,
    )


PERSONAL_RECOMMENDATION_METADATA = ToolMetadata(
    name="PersonalRecommendationTool",
    description="Perfil de compras del cliente autenticado y recomendacion personalizada (cross-selling / up-selling). Incluye ofertas activas relevantes.",
    owner="marketing",
    capabilities=["recomendar_al_cliente"],
    permissions=["IsAuthenticatedActiveUser"],
    risk="low",
    audit_level="none",
    args_schema={"type": "object", "properties": {}},
)


@register_tool(PERSONAL_RECOMMENDATION_METADATA)
async def personal_recommendation_tool(ctx: ToolContext) -> dict:
    """Envuelve MarketingSelector.get_user_marketing_profile() + flash offers relevantes."""
    return await django_internal_get(
        ctx.token, "/marketing/recommendation/",
        timeout_ms=PERSONAL_RECOMMENDATION_METADATA.timeout_ms,
    )
