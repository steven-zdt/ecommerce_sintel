"""
Endpoints admin de organization. Sin panel propio en dashboard/ a proposito (CORE v4): esta
app es dueno de su propia API admin, siguiendo el patron ya establecido por kyc/security/
notifications/operations -- dashboard deja de ser el unico BFF a medida que cada dominio
madura (ver MIGRACION_CORE_V4_DOMINIOS_FASE1_AUDITORIA.md, hallazgo 4.D).

Todos los agregados salvo SocialLink son singletons -- mismo patron list()+update() que
AdminSiteBrandViewSet en dashboard/api/views.py.
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from users.api.permissions import IsAdminUser

from organization.services.selectors import OrganizationSelector
from organization.services.commands import OrganizationCommands
from organization.api.serializers import (
    CompanySerializer, CompanyInputSerializer,
    BrandingSerializer, BrandingInputSerializer,
    ContactInfoSerializer, ContactInfoInputSerializer,
    SocialLinkSerializer, SocialLinkInputSerializer,
    EmailSettingsSerializer, EmailSettingsInputSerializer,
    DomainSettingsSerializer, DomainSettingsInputSerializer,
    SeoSettingsSerializer, SeoSettingsInputSerializer,
    LegalEntityInfoSerializer, LegalEntityInfoInputSerializer,
)

ADMIN_PERMISSIONS = [IsAdminUser]


def _invalidate_site_config_cache():
    """
    [2026-07-12, Fase 8] Company/Branding se muestran en el endpoint publico
    core.api.views::site_config() (cache de 5 min, key 'sintel_site_config_v1'). Regresion
    real encontrada en la Fase 8 de CORE v4: escribir aqui sin invalidar esa cache dejaba el
    sitio publico mostrando datos viejos hasta que expirara el TTL. Mismo patron ya usado en
    dashboard/api/views.py -- duplicado aqui a proposito para no crear una dependencia
    `organization` -> `dashboard` (organization no deberia depender de dashboard).
    """
    from django.core.cache import cache
    from core.api.views import SITE_CONFIG_CACHE_KEY
    cache.delete(SITE_CONFIG_CACHE_KEY)


def _invalidate_footer_cache():
    """Ver _invalidate_site_config_cache() -- mismo caso para ContactInfo/SocialLink."""
    from django.core.cache import cache
    from core.api.views import FOOTER_CACHE_KEY
    cache.delete(FOOTER_CACHE_KEY)


class CompanyViewSet(viewsets.ViewSet):
    """/api/v1/organization/company/"""
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        company = OrganizationSelector.get_company()
        return Response(CompanySerializer(company).data if company else None)

    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_company(self, request):
        s = CompanyInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        company = OrganizationCommands.upsert_company(s.validated_data)
        _invalidate_site_config_cache()
        return Response(CompanySerializer(company).data)


class BrandingViewSet(viewsets.ViewSet):
    """/api/v1/organization/branding/"""
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request):
        branding = OrganizationSelector.get_branding()
        return Response(BrandingSerializer(branding, context={'request': request}).data if branding else None)

    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_branding(self, request):
        s = BrandingInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        branding = OrganizationCommands.upsert_branding(s.validated_data)
        _invalidate_site_config_cache()
        return Response(BrandingSerializer(branding, context={'request': request}).data)


class ContactInfoViewSet(viewsets.ViewSet):
    """/api/v1/organization/contact/"""
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        contact = OrganizationSelector.get_contact_info()
        return Response(ContactInfoSerializer(contact).data if contact else None)

    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_contact(self, request):
        s = ContactInfoInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        contact = OrganizationCommands.upsert_contact_info(s.validated_data)
        _invalidate_footer_cache()
        return Response(ContactInfoSerializer(contact).data)


class SocialLinkViewSet(viewsets.ViewSet):
    """/api/v1/organization/social-links/ -- unico agregado no-singleton (CRUD completo)."""
    permission_classes = ADMIN_PERMISSIONS
    lookup_field = 'uuid'

    def list(self, request):
        links = OrganizationSelector.list_social_links(active_only=False)
        return Response(SocialLinkSerializer(links, many=True).data)

    def create(self, request):
        s = SocialLinkInputSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        link = OrganizationCommands.create_social_link(
            platform=d['platform'], url=d['url'],
            icon_class=d.get('icon_class', ''), display_order=d.get('display_order', 0),
        )
        _invalidate_footer_cache()
        return Response(SocialLinkSerializer(link).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, uuid=None):
        link = OrganizationSelector.get_social_link_by_uuid(uuid)
        s = SocialLinkInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        link = OrganizationCommands.update_social_link(link, s.validated_data)
        _invalidate_footer_cache()
        return Response(SocialLinkSerializer(link).data)

    def destroy(self, request, uuid=None):
        link = OrganizationSelector.get_social_link_by_uuid(uuid)
        OrganizationCommands.delete_social_link(link)
        _invalidate_footer_cache()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EmailSettingsViewSet(viewsets.ViewSet):
    """/api/v1/organization/email-settings/ -- solo datos de negocio, NUNCA secretos SMTP."""
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        settings_obj = OrganizationSelector.get_email_settings()
        return Response(EmailSettingsSerializer(settings_obj).data if settings_obj else None)

    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_settings(self, request):
        s = EmailSettingsInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        settings_obj = OrganizationCommands.upsert_email_settings(s.validated_data)
        return Response(EmailSettingsSerializer(settings_obj).data)


class DomainSettingsViewSet(viewsets.ViewSet):
    """/api/v1/organization/domain-settings/"""
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        settings_obj = OrganizationSelector.get_domain_settings()
        return Response(DomainSettingsSerializer(settings_obj).data if settings_obj else None)

    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_settings(self, request):
        s = DomainSettingsInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        settings_obj = OrganizationCommands.upsert_domain_settings(s.validated_data)
        return Response(DomainSettingsSerializer(settings_obj).data)


class SeoSettingsViewSet(viewsets.ViewSet):
    """/api/v1/organization/seo-settings/"""
    permission_classes = ADMIN_PERMISSIONS
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request):
        settings_obj = OrganizationSelector.get_seo_settings()
        return Response(SeoSettingsSerializer(settings_obj, context={'request': request}).data if settings_obj else None)

    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_settings(self, request):
        s = SeoSettingsInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        settings_obj = OrganizationCommands.upsert_seo_settings(s.validated_data)
        _invalidate_site_config_cache()
        return Response(SeoSettingsSerializer(settings_obj, context={'request': request}).data)


class LegalEntityInfoViewSet(viewsets.ViewSet):
    """/api/v1/organization/legal-entity/"""
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request):
        info = OrganizationSelector.get_legal_entity_info()
        return Response(LegalEntityInfoSerializer(info).data if info else None)

    @action(detail=False, methods=['post', 'patch'], url_path='update')
    def update_info(self, request):
        s = LegalEntityInfoInputSerializer(data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        info = OrganizationCommands.upsert_legal_entity_info(s.validated_data)
        return Response(LegalEntityInfoSerializer(info).data)
