"""
MetaAdsMCPClient -- adaptador hacia el MCP oficial de Meta Ads.

Responsabilidad UNICA: hablar el protocolo MCP (transporte streamable-HTTP +
OAuth). Sin logica de negocio de SINTEL, sin ORM, sin capabilities. La
seleccion de que tool llamar y la aprobacion humana viven arriba (Action Graph,
FASE 11-14).

Contrato de errores: ningun metodo publico propaga una excepcion al caller --
todo vuelve como dict serializable ({"error": ..., ...}), igual que
tools/http_bridge.py. El refresh token nunca aparece en esos dicts ni en logs.

Los imports del SDK `mcp` son perezosos (dentro de los metodos) para que este
modulo se pueda importar y testear sin el paquete instalado.
"""
import asyncio
import logging

from config import MCP_CALL_TIMEOUT_S, MCP_OAUTH_CALLBACK_PORT
from mcp_client.policy import classify_mcp_tool
from mcp_client.registry import MCPServerRegistry
from mcp_client.storage import FileTokenStorage

logger = logging.getLogger("mcp_client.client")


class MCPClientError(Exception):
    """Fallo de configuracion / autorizacion del cliente MCP (no de una tool)."""


class MetaAdsMCPClient:

    def __init__(self, *, server_key: str = "meta_ads", allow_writes: bool | None = None):
        srv = MCPServerRegistry.get(server_key)
        if srv is None:
            raise MCPClientError(f"Servidor MCP desconocido: {server_key!r}")
        self._srv = srv
        self._allow_writes = srv.allow_writes if allow_writes is None else bool(allow_writes)
        self._storage = FileTokenStorage(srv.key)

    # -- estado ----------------------------------------------------------

    @property
    def server_url(self) -> str:
        return self._srv.url

    def is_authorized(self) -> bool:
        """True si hay un refresh/access token guardado. No valida contra Meta."""
        return self._storage.has_credentials()

    # -- OAuth ----------------------------------------------------------

    @property
    def redirect_uri(self) -> str:
        return f"http://localhost:{MCP_OAUTH_CALLBACK_PORT}/callback"

    def build_oauth_provider(self, *, redirect_handler=None, callback_handler=None):
        """OAuthClientProvider del SDK. Los handlers solo se pasan reales desde
        mcp_client/authorize.py (flujo interactivo one-shot). En uso normal el
        provider solo refresca el token guardado, sin interaccion.

        El MCP de Meta NO soporta dynamic registration: si hay client_id
        configurado se siembra el registro de cliente en storage para que el SDK
        salte el /register. Sin client_id, lanza MCPClientError con instrucciones.
        """
        from mcp.client.auth import OAuthClientProvider
        from mcp.shared.auth import OAuthClientMetadata

        if not self._srv.client_id:
            raise MCPClientError(
                "MCP_META_ADS_CLIENT_ID (o META_APP_ID) no configurado. El MCP de "
                "Meta Ads no permite dynamic registration: necesitas un App de Meta "
                "(developers.facebook.com) con este redirect URI registrado: "
                f"{self.redirect_uri}"
            )
        self._storage.seed_client_info(
            client_id=self._srv.client_id,
            redirect_uris=[self.redirect_uri],
            scope=self._srv.scope,
        )

        metadata = OAuthClientMetadata(
            client_name="SINTEL ai_engine (Meta Ads MCP)",
            redirect_uris=[self.redirect_uri],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            token_endpoint_auth_method="none",
            scope=self._srv.scope or None,
        )
        return OAuthClientProvider(
            server_url=self._srv.url,
            client_metadata=metadata,
            storage=self._storage,
            redirect_handler=redirect_handler or _redirect_needs_authorize,
            callback_handler=callback_handler or _callback_needs_authorize,
        )

    # -- sesion MCP ----------------------------------------------------------

    def _open_session(self, *, auth_provider=None):
        """Devuelve un async context manager que entrega una ClientSession MCP
        ya inicializada. Se separa para poder mockearlo en tests."""
        from contextlib import asynccontextmanager

        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        provider = auth_provider or self.build_oauth_provider()

        @asynccontextmanager
        async def _cm():
            async with streamablehttp_client(self._srv.url, auth=provider) as (read, write, _sid):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

        return _cm()

    # -- API publica -----------------------------------------------------------

    async def list_tools(self) -> dict:
        if not self.is_authorized():
            return _unauthorized()
        try:
            async with self._open_session() as session:
                result = await asyncio.wait_for(session.list_tools(), timeout=MCP_CALL_TIMEOUT_S)
        except Exception as exc:  # noqa: BLE001 -- contrato: nunca propagar
            return _wrap_error(exc)
        tools = [
            {
                "name": t.name,
                "description": getattr(t, "description", "") or "",
                "input_schema": getattr(t, "inputSchema", None),
                "policy": classify_mcp_tool(self._srv.key, t.name, allow_writes=self._allow_writes),
            }
            for t in getattr(result, "tools", [])
        ]
        return {"authorized": True, "count": len(tools), "tools": tools}

    async def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        decision = classify_mcp_tool(self._srv.key, name, allow_writes=self._allow_writes)
        if decision != "allow":
            logger.info("mcp_client: tool '%s' bloqueada por policy=%s", name, decision)
            return {
                "error": (
                    f"La tool MCP '{name}' esta clasificada como '{decision}'. "
                    "Esta capa (FASE 10) es de solo lectura; las escrituras llegan "
                    "en las FASE 16-18 con aprobacion humana."
                ),
                "policy": decision,
            }
        if not self.is_authorized():
            return _unauthorized()
        try:
            async with self._open_session() as session:
                result = await asyncio.wait_for(
                    session.call_tool(name, arguments or {}), timeout=MCP_CALL_TIMEOUT_S,
                )
        except Exception as exc:  # noqa: BLE001
            return _wrap_error(exc)
        return _serialize_tool_result(result)

    async def ping(self) -> dict:
        """Smoke test de la conexion: refresca el token si hace falta y lista tools."""
        out = await self.list_tools()
        if out.get("authorized"):
            return {"ok": True, "server": self._srv.url, "tool_count": out.get("count", 0)}
        return {"ok": False, "server": self._srv.url, **out}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _unauthorized() -> dict:
    return {
        "authorized": False,
        "error": (
            "El MCP de Meta Ads no esta autorizado en este entorno. Ejecuta una "
            "vez, dentro del contenedor sintel_ai: `python -m mcp_client.authorize`."
        ),
    }


def _wrap_error(exc: Exception) -> dict:
    text = str(exc)
    low = text.lower()
    if isinstance(exc, MCPClientError):
        return {"error": text, "authorized": False}
    if isinstance(exc, asyncio.TimeoutError):
        return {"error": "El MCP de Meta no respondio a tiempo.", "transient": True}
    if any(k in low for k in ("401", "unauthorized", "invalid_grant", "invalid_token", "forbidden", "403")):
        return {
            "error": "Meta rechazo la autorizacion del MCP (token expirado o revocado). "
                     "Vuelve a correr `python -m mcp_client.authorize`.",
            "authorized": False,
        }
    if any(k in low for k in ("timeout", "connection", "reset", "temporarily", "503", "502", "429")):
        return {"error": "Fallo transitorio hablando con el MCP de Meta.", "transient": True}
    logger.warning("mcp_client: error no clasificado: %s", type(exc).__name__)
    return {"error": "Error hablando con el MCP de Meta Ads."}


def _serialize_tool_result(result) -> dict:
    """Convierte un CallToolResult del SDK a un dict plano y serializable."""
    is_error = bool(getattr(result, "isError", False))
    structured = getattr(result, "structuredContent", None)
    blocks = []
    for item in getattr(result, "content", []) or []:
        itype = getattr(item, "type", None)
        if itype == "text":
            blocks.append({"type": "text", "text": getattr(item, "text", "")})
        elif itype in ("image", "audio"):
            blocks.append({"type": itype, "mimeType": getattr(item, "mimeType", None)})
        else:
            blocks.append({"type": itype or "unknown"})
    out = {"is_error": is_error, "content": blocks}
    if structured is not None:
        out["structured"] = structured
    return out


async def _redirect_needs_authorize(auth_url: str) -> None:
    raise MCPClientError(
        "El MCP requiere autorizacion interactiva y no hay refresh token guardado. "
        "Ejecuta `python -m mcp_client.authorize`."
    )


async def _callback_needs_authorize() -> tuple[str, str | None]:
    raise MCPClientError(
        "El MCP requiere autorizacion interactiva. Ejecuta `python -m mcp_client.authorize`."
    )
