"""
HARDENING F4 (2026-09-24) -- clasificacion formal de Tools y politica derivada.

Plan: PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md sec. 8; propuesta:
ai_engine_adk/.AGENT/HARDENING_F4_PROPOSAL_2026-09-24.md.

Un unico punto de revision de la politica de las Tools (en vez de tocar los ~15 archivos de dominio):
`apply_policy(metadata)` corre en `registry.register_tool` y completa la metadata declarada:

  level  0 lectura | 1 escritura local no destructiva (borrador, alta de ticket) | 2 escritura de consecuencia
         | 3 efecto externo/reserva | 4 destructivo/financiero/seguridad (ninguna Tool actual: el agente no borra ni
         mueve dinero -- regla del plan "no dar delete al agente salvo aprobacion arquitectonica especifica").
  requires_confirmation  forzado a True para los `*Update*` de catalogo/servicios (decision del usuario 2026-09-24:
         modifican datos ya publicados); las Tools de nivel >= 2 SIEMPRE lo exigen (invariante).
  rate_limit  si una escritura no declara uno: 10/hour/user (risk=high) o 30/hour/user (resto).
  idempotent  True para toda escritura: el adapter del ADK deduplica repeticiones identicas (ver idempotency.py).

Una escritura NUEVA sin entrada explicita en TOOL_LEVELS recibe nivel 2 (conservador: pide confirmacion) y el test
de invariantes falla hasta que se clasifique a proposito.
"""
from tools.metadata import ToolMetadata

# Solo escrituras (side_effects=True); toda lectura es nivel 0 automaticamente.
TOOL_LEVELS: dict[str, int] = {
    # 1 -- borradores (is_active=False) y alta de ticket: reversibles / de bajo impacto
    "CatalogBrandCreateDraftTool": 1,
    "CatalogCategoryCreateDraftTool": 1,
    "CatalogProductCreateDraftTool": 1,
    "ServiceCreateDraftTool": 1,
    "OpenSupportTicketTool": 1,
    # 2 -- modifican datos ya publicados, estado publicado, impuestos, contenido del sitio, identidad
    "CatalogBrandUpdateTool": 2,
    "CatalogCategoryUpdateTool": 2,
    "CatalogProductUpdateDraftTool": 2,
    "ServiceUpdateDraftTool": 2,
    "CatalogBrandSetPublishedStateTool": 2,
    "CatalogCategorySetPublishedStateTool": 2,
    "CatalogProductSetPublishedStateTool": 2,
    "CatalogTaxCreateTool": 2,
    "CatalogTaxUpdateTool": 2,
    "CoreBannerCreateTool": 2,
    "CoreBannerUpdateTool": 2,
    "CoreNavbarLinkCreateTool": 2,
    "CoreNavbarLinkUpdateTool": 2,
    "CoreBrandSliderUpdateTool": 2,
    "RequestKycUpgradeTool": 2,
    "StartQuotationTool": 2,
    # 3 -- reservas / efecto sobre operaciones reales de un cliente
    "CreateRentalRequestTool": 3,
    "CancelRentalTool": 3,
}

# Decision del usuario (2026-09-24): pedir confirmacion humana en los *Update* que tocan datos ya publicados.
FORCE_CONFIRMATION: set[str] = {
    "CatalogBrandUpdateTool",
    "CatalogCategoryUpdateTool",
    "CatalogProductUpdateDraftTool",
    "ServiceUpdateDraftTool",
}

RATE_LIMIT_HIGH_RISK = "10/hour/user"
RATE_LIMIT_DEFAULT_WRITE = "30/hour/user"
DEFAULT_UNCLASSIFIED_WRITE_LEVEL = 2


def level_for(name: str, side_effects: bool) -> int:
    if not side_effects:
        return 0
    return TOOL_LEVELS.get(name, DEFAULT_UNCLASSIFIED_WRITE_LEVEL)


def apply_policy(metadata: ToolMetadata) -> ToolMetadata:
    """Completa (no sobrescribe lo ya declarado salvo la confirmacion forzada) level/rate_limit/confirmacion/idempotencia."""
    metadata.level = level_for(metadata.name, metadata.side_effects)
    if metadata.side_effects:
        metadata.idempotent = True
        if not metadata.rate_limit:
            metadata.rate_limit = RATE_LIMIT_HIGH_RISK if metadata.risk == "high" else RATE_LIMIT_DEFAULT_WRITE
        if metadata.name in FORCE_CONFIRMATION or metadata.level >= 2:
            metadata.requires_confirmation = True
    return metadata
