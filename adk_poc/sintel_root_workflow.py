"""
ADK-03/04/06 -- Root Workflow de SINTEL.

Runtime real (todavia aislado en adk_poc/, NO integrado a ai_engine/main.py
-- eso es responsabilidad de ADK-11 Cutover, no de esta fase) que cumple el
checklist del plan de migracion: recibe una peticion, resuelve identidad,
obtiene contexto, selecciona el agente, enruta, mantiene sesion, emite
eventos.

## Decision de arquitectura ADK-04 (confirmada por el usuario, ver
## AUDITORIA/ADK_MIGRATION_AUDIT.md seccion 8ter)

ADK-03 probo (test_root_workflow.py) que `LlmAgent.sub_agents` +
transferencia LLM-driven FUNCIONA. Pero el routing REAL de `ai_engine` hoy
es 100% deterministico: `detect_business_intents()` (regex) ->
`AgentRegistry.route()` (dict) -> `AgentRegistry.apply_escalation()` (regex
de seguridad -- ej. una queja SIEMPRE escala a SupportAgent, un cambio de
fecha de alquiler SIEMPRE es no-self-service, decision del usuario
2026-07-16 "gap #1"). El propio `action_graph.py` lo declara como regla
dura: "Ninguna regla de negocio vive en el prompt: las Tools/Selectors
deciden."

Delegar esa decision a un LLM (via sub_agents) violaria la regla de la
mision "ADK ORQUESTA. SINTEL EJECUTA Y CONTROLA" -- por eso, con
confirmacion explicita del usuario, este modulo NO usa sub_agents/transfer
para el routing de produccion. `resolve_turn_agent()` reutiliza las
funciones REALES de `action_graph.py` (no las copia) para decidir; ADK solo
ejecuta al agente ya elegido por Sintel. El mecanismo `sub_agents` queda
validado como capacidad real del framework (ADK-03), sin uso en este flujo.

## Identidad y sesion (sin cambios desde ADK-03)

- `auth.decode_django_jwt` / `auth.fetch_user_context` -- boundary real de
  identidad, YA es el "AIContext" que el plan pedia crear de cero.
- `session_id = f"{user_id}:{conversation_id}"` -- mismo patron que
  `action_graph.run_action_chat`'s `thread_id`.

## Los 9 agentes de dominio (ADK-04)

`get_domain_agent(profile_name)` construye un `LlmAgent` real por cada
`AgentProfile` YAML (`ai_engine/agents/profiles/*.yaml`, cargados por el
`AgentRegistry` real) -- mismo nombre, mismas tools (adaptadas 1:1 via
`sintel_adapter.adapt_sintel_tool`, ADK-02), mismo tono/objetivo/
personalidad como instruccion (texto real del YAML, no inventado). Un
`Runner` explicito (no `InMemoryRunner`, que crea su propio
`InMemorySessionService` AISLADO por instancia -- verificado que rompe la
continuidad de sesion entre turnos si el agente activo cambia de un turno a
otro) comparte un unico `InMemorySessionService` a nivel de modulo, para que
la sesion sobreviva aunque el agente cambie turno a turno.

## RAG (ADK-06)

Retrieval NO es una decision del LLM en el sistema real -- es una rama
determinista del grafo (`node_route_after_context`, solo si
`intent == "knowledge"`). Mismo principio que ADK-04: el Root Workflow
decide SI hace retrieval (via `resolve_turn_agent()`, ya determinista) y le
INYECTA el resultado al agente -- nunca se expone como una Tool que el LLM
pueda invocar por su cuenta. `sintel_rag_adapter.build_knowledge_context()`
reutiliza `retrievers.retrieve_knowledge_for_chat` real (pgvector via
`ai_knowledge`, ver `project_chromadb_to_pgvector_migration` en memoria) y
replica el marcador de gobernanza real de Fase 17 (sin el, el LLM alucina
cuando no hay conocimiento -- incidente real ya documentado en
`action_graph.py`).

La inyeccion usa `LlmAgent.instruction` como CALLABLE
(`(ReadonlyContext) -> str`, campo real de ADK, evaluado por turno) que lee
`SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY` del state de la sesion -- el state se
setea por turno via `Runner.run_async(state_delta=...)` (parametro real de
`Runner`), nunca queda "pegado" de un turno anterior: en turnos con
`intent != "knowledge"` se limpia explicitamente a cadena vacia, replicando
que `action_graph.py::node_optimize_context` reconstruye `optimized_context`
desde cero cada turno, nunca lo acumula entre turnos.
"""
import sys
from pathlib import Path

AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel" / "ai_engine"
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))

from google.adk.features._feature_registry import FeatureName, override_feature_enabled

override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, False)

from google.genai import types

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

from sintel_adapter import SINTEL_TOKEN_STATE_KEY, SINTEL_USER_STATE_KEY, adapt_sintel_tool
from sintel_rag_adapter import SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY, build_knowledge_context

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"
APP_NAME = "sintel_root_workflow"


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
    """Router REAL de Sintel -- reutiliza `action_graph.py::
    detect_business_intents` y `agents.AgentRegistry.route/
    apply_escalation` tal cual, replicando exactamente la logica de
    `action_graph.py::node_detect_intent` (mismo codigo, no una copia).
    Devuelve (intent, agent_name, handoff)."""
    from action_graph import detect_business_intents, INTENT_CAPABILITIES
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

    # Callable (no string fijo): LlmAgent.instruction acepta
    # (ReadonlyContext) -> str, evaluado por turno -- necesario para
    # inyectar el bloque de conocimiento RAG (ADK-06) solo en los turnos
    # que lo traen via state_delta, igual que optimized_context en el
    # sistema real se reconstruye turno a turno, nunca queda fijo.
    async def instruction_provider(ctx) -> str:
        knowledge = ctx.state.get(SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY, "")
        if knowledge:
            return f"{base_instruction}\n\nConocimiento relevante:\n{knowledge}"
        return base_instruction

    agent = LlmAgent(
        name=profile.name,
        model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
        description=profile.description,
        instruction=instruction_provider,
        tools=tools,
    )
    _domain_agent_cache[profile_name] = agent
    return agent


# InMemoryRunner crea su propio InMemorySessionService AISLADO por instancia
# (verificado leyendo InMemoryRunner.__init__) -- si se creara un Runner por
# turno con InMemoryRunner, la sesion se perderia en cuanto el agente activo
# cambiara de un turno a otro. Un unico session_service a nivel de modulo,
# compartido entre Runners, resuelve esto sin tocar la API publica de ADK.
_session_service = InMemorySessionService()


async def run_sintel_turn(*, message: str, token: str, conversation_id: str | None = None) -> dict:
    """Punto de entrada del Root Workflow -- checklist de ADK-03/04:
    identidad -> contexto -> seleccion de agente (router REAL de Sintel,
    no LLM) -> routing -> sesion -> eventos. No replica todavia el
    contrato completo de ChatResponse (tool_calls, needs_confirmation,
    metrics) -- eso se decide en ADK-10 (dual run).
    """
    context = await resolve_identity(token)
    user_id = context["user_id"]
    conversation_id = conversation_id or "adk-root-default"
    session_id = build_session_id(user_id, conversation_id)

    intent, agent_name, handoff = resolve_turn_agent(message)
    domain_agent = get_domain_agent(agent_name)

    # ADK-06: retrieval SOLO si el router determinista clasifico "knowledge"
    # (mismo criterio que node_route_after_context real) -- nunca a
    # discrecion del LLM. En cualquier otro intent se limpia explicitamente
    # a "" para no arrastrar el conocimiento de un turno anterior de la
    # MISMA sesion (mismo criterio que optimized_context, reconstruido
    # desde cero cada turno en el sistema real).
    knowledge_context = await build_knowledge_context(message) if intent == "knowledge" else ""

    runner = Runner(
        app_name=APP_NAME, agent=domain_agent, session_service=_session_service,
    )

    existing = await _session_service.get_session(
        app_name=APP_NAME, user_id=str(user_id), session_id=session_id,
    )
    if existing is None:
        await _session_service.create_session(
            app_name=APP_NAME, user_id=str(user_id), session_id=session_id,
            state={SINTEL_USER_STATE_KEY: context, SINTEL_TOKEN_STATE_KEY: token},
        )

    adk_message = types.Content(role="user", parts=[types.Part(text=message)])
    events = []
    async for event in runner.run_async(
        user_id=str(user_id), session_id=session_id, new_message=adk_message,
        state_delta={SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY: knowledge_context},
    ):
        events.append(event)

    final_text = "".join(
        part.text or ""
        for event in events
        if event.content and event.content.parts
        for part in event.content.parts
        if part.text
    )

    return {
        "conversation_id": conversation_id,
        "session_id": session_id,
        "intent": intent,
        "agent": agent_name,
        "handoff": handoff,
        "response": final_text,
        "events": events,
    }
