"""
dashboard/api/urls.py

Router centralizado del BFF administrativo.
Todas las rutas bajo /api/v1/dashboard/.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from dashboard.api.views import (
    AdminMetricsView,
    AdminProductViewSet,
    AdminCategoryViewSet,
    AdminBrandViewSet,
    AdminTaxViewSet,
    AdminOrderViewSet,
    AdminEquipmentViewSet,
    AdminRentingCategoryViewSet,
    AdminRentingBrandViewSet,
    AdminRentalLaborViewSet,
    AdminQuotationViewSet,
    AdminQuoteTemplateCategoryViewSet,
    AdminQuoteTemplateSubcategoryViewSet,
    AdminQuoteTemplateViewSet,
    AdminQuoteTemplateAttributeViewSet,
    AdminQuoteEquipmentTypeViewSet,
    AdminQuoteTemplateModuleViewSet,
    AdminQuoteQuestionViewSet,
    AdminQuoteQuestionOptionViewSet,
    AdminTechnicalServiceViewSet,
    AdminServiceRequestViewSet,
    AdminServiceCategoryViewSet,
    AdminServiceLevelViewSet,
    AdminServiceVariantViewSet,
    AdminServiceFAQViewSet,
)
from dashboard.api.services_catalog_views import (
    AdminServiceIncludedItemViewSet,
    AdminServiceExcludedItemViewSet,
    AdminServiceRequirementViewSet,
    AdminServiceSpecificationGroupViewSet,
    AdminServiceSpecificationViewSet,
    AdminServiceDocumentViewSet,
    AdminServiceVideoViewSet,
    AdminServiceProcessStepViewSet,
)
from dashboard.api.views import (
    AdminMarketingViewSet,
    AdminShopCostRuleViewSet,
    AdminRentalCostRuleViewSet,
    AdminServiceCostRuleViewSet,
    AdminHomeConfigViewSet,
    AdminHomeCardViewSet,
    AdminHomeCardGroupViewSet,
    AdminFeatureBannerSectionViewSet,
    AdminFeatureBannerBlockViewSet,
    AdminFooterViewSet,
    AdminFooterGroupViewSet,
    AdminSiteBrandViewSet,
    AdminNavbarViewSet,
    AdminFooterCTAViewSet,
    AdminBrandSliderViewSet,
    AdminAboutUsViewSet,
    AdminSeoMetaTagViewSet,
    AdminSiteVerificationFileViewSet,
    AdminSupportChatViewSet,
    AdminSecurityViewSet,
    AdminNotificationTemplateViewSet,
    AdminNotificationLogViewSet,
    AdminPaymentViewSet,
)
from dashboard.api.renting_catalog_views import (
    AdminEquipmentImageViewSet,
    AdminRentalIncludedItemViewSet,
    AdminRentalExcludedItemViewSet,
    AdminRentalFeatureViewSet,
    AdminRentalSpecificationGroupViewSet,
    AdminRentalSpecificationViewSet,
    AdminRentalRequirementViewSet,
    AdminRentalServiceIncludedViewSet,
    AdminRentalOptionalServiceViewSet,
    AdminRentalFAQViewSet,
    AdminRentalVideoViewSet,
    AdminRentalDocumentViewSet,
)
from dashboard.api.package_views import (
    AdminServicePackageViewSet,
    AdminPackageIncludedItemViewSet,
    AdminPackageAdditionalCostViewSet,
)
from dashboard.api.shop_catalog_views import (
    AdminProductImageViewSet,
    AdminProductIncludedItemViewSet,
    AdminProductExcludedItemViewSet,
    AdminProductFeatureViewSet,
    AdminProductSpecificationGroupViewSet,
    AdminProductSpecificationViewSet,
    AdminProductRequirementViewSet,
    AdminProductServiceIncludedViewSet,
    AdminProductOptionalServiceViewSet,
    AdminProductFAQViewSet,
    AdminProductVideoViewSet,
    AdminProductDocumentViewSet,
    AdminProductFunctioningStepViewSet,
)
from dashboard.api.content_blocks_views import (
    AdminProductContentBlockViewSet, AdminProductRelationViewSet,
    AdminServiceContentBlockViewSet, AdminServiceRelationViewSet,
)
from operations.api.views import AdminOperationViewSet, AdminDispatcherViewSet
from dashboard.api.ai_provider_views import AdminAIProviderViewSet, AdminAIChannelConfigViewSet

router = DefaultRouter()

# Users: administrado en /api/v1/users/ (users.api.views.UserViewSet), no aca.

# Shop
router.register(r'products',          AdminProductViewSet,          basename='admin-products')
router.register(r'categories',        AdminCategoryViewSet,         basename='admin-categories')
router.register(r'brands',            AdminBrandViewSet,            basename='admin-brands')
router.register(r'taxes',             AdminTaxViewSet,              basename='admin-taxes')

# Catalogo enriquecido de Product (2026-08-03) -- espejo del de Equipment (linea 97 abajo)
router.register(r'product-catalog-images',      AdminProductImageViewSet,            basename='admin-product-catalog-images')
router.register(r'product-included-items',      AdminProductIncludedItemViewSet,     basename='admin-product-included-items')
router.register(r'product-excluded-items',      AdminProductExcludedItemViewSet,     basename='admin-product-excluded-items')
router.register(r'product-features',            AdminProductFeatureViewSet,          basename='admin-product-features')
router.register(r'product-specification-groups', AdminProductSpecificationGroupViewSet, basename='admin-product-specification-groups')
router.register(r'product-specifications',      AdminProductSpecificationViewSet,    basename='admin-product-specifications')
router.register(r'product-requirements',        AdminProductRequirementViewSet,      basename='admin-product-requirements')
router.register(r'product-services-included',   AdminProductServiceIncludedViewSet,  basename='admin-product-services-included')
router.register(r'product-optional-services',   AdminProductOptionalServiceViewSet,  basename='admin-product-optional-services')
router.register(r'product-faqs',                AdminProductFAQViewSet,              basename='admin-product-faqs')
router.register(r'product-videos',              AdminProductVideoViewSet,            basename='admin-product-videos')
router.register(r'product-documents',           AdminProductDocumentViewSet,         basename='admin-product-documents')
router.register(r'product-functioning-steps',   AdminProductFunctioningStepViewSet,  basename='admin-product-functioning-steps')

# Contenido del Producto (Fase 3, reingenieria PDP 2026-08-05) -- orden/visibilidad de
# bloques + relaciones (compatibles/accesorios/relacionados). Generico en el modelo
# (shared/models.py) pero expuesto Shop-only en este contrato (recibe `product`).
router.register(r'product-content-blocks',      AdminProductContentBlockViewSet,     basename='admin-product-content-blocks')
router.register(r'product-relations',           AdminProductRelationViewSet,         basename='admin-product-relations')

# Orders
router.register(r'orders',            AdminOrderViewSet,            basename='admin-orders')

# Renting
router.register(r'equipment',         AdminEquipmentViewSet,        basename='admin-equipment')
router.register(r'renting-categories', AdminRentingCategoryViewSet, basename='admin-renting-categories')
router.register(r'renting-brands',    AdminRentingBrandViewSet,     basename='admin-renting-brands')
router.register(r'rental-labor',      AdminRentalLaborViewSet,      basename='admin-rental-labor')

# Catalogo enriquecido de Equipment (2026-07-16)
router.register(r'equipment-images',            AdminEquipmentImageViewSet,          basename='admin-equipment-images')
router.register(r'rental-included-items',       AdminRentalIncludedItemViewSet,      basename='admin-rental-included-items')
router.register(r'rental-excluded-items',       AdminRentalExcludedItemViewSet,      basename='admin-rental-excluded-items')
router.register(r'rental-features',             AdminRentalFeatureViewSet,           basename='admin-rental-features')
router.register(r'rental-specification-groups', AdminRentalSpecificationGroupViewSet, basename='admin-rental-specification-groups')
router.register(r'rental-specifications',       AdminRentalSpecificationViewSet,      basename='admin-rental-specifications')
router.register(r'rental-requirements',         AdminRentalRequirementViewSet,        basename='admin-rental-requirements')
router.register(r'rental-services-included',    AdminRentalServiceIncludedViewSet,    basename='admin-rental-services-included')
router.register(r'rental-optional-services',    AdminRentalOptionalServiceViewSet,    basename='admin-rental-optional-services')
router.register(r'rental-faqs',                 AdminRentalFAQViewSet,                basename='admin-rental-faqs')
router.register(r'rental-videos',               AdminRentalVideoViewSet,              basename='admin-rental-videos')
router.register(r'rental-documents',            AdminRentalDocumentViewSet,           basename='admin-rental-documents')

# Paquetes de Servicio (2026-07-16)
router.register(r'service-packages',          AdminServicePackageViewSet,          basename='admin-service-packages')
router.register(r'package-included-items',    AdminPackageIncludedItemViewSet,     basename='admin-package-included-items')
router.register(r'package-additional-costs',  AdminPackageAdditionalCostViewSet,   basename='admin-package-additional-costs')

# Quotations
router.register(r'quotations',        AdminQuotationViewSet,        basename='admin-quotations')

# Constructor de Cuestionarios Tecnicos — dominio de definicion de plantillas
router.register(r'quote-template-categories', AdminQuoteTemplateCategoryViewSet, basename='admin-quote-template-categories')
router.register(r'quote-template-subcategories', AdminQuoteTemplateSubcategoryViewSet, basename='admin-quote-template-subcategories')
router.register(r'quote-templates',           AdminQuoteTemplateViewSet,         basename='admin-quote-templates')
router.register(r'quote-template-attributes', AdminQuoteTemplateAttributeViewSet, basename='admin-quote-template-attributes')
router.register(r'quote-equipment-types',     AdminQuoteEquipmentTypeViewSet,    basename='admin-quote-equipment-types')
router.register(r'quote-template-modules',    AdminQuoteTemplateModuleViewSet,   basename='admin-quote-template-modules')
router.register(r'quote-questions',           AdminQuoteQuestionViewSet,         basename='admin-quote-questions')
router.register(r'quote-question-options',    AdminQuoteQuestionOptionViewSet,   basename='admin-quote-question-options')

# Technical Services
router.register(r'services',          AdminTechnicalServiceViewSet, basename='admin-services')
router.register(r'technical-services/requests', AdminServiceRequestViewSet, basename='admin-service-requests')
router.register(r'service-categories', AdminServiceCategoryViewSet, basename='admin-service-categories')
router.register(r'service-levels',     AdminServiceLevelViewSet,    basename='admin-service-levels')
router.register(r'service-variants',   AdminServiceVariantViewSet,   basename='admin-service-variants')
router.register(r'service-faqs',       AdminServiceFAQViewSet,       basename='admin-service-faqs')

# Catalogo enriquecido de TechnicalService (2026-08-05) -- espejo del de Product (linea 97 arriba)
router.register(r'service-included-items',      AdminServiceIncludedItemViewSet,     basename='admin-service-included-items')
router.register(r'service-excluded-items',      AdminServiceExcludedItemViewSet,     basename='admin-service-excluded-items')
router.register(r'service-requirements',        AdminServiceRequirementViewSet,      basename='admin-service-requirements')
router.register(r'service-specification-groups', AdminServiceSpecificationGroupViewSet, basename='admin-service-specification-groups')
router.register(r'service-specifications',      AdminServiceSpecificationViewSet,    basename='admin-service-specifications')
router.register(r'service-documents',           AdminServiceDocumentViewSet,         basename='admin-service-documents')
router.register(r'service-videos',              AdminServiceVideoViewSet,            basename='admin-service-videos')
router.register(r'service-process-steps',       AdminServiceProcessStepViewSet,      basename='admin-service-process-steps')

# Contenido del Servicio (reingenieria SDP 2026-08-05) -- espejo de
# product-content-blocks/product-relations (linea ~117 arriba)
router.register(r'service-content-blocks',      AdminServiceContentBlockViewSet,     basename='admin-service-content-blocks')
router.register(r'service-relations',           AdminServiceRelationViewSet,         basename='admin-service-relations')

# Per-app Cost Rules (Motor de Precios Descentralizado)
router.register(r'shop-cost-rules',    AdminShopCostRuleViewSet,    basename='admin-shop-cost-rules')
router.register(r'rental-cost-rules',  AdminRentalCostRuleViewSet,  basename='admin-rental-cost-rules')
router.register(r'service-cost-rules', AdminServiceCostRuleViewSet, basename='admin-service-cost-rules')

# Marketing
router.register(r'marketing',         AdminMarketingViewSet,        basename='admin-marketing')

# Home (core)
router.register(r'home-config',       AdminHomeConfigViewSet,       basename='admin-home-config')
router.register(r'home-cards',        AdminHomeCardViewSet,         basename='admin-home-cards')
router.register(r'home-card-groups',  AdminHomeCardGroupViewSet,    basename='admin-home-card-groups')
router.register(r'feature-banner-sections', AdminFeatureBannerSectionViewSet, basename='admin-feature-banner-sections')
router.register(r'feature-banner-blocks',   AdminFeatureBannerBlockViewSet,   basename='admin-feature-banner-blocks')
router.register(r'footer',            AdminFooterViewSet,           basename='admin-footer')
router.register(r'footer-groups',     AdminFooterGroupViewSet,      basename='admin-footer-groups')
router.register(r'site-brand',        AdminSiteBrandViewSet,        basename='admin-site-brand')
router.register(r'navbar',            AdminNavbarViewSet,           basename='admin-navbar')
router.register(r'footer-cta',        AdminFooterCTAViewSet,        basename='admin-footer-cta')
router.register(r'brand-slider',      AdminBrandSliderViewSet,      basename='admin-brand-slider')
router.register(r'about-us',          AdminAboutUsViewSet,          basename='admin-about-us')

# SEO / Metaetiquetas
router.register(r'seo/meta-tags',          AdminSeoMetaTagViewSet,          basename='admin-seo-meta-tags')
router.register(r'seo/verification-files', AdminSiteVerificationFileViewSet, basename='admin-seo-verification-files')

# Support Chat
router.register(r'support/chats',     AdminSupportChatViewSet,      basename='admin-support-chats')

# Operations & Logistics
router.register(r'operations',        AdminOperationViewSet,        basename='admin-operations')
router.register(r'dispatchers',       AdminDispatcherViewSet,       basename='admin-dispatchers')

# Security
router.register(r'security-events',   AdminSecurityViewSet,         basename='admin-security-events')

# Notifications
router.register(r'notification-templates', AdminNotificationTemplateViewSet, basename='admin-notification-templates')
router.register(r'notification-logs',      AdminNotificationLogViewSet,      basename='admin-notification-logs')

# Payment
router.register(r'payment-transactions',   AdminPaymentViewSet,          basename='admin-payment-transactions')

# AI Providers (Config dinamica de modelos locales, FASE 3, 2026-08-13)
router.register(r'ai-providers',      AdminAIProviderViewSet,       basename='admin-ai-providers')
router.register(r'ai-channel-config', AdminAIChannelConfigViewSet,  basename='admin-ai-channel-config')

urlpatterns = [
    path('metrics/', AdminMetricsView.as_view(), name='admin-metrics'),
    path('', include(router.urls)),
]
