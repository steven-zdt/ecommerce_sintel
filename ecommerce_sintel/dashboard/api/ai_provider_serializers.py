"""
dashboard/api/ai_provider_serializers.py

Serializers del panel admin de proveedores/modelos de IA (plan maestro
"CONFIGURACION DINAMICA DE MODELOS LOCALES", FASE 3, 2026-08-13). Archivo separado
del `serializers.py` principal siguiendo el mismo criterio de split ya usado por
`services_catalog_views.py` -- dominio autocontenido, evita seguir engordando el
archivo central.

Regla dura (regla del plan maestro, "API key nunca se envia al frontend"):
`AIProviderSerializer` (lectura) NUNCA incluye `api_key` -- solo `has_api_key`.
`AIProviderInputSerializer` (escritura) acepta `api_key` como write-only y opcional;
vacio en un update significa "no cambiar" (ver AIProviderCommands.update_provider).
"""
from rest_framework import serializers

from ai_provider.models import AIChannelConfig, AIModel, AIProvider


class AIModelSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    model_id = serializers.CharField()
    display_name = serializers.CharField(allow_blank=True)
    is_active = serializers.BooleanField()
    is_default = serializers.BooleanField(required=False)
    discovered_automatically = serializers.BooleanField(read_only=True)
    temperature = serializers.FloatField(required=False, allow_null=True)
    max_tokens = serializers.IntegerField(required=False, allow_null=True)
    context_window = serializers.IntegerField(required=False, allow_null=True)


class AIProviderSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(read_only=True)
    name = serializers.CharField()
    slug = serializers.CharField(read_only=True)
    kind = serializers.ChoiceField(choices=AIProvider.KIND_CHOICES)
    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    base_url = serializers.CharField(allow_blank=True)
    has_api_key = serializers.SerializerMethodField()
    is_active = serializers.BooleanField()
    is_default = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField()
    timeout = serializers.IntegerField(required=False)
    max_retries = serializers.IntegerField(required=False)
    config_version = serializers.IntegerField(read_only=True)
    last_tested_at = serializers.DateTimeField(read_only=True)
    last_test_ok = serializers.BooleanField(read_only=True)
    last_test_latency_ms = serializers.IntegerField(read_only=True)
    last_test_error = serializers.CharField(read_only=True)
    models = AIModelSerializer(many=True, read_only=True)

    def get_has_api_key(self, obj) -> bool:
        return bool(obj.api_key)


class AIProviderInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    kind = serializers.ChoiceField(choices=AIProvider.KIND_CHOICES)
    base_url = serializers.CharField(max_length=500, allow_blank=True, required=False)
    api_key = serializers.CharField(allow_blank=True, required=False, write_only=True)
    is_active = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField(required=False)
    timeout = serializers.IntegerField(required=False)
    max_retries = serializers.IntegerField(required=False)


class AIModelInputSerializer(serializers.Serializer):
    model_id = serializers.CharField(max_length=200)
    display_name = serializers.CharField(max_length=200, allow_blank=True, required=False)


class AIChannelFallbackSerializer(serializers.Serializer):
    uuid = serializers.UUIDField(source='model.uuid', read_only=True)
    model_id = serializers.CharField(source='model.model_id', read_only=True)
    order = serializers.IntegerField()


class AIChannelConfigSerializer(serializers.Serializer):
    channel = serializers.CharField(read_only=True)
    enabled = serializers.BooleanField(required=False)
    config_version = serializers.IntegerField(read_only=True)
    primary_model = AIModelSerializer(read_only=True)
    fallbacks = serializers.SerializerMethodField()
    updated_at = serializers.DateTimeField(read_only=True)

    def get_fallbacks(self, obj: AIChannelConfig):
        return AIChannelFallbackSerializer(
            obj.fallbacks.filter(is_deleted=False).select_related('model').order_by('order'), many=True,
        ).data


class AIConfigRevisionSerializer(serializers.Serializer):
    """Historial de configuracion (PLAN_LLMDINAMICO F18). El snapshot no contiene secretos por construccion (ver revisions.py)."""
    version = serializers.IntegerField()
    scope = serializers.CharField()
    action = serializers.CharField()
    snapshot = serializers.JSONField()
    changed_by = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField()

    def get_changed_by(self, obj):
        return getattr(obj.changed_by, 'email', None)
