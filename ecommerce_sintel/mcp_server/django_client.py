"""
mcp_server/django_client.py -- UNICO punto por el que el MCP habla con Django (plan MCP sec. 1, 7, 28).

Reglas duras:
- Solo construye URLs a partir del registro (`registry.Resource`): una base `/api/v1/dashboard/<recurso>/` mas, opcionalmente, un uuid validado. No existe una funcion
  "llama a esta URL": el LLM no puede inventar endpoints ni apuntar a otro host (sin SSRF por construccion).
- Reenvia el bearer del cliente MCP: Django aplica SU autenticacion, SUS permisos y SU capa de servicio. El MCP nunca usa credenciales propias.
- Sin redirects, con timeout, con tope de bytes de respuesta.
"""
import json
import re
import uuid as uuid_lib
from dataclasses import dataclass

import httpx

from . import errors
from .config import Settings
from .errors import McpToolError

_TAIL_RE = re.compile(r"^[a-z0-9][a-z0-9_\-/]*/$")
API_PREFIX = "/api/v1/dashboard/"


@dataclass
class ApiResponse:
    status: int
    data: object
    truncated: bool = False

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


def validate_uuid(value: str) -> str:
    try:
        return str(uuid_lib.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        raise McpToolError(errors.INVALID_ARGUMENT, "target debe ser un UUID valido.")


class DjangoAPI:
    def __init__(self, settings: Settings, transport=None):
        self.s = settings
        self._client = httpx.AsyncClient(
            base_url=settings.django_api_url, timeout=httpx.Timeout(settings.request_timeout, connect=5.0), follow_redirects=False,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10), transport=transport)

    def _headers(self, token: str, request_id: str) -> dict:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "X-Request-ID": request_id}
        if self.s.django_host_header:
            # Mismo criterio que ai_engine.config.internal_django_headers: ALLOWED_HOSTS/SECURE_SSL_REDIRECT de produccion aceptan la llamada interna.
            headers["Host"] = self.s.django_host_header
            headers["X-Forwarded-Proto"] = "https"
        return headers

    async def call(self, method: str, tail: str, *, token: str, request_id: str = "-", params: dict | None = None, json_body: dict | None = None) -> ApiResponse:
        """`tail` es la ruta bajo /api/v1/dashboard/ (p. ej. `products/` o `products/<uuid>/`); solo minusculas, digitos, `-`, `_` y `/`."""
        if not _TAIL_RE.match(tail) or ".." in tail:
            raise McpToolError(errors.INVALID_ARGUMENT, "Ruta no permitida.")
        return await self._request(method, API_PREFIX + tail, token=token, request_id=request_id, params=params, json_body=json_body)

    async def report_audit(self, *, token: str, request_id: str, payload: dict) -> None:
        """Copia durable de la auditoria en Django (SecurityEvent MCP_ACTION). Best-effort: un fallo NO afecta a la operacion (ya quedo en los logs del MCP)."""
        try:
            await self._client.post("/api/v1/dashboard/mcp/audit/", json=payload, headers=self._headers(token, request_id))
        except httpx.HTTPError:
            pass

    async def exchange(self, path: str, *, secret: str, request_id: str = "-") -> ApiResponse:
        """POST JSON sin Authorization a una ruta FIJA interna de Django (canje de token personal): el secreto viaja en el cuerpo, nunca en la URL ni en logs."""
        headers = {"Accept": "application/json", "X-Request-ID": request_id}
        if self.s.django_host_header:
            headers["Host"] = self.s.django_host_header
            headers["X-Forwarded-Proto"] = "https"
        try:
            resp = await self._client.post(path, json={"token": secret}, headers=headers)
        except httpx.HTTPError:
            raise McpToolError(errors.UPSTREAM_ERROR, "No se pudo contactar con Django.")
        try:
            data = resp.json()
        except ValueError:
            data = None
        return ApiResponse(resp.status_code, data)

    async def probe(self, path: str, *, token: str, request_id: str = "-", params: dict | None = None) -> ApiResponse:
        """GET a una ruta FIJA interna del propio MCP (whoami, schema): el llamador nunca es el LLM."""
        return await self._request("GET", path, token=token, request_id=request_id, params=params, json_body=None)

    async def _request(self, method, path, *, token, request_id, params, json_body) -> ApiResponse:
        try:
            async with self._client.stream(method, path, headers=self._headers(token, request_id), params=params, json=json_body) as resp:
                cap = self.s.max_output_bytes * 20 if path.endswith("/schema/") else self.s.max_output_bytes * 2
                chunks, size, truncated = [], 0, False
                async for chunk in resp.aiter_bytes():
                    size += len(chunk)
                    if size > cap:
                        truncated = True
                        break
                    chunks.append(chunk)
                status = resp.status_code
        except httpx.TimeoutException:
            raise McpToolError(errors.UPSTREAM_ERROR, "Django no respondio a tiempo.")
        except httpx.HTTPError:
            raise McpToolError(errors.UPSTREAM_ERROR, "No se pudo contactar con Django.")
        body = b"".join(chunks)
        if truncated:
            return ApiResponse(status, None, truncated=True)
        try:
            data = json.loads(body) if body else None
        except ValueError:
            data = None
        return ApiResponse(status, data)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def reachable(self) -> bool:
        try:
            resp = await self._client.get("/api/v1/health/", headers={"Host": self.s.django_host_header} if self.s.django_host_header else None)
            return resp.status_code < 500
        except httpx.HTTPError:
            return False
