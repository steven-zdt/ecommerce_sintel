"""
mcp_server/policy.py -- clases de herramienta y perfiles MCP (plan MCP sec. 12, 30, 34).

Esta es una capa ADICIONAL: `MCP permission != Django permission != Tool permission != business authorization`. Que un perfil permita una Tool NO da autoridad sobre Django: cada llamada
sigue pasando por la autenticacion, los permisos y la capa de servicio de Django con el token del propio admin.
"""
from . import errors
from .errors import McpToolError

READ = "READ"
WRITE = "WRITE"
DESTRUCTIVE = "DESTRUCTIVE"
EXTERNAL_SIDE_EFFECT = "EXTERNAL_SIDE_EFFECT"
SECURITY_SENSITIVE = "SECURITY_SENSITIVE"

# tool -> clase. Las clases DESTRUCTIVE/EXTERNAL_SIDE_EFFECT/SECURITY_SENSITIVE exigen confirmacion explicita (ver crud.py).
TOOL_CLASS = {
    "mcp.whoami": READ, "api.describe": READ, "crud.list": READ, "crud.get": READ,
    "crud.preview_create": READ, "crud.preview_update": READ, "crud.preview_delete": READ,
    "crud.create": WRITE, "crud.update": WRITE, "crud.delete": DESTRUCTIVE,
    "code.search": READ, "code.read": READ,
}

_READ_ONLY = {"mcp.whoami", "api.describe", "crud.list", "crud.get", "code.search", "code.read"}
_CRUD = {"crud.preview_create", "crud.preview_update", "crud.preview_delete", "crud.create", "crud.update", "crud.delete"}

# Los perfiles de codigo (CODE_REVIEW/CODE_CHANGE) reservan las Tools del plano de codigo que aun no existen (impact/propose/validate/tests/approval/promote/rollback):
# hoy equivalen a READ_ONLY. Cuando se integre ai_editor se anaden aqui, siempre SIN saltarse la aprobacion humana de ai_editor (ni siquiera FULL_MAINTAINER).
PROFILE_TOOLS = {
    "READ_ONLY": frozenset(_READ_ONLY),
    "ADMIN_CRUD": frozenset(_READ_ONLY | _CRUD),
    "CODE_REVIEW": frozenset(_READ_ONLY),
    "CODE_CHANGE": frozenset(_READ_ONLY),
    "FULL_MAINTAINER": frozenset(_READ_ONLY | _CRUD),
}


def allowed_tools(profile: str) -> frozenset:
    return PROFILE_TOOLS.get(profile, frozenset())


def require(profile: str, tool: str) -> None:
    if tool not in TOOL_CLASS:
        raise McpToolError(errors.FORBIDDEN_TOOL, "Herramienta desconocida.")
    if tool not in allowed_tools(profile):
        raise McpToolError(errors.FORBIDDEN_TOOL, f"Tu perfil MCP ({profile}) no incluye '{tool}'.", profile=profile)
