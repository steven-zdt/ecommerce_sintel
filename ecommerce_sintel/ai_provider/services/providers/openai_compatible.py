"""
ai_provider/services/providers/openai_compatible.py -- Plan "AI Provider Runtime"
FASE 9.

Cubre CUALQUIER motor que hable /v1/chat/completions + /v1/models sin una clase
de Python por motor: LM Studio, vLLM, llama.cpp (modo servidor), text-generation-
webui, LocalAI, OpenAI real, DeepSeek. Ejemplo LM Studio en Windows (AI Engine en
Docker, LM Studio nativo en Windows):
    http://host.docker.internal:1234/v1
NUNCA http://127.0.0.1:1234/v1 desde dentro de Docker -- ese loopback apunta al
propio contenedor, no al host.
"""
import time

import requests

from ai_provider.services.providers.base import (
    ERROR_CONNECTION_REFUSED, ERROR_DNS, ERROR_INVALID_RESPONSE, ERROR_TIMEOUT,
    ERROR_UNAUTHORIZED, ERROR_UNKNOWN, SUCCESS, BaseProviderAdapter, ConnectionTestResult,
)
from ai_provider.services.providers.ollama import _classify_connection_error

_TIMEOUT_SECONDS = 10


class OpenAICompatibleAdapter(BaseProviderAdapter):
    def _headers(self) -> dict:
        return {'Authorization': f'Bearer {self.provider.api_key}'} if self.provider.api_key else {}

    def test_connection(self) -> ConnectionTestResult:
        start = time.monotonic()
        try:
            resp = requests.get(
                f'{self.provider.base_url.rstrip("/")}/models', headers=self._headers(), timeout=_TIMEOUT_SECONDS,
            )
            latency_ms = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                return ConnectionTestResult(True, self.provider.name, self.provider.base_url, None, latency_ms, resp.status_code, SUCCESS, '')
            if resp.status_code in (401, 403):
                return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, resp.status_code, ERROR_UNAUTHORIZED, 'API key invalida o faltante.')
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, resp.status_code, ERROR_INVALID_RESPONSE, f'HTTP {resp.status_code}')
        except requests.exceptions.Timeout:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, None, ERROR_TIMEOUT, 'Timeout de conexion.')
        except requests.exceptions.ConnectionError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(
                False, self.provider.name, self.provider.base_url, None, latency_ms, None,
                _classify_connection_error(exc), 'No se pudo establecer conexion.',
            )
        except requests.RequestException as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, None, ERROR_UNKNOWN, type(exc).__name__)

    def list_models(self) -> list[dict]:
        try:
            resp = requests.get(
                f'{self.provider.base_url.rstrip("/")}/models', headers=self._headers(), timeout=_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return [{'model_id': m['id'], 'display_name': m['id']} for m in resp.json().get('data', [])]
        except (requests.RequestException, KeyError, ValueError):
            return []
