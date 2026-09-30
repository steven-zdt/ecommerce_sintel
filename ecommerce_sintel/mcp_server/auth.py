"""
mcp_server/auth.py -- autenticacion y principal (plan MCP sec. 4-5, FASE 2).

El bearer del cliente MCP es el JWT de acceso de un ADMIN de Django. El MCP NO lo valida por su cuenta (no tiene el secreto de firma): le pregunta a Django (`/dashboard/mcp/whoami/`,
que exige IsAdminUser). Si Django dice 401/403 el token es invalido, expirado o no es admin => el MCP responde 401. La identidad NUNCA viene de los argumentos de una Tool
(user_id/role/is_admin se ignoran), sino de este verificador. El perfil MCP (READ_ONLY, ADMIN_CRUD...) es una capa ADICIONAL de politica: por defecto el mas restrictivo.
"""
import base64
import hashlib
import json
import time
from dataclasses import dataclass, field

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

from . import errors
from .config import Settings
from .django_client import DjangoAPI
from .errors import McpToolError

WHOAMI = "/api/v1/dashboard/mcp/whoami/"
EXCHANGE = "/api/v1/internal/mcp/exchange/"
PAT_PREFIX = "smcp_"
SWITCH_TTL = 10.0       # con el interruptor del panel activo, un cambio (activar/desactivar escritura) se nota en <= 10 s
POSITIVE_TTL = 60.0     # un token valido se reconfirma con Django cada minuto (revocacion/desactivacion se nota rapido)
NEGATIVE_TTL = 5.0      # un fallo no martillea a Django


@dataclass(frozen=True)
class Principal:
    uuid: str
    email: str
    profile: str
    token: str = field(repr=False)  # nunca aparece en repr/logs

    @property
    def label(self) -> str:
        return self.email or self.uuid


def _jwt_exp(token: str):
    try:
        payload = token.split(".")[1]
        return int(json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("exp"))
    except Exception:  # noqa: BLE001 - un token que no es JWT simplemente no trae exp
        return None


class DjangoTokenVerifier:
    """Implementa el protocolo TokenVerifier del SDK MCP delegando la decision en Django."""

    def __init__(self, settings: Settings, api: DjangoAPI, clock=time.monotonic):
        self.s, self.api, self._clock = settings, api, clock
        self._cache: dict[str, tuple] = {}

    async def _verify_pat(self, pat: str) -> AccessToken | None:
        """Token personal (smcp_...): se canjea en Django por un JWT corto del mismo admin (claim via=mcp). Django sigue siendo la autoridad: revocado, caducado
        o usuario sin permisos => 401. El resultado se cachea `pat_cache_ttl` segundos (= lo que tarda en notarse una revocacion) y nunca mas que la vida del JWT."""
        try:
            resp = await self.api.exchange(EXCHANGE, secret=pat)
        except McpToolError:
            return None  # Django inalcanzable => fallar cerrado
        if not (resp.ok and isinstance(resp.data, dict) and resp.data.get("access") and (resp.data.get("user") or {}).get("is_admin") is True):
            return None
        user = resp.data["user"]
        email = str(user.get("email") or "").lower()
        profile = self.s.principal_profiles.get(email, self.s.default_profile)
        write_until = resp.data.get("write_until_ts")
        if self.s.panel_write_switch and resp.data.get("write_enabled") is True and isinstance(write_until, int) and write_until > time.time() and profile == "READ_ONLY":
            profile = "ADMIN_CRUD"  # ventana de escritura abierta por el admin en el panel (caduca sola)
        return AccessToken(token=resp.data["access"], client_id=email or str(user.get("uuid")), scopes=[profile], expires_at=_jwt_exp(resp.data["access"]),
                           subject=str(user.get("uuid")), claims={"uuid": str(user.get("uuid")), "email": email, "profile": profile, "via_pat": True})

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or len(token) > 4096:
            return None
        key = hashlib.sha256(token.encode()).hexdigest()
        now = self._clock()
        hit = self._cache.get(key)
        if hit and hit[0] > now:
            return hit[1]
        if token.startswith(PAT_PREFIX):
            access = await self._verify_pat(token)
            ttl = min(float(self.s.pat_cache_ttl), 600.0) if access else NEGATIVE_TTL
            if access and self.s.panel_write_switch:
                ttl = min(ttl, SWITCH_TTL)
            if len(self._cache) > 500:
                self._cache.clear()
            self._cache[key] = (now + ttl, access)
            return access
        try:
            resp = await self.api.probe(WHOAMI, token=token)
        except McpToolError:
            return None  # Django inalcanzable => fallar cerrado
        access = None
        if resp.ok and isinstance(resp.data, dict) and resp.data.get("is_admin") is True:
            email = str(resp.data.get("email") or "").lower()
            profile = self.s.principal_profiles.get(email, self.s.default_profile)
            access = AccessToken(token=token, client_id=email or str(resp.data.get("uuid")), scopes=[profile], expires_at=_jwt_exp(token),
                                 subject=str(resp.data.get("uuid")), claims={"uuid": str(resp.data.get("uuid")), "email": email, "profile": profile})
        if len(self._cache) > 500:
            self._cache.clear()
        self._cache[key] = (now + (POSITIVE_TTL if access else NEGATIVE_TTL), access)
        return access


def current_principal() -> Principal:
    access = get_access_token()
    if access is None or not access.claims:
        raise McpToolError(errors.UNAUTHENTICATED, "Se requiere un bearer token valido de administrador.")
    claims = access.claims
    return Principal(uuid=claims["uuid"], email=claims.get("email", ""), profile=claims["profile"], token=access.token)
