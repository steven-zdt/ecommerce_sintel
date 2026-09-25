"""
PLAN_LLMDINAMICO sec. 15-16 (2026-09-25) -- salud persistida de un proveedor.

Estados: HEALTHY / DEGRADED / UNAVAILABLE / MISCONFIGURED / DISABLED. Se calculan SOLO a partir de una comprobacion real de conectividad
(`adapter.test_connection()`: ping o catalogo, nunca una generacion ni datos de clientes), no de suposiciones.

- DISABLED: el proveedor esta inactivo (no se le llama).
- MISCONFIGURED: el problema es de configuracion, no del servicio: DNS, URL loopback, credenciales, ruta inexistente.
- UNAVAILABLE: el servicio no responde (conexion rechazada, sin ruta, timeout, respuesta invalida).
- DEGRADED: responde pero lento (> DEGRADED_LATENCY_MS).
- HEALTHY: responde a tiempo.
El circuit breaker (CLOSED/OPEN/HALF_OPEN) vive en el ADK, por proveedor y en Redis (model_runtime.py); esto es el estado *configurado y probado* que ve el admin.
"""
from django.db import transaction
from django.utils import timezone

from ai_provider.models import AIProvider
from ai_provider.services.providers import get_adapter
from ai_provider.services.providers.base import (
    ERROR_DNS, ERROR_LOOPBACK_URL, ERROR_NOT_FOUND, ERROR_UNAUTHORIZED, SUCCESS,
)

DEGRADED_LATENCY_MS = 5000
_MISCONFIGURED_CODES = frozenset({ERROR_DNS, ERROR_LOOPBACK_URL, ERROR_UNAUTHORIZED, ERROR_NOT_FOUND})


def classify_health(provider: AIProvider, success: bool, error_code: str, latency_ms: int | None) -> str:
    if not provider.is_active:
        return AIProvider.HEALTH_DISABLED
    if success:
        return AIProvider.HEALTH_DEGRADED if (latency_ms or 0) > DEGRADED_LATENCY_MS else AIProvider.HEALTH_HEALTHY
    if error_code in _MISCONFIGURED_CODES:
        return AIProvider.HEALTH_MISCONFIGURED
    return AIProvider.HEALTH_UNAVAILABLE


@transaction.atomic
def check_provider_health(provider: AIProvider, user=None) -> dict:
    """Prueba el proveedor, persiste ultimo test + estado de salud y devuelve un reporte seguro (sin secretos)."""
    from ai_provider.services.commands import AIProviderCommands

    result = get_adapter(provider).test_connection()
    AIProviderCommands.record_test_result(
        provider, ok=result.success, latency_ms=result.latency_ms,
        error=result.error_message_safe if not result.success else '', user=user,
    )
    status = classify_health(provider, result.success, result.error_code, result.latency_ms)
    provider.health_status = status
    provider.last_health_at = timezone.now()
    provider.save(update_fields=['health_status', 'last_health_at'])
    return {
        'status': status, 'success': result.success, 'error_code': '' if result.success else result.error_code,
        'message': result.error_message_safe, 'latency_ms': result.latency_ms, 'checked_at': provider.last_health_at.isoformat(),
        'provider': provider.name,
    }
