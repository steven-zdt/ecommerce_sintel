"""
ai_provider/services/providers/anthropic.py -- Plan "AI Provider Runtime" FASE 10.

Anthropic (Claude) -- unica familia que no habla el protocolo OpenAI-compatible.
API key SIEMPRE cifrada (EncryptedTextField, ver ai_provider/models.py). Sin
descubrimiento dinamico de modelos (Anthropic no expone un endpoint publico de
catalogo equivalente a /v1/models de forma estable) -- FASE 12 exige "modelo
manual cuando no exista endpoint universal", exactamente el caso aqui:
list_models() siempre devuelve [] y el admin escribe el model_identifier a mano
(ver FASE 5/frontend, boton "Descubrir modelos" ya maneja [] con gracia).
"""
import time

import requests

from ai_provider.services.providers.base import (
    ERROR_INVALID_RESPONSE, ERROR_TIMEOUT, ERROR_UNAUTHORIZED, ERROR_UNKNOWN,
    SUCCESS, BaseProviderAdapter, ConnectionTestResult,
)

_TIMEOUT_SECONDS = 10
_ANTHROPIC_API_BASE = 'https://api.anthropic.com/v1'


class AnthropicAdapter(BaseProviderAdapter):
    def test_connection(self) -> ConnectionTestResult:
        headers = {'x-api-key': self.provider.api_key, 'anthropic-version': '2023-06-01'}
        start = time.monotonic()
        try:
            # /v1/models: catalogo real de Anthropic, sin costo de tokens -- sirve como
            # probe de disponibilidad + validez de la key en una sola llamada.
            resp = requests.get(f'{_ANTHROPIC_API_BASE}/models', headers=headers, timeout=_TIMEOUT_SECONDS)
            latency_ms = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                return ConnectionTestResult(True, self.provider.name, _ANTHROPIC_API_BASE, None, latency_ms, resp.status_code, SUCCESS, '')
            if resp.status_code in (401, 403):
                return ConnectionTestResult(False, self.provider.name, _ANTHROPIC_API_BASE, None, latency_ms, resp.status_code, ERROR_UNAUTHORIZED, 'API key invalida.')
            return ConnectionTestResult(False, self.provider.name, _ANTHROPIC_API_BASE, None, latency_ms, resp.status_code, ERROR_INVALID_RESPONSE, f'HTTP {resp.status_code}')
        except requests.exceptions.Timeout:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, _ANTHROPIC_API_BASE, None, latency_ms, None, ERROR_TIMEOUT, 'Timeout de conexion.')
        except requests.RequestException as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, _ANTHROPIC_API_BASE, None, latency_ms, None, ERROR_UNKNOWN, type(exc).__name__)

    def list_models(self) -> list[dict]:
        return []

    def validate_model(self, model_id: str) -> bool:
        # Sin catalogo dinamico -- validacion real requeriria una llamada de generacion
        # (costo real). Se acepta cualquier model_id no vacio; el error real (si el
        # identifier no existe) aparece en el primer /chat real, categorizado como
        # MODEL_NOT_FOUND por AI Engine, no aqui.
        return bool(model_id and model_id.strip())
