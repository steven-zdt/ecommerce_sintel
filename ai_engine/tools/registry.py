"""
ToolRegistry (Fase 2 AI Core): nombre -> funcion + ToolMetadata + JSON-schema
de argumentos (este ultimo para bind_tools en la Fase 3).

Las Tools se declaran en tools/<dominio>.py con el decorador @register_tool
y quedan disponibles via get_tool()/list_tools()/invoke(). El LLM nunca ve
este registro directamente -- solo ve el CapabilityRegistry
(capabilities/registry.py), que apunta aqui.
"""
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from tools.metadata import ToolContext, ToolMetadata

logger = logging.getLogger("tools.registry")

ToolFunc = Callable[..., Awaitable[dict]]


@dataclass
class RegisteredTool:
    metadata: ToolMetadata
    func: ToolFunc


_TOOLS: dict[str, RegisteredTool] = {}


def register_tool(metadata: ToolMetadata):
    """Decorador: registra una Tool async (ctx: ToolContext, **args) -> dict."""
    def decorator(func: ToolFunc) -> ToolFunc:
        if metadata.name in _TOOLS:
            raise ValueError(f"Tool duplicada: {metadata.name}")
        if not inspect.iscoroutinefunction(func):
            raise TypeError(f"La Tool {metadata.name} debe ser async.")
        _TOOLS[metadata.name] = RegisteredTool(metadata=metadata, func=func)
        return func
    return decorator


def get_tool(name: str) -> RegisteredTool | None:
    return _TOOLS.get(name)


def list_tools() -> list[ToolMetadata]:
    return [t.metadata for t in _TOOLS.values()]


async def invoke(name: str, ctx: ToolContext, args: dict[str, Any] | None = None) -> dict:
    """
    Ejecuta una Tool registrada. Los argumentos desconocidos se rechazan
    (nunca **kwargs ciegos hacia la funcion) y todo error vuelve como dict
    serializable -- una Tool jamas propaga excepciones al caller.
    """
    tool = _TOOLS.get(name)
    if tool is None:
        return {"error": f"Tool desconocida: {name}", "status_code": 404}

    args = args or {}
    params = inspect.signature(tool.func).parameters
    accepts_kwargs = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params.values())
    if not accepts_kwargs:
        allowed = set(params) - {"ctx"}
        unknown = set(args) - allowed
        if unknown:
            return {"error": f"Argumentos no soportados: {sorted(unknown)}", "status_code": 400}
    else:
        # Tools **kwargs (ej. CreateRentalRequestTool): filtrar contra su schema
        schema_props = set((tool.metadata.args_schema or {}).get("properties", {}))
        args = {k: v for k, v in args.items() if k in schema_props}

    try:
        return await tool.func(ctx, **args)
    except Exception as exc:
        logger.exception("[tools] Error ejecutando %s: %s", name, exc)
        return {"error": "Error interno ejecutando la herramienta.", "status_code": 500}
