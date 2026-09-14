"""
Registro de servidores MCP disponibles para ai_engine.

Hoy solo el MCP oficial de Meta Ads. El registro existe para que anadir un
segundo servidor (p.ej. otro connector oficial) sea declarar una entrada aqui,
no tocar client.py.
"""
from dataclasses import dataclass

from config import (
    MCP_META_ADS_ALLOW_WRITES,
    MCP_META_ADS_CLIENT_ID,
    MCP_META_ADS_ENABLED,
    MCP_META_ADS_SCOPE,
    MCP_META_ADS_URL,
)


@dataclass(frozen=True)
class MCPServer:
    key: str                 # identificador estable (nombre de los archivos de token)
    url: str                 # endpoint MCP remoto
    enabled: bool            # flag de config
    allow_writes: bool       # FASE 10: siempre False hasta F16-18
    # client_id OAuth pre-registrado (el App ID de Meta). El MCP de Meta NO
    # soporta dynamic registration -- sin esto, authorize.py aborta con un
    # mensaje claro.
    client_id: str = ""
    # scopes OAuth solicitados, separados por coma.
    scope: str = ""


_SERVERS: dict[str, MCPServer] = {
    "meta_ads": MCPServer(
        key="meta_ads",
        url=MCP_META_ADS_URL,
        enabled=MCP_META_ADS_ENABLED,
        allow_writes=MCP_META_ADS_ALLOW_WRITES,
        client_id=MCP_META_ADS_CLIENT_ID,
        scope=MCP_META_ADS_SCOPE,
    ),
}


class MCPServerRegistry:

    @staticmethod
    def get(key: str) -> MCPServer | None:
        return _SERVERS.get(key)

    @staticmethod
    def list_all() -> list[MCPServer]:
        return list(_SERVERS.values())

    @staticmethod
    def list_enabled() -> list[MCPServer]:
        return [s for s in _SERVERS.values() if s.enabled]
