"""
mcp_server/openapi.py -- el OpenAPI de Django como CONTRATO (plan MCP sec. 6, 28).

Se descarga de `/api/schema/` (Django lo protege con IsAdminUser) con el token del cliente y se cachea unos minutos. Sirve para: (1) `api.describe`, y (2) verificar que cada operacion del
registro existe de verdad: una ESCRITURA que el OpenAPI no confirma se trata como no disponible (falla cerrado); una lectura se permite aunque el esquema no se haya podido cargar.
"""
import time

from .django_client import DjangoAPI

SCHEMA_PATH = "/api/schema/"
TTL = 600.0


class OpenAPIIndex:
    def __init__(self, api: DjangoAPI, clock=time.monotonic):
        self._api, self._clock = api, clock
        self._paths: dict | None = None
        self._loaded_at = 0.0
        self.total_paths = 0
        self.dashboard_paths = 0

    @property
    def ready(self) -> bool:
        return self._paths is not None

    async def ensure(self, token: str, request_id: str = "-") -> bool:
        if self._paths is not None and self._clock() - self._loaded_at < TTL:
            return True
        try:
            resp = await self._api.probe(SCHEMA_PATH, token=token, request_id=request_id, params={"format": "json"})
        except Exception:  # noqa: BLE001 - el esquema es una ayuda; su ausencia no rompe las lecturas
            return self._paths is not None
        if not resp.ok or not isinstance(resp.data, dict) or not isinstance(resp.data.get("paths"), dict):
            return self._paths is not None
        self._paths = {path: {m.lower() for m in ops if m.lower() in ("get", "post", "put", "patch", "delete")} for path, ops in resp.data["paths"].items()}
        self._loaded_at = self._clock()
        self.total_paths = len(self._paths)
        self.dashboard_paths = sum(1 for p in self._paths if p.startswith("/api/v1/dashboard/"))
        return True

    def verified(self, method: str, path: str) -> bool | None:
        """True/False si el esquema esta cargado; None si no se pudo cargar (desconocido)."""
        if self._paths is None:
            return None
        return method.lower() in self._paths.get(path, set())
