"""
Persistencia del OAuth del MCP: registro de cliente (dynamic client
registration) + tokens (access + refresh).

Implementa el Protocol `mcp.client.auth.TokenStorage` del SDK. Se guarda en
disco, en MCP_TOKEN_STORE_DIR (un volumen montado del contenedor sintel_ai, NO
versionado). Archivos con permisos 0600.

El refresh token es la unica credencial persistente del MCP: NUNCA se loggea,
NUNCA sale de este modulo hacia Django / el prompt / el estado del grafo.
"""
import json
import logging
import os
from pathlib import Path

from config import MCP_TOKEN_STORE_DIR

logger = logging.getLogger("mcp_client.storage")


class FileTokenStorage:
    """TokenStorage sobre disco para un servidor MCP concreto (por `server_key`)."""

    def __init__(self, server_key: str, base_dir: str | None = None):
        self._dir = Path(base_dir or MCP_TOKEN_STORE_DIR)
        self._key = server_key
        self._tokens_path = self._dir / f"{server_key}_tokens.json"
        self._client_path = self._dir / f"{server_key}_client.json"

    # -- helpers de disco --------------------------------------------------

    def _read(self, path: Path) -> dict | None:
        try:
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return None
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("mcp_client.storage: %s ilegible (%s) -- se ignora", path.name, exc)
            return None

    def _write(self, path: Path, payload: dict) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, path)

    def has_credentials(self) -> bool:
        data = self._read(self._tokens_path) or {}
        return bool(data.get("refresh_token") or data.get("access_token"))

    def seed_client_info(self, *, client_id: str, redirect_uris: list[str],
                         scope: str = "", client_name: str = "SINTEL ai_engine") -> None:
        """Escribe un registro de cliente OAuth PRE-REGISTRADO (el MCP de Meta no
        soporta dynamic registration). Sincrono a proposito: se llama desde
        build_oauth_provider() antes de arrancar el flujo async. Forma compatible
        con OAuthClientInformationFull del SDK."""
        payload = {
            "client_id": client_id,
            "redirect_uris": redirect_uris,
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": client_name,
        }
        if scope:
            payload["scope"] = scope
        existing = self._read(self._client_path) or {}
        if existing.get("client_id") == client_id and existing.get("scope") == payload.get("scope"):
            return  # ya sembrado e identico
        self._write(self._client_path, payload)
        logger.info("mcp_client.storage: client_id pre-registrado sembrado para '%s'", self._key)

    # -- Protocol TokenStorage del SDK -----------------------------------

    async def get_tokens(self):
        data = self._read(self._tokens_path)
        if not data:
            return None
        from mcp.shared.auth import OAuthToken
        return OAuthToken.model_validate(data)

    async def set_tokens(self, tokens) -> None:
        self._write(self._tokens_path, tokens.model_dump(exclude_none=True))
        logger.info("mcp_client.storage: tokens de '%s' actualizados", self._key)

    async def get_client_info(self):
        data = self._read(self._client_path)
        if not data:
            return None
        from mcp.shared.auth import OAuthClientInformationFull
        return OAuthClientInformationFull.model_validate(data)

    async def set_client_info(self, client_info) -> None:
        self._write(self._client_path, client_info.model_dump(exclude_none=True, mode="json"))
        logger.info("mcp_client.storage: registro de cliente OAuth de '%s' guardado", self._key)
