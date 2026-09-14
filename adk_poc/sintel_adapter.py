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
from typing import Any, Callable

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext as AdkToolContext

SINTEL_USER_STATE_KEY = "sintel_user"
SINTEL_TOKEN_STATE_KEY = "sintel_token"


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
    """
    metadata = registered_tool.metadata
    real_func: Callable[..., Any] = registered_tool.func
    real_sig = inspect.signature(real_func)

    forwarded_params = [
        p for name, p in real_sig.parameters.items() if name != "ctx"
    ]
    adk_context_param = inspect.Parameter(
        "tool_context", inspect.Parameter.KEYWORD_ONLY, annotation=AdkToolContext,
    )
    wrapper_sig = inspect.Signature(forwarded_params + [adk_context_param])

    async def wrapper(*, tool_context: AdkToolContext, **kwargs):
        sintel_ctx = _sintel_ctx_from_adk_state(tool_context)
        # Llamada real a la funcion Sintel original -- cero logica de negocio
        # nueva en este adapter.
        return await real_func(sintel_ctx, **kwargs)

    wrapper.__name__ = metadata.name
    wrapper.__doc__ = metadata.description
    wrapper.__signature__ = wrapper_sig

    return FunctionTool(wrapper, require_confirmation=metadata.requires_confirmation)
