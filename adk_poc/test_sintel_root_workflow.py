"""
ADK-03/04 -- prueba end-to-end de sintel_root_workflow.py.

Se mockean SOLO los puntos de red reales que este runtime toca (mismo
criterio que ADK-02): `auth.fetch_user_context` (llamada real a Django
`/internal/ai-context/`) y `tools.orders_tools.django_internal_get` (llamada
real a Django `/orders/`). `decode_django_jwt` NO se mockea -- se firma un
JWT real con la misma libreria (PyJWT) y el mismo JWT_SECRET_KEY que el
modulo real usa, para probar la validacion de firma real, no un stand-in.

`resolve_turn_agent()` se prueba SIN Ollama (es codigo puro, determinista --
reutiliza `action_graph.detect_business_intents` + `agents.AgentRegistry`
reales) para verificar el router real y su regla de escalamiento de forma
rapida y sin depender de un LLM.
"""
import os
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import jwt
import pytest

os.environ.setdefault("JWT_SECRET_KEY", "adk-poc-test-secret-key-32-bytes-minimum")

AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel" / "ai_engine"
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))

from sintel_adapter import _EPHEMERAL_TOKENS
from sintel_rag_adapter import SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY
from sintel_root_workflow import (
    APP_NAME,
    IdentityResolutionError,
    _session_service,
    resolve_identity,
    resolve_turn_agent,
    run_sintel_turn,
)

# NOTA (gotcha real encontrado escribiendo estos tests): mockear
# `retrievers.httpx.AsyncClient` (como hace test_sintel_rag_adapter.py, en
# aislamiento) rompe cualquier test que en el MISMO turno tambien haga una
# llamada real a Ollama -- `retrievers.py` hace `import httpx` (no `from
# httpx import AsyncClient`), asi que `retrievers.httpx` ES el modulo httpx
# compartido globalmente, no una referencia local; parchear
# `AsyncClient` ahi lo parcha para TODO el proceso, incluyendo el propio
# `httpx.AsyncClient` interno de litellm -- el turno explota con
# "'coroutine' object has no attribute 'get'" al intentar hablar con
# Ollama. Por eso estos tests mockean `retrievers.retrieve_knowledge_for_chat`
# directo (la funcion real que `sintel_rag_adapter.build_knowledge_context`
# ya importa localmente en cada llamada) en vez de su transporte HTTP.

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]


def _make_real_access_token(user_id: int) -> str:
    """JWT real (firma HS256 valida), con los mismos claims que SimpleJWT
    siempre emite -- prueba `auth.decode_django_jwt` real, sin mock."""
    now = int(time.time())
    payload = {
        "token_type": "access",
        "user_id": user_id,
        "iat": now,
        "exp": now + 300,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm="HS256")


@pytest.mark.asyncio
async def test_resolve_identity_uses_real_jwt_validation_and_real_django_context_call():
    token = _make_real_access_token(user_id=42)
    fake_context = {
        "user_id": 42, "email": "cliente@sintel.dev", "user_type": "customer",
        "is_staff": False, "kyc_status": "verified",
    }
    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)) as mock_ctx:
        context = await resolve_identity(token)

    mock_ctx.assert_awaited_once_with(token)
    assert context["user_id"] == 42
    assert context["kyc_status"] == "verified"


@pytest.mark.asyncio
async def test_resolve_identity_fails_closed_on_invalid_signature():
    bad_token = jwt.encode(
        {"token_type": "access", "user_id": 1, "exp": int(time.time()) + 300},
        "wrong-secret-key-but-still-32-bytes-plus", algorithm="HS256",
    )
    with pytest.raises(IdentityResolutionError):
        await resolve_identity(bad_token)


def test_resolve_turn_agent_routes_order_status_without_escalation():
    """Router REAL, sin Ollama: un mensaje de pedido normal enruta a
    OrderAgent, sin handoff -- mismo resultado que produciria
    action_graph.py::node_detect_intent con el mismo mensaje."""
    intent, agent_name, handoff = resolve_turn_agent("Cual es el estado de mi pedido?")
    assert intent == "order_status"
    assert agent_name == "OrderAgent"
    assert handoff is None


def test_resolve_turn_agent_escalates_complaint_to_support_agent():
    """Router REAL, sin Ollama: una queja sobre un pedido enruta primero a
    OrderAgent por intent, pero la regla de escalamiento de OrderAgent
    ("queja|reclamo|molesto|inaceptable|...") la deriva a SupportAgent --
    mismo comportamiento que el `action_graph.py` real en produccion."""
    intent, agent_name, handoff = resolve_turn_agent(
        "Estoy muy molesto con mi pedido, esto es inaceptable",
    )
    assert intent == "order_status"
    assert agent_name == "SupportAgent"
    assert handoff == "OrderAgent->SupportAgent"


@pytest.mark.asyncio
async def test_root_workflow_end_to_end_resolves_identity_routes_and_maintains_session():
    """Checklist completo de ADK-03/04 en un solo turno: recibe peticion ->
    resuelve identidad (JWT real) -> obtiene contexto (Django mockeado) ->
    router REAL de Sintel enruta a OrderAgent -> la tool real ejecuta
    (bridge HTTP mockeado) -> se reusa la MISMA sesion en un segundo turno
    (mismo conversation_id -> mismo session_id, sin recrear sesion)."""
    token = _make_real_access_token(user_id=7)
    fake_context = {"user_id": 7, "email": "cliente2@sintel.dev", "user_type": "customer"}
    order_response = {"results": [{"uuid": "ord-42", "status": "in_transit"}]}

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response)):
        result = await run_sintel_turn(
            message="Cual es el estado de mi pedido?",
            token=token,
            conversation_id="conv-abc",
        )

    print(f"\n[ADK-04] intent={result['intent']} agent={result['agent']} handoff={result['handoff']} session_id={result['session_id']}")
    print(f"[ADK-04] response={result['response']!r}")

    assert result["session_id"] == "7:conv-abc"
    assert result["intent"] == "order_status"
    assert result["agent"] == "OrderAgent", (
        f"El Root Workflow no enruto a OrderAgent: {result['agent']}"
    )
    assert result["handoff"] is None
    assert result["response"], "El Root Workflow no genero respuesta final"

    # Segundo turno, mismo conversation_id -> misma sesion ADK (no se
    # recrea, no se pierde historial), aunque el agente activo sea el
    # mismo en este caso -- lo que se prueba es que el Runner explicito con
    # session_service compartido (no InMemoryRunner) preserva la sesion.
    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response)):
        result2 = await run_sintel_turn(
            message="Y el envio ya salio?",
            token=token,
            conversation_id="conv-abc",
        )
    assert result2["session_id"] == result["session_id"]


@pytest.mark.asyncio
async def test_run_sintel_turn_routes_knowledge_intent_to_sales_agent_and_injects_rag_context():
    """ADK-06: un mensaje de politica/FAQ real enruta (router determinista,
    no el LLM) a SalesAgent y el contexto recuperado (mockeado en el unico
    punto de red real) queda sembrado en el state de la sesion de ADK --
    verifica el mecanismo de inyeccion, no solo que responda algo."""
    token = _make_real_access_token(user_id=15)
    fake_context = {"user_id": 15, "email": "cliente3@sintel.dev", "user_type": "customer"}
    chunks = [{"content": "La garantia de todos los equipos es de 12 meses desde la fecha de compra."}]

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=chunks)):
        result = await run_sintel_turn(
            message="Cual es la politica de garantia de ustedes?",
            token=token,
            conversation_id="conv-knowledge",
        )

    assert result["intent"] == "knowledge"
    assert result["agent"] == "SalesAgent"

    session = await _session_service.get_session(
        app_name=APP_NAME, user_id="15", session_id=result["session_id"],
    )
    assert "garantia de todos los equipos es de 12 meses" in session.state[SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY]


@pytest.mark.asyncio
async def test_run_sintel_turn_e2e_answer_is_grounded_not_hallucinated():
    """Regresion directa del incidente real de Fase 17 (ver
    sintel_rag_adapter.py): con Ollama REAL respondiendo, la respuesta debe
    basarse en el hecho inyectado (un dato verificable y especifico que el
    modelo no podria adivinar), no en una alucinacion generica."""
    token = _make_real_access_token(user_id=16)
    fake_context = {"user_id": 16, "email": "cliente4@sintel.dev", "user_type": "customer"}
    chunks = [{"content": "El horario de atencion de Sintel es de 7:00am a 4:30pm, de lunes a viernes."}]

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=chunks)):
        result = await run_sintel_turn(
            message="Cual es el horario de atencion?",
            token=token,
            conversation_id="conv-grounded",
        )

    print(f"\n[ADK-06] response={result['response']!r}")
    assert "7:00" in result["response"] or "7:00am" in result["response"] or "7am" in result["response"].lower(), (
        f"La respuesta no parece basada en el dato real inyectado (horario "
        f"7:00am-4:30pm) -- posible alucinacion: {result['response']!r}"
    )


@pytest.mark.asyncio
async def test_run_sintel_turn_clears_knowledge_context_on_next_non_knowledge_turn():
    """El contexto RAG de un turno de 'knowledge' NUNCA debe seguir presente
    en un turno posterior de otro intent dentro de la MISMA sesion -- mismo
    criterio que optimized_context, reconstruido desde cero cada turno en
    el sistema real (si esto fallara, un agente de OTRO dominio recibiria
    conocimiento de una pregunta anterior no relacionada)."""
    token = _make_real_access_token(user_id=17)
    fake_context = {"user_id": 17, "email": "cliente5@sintel.dev", "user_type": "customer"}
    chunks = [{"content": "Informacion de politica que NO debe sobrevivir al siguiente turno."}]
    order_response = {"results": [{"uuid": "ord-99", "status": "delivered"}]}

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=chunks)):
        first = await run_sintel_turn(
            message="Cual es la politica de garantia?",
            token=token, conversation_id="conv-leak-check",
        )
    assert first["intent"] == "knowledge"

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response)):
        second = await run_sintel_turn(
            message="Cual es el estado de mi pedido?",
            token=token, conversation_id="conv-leak-check",
        )
    assert second["intent"] == "order_status"
    assert second["session_id"] == first["session_id"]

    session = await _session_service.get_session(
        app_name=APP_NAME, user_id="17", session_id=second["session_id"],
    )
    assert session.state[SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY] == "", (
        "El conocimiento RAG del turno anterior sobrevivio a un turno de "
        "otro intent -- se filtraria al agente de otro dominio."
    )


@pytest.mark.asyncio
async def test_run_sintel_turn_never_persists_the_jwt_in_session_state():
    """ADK-08, regresion de seguridad directa: `action_graph.py` real
    declara la regla dura "el checkpointer persiste el estado; un token no
    se persiste". `Session.state` es exactamente lo que un SessionService
    persistente de ADK (confirmado real: `DatabaseSessionService`, bundled
    con el propio framework) guardaria tal cual -- si el token apareciera
    ahi, el dia que ADK-11+ cambie `InMemorySessionService` por un backend
    persistente, el JWT quedaria escrito en ese backend. Prueba que el
    token JAMAS aparece en `Session.state` (en ningun valor, no solo bajo
    la clave conocida) mientras la tool real SI lo recibe y lo usa
    correctamente (no es un test de "no funciona", es un test de "funciona
    Y no persiste")."""
    token = _make_real_access_token(user_id=23)
    fake_context = {"user_id": 23, "email": "cliente6@sintel.dev", "user_type": "customer"}
    order_response = {"results": [{"uuid": "ord-secure", "status": "delivered"}]}

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch(
             "tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response),
         ) as mock_bridge:
        result = await run_sintel_turn(
            message="Cual es el estado de mi pedido?",
            token=token, conversation_id="conv-token-security",
        )

    # La tool real SI recibio el token real -- la seguridad no vino a costa
    # de romper la funcionalidad.
    call_args = mock_bridge.call_args
    token_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("token")
    assert token_arg == token, "La tool real nunca recibio el token -- la funcionalidad se rompio"

    session = await _session_service.get_session(
        app_name=APP_NAME, user_id="23", session_id=result["session_id"],
    )
    serialized_state = str(session.state)
    assert token not in serialized_state, (
        "El JWT aparece en Session.state -- un SessionService persistente lo "
        "guardaria, violando la regla real de action_graph.py."
    )

    # El dict efimero tampoco debe dejar el token colgado despues del turno.
    assert result["session_id"] not in _EPHEMERAL_TOKENS
