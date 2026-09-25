"""
ai_provider/services/providers/ollama.py -- Plan "AI Provider Runtime" FASE 8.

Ollama nativo. Dos topologias reales de este proyecto (nunca asumir localhost):
  1. http://sintel_ollama:11434   (Ollama en Docker, mismo compose network)
  2. http://host.docker.internal:11434  (Ollama nativo corriendo en Windows,
     AI Engine sigue en Docker -- Docker Desktop resuelve ese hostname especial
     al host real)
"""
import time

import requests

from ai_provider.services.providers.base import (
    ERROR_CONNECTION_REFUSED, ERROR_DNS, ERROR_INVALID_RESPONSE, ERROR_NETWORK_UNREACHABLE, ERROR_TIMEOUT,
    ERROR_UNKNOWN, SUCCESS, BaseProviderAdapter, ConnectionTestResult, connection_failure,
)

_TIMEOUT_SECONDS = 10


def _classify_connection_error(exc: Exception) -> str:
    """DNS vs CONNECTION_REFUSED vs generico -- ambos llegan como
    requests.exceptions.ConnectionError, se distinguen por el texto de la causa
    real (urllib3 envuelve socket.gaierror/ConnectionRefusedError)."""
    text = str(exc).lower()
    if 'name or service not known' in text or 'nodename nor servname' in text or 'getaddrinfo failed' in text or 'name resolution' in text:
        return ERROR_DNS
    if 'connection refused' in text or 'actively refused' in text:
        return ERROR_CONNECTION_REFUSED
    if 'network is unreachable' in text or 'no route to host' in text or 'errno 101' in text or 'errno 113' in text:
        return ERROR_NETWORK_UNREACHABLE
    return ERROR_UNKNOWN


class OllamaAdapter(BaseProviderAdapter):
    def test_connection(self) -> ConnectionTestResult:
        start = time.monotonic()
        try:
            resp = requests.get(f'{self.provider.base_url.rstrip("/")}/api/tags', timeout=_TIMEOUT_SECONDS, allow_redirects=False)
            latency_ms = int((time.monotonic() - start) * 1000)
            if resp.status_code == 200:
                return ConnectionTestResult(
                    True, self.provider.name, self.provider.base_url, None, latency_ms,
                    resp.status_code, SUCCESS, '',
                )
            return ConnectionTestResult(
                False, self.provider.name, self.provider.base_url, None, latency_ms,
                resp.status_code, ERROR_INVALID_RESPONSE, f'HTTP {resp.status_code}',
            )
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
            resp = requests.get(f'{self.provider.base_url.rstrip("/")}/api/tags', timeout=_TIMEOUT_SECONDS, allow_redirects=False)
            resp.raise_for_status()
            return [{'model_id': m['name'], 'display_name': m['name']} for m in resp.json().get('models', [])]
        except (requests.RequestException, KeyError, ValueError):
            return []
