from rest_framework.routers import DefaultRouter

from organization.api.views import (
    CompanyViewSet, BrandingViewSet, ContactInfoViewSet, SocialLinkViewSet,
    EmailSettingsViewSet, DomainSettingsViewSet, SeoSettingsViewSet, LegalEntityInfoViewSet,
    LegalDocumentViewSet, CommunicationEventViewSet,
)

router = DefaultRouter()
router.register(r'company', CompanyViewSet, basename='organization-company')
router.register(r'branding', BrandingViewSet, basename='organization-branding')
router.register(r'contact', ContactInfoViewSet, basename='organization-contact')
router.register(r'social-links', SocialLinkViewSet, basename='organization-social-links')
router.register(r'email-settings', EmailSettingsViewSet, basename='organization-email-settings')
router.register(r'domain-settings', DomainSettingsViewSet, basename='organization-domain-settings')
router.register(r'seo-settings', SeoSettingsViewSet, basename='organization-seo-settings')
router.register(r'legal-entity', LegalEntityInfoViewSet, basename='organization-legal-entity')
router.register(r'legal-documents', LegalDocumentViewSet, basename='organization-legal-documents')
router.register(r'communication-events', CommunicationEventViewSet, basename='organization-communication-events')

urlpatterns = router.urls
