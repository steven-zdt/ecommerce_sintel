"""
Rutas del AI Gateway.

Fase 1: /context (identidad).
Fase 2: /tools/debug (invocacion directa de Tools, SOLO dev tras el flag
AI_TOOLS_DEBUG) -- separa "la Tool funciona?" de "el LLM la elige bien?"
(eso llega en la Fase 3 con el Action Graph). Las rutas de capability por
dominio se conectaran al Action Graph, no se duplican aqui como REST.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import tools as tool_registry
from auth import get_user_context, get_validated_token
from capabilities import CapabilityRegistry
from config import AI_TOOLS_DEBUG
from tools import ToolContext

ai_router = APIRouter(prefix="/api/v1/ai", tags=["ai-gateway"])


@ai_router.get("/context")
async def ai_context(user_context: dict = Depends(get_user_context)) -> dict:
    """
    Devuelve el contexto de identidad del usuario autenticado, resuelto por
    Django (Customer Context Builder v1). Sirve ademas como smoke-test del
    puente completo: JWT valido -> identidad real; sin JWT -> 401.
    """
    return user_context


class ToolDebugRequest(BaseModel):
    tool: str
    args: dict = {}
    # Fase 4: las Tools con side_effects exigen confirmed=true tambien aqui --
    # Restriccion Dura: ninguna escritura se salta la Policy Layer, ni en
    # pruebas manuales via /tools/debug.
    confirmed: bool = False


def _require_debug_enabled() -> None:
    # 404 (no 403) para no revelar la existencia del endpoint fuera de dev.
    if not AI_TOOLS_DEBUG:
        raise HTTPException(404, "Not found")


@ai_router.get("/tools/debug")
async def tools_debug_list(token: str = Depends(get_validated_token)) -> dict:
    """Lista Tools registradas y Capabilities (solo dev)."""
    _require_debug_enabled()
    from agents import AgentRegistry
    return {
        "tools": [m.model_dump() for m in tool_registry.list_tools()],
        "capabilities": [c.model_dump() for c in CapabilityRegistry.list_all()],
        "agents": [a.model_dump() for a in AgentRegistry.list_all()],
    }


@ai_router.post("/tools/debug")
async def tools_debug_invoke(
    req: ToolDebugRequest,
    token: str = Depends(get_validated_token),
    user_context: dict = Depends(get_user_context),
) -> dict:
    """
    Invoca una Tool directamente con el JWT del usuario autenticado (solo
    dev). Acepta el nombre de la Tool o de una capability (que se resuelve
    via CapabilityRegistry, igual que hara el LLM en la Fase 3).
    """
    _require_debug_enabled()
    tool_name = req.tool
    if tool_registry.get_tool(tool_name) is None:
        resolved = CapabilityRegistry.resolve_tool_name(tool_name)
        if resolved:
            tool_name = resolved
    tool = tool_registry.get_tool(tool_name)
    if tool is not None and tool.metadata.side_effects and not req.confirmed:
        return {"tool": tool_name, "result": {
            "error": "Tool de escritura: requiere confirmed=true (Policy Layer aplica tambien en debug).",
            "status_code": 403,
        }}
    # F1 (AUDITORIA/16, 2026-08-01): antes este endpoint solo validaba side_effects+confirmed,
    # sin chequear metadata.permissions -- a diferencia del flujo normal de /chat
    # (action_graph.py::node_evaluate_policy), que SI lo hace. No era explotable (los endpoints
    # internos de Django re-validan permisos de forma independiente y son la autoridad final),
    # pero era una asimetria real de defensa en profundidad frente al flujo normal. Mismo
    # criterio que node_evaluate_policy: solo el chequeo de IsAdminUser, no se duplica el
    # rate-limit propio de esa capability aca (este endpoint ya esta detras de AI_TOOLS_DEBUG,
    # solo dev).
    if tool is not None and "IsAdminUser" in tool.metadata.permissions and not user_context.get("is_staff"):
        return {"tool": tool_name, "result": {
            "error": "Tool solo para administradores (Policy Layer aplica tambien en debug).",
            "status_code": 403,
        }}
    ctx = ToolContext(user=user_context, token=token)
    result = await tool_registry.invoke(tool_name, ctx, req.args)
    return {"tool": tool_name, "result": result}


@ai_router.get("/mcp/status")
async def mcp_status(token: str = Depends(get_validated_token)) -> dict:
    """
    Estado de los servidores MCP configurados (FASE 10 integracion Meta Business,
    solo dev). No expone tokens. `?ping=1` intenta una llamada real (refresca el
    token si hace falta y cuenta las tools).
    """
    _require_debug_enabled()
    from mcp_client.registry import MCPServerRegistry

    servers = []
    for srv in MCPServerRegistry.list_all():
        from mcp_client.client import MetaAdsMCPClient
        client = MetaAdsMCPClient(server_key=srv.key)
        servers.append({
            "key": srv.key,
            "url": srv.url,
            "enabled": srv.enabled,
            "allow_writes": srv.allow_writes,
            "authorized": client.is_authorized(),
        })
    return {"servers": servers}


@ai_router.post("/mcp/ping")
async def mcp_ping(token: str = Depends(get_validated_token),
                   user_context: dict = Depends(get_user_context)) -> dict:
    """Smoke test real de la conexion MCP (solo dev, solo admin)."""
    _require_debug_enabled()
    if not user_context.get("is_staff"):
        raise HTTPException(403, "Solo administradores.")
    from mcp_client.client import MetaAdsMCPClient
    return await MetaAdsMCPClient().ping()
