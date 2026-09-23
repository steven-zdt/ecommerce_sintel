"""
Tool Registry del AI Core (Fases 2-8) — punto de entrada del paquete.

Importar los modulos de dominio aqui es lo que dispara el registro de cada
Tool (@register_tool). El registro real vive en tools/registry.py; este
__init__ lo re-exporta como pide el plan ("tools/__init__.py — ToolRegistry").
"""
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import RegisteredTool, get_tool, invoke, list_tools, register_tool

# El orden es alfabetico por dominio; agregar dominios nuevos aqui.
import tools.catalog_tools     # noqa: F401  Admin AI Assistant Fase 3: Product/Category/Brand/Tax Tools (listar, ver, crear_borrador/crear, editar, publicar)
import tools.core_tools        # noqa: F401  Fase 8: CoreHomeTool, CoreNavbarTool, CoreFooterTool, CoreBrandSliderTool, CoreBannerUpdateTool, CoreBannerCreateTool, CoreNavbarLinkUpdateTool, CoreNavbarLinkCreateTool, CoreBrandSliderUpdateTool
# tools.graph_tools (GraphImpactAnalysisTool) retirado 2026-08-10 (FASE 0, desacoplamiento
# ai_engine <-> project_knowledge_graph): era una capacidad de arquitectura/ingenieria
# (analizar_impacto_arquitectura), no de soporte al cliente -- ai_engine ya no debe
# importar project_knowledge_graph en absoluto. Su reemplazo futuro vive en el AI Editor
# Runtime (no construido todavia), consumiendo el grafo via su propio SDK/API.
import tools.inventory_tools   # noqa: F401  StockCheckTool
import tools.kyc_tools         # noqa: F401  KycStatusTool, RequestKycUpgradeTool
import tools.marketing_tools   # noqa: F401  ActivePromosTool, MarketingDashboardTool, StaleStockAlertsTool, CampaignTargetsTool, PersonalRecommendationTool
import tools.orders_tools      # noqa: F401  OrderStatusTool
import tools.payment_tools     # noqa: F401  PaymentStatusTool
import tools.quotes_tools      # noqa: F401  QuoteTemplatesTool, StartQuotationTool
import tools.renting_tools     # noqa: F401  RentalStatusTool, RentalAvailabilityTool, EquipmentSearchTool, CreateRentalRequestTool, CancelRentalTool, MaintenanceCheckTool
import tools.services_tools    # noqa: F401  ServiceStatusTool
import tools.support_tools     # noqa: F401  OpenSupportTicketTool
import tools.technical_services_tools  # noqa: F401  Admin AI Assistant, vertical Servicios (2026-09-23): ServiceListTool, ServiceGetTool, ServiceCategoryListTool, ServiceCreateDraftTool, ServiceUpdateDraftTool

__all__ = [
    "RegisteredTool",
    "ToolContext",
    "ToolMetadata",
    "get_tool",
    "invoke",
    "list_tools",
    "register_tool",
]
