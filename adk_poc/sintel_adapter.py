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

    Construye dinamicamente un wrapper con la firma que el LLM debe ver --
    ADK necesita una firma Python real con type hints para declarar la tool
    (confirmado en ADK-01: FunctionTool introspecciona
    `inspect.signature(func)`, no acepta un JSON-schema suelto). El wrapper
    llama a la funcion Sintel REAL sin reimplementar nada de su logica.

    ADK-05, hallazgo real (`open_support_ticket_tool`, ver
    ai_engine/tools/support_tools.py): la funcion real puede tener un
    parametro con default que EXISTE en Python pero deliberadamente NO esta
    en `args_schema` -- `history: list | None = None`, inyectado por el
    grafo desde su propio estado (Human Handoff), nunca por el LLM ("el LLM
    jamas lo controla", comentario real del codigo). Por eso la superficie
    expuesta al LLM se construye SIEMPRE a partir de
    `ToolMetadata.args_schema.properties` -- la fuente autoritativa real
    ("JSON-schema de argumentos, para bind_tools", metadata.py) -- nunca de
    `inspect.signature` cruda. Un parametro real ausente del schema
    simplemente no se expone ni se reenvia; `real_func` usa su propio
    default. Tools con `**kwargs` real (ej. CoreBannerUpdateTool):
    `inspect.signature` no puede recuperar esos nombres de campo -- se
    sintetizan parametros keyword-only adicionales desde
    `args_schema.properties` para que el LLM los vea.
    """
    metadata = registered_tool.metadata
    real_func: Callable[..., Any] = registered_tool.func
    real_sig = inspect.signature(real_func)
    args_schema = metadata.args_schema or {}
    schema_props: dict = args_schema.get("properties") or {}
    required = set(args_schema.get("required", []))

    fixed_names: set[str] = set()
    has_var_keyword = False
    for name, p in real_sig.parameters.items():
        if name == "ctx":
            continue
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            has_var_keyword = True
            continue
        fixed_names.add(name)

    # Solo lo que args_schema declara se expone al LLM -- ver docstring.
    exposed_params = [
        p for name, p in real_sig.parameters.items()
        if name in fixed_names and name in schema_props
    ]

    extra_params = []
    if has_var_keyword:
        for prop_name, prop_schema in schema_props.items():
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
    wrapper_sig = inspect.Signature(exposed_params + extra_params + [adk_context_param])

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
        # nueva en este adapter. Cualquier parametro real oculto al LLM
        # (ausente de args_schema, ej. `history`) no llega en kwargs -- usa
        # el default real de `real_func`.
        return await real_func(sintel_ctx, **call_kwargs)

    wrapper.__name__ = metadata.name
    wrapper.__doc__ = metadata.description
    wrapper.__signature__ = wrapper_sig

    return FunctionTool(wrapper, require_confirmation=metadata.requires_confirmation)
