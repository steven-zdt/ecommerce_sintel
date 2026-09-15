"""
Mision RAG Enterprise (2026-09-16, FASE 10 -- evaluacion formal). Runner
del dataset versionado (dataset.py) -- E2E real contra LM Studio (mismo
backend de produccion), mismo patron ya probado en
ai_engine_adk/tests/test_evaluation_battery.py (EB1/EB2), extendido a un
dataset categorizado y parametrizado en vez de 2 casos sueltos.

Mide (impreso via -s, no como assertion estricta -- el entorno de latencia
real varia): latencia, intent resuelto, si el turno escalo/pidio
confirmacion. Regla de la mision (FASE 11): "None/NOT_MEASURED cuando
corresponda" -- no se fabrica una metrica de precision/recall real porque
las categorias que las necesitarian estan BLOQUEADAS por F-1 (ver
dataset.py, BLOCKED_CATEGORIES).
"""
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dataset import BLOCKED_CATEGORIES, DATASET  # noqa: E402

_BASE_USER_ID = 200  # rango dedicado, sin colision con otros archivos de test


async def _real_turn(message: str, *, user_id: int, conversation_id: str):
    import jwt as pyjwt
    import time as _time
    import os

    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-len")
    from sintel_root_workflow import run_sintel_turn

    token = pyjwt.encode(
        {"token_type": "access", "user_id": user_id, "exp": int(_time.time()) + 300},
        os.environ["JWT_SECRET_KEY"], algorithm="HS256",
    )
    fake_context = {"user_id": user_id, "email": f"eval{user_id}@sintel.dev", "user_type": "customer"}
    with patch("auth.fetch_user_context", new=AsyncMock(return_value=fake_context)), \
         patch("cost_control.check_and_increment_daily_turns", new=AsyncMock(return_value=True)):
        return await run_sintel_turn(message=message, token=token, conversation_id=conversation_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", DATASET, ids=[c.id for c in DATASET])
async def test_rag_evaluation_case(case):
    user_id = _BASE_USER_ID + DATASET.index(case)
    started = time.monotonic()
    result = await _real_turn(case.query, user_id=user_id, conversation_id=f"eval-{case.id}")
    latency_ms = (time.monotonic() - started) * 1000

    response_lower = (result["response"] or "").lower()

    # Invariantes que aplican a TODA categoria, sin importar contenido real:
    assert result["response"], f"{case.id}: el turno debe producir una respuesta publica"
    assert "<think" not in response_lower, f"{case.id}: leak de razonamiento interno"
    assert "reasoning_content" not in response_lower, f"{case.id}: leak de razonamiento interno"

    for forbidden in case.forbidden_substrings:
        assert forbidden.lower() not in response_lower, (
            f"{case.id}: respuesta contiene un dato especifico que no deberia poder "
            f"afirmar sin evidencia real: {forbidden!r}"
        )

    # Observabilidad de la corrida (no assertions de latencia -- entorno
    # compartido/variable, ver FASE 13 "optimizacion" para umbrales reales
    # una vez haya mediciones repetidas).
    print(
        f"\n[rag-eval] {case.id} ({case.category}) latency_ms={latency_ms:.0f} "
        f"intent={result['intent']} agent={result['agent']} "
        f"needs_confirmation={result['needs_confirmation']} "
        f"metrics={result.get('metrics')}"
    )


def test_categorias_bloqueadas_no_tienen_casos_fabricados():
    """Confirma que ninguna categoria bloqueada por F-1 (contenido real
    inexistente) tiene un caso en el dataset -- evita que alguien agregue
    un caso con una "respuesta esperada" inventada sin corpus real."""
    dataset_categories = {c.category for c in DATASET}
    assert not (dataset_categories & set(BLOCKED_CATEGORIES))


def test_dataset_tiene_al_menos_un_caso_por_categoria_evaluable():
    categorias_presentes = {c.category for c in DATASET}
    assert categorias_presentes == {
        "NO_ANSWER", "AMBIGUOUS", "ADVERSARIAL", "MULTI_TOPIC", "PROMPT_INJECTION",
    }
