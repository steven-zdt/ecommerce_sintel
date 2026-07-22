"""
OrganizationSelector -- Fase 5. Unico punto de lectura de los agregados de
organization. Ninguna otra app debe consultar los modelos directamente.
"""
from django.shortcuts import get_object_or_404

from organization.models import (
    Company, Branding, ContactInfo, SocialLink,
    EmailSettings, DomainSettings, SeoSettings, LegalEntityInfo,
)


class OrganizationSelector:

    # ── Empresa / Branding ──────────────────────────────────────────────
    @staticmethod
    def get_company():
        return Company.objects.filter(is_active=True, is_deleted=False).first()

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

    # ── Correos ──────────────────────────────────────────────────────────
    @staticmethod
    def get_email_settings():
        return EmailSettings.objects.filter(is_active=True, is_deleted=False).first()

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

    # ── Integraciones (fachada de solo lectura sobre settings) ──────────
    @staticmethod
    def get_integration_settings():
        """
        Los tokens de Meta/WhatsApp/Facebook/Instagram/YouTube/TikTok/X/Google
        Business siguen viviendo en settings/.env -- decision de seguridad
        confirmada 2026-07-12 (misma logica que EmailSettings: los secretos
        operativos no se centralizan en BD). Esta fachada existe para que los
        consumidores (marketing/channels/*, notifications/clients/whatsapp.py)
        puedan migrar a leer de OrganizationSelector sin que el dato en si
        cambie de lugar -- ver Fase 6 (consumidor Marketing), todavia no
        ejecutada.
        """
        from django.conf import settings
        return {
            'meta_access_token': settings.META_ACCESS_TOKEN,
            'whatsapp_phone_number_id': settings.WHATSAPP_PHONE_NUMBER_ID,
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
