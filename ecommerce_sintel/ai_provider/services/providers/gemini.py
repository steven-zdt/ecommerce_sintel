"""
ai_provider/services/providers/gemini.py -- PLAN_LLMDINAMICO sec. 4 (Google Gemini via Generative Language API).

Autenticacion por cabecera `x-goog-api-key` (nunca en la URL: las URLs acaban en logs). El catalogo /v1beta/models es gratuito y sirve como probe de
disponibilidad y de validez de la key. La inferencia real la hace LiteLLM (`gemini/<modelo>`), ver ai_engine_adk/model_runtime.py.
"""
import time

import requests

from ai_provider.services.providers.base import (
    ERROR_INVALID_RESPONSE, ERROR_TIMEOUT, ERROR_UNAUTHORIZED, ERROR_UNKNOWN,
    SUCCESS, BaseProviderAdapter, ConnectionTestResult, connection_failure,
)
from ai_provider.services.providers.ollama import _classify_connection_error

DEFAULT_BASE_URL = 'https://generativelanguage.googleapis.com'


class GeminiAdapter(BaseProviderAdapter):
    def _base(self) -> str:
        return (self.provider.base_url or DEFAULT_BASE_URL).rstrip('/')

    def _headers(self) -> dict:
        return {'x-goog-api-key': self.provider.api_key} if self.provider.api_key else {}

    def test_connection(self) -> ConnectionTestResult:
        start = time.monotonic()
        url = self._base()
        try:
            resp = requests.get(f'{url}/v1beta/models', params={'pageSize': 1}, headers=self._headers(), **self._request_kwargs())
            latency_ms = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                return ConnectionTestResult(True, self.provider.name, url, None, latency_ms, resp.status_code, SUCCESS, '')
            if resp.status_code in (400, 401, 403):
                return ConnectionTestResult(False, self.provider.name, url, None, latency_ms, resp.status_code, ERROR_UNAUTHORIZED, 'API key invalida o sin permisos.')
            return ConnectionTestResult(False, self.provider.name, url, None, latency_ms, resp.status_code, ERROR_INVALID_RESPONSE, f'HTTP {resp.status_code}')
        except requests.exceptions.Timeout:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, url, None, latency_ms, None, ERROR_TIMEOUT, 'Timeout de conexion.')
        except requests.exceptions.ConnectionError as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            code, message = connection_failure(url, _classify_connection_error(exc))
            return ConnectionTestResult(False, self.provider.name, url, None, latency_ms, None, code, message)
        except requests.RequestException as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, url, None, latency_ms, None, ERROR_UNKNOWN, type(exc).__name__)

    def list_models(self) -> list[dict]:
        try:
            resp = requests.get(f'{self._base()}/v1beta/models', params={'pageSize': 100}, headers=self._headers(), **self._request_kwargs())
            resp.raise_for_status()
            out = []
            for m in resp.json().get('models', []):
                if 'generateContent' in (m.get('supportedGenerationMethods') or []):
                    model_id = m['name'].split('/', 1)[-1]
                    out.append({'model_id': model_id, 'display_name': m.get('displayName') or model_id})
            return out
        except (requests.RequestException, KeyError, ValueError):
            return []

    def detect_capabilities(self, model_id: str) -> dict:
        """Gemini declara metodos soportados por modelo. Tool calling y streaming son comunes a la familia generateContent; el resto queda desconocido."""
        caps = self._empty_capabilities()
        try:
            resp = requests.get(f'{self._base()}/v1beta/models/{model_id}', headers=self._headers(), **self._request_kwargs())
            resp.raise_for_status()
            methods = resp.json().get('supportedGenerationMethods') or []
        except (requests.RequestException, ValueError):
            return caps
        if 'generateContent' in methods:
            caps['tool_calling'] = True
            caps['structured_output'] = True
            caps['json_mode'] = True
        if 'streamGenerateContent' in methods:
            caps['streaming'] = True
        return caps
