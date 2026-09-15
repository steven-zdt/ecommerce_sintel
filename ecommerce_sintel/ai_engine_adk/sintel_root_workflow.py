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
from google.adk.features._feature_registry import FeatureName, override_feature_enabled

override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)

from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.tools.tool_confirmation import ToolConfirmation

from sintel_adapter import (
    SINTEL_USER_STATE_KEY,
    adapt_sintel_tool,
    clear_ephemeral_token,
    set_ephemeral_token,
)
from sintel_rag_adapter import SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY, build_knowledge_context
from public_response import REQUEST_CONFIRMATION_FUNCTION_CALL_NAME, extract_public_response

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


def _build_litellm_model():
    """Lee el LOCAL_MODEL_CHAIN real (mismo formato/modulo que llm_factory.py
    del sistema OLD) y construye el LiteLlm de la entrada PRIMARIA."""
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
        return LiteLlm(model=f"ollama_chat/{entry['model']}", api_base=entry["base_url"],
                        timeout=_LLM_TIMEOUT_SECONDS)
    if kind == "openai-compatible":
        return LiteLlm(model=f"openai/{entry['model']}", api_base=entry["base_url"], api_key="not-needed",
                        timeout=_LLM_TIMEOUT_SECONDS)
    if kind == "anthropic":
        from decouple import config as env
        from config import ANTHROPIC_API_KEY

        api_key = env(entry["api_key_env"], default=ANTHROPIC_API_KEY) if entry.get("api_key_env") else ANTHROPIC_API_KEY
        return LiteLlm(model=f"anthropic/{entry['model']}", api_key=api_key, timeout=_LLM_TIMEOUT_SECONDS)
    raise RuntimeError(f"kind desconocido en LOCAL_MODEL_CHAIN: {kind!r}")


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


def resolve_turn_agent(message: str) -> tuple[str, str, str | None]:
    """Router REAL de Sintel -- reutiliza `routing.py` (extraido de
    `action_graph.py`, mismo codigo) y `agents.AgentRegistry.route/
    apply_escalation` tal cual. Devuelve (intent, agent_name, handoff)."""
    from routing import detect_business_intents, INTENT_CAPABILITIES
    from agents import AgentRegistry

    intents = detect_business_intents(message)
    data_intents = [i for i in intents if i in INTENT_CAPABILITIES]
    intent = data_intents[0] if data_intents else ("knowledge" if "knowledge" in intents else "unknown")

    agent = AgentRegistry.route(intent)
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
        "inventes informacion que no venga de una tool."
    )

    async def instruction_provider(ctx) -> str:
        knowledge = ctx.state.get(SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY, "")
        if knowledge:
            return f"{base_instruction}\n\nConocimiento relevante:\n{knowledge}"
        return base_instruction

    agent = LlmAgent(
        name=profile.name,
        model=_build_litellm_model(),
        description=profile.description,
        instruction=instruction_provider,
        tools=tools,
    )
    _domain_agent_cache[profile_name] = agent
    return agent


# InMemoryRunner crea su propio InMemorySessionService AISLADO por instancia
# -- un Runner explicito comparte un unico session_service a nivel de
# modulo. Backend persistente real: pendiente, ver
# AUDITORIA/ADK_CUTOVER_PLAN.md seccion 4.
_session_service = InMemorySessionService()

# Registros efimeros de proceso, indexados por session_id -- mismo patron
# que `sintel_adapter._EPHEMERAL_TOKENS` (ADK-08): nunca pasan por
# `Session.state`, no sobreviven a un reinicio del proceso (aceptable hoy,
# el sistema OLD tampoco garantiza continuidad de una confirmacion
# pendiente a traves de un reinicio del contenedor).
_PENDING_CONFIRMATIONS: dict[str, str] = {}
_LAST_TURN_AGENT: dict[str, tuple[str, str, str | None]] = {}


async def run_sintel_turn(
    *, message: str, token: str, conversation_id: str | None = None, confirm: bool | None = None,
) -> dict:
    """Punto de entrada del Root Workflow. Checklist completo: identidad ->
    contexto -> seleccion de agente (router REAL, no LLM) -> routing ->
    sesion -> eventos -> tool_calls/needs_confirmation/confirmation.

    `confirm`: si no es None Y hay una confirmacion pendiente real para esta
    sesion, este turno RESUME esa pausa (mismo mecanismo que ChatRequest.
    confirm del sistema OLD) en vez de procesar `message` como una peticion
    nueva.
    """
    context = await resolve_identity(token)
    user_id = context["user_id"]
    conversation_id = conversation_id or "adk-root-default"
    session_id = build_session_id(user_id, conversation_id)

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
        }

    pending_fc_id = _PENDING_CONFIRMATIONS.get(session_id)
    is_resume = confirm is not None and pending_fc_id is not None

    if is_resume:
        intent, agent_name, handoff = _LAST_TURN_AGENT.get(session_id, ("unknown", None, None))
        knowledge_context = ""
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
        intent, agent_name, handoff = resolve_turn_agent(message)
        knowledge_context = await build_knowledge_context(message) if intent == "knowledge" else ""
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

    events = []
    set_ephemeral_token(session_id, token)
    try:
        async for event in runner.run_async(
            user_id=str(user_id), session_id=session_id, new_message=adk_message,
            state_delta={SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY: knowledge_context},
        ):
            events.append(event)
    finally:
        clear_ephemeral_token(session_id)

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
    }
