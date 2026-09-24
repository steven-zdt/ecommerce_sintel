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

Ademas de este adapter, `deny_after_max_tool_calls_per_turn()` (mas abajo) es un
`before_tool_callback` real de ADK que limita cuantas Tools se pueden invocar
dentro de un mismo turno -- gap real que no tenia equivalente nativo en ADK,
ver auditoria de hardening 2026-09-14.

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
import time
from typing import Any, Callable, Optional

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext as AdkToolContext

from permissions import user_lacks_admin_permission
from rate_limit import rate_limit_exceeded
import idempotency
import input_guard
import result_limits
from tools.arg_validation import validate_args

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


# Auditoria de hardening (2026-09-14, "PROMPT MAESTRO" seccion 34, "Seguridad del
# Agente" -- "Definir max tool calls, max iterations... cuando el runtime lo
# soporte"). Introspeccion real confirmo que `LlmAgent`/`Runner` de Google ADK NO
# exponen un limite nativo de tool calls/iteraciones por turno (a diferencia del
# sistema OLD, `action_graph.py::tool_calls[:4]`) -- solo hooks
# (`before_tool_callback`) donde el runtime que lo usa debe implementar su propio
# contador. A diferencia de OLD (un solo paso, sin loop real de tool-calling),
# ADK SI soporta rondas iterativas reales de tool-calling dentro de un mismo turno
# -- un modelo comprometido/en loop podria en teoria encadenar llamadas
# indefinidamente. `ToolContext.invocation_id` (real, confirmado via
# introspeccion) es unico por turno (por llamada a `runner.run_async()`), no por
# sesion -- clave correcta para un cap por-turno, no acumulativo entre turnos.
# `sintel_root_workflow.py::run_sintel_turn()` limpia la entrada en su bloque
# `finally`, igual que `_EPHEMERAL_TOKENS` de arriba.
MAX_TOOL_CALLS_PER_TURN = 6
_TOOL_CALL_COUNTS: dict[str, int] = {}


def clear_tool_call_count(invocation_id: str) -> None:
    _TOOL_CALL_COUNTS.pop(invocation_id, None)


def deny_after_max_tool_calls_per_turn(*, tool, args, tool_context, **_ignored):
    """`before_tool_callback` real de ADK: devolver un dict (no None) aqui
    salta la ejecucion real de la Tool y usa ese dict como su resultado
    (confirmado via lectura directa de
    `google.adk.flows.llm_flows._tool_caller`, "Step 2: ... funcion es
    respondida sin llegar a ejecutarse"). Devolver `None` deja pasar la
    llamada normalmente -- unico caso donde este callback actua."""
    invocation_id = tool_context.invocation_id
    count = _TOOL_CALL_COUNTS.get(invocation_id, 0) + 1
    _TOOL_CALL_COUNTS[invocation_id] = count
    if count > MAX_TOOL_CALLS_PER_TURN:
        logger.warning(
            "[policy] limite de tool calls por turno alcanzado (%d) en invocation_id=%s, "
            "tool=%s denegada", MAX_TOOL_CALLS_PER_TURN, invocation_id, tool.name,
        )
        return {
            "error": "Este turno ya alcanzo el limite de acciones permitidas. "
                      "Reformula tu pregunta en un mensaje nuevo.",
            "status_code": 429,
        }
    return None


# Auditoria de hardening (2026-09-14, "PROMPT MAESTRO" seccion 43 caso 8 / seccion
# 45 "Fail-safe"). Hallazgo real confirmado empiricamente (no teorico): una Tool
# real que levanta una excepcion (ej. Django cae, timeout de red) NO se atrapa en
# ningun punto de la libreria ADK por defecto -- `_tool_caller.py` la vuelve a
# levantar (`raise tool_error`) y se propaga hasta afuera de `run_sintel_turn()`.
# El catch-all de `main.py::chat()` ya evita un 500 crudo (degrada con gracia,
# nunca expone el traceback al cliente -- confirmado, no es un hueco de
# seguridad), pero mata el TURNO COMPLETO por un fallo de UNA sola Tool, perdiendo
# cualquier otro resultado ya obtenido en el mismo turno -- el sistema OLD
# (action_graph.py::_execute_capability) SI degradaba por-Tool, dejando que el LLM
# siguiera con lo que ya tenia. `on_tool_error_callback` (hook real de ADK,
# confirmado via lectura directa de _tool_error_handler.py) cierra esa brecha:
# devolver un dict aqui evita que la excepcion se vuelva a levantar, el LLM ve un
# resultado de error para ESA Tool nada mas y puede seguir el turno.
def handle_tool_error(*, tool, args, tool_context, error, **_ignored):
    logger.exception(
        "[policy] error real en Tool %s (turno continua degradado, invocation_id=%s): %s",
        tool.name, getattr(tool_context, "invocation_id", "?"), error,
    )
    return {
        "error": "No se pudo completar esta accion en este momento. Intenta de nuevo "
                  "o pide hablar con un agente humano.",
        "status_code": 502,
    }


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


def validate_tool_args_before(*, tool, args, tool_context, **_ignored):
    """HARDENING F4/C2: `before_tool_callback` que valida los argumentos CRUDOS del modelo contra `args_schema`
    (campos desconocidos, requeridos, tipos, UUID, enum, rangos). El ADK descarta en silencio los campos ajenos a la
    firma, por eso esto no puede vivir dentro del wrapper de la Tool.

    AI_TOOL_STRICT_ARGS=false (default): MONITOR -- deja pasar y loguea `security_event=ai_tool_args_invalid mode=monitor`
    (sin valores, solo nombres de campo). true: devuelve un dict de error (400) y la Tool NO se ejecuta."""
    import config as ai_config
    from tools.registry import get_tool

    registered = get_tool(tool.name)
    if registered is None:
        return None
    errors = validate_args(registered.metadata.args_schema or {}, dict(args or {}))
    if not errors:
        return None
    strict = ai_config.AI_TOOL_STRICT_ARGS
    logger.warning("security_event=ai_tool_args_invalid mode=%s tool=%s errors=%s",
                   "strict" if strict else "monitor", tool.name, errors)
    if strict:
        return {"error": "Argumentos invalidos para la accion solicitada.", "status_code": 400,
                "validation_errors": errors}
    return None


def _audit_tool(*, metadata, tool_context, sintel_ctx, authz, status, latency_ms, status_code=None, error_class=None,
                replay=False):
    """HARDENING F4/C5: UN evento de auditoria por ejecucion de Tool, sin argumentos ni secretos (solo identificadores)."""
    session = getattr(tool_context, "session", None)
    logger.info(
        "ai_tool_audit invocation_id=%s session_id=%s user_id=%s agent=%s tool=%s level=%s authz=%s "
        "confirmation=%s status=%s status_code=%s latency_ms=%s error_class=%s replay=%s",
        getattr(tool_context, "invocation_id", None), getattr(session, "id", None),
        sintel_ctx.user.get("user_id"), getattr(tool_context, "agent_name", None), metadata.name, metadata.level,
        authz, "confirmed" if metadata.requires_confirmation else "not_required", status, status_code, latency_ms,
        error_class, replay,
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
        started = time.monotonic()
        if user_lacks_admin_permission(metadata.permissions, sintel_ctx.user):
            logger.warning("[policy] IsAdminUser requerido para %s, user=%s no es staff",
                            metadata.name, sintel_ctx.user.get("user_id"))
            _audit_tool(metadata=metadata, tool_context=tool_context, sintel_ctx=sintel_ctx, authz="denied",
                        status="denied", status_code=403, latency_ms=round((time.monotonic() - started) * 1000))
            return {"error": "Esta accion es solo para administradores.", "status_code": 403}
        # HARDENING F4/C3: idempotencia server-side de escrituras (antes del rate limit: una repeticion identica no
        # debe consumir cupo). Ver idempotency.py.
        import config as ai_config
        idem_key = None
        if metadata.side_effects and metadata.idempotent and ai_config.AI_TOOL_IDEMPOTENCY_ENABLED:
            session = getattr(tool_context, "session", None)
            key = idempotency.make_key(getattr(session, "id", ""), sintel_ctx.user.get("user_id"), metadata.name, call_kwargs)
            existing, first = await idempotency.begin(key)
            if not first:
                if existing == idempotency.UNAVAILABLE:
                    _audit_tool(metadata=metadata, tool_context=tool_context, sintel_ctx=sintel_ctx, authz="allowed",
                                status="idempotency_unavailable", status_code=503,
                                latency_ms=round((time.monotonic() - started) * 1000))
                    return {"error": "No se pudo ejecutar la accion de forma segura en este momento. "
                                     "Un agente humano puede ayudarte.", "status_code": 503}
                if existing == idempotency.PENDING:
                    _audit_tool(metadata=metadata, tool_context=tool_context, sintel_ctx=sintel_ctx, authz="allowed",
                                status="duplicate_in_flight", status_code=409, replay=True,
                                latency_ms=round((time.monotonic() - started) * 1000))
                    return {"error": "Una operacion identica ya esta en curso.", "status_code": 409}
                _audit_tool(metadata=metadata, tool_context=tool_context, sintel_ctx=sintel_ctx, authz="allowed",
                            status="replayed", replay=True, latency_ms=round((time.monotonic() - started) * 1000))
                return {**existing, "idempotent_replay": True}
            idem_key = key
        # ADK-12, hallazgo real de la auditoria: `ToolMetadata.rate_limit` lo aplicaba SOLO la Policy Layer de
        # `action_graph.py` (OLD). Se evalua ANTES de ejecutar la funcion real (rate_limit.py, Redis, fail-open).
        if metadata.rate_limit:
            user_id = sintel_ctx.user.get("user_id")
            if await rate_limit_exceeded(user_id, metadata.name, metadata.rate_limit):
                logger.warning("[policy] rate limit %s para user=%s", metadata.name, user_id)
                if idem_key:
                    await idempotency.abort(idem_key)
                _audit_tool(metadata=metadata, tool_context=tool_context, sintel_ctx=sintel_ctx, authz="allowed",
                            status="rate_limited", status_code=429, latency_ms=round((time.monotonic() - started) * 1000))
                return {"error": "Limite de intentos alcanzado para esta accion, "
                                  "intentar mas tarde.", "status_code": 429}
        # Llamada real a la funcion Sintel original -- cero logica de negocio nueva en este adapter. Cualquier
        # parametro real oculto al LLM (ausente de args_schema, ej. `history`) usa el default real de `real_func`.
        try:
            result = await real_func(sintel_ctx, **call_kwargs)
        except Exception as exc:
            if idem_key:
                await idempotency.abort(idem_key)
            _audit_tool(metadata=metadata, tool_context=tool_context, sintel_ctx=sintel_ctx, authz="allowed",
                        status="exception", error_class=type(exc).__name__,
                        latency_ms=round((time.monotonic() - started) * 1000))
            raise
        # HARDENING F5/C1+C4: la salida de una Tool es contenido NO confiable -> saneo Unicode (sin cambiar la forma) y
        # deteccion en monitor (sin contenido en el log).
        if ai_config.AI_INPUT_GUARD_ENABLED and isinstance(result, (dict, list)):
            result = input_guard.sanitize_json_strings(result)
            input_guard.flag_tool_output(metadata.name, result)
        # HARDENING F12/C4: tope del resultado que vuelve al modelo (contexto de Ollama = 4096 tokens). MONITOR por defecto.
        limited, limit_info = result_limits.limit_result(result, ai_config.AI_TOOL_MAX_RESULT_CHARS)
        if limit_info:
            logger.warning(
                "ai_operation_event=tool_result_truncated enforced=%s tool=%s original_chars=%s final_chars=%s shown=%s total=%s "
                "strings_capped=%s limit=%s", ai_config.AI_TOOL_RESULT_ENFORCE, metadata.name, limit_info["original_chars"],
                limit_info["final_chars"], limit_info["shown"], limit_info["total"], limit_info["strings_capped"],
                ai_config.AI_TOOL_MAX_RESULT_CHARS)
            if ai_config.AI_TOOL_RESULT_ENFORCE:
                result = limited
        failed = isinstance(result, dict) and bool(result.get("error"))
        if idem_key:
            if failed or not isinstance(result, dict):
                await idempotency.abort(idem_key)  # un fallo no bloquea un reintento legitimo
            else:
                await idempotency.finish(idem_key, result)
        _audit_tool(metadata=metadata, tool_context=tool_context, sintel_ctx=sintel_ctx, authz="allowed",
                    status="error" if failed else "ok",
                    status_code=(result.get("status_code") if isinstance(result, dict) else None),
                    latency_ms=round((time.monotonic() - started) * 1000))
        return result

    wrapper.__name__ = metadata.name
    wrapper.__doc__ = metadata.description
    wrapper.__signature__ = wrapper_sig

    return FunctionTool(wrapper, require_confirmation=metadata.requires_confirmation)
