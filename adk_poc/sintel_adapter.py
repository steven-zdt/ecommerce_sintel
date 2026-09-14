"""
ADK-02 -- SINTEL Tool Adapter (POC, sigue aislado -- ver adk_poc/README.md).

Traduce una Tool REAL de ai_engine (RegisteredTool: ToolMetadata + funcion
async `(ctx: tools.metadata.ToolContext, **args) -> dict`, ver
ai_engine/tools/registry.py) a un google.adk.tools.FunctionTool real, SIN
reescribir la logica de la tool -- la funcion original se llama tal cual.

Regla de la mision (seccion 5, "no duplicar"): esto es un adapter fino, no
una segunda implementacion de las tools. La prueba de que es fino: importa
el modulo REAL de ai_engine.tools via sys.path (no copia/reescribe nada de
su codigo) y lo invoca sin modificarlo.

Mapeo:
  ToolMetadata.name/description   -> nombre/descripcion de la FunctionTool ADK
  ToolMetadata.requires_confirmation -> FunctionTool(require_confirmation=...)
                                        (mapeo directo, mismo concepto en ambos lados)
  ToolContext(user, token) de Sintel -> reconstruido desde tool_context.state
                                        de ADK (sembrado en la sesion al
                                        arrancarla -- la resolucion de
                                        identidad real es responsabilidad de
                                        ADK-03/Root Workflow, no de este
                                        adapter; aqui solo se demuestra el
                                        mecanismo de paso de contexto)
"""
import inspect
from typing import Any, Callable, Optional

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext as AdkToolContext

SINTEL_USER_STATE_KEY = "sintel_user"
SINTEL_TOKEN_STATE_KEY = "sintel_token"

# ADK-04: 5 tools reales de ai_engine (core_tools.py -- Core*Update/Create)
# usan `**kwargs` para overrides opcionales (ver ToolMetadata.args_schema,
# que SI declara cada campo real: title/subtitle/link_url/...). inspect.
# signature() no puede recuperar nombres de campos desde un **kwargs --
# hay que sintetizarlos desde args_schema o el LLM nunca veria esos campos.
_JSON_SCHEMA_TYPE_MAP: dict[str, type] = {
    "string": str, "integer": int, "number": float, "boolean": bool,
    "object": dict, "array": list,
}


def _sintel_ctx_from_adk_state(adk_tool_context: AdkToolContext):
    """Reconstruye tools.metadata.ToolContext (Sintel) desde el estado de
    sesion de ADK. Import diferido: el modulo real de ai_engine.tools solo
    debe existir en sys.path cuando se usa este adapter, no como dependencia
    dura de adk_poc en general."""
    from tools.metadata import ToolContext as SintelToolContext

    state = adk_tool_context.state
    return SintelToolContext(
        user=state.get(SINTEL_USER_STATE_KEY, {}),
        token=state.get(SINTEL_TOKEN_STATE_KEY, ""),
    )


def adapt_sintel_tool(registered_tool) -> FunctionTool:
    """
    registered_tool: tools.registry.RegisteredTool real (obtenido via
    tools.registry.get_tool("OrderStatusTool") tras importar el modulo de
    dominio real, ej. `import tools.orders_tools`).

    Construye dinamicamente un wrapper con la MISMA firma que la funcion
    Sintel real (menos `ctx`, mas `tool_context` de ADK) -- ADK necesita una
    firma Python real con type hints para declarar la tool al LLM (confirmado
    en ADK-01: FunctionTool introspecciona `inspect.signature(func)`, no
    acepta un JSON-schema suelto). El wrapper llama a la funcion Sintel REAL
    sin reimplementar nada de su logica.

    Tools con `**kwargs` real (ej. CoreBannerUpdateTool): `inspect.signature`
    no puede recuperar los nombres de campo desde un VAR_KEYWORD -- se
    sintetizan parametros keyword-only adicionales desde
    `ToolMetadata.args_schema.properties` (la fuente real que YA declara esos
    campos, ver ai_engine/tools/core_tools.py) para que el LLM los vea. El
    wrapper en si sigue reenviando todo como **kwargs al `real_func` --
    Python no exige que `__signature__` coincida con la firma real en tiempo
    de ejecucion, solo se usa para la declaracion de schema al LLM.
    """
    metadata = registered_tool.metadata
    real_func: Callable[..., Any] = registered_tool.func
    real_sig = inspect.signature(real_func)

    named_params = []
    fixed_names: set[str] = set()
    has_var_keyword = False
    for name, p in real_sig.parameters.items():
        if name == "ctx":
            continue
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            has_var_keyword = True
            continue
        named_params.append(p)
        fixed_names.add(name)

    extra_params = []
    if has_var_keyword:
        args_schema = metadata.args_schema or {}
        required = set(args_schema.get("required", []))
        for prop_name, prop_schema in (args_schema.get("properties") or {}).items():
            if prop_name in fixed_names:
                continue
            py_type = _JSON_SCHEMA_TYPE_MAP.get(prop_schema.get("type"), str)
            is_required = prop_name in required
            extra_params.append(inspect.Parameter(
                prop_name, inspect.Parameter.KEYWORD_ONLY,
                default=inspect.Parameter.empty if is_required else None,
                annotation=py_type if is_required else Optional[py_type],
            ))

    adk_context_param = inspect.Parameter(
        "tool_context", inspect.Parameter.KEYWORD_ONLY, annotation=AdkToolContext,
    )
    wrapper_sig = inspect.Signature(named_params + extra_params + [adk_context_param])

    async def wrapper(*, tool_context: AdkToolContext, **kwargs):
        sintel_ctx = _sintel_ctx_from_adk_state(tool_context)
        # Los campos opcionales sintetizados desde args_schema que el LLM no
        # lleno llegan como None -- se descartan aqui (mismo criterio que ya
        # aplican las tools reales de escritura, ver core_tools.py:
        # "{k: v for k, v in kwargs.items() if v is not None}") para no
        # sobre-escribir un campo real con None.
        call_kwargs = {
            k: v for k, v in kwargs.items() if k in fixed_names or v is not None
        }
        # Llamada real a la funcion Sintel original -- cero logica de negocio
        # nueva en este adapter.
        return await real_func(sintel_ctx, **call_kwargs)

    wrapper.__name__ = metadata.name
    wrapper.__doc__ = metadata.description
    wrapper.__signature__ = wrapper_sig

    return FunctionTool(wrapper, require_confirmation=metadata.requires_confirmation)
