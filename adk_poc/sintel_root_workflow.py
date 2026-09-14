"""
ADK-03 -- Root Workflow de SINTEL.

Runtime real (todavia aislado en adk_poc/, NO integrado a ai_engine/main.py
-- eso es responsabilidad de ADK-11 Cutover, no de esta fase) que cumple el
checklist del plan de migracion para ADK-03: recibe una peticion, resuelve
identidad, obtiene contexto, selecciona el agente, enruta, mantiene sesion,
emite eventos.

Reutiliza el boundary REAL de identidad de ai_engine (no lo reinventa):

- `auth.decode_django_jwt` / `auth.fetch_user_context` (JWT HS256 local +
  resolucion de perfil via `/internal/ai-context/`) -- este ES, de hecho, el
  sistema "AIContext" que el plan de migracion (seccion de arquitectura
  propuesta) pedia crear como algo NUEVO. Ya existe, con otro nombre.
  ADK-03 lo consume tal cual, no lo duplica.
- El patron de sesion de `action_graph.run_action_chat`
  (`thread_id = f"{user_id}:{conversation_id}"`, namespaced por usuario para
  que nadie retome la conversacion de otro adivinando el conversation_id) se
  replica 1:1 como `session_id` de ADK.

Alcance deliberado de ADK-03 (no de ADK-04/05): solo se construye UN agente
de dominio real, `support_agent`, envolviendo tools YA probadas en ADK-02
(`OrderStatusTool`, `KycStatusTool` -- ambas de lectura, sin
require_confirmation). Migrar el resto del registro de ~28 tools reales
(inventory/marketing/payment/quotes/renting/services/support/core) y separar
Sales/Operations/Engineering es trabajo de ADK-04 (Support Agents) y ADK-05
(migracion de tools 1 a 1) -- no de esta fase, para respetar la regla de
cambio minimo y no inventar logica de dominio que todavia no tiene tools
reales migradas.

"Seleccionar workflow" (item del checklist del plan) se resuelve aqui con el
MISMO mecanismo probado en ADK-03 (ver test_root_workflow.py):
`LlmAgent.sub_agents` + transferencia LLM-driven. No existe today un segundo
sub-agente real con el que comparar routing -- por eso no se agrega un
segundo agente sintetico a este modulo (a diferencia del POC de test, donde
un "sales_agent" con una tool falsa SOLO sirve para probar que el routing no
cruza dominios, no para simular logica de negocio real).
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
from google.adk.runners import InMemoryRunner

from sintel_adapter import SINTEL_TOKEN_STATE_KEY, SINTEL_USER_STATE_KEY, adapt_sintel_tool

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"
APP_NAME = "sintel_root_workflow"

SINTEL_CONTEXT_STATE_KEY = "sintel_context"


class IdentityResolutionError(Exception):
    """El token no se pudo validar o Django rechazo la identidad -- fallar
    cerrado (nunca degradar a un turno anonimo)."""


async def resolve_identity(token: str) -> dict:
    """Reutiliza el boundary real de auth.py -- no reimplementa validacion
    de JWT ni resolucion de perfil. `decode_django_jwt` valida firma/
    expiracion localmente (HS256, misma SIGNING_KEY que Django);
    `fetch_user_context` reenvia el token a Django
    (`/internal/ai-context/`), que es la unica autoridad de perfil real
    (ProfileResolver vive solo ahi)."""
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
    """Mismo patron que `action_graph.run_action_chat`'s `thread_id` --
    namespaced por user_id para que nadie retome la conversacion de otro
    usuario adivinando el conversation_id."""
    return f"{user_id}:{conversation_id}"


_root_agent_singleton: LlmAgent | None = None


def get_root_agent() -> LlmAgent:
    """Construye (una sola vez) el Root Agent con sus sub-agentes de
    dominio reales. Ver docstring del modulo para el alcance deliberado
    (solo support_agent en ADK-03)."""
    global _root_agent_singleton
    if _root_agent_singleton is not None:
        return _root_agent_singleton

    from tools.registry import get_tool

    order_status_tool = adapt_sintel_tool(get_tool("OrderStatusTool"))
    kyc_status_tool = adapt_sintel_tool(get_tool("KycStatusTool"))

    support_agent = LlmAgent(
        name="support_agent",
        model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
        description=(
            "Atiende consultas de soporte al cliente sobre pedidos existentes "
            "y estado de verificacion KYC."
        ),
        instruction=(
            "Eres el agente de soporte de Sintel. Usa OrderStatusTool para "
            "consultar pedidos y KycStatusTool para consultar el estado de "
            "verificacion del cliente. Nunca inventes datos que no vengan de "
            "una tool."
        ),
        tools=[order_status_tool, kyc_status_tool],
    )

    root_agent = LlmAgent(
        name="sintel_root_agent",
        model=LiteLlm(model=f"ollama_chat/{OLLAMA_MODEL}", api_base=OLLAMA_BASE_URL),
        description="Root agent de Sintel -- enruta cada turno al agente de dominio correcto.",
        instruction=(
            "Eres el enrutador principal de Sintel. NUNCA respondas preguntas "
            "de negocio tu mismo -- SIEMPRE transfiere la conversacion al "
            "sub-agente apropiado. Hoy solo existe support_agent (pedidos y "
            "KYC); transferele cualquier consulta de ese tipo."
        ),
        sub_agents=[support_agent],
    )
    _root_agent_singleton = root_agent
    return root_agent


async def run_sintel_turn(*, message: str, token: str, conversation_id: str | None = None) -> dict:
    """Punto de entrada del Root Workflow -- equivalente de ADK a
    `action_graph.run_action_chat`, pero SOLO cubre el boundary de
    identidad/sesion/routing/eventos (checklist de ADK-03). No replica
    todavia el contrato completo de ChatResponse (intent, tool_calls,
    needs_confirmation, metrics) -- eso se decide en ADK-10 (dual run),
    comparando este runtime contra el real antes de exponerlo.
    """
    context = await resolve_identity(token)
    user_id = context["user_id"]
    conversation_id = conversation_id or "adk-root-default"
    session_id = build_session_id(user_id, conversation_id)

    root_agent = get_root_agent()
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)

    existing = await runner.session_service.get_session(
        app_name=APP_NAME, user_id=str(user_id), session_id=session_id,
    )
    if existing is None:
        await runner.session_service.create_session(
            app_name=APP_NAME, user_id=str(user_id), session_id=session_id,
            state={SINTEL_USER_STATE_KEY: context, SINTEL_TOKEN_STATE_KEY: token},
        )

    adk_message = types.Content(role="user", parts=[types.Part(text=message)])
    events = []
    async for event in runner.run_async(
        user_id=str(user_id), session_id=session_id, new_message=adk_message,
    ):
        events.append(event)

    final_text = "".join(
        part.text or ""
        for event in events
        if event.content and event.content.parts
        for part in event.content.parts
        if part.text
    )
    routed_to = next((e.author for e in events if e.author != "sintel_root_agent"), None)

    return {
        "conversation_id": conversation_id,
        "session_id": session_id,
        "routed_to": routed_to,
        "response": final_text,
        "events": events,
    }
