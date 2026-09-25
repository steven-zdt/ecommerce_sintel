"""
PLAN_LLMDINAMICO sec. 5 (2026-09-25) -- registro y prueba de servidores MCP como integracion INDEPENDIENTE de los proveedores LLM.

MCP != API HTTP de un LLM: aqui solo se registra el servidor (URL, transporte, autenticacion), se comprueba el handshake JSON-RPC
(`initialize` + `notifications/initialized` + `tools/list`) y se guardan capacidades y numero de tools. Nada de esto convierte a un servidor MCP en
proveedor de inferencia: `exposes_model_invocation` es informativo y false por defecto.

Seguridad: la URL pasa por el guard SSRF (`url_guard`) y por el rechazo de loopback del modelo; sin redirects; la API key va cifrada y nunca se
devuelve ni se registra; el resultado de la prueba solo lleva mensajes seguros.
"""
import json
import time

import requests
from django.db import transaction
from django.utils import timezone

from ai_provider.models import MCPServer
from ai_provider.services.providers.base import (
    ERROR_INVALID_RESPONSE, ERROR_TIMEOUT, ERROR_UNAUTHORIZED, ERROR_UNKNOWN, SUCCESS, connection_failure,
)
from ai_provider.services.providers.ollama import _classify_connection_error
from ai_provider.services.url_guard import UnsafeProviderURL, validate_provider_url

PROTOCOL_VERSION = '2025-03-26'
_TIMEOUT = (5, 15)
_SERVER_ALLOWED_FIELDS = ('name', 'server_url', 'transport', 'auth_type', 'api_key_header', 'api_key', 'verify_tls', 'is_active', 'metadata')
_MISCONFIGURED = frozenset({'DNS', 'LOOPBACK_URL', ERROR_UNAUTHORIZED, 'UNSUPPORTED_TRANSPORT', 'UNSAFE_URL'})


def _headers(server: MCPServer, session_id: str | None = None) -> dict:
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': PROTOCOL_VERSION}
    if server.api_key and server.auth_type == 'bearer':
        headers['Authorization'] = f'Bearer {server.api_key}'
    elif server.api_key and server.auth_type == 'header':
        headers[server.api_key_header or 'x-api-key'] = server.api_key
    if session_id:
        headers['Mcp-Session-Id'] = session_id
    return headers


def _parse_rpc(resp) -> dict:
    """La respuesta de un servidor MCP puede ser JSON o un evento SSE (`data: {...}`)."""
    content_type = resp.headers.get('Content-Type', '')
    if 'text/event-stream' in content_type:
        for line in resp.text.splitlines():
            if line.startswith('data:'):
                return json.loads(line[5:].strip())
        raise ValueError('sin evento data')
    return resp.json()


def _rpc(server, method, params=None, request_id=1, session_id=None):
    payload = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
    if request_id is not None:
        payload['id'] = request_id
    return requests.post(server.server_url, json=payload, headers=_headers(server, session_id), timeout=_TIMEOUT,
                         verify=server.verify_tls, allow_redirects=False)


def probe_mcp_server(server: MCPServer) -> dict:
    """Handshake MCP real. Devuelve {ok, status, latency_ms, capabilities, tools_count, server_info, error_code, message}. Nunca lanza."""
    report = {'ok': False, 'status': 'UNAVAILABLE', 'latency_ms': None, 'capabilities': {}, 'tools_count': 0, 'server_info': {},
              'error_code': '', 'message': ''}

    def failed(code, message):
        report.update(ok=False, error_code=code, message=message,
                      status='MISCONFIGURED' if code in _MISCONFIGURED else 'UNAVAILABLE')
        return report

    if not server.is_active:
        report.update(status='DISABLED', error_code='DISABLED', message='El servidor MCP esta desactivado.')
        return report
    if server.transport != MCPServer.TRANSPORT_STREAMABLE_HTTP:
        return failed('UNSUPPORTED_TRANSPORT', 'El transporte SSE legado no se puede probar desde aqui: usa Streamable HTTP.')
    try:
        validate_provider_url(server.server_url)
    except UnsafeProviderURL as exc:
        return failed('UNSAFE_URL', str(exc))

    start = time.monotonic()
    try:
        resp = _rpc(server, 'initialize', {
            'protocolVersion': PROTOCOL_VERSION, 'capabilities': {}, 'clientInfo': {'name': 'sintel-admin', 'version': '1.0'},
        })
        report['latency_ms'] = int((time.monotonic() - start) * 1000)
        if resp.status_code in (401, 403):
            return failed(ERROR_UNAUTHORIZED, 'Credenciales invalidas o faltantes.')
        if resp.status_code >= 400:
            return failed(ERROR_INVALID_RESPONSE, f'HTTP {resp.status_code}')
        result = _parse_rpc(resp).get('result') or {}
        if 'protocolVersion' not in result and 'capabilities' not in result:
            return failed(ERROR_INVALID_RESPONSE, 'La respuesta no es un handshake MCP valido.')
        session_id = resp.headers.get('Mcp-Session-Id')
        report['capabilities'] = {k: True for k in (result.get('capabilities') or {})}
        report['server_info'] = {k: str(v)[:100] for k, v in (result.get('serverInfo') or {}).items() if k in ('name', 'version')}
        try:  # best effort: el spec pide notificar initialized antes de operar
            _rpc(server, 'notifications/initialized', request_id=None, session_id=session_id)
            tools = _parse_rpc(_rpc(server, 'tools/list', request_id=2, session_id=session_id)).get('result') or {}
            report['tools_count'] = len(tools.get('tools') or [])
        except (requests.RequestException, ValueError):
            report['capabilities'].setdefault('tools_list_failed', True)
    except requests.exceptions.Timeout:
        report['latency_ms'] = int((time.monotonic() - start) * 1000)
        return failed(ERROR_TIMEOUT, 'Timeout de conexion.')
    except requests.exceptions.ConnectionError as exc:
        report['latency_ms'] = int((time.monotonic() - start) * 1000)
        code, message = connection_failure(server.server_url, _classify_connection_error(exc))
        return failed(code, message)
    except (requests.RequestException, ValueError) as exc:
        return failed(ERROR_UNKNOWN, type(exc).__name__)
    report.update(ok=True, status='HEALTHY', error_code=SUCCESS, message='')
    return report


class MCPServerSelector:
    @staticmethod
    def list_servers():
        return MCPServer.objects.filter(is_deleted=False).order_by('name')

    @staticmethod
    def get_server(uuid):
        return MCPServer.objects.get(uuid=uuid, is_deleted=False)


def _audit(user, metadata: dict):
    from security.models import SecurityEvent
    from security.services.commands import SecurityCommands
    SecurityCommands.log_event(SecurityEvent.AI_PROVIDER_UPDATED, user=user, metadata={'resource': 'MCPServer', **metadata})


class MCPServerCommands:
    @staticmethod
    @transaction.atomic
    def create_server(data: dict, user=None) -> MCPServer:
        server = MCPServer(**{k: v for k, v in data.items() if k in _SERVER_ALLOWED_FIELDS})
        server.full_clean()
        server.save()
        _audit(user, {'action': 'mcp_created', 'server_uuid': str(server.uuid), 'name': server.name})
        return server

    @staticmethod
    @transaction.atomic
    def update_server(server: MCPServer, data: dict, user=None) -> MCPServer:
        changed = []
        for field in _SERVER_ALLOWED_FIELDS:
            if field in data:
                if field == 'api_key' and data[field] == '':
                    continue  # vacio = no cambiar la key existente (igual que los proveedores LLM)
                setattr(server, field, data[field])
                changed.append(field)
        server.full_clean()
        server.save()
        _audit(user, {'action': 'mcp_updated', 'server_uuid': str(server.uuid), 'fields': [f for f in changed if f != 'api_key'],
                      'api_key_changed': 'api_key' in changed})
        return server

    @staticmethod
    @transaction.atomic
    def delete_server(server: MCPServer, user=None) -> None:
        server.is_deleted = True
        server.save(update_fields=['is_deleted', 'updated_at'])
        _audit(user, {'action': 'mcp_deleted', 'server_uuid': str(server.uuid), 'name': server.name})

    @staticmethod
    @transaction.atomic
    def test_server(server: MCPServer, user=None) -> dict:
        report = probe_mcp_server(server)
        server.status = report['status']
        server.last_checked_at = timezone.now()
        server.last_latency_ms = report['latency_ms']
        server.last_error = '' if report['ok'] else (report['message'] or report['error_code'])[:300]
        if report['ok']:
            server.capabilities = report['capabilities']
            server.tools_count = report['tools_count']
        server.save(update_fields=['status', 'last_checked_at', 'last_latency_ms', 'last_error', 'capabilities', 'tools_count', 'updated_at'])
        _audit(user, {'action': 'mcp_tested', 'server_uuid': str(server.uuid), 'ok': report['ok'], 'status': report['status']})
        return report
