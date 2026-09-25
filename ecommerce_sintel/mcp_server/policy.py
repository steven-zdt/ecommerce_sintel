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
    "code.search": READ, "code.read": READ, "business.audit": READ,
    "code.graph_status": READ, "code.describe_symbol": READ, "code.find_references": READ, "code.impact_analysis": READ, "code.resolve_change": READ,
    "code.build_context": READ, "code.find_tests": READ, "code.list_changes": READ, "code.change_status": READ,
    "code.propose_change": WRITE, "code.discard_change": WRITE, "code.promote_change": DESTRUCTIVE, "code.rollback_change": DESTRUCTIVE,
}

_READ_ONLY = {"mcp.whoami", "api.describe", "crud.list", "crud.get", "code.search", "code.read", "business.audit"}
_CRUD = {"crud.preview_create", "crud.preview_update", "crud.preview_delete", "crud.create", "crud.update", "crud.delete"}

# Plano de codigo (ai_editor, solo desarrollo; Django lo apaga por defecto). NO existe Tool de aprobacion: la decision es de un humano en el panel (Django rechaza via=mcp).
_CODE_REVIEW = {"code.graph_status", "code.describe_symbol", "code.find_references", "code.impact_analysis", "code.resolve_change", "code.build_context", "code.find_tests",
                "code.list_changes", "code.change_status"}
_CODE_CHANGE = {"code.propose_change", "code.discard_change", "code.promote_change", "code.rollback_change"}
PROFILE_TOOLS = {
    "READ_ONLY": frozenset(_READ_ONLY),
    "ADMIN_CRUD": frozenset(_READ_ONLY | _CRUD),
    "CODE_REVIEW": frozenset(_READ_ONLY | _CODE_REVIEW),
    "CODE_CHANGE": frozenset(_READ_ONLY | _CODE_REVIEW | _CODE_CHANGE),
    "FULL_MAINTAINER": frozenset(_READ_ONLY | _CRUD | _CODE_REVIEW | _CODE_CHANGE),
}


def allowed_tools(profile: str) -> frozenset:
    return PROFILE_TOOLS.get(profile, frozenset())


def require(profile: str, tool: str) -> None:
    if tool not in TOOL_CLASS:
        raise McpToolError(errors.FORBIDDEN_TOOL, "Herramienta desconocida.")
    if tool not in allowed_tools(profile):
        raise McpToolError(errors.FORBIDDEN_TOOL, f"Tu perfil MCP ({profile}) no incluye '{tool}'.", profile=profile)
