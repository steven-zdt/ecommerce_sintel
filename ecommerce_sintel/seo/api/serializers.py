from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.html import strip_tags
from rest_framework import serializers

from seo.models import SiteMetaTag, SeoMetaTagAuditLog, SiteVerificationFile
from seo.services.sanitizer import sanitize_meta_html


def _strip_html_fields(attrs: dict, fields=('name', 'description')) -> dict:
    """Defensa en profundidad contra XSS almacenado en campos de texto plano
    -- mismo patron que core/api/serializers.py::_strip_html_fields."""
    for key in fields:
        if key in attrs and isinstance(attrs[key], str):
            attrs[key] = strip_tags(attrs[key]).strip()
    return attrs


class SiteMetaTagSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source='get_provider_display', read_only=True)
    tag_type_label = serializers.CharField(source='get_tag_type_display', read_only=True)
    environment_label = serializers.CharField(source='get_environment_display', read_only=True)
    rendered_html = serializers.SerializerMethodField()
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True, default=None)
    updated_by_email = serializers.EmailField(source='updated_by.email', read_only=True, default=None)

    class Meta:
        model = SiteMetaTag
        fields = [
            'uuid', 'name', 'provider', 'provider_label', 'tag_type', 'tag_type_label',
            'description', 'meta_name', 'meta_content', 'html_snippet',
            'priority', 'is_active', 'target_page', 'environment', 'environment_label',
            'rendered_html', 'created_by_email', 'updated_by_email',
            'created_at', 'updated_at',
        ]

    def get_rendered_html(self, obj):
        return obj.to_html()


class SiteMetaTagInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    provider = serializers.ChoiceField(choices=SiteMetaTag.PROVIDER_CHOICES)
    tag_type = serializers.ChoiceField(choices=SiteMetaTag.TYPE_CHOICES)
    description = serializers.CharField(required=False, allow_blank=True, default='')
    meta_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    meta_content = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    html_snippet = serializers.CharField(required=False, allow_blank=True, default='')
    priority = serializers.IntegerField(required=False, default=0, min_value=0)
    is_active = serializers.BooleanField(required=False, default=True)
    target_page = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    environment = serializers.ChoiceField(choices=SiteMetaTag.ENV_CHOICES, required=False, default=SiteMetaTag.ENV_ALL)

    def validate_html_snippet(self, value):
        try:
            return sanitize_meta_html(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

    def validate(self, attrs):
        attrs = _strip_html_fields(attrs)
        has_meta_pair = bool(attrs.get('meta_name')) and bool(attrs.get('meta_content'))
        has_snippet = bool(attrs.get('html_snippet'))
        if not has_meta_pair and not has_snippet:
            raise serializers.ValidationError({
                'meta_name': 'Se requiere meta_name + meta_content, o un html_snippet valido.',
            })
        if bool(attrs.get('meta_name')) != bool(attrs.get('meta_content')):
            raise serializers.ValidationError({
                'meta_content': 'meta_name y meta_content deben completarse juntos.',
            })
        return attrs


class SiteMetaTagReorderSerializer(serializers.Serializer):
    items = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)


class SiteMetaTagImportSerializer(serializers.Serializer):
    items = SiteMetaTagInputSerializer(many=True)


class SiteVerificationFileSerializer(serializers.ModelSerializer):
    provider_label = serializers.CharField(source='get_provider_display', read_only=True)
    url_path = serializers.SerializerMethodField()

    class Meta:
        model = SiteVerificationFile
        fields = [
            'uuid', 'name', 'provider', 'provider_label', 'filename', 'content',
            'is_active', 'url_path', 'created_at', 'updated_at',
        ]

    def get_url_path(self, obj):
        return f'/{obj.filename}'


class SiteVerificationFileInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    provider = serializers.ChoiceField(choices=SiteMetaTag.PROVIDER_CHOICES)
    filename = serializers.RegexField(
        r'^[A-Za-z0-9._-]+\.html$', max_length=255,
        error_messages={'invalid': 'Solo letras, numeros, puntos, guiones y guion bajo, terminado en .html.'},
    )
    # `content` es intencionalmente texto crudo sin sanitizar: este recurso
    # sirve el archivo TAL CUAL en la raiz del dominio -- el proveedor externo
    # (Meta, Google Search Console...) exige un contenido exacto, a veces un
    # documento HTML completo. El campo esta detras de ADMIN_PERMISSIONS
    # (solo staff+superuser); no es un input de usuario final.
    content = serializers.CharField()
    is_active = serializers.BooleanField(required=False, default=True)

    def validate_name(self, value):
        return strip_tags(value).strip()


class SeoMetaTagAuditLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True, default=None)

    class Meta:
        model = SeoMetaTagAuditLog
        fields = [
            'uuid', 'meta_tag_name', 'action', 'action_label',
            'user_email', 'ip_address', 'changes', 'created_at',
        ]
