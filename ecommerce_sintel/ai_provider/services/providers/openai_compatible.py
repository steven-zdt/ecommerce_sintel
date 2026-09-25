"""
ai_provider/services/providers/openai_compatible.py -- Plan "AI Provider Runtime" FASE 9.

OpenAI-compatible: LM Studio, vLLM, OpenAI, DeepSeek, etc. Autenticacion configurable (PLAN_LLMDINAMICO sec. 3): Bearer (default), cabecera
personalizada o ninguna; ruta de descubrimiento configurable (`endpoint_path`, default /models).
"""
import time
from urllib.parse import urlparse

import requests

from ai_provider.services.providers.base import (
    ERROR_INVALID_RESPONSE, ERROR_TIMEOUT, ERROR_UNAUTHORIZED, ERROR_UNKNOWN,
    SUCCESS, BaseProviderAdapter, ConnectionTestResult, connection_failure,
)
from ai_provider.services.providers.ollama import _classify_connection_error

_TIMEOUT_SECONDS = 10


class OpenAICompatibleAdapter(BaseProviderAdapter):
    def _headers(self) -> dict:
        return self._auth_headers()

    def _models_url(self) -> str:
        path = (self.provider.endpoint_path or '/models').strip()
        if not path.startswith('/'):
            path = '/' + path
        return f'{self.provider.base_url.rstrip("/")}{path}'

    def test_connection(self) -> ConnectionTestResult:
        start = time.monotonic()
        try:
            resp = requests.get(self._models_url(), headers=self._headers(), **self._request_kwargs())
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
            code, message = connection_failure(self.provider.base_url, _classify_connection_error(exc))
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, None, code, message)
        except requests.RequestException as exc:
            latency_ms = int((time.monotonic() - start) * 1000)
            return ConnectionTestResult(False, self.provider.name, self.provider.base_url, None, latency_ms, None, ERROR_UNKNOWN, type(exc).__name__)

    def list_models(self) -> list[dict]:
        try:
            resp = requests.get(self._models_url(), headers=self._headers(), **self._request_kwargs())
            resp.raise_for_status()
            return [{'model_id': m['id'], 'display_name': m['id']} for m in resp.json().get('data', [])]
        except (requests.RequestException, KeyError, ValueError):
            return []

    def detect_capabilities(self, model_id: str) -> dict:
        """OpenAI /v1/models no declara capacidades. LM Studio expone /api/v0/models/<id> con `type` (llm|vlm|embeddings) y `capabilities`
        (p. ej. ["tool_use"]): se intenta ahi; si no existe (OpenAI, vLLM...) todo queda "desconocido" en vez de inventarse."""
        caps = self._empty_capabilities()
        parsed = urlparse(self.provider.base_url)
        root = f'{parsed.scheme}://{parsed.netloc}'
        try:
            resp = requests.get(f'{root}/api/v0/models/{model_id}', headers=self._headers(), **self._request_kwargs())
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return caps
        declared = data.get('capabilities')
        if isinstance(declared, list):
            caps['tool_calling'] = 'tool_use' in declared
        if data.get('type') in ('llm', 'vlm', 'embeddings'):
            caps['vision'] = data['type'] == 'vlm'
        caps['streaming'] = True
        return caps
