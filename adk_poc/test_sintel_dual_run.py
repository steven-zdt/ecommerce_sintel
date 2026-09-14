"""
ADK-10 -- dual run REAL: OLD (action_graph.py, LangGraph) vs NEW
(sintel_root_workflow.py, ADK), contra Redis y Ollama REALES
(`ecommerce_sintel_redis`/`ecommerce_sintel_ollama`, confirmados corriendo
via `docker ps`). Django se mockea en ambos lados -- ver docstring de
sintel_dual_run.py para el porque (no extraer JWT_SECRET_KEY real de un
contenedor vivo).

Gotcha real encontrado (mismo tipo que ADK-02, generalizado aqui):
`action_graph.py` hace `from auth import fetch_company_display_name,
fetch_user_context` a nivel de MODULO (no diferido) -- su propia referencia
local queda fijada en tiempo de import. Hay que mockear
`action_graph.fetch_user_context`/`action_graph.fetch_company_display_name`
para el sistema OLD, NO `auth.fetch_user_context` (que si funciona para el
sistema NEW, que importa `auth` de forma diferida dentro de la funcion).
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

from sintel_dual_run import DUAL_RUN_USER_ID, dual_run

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]

# Gotcha real de testing (no un bug de action_graph.py): `get_action_graph()`
# cachea `_GRAPH`/`_CHECKPOINTER` a nivel de MODULO -- correcto en produccion
# (un unico event loop persistente, todo el ciclo de vida del proceso
# uvicorn), pero pytest-asyncio por default da un event loop NUEVO por test.
# El cliente Redis async cacheado queda atado al loop del primer test; el
# segundo test revienta con "Event loop is closed" al reusarlo. `loop_scope
# ="module"` (aplicado en cada @pytest.mark.asyncio de abajo) fuerza un solo
# loop para todo este archivo, igual que en produccion real.


def _make_real_access_token(user_id: int) -> str:
    now = int(time.time())
    return jwt.encode(
        {"token_type": "access", "user_id": user_id, "iat": now, "exp": now + 300},
        JWT_SECRET_KEY, algorithm="HS256",
    )


@pytest.mark.asyncio(loop_scope="module")
async def test_dual_run_order_status_intent_agrees_between_old_and_new_with_real_llm_and_redis():
    """Mensaje de pedido real, contra Ollama/Redis reales -- ambos sistemas
    deben coincidir en intent/agent (el router es el MISMO codigo real
    reusado por ambos, ver ADK-04) y ambos deben producir una respuesta."""
    token = _make_real_access_token(user_id=DUAL_RUN_USER_ID)
    fake_context = {"user_id": DUAL_RUN_USER_ID, "email": "dualrun@sintel.dev", "user_type": "customer"}
    order_response = {"results": [{"uuid": "ord-dualrun-1", "status": "shipped"}]}

    with patch("action_graph.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("action_graph.fetch_company_display_name", new=AsyncMock(return_value="Sintel")), \
         patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get", new=AsyncMock(return_value=order_response)):
        result = await dual_run(
            message="Cual es el estado de mi pedido?",
            token=token, conversation_id="dualrun-order-status",
        )

    print(f"\n[ADK-10] OLD intent={result['old'].get('intent')} agent={result['old'].get('agent')}")
    print(f"[ADK-10] NEW intent={result['new'].get('intent')} agent={result['new'].get('agent')}")
    print(f"[ADK-10] OLD response={result['old'].get('response')!r}")
    print(f"[ADK-10] NEW response={result['new'].get('response')!r}")
    print(f"[ADK-10] discrepancias={result['discrepancies']}")

    assert result["discrepancies"] == [], f"Discrepancias reales entre OLD y NEW: {result['discrepancies']}"
    assert result["old"]["intent"] == "order_status"
    assert result["new"]["intent"] == "order_status"


@pytest.mark.asyncio(loop_scope="module")
async def test_dual_run_complaint_escalation_agrees_between_old_and_new():
    """Regla de escalamiento real (queja -> SupportAgent) -- debe coincidir
    en ambos sistemas, contra Redis/Ollama reales."""
    token = _make_real_access_token(user_id=DUAL_RUN_USER_ID)
    fake_context = {"user_id": DUAL_RUN_USER_ID, "email": "dualrun@sintel.dev", "user_type": "customer"}

    with patch("action_graph.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("action_graph.fetch_company_display_name", new=AsyncMock(return_value="Sintel")), \
         patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.support_tools.django_internal_post", new=AsyncMock(return_value={"room_uuid": "r1", "ok": True})):
        result = await dual_run(
            message="Estoy muy molesto con mi pedido, esto es inaceptable",
            token=token, conversation_id="dualrun-escalation",
        )

    print(f"\n[ADK-10] OLD agent={result['old'].get('agent')} handoff={result['old'].get('handoff')}")
    print(f"[ADK-10] NEW agent={result['new'].get('agent')} handoff={result['new'].get('handoff')}")
    print(f"[ADK-10] discrepancias={result['discrepancies']}")

    assert result["discrepancies"] == [], f"Discrepancias reales entre OLD y NEW: {result['discrepancies']}"
    assert result["old"]["agent"] == "SupportAgent"
    assert result["new"]["agent"] == "SupportAgent"
