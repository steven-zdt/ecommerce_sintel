"""
Tool Registry del AI Core (Fases 2-8) — punto de entrada del paquete.

Importar los modulos de dominio aqui es lo que dispara el registro de cada
Tool (@register_tool). El registro real vive en tools/registry.py; este
__init__ lo re-exporta como pide el plan ("tools/__init__.py — ToolRegistry").
"""
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import RegisteredTool, get_tool, invoke, list_tools, register_tool

# El orden es alfabetico por dominio; agregar dominios nuevos aqui.
import tools.core_tools        # noqa: F401  Fase 8: CoreHomeTool, CoreNavbarTool, CoreFooterTool, CoreBrandSliderTool, CoreBannerUpdateTool, CoreBannerCreateTool, CoreNavbarLinkUpdateTool, CoreNavbarLinkCreateTool, CoreBrandSliderUpdateTool
import tools.inventory_tools   # noqa: F401  StockCheckTool
import tools.kyc_tools         # noqa: F401  KycStatusTool, RequestKycUpgradeTool
import tools.marketing_tools   # noqa: F401  ActivePromosTool, MarketingDashboardTool, StaleStockAlertsTool, CampaignTargetsTool, PersonalRecommendationTool
import tools.orders_tools      # noqa: F401  OrderStatusTool
import tools.payment_tools     # noqa: F401  PaymentStatusTool
import tools.quotes_tools      # noqa: F401  QuoteTemplatesTool, StartQuotationTool
import tools.renting_tools     # noqa: F401  RentalStatusTool, RentalAvailabilityTool, EquipmentSearchTool, CreateRentalRequestTool, CancelRentalTool, MaintenanceCheckTool
import tools.services_tools    # noqa: F401  ServiceStatusTool
import tools.support_tools     # noqa: F401  OpenSupportTicketTool

__all__ = [
    "RegisteredTool",
    "ToolContext",
    "ToolMetadata",
    "get_tool",
    "invoke",
    "list_tools",
    "register_tool",
]
