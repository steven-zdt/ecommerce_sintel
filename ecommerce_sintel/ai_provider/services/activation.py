"""
PLAN_LLMDINAMICO seccion 7 (2026-09-25) -- validar ANTES de activar un modelo como primario del canal.

Cadena del plan: validate -> authenticate -> test connectivity -> test model -> test capabilities -> (transaccion) persist. Aqui van los pasos previos a la
transaccion; la persistencia y el versionado siguen en `AIChannelConfigCommands.set_primary` (que sube `config_version`).

- Solo pruebas inocuas: ping al proveedor y listado de modelos, nunca una generacion ni datos de clientes.
- El proveedor debe ser EJECUTABLE (`AIProvider.RUNNABLE_KINDS`): generic-rest/custom se registran y prueban pero no se pueden usar como primario.
- Capacidades (sec. 10): el chat de soporte usa tools. Si el modelo tiene `tool_calling=False` se BLOQUEA (nunca se degrada en silencio); si es desconocido
  (None) se permite con advertencia para que el admin ejecute "Detectar capacidades".
- Si el proveedor no soporta listado de modelos (`list_models() == []`), el modelo queda "no verificado": se permite con advertencia.
- `force=True` (accion explicita del admin) omite la validacion, p. ej. para dejar configurado un proveedor que esta apagado a proposito.
"""
from ai_provider.models import AIChannelConfig, AIModel, AIProvider
from ai_provider.services.providers import get_adapter
from ai_provider.services.providers.base import ERROR_TOOL_CALLING_UNSUPPORTED

# Canales cuyo modelo primario debe soportar tool calling (el agente de soporte llama a Tools). El de embeddings no.
_TOOL_CALLING_CHANNELS = (AIChannelConfig.CHANNEL_SUPPORT_CHAT,)


class ActivationCheckFailed(ValueError):
    """La validacion previa fallo; `.report` es seguro de mostrar (sin secretos)."""

    def __init__(self, report: dict):
        self.report = report
        super().__init__(report.get('message', 'Validacion previa fallida.'))


def validate_model_for_activation(model: AIModel, channel: str = AIChannelConfig.CHANNEL_SUPPORT_CHAT) -> dict:
    provider = model.provider
    report = {'ok': False, 'provider': provider.name, 'model': model.model_id, 'checks': [], 'warnings': [], 'latency_ms': None,
              'error_code': '', 'message': ''}

    def fail(code, message):
        report.update(ok=False, error_code=code, message=message)
        raise ActivationCheckFailed(report)

    if model.is_deleted or not model.is_active:
        fail('MODEL_INACTIVE', 'El modelo esta inactivo o eliminado.')
    report['checks'].append('model_active')
    if provider.is_deleted or not provider.is_active:
        fail('PROVIDER_INACTIVE', 'El proveedor esta inactivo o eliminado. Activalo primero.')
    report['checks'].append('provider_active')
    if provider.kind not in AIProvider.RUNNABLE_KINDS:
        fail('KIND_NOT_RUNNABLE', f'El tipo "{provider.get_kind_display()}" se puede registrar y probar, pero todavia no se ejecuta como proveedor del chat.')
    report['checks'].append('kind_runnable')

    adapter = get_adapter(provider)
    ping = adapter.test_connection()
    report['latency_ms'] = ping.latency_ms
    if not ping.success:
        fail(ping.error_code, f'No se pudo conectar con el proveedor: {ping.error_message_safe}')
    report['checks'].append('connectivity')

    available = adapter.list_models()
    if available:
        if not any(m.get('model_id') == model.model_id for m in available):
            fail('MODEL_NOT_FOUND', 'El proveedor no reporta ese modelo. Usa "Detectar modelos" para ver los disponibles.')
        report['checks'].append('model_available')
    else:
        report['warnings'].append('El proveedor no permite listar modelos: la disponibilidad del modelo no se pudo verificar.')

    if channel in _TOOL_CALLING_CHANNELS:
        tool_calling = (model.capabilities or {}).get('tool_calling')
        if tool_calling is False:
            fail(ERROR_TOOL_CALLING_UNSUPPORTED, 'Este modelo no soporta tool calling y el chat de soporte usa herramientas. Elige otro modelo.')
        if tool_calling is True:
            report['checks'].append('tool_calling')
        else:
            report['warnings'].append('No se conoce si el modelo soporta tool calling: ejecuta "Detectar capacidades" antes de usarlo en produccion.')

    report.update(ok=True, message='Validacion previa correcta.')
    return report
