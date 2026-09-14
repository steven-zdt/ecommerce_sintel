import re

from rest_framework import serializers

from organization.models import (
    Company, Branding, ContactInfo, SocialLink,
    EmailSettings, DomainSettings, SeoSettings, LegalEntityInfo,
    CommunicationEvent, LegalDocument,
)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['uuid', 'trade_name', 'description', 'founded_year', 'updated_at']


class CompanyInputSerializer(serializers.Serializer):
    trade_name = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    founded_year = serializers.IntegerField(required=False, allow_null=True)


class BrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branding
        fields = ['uuid', 'logo', 'favicon', 'tagline', 'primary_color', 'accent_color', 'updated_at']


class BrandingInputSerializer(serializers.Serializer):
    logo = serializers.ImageField(required=False, allow_null=True)
    favicon = serializers.ImageField(required=False, allow_null=True)
    tagline = serializers.CharField(max_length=300, required=False, allow_blank=True)
    primary_color = serializers.CharField(max_length=20, required=False, allow_blank=True)
    accent_color = serializers.CharField(max_length=20, required=False, allow_blank=True)
    remove_logo = serializers.BooleanField(required=False, default=False)
    remove_favicon = serializers.BooleanField(required=False, default=False)


class ContactInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInfo
        fields = ['id', 'uuid', 'phone', 'email', 'address', 'working_hours', 'is_active', 'updated_at']


# Fase 10 (AUDITORIA/25_AUDITORIA_ORGANIZATION.md, 2026-08-01): mismo patron de celular
# colombiano ya usado en notifications/services/commands.py::_PHONE_RE -- antes se guardaba
# cualquier texto sin validar y solo se descubria roto cuando el Communication Center intentaba
# usarlo (el numero institucional de WhatsApp viene de este mismo campo).
_COLOMBIA_PHONE_RE = re.compile(r'^3\d{9}$')


class ContactInfoInputSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    email = serializers.EmailField(max_length=254, required=False, allow_blank=True, default='')
    address = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    working_hours = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate_phone(self, value):
        # ContactInfo ya existia antes de que se aplicara la validacion estricta y
        # produccion conserva numeros con formatos como "+57 314 460 1878". Aceptar
        # los separadores habituales, quitar el indicativo colombiano y persistir
        # siempre los diez digitos locales para que el resto de consumidores tenga
        # un formato unico.
        normalized = re.sub(r'[^0-9]', '', value)
        if normalized.startswith('57') and len(normalized) == 12:
            normalized = normalized[2:]

        if normalized and not _COLOMBIA_PHONE_RE.fullmatch(normalized):
            raise serializers.ValidationError(
                'Numero de telefono colombiano invalido -- debe tener 10 digitos e iniciar con 3.'
            )
        return normalized


class SocialLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialLink
        fields = ['id', 'uuid', 'platform', 'url', 'icon_class', 'display_order', 'is_active', 'created_at']


class SocialLinkInputSerializer(serializers.Serializer):
    platform = serializers.CharField(max_length=100)
    url = serializers.CharField(max_length=500)
    icon_class = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active = serializers.BooleanField(required=False, default=True)


class EmailSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailSettings
        fields = ['uuid', 'default_from_email', 'frontend_base_url', 'admin_login_url', 'updated_at']


class EmailSettingsInputSerializer(serializers.Serializer):
    default_from_email = serializers.EmailField(max_length=254, required=False, allow_blank=True)
    frontend_base_url = serializers.CharField(max_length=300, required=False, allow_blank=True)
    admin_login_url = serializers.CharField(max_length=300, required=False, allow_blank=True)


class DomainSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainSettings
        fields = ['uuid', 'primary_domain', 'admin_panel_domain', 'api_domain', 'updated_at']


class DomainSettingsInputSerializer(serializers.Serializer):
    primary_domain = serializers.CharField(max_length=255, required=False, allow_blank=True)
    admin_panel_domain = serializers.CharField(max_length=255, required=False, allow_blank=True)
    api_domain = serializers.CharField(max_length=255, required=False, allow_blank=True)


class SeoSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeoSettings
        fields = ['uuid', 'meta_title', 'meta_description', 'og_image', 'updated_at']


class SeoSettingsInputSerializer(serializers.Serializer):
    meta_title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    meta_description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    og_image = serializers.ImageField(required=False, allow_null=True)
    remove_og_image = serializers.BooleanField(required=False, default=False)


class LegalEntityInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalEntityInfo
        fields = [
            'uuid', 'legal_name', 'tax_id', 'fiscal_address',
            'legal_representative', 'city', 'department', 'updated_at',
        ]


class LegalEntityInfoInputSerializer(serializers.Serializer):
    legal_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tax_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    fiscal_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    legal_representative = serializers.CharField(max_length=255, required=False, allow_blank=True)
    city = serializers.CharField(max_length=150, required=False, allow_blank=True)
    department = serializers.CharField(max_length=150, required=False, allow_blank=True)


class LegalDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LegalDocument
        fields = ['uuid', 'doc_type', 'title', 'updated_label', 'sections', 'is_active', 'updated_at']


class LegalDocumentInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    updated_label = serializers.CharField(max_length=100, required=False, allow_blank=True)
    sections = serializers.JSONField(required=False)
    is_active = serializers.BooleanField(required=False)


class CommunicationEventInputSerializer(serializers.Serializer):
    """Entrada publica (visitantes anonimos incluidos) del Centro de Comunicacion."""
    event_type = serializers.ChoiceField(choices=CommunicationEvent.EVENT_CHOICES)
    channel = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')
    module = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    metadata = serializers.DictField(required=False, default=dict)
