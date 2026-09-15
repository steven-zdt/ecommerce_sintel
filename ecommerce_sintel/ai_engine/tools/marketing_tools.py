"""Tools del dominio marketing (Fase 2 y Fase 8 AI Core).

Fase 2: ActivePromosTool (cualquier usuario activo).
Fase 8 (automatizacion comercial y de campanas):
  - MarketingDashboardTool   -- dashboard consolidado (admin)
  - StaleStockAlertsTool     -- alertas de stock inactivo (admin)
  - CampaignTargetsTool      -- usuarios objetivo para campanas (admin)
  - PersonalRecommendationTool -- perfil + recomendacion personalizada (usuario)

Meta Business FASE 11 (camino corto, 2026-09-15): envuelve las 4 vistas
AiMeta*View ya desplegadas desde FASE 9 (marketing/api/internal_ai.py,
admin-only, solo lectura) -- NO depende del MCP/OAuth de FASE 10, que sigue
sin autorizar (volumen de tokens vacio). Mientras META_ACCESS_TOKEN/
META_AD_ACCOUNT_ID reales no esten cargados, estas Tools devuelven el error
{"configured": false} que ya arma _meta_error_response() en Django -- nunca
inventan datos. Todas side_effects=False, ninguna escribe contra Meta.
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


# --- FASE 11 (camino corto): Meta Ads READ, sin MCP/OAuth ---------------------

META_CAMPAIGNS_METADATA = ToolMetadata(
    name="MetaCampaignsTool",
    description="Lista las campanas de Meta Ads (Facebook/Instagram) de la cuenta publicitaria configurada, con su estado. Solo admin.",
    owner="marketing",
    capabilities=["consultar_campanas_meta"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Maximo de campanas a devolver (default 50, tope 100)."},
            "effective_status": {
                "type": "array", "items": {"type": "string"},
                "description": "Filtrar por estado efectivo (ej. ACTIVE, PAUSED). Opcional.",
            },
        },
    },
)


@register_tool(META_CAMPAIGNS_METADATA)
async def meta_campaigns_tool(ctx: ToolContext, limit: int = 50, effective_status: list | None = None) -> dict:
    """Envuelve MetaCampaignSelector.get_campaigns() via AiMetaCampaignsView."""
    params: dict = {"limit": limit}
    if effective_status:
        params["effective_status"] = effective_status
    return await django_internal_get(
        ctx.token, "/marketing/meta/campaigns/", params,
        timeout_ms=META_CAMPAIGNS_METADATA.timeout_ms,
    )


META_CAMPAIGN_DETAIL_METADATA = ToolMetadata(
    name="MetaCampaignDetailTool",
    description="Detalle de una campana especifica de Meta Ads: adsets e insights. Solo admin.",
    owner="marketing",
    capabilities=["consultar_detalle_campana_meta"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "campaign_id": {"type": "string", "description": "ID de la campana de Meta Ads (obligatorio)."},
        },
        "required": ["campaign_id"],
    },
)


@register_tool(META_CAMPAIGN_DETAIL_METADATA)
async def meta_campaign_detail_tool(ctx: ToolContext, campaign_id: str) -> dict:
    """Envuelve MetaCampaignSelector.get_campaign_detail() via AiMetaCampaignDetailView."""
    return await django_internal_get(
        ctx.token, f"/marketing/meta/campaign/{campaign_id}/",
        timeout_ms=META_CAMPAIGN_DETAIL_METADATA.timeout_ms,
    )


META_INSIGHTS_METADATA = ToolMetadata(
    name="MetaInsightsTool",
    description="Metricas de rendimiento (insights) de una cuenta, campana, adset o anuncio de Meta Ads. Solo admin.",
    owner="marketing",
    capabilities=["consultar_insights_meta"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "object_id": {"type": "string", "description": "ID del objeto de Meta a consultar (obligatorio)."},
            "level": {"type": "string", "description": "Nivel: account, campaign, adset o ad (default campaign)."},
            "date_preset": {"type": "string", "description": "Rango de fechas predefinido de Meta (default last_30d)."},
        },
        "required": ["object_id"],
    },
)


@register_tool(META_INSIGHTS_METADATA)
async def meta_insights_tool(ctx: ToolContext, object_id: str, level: str = "campaign",
                              date_preset: str = "last_30d") -> dict:
    """Envuelve MetaCampaignSelector.get_insights() via AiMetaInsightsView."""
    return await django_internal_get(
        ctx.token, "/marketing/meta/insights/",
        {"object_id": object_id, "level": level, "date_preset": date_preset},
        timeout_ms=META_INSIGHTS_METADATA.timeout_ms,
    )


META_ACCOUNT_SUMMARY_METADATA = ToolMetadata(
    name="MetaAccountSummaryTool",
    description="Resumen de la cuenta publicitaria de Meta Ads (gasto, alcance, resultados) en un rango de fechas. Solo admin.",
    owner="marketing",
    capabilities=["consultar_resumen_cuenta_meta"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "date_preset": {"type": "string", "description": "Rango de fechas predefinido de Meta (default last_30d)."},
        },
    },
)


@register_tool(META_ACCOUNT_SUMMARY_METADATA)
async def meta_account_summary_tool(ctx: ToolContext, date_preset: str = "last_30d") -> dict:
    """Envuelve MetaCampaignSelector.get_account_summary() via AiMetaAccountSummaryView."""
    return await django_internal_get(
        ctx.token, "/marketing/meta/account-summary/", {"date_preset": date_preset},
        timeout_ms=META_ACCOUNT_SUMMARY_METADATA.timeout_ms,
    )
