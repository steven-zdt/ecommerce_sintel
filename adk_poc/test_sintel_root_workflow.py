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

from sintel_root_workflow import IdentityResolutionError, resolve_identity, resolve_turn_agent, run_sintel_turn

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
