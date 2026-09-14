"""
ADK-06 -- RAG adapter de SINTEL.

`retrieve_knowledge_for_chat` (ai_engine/retrievers.py) no tiene un seam de
mock simple tipo `http_bridge.django_internal_get` -- abre su propio
`httpx.AsyncClient` inline. Se mockea `retrievers.httpx.AsyncClient`
directo (unico punto de red real que este modulo toca), igual criterio de
"mockear solo el punto de red" que el resto de la suite.
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

AI_ENGINE_ROOT = Path(__file__).resolve().parent.parent / "ecommerce_sintel" / "ai_engine"
if str(AI_ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ENGINE_ROOT))

from sintel_rag_adapter import SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY, build_knowledge_context


def _mock_httpx_client(status_code: int, json_body: dict):
    """Doble minimo de httpx.AsyncClient como context manager async, para
    mockear la unica llamada de red real de retrieve_knowledge_for_chat."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body

    client = AsyncMock()
    client.post = AsyncMock(return_value=resp)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=client)
    return factory, client


@pytest.mark.asyncio
async def test_build_knowledge_context_joins_and_truncates_real_chunks():
    chunks = [
        {"content": "La garantia de los equipos dura 12 meses desde la compra."},
        {"content": "Los cambios de fecha de alquiler requieren contactar a soporte."},
    ]
    factory, client = _mock_httpx_client(200, {"chunks": chunks})

    with patch("retrievers.httpx.AsyncClient", new=factory):
        context = await build_knowledge_context("cual es la garantia de los equipos?")

    assert "garantia de los equipos dura 12 meses" in context
    assert "cambios de fecha de alquiler" in context
    assert "\n---\n" in context
    client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_knowledge_context_injects_governance_marker_when_empty():
    """Regresion directa del hallazgo real de Fase 17 (ver docstring de
    sintel_rag_adapter.py): sin este marcador el LLM alucino una respuesta
    de horario de atencion -- el marcador debe ser BIT a BIT el mismo texto
    real que usa action_graph.py::node_retrieve_knowledge."""
    factory, client = _mock_httpx_client(200, {"chunks": []})

    with patch("retrievers.httpx.AsyncClient", new=factory):
        context = await build_knowledge_context("cual es el horario de atencion?")

    assert context == "NINGUNO -- no se encontro informacion verificada sobre este tema."


@pytest.mark.asyncio
async def test_build_knowledge_context_degrades_gracefully_when_django_unreachable():
    """retrieve_knowledge_for_chat real devuelve [] (nunca lanza) si Django
    no responde -- confirma que el adapter hereda esa degradacion con
    gracia, no un 500 crudo."""
    factory, client = _mock_httpx_client(503, {})

    with patch("retrievers.httpx.AsyncClient", new=factory):
        context = await build_knowledge_context("algo")

    assert context == "NINGUNO -- no se encontro informacion verificada sobre este tema."
