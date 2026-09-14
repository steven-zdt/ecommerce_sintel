from django.db import transaction
from django.utils import timezone

from ai_provider.models import AIChannelConfig, AIChannelFallback, AIModel, AIProvider
from ai_provider.services import runtime_cache

_PROVIDER_ALLOWED_FIELDS = (
    'name', 'kind', 'base_url', 'api_key', 'is_active', 'display_order', 'timeout', 'max_retries', 'metadata',
)
_MODEL_ALLOWED_FIELDS = ('display_name', 'is_active', 'temperature', 'max_tokens', 'context_window', 'metadata')


def _audit(event_type, user, metadata: dict):
    """Plan 'AI Provider Runtime' FASE 34 -- unico punto de auditoria de este dominio.
    Deliberadamente pasa `user=` (nunca `request=`) -- los Commands no reciben el
    HTTPRequest crudo (violaria la separacion de capas), solo el `User` ya resuelto
    por la vista/orchestrator. Nunca incluir `api_key`/secretos en `metadata`."""
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(event_type, user=user, metadata=metadata)


class AIProviderCommands:
    @staticmethod
    @transaction.atomic
    def create_provider(data: dict, user=None) -> AIProvider:
        provider = AIProvider(**{k: v for k, v in data.items() if k in _PROVIDER_ALLOWED_FIELDS})
        provider.full_clean()
        provider.save()
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_PROVIDER_CREATED, user, {'provider_uuid': str(provider.uuid), 'name': provider.name, 'kind': provider.kind})
        return provider

    @staticmethod
    @transaction.atomic
    def update_provider(provider: AIProvider, data: dict, user=None) -> AIProvider:
        changed_fields = []
        for field in _PROVIDER_ALLOWED_FIELDS:
            if field in data:
                # api_key vacio en un update = "no cambiar la key existente" (el frontend
                # nunca reenvia la key real, solo un placeholder enmascarado -- FASE 5).
                if field == 'api_key' and data[field] == '':
                    continue
                setattr(provider, field, data[field])
                changed_fields.append(field)
        provider.full_clean()
        provider.save()
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_PROVIDER_UPDATED, user, {
            'provider_uuid': str(provider.uuid), 'fields': [f for f in changed_fields if f != 'api_key'],
            'api_key_changed': 'api_key' in changed_fields,
        })
        # FASE 20 -- un provider referenciado como primary/fallback de un canal puede
        # cambiar de base_url/api_key/kind aqui; el runtime debe recogerlo sin esperar el TTL.
        runtime_cache.invalidate(AIChannelConfig.CHANNEL_SUPPORT_CHAT)
        return provider

    @staticmethod
    @transaction.atomic
    def delete_provider(provider: AIProvider, user=None) -> None:
        provider.is_deleted = True
        provider.save(update_fields=['is_deleted'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.ADMIN_RESOURCE_DELETED, user, {'resource': 'AIProvider', 'provider_uuid': str(provider.uuid), 'name': provider.name})
        runtime_cache.invalidate(AIChannelConfig.CHANNEL_SUPPORT_CHAT)

    @staticmethod
    @transaction.atomic
    def activate(provider: AIProvider, user=None) -> AIProvider:
        provider.is_active = True
        provider.save(update_fields=['is_active'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_PROVIDER_ACTIVATED, user, {'provider_uuid': str(provider.uuid), 'name': provider.name})
        runtime_cache.invalidate(AIChannelConfig.CHANNEL_SUPPORT_CHAT)
        return provider

    @staticmethod
    @transaction.atomic
    def deactivate(provider: AIProvider, user=None) -> AIProvider:
        provider.is_active = False
        provider.save(update_fields=['is_active'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_PROVIDER_DEACTIVATED, user, {'provider_uuid': str(provider.uuid), 'name': provider.name})
        # is_active=False saca al provider (y por lo tanto sus modelos) de
        # get_resolved_chain() -- el runtime debe dejar de usarlo de inmediato.
        runtime_cache.invalidate(AIChannelConfig.CHANNEL_SUPPORT_CHAT)
        return provider

    @staticmethod
    @transaction.atomic
    def set_default(provider: AIProvider, user=None) -> AIProvider:
        """Un unico AIProvider.is_default=True a la vez -- desactiva cualquier otro."""
        AIProvider.objects.filter(is_deleted=False, is_default=True).exclude(pk=provider.pk).update(is_default=False)
        provider.is_default = True
        provider.save(update_fields=['is_default'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_PROVIDER_UPDATED, user, {'provider_uuid': str(provider.uuid), 'action': 'set_default'})
        return provider

    @staticmethod
    @transaction.atomic
    def record_test_result(provider: AIProvider, ok: bool, latency_ms: int | None, error: str, user=None) -> AIProvider:
        provider.last_tested_at = timezone.now()
        provider.last_test_ok = ok
        provider.last_test_latency_ms = latency_ms
        provider.last_test_error = error or ''
        provider.save(update_fields=['last_tested_at', 'last_test_ok', 'last_test_latency_ms', 'last_test_error'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_PROVIDER_TESTED, user, {
            'provider_uuid': str(provider.uuid), 'ok': ok, 'latency_ms': latency_ms,
            # error_message_safe -- nunca la key, solo el motivo de fallo de red/HTTP.
            'error': (error or '')[:300],
        })
        return provider


class AIModelCommands:
    @staticmethod
    @transaction.atomic
    def add_model(provider: AIProvider, model_id: str, display_name: str = '',
                  discovered_automatically: bool = False, user=None) -> AIModel:
        model = AIModel.objects.create(
            provider=provider, model_id=model_id, display_name=display_name,
            discovered_automatically=discovered_automatically,
        )
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_MODEL_CHANGED, user, {
            'action': 'added', 'provider_uuid': str(provider.uuid), 'model_id': model_id,
            'discovered_automatically': discovered_automatically,
        })
        return model

    @staticmethod
    @transaction.atomic
    def update_model(model: AIModel, data: dict, user=None) -> AIModel:
        for field in _MODEL_ALLOWED_FIELDS:
            if field in data:
                setattr(model, field, data[field])
        model.full_clean()
        model.save()
        # is_active/temperature/max_tokens pueden ser el modelo primary/fallback de un
        # canal ahora mismo -- FASE 20, ver AIProviderCommands.deactivate().
        runtime_cache.invalidate(AIChannelConfig.CHANNEL_SUPPORT_CHAT)
        return model

    @staticmethod
    @transaction.atomic
    def delete_model(model: AIModel, user=None) -> None:
        model_id, provider_uuid = model.model_id, str(model.provider_id)
        model.is_deleted = True
        model.save(update_fields=['is_deleted'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_MODEL_CHANGED, user, {'action': 'removed', 'provider_uuid': provider_uuid, 'model_id': model_id})
        runtime_cache.invalidate(AIChannelConfig.CHANNEL_SUPPORT_CHAT)

    @staticmethod
    @transaction.atomic
    def set_default(model: AIModel, user=None) -> AIModel:
        """Un unico AIModel.is_default=True por proveedor a la vez."""
        AIModel.objects.filter(
            is_deleted=False, provider_id=model.provider_id, is_default=True,
        ).exclude(pk=model.pk).update(is_default=False)
        model.is_default = True
        model.save(update_fields=['is_default'])
        return model


class AIChannelConfigCommands:
    @staticmethod
    @transaction.atomic
    def set_primary(config: AIChannelConfig, model: AIModel | None, user=None) -> AIChannelConfig:
        config.primary_model = model
        config.updated_by = user
        config.save(update_fields=['primary_model', 'updated_by', 'updated_at'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_CHANNEL_CHANGED, user, {
            'channel': config.channel, 'action': 'set_primary',
            'model_id': model.model_id if model else None,
        })
        runtime_cache.invalidate(config.channel)
        return config

    @staticmethod
    @transaction.atomic
    def set_fallback_chain(config: AIChannelConfig, ordered_models: list[AIModel], user=None) -> AIChannelConfig:
        """Reemplaza la cadena de fallback completa -- mas simple y menos propenso a
        colisiones de 'order' que un update incremental."""
        config.fallbacks.all().delete()
        for idx, model in enumerate(ordered_models):
            AIChannelFallback.objects.create(channel_config=config, model=model, order=idx)
        config.updated_by = user
        config.save(update_fields=['updated_by', 'updated_at'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_CHANNEL_CHANGED, user, {
            'channel': config.channel, 'action': 'set_fallback_chain',
            'model_ids': [m.model_id for m in ordered_models],
        })
        runtime_cache.invalidate(config.channel)
        return config

    @staticmethod
    @transaction.atomic
    def set_enabled(config: AIChannelConfig, enabled: bool, user=None) -> AIChannelConfig:
        config.enabled = enabled
        config.updated_by = user
        config.save(update_fields=['enabled', 'updated_by', 'updated_at'])
        from security.models import SecurityEvent
        _audit(SecurityEvent.AI_CHANNEL_CHANGED, user, {'channel': config.channel, 'action': 'set_enabled', 'enabled': enabled})
        runtime_cache.invalidate(config.channel)
        return config
