"""
ADK-03 -- prueba end-to-end de sintel_root_workflow.py contra Ollama real.

Se mockean SOLO los 2 puntos de red reales que este runtime toca (mismo
criterio que ADK-02): `auth.fetch_user_context` (llamada real a Django
`/internal/ai-context/`) y `tools.orders_tools.django_internal_get` (llamada
real a Django `/orders/`). `decode_django_jwt` NO se mockea -- se firma un
JWT real con la misma libreria (PyJWT) y el mismo JWT_SECRET_KEY que el
modulo real usa, para probar la validacion de firma real, no un stand-in.
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

from sintel_root_workflow import IdentityResolutionError, resolve_identity, run_sintel_turn

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


@pytest.mark.asyncio
async def test_root_workflow_end_to_end_resolves_identity_routes_and_maintains_session():
    """Checklist completo de ADK-03 en un solo turno: recibe peticion ->
    resuelve identidad (JWT real) -> obtiene contexto (Django mockeado) ->
    enruta al agente de dominio real -> la tool real ejecuta (bridge HTTP
    mockeado) -> se reusa la MISMA sesion en un segundo turno (mismo
    conversation_id -> mismo session_id, sin recrear sesion)."""
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

    print(f"\n[ADK-03] routed_to={result['routed_to']} session_id={result['session_id']}")
    print(f"[ADK-03] response={result['response']!r}")

    assert result["session_id"] == "7:conv-abc"
    assert result["routed_to"] == "support_agent", (
        f"El Root Workflow no enruto a support_agent: {result['routed_to']}"
    )
    assert result["response"], "El Root Workflow no genero respuesta final"

    # Segundo turno, mismo conversation_id -> misma sesion ADK (no se
    # recrea, no se pierde historial). Se prueba llamando de nuevo y
    # confirmando que NO se lanza (create_session con un session_id ya
    # existente lanzaria si el runtime lo recreara sin el guard de
    # get_session existente en run_sintel_turn).
    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response)):
        result2 = await run_sintel_turn(
            message="Y el envio ya salio?",
            token=token,
            conversation_id="conv-abc",
        )
    assert result2["session_id"] == result["session_id"]
