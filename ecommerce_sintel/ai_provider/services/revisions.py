"""
PLAN_LLMDINAMICO F1/F7/F18 (2026-09-25) -- config_version, historial y rollback de la configuracion de proveedores LLM.

- Cada cambio que afecta a un canal (primario, fallbacks, enabled, o edicion/activacion/borrado de un proveedor o modelo) sube
  `AIChannelConfig.config_version` y guarda un snapshot inmutable (`AIConfigRevision`, scope=channel).
- Cada cambio de un proveedor sube `AIProvider.config_version` y guarda un snapshot de sus campos NO secretos (scope=provider).
- Los snapshots nunca contienen api_key. Un rollback de proveedor conserva la key actual; para cambiarla se edita el proveedor.
- El rollback es un cambio mas (nueva version, action `rollback_to_vN`): el historial nunca se reescribe.
Solo los Commands (y esta capa) escriben; las vistas y el LLM no participan.
"""
import logging

from django.db import transaction
from django.db.models import F

from ai_provider.models import AIChannelConfig, AIChannelFallback, AIConfigRevision, AIModel, AIProvider
from ai_provider.services import runtime_cache

_PROVIDER_SNAPSHOT_FIELDS = ('name', 'kind', 'base_url', 'is_active', 'display_order', 'timeout', 'max_retries', 'metadata',
                             'auth_type', 'api_key_header', 'endpoint_path', 'verify_tls', 'connect_timeout')
_CHANNEL_OVERRIDES = ('temperature', 'max_tokens', 'timeout')

logger = logging.getLogger(__name__)


class RollbackError(ValueError):
    """La revision no se puede restaurar (destino inexistente, modelo borrado, configuracion invalida)."""


def _label(model: AIModel) -> str:
    return f'{model.provider.name} / {model.model_id}'


def channel_snapshot(config: AIChannelConfig) -> dict:
    fallbacks = list(config.fallbacks.filter(is_deleted=False).select_related('model__provider').order_by('order'))
    primary = config.primary_model
    labels = {}
    if primary:
        labels[str(primary.uuid)] = _label(primary)
    for fb in fallbacks:
        labels[str(fb.model.uuid)] = _label(fb.model)
    return {
        'enabled': config.enabled,
        'primary_model_uuid': str(primary.uuid) if primary else None,
        'fallback_model_uuids': [str(fb.model.uuid) for fb in fallbacks],
        'overrides': {name: getattr(config, name) for name in _CHANNEL_OVERRIDES},
        'labels': labels,
    }


def provider_snapshot(provider: AIProvider) -> dict:
    data = {name: getattr(provider, name) for name in _PROVIDER_SNAPSHOT_FIELDS}
    data['has_api_key'] = bool(provider.api_key)  # nunca la key
    return data


def _next_version(model_cls, pk) -> int:
    model_cls.objects.filter(pk=pk).update(config_version=F('config_version') + 1)
    return model_cls.objects.values_list('config_version', flat=True).get(pk=pk)


@transaction.atomic
def touch_channel(action: str, user=None, channel: str = AIChannelConfig.CHANNEL_SUPPORT_CHAT) -> int:
    """Sube config_version del canal, guarda el snapshot e invalida la cache del runtime. Devuelve la nueva version."""
    config, _ = AIChannelConfig.objects.get_or_create(channel=channel)
    version = _next_version(AIChannelConfig, config.pk)
    config.refresh_from_db()
    AIConfigRevision.objects.create(
        scope=AIConfigRevision.SCOPE_CHANNEL, target_uuid=config.uuid, channel=channel, version=version,
        action=action[:60], snapshot=channel_snapshot(config), changed_by=user,
    )
    runtime_cache.invalidate(channel)
    # PLAN_LLMDINAMICO sec. 7 "emit provider_changed": evento estructurado (el ADK recarga la cadena en <= TTL y lo registra como registry_chain_loaded).
    logger.info('ai_operation_event=provider_changed channel=%s config_version=%s action=%s', channel, version, action[:60])
    return version


@transaction.atomic
def touch_provider(provider: AIProvider, action: str, user=None, initial: bool = False) -> int:
    """Guarda el snapshot no secreto del proveedor; `initial=True` (alta) conserva la version 1 en vez de subirla."""
    if initial:
        version = provider.config_version
    else:
        version = _next_version(AIProvider, provider.pk)
        provider.config_version = version
    AIConfigRevision.objects.create(
        scope=AIConfigRevision.SCOPE_PROVIDER, target_uuid=provider.uuid, version=version, action=action[:60],
        snapshot=provider_snapshot(provider), changed_by=user,
    )
    return version


def list_history(scope: str, target_uuid, limit: int = 50):
    return AIConfigRevision.objects.filter(scope=scope, target_uuid=target_uuid, is_deleted=False).select_related('changed_by')[:limit]


def get_revision(scope: str, target_uuid, version: int) -> AIConfigRevision:
    return AIConfigRevision.objects.get(scope=scope, target_uuid=target_uuid, version=version)


def _audit(user, metadata: dict):
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(SecurityEvent.AI_CHANNEL_CHANGED, user=user, metadata=metadata)


@transaction.atomic
def rollback_channel(config: AIChannelConfig, version: int, user=None) -> AIChannelConfig:
    """Restaura enabled, primario, cadena de fallback y overrides de la version indicada. Todo o nada: si algun modelo referenciado ya no
    existe se rechaza sin cambiar nada. Un proveedor/modelo hoy inactivo se restaura igual (get_resolved_chain lo salta)."""
    try:
        revision = get_revision(AIConfigRevision.SCOPE_CHANNEL, config.uuid, version)
    except AIConfigRevision.DoesNotExist:
        raise RollbackError(f'No existe la version {version} del canal.')
    snap = revision.snapshot
    wanted = [u for u in [snap.get('primary_model_uuid'), *snap.get('fallback_model_uuids', [])] if u]
    found = {str(m.uuid): m for m in AIModel.objects.filter(uuid__in=wanted, is_deleted=False).select_related('provider')}
    missing = [snap.get('labels', {}).get(u, u) for u in wanted if u not in found]
    if missing:
        raise RollbackError('No se puede restaurar: ya no existen los modelos ' + ', '.join(missing) + '.')

    config.enabled = bool(snap.get('enabled', True))
    config.primary_model = found.get(snap.get('primary_model_uuid'))
    for name in _CHANNEL_OVERRIDES:
        setattr(config, name, (snap.get('overrides') or {}).get(name))
    config.updated_by = user
    config.save()
    config.fallbacks.all().delete()
    for idx, model_uuid in enumerate(snap.get('fallback_model_uuids', [])):
        AIChannelFallback.objects.create(channel_config=config, model=found[model_uuid], order=idx)
    new_version = touch_channel(f'rollback_to_v{version}', user=user, channel=config.channel)
    _audit(user, {'channel': config.channel, 'action': 'rollback', 'restored_version': version, 'new_version': new_version})
    config.refresh_from_db()
    return config


@transaction.atomic
def rollback_provider(provider: AIProvider, version: int, user=None) -> AIProvider:
    """Restaura los campos no secretos del proveedor (la api_key actual se conserva). La URL restaurada pasa otra vez por el guard SSRF."""
    from django.core.exceptions import ValidationError

    try:
        revision = get_revision(AIConfigRevision.SCOPE_PROVIDER, provider.uuid, version)
    except AIConfigRevision.DoesNotExist:
        raise RollbackError(f'No existe la version {version} del proveedor.')
    for name in _PROVIDER_SNAPSHOT_FIELDS:
        if name in revision.snapshot:
            setattr(provider, name, revision.snapshot[name])
    try:
        provider.full_clean()
    except ValidationError as exc:
        raise RollbackError('La version indicada ya no es valida: ' + '; '.join(exc.messages))
    provider.save()
    touch_provider(provider, f'rollback_to_v{version}', user=user)
    touch_channel(f'provider_rollback:{provider.name}', user=user)
    _audit(user, {'channel': AIChannelConfig.CHANNEL_SUPPORT_CHAT, 'action': 'provider_rollback', 'provider_uuid': str(provider.uuid),
                  'restored_version': version})
    return provider
