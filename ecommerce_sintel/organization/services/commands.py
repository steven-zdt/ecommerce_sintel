"""
OrganizationCommands -- Fase 5. Escritura (create/update/delete) de los
agregados de organization. Sin signals: si en el futuro un consumidor necesita
invalidar cache al escribir aqui, la invalidacion debe hacerse explicita en el
caller (mismo patron que ya usan los ViewSets admin de core/dashboard), nunca
via post_save/post_delete.
"""
from django.db import transaction

from organization.models import (
    Company, Branding, ContactInfo, SocialLink,
    EmailSettings, DomainSettings, SeoSettings, LegalEntityInfo,
    CommunicationEvent, LegalDocument,
)
from organization.services.selectors import OrganizationSelector


class OrganizationCommands:

    # ── Empresa ──────────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_company(data):
        company = OrganizationSelector.get_company()
        if not company:
            company = Company.objects.create(trade_name=data.get('trade_name', 'Sintel'))
        for field in ('trade_name', 'description', 'founded_year'):
            if field in data:
                setattr(company, field, data[field])
        company.save()
        return company

    # ── Branding ─────────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_branding(data):
        branding = OrganizationSelector.get_branding()
        if not branding:
            branding = Branding.objects.create()
        if data.pop('remove_logo', False):
            branding.logo = None
        if data.pop('remove_favicon', False):
            branding.favicon = None
        for field in ('logo', 'favicon', 'tagline', 'primary_color', 'accent_color'):
            if field in data:
                setattr(branding, field, data[field])
        branding.save()
        return branding

    # ── Contacto ─────────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_contact_info(data):
        contact = OrganizationSelector.get_contact_info()
        if contact:
            for field in ('phone', 'email', 'address', 'working_hours'):
                if field in data:
                    setattr(contact, field, data[field])
            contact.save()
        else:
            contact = ContactInfo.objects.create(
                phone=data.get('phone', ''),
                email=data.get('email', ''),
                address=data.get('address', ''),
                working_hours=data.get('working_hours', ''),
            )
        return contact

    # ── Redes Sociales ───────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def create_social_link(platform, url, icon_class='', display_order=0):
        return SocialLink.objects.create(
            platform=platform, url=url, icon_class=icon_class, display_order=display_order,
        )

    @staticmethod
    @transaction.atomic
    def update_social_link(link, data):
        allowed = ('platform', 'url', 'icon_class', 'display_order', 'is_active')
        for field in allowed:
            if field in data:
                setattr(link, field, data[field])
        link.save()
        return link

    @staticmethod
    @transaction.atomic
    def delete_social_link(link):
        link.is_active = False
        link.is_deleted = True
        link.save(update_fields=['is_active', 'is_deleted'])

    # ── Correos ──────────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_email_settings(data):
        settings_obj = OrganizationSelector.get_email_settings()
        if not settings_obj:
            settings_obj = EmailSettings.objects.create()
        for field in ('default_from_email', 'frontend_base_url', 'admin_login_url'):
            if field in data:
                setattr(settings_obj, field, data[field])
        settings_obj.save()
        # Fase 10 (AUDITORIA/25_AUDITORIA_ORGANIZATION.md, 2026-08-01): invalidar aqui, no solo
        # en el ViewSet -- OrganizationSelector.get_email_settings() (llamado arriba para
        # encontrar la fila a actualizar) cachea la version PRE-update; si la invalidacion solo
        # viviera en la vista, cualquier otro caller de este command (management commands,
        # otros services, tests) dejaria el cache envenenado con datos viejos sin que nada lo
        # limpie despues. El command es el unico punto de escritura real -- invalida aqui.
        from django.core.cache import cache
        from organization.services.selectors import EMAIL_SETTINGS_CACHE_KEY
        cache.delete(EMAIL_SETTINGS_CACHE_KEY)
        return settings_obj

    # ── Dominios ─────────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_domain_settings(data):
        settings_obj = OrganizationSelector.get_domain_settings()
        if not settings_obj:
            settings_obj = DomainSettings.objects.create()
        for field in ('primary_domain', 'admin_panel_domain', 'api_domain'):
            if field in data:
                setattr(settings_obj, field, data[field])
        settings_obj.save()
        return settings_obj

    # ── SEO ──────────────────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_seo_settings(data):
        settings_obj = OrganizationSelector.get_seo_settings()
        if not settings_obj:
            settings_obj = SeoSettings.objects.create()
        if data.pop('remove_og_image', False):
            settings_obj.og_image = None
        for field in ('meta_title', 'meta_description', 'og_image'):
            if field in data:
                setattr(settings_obj, field, data[field])
        settings_obj.save()
        return settings_obj

    # ── Centro de Comunicacion ───────────────────────────────────────────
    @staticmethod
    def log_communication_event(*, event_type, channel='', module='', user=None, metadata=None):
        """
        Sin @transaction.atomic: un solo INSERT, no hay nada mas que
        coordinar. Nunca debe tumbar la request del visitante -- el caller
        (la vista) es responsable de no dejar que un fallo aqui rompa la
        experiencia real del boton de contacto.
        """
        return CommunicationEvent.objects.create(
            event_type=event_type,
            channel=channel,
            module=module,
            user=user if (user is not None and user.is_authenticated) else None,
            metadata=metadata or {},
        )

    # ── Informacion Legal ────────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_legal_entity_info(data):
        info = OrganizationSelector.get_legal_entity_info()
        if not info:
            info = LegalEntityInfo.objects.create()
        allowed = (
            'legal_name', 'tax_id', 'fiscal_address',
            'legal_representative', 'city', 'department',
        )
        for field in allowed:
            if field in data:
                setattr(info, field, data[field])
        info.save()
        return info

    # ── Documentos legales ───────────────────────────────────────────────
    @staticmethod
    @transaction.atomic
    def upsert_legal_document(doc_type, data):
        """White-label F5 -- doc_type es la clave natural (unique=True), no
        hay concepto de singleton is_active como en el resto de la app: cada
        doc_type es su propio documento independiente."""
        doc, _ = LegalDocument.objects.get_or_create(
            doc_type=doc_type, defaults={'title': data.get('title', doc_type)},
        )
        allowed = ('title', 'updated_label', 'sections', 'is_active')
        for field in allowed:
            if field in data:
                setattr(doc, field, data[field])
        doc.save()
        return doc
