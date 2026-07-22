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
    AdminServiceCategoryViewSet,
    AdminServiceLevelViewSet,
    AdminServiceVariantViewSet,
    AdminServiceFAQViewSet,
    AdminMarketingViewSet,
    AdminShopCostRuleViewSet,
    AdminRentalCostRuleViewSet,
    AdminServiceCostRuleViewSet,
    AdminHomeConfigViewSet,
    AdminHomeCardViewSet,
    AdminHomeCardGroupViewSet,
    AdminFooterViewSet,
    AdminFooterGroupViewSet,
    AdminSiteBrandViewSet,
    AdminNavbarViewSet,
    AdminFooterCTAViewSet,
    AdminBrandSliderViewSet,
    AdminAboutUsViewSet,
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
from operations.api.views import AdminOperationViewSet, AdminDispatcherViewSet

router = DefaultRouter()

# Users: administrado en /api/v1/users/ (users.api.views.UserViewSet), no aca.

# Shop
router.register(r'products',          AdminProductViewSet,          basename='admin-products')
router.register(r'categories',        AdminCategoryViewSet,         basename='admin-categories')
router.register(r'brands',            AdminBrandViewSet,            basename='admin-brands')
router.register(r'taxes',             AdminTaxViewSet,              basename='admin-taxes')

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
router.register(r'service-categories', AdminServiceCategoryViewSet, basename='admin-service-categories')
router.register(r'service-levels',     AdminServiceLevelViewSet,    basename='admin-service-levels')
router.register(r'service-variants',   AdminServiceVariantViewSet,   basename='admin-service-variants')
router.register(r'service-faqs',       AdminServiceFAQViewSet,       basename='admin-service-faqs')

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
router.register(r'footer',            AdminFooterViewSet,           basename='admin-footer')
router.register(r'footer-groups',     AdminFooterGroupViewSet,      basename='admin-footer-groups')
router.register(r'site-brand',        AdminSiteBrandViewSet,        basename='admin-site-brand')
router.register(r'navbar',            AdminNavbarViewSet,           basename='admin-navbar')
router.register(r'footer-cta',        AdminFooterCTAViewSet,        basename='admin-footer-cta')
router.register(r'brand-slider',      AdminBrandSliderViewSet,      basename='admin-brand-slider')
router.register(r'about-us',          AdminAboutUsViewSet,          basename='admin-about-us')

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

urlpatterns = [
    path('metrics/', AdminMetricsView.as_view(), name='admin-metrics'),
    path('', include(router.urls)),
]
