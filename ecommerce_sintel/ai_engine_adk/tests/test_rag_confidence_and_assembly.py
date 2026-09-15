"""
Mision RAG Enterprise (2026-09-16, ver AUDITORIA/RAG_SUPPORT_BASELINE.md,
FASE 5/6). Cubre `sintel_rag_adapter.build_knowledge_context`:

  - retrieval confidence / answerability (best_similarity < umbral -> marcador
    explicito, nunca dejar que el LLM improvise sobre evidencia lejana);
  - context assembly estructurado (cada fuente lleva titulo/dominio/fecha,
    no solo el contenido crudo -- hallazgo F-5 del baseline);
  - comportamiento sin resultados preservado (marcador de Fase 17 original).

`retrieve_knowledge_for_chat` se mockea (no depende de pgvector/Ollama real
corriendo) -- el retrieval real contra Postgres ya esta cubierto por
`ai_knowledge/tests.py::RetrievalVisibilityTests`. Este archivo prueba
UNICAMENTE la logica de `sintel_rag_adapter.py` sobre datos ya recuperados.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sintel_rag_adapter import (  # noqa: E402
    MIN_ANSWERABLE_SIMILARITY,
    _LOW_CONFIDENCE_MARKER,
    _NO_KNOWLEDGE_MARKER,
    build_knowledge_context,
)


def _doc(content: str, distance: float, *, title="Doc", app_name="shop", updated_at="2026-09-15T10:00:00+00:00"):
    return {
        "content": content, "source": "manual", "app_name": app_name,
        "title": title, "updated_at": updated_at, "distance": distance,
    }


@pytest.mark.asyncio
async def test_sin_resultados_devuelve_marcador_original_fase17():
    with patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=[])):
        result = await build_knowledge_context("pregunta cualquiera")
    assert result == _NO_KNOWLEDGE_MARKER


@pytest.mark.asyncio
async def test_evidencia_lejana_no_supera_el_umbral_devuelve_marcador_baja_confianza():
    # distance=1.9 -> similarity=-0.9, muy por debajo de MIN_ANSWERABLE_SIMILARITY (0.35).
    docs = [_doc("contenido no relacionado", distance=1.9)]
    with patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=docs)):
        result = await build_knowledge_context("pregunta cualquiera")
    assert result == _LOW_CONFIDENCE_MARKER


@pytest.mark.asyncio
async def test_evidencia_justo_en_el_umbral_es_answerable():
    # similarity = 1 - distance debe ser >= MIN_ANSWERABLE_SIMILARITY para pasar.
    distance_en_el_limite = 1.0 - MIN_ANSWERABLE_SIMILARITY
    docs = [_doc("contenido relevante real", distance=distance_en_el_limite, title="Politica de garantia")]
    with patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=docs)):
        result = await build_knowledge_context("cual es la garantia")
    assert result != _LOW_CONFIDENCE_MARKER
    assert result != _NO_KNOWLEDGE_MARKER
    assert "Politica de garantia" in result


@pytest.mark.asyncio
async def test_context_assembly_incluye_metadata_estructurada_por_fuente():
    docs = [
        _doc("El horario es de lunes a sabado.", distance=0.1, title="Horario de atencion",
             app_name="support", updated_at="2026-08-01T00:00:00+00:00"),
        _doc("La garantia cubre 12 meses.", distance=0.2, title="Politica de garantia",
             app_name="shop", updated_at="2026-07-15T00:00:00+00:00"),
    ]
    with patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=docs)):
        result = await build_knowledge_context("horario y garantia")

    # Cada fuente debe llevar su encabezado real (antes de esta mision, solo
    # se enviaba el contenido crudo, sin title/app_name/updated_at -- F-5).
    assert "[Fuente 1] Horario de atencion (dominio: support, actualizado: 2026-08-01)" in result
    assert "El horario es de lunes a sabado." in result
    assert "[Fuente 2] Politica de garantia (dominio: shop, actualizado: 2026-07-15)" in result
    assert "La garantia cubre 12 meses." in result
    assert "\n---\n" in result


@pytest.mark.asyncio
async def test_confianza_usa_el_mejor_candidato_no_el_promedio():
    """Un solo resultado fuerte entre varios debiles debe seguir siendo
    answerable -- la decision se basa en el MEJOR candidato, no en diluir
    la confianza promediando con resultados irrelevantes de relleno (top-k
    siempre completa k si hay filas, sin piso de calidad propio)."""
    fuerte = 1.0 - MIN_ANSWERABLE_SIMILARITY - 0.05  # similarity por encima del umbral
    docs = [
        _doc("contenido realmente relevante", distance=fuerte, title="Fuente fuerte"),
        _doc("relleno irrelevante 1", distance=1.8),
        _doc("relleno irrelevante 2", distance=1.9),
    ]
    with patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=docs)):
        result = await build_knowledge_context("pregunta real")
    assert result != _LOW_CONFIDENCE_MARKER
    assert "Fuente fuerte" in result


@pytest.mark.asyncio
async def test_distance_ausente_no_rompe_no_lanza_excepcion():
    """Defensivo: si algun caller futuro (o una version distinta del
    endpoint interno) no incluye "distance", no debe lanzar KeyError --
    debe tratarse como similitud minima (0.0), no como evidencia fuerte."""
    doc_sin_distance = {"content": "x", "source": "", "app_name": "shop", "title": "T", "updated_at": "2026-01-01T00:00:00+00:00"}
    with patch("retrievers.retrieve_knowledge_for_chat", new=AsyncMock(return_value=[doc_sin_distance])):
        result = await build_knowledge_context("pregunta")
    assert result == _LOW_CONFIDENCE_MARKER
