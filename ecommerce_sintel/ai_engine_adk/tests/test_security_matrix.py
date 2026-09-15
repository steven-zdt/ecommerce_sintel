"""
Auditoria de hardening (2026-09-14, "PROMPT MAESTRO" seccion 43, "Tests de
seguridad" -- matriz de 15 casos). La mayoria de esos 15 casos ya tenian
cobertura real en otros archivos de esta sesion:
  prompt injection          -> test_prompt_injection_resistance.py
  tool misuse/unauthorized  -> test_prompt_injection_resistance.py (PI1)
  privilege escalation      -> test_permissions.py
  RAG data leakage          -> ai_knowledge/tests.py::RetrievalVisibilityTests
  reasoning leakage         -> test_reasoning_separation.py
  unbounded loops           -> test_agent_loop_limits.py
  timeout                   -> restaurado en sintel_root_workflow.py (LLM timeout)
Este archivo cubre los casos que SI eran gaps reales de cobertura:
  invalid tool arguments / tool genera error (caso 8 del prompt)
  oversized inputs
  provider failure (fallo total del LLM, no de una Tool)
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError

from main import ChatRequest


def test_sm1_oversized_input_es_rechazado_por_validacion():
    """ChatRequest.message tiene max_length=4000 (mismo limite que el sistema
    OLD, G1/AUDITORIA/16 -- sin techo, un proveedor de pago detras de
    LOCAL_MODEL_CHAIN es un riesgo de costo directo)."""
    with pytest.raises(ValidationError):
        ChatRequest(message="x" * 4001)
    # Justo en el limite: no debe rechazar.
    ChatRequest(message="x" * 4000)


@pytest.mark.asyncio
async def test_sm2_error_real_de_una_tool_degrada_el_turno_sin_matar_todo():
    """Hallazgo real de esta auditoria (seccion 43 caso 8 / seccion 45
    Fail-safe): confirmado EMPIRICAMENTE que sin on_tool_error_callback, ADK
    no atrapa una excepcion real de una Tool -- se propaga hasta afuera de
    run_sintel_turn(). handle_tool_error() (sintel_adapter.py) lo cierra:
    la Tool que falla queda como un resultado de error estructurado, el LLM
    sigue el turno y produce una respuesta publica normal -- no un 500, no
    un traceback, no un turno completo perdido por UNA sola Tool caida."""
    from unittest.mock import AsyncMock, patch
    import jwt as pyjwt
    import time
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_root_workflow import run_sintel_turn

    token = pyjwt.encode(
        {"token_type": "access", "user_id": 45, "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )
    fake_context = {"user_id": 45, "email": "sm2@sintel.dev", "user_type": "customer"}

    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("tools.orders_tools.django_internal_get",
               new=AsyncMock(side_effect=RuntimeError("boom real de la tool -- Django caido"))), \
         patch("cost_control.check_and_increment_daily_turns", new=AsyncMock(return_value=True)):
        result = await run_sintel_turn(
            message="Cual es el estado de mi pedido?", token=token, conversation_id="sm2-conv",
        )

    assert result["response"], "El turno no genero respuesta publica"
    # No debe filtrarse nada de la excepcion real al canal publico.
    assert "boom real de la tool" not in result["response"]
    assert "Traceback" not in result["response"]
    assert "RuntimeError" not in result["response"]
    # La Tool que fallo SI queda registrada como resultado de error estructurado.
    assert any(
        tr["name"] == "OrderStatusTool" and tr["response"].get("status_code") == 502
        for tr in result["tool_results"]
    )


@pytest.mark.asyncio
async def test_sm3_fallo_total_del_proveedor_llm_no_expone_traceback():
    """A diferencia de sm2 (una Tool falla), aqui falla el LLM/proveedor
    completo -- el catch-all real de main.py::chat() (no run_sintel_turn())
    es el que degrada con gracia. Prueba la funcion de endpoint real
    directamente (sin servidor HTTP), mismo criterio que el resto de esta
    sesion: contra la funcion real, no un mock de "como creo que se comporta"."""
    from unittest.mock import AsyncMock, patch
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    import main as main_module

    req = main_module.ChatRequest(message="hola", conversation_id="sm3-conv")

    with patch(
        "main.run_sintel_turn",
        new=AsyncMock(side_effect=ConnectionError("LM Studio inalcanzable -- fallo real de proveedor")),
    ):
        response = await main_module.chat(req, token="fake-token-no-se-valida-en-este-mock")

    assert response.metrics == {"engine_unavailable": True}
    assert "LM Studio inalcanzable" not in response.response
    assert "Traceback" not in response.response
    assert "ConnectionError" not in response.response
    assert response.response   # respuesta publica no vacia, con handoff implicito
