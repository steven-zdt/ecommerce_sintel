"""
OrganizationSelector -- Fase 5. Unico punto de lectura de los agregados de
organization. Ninguna otra app debe consultar los modelos directamente.
"""
from django.shortcuts import get_object_or_404

from organization.models import (
    Company, Branding, ContactInfo, SocialLink,
    EmailSettings, DomainSettings, SeoSettings, LegalEntityInfo, LegalDocument,
)

# Fase 10 (AUDITORIA/25_AUDITORIA_ORGANIZATION.md, 2026-08-01): get_email_settings() se llama
# sin cache desde notifications/tasks.py, accounts/services/commands.py, users/services/
# commands.py, marketing/channels/email_channel.py y users/api/admin_auth.py -- un SELECT extra
# por cada envio de email, inconsistente con Company/Branding/ContactInfo (que si tienen cache
# en el endpoint publico de core). Invalidada explicitamente en
# OrganizationCommands.upsert_email_settings() -- el unico punto de escritura real, no en el
# ViewSet (a diferencia de Company/Branding/ContactInfo, cuyo cache vive en el endpoint publico
# core.api.views, un concepto distinto a este selector interno).
EMAIL_SETTINGS_CACHE_KEY = 'sintel_org_email_settings_v1'
EMAIL_SETTINGS_CACHE_TTL = 60 * 5


class OrganizationSelector:

    # ── Empresa / Branding ──────────────────────────────────────────────
    @staticmethod
    def get_company():
        return Company.objects.filter(is_active=True, is_deleted=False).first()

    @staticmethod
    def get_display_name(default=''):
        """Nombre comercial a mostrar cuando el llamador no tiene una regla de
        fallback propia. Consolida en un unico lugar el literal 'Sintel' que
        antes estaba duplicado en core/api/views.py, dashboard/api/views.py y
        seo/templatetags/seo_tags.py (ver white-label readiness audit,
        AUDITORIA/WHITE_LABEL/WHITE_LABEL_IDENTITY_COUPLING_AUDIT.md)."""
        company = OrganizationSelector.get_company()
        if company and company.trade_name:
            return company.trade_name
        return default

    @staticmethod
    def get_branding():
        return Branding.objects.filter(is_active=True, is_deleted=False).first()

    # ── Contacto ─────────────────────────────────────────────────────────
    @staticmethod
    def get_contact_info():
        return ContactInfo.objects.filter(is_active=True, is_deleted=False).first()

    # ── Redes Sociales ───────────────────────────────────────────────────
    @staticmethod
    def list_social_links(active_only=True):
        qs = SocialLink.objects.filter(is_deleted=False)
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by('display_order')

    @staticmethod
    def get_social_link_by_uuid(uuid):
        return get_object_or_404(SocialLink, uuid=uuid, is_deleted=False)

    @staticmethod
    def find_social_link_by_uuid(uuid):
        """Como get_social_link_by_uuid pero devuelve None en vez de 404 --
        para callers que necesitan distinguir 'no es un social link' de un
        error real (ej. dashboard.AdminFooterViewSet, que usa el mismo uuid
        param para social links y footer links normales). Consolida el
        acceso directo a SocialLink.objects que antes vivia en
        dashboard/api/views.py (white-label F2, 2026-08-14)."""
        return SocialLink.objects.filter(uuid=uuid, is_deleted=False).first()

    # ── Correos ──────────────────────────────────────────────────────────
    @staticmethod
    def get_email_settings():
        from django.core.cache import cache
        cached = cache.get(EMAIL_SETTINGS_CACHE_KEY)
        if cached is not None:
            return cached
        settings_obj = EmailSettings.objects.filter(is_active=True, is_deleted=False).first()
        if settings_obj is not None:
            cache.set(EMAIL_SETTINGS_CACHE_KEY, settings_obj, EMAIL_SETTINGS_CACHE_TTL)
        return settings_obj

    # ── Dominios ─────────────────────────────────────────────────────────
    @staticmethod
    def get_domain_settings():
        return DomainSettings.objects.filter(is_active=True, is_deleted=False).first()

    # ── SEO ──────────────────────────────────────────────────────────────
    @staticmethod
    def get_seo_settings():
        return SeoSettings.objects.filter(is_active=True, is_deleted=False).first()

    # ── Informacion Legal ────────────────────────────────────────────────
    @staticmethod
    def get_legal_entity_info():
        return LegalEntityInfo.objects.filter(is_active=True, is_deleted=False).first()

    @staticmethod
    def get_legal_document(doc_type):
        # 'privacidad' es un alias de 'politica' -- mismo docType que usaba
        # LEGAL_DOCS.privacidad = LEGAL_DOCS.politica en legalDocs.js (ver
        # comentario original sobre el enlace del footer "#privacidad").
        if doc_type == LegalDocument.DOC_PRIVACIDAD or doc_type == 'privacidad':
            doc_type = LegalDocument.DOC_PRIVACIDAD
        return LegalDocument.objects.filter(doc_type=doc_type, is_active=True, is_deleted=False).first()

    @staticmethod
    def list_legal_documents():
        return LegalDocument.objects.filter(is_deleted=False).order_by('doc_type')

    # ── Integraciones (fachada de solo lectura sobre settings) ──────────
    @staticmethod
    def get_integration_settings():
        """
        Los tokens de Meta/WhatsApp/Facebook/Instagram/YouTube/TikTok/X/Google
        Business siguen viviendo en settings/.env -- decision de seguridad
        confirmada 2026-07-12 (misma logica que EmailSettings: los secretos
        operativos no se centralizan en BD). Esta fachada existe para que los
        consumidores (marketing/channels/*, marketing/integrations/meta/*,
        notifications/clients/whatsapp.py) puedan leer de OrganizationSelector
        sin que el dato en si cambie de lugar.

        FASE 1 (integracion Meta Business, 2026-08-31): se agregaron las claves
        meta_graph_api_version / meta_business_id / meta_waba_id /
        meta_ad_account_id / meta_catalog_id / meta_pixel_id / meta_dataset_id /
        whatsapp_webhook_verify_token / meta_app_secret. Son IDs de activos
        publicos (salvo meta_app_secret, que es el secreto de firma de webhooks),
        y siguen la misma regla: aqui es solo lectura, el valor vive en .env.
        """
        from django.conf import settings
        return {
            'meta_access_token': settings.META_ACCESS_TOKEN,
            'meta_app_secret': settings.META_APP_SECRET,
            'meta_graph_api_version': settings.META_GRAPH_API_VERSION,
            'meta_business_id': settings.META_BUSINESS_ID,
            'meta_waba_id': settings.META_WABA_ID,
            'meta_ad_account_id': settings.META_AD_ACCOUNT_ID,
            'meta_catalog_id': settings.META_CATALOG_ID,
            'meta_pixel_id': settings.META_PIXEL_ID,
            'meta_dataset_id': settings.META_DATASET_ID,
            'whatsapp_phone_number_id': settings.WHATSAPP_PHONE_NUMBER_ID,
            'whatsapp_webhook_verify_token': settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN,
            'facebook_page_id': settings.FACEBOOK_PAGE_ID,
            'instagram_business_account_id': settings.INSTAGRAM_BUSINESS_ACCOUNT_ID,
            'youtube_client_id': settings.YOUTUBE_CLIENT_ID,
            'youtube_client_secret': settings.YOUTUBE_CLIENT_SECRET,
            'youtube_refresh_token': settings.YOUTUBE_REFRESH_TOKEN,
            'tiktok_access_token': settings.TIKTOK_ACCESS_TOKEN,
            'x_bearer_token': settings.X_BEARER_TOKEN,
            'google_business_client_id': settings.GOOGLE_BUSINESS_CLIENT_ID,
            'google_business_client_secret': settings.GOOGLE_BUSINESS_CLIENT_SECRET,
            'google_business_refresh_token': settings.GOOGLE_BUSINESS_REFRESH_TOKEN,
            'google_business_location_name': settings.GOOGLE_BUSINESS_LOCATION_NAME,
        }
