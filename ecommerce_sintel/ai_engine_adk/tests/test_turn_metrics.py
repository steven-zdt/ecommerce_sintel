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


# ── Mision RAG-POST2 (FASE 5, 2026-09-16): observabilidad extendida ────────


@pytest.mark.asyncio
async def test_metrics_request_id_es_unico_por_turno():
    r1 = await _turn("hola", [], user_id=74, conversation_id="tm5-conv")
    r2 = await _turn("hola de nuevo", [], user_id=74, conversation_id="tm5-conv")
    assert r1["metrics"]["request_id"]
    assert r2["metrics"]["request_id"]
    assert r1["metrics"]["request_id"] != r2["metrics"]["request_id"]


@pytest.mark.asyncio
async def test_metrics_retrieval_diagnostics_con_evidencia_real():
    evidence = [{"content": "La garantia es de 12 meses.", "source": "manual",
                 "app_name": "shop", "title": "Politica de garantia",
                 "updated_at": "2026-09-15T00:00:00+00:00", "distance": 0.05}]
    result = await _turn(
        "cual es la garantia?", evidence, user_id=75, conversation_id="tm6-conv",
        extra_patches=[patch("sintel_root_workflow.check_grounding", new=AsyncMock(return_value="SUPPORTED"))],
    )
    metrics = result["metrics"]
    assert metrics["retrieval_candidates"] == 1
    assert metrics["selected_sources"] == ["Politica de garantia"]
    assert metrics["best_similarity"] is not None and metrics["best_similarity"] > 0.9
    assert isinstance(metrics["retrieval_latency_ms"], int)
    assert isinstance(metrics["agent_latency_ms"], int) and metrics["agent_latency_ms"] >= 0
    assert isinstance(metrics["grounding_latency_ms"], int) and metrics["grounding_latency_ms"] >= 0
    assert isinstance(metrics["metadata_filters"], list)


@pytest.mark.asyncio
async def test_metrics_retrieval_diagnostics_vacios_si_intent_no_es_knowledge():
    result = await _turn("hola, necesito ayuda con mi pedido", [], user_id=76, conversation_id="tm7-conv")
    metrics = result["metrics"]
    assert metrics["retrieval_candidates"] is None
    assert metrics["selected_sources"] == []
    assert metrics["best_similarity"] is None
    assert metrics["retrieval_latency_ms"] is None
    assert metrics["grounding_latency_ms"] is None
    # agent_latency_ms SI corre siempre (el Runner de ADK corre para todo
    # intent, no solo "knowledge") -- unico campo de latencia no condicionado
    # a retrieval.
    assert isinstance(metrics["agent_latency_ms"], int)


@pytest.mark.asyncio
async def test_metrics_escalation_true_cuando_se_abre_ticket_de_soporte():
    result = await _turn(
        "quiero hablar con un humano, tengo un reclamo", [], user_id=77, conversation_id="tm8-conv",
        extra_patches=[patch(
            "sintel_root_workflow.extract_public_response",
            return_value=(
                "Te conecto con un agente humano.", None, ["abrir_ticket_soporte"],
                [{"capability": "abrir_ticket_soporte", "result": {"ticket_number": "SUP-1"}}],
            ),
        )],
    )
    assert result["metrics"]["escalation"] is True


@pytest.mark.asyncio
async def test_metrics_escalation_false_sin_ticket():
    result = await _turn("hola", [], user_id=78, conversation_id="tm9-conv")
    assert result["metrics"]["escalation"] is False
