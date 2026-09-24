"""
Root Workflow de SINTEL -- runtime REAL (ADK-11 Cutover, ver
AUDITORIA/ADK_CUTOVER_PLAN.md). Promovido desde `adk_poc/sintel_root_
workflow.py` (ADK-03 a ADK-10) al servicio real `ai_engine_adk/`, desplegado
JUNTO al servicio OLD (`ai_engine/`, ver Opcion A del plan de cutover) --
NO reemplaza produccion todavia, `settings.AI_ENGINE_URL` sigue apuntando a
`sintel_ai` hasta que se autorice el swap de trafico.

## Decision de arquitectura ADK-04 (confirmada por el usuario)

El routing REAL de `ai_engine` es 100% deterministico: `detect_business_
intents()` (regex) -> `AgentRegistry.route()` (dict) -> `AgentRegistry.
apply_escalation()` (regex de seguridad). Delegar esa decision a un LLM
(via `sub_agents`) violaria "ADK ORQUESTA. SINTEL EJECUTA Y CONTROLA" --
`resolve_turn_agent()` reutiliza `routing.py` (extraido de `action_graph.py`
en este mismo cutover, ver AUDITORIA/ADK_CUTOVER_PLAN.md) y `agents.
AgentRegistry`, mismo codigo, no una copia.

## Identidad y sesion (ADK-08)

El JWT NUNCA se siembra en `Session.state`/`state_delta` -- vive en
`sintel_adapter._EPHEMERAL_TOKENS`, un dict de proceso indexado por
`session_id`, mismo rol que `config["configurable"]["token"]` de LangGraph.

## RAG (ADK-06)

Retrieval no es una decision del LLM -- el Root Workflow decide SI hacerlo
(intent == "knowledge", router determinista) e inyecta el resultado via
`LlmAgent.instruction` como callable, sembrado por turno via `state_delta`.

## Contrato HTTP completo y flujo de RESUME (ADK-11, cerrado en este cutover)

Pendiente desde ADK-03/ADK-02 respectivamente, ahora resuelto:
- `response`/`tool_calls`/`tool_results`: construidos por
  `public_response.extract_public_response()` -- UNICO punto de conversion
  de eventos reales de ADK al payload publico (ver ese modulo para la
  correccion arquitectonica del leak de razonamiento de Qwen3.5/LM Studio,
  2026-09-14: `Part.thought` se filtra ANTES de armar `response`).
- `needs_confirmation`/`confirmation`: un turno queda pausado cuando algun
  evento trae `long_running_tool_ids` no vacio (hallazgo real, verificado
  empiricamente contra Ollama real en `adk_poc/test_sintel_hitl_resume.py`
  -- el id relevante para RESUMIR es el de ESE evento sintetico, NO la
  clave de `event.actions.requested_tool_confirmations`, que es la del
  llamado ORIGINAL). El id pendiente se guarda en `_PENDING_CONFIRMATIONS`
  (mismo patron efimero que `_EPHEMERAL_TOKENS`, indexado por session_id) y
  se consume en el turno siguiente si `run_sintel_turn(confirm=...)` trae
  un valor no-None.

## Seleccion de modelo LLM

Lee `LOCAL_MODEL_CHAIN` real (`config.py`, `model_chain.py` -- mismos
modulos reales que usa `llm_factory.py` del sistema OLD, sin arrastrar
langchain-core) y usa la entrada PRIMARIA para construir un `LiteLlm`
(Ollama nativo u openai-compatible/LM Studio). Sin fallback multi-entry
todavia (pendiente, ver AUDITORIA/ADK_CUTOVER_PLAN.md seccion 4). El fix de
`JSON_SCHEMA_FOR_FUNC_DECL=False` (ADK-01) esta verificado SOLO contra
Ollama -- comportamiento contra LM Studio real sin verificar todavia,
riesgo heredado y documentado, no resuelto silenciosamente aqui.
"""
import asyncio
import logging
import re
import time
import uuid

from google.adk.features._feature_registry import FeatureName, override_feature_enabled

override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)

from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.agents.run_config import RunConfig
import input_guard
import observability_logging
import output_guard
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.tool_confirmation import ToolConfirmation

from sintel_adapter import (
    SINTEL_USER_STATE_KEY,
    adapt_sintel_tool,
    clear_ephemeral_token,
    clear_tool_call_count,
    deny_after_max_tool_calls_per_turn,
    validate_tool_args_before,
    handle_tool_error,
    set_ephemeral_token,
)
from sintel_rag_adapter import (
    EMPTY_KNOWLEDGE_DIAGNOSTICS,
    SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY,
    _LOW_CONFIDENCE_MARKER,
    _NO_KNOWLEDGE_MARKER,
    fetch_and_assemble_knowledge,
)
from public_response import REQUEST_CONFIRMATION_FUNCTION_CALL_NAME, extract_public_response
from grounding import UNGROUNDED_FALLBACK_RESPONSE, UNSUPPORTED, check_grounding
from customer_memory_adapter import (
    SINTEL_CUSTOMER_MEMORY_STATE_KEY,
    build_memory_context,
    extract_and_store_memory,
    fetch_customer_memories,
)

logger = logging.getLogger("sintel_root_workflow")

APP_NAME = "sintel_ai_adk"


# Auditoria de hardening (2026-09-14, "PROMPT MAESTRO"): el sistema OLD tenia un
# timeout propio por llamada al LLM (`llm_factory.py::LLM_TIMEOUT_SECONDS = 90`,
# real desde G2/AUDITORIA/16, 2026-08-01 -- "ninguna llamada al LLM tenia
# timeout propio, el unico corte end-to-end era AI_CHAT_TIMEOUT_SECONDS=300 del
# lado Django"). Se perdio al retirar `llm_factory.py` en ADK-12 (2026-09-14) --
# `ai_engine_adk` quedo sin ningun timeout propio para la llamada al LLM, solo
# el limite externo de 300s de `support/services/ai_bridge.py`. Restaurado aqui
# con el mismo valor -- `LiteLlm(**kwargs)` reenvia `timeout` tal cual a
# `litellm.acompletion()` (confirmado via introspeccion real de
# `LiteLlm.__init__`, que guarda `**kwargs` como `_additional_args`).
_LLM_TIMEOUT_SECONDS = 90


def _resolve_primary_llm_params() -> dict:
    """Lee el LOCAL_MODEL_CHAIN real (mismo formato/modulo que llm_factory.py
    del sistema OLD) y devuelve los parametros crudos (model/api_base/
    api_key) de la entrada PRIMARIA -- extraido de _build_litellm_model()
    (Mision RAG Enterprise, FASE 7, 2026-09-16) para que grounding.py pueda
    hacer una llamada litellm directa con el MISMO modelo/proveedor real del
    turno (Regla 3 de la mision: no cambiar de modelo sin evidencia), sin
    duplicar este parseo ni crear un segundo LlmAgent/Runner completo para
    una pregunta de si/no."""
    from config import LOCAL_MODEL_CHAIN
    from model_chain import parse_local_model_chain

    entries = parse_local_model_chain(LOCAL_MODEL_CHAIN)
    if not entries:
        raise RuntimeError(
            "LOCAL_MODEL_CHAIN vacio o invalido -- ningun proveedor LLM configurado "
            "para ai_engine_adk."
        )
    entry = entries[0]
    kind = entry["kind"]
    if kind == "ollama-nativo":
        return {"model": f"ollama_chat/{entry['model']}", "api_base": entry["base_url"]}
    if kind == "openai-compatible":
        return {"model": f"openai/{entry['model']}", "api_base": entry["base_url"], "api_key": "not-needed"}
    if kind == "anthropic":
        from decouple import config as env
        from config import ANTHROPIC_API_KEY

        api_key = env(entry["api_key_env"], default=ANTHROPIC_API_KEY) if entry.get("api_key_env") else ANTHROPIC_API_KEY
        return {"model": f"anthropic/{entry['model']}", "api_key": api_key}
    raise RuntimeError(f"kind desconocido en LOCAL_MODEL_CHAIN: {kind!r}")


def _build_litellm_model():
    """Modelo real (ADK) para los agentes. HARDENING F3/C2 (2026-09-24): con AI_BREAKER_ENABLED (default)
    devuelve `FallbackLiteLlm` (model_runtime.py): recorre LOCAL_MODEL_CHAIN en orden con circuit breaker por
    proveedor y un solo fallback por llamada. Con el breaker apagado conserva el comportamiento anterior:
    LiteLlm de la entrada PRIMARIA (ver _resolve_primary_llm_params())."""
    import config as ai_config

    if ai_config.AI_BREAKER_ENABLED:
        from model_runtime import build_fallback_model

        return build_fallback_model(_LLM_TIMEOUT_SECONDS)
    return LiteLlm(timeout=_LLM_TIMEOUT_SECONDS, **_resolve_primary_llm_params())


class IdentityResolutionError(Exception):
    """El token no se pudo validar o Django rechazo la identidad -- fallar
    cerrado (nunca degradar a un turno anonimo)."""


async def resolve_identity(token: str) -> dict:
    """Reutiliza el boundary real de auth.py -- no reimplementa validacion
    de JWT ni resolucion de perfil."""
    from auth import decode_django_jwt, fetch_user_context
    from fastapi import HTTPException

    try:
        payload = decode_django_jwt(token)
        context = await fetch_user_context(token)
    except HTTPException as exc:
        raise IdentityResolutionError(f"{exc.status_code}: {exc.detail}") from exc
    context.setdefault("user_id", payload.get("user_id"))
    return context


def build_session_id(user_id, conversation_id: str) -> str:
    """Mismo patron que `action_graph.run_action_chat`'s `thread_id`."""
    return f"{user_id}:{conversation_id}"


# PLAN_SINTEL_ADMIN_AI_ADK_PANEL_LOOP.md, Fase 2 (Admin AI Gateway): "enviar
# unicamente capacidades permitidas". Bug real encontrado en vivo
# (2026-09-23, primera prueba real de /panel/asistente): un admin escribio
# una frase que no matcheaba el regex de `catalog_admin` -- el router cayo
# a `support` (intent generico de CLIENTE) -> SupportAgent, que abrio un
# ticket de soporte real tratando al administrador como comprador. Causa
# raiz: `resolve_turn_agent` decidia el agente solo por el texto del
# mensaje, sin saber si la llamada viene de /panel/asistente (admin) o del
# widget de soporte (cliente) -- el mismo `/chat` sirve a ambos canales.
# Lista explicita, no un campo nuevo en AgentProfile: solo existe UN agente
# admin hoy (Fase 3 del plan: "evitar explosion de subagentes... comenzar
# con AdminAgent"). Si se agregan mas agentes admin (Fase 10/11), agregarlos
# aqui.
_ADMIN_AGENT_NAMES = {"CatalogAgent"}
# HARDENING F10 (hallazgo A-014): MarketingAgent atiende TAMBIEN a clientes (personal_recommendation), asi que no puede ir en la lista
# de arriba; para source=admin solo se acepta cuando el intent es marketing_admin (de lo contrario todo mensaje admin de marketing se
# reencaminaba a CatalogAgent).
_ADMIN_INTENT_AGENTS = {"marketing_admin": "MarketingAgent"}

# HARDENING F10 (hallazgo A-012): "garantia de las camaras" caia en renting_search por el sustantivo. Una PREGUNTA de conocimiento
# (garantia/politica/horario...) cuyo unico otro intent viene de sustantivos de producto NO es una accion de alquiler: gana knowledge.
# Si hay un verbo de accion (alquilar/rentar/reservar/disponibilidad) o cualquier otro intent, no se toca el routing.
_RENTING_ACTION_RE = re.compile(r"\b(alquil\w*|rent\w*|reserv\w*|disponib\w*)", re.I)
_NOUN_ONLY_INTENTS = {"renting_search", "knowledge"}


def should_extract_memory(*, is_resume: bool, final_text, source: str, injection_flags: dict) -> bool:
    """HARDENING F7/C6 (2026-09-24): la extraccion de memoria SOLO corre para un turno nuevo de cliente con respuesta, y NUNCA para el
    asistente de administracion (`source="admin"`, la memoria es del CLIENTE) ni para un mensaje que F5 marco como inyeccion (fail-closed:
    un intento de manipulacion no debe convertirse en un recuerdo). Solo lee el MENSAJE del usuario, jamas RAG ni salidas de Tools."""
    return bool(not is_resume and final_text and source != "admin" and not injection_flags.get("user"))


def _turn_max_llm_calls() -> int:
    import config as ai_config

    return ai_config.AI_TURN_MAX_LLM_CALLS


def _max_output_tokens_for(profile_name: str) -> int:
    import config as ai_config

    return ai_config.AI_ADMIN_MAX_OUTPUT_TOKENS if profile_name in _ADMIN_AGENT_NAMES \
        else ai_config.AI_SUPPORT_MAX_OUTPUT_TOKENS


def resolve_turn_agent(message: str, *, source: str = "customer") -> tuple[str, str, str | None]:
    """Router REAL de Sintel -- reutiliza `routing.py` (extraido de
    `action_graph.py`, mismo codigo) y `agents.AgentRegistry.route/
    apply_escalation` tal cual. Devuelve (intent, agent_name, handoff).

    `source="admin"` (ver ChatRequest.source, main.py): restringe el
    resultado a un agente admin SIEMPRE, sin importar que intent haya
    detectado el regex -- nunca cae a un agente de cara al cliente. No
    toca `apply_escalation` (regla explicita y deliberada de
    `catalog_agent.yaml`, ej. "eliminar" -> SupportAgent para revision
    humana -- decision de diseño previa, distinta del bug de arriba)."""
    from routing import detect_business_intents, INTENT_CAPABILITIES
    from agents import AgentRegistry

    intents = detect_business_intents(message)
    data_intents = [i for i in intents if i in INTENT_CAPABILITIES]
    intent = data_intents[0] if data_intents else ("knowledge" if "knowledge" in intents else "unknown")
    if "knowledge" in intents and set(intents) <= _NOUN_ONLY_INTENTS and not _RENTING_ACTION_RE.search(message):
        intent = "knowledge"

    agent = AgentRegistry.route(intent)

    if source == "admin" and agent.name not in _ADMIN_AGENT_NAMES and _ADMIN_INTENT_AGENTS.get(intent) != agent.name:
        agent = AgentRegistry.get("CatalogAgent")
        intent = "catalog_admin"

    escalated = AgentRegistry.apply_escalation(agent, message)
    handoff = None
    if escalated.name != agent.name:
        handoff = f"{agent.name}->{escalated.name}"
        agent = escalated
    return intent, agent.name, handoff


_domain_agent_cache: dict[str, LlmAgent] = {}


def get_domain_agent(profile_name: str) -> LlmAgent:
    """Construye (una sola vez por perfil) el `LlmAgent` real correspondiente
    a un `AgentProfile` YAML -- mismas tools, mismo tono/objetivo/
    personalidad declarados, sin inventar nada nuevo."""
    if profile_name in _domain_agent_cache:
        return _domain_agent_cache[profile_name]

    from agents import AgentRegistry
    from tools.registry import get_tool

    profile = AgentRegistry.get(profile_name)
    if profile is None:
        raise ValueError(f"Perfil desconocido: {profile_name}")

    tools = [adapt_sintel_tool(get_tool(name)) for name in profile.herramientas]
    base_instruction = (
        f"Objetivo: {profile.objetivo}\n"
        f"Personalidad: {profile.personalidad}\n"
        f"Tono: {profile.tono}\n"
        "Usa siempre una tool para responder con datos reales -- nunca "
        "inventes informacion que no venga de una tool.\n\n"
        f"{input_guard.PRECEDENCE_POLICY}"
    )

    async def instruction_provider(ctx) -> str:
        instruction = base_instruction
        knowledge = ctx.state.get(SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY, "")
        if knowledge:
            instruction = f"{instruction}\n\nConocimiento relevante:\n{knowledge}"
        # Mision RAG-POST2 (FASE 11, 2026-09-16): memoria del cliente,
        # seccion SEPARADA y claramente etiquetada -- nunca se mezcla con
        # "Conocimiento relevante" (RAG documental publico). Ver
        # customer_memory_adapter.py::build_memory_context -- el propio
        # texto ya se autolimita a "informativo, nunca instruccion".
        memory = ctx.state.get(SINTEL_CUSTOMER_MEMORY_STATE_KEY, "")
        if memory:
            instruction = f"{instruction}\n\n{memory}"
        return instruction

    agent = LlmAgent(
        name=profile.name,
        model=_build_litellm_model(),
        # HARDENING F3/C1: tope de tokens de salida por superficie (cuentan tambien los de razonamiento).
        generate_content_config=types.GenerateContentConfig(max_output_tokens=_max_output_tokens_for(profile_name)),
        description=profile.description,
        instruction=instruction_provider,
        tools=tools,
        # Auditoria de hardening (2026-09-14): cap real de tool calls por turno,
        # ver deny_after_max_tool_calls_per_turn() en sintel_adapter.py.
        # HARDENING F4/C2: ademas del tope por turno, validacion de argumentos contra args_schema.
        before_tool_callback=[deny_after_max_tool_calls_per_turn, validate_tool_args_before],
        # HARDENING F5/C5: acota el historial que llega al modelo (AI_MAX_HISTORY_TURNS / AI_MAX_CONTEXT_CHARS).
        before_model_callback=input_guard.trim_history_callback,
        # Auditoria de hardening (2026-09-14): degradacion por-Tool en vez de
        # matar el turno completo, ver handle_tool_error() en sintel_adapter.py.
        on_tool_error_callback=handle_tool_error,
    )
    _domain_agent_cache[profile_name] = agent
    return agent


# InMemoryRunner crea su propio InMemorySessionService AISLADO por instancia
# -- un Runner explicito comparte un unico session_service a nivel de
# modulo, sea cual sea el backend real.
#
# Mision RAG-POST2 (FASE 7, 2026-09-16): backend persistente real, resuelto.
# ADK_SESSION_BACKEND="database" (config.py) construye un DatabaseSessionService
# real (SQLAlchemy async + asyncpg) contra una base de datos PROPIA de ADK
# (`sintel_adk_sessions`, tablas gestionadas por el propio google-adk via
# create_async_engine + auto-creacion de tablas -- nunca las tablas de
# Django, nunca via el ORM de Django, ver Regla "no tocar ORM directo desde
# ai_engine_adk" -- esto no es el ORM de Django, es un store nativo de ADK
# sobre un Postgres fisicamente separado). Default real ("memory") preserva
# el comportamiento anterior a esta fase para cualquier entorno que no
# configure las 2 variables explicitamente (ver config.py). El JWT sigue sin
# tocar esto (ADK-08, _EPHEMERAL_TOKENS de proceso, ver arriba) -- cambiar
# de backend de sesion NO cambia donde vive el token, a proposito.
def _build_session_service() -> BaseSessionService:
    from config import ADK_SESSION_BACKEND, ADK_SESSION_DB_URL

    if ADK_SESSION_BACKEND != "database":
        return InMemorySessionService()

    if not ADK_SESSION_DB_URL:
        raise RuntimeError(
            "ADK_SESSION_BACKEND=database pero ADK_SESSION_DB_URL esta vacio -- "
            "configuralo (postgresql+asyncpg://...) o vuelve ADK_SESSION_BACKEND a 'memory'."
        )
    from google.adk.sessions.database_session_service import DatabaseSessionService

    logger.info("[session] backend persistente activo (DatabaseSessionService)")
    return DatabaseSessionService(db_url=ADK_SESSION_DB_URL)


_session_service = _build_session_service()

# Registros efimeros de proceso, indexados por session_id -- mismo patron
# que `sintel_adapter._EPHEMERAL_TOKENS` (ADK-08): nunca pasan por
# `Session.state`, no sobreviven a un reinicio del proceso (aceptable hoy,
# el sistema OLD tampoco garantiza continuidad de una confirmacion
# pendiente a traves de un reinicio del contenedor).
_PENDING_CONFIRMATIONS: dict[str, str] = {}
_LAST_TURN_AGENT: dict[str, tuple[str, str, str | None]] = {}

# Mision RAG-POST2 (FASE 10, 2026-09-16): referencia fuerte a las tareas de
# extraccion de memoria en background -- asyncio.create_task() sin esto
# arriesga que el garbage collector recolecte la tarea a mitad de
# ejecucion (advertencia real y documentada de la stdlib de asyncio, no
# teorica). Se autolimpia via add_done_callback.
_BACKGROUND_TASKS: set = set()


async def run_sintel_turn(
    *, message: str, token: str, conversation_id: str | None = None, confirm: bool | None = None, channel: str = "web",
    source: str = "customer",
) -> dict:
    """Punto de entrada del Root Workflow. Checklist completo: identidad ->
    contexto -> seleccion de agente (router REAL, no LLM) -> routing ->
    sesion -> eventos -> tool_calls/needs_confirmation/confirmation.

    `confirm`: si no es None Y hay una confirmacion pendiente real para esta
    sesion, este turno RESUME esa pausa (mismo mecanismo que ChatRequest.
    confirm del sistema OLD) en vez de procesar `message` como una peticion
    nueva.
    """
    # Mision RAG Enterprise (2026-09-16, FASE 11 -- observabilidad): duracion
    # real del turno completo (identidad -> retrieval -> ADK -> grounding).
    turn_started_at = time.monotonic()
    # Mision RAG-POST2 (FASE 5, 2026-09-16): id real de correlacion por
    # turno -- ADK no expone uno propio estable entre eventos de un mismo
    # turno, se genera aqui, antes de cualquier rama de retorno.
    # HARDENING F9: el id lo fija main.py desde X-Request-ID (correlacion con nginx/Django); sin cabecera se genera aqui.
    request_id = observability_logging.current_request_id() or f"req-{uuid.uuid4()}"

    context = await resolve_identity(token)
    user_id = context["user_id"]
    conversation_id = conversation_id or "adk-root-default"
    session_id = build_session_id(user_id, conversation_id)
    # HARDENING F3/C2: trazabilidad del proveedor/modelo/fallback de ESTE turno (sin prompts ni respuestas).
    from model_runtime import begin_turn_trace, get_turn_usage

    model_trace = begin_turn_trace()

    # HARDENING F5/C1+C4: saneo Unicode del mensaje y deteccion en MONITOR (nunca bloquea).
    import config as ai_config

    injection_flags: dict[str, list[str]] = {}
    if ai_config.AI_INPUT_GUARD_ENABLED:
        message = input_guard.sanitize_text(message)
        user_flags = input_guard.flag_injection("user", message)
        if user_flags:
            injection_flags["user"] = user_flags

    # Cost Control real (cost_control.py, reusado tal cual -- mismo Redis,
    # mismo limite, mismo comportamiento que el sistema OLD; ver
    # AUDITORIA/ADK_CUTOVER_PLAN.md seccion 4, "Cost control real").
    from cost_control import DAILY_TURN_LIMIT_PER_USER, check_and_increment_daily_turns

    if not await check_and_increment_daily_turns(user_id):
        return {
            "conversation_id": conversation_id, "session_id": session_id,
            "intent": "unknown", "agent": None, "handoff": None,
            "response": (
                "Has alcanzado el limite de mensajes por hoy con nuestro asistente. "
                "Un agente humano puede seguir ayudandote -- escribenos y te atendemos."
            ),
            "tool_calls": [], "tool_results": [], "needs_confirmation": False,
            "confirmation": None, "events": [],
            "metrics": {
                "request_id": request_id,
                "rate_limited": True,
                "duration_ms": round((time.monotonic() - turn_started_at) * 1000),
            },
        }

    pending_fc_id = _PENDING_CONFIRMATIONS.get(session_id)
    is_resume = confirm is not None and pending_fc_id is not None

    if is_resume:
        intent, agent_name, handoff = _LAST_TURN_AGENT.get(session_id, ("unknown", None, None))
        knowledge_context = ""
        knowledge_diagnostics = dict(EMPTY_KNOWLEDGE_DIAGNOSTICS)
        memory_context = ""
        confirmation_payload = ToolConfirmation(confirmed=bool(confirm))
        adk_message = types.Content(
            role="user",
            parts=[types.Part(function_response=types.FunctionResponse(
                id=pending_fc_id, name=REQUEST_CONFIRMATION_FUNCTION_CALL_NAME,
                response=confirmation_payload.model_dump(),
            ))],
        )
        _PENDING_CONFIRMATIONS.pop(session_id, None)
    else:
        intent, agent_name, handoff = resolve_turn_agent(message, source=source)
        if intent == "knowledge":
            knowledge_context, knowledge_diagnostics = await fetch_and_assemble_knowledge(message)
        else:
            knowledge_context = ""
            knowledge_diagnostics = dict(EMPTY_KNOWLEDGE_DIAGNOSTICS)
        # Mision RAG-POST2 (FASE 11, 2026-09-16): memoria del cliente, para
        # TODO intent (una preferencia puede salir en cualquier tipo de
        # mensaje, a diferencia del conocimiento documental que solo aplica
        # a intent=="knowledge"). Nunca lanza, [] ante cualquier fallo (ver
        # customer_memory_adapter.py).
        memories = await fetch_customer_memories(token)
        memory_context = build_memory_context(memories)
        adk_message = types.Content(role="user", parts=[types.Part(text=message)])

    domain_agent = get_domain_agent(agent_name)
    runner = Runner(app_name=APP_NAME, agent=domain_agent, session_service=_session_service)

    existing = await _session_service.get_session(
        app_name=APP_NAME, user_id=str(user_id), session_id=session_id,
    )
    if existing is None:
        # ADK-08: el token NUNCA se siembra aqui -- `context` (perfil ya
        # resuelto por Django, no sensible) si es seguro de persistir.
        await _session_service.create_session(
            app_name=APP_NAME, user_id=str(user_id), session_id=session_id,
            state={SINTEL_USER_STATE_KEY: context},
        )

    # HARDENING F5/C2+C4: RAG y memoria son datos NO confiables -> cerca con nonce por turno (el grounding sigue
    # usando `knowledge_context` sin cerca). Los marcadores fijos de la aplicacion no se cercan.
    protected_knowledge, protected_memory = knowledge_context, memory_context
    if ai_config.AI_INPUT_GUARD_ENABLED:
        fence_nonce = input_guard.new_nonce()
        if knowledge_context and knowledge_context not in (_NO_KNOWLEDGE_MARKER, _LOW_CONFIDENCE_MARKER):
            rag_flags = input_guard.flag_injection("rag", knowledge_context)
            if rag_flags:
                injection_flags["rag"] = rag_flags
        if memory_context:
            mem_flags = input_guard.flag_injection("memory", memory_context)
            if mem_flags:
                injection_flags["memory"] = mem_flags
        protected_knowledge = input_guard.protect_block(
            "RAG", knowledge_context, fence_nonce, skip=(_NO_KNOWLEDGE_MARKER, _LOW_CONFIDENCE_MARKER))
        protected_memory = input_guard.protect_block("MEMORIA", memory_context, fence_nonce)

    events = []
    set_ephemeral_token(session_id, token)
    agent_started_at = time.monotonic()
    try:
        async for event in runner.run_async(
            user_id=str(user_id), session_id=session_id, new_message=adk_message,
            # HARDENING F3/C1: tope de llamadas al LLM por turno (RunConfig.max_llm_calls).
            run_config=RunConfig(max_llm_calls=_turn_max_llm_calls()),
            state_delta={
                SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY: protected_knowledge,
                SINTEL_CUSTOMER_MEMORY_STATE_KEY: protected_memory,
            },
        ):
            events.append(event)
    finally:
        agent_latency_ms = round((time.monotonic() - agent_started_at) * 1000)
        clear_ephemeral_token(session_id)
        # Auditoria de hardening (2026-09-14): limpia el contador de
        # deny_after_max_tool_calls_per_turn() -- invocation_id es unico por
        # turno, sin este cleanup el dict de proceso crece sin limite.
        for event in events:
            if event.invocation_id:
                clear_tool_call_count(event.invocation_id)
                break

    _LAST_TURN_AGENT[session_id] = (intent, agent_name, handoff)

    long_running_events = [e for e in events if e.long_running_tool_ids]
    needs_confirmation = bool(long_running_events)
    confirmation: dict | None = None
    if needs_confirmation:
        new_fc_id = next(iter(long_running_events[-1].long_running_tool_ids))
        _PENDING_CONFIRMATIONS[session_id] = new_fc_id
        confirmation_events = [e for e in events if e.actions and e.actions.requested_tool_confirmations]
        hint = None
        if confirmation_events:
            tc = next(iter(confirmation_events[-1].actions.requested_tool_confirmations.values()))
            hint = tc.hint
        confirmation = {"hint": hint}

    # UNICO punto de conversion Event -> payload publico (ver
    # public_response.py) -- filtra Part.thought (razonamiento interno de
    # Qwen3.5/LM Studio, u otro proveedor) ANTES de construir `response`.
    # `internal_reasoning` es solo para logging interno, nunca se devuelve.
    final_text, _internal_reasoning, tool_calls, tool_results = extract_public_response(
        events, conversation_id=conversation_id,
    )

    # Mision RAG Enterprise (2026-09-16, FASE 7): grounding/claim validation
    # POST-generacion. Distinto de retrieval confidence/answerability
    # (sintel_rag_adapter.py, FASE 6, que decide ANTES de generar) -- esto
    # verifica que la respuesta YA generada realmente use la evidencia
    # recuperada, no solo que hubo evidencia disponible. Acotado a turnos
    # de intent "knowledge" con evidencia REAL (nunca sobre los marcadores
    # de "sin conocimiento"/"baja confianza" -- ahi no hay nada que validar).
    # HARDENING F8: guardia de SALIDA (secretos, infraestructura/prompt, enlaces, largo) sobre lo que ve el cliente.
    output_flags: list[str] = []
    if ai_config.AI_OUTPUT_GUARD_ENABLED and final_text:
        final_text, output_flags = output_guard.guard_public_response(
            final_text, surface="admin" if source == "admin" else "customer")

    grounding_verdict: str | None = None
    has_real_knowledge_evidence = bool(
        intent == "knowledge"
        and knowledge_context
        and knowledge_context not in (_NO_KNOWLEDGE_MARKER, _LOW_CONFIDENCE_MARKER)
    )
    grounding_latency_ms: int | None = None
    if has_real_knowledge_evidence and final_text:
        grounding_started_at = time.monotonic()
        grounding_verdict = await check_grounding(
            response=final_text, evidence=knowledge_context, **_resolve_primary_llm_params(),
        )
        grounding_latency_ms = round((time.monotonic() - grounding_started_at) * 1000)
        if grounding_verdict == UNSUPPORTED:
            logger.warning(
                "[grounding] respuesta NO sustentada por la evidencia recuperada, "
                "reemplazada por fallback seguro conversation_id=%s", conversation_id,
            )
            final_text = UNGROUNDED_FALLBACK_RESPONSE

    # Mision RAG-POST2 (FASE 10, 2026-09-16): extraccion de memoria -- en
    # BACKGROUND (asyncio.create_task, nunca await directo). Medido en vivo
    # (ver docstring de extract_and_store_memory): esta llamada real toma
    # 30-40s con el modelo local actual -- bloquear CADA turno con eso
    # seria una degradacion injustificada (FASE 16 de la mision). El
    # proceso de ai_engine_adk es un servidor ASGI de larga duracion
    # (uvicorn) -- la tarea sigue corriendo despues de que este turno
    # responda al cliente, mismo patron real que ya usa
    # support/consumers.py::receive() para _ai_reply(). No corre en turnos
    # de resume (confirmacion de una escritura pendiente, nada nuevo que
    # extraer). _BACKGROUND_TASKS mantiene una referencia fuerte -- sin
    # esto, asyncio puede recolectar la tarea a mitad de ejecucion (riesgo
    # real y documentado de asyncio.create_task, no teorico).
    memory_extraction_scheduled = False
    if should_extract_memory(is_resume=is_resume, final_text=final_text, source=source, injection_flags=injection_flags):
        task = asyncio.create_task(extract_and_store_memory(
            message=message, token=token, conversation_id=conversation_id, channel=channel,
            **_resolve_primary_llm_params(),
        ))
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)
        memory_extraction_scheduled = True

    # Mision RAG Enterprise (2026-09-16, FASE 11 -- observabilidad). Antes de
    # esto, ChatResponse.metrics quedaba hardcodeado en None (main.py,
    # "TurnMetrics real: pendiente") -- cerrado aqui SOLO para las senales
    # de RAG que esta mision introdujo (retrieval/confidence/grounding);
    # token/costo del LLM siguen sin medirse (gap preexistente, documentado
    # aparte, ADK no expone usage_metadata por Event de forma directa --
    # no se inventa un numero, se omite el campo en vez de fingir "0").
    # knowledge_state: cual de los 3 caminos reales de sintel_rag_adapter.py
    # se tomo -- diagnostico honesto de por que el cliente vio (o no) una
    # respuesta con evidencia, sin exponer el contenido del conocimiento.
    if intent != "knowledge":
        knowledge_state = None
    elif not knowledge_context or knowledge_context == _NO_KNOWLEDGE_MARKER:
        knowledge_state = "no_knowledge"
    elif knowledge_context == _LOW_CONFIDENCE_MARKER:
        knowledge_state = "low_confidence"
    else:
        knowledge_state = "answered"

    # Mision RAG-POST2 (FASE 5, 2026-09-16): observabilidad extendida --
    # request_id (correlacion real por turno, generado aqui porque ADK no
    # expone uno propio de forma estable entre eventos), metadata_filters/
    # retrieval_candidates/selected_sources/best_similarity (de
    # fetch_and_assemble_knowledge), desglose de latencia por segmento
    # (antes solo existia duration_ms total) y escalation (True si el turno
    # abrio un ticket de soporte -- mismo criterio real que
    # support/services/ai_bridge.py::ai_response_opened_ticket, replicado
    # aqui porque ai_engine_adk no puede importar codigo de Django).
    escalation = any(
        isinstance(r, dict) and r.get("capability") == "abrir_ticket_soporte"
        and isinstance(r.get("result"), dict) and not r["result"].get("error")
        for r in tool_results
    )

    # HARDENING F9/C3: tokens reales del turno (usage_metadata). llm_tokens_in/out son las claves que ya lee
    # ChatAnalyticsSelector; tokens_per_s = generados / tiempo del agente. TTFT no existe (sin streaming).
    usage = get_turn_usage()
    metrics = {
        "llm_calls": usage["llm_calls"],
        "llm_tokens_in": usage["prompt_tokens"],
        "llm_tokens_out": usage["completion_tokens"],
        "tokens_per_s": observability_logging.tokens_per_second(usage["completion_tokens"], agent_latency_ms),
        "request_id": request_id,
        "agent": agent_name,
        "intent": intent,
        "handoff": handoff,
        "escalation": escalation,
        "tool_calls": len(tool_calls),
        "needs_confirmation": needs_confirmation,
        "retrieval_used": has_real_knowledge_evidence,
        "knowledge_state": knowledge_state,
        "metadata_filters": knowledge_diagnostics.get("metadata_filters"),
        "retrieval_candidates": knowledge_diagnostics.get("retrieval_candidates"),
        "selected_sources": knowledge_diagnostics.get("selected_sources"),
        "best_similarity": knowledge_diagnostics.get("best_similarity"),
        "grounding_result": grounding_verdict,
        "retrieval_latency_ms": knowledge_diagnostics.get("retrieval_latency_ms"),
        "agent_latency_ms": agent_latency_ms,
        "grounding_latency_ms": grounding_latency_ms,
        # Mision RAG-POST2 (FASE 10-11, 2026-09-16): memory_used = habia
        # memoria previa inyectada en la instruccion de este turno.
        # memory_extraction_scheduled = se lanzo la tarea de extraccion en
        # background para ESTE turno -- NUNCA "se extrajo algo": la
        # extraccion real corre despues de que el turno ya respondio (ver
        # docstring arriba), su resultado no puede reportarse de forma
        # sincrona sin reintroducir la latencia que este diseno evita.
        # Observable via logs (customer_memory_adapter logger), no via
        # metrics de ESTE turno.
        "memory_used": bool(memory_context),
        "memory_extraction_scheduled": memory_extraction_scheduled,
        "duration_ms": round((time.monotonic() - turn_started_at) * 1000),
        "model_trace": dict(model_trace),
        "injection_flags": injection_flags,
        "output_flags": output_flags,
    }

    return {
        "conversation_id": conversation_id,
        "session_id": session_id,
        "intent": intent,
        "agent": agent_name,
        "handoff": handoff,
        "response": final_text,
        "tool_calls": tool_calls,
        "tool_results": tool_results,
        "needs_confirmation": needs_confirmation,
        "confirmation": confirmation,
        "events": events,
        "metrics": metrics,
    }
