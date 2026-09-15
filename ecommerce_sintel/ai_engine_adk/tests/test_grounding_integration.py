"""
Mision RAG Enterprise (2026-09-16, FASE 7). Integracion real de
`check_grounding()` dentro de `run_sintel_turn()` -- E2E contra LM Studio
real para la GENERACION (mismo backend de produccion), con `check_grounding`
mockeado para controlar el veredicto de forma deterministica (su propia
correctitud interna ya esta cubierta por test_grounding.py -- aqui se
prueba el WIRING: ¿el turno real realmente reemplaza la respuesta cuando el
veredicto es UNSUPPORTED? ¿de verdad no corre el validador cuando no hay
evidencia?).
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from grounding import PARTIALLY_SUPPORTED, SUPPORTED, UNGROUNDED_FALLBACK_RESPONSE, UNSUPPORTED, check_grounding  # noqa: E402


def _poisoned_chunk(content: str) -> dict:
    return {
        "content": content, "source": "manual", "app_name": "shop",
        "title": "Politica", "updated_at": "2026-09-15T00:00:00+00:00", "distance": 0.05,
    }


async def _turn_with_mocked_retrieval(message, evidence_chunks, *, user_id, conversation_id, extra_patches=()):
    import jwt as pyjwt
    import time
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_root_workflow import run_sintel_turn

    token = pyjwt.encode(
        {"token_type": "access", "user_id": user_id, "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )
    fake_context = {"user_id": user_id, "email": f"g{user_id}@sintel.dev", "user_type": "customer"}

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
async def test_veredicto_unsupported_reemplaza_la_respuesta_real_con_el_fallback_seguro():
    evidence = [_poisoned_chunk("La garantia de Sintel es de 12 meses en productos nuevos.")]
    result = await _turn_with_mocked_retrieval(
        "cual es la garantia de los productos?", evidence, user_id=60, conversation_id="g1-conv",
        extra_patches=[patch("sintel_root_workflow.check_grounding", new=AsyncMock(return_value="UNSUPPORTED"))],
    )
    assert result["intent"] == "knowledge"
    assert result["response"] == UNGROUNDED_FALLBACK_RESPONSE


@pytest.mark.asyncio
async def test_veredicto_supported_conserva_la_respuesta_real_generada_por_el_llm():
    evidence = [_poisoned_chunk("La garantia de Sintel es de 12 meses en productos nuevos.")]
    result = await _turn_with_mocked_retrieval(
        "cual es la garantia de los productos?", evidence, user_id=61, conversation_id="g2-conv",
        extra_patches=[patch("sintel_root_workflow.check_grounding", new=AsyncMock(return_value="SUPPORTED"))],
    )
    assert result["intent"] == "knowledge"
    assert result["response"] != UNGROUNDED_FALLBACK_RESPONSE
    assert result["response"]  # respuesta real, no vacia -- vino del LLM real, no se toco


@pytest.mark.asyncio
async def test_check_grounding_real_detecta_respuesta_que_contradice_la_evidencia():
    """Mision RAG-POST2 (FASE 4, 2026-09-16): re-evaluacion explicita de si
    hace falta un veredicto CONTRADICTED separado (ver AUDITORIA/RAG_POST2_
    RETRIEVAL_ANSWERABILITY_GROUNDING.md -- decision: no, UNSUPPORTED ya lo
    cubre). Esta prueba es la evidencia real de esa decision: contra el LLM
    REAL (no mockeado, a diferencia del resto de este archivo), una
    respuesta que CONTRADICE explicitamente la evidencia (no solo "no la
    menciona") debe caer en UNSUPPORTED, nunca en SUPPORTED."""
    from sintel_root_workflow import _resolve_primary_llm_params

    evidence = "[Fuente 1] Politica de garantia\nLa garantia de Sintel es de 12 meses en productos nuevos."
    contradictory_response = "La garantia de Sintel es de 30 dias unicamente, sin excepciones."

    verdict = await check_grounding(
        response=contradictory_response, evidence=evidence, **_resolve_primary_llm_params(),
    )
    assert verdict in (UNSUPPORTED, PARTIALLY_SUPPORTED), (
        f"una respuesta que contradice la evidencia nunca debe evaluarse como {SUPPORTED!r}, "
        f"el validador real devolvio {verdict!r}"
    )


@pytest.mark.asyncio
async def test_grounding_no_corre_cuando_no_hay_evidencia_real():
    """Estado real del proyecto hoy (hallazgo F-1 del baseline): ai_knowledge
    esta vacio, asi que en produccion real esto ocurre en el 100% de los
    turnos de intent "knowledge" -- confirma explicitamente que el validador
    NO se invoca (ni su costo/latencia) cuando no hay nada que validar."""
    with patch("sintel_root_workflow.check_grounding", new=AsyncMock()) as mock_check:
        result = await _turn_with_mocked_retrieval(
            "cual es el horario de atencion?", [], user_id=62, conversation_id="g3-conv",
        )
    assert result["intent"] == "knowledge"
    mock_check.assert_not_called()
