"""
ai_provider/services/providers/generic_rest.py -- PLAN_LLMDINAMICO sec. 4 (GENERIC_REST y CUSTOM).

Solo REGISTRO y PRUEBA de conexion: se puede guardar un endpoint REST arbitrario, comprobar que responde y descubrir modelos si `endpoint_path` apunta a un
catalogo con forma OpenAI (`{"data": [{"id": ...}]}`). NO se ejecuta como proveedor de inferencia del chat: no existe todavia un adaptador declarativo de
request/response. Por eso `activation.py` bloquea usarlo como primario (codigo KIND_NOT_RUNNABLE) en vez de degradar en silencio.

Nunca se evalua codigo de la configuracion (sin eval/exec/shell/subprocess): la prueba es un GET a una URL ya validada por el guard SSRF.
"""
import time

import requests

from ai_provider.services.providers.base import (
    ERROR_INVALID_RESPONSE, ERROR_TIMEOUT, ERROR_UNAUTHORIZED, ERROR_UNKNOWN,
    SUCCESS, BaseProviderAdapter, ConnectionTestResult, connection_failure,
)
from ai_provider.services.providers.ollama import _classify_connection_error


class GenericRestAdapter(BaseProviderAdapter):
    def _probe_url(self) -> str:
        path = (self.provider.endpoint_path or '').strip()
        if path and not path.startswith('/'):
            path = '/' + path
        return f'{self.provider.base_url.rstrip("/")}{path}'

    def test_connection(self) -> ConnectionTestResult:
        start = time.monotonic()
        try:
            resp = requests.get(self._probe_url(), headers=self._auth_headers(), **self._request_kwargs())
            latency_ms = int((time.monotonic() - start) * 1000)
            if resp.status_code < 400:
                return ConnectionTestResult(True, self.provider.name, self.provider.base_url, None, latency_ms, resp.status_code, SUCCESS, '')
            if resp.status_code in (401, 403):
                return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, resp.status_code, ERROR_UNAUTHORIZED, 'Credenciales invalidas o faltantes.')
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, resp.status_code, ERROR_INVALID_RESPONSE, f'HTTP {resp.status_code}')
        except requests.exceptions.Timeout:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, None, ERROR_TIMEOUT, 'Timeout de conexion.')
        except requests.exceptions.ConnectionError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            code, message = connection_failure(self.provider.base_url, _classify_connection_error(exc))
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, None, code, message)
        except requests.RequestException as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, None, ERROR_UNKNOWN, type(exc).__name__)

    def list_models(self) -> list[dict]:
        try:
            resp = requests.get(self._probe_url(), headers=self._auth_headers(), **self._request_kwargs())
            resp.raise_for_status()
            return [{'model_id': m['id'], 'display_name': m['id']} for m in resp.json().get('data', [])]
        except (requests.RequestException, KeyError, ValueError, AttributeError, TypeError):
            return []
