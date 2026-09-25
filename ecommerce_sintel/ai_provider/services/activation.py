"""
PLAN_LLMDINAMICO seccion 7 (2026-09-25) -- validar ANTES de activar un modelo como primario del canal.

Cadena del plan: validate -> authenticate -> test connectivity -> test model -> (transaccion) persist. Aqui van los pasos previos a la
transaccion; la persistencia y el versionado siguen en `AIChannelConfigCommands.set_primary` (que sube `config_version`).

- Solo pruebas inocuas: ping al proveedor y listado de modelos, nunca una generacion ni datos de clientes.
- Si el proveedor no soporta listado de modelos (`list_models() == []`), el modelo queda "no verificado": se permite con advertencia.
- `force=True` (accion explicita del admin) omite la validacion, p. ej. para dejar configurado un proveedor que esta apagado a proposito.
"""
from ai_provider.models import AIModel
from ai_provider.services.providers import get_adapter


class ActivationCheckFailed(ValueError):
    """La validacion previa fallo; `.report` es seguro de mostrar (sin secretos)."""

    def __init__(self, report: dict):
        self.report = report
        super().__init__(report.get('message', 'Validacion previa fallida.'))


def validate_model_for_activation(model: AIModel) -> dict:
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

    report.update(ok=True, message='Validacion previa correcta.')
    return report
