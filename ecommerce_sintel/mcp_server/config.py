"""
mcp_server/config.py -- configuracion minima por entorno (plan MCP sec. 38). Solo bootstrap: sin secretos de negocio.

`MCP_AUTH_MODE`: unico modo implementado = `django_jwt` (el bearer del cliente MCP es el JWT de acceso de un admin de Django; el MCP lo valida con Django y lo reenvia,
asi la autoridad y el RBAC siguen siendo los de Django). `service_token` y `oauth` NO estan implementados y el servidor se niega a arrancar con ellos (falla cerrado).
"""
import os
import secrets
from dataclasses import dataclass
from urllib.parse import urlparse

PROFILES = ("READ_ONLY", "ADMIN_CRUD", "CODE_REVIEW", "CODE_CHANGE", "FULL_MAINTAINER")
IMPLEMENTED_AUTH_MODES = ("django_jwt",)


def _bool(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _csv(name: str, default: str = "") -> tuple:
    return tuple(x.strip() for x in os.environ.get(name, default).split(",") if x.strip())


def _profiles(raw: str) -> dict:
    """`email=PERFIL,otro@x.com=ADMIN_CRUD`. Un perfil desconocido se ignora (queda el perfil por defecto, el mas restrictivo)."""
    out = {}
    for chunk in raw.split(","):
        if "=" not in chunk:
            continue
        email, profile = (p.strip() for p in chunk.split("=", 1))
        if email and profile.upper() in PROFILES:
            out[email.lower()] = profile.upper()
    return out


@dataclass(frozen=True)
class Settings:
    enabled: bool
    host: str
    port: int
    public_base_url: str
    auth_mode: str
    django_api_url: str
    django_host_header: str
    allowed_origins: tuple
    allowed_hosts: tuple
    rate_limit_per_minute: int
    write_rate_limit_per_minute: int
    max_body_bytes: int
    request_timeout: float
    max_output_bytes: int
    max_records: int
    max_page_depth: int
    confirmation_ttl: int
    confirmation_secret: str
    default_profile: str
    principal_profiles: dict
    workspace_root: str
    log_level: str

    def validate(self) -> None:
        if self.auth_mode not in IMPLEMENTED_AUTH_MODES:
            raise SystemExit(f"MCP_AUTH_MODE={self.auth_mode!r} no esta implementado (validos: {IMPLEMENTED_AUTH_MODES}). El servidor no arranca sin autenticacion.")
        if self.default_profile not in PROFILES:
            raise SystemExit(f"MCP_DEFAULT_PROFILE invalido: {self.default_profile!r}.")
        if not urlparse(self.public_base_url).scheme:
            raise SystemExit("MCP_PUBLIC_BASE_URL es obligatorio (http(s)://host:puerto).")


def load() -> Settings:
    public = os.environ.get("MCP_PUBLIC_BASE_URL", "http://127.0.0.1:8200").rstrip("/")
    public_host = urlparse(public).netloc
    hosts = _csv("MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*,mcp_server:*")
    if public_host and public_host not in hosts:
        hosts = hosts + (public_host,)
    return Settings(
        enabled=_bool("MCP_ENABLED", False),
        host=os.environ.get("MCP_HOST", "127.0.0.1"),
        port=_int("MCP_PORT", 8200),
        public_base_url=public,
        auth_mode=os.environ.get("MCP_AUTH_MODE", "django_jwt").strip().lower(),
        django_api_url=os.environ.get("MCP_DJANGO_API_URL", "http://django:8000").rstrip("/"),
        django_host_header=os.environ.get("DJANGO_INTERNAL_HOST_HEADER", ""),
        allowed_origins=_csv("MCP_ALLOWED_ORIGINS", ""),
        allowed_hosts=hosts,
        rate_limit_per_minute=_int("MCP_RATE_LIMIT", 60),
        write_rate_limit_per_minute=_int("MCP_WRITE_RATE_LIMIT", 20),
        max_body_bytes=_int("MCP_MAX_BODY_BYTES", 262144),
        request_timeout=float(_int("MCP_REQUEST_TIMEOUT", 20)),
        max_output_bytes=_int("MCP_MAX_OUTPUT_BYTES", 200000),
        max_records=_int("MCP_MAX_RECORDS", 50),
        max_page_depth=_int("MCP_MAX_PAGE_DEPTH", 20),
        confirmation_ttl=_int("MCP_CONFIRMATION_TTL", 300),
        # Sin secreto configurado se genera uno por proceso: las confirmaciones solo valen dentro de este proceso (y mueren al reiniciar).
        confirmation_secret=os.environ.get("MCP_CONFIRMATION_SECRET", "") or secrets.token_hex(32),
        default_profile=os.environ.get("MCP_DEFAULT_PROFILE", "READ_ONLY").strip().upper(),
        principal_profiles=_profiles(os.environ.get("MCP_PRINCIPAL_PROFILES", "")),
        workspace_root=os.environ.get("MCP_WORKSPACE_ROOT", "").strip(),
        log_level=os.environ.get("MCP_LOG_LEVEL", "INFO").upper(),
    )
