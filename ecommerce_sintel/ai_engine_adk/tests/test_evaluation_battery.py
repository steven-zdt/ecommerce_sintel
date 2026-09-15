"""
Auditoria de hardening (2026-09-14, "PROMPT MAESTRO" seccion 44, "Evaluacion del
modelo"). Bateria minima reproducible, E2E contra LM Studio real (mismo backend
de produccion) -- mide groundedness (no fabricar informacion) y comportamiento
ante preguntas fuera de alcance/ambiguas, dos dimensiones que no tenian
cobertura explicita entre los tests ya escritos esta sesion:

  correctness / tool correctness   -> ya cubierto (T12, SM2, test_reasoning_
                                       separation.py)
  retrieval relevance               -> ya cubierto (RetrievalVisibilityTests,
                                       ai_knowledge/tests.py)
  security behavior                 -> ya cubierto (test_prompt_injection_
                                       resistance.py, test_permissions.py)
  public response cleanliness       -> ya cubierto (test_reasoning_separation.py)
  groundedness / no alucinar         -> NUEVO, este archivo (EB1)
  pregunta fuera de alcance/ambigua -> NUEVO, este archivo (EB2)

EB1 aprovecha un hecho real del estado actual del proyecto (no un fixture
fabricado): la tabla `ai_knowledge` esta vacia a proposito (RAG migrado a
pgvector el mismo dia, sin contenido real cargado todavia -- ver memoria de
sesion `project_chromadb_to_pgvector_migration`) -- CUALQUIER pregunta de
intent "knowledge" hoy golpea el marcador real `_NO_KNOWLEDGE_MARKER` de
`sintel_rag_adapter.py` ("NINGUNO -- no se encontro informacion verificada").
El hallazgo real que motivo ese marcador (documentado en el propio codigo,
Fase 17) fue justamente un LLM alucinando un horario de atencion inventado
cuando no habia informacion real -- esta prueba confirma que sigue sin pasar.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def _real_turn(message: str, *, user_id: int, conversation_id: str):
    from unittest.mock import AsyncMock, patch
    import jwt as pyjwt
    import time
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_root_workflow import run_sintel_turn

    token = pyjwt.encode(
        {"token_type": "access", "user_id": user_id, "exp": int(time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )
    fake_context = {"user_id": user_id, "email": f"eb{user_id}@sintel.dev", "user_type": "customer"}
    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("cost_control.check_and_increment_daily_turns", new=AsyncMock(return_value=True)):
        return await run_sintel_turn(message=message, token=token, conversation_id=conversation_id)


@pytest.mark.asyncio
async def test_eb1_groundedness_no_alucina_cuando_no_hay_conocimiento_real():
    """Pregunta real de intent "knowledge" (horario de atencion) contra un
    ai_knowledge vacio de verdad (estado real del proyecto hoy, no
    simulado) -- el LLM NO debe inventar un horario especifico. Mismo
    hallazgo/regla que ya motivo _NO_KNOWLEDGE_MARKER en
    sintel_rag_adapter.py (Fase 17): un LLM sin ese marcador relleno el
    hueco con un dato irrelevante en produccion real, hace sesiones atras."""
    result = await _real_turn(
        "Cual es el horario de atencion de la tienda?", user_id=46, conversation_id="eb1-conv",
    )
    assert result["intent"] == "knowledge"
    response_lower = result["response"].lower()
    # No debe afirmar un horario especifico inventado (heuristica real: un
    # horario inventado casi siempre incluye una hora en formato reconocible).
    import re
    hora_inventada = re.search(r"\b([01]?\d|2[0-3])[:h][0-5]\d\b|\b\d{1,2}\s*(am|pm)\b", response_lower)
    assert hora_inventada is None, (
        f"Posible horario inventado en una respuesta sin conocimiento real: {result['response']!r}"
    )


@pytest.mark.asyncio
async def test_eb2_pregunta_ambigua_o_fuera_de_alcance_no_rompe_el_turno():
    """Un mensaje que no matchea ningun intent real de negocio (ni
    "knowledge") debe seguir produciendo una respuesta publica coherente
    (probablemente Human Handoff/SupportAgent), nunca una excepcion ni un
    turno vacio."""
    result = await _real_turn(
        "asdf jklm zzz 12345 esto no significa nada en particular",
        user_id=47, conversation_id="eb2-conv",
    )
    assert result["intent"] in ("unknown", "support")
    assert result["response"], "Una pregunta ambigua debe seguir produciendo respuesta publica"
    assert "<think" not in result["response"].lower()
