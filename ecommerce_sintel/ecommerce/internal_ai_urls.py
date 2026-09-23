"""
Rutas internas /api/v1/internal/ai/* consumidas SOLO por el AI Engine
(Fases 2-8 del AI Core, ai_engine/.AGENT/PLAN_DE_ACCION_AI_CORE.md).

Cada vista vive en la app duena del dominio y envuelve exclusivamente
Selectors/Commands ya existentes. Nginx no proxea /internal/ hacia afuera.
"""
from django.urls import path

from accounts.api.internal_ai import AiCustomerContextView
from ai_knowledge.api.views import AiKnowledgeRetrieveView
from ai_provider.api.internal_ai import AiProviderConfigView
from customer_memory.api.views import CustomerMemoryRetrieveView, CustomerMemoryStoreView
from core.api.internal_ai import (
    AiCoreHomeConfigView,
    AiCoreNavbarView,
    AiCoreFooterView,
    AiCoreBrandSliderView,
    AiCoreBannerUpdateView,
    AiCoreBannerCreateView,
    AiCoreNavbarLinkUpdateView,
    AiCoreNavbarLinkCreateView,
    AiCoreBrandSliderItemUpdateView,
)
from inventory.api.internal_ai import AiStockCheckView
from kyc.api.internal_ai import AiKycStatusView, AiRequestKycUpgradeView
from marketing.api.internal_ai import (
    AiActivePromosView,
    AiMarketingDashboardView,
    AiStaleStockAlertsView,
    AiCampaignTargetsView,
    AiPersonalRecommendationView,
    AiMetaCampaignsView,
    AiMetaCampaignDetailView,
    AiMetaInsightsView,
    AiMetaAccountSummaryView,
)
from orders.api.internal_ai import AiOrderStatusView
from payment.api.internal_ai import AiPaymentStatusView
from quotes.api.internal_ai import AiQuoteTemplatesView, AiStartQuotationView
from renting.api.internal_ai import (
    AiCancelRentalView,
    AiCreateRentalRequestView,
    AiEquipmentMaintenanceView,
    AiEquipmentSearchView,
    AiRentalAvailabilityView,
    AiRentalStatusView,
)
from shop.api.internal_ai import (
    AiCatalogBrandCreateDraftView,
    AiCatalogBrandGetView,
    AiCatalogBrandListView,
    AiCatalogBrandSetPublishedStateView,
    AiCatalogBrandUpdateView,
    AiCatalogCategoryCreateDraftView,
    AiCatalogCategoryGetView,
    AiCatalogCategoryListView,
    AiCatalogCategorySetPublishedStateView,
    AiCatalogCategoryUpdateView,
    AiCatalogProductCreateDraftView,
    AiCatalogProductGetView,
    AiCatalogProductListView,
    AiCatalogProductSetPublishedStateView,
    AiCatalogProductUpdateDraftView,
    AiCatalogTaxCreateView,
    AiCatalogTaxGetView,
    AiCatalogTaxListView,
    AiCatalogTaxUpdateView,
)
from support.api.internal_ai import AiOpenSupportTicketView
from technical_services.api.internal_ai import AiServiceStatusView
from technical_services.api.internal_ai import (
    AiServiceAdminCategoryListView,
    AiServiceAdminCreateDraftView,
    AiServiceAdminGetView,
    AiServiceAdminListView,
    AiServiceAdminUpdateDraftView,
)

app_name = "internal_ai"

urlpatterns = [
    # Fase 2 - lectura
    path("orders/",               AiOrderStatusView.as_view(),         name="ai-orders"),
    path("rentals/",              AiRentalStatusView.as_view(),        name="ai-rentals"),
    path("renting/availability/", AiRentalAvailabilityView.as_view(),  name="ai-renting-availability"),
    path("renting/equipment/",    AiEquipmentSearchView.as_view(),     name="ai-renting-equipment"),
    path("payments/",             AiPaymentStatusView.as_view(),       name="ai-payments"),
    path("services/",             AiServiceStatusView.as_view(),       name="ai-services"),
    # Admin AI Assistant, vertical Servicios (PLAN_SINTEL_ADMIN_ASISTENTE_RAG_
    # FORMULARIOS_LOOP.md, Fase 1-3, 2026-09-23) -- namespace services/admin/*
    # deliberadamente separado de services/ de arriba (cliente, IsAuthenticatedActiveUser)
    # vs. esto (admin, IsAdminUser).
    path("services/admin/",                  AiServiceAdminListView.as_view(),         name="ai-services-admin"),
    path("services/admin/get/",              AiServiceAdminGetView.as_view(),          name="ai-services-admin-get"),
    path("services/admin/create-draft/",     AiServiceAdminCreateDraftView.as_view(),  name="ai-services-admin-create-draft"),
    path("services/admin/update-draft/",     AiServiceAdminUpdateDraftView.as_view(),  name="ai-services-admin-update-draft"),
    path("services/admin/categories/",       AiServiceAdminCategoryListView.as_view(), name="ai-services-admin-categories"),
    path("kyc/",                  AiKycStatusView.as_view(),           name="ai-kyc"),
    path("inventory/stock/",      AiStockCheckView.as_view(),          name="ai-inventory-stock"),
    path("marketing/promos/",     AiActivePromosView.as_view(),        name="ai-marketing-promos"),
    # Fase 5 - CRM Context
    path("customer-context/",     AiCustomerContextView.as_view(),     name="ai-customer-context"),
    # Config dinamica de modelos locales, FASE 2 (2026-08-13)
    path("provider-config/",      AiProviderConfigView.as_view(),      name="ai-provider-config"),
    # RAG sobre pgvector, FASE 1 de la mision de simplificacion arquitectonica (2026-09-14)
    path("knowledge/retrieve/",   AiKnowledgeRetrieveView.as_view(),   name="ai-knowledge-retrieve"),
    # Memoria del cliente, Mision RAG-POST2 FASE 9 (2026-09-16)
    path("memory/retrieve/",      CustomerMemoryRetrieveView.as_view(), name="ai-memory-retrieve"),
    path("memory/store/",         CustomerMemoryStoreView.as_view(),   name="ai-memory-store"),
    # Fase 4 - escritura (permission classes reales + SecurityEvent audit)
    path("rentals/create/",       AiCreateRentalRequestView.as_view(), name="ai-rentals-create"),
    path("rentals/cancel/",       AiCancelRentalView.as_view(),        name="ai-rentals-cancel"),
    path("quotes/templates/",     AiQuoteTemplatesView.as_view(),      name="ai-quotes-templates"),
    path("quotes/create/",        AiStartQuotationView.as_view(),      name="ai-quotes-create"),
    path("kyc/request-upgrade/",  AiRequestKycUpgradeView.as_view(),   name="ai-kyc-request-upgrade"),
    path("support/ticket/",       AiOpenSupportTicketView.as_view(),   name="ai-support-ticket"),
    # Fase 8 - AI Business Automation
    path("marketing/dashboard/",        AiMarketingDashboardView.as_view(),      name="ai-marketing-dashboard"),
    path("marketing/stale-stock/",      AiStaleStockAlertsView.as_view(),        name="ai-marketing-stale-stock"),
    path("marketing/campaign-targets/", AiCampaignTargetsView.as_view(),         name="ai-marketing-campaign-targets"),
    path("marketing/recommendation/",   AiPersonalRecommendationView.as_view(),  name="ai-marketing-recommendation"),
    # Meta Ads READ (FASE 9 integracion Meta Business) -- admin-only
    path("marketing/meta/campaigns/",              AiMetaCampaignsView.as_view(),      name="ai-marketing-meta-campaigns"),
    path("marketing/meta/campaign/<str:campaign_id>/", AiMetaCampaignDetailView.as_view(), name="ai-marketing-meta-campaign-detail"),
    path("marketing/meta/insights/",               AiMetaInsightsView.as_view(),       name="ai-marketing-meta-insights"),
    path("marketing/meta/account-summary/",        AiMetaAccountSummaryView.as_view(), name="ai-marketing-meta-account-summary"),
    path("renting/maintenance/",        AiEquipmentMaintenanceView.as_view(),    name="ai-renting-maintenance"),
    path("core/home/",                  AiCoreHomeConfigView.as_view(),          name="ai-core-home"),
    path("core/navbar/",                AiCoreNavbarView.as_view(),              name="ai-core-navbar"),
    path("core/footer/",                AiCoreFooterView.as_view(),              name="ai-core-footer"),
    path("core/brand-slider/",          AiCoreBrandSliderView.as_view(),         name="ai-core-brand-slider"),
    path("core/banners/update/",        AiCoreBannerUpdateView.as_view(),        name="ai-core-banner-update"),
    path("core/banners/create/",        AiCoreBannerCreateView.as_view(),        name="ai-core-banner-create"),
    path("core/navbar/update/",         AiCoreNavbarLinkUpdateView.as_view(),    name="ai-core-navbar-update"),
    path("core/navbar/create/",         AiCoreNavbarLinkCreateView.as_view(),    name="ai-core-navbar-create"),
    path("core/brand-slider/update/",   AiCoreBrandSliderItemUpdateView.as_view(), name="ai-core-brand-slider-update"),
    # Admin AI Assistant, vertical piloto Catalogo (Fase 3, 2026-09-16) -- solo
    # Product, solo Nivel 0-2 (ver ai_engine/.AGENT/ADMIN_AI_ASSISTANT_FASE1_TOOLS_CATALOGO.md).
    path("catalog/products/",               AiCatalogProductListView.as_view(),        name="ai-catalog-products"),
    path("catalog/products/get/",           AiCatalogProductGetView.as_view(),         name="ai-catalog-products-get"),
    path("catalog/products/create-draft/",  AiCatalogProductCreateDraftView.as_view(), name="ai-catalog-products-create-draft"),
    path("catalog/products/update-draft/",  AiCatalogProductUpdateDraftView.as_view(), name="ai-catalog-products-update-draft"),
    path("catalog/products/set-published-state/", AiCatalogProductSetPublishedStateView.as_view(), name="ai-catalog-products-set-published-state"),
    path("catalog/categories/",               AiCatalogCategoryListView.as_view(),        name="ai-catalog-categories"),
    path("catalog/categories/get/",           AiCatalogCategoryGetView.as_view(),         name="ai-catalog-categories-get"),
    path("catalog/categories/create-draft/",  AiCatalogCategoryCreateDraftView.as_view(), name="ai-catalog-categories-create-draft"),
    path("catalog/categories/update/",        AiCatalogCategoryUpdateView.as_view(),      name="ai-catalog-categories-update"),
    path("catalog/categories/set-published-state/", AiCatalogCategorySetPublishedStateView.as_view(), name="ai-catalog-categories-set-published-state"),
    path("catalog/brands/",               AiCatalogBrandListView.as_view(),        name="ai-catalog-brands"),
    path("catalog/brands/get/",           AiCatalogBrandGetView.as_view(),         name="ai-catalog-brands-get"),
    path("catalog/brands/create-draft/",  AiCatalogBrandCreateDraftView.as_view(), name="ai-catalog-brands-create-draft"),
    path("catalog/brands/update/",        AiCatalogBrandUpdateView.as_view(),      name="ai-catalog-brands-update"),
    path("catalog/brands/set-published-state/", AiCatalogBrandSetPublishedStateView.as_view(), name="ai-catalog-brands-set-published-state"),
    path("catalog/taxes/",         AiCatalogTaxListView.as_view(),   name="ai-catalog-taxes"),
    path("catalog/taxes/get/",     AiCatalogTaxGetView.as_view(),    name="ai-catalog-taxes-get"),
    path("catalog/taxes/create/",  AiCatalogTaxCreateView.as_view(), name="ai-catalog-taxes-create"),
    path("catalog/taxes/update/",  AiCatalogTaxUpdateView.as_view(), name="ai-catalog-taxes-update"),
]
