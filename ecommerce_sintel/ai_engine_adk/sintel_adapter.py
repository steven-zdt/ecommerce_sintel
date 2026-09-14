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
  ToolMetadata.rate_limit         -> chequeado en el wrapper via rate_limit.py
                                        (ADK-12, mismo Redis/criterio que la
                                        Policy Layer de action_graph.py) antes
                                        de llamar a la funcion real.
  ToolMetadata.permissions        -> "IsAdminUser" chequeado en el wrapper via
                                        permissions.py (ADK-13, mismo criterio
                                        que la Policy Layer de action_graph.py)
                                        antes de llamar a la funcion real.
  ToolContext(user, token) de Sintel -> `user` se reconstruye desde
                                        tool_context.state (no sensible,
                                        perfil ya resuelto por Django);
                                        `token` se resuelve por session_id
                                        desde `_EPHEMERAL_TOKENS` (ADK-08 --
                                        NUNCA desde `state`, para que un
                                        SessionService persistente jamas lo
                                        guarde), con fallback a `state` solo
                                        para los tests aislados de este
                                        modulo que no pasan por el Root
                                        Workflow real.
"""
import inspect
import logging
from typing import Any, Callable, Optional

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext as AdkToolContext

from permissions import user_lacks_admin_permission
from rate_limit import rate_limit_exceeded

logger = logging.getLogger(__name__)

SINTEL_USER_STATE_KEY = "sintel_user"
SINTEL_TOKEN_STATE_KEY = "sintel_token"

# ADK-08, hallazgo de seguridad real: `action_graph.py` (docstring propio)
# declara una regla dura ya vigente en produccion -- "El JWT del usuario
# viaja por config['configurable'], NUNCA dentro del estado (el
# checkpointer persiste el estado; un token no se persiste)". Confirmado
# que ADK tiene su propio `DatabaseSessionService` real (bundled con el
# framework) que persiste `Session.state` completo -- si `sintel_root_
# workflow.py` sembrara el token en `state`/`state_delta` (como hacia
# antes de ADK-08), el dia que se cambie `InMemorySessionService` por un
# backend persistente (ADK-11+) el JWT quedaria escrito en ese backend,
# violando la regla real. Este dict, indexado por `session_id`, cumple el
# mismo rol que `config["configurable"]` de LangGraph -- nunca pasa por
# `Session.state`, por diseno. `sintel_root_workflow.py` lo puebla/limpia
# alrededor de cada turno (ver `run_sintel_turn`); si no lo puebla (como
# los tests aislados de ADK-02 que siguen sembrando el token en `state`
# directo, valido porque ahi jamas hay un backend persistente de por
# medio), `_sintel_ctx_from_adk_state` cae al fallback de `state` de
# abajo, sin romper ningun test existente.
_EPHEMERAL_TOKENS: dict[str, str] = {}


def set_ephemeral_token(session_id: str, token: str) -> None:
    _EPHEMERAL_TOKENS[session_id] = token


def clear_ephemeral_token(session_id: str) -> None:
    _EPHEMERAL_TOKENS.pop(session_id, None)

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
    dura de adk_poc en general.

    El token se busca PRIMERO en `_EPHEMERAL_TOKENS` (nunca persistido, ver
    ADK-08 arriba) por `session.id`; solo si no esta ahi (tests aislados de
    ADK-02 que siembran el token directo en `state`) cae al fallback de
    `state.get(SINTEL_TOKEN_STATE_KEY, "")`."""
    from tools.metadata import ToolContext as SintelToolContext

    state = adk_tool_context.state
    session = getattr(adk_tool_context, "session", None)
    session_id = getattr(session, "id", None)
    token = (
        _EPHEMERAL_TOKENS.get(session_id) if session_id else None
    ) or state.get(SINTEL_TOKEN_STATE_KEY, "")
    return SintelToolContext(
        user=state.get(SINTEL_USER_STATE_KEY, {}),
        token=token,
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
        # ADK-13, hallazgo real de la auditoria (mismo patron que el rate
        # limiter de ADK-12): `ToolMetadata.permissions = ["IsAdminUser"]` lo
        # aplicaba SOLO la Policy Layer de `action_graph.py` (OLD, en DOS
        # sitios: lectura en node_select_and_execute_tools, escritura en
        # node_evaluate_policy) -- este runtime nunca lo porto. Mismo mensaje
        # y status_code que el sistema OLD (node_select_and_execute_tools).
        if user_lacks_admin_permission(metadata.permissions, sintel_ctx.user):
            logger.warning("[policy] IsAdminUser requerido para %s, user=%s no es staff",
                            metadata.name, sintel_ctx.user.get("user_id"))
            return {"error": "Esta accion es solo para administradores.", "status_code": 403}
        # ADK-12, hallazgo real de la auditoria: `ToolMetadata.rate_limit` lo
        # aplicaba SOLO la Policy Layer de `action_graph.py` (OLD) -- este
        # runtime nunca lo porto, y ya sirve clientes reales (AI_SUPPORT_
        # CHAT_ENABLED=True en produccion desde 2026-09-14). Mismo criterio
        # que node_evaluate_policy: se evalua ANTES de ejecutar la funcion
        # real, con el mismo rate_limit.py (Redis, fail-open) que ahora usa
        # tambien `action_graph.py`. Si no hay rate_limit en la metadata,
        # rate_limit_exceeded() devuelve False sin tocar Redis.
        if metadata.rate_limit:
            user_id = sintel_ctx.user.get("user_id")
            if await rate_limit_exceeded(user_id, metadata.name, metadata.rate_limit):
                logger.warning("[policy] rate limit %s para user=%s", metadata.name, user_id)
                return {"error": "Limite de intentos alcanzado para esta accion, "
                                  "intentar mas tarde.", "status_code": 429}
        # Llamada real a la funcion Sintel original -- cero logica de negocio
        # nueva en este adapter. Cualquier parametro real oculto al LLM
        # (ausente de args_schema, ej. `history`) no llega en kwargs -- usa
        # el default real de `real_func`.
        return await real_func(sintel_ctx, **call_kwargs)

    wrapper.__name__ = metadata.name
    wrapper.__doc__ = metadata.description
    wrapper.__signature__ = wrapper_sig

    return FunctionTool(wrapper, require_confirmation=metadata.requires_confirmation)
