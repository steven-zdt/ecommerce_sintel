"""
Mision RAG Enterprise (2026-09-16, FASE 11 -- observabilidad). Cubre el
campo `metrics` de `run_sintel_turn()` -- antes de esta fase, `ChatResponse.
metrics` quedaba hardcodeado en None (main.py). Cierra SOLO las senales de
RAG que esta mision introdujo (retrieval_used/knowledge_state/
grounding_result/duration_ms) -- token/costo del LLM siguen sin medirse
(gap preexistente, documentado, no inventado aqui)."""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def _turn(message, evidence_chunks, *, user_id, conversation_id, extra_patches=()):
    import jwt as pyjwt
    import time
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_root_workflow import run_sintel_turn

    token = pyjwt.encode(
        {"token_type": "access", "user_id": user_id, "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )
    fake_context = {"user_id": user_id, "email": f"tm{user_id}@sintel.dev", "user_type": "customer"}
    patches = [
        patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)),
        patch("cost_control.check_and_increment_daily_turns", new=AsyncMock(return_value=True)),
        patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=evidence_chunks)),
        *extra_patches,
    ]
    for p in patches:
        p.start()
    try:
        return await run_sintel_turn(message=message, token=token, conversation_id=conversation_id)
    finally:
        for p in patches:
            p.stop()


@pytest.mark.asyncio
async def test_metrics_con_evidencia_real_y_grounding_supported():
    evidence = [{"content": "La garantia es de 12 meses.", "source": "manual",
                 "app_name": "shop", "title": "Garantia", "updated_at": "2026-09-15T00:00:00+00:00",
                 "distance": 0.05}]
    result = await _turn(
        "cual es la garantia?", evidence, user_id=70, conversation_id="tm1-conv",
        extra_patches=[patch("sintel_root_workflow.check_grounding", new=AsyncMock(return_value="SUPPORTED"))],
    )
    metrics = result["metrics"]
    assert metrics["intent"] == "knowledge"
    assert metrics["retrieval_used"] is True
    assert metrics["knowledge_state"] == "answered"
    assert metrics["grounding_result"] == "SUPPORTED"
    assert isinstance(metrics["duration_ms"], int)
    assert metrics["duration_ms"] >= 0
    assert metrics["tool_calls"] == 0


@pytest.mark.asyncio
async def test_metrics_sin_evidencia_no_corre_grounding():
    result = await _turn("cual es el horario de atencion?", [], user_id=71, conversation_id="tm2-conv")
    metrics = result["metrics"]
    assert metrics["intent"] == "knowledge"
    assert metrics["retrieval_used"] is False
    assert metrics["knowledge_state"] == "no_knowledge"
    assert metrics["grounding_result"] is None  # nunca corrio -- nada que validar


@pytest.mark.asyncio
async def test_metrics_intent_no_knowledge_no_tiene_knowledge_state():
    result = await _turn("hola, necesito ayuda con mi pedido", [], user_id=72, conversation_id="tm3-conv")
    metrics = result["metrics"]
    assert metrics["intent"] != "knowledge"
    assert metrics["knowledge_state"] is None
    assert metrics["retrieval_used"] is False
    assert metrics["grounding_result"] is None


@pytest.mark.asyncio
async def test_metrics_nunca_incluye_datos_sensibles():
    """Regla de la mision (FASE 11): nunca secrets/JWT/credenciales/
    razonamiento interno en las metricas de observabilidad."""
    result = await _turn("cual es el horario de atencion?", [], user_id=73, conversation_id="tm4-conv")
    metrics_keys = set(result["metrics"].keys())
    forbidden = {"token", "jwt", "reasoning", "internal_reasoning", "password", "secret"}
    assert not (metrics_keys & forbidden)
