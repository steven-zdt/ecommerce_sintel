"""
retrieve_knowledge_for_chat (retrievers.py) -- FASE 3 (mision de
simplificacion arquitectonica, 2026-09-14): ya no habla con ChromaDB
directo, delega en el endpoint interno de Django `ai_knowledge`
(POST /internal/ai/knowledge/retrieve/, RetrievalService sobre pgvector).

El invariante de gobernanza real (nunca devolver contenido interno de
ingenieria a un cliente, ver AI_SUPPORT_SCOPE.md seccion 6 -- hallazgo
original: una pregunta de "horario de atencion" recupero un fragmento de
arquitectura interna y el LLM fabrico una respuesta) ahora se aplica y se
prueba del lado Django -- ver ai_knowledge/tests.py::RetrievalVisibilityTests.
Esta suite cubre el contrato propio de ai_engine: como arma la llamada HTTP,
como interpreta la respuesta, y que se degrada con gracia (nunca lanza) si
Django no responde. httpx.AsyncClient se mockea (no hay respx instalado en
este entorno, mismo criterio que tests/test_dynamic_llm_config.py).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from retrievers import retrieve_knowledge_for_chat


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


async def test_retrieve_knowledge_for_chat_devuelve_los_chunks_de_django():
    payload = {"chunks": [
        {"content": "La garantia de renting es de 12 meses.", "source": "manual",
         "app_name": "renting", "title": "FAQ garantia", "updated_at": "2026-09-14T00:00:00Z"},
    ]}
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_response(200, payload))):
        docs = await retrieve_knowledge_for_chat("como funciona la garantia del renting", apps=["renting"])
    assert len(docs) == 1
    assert docs[0]["content"] == "La garantia de renting es de 12 meses."


async def test_retrieve_knowledge_for_chat_envia_query_y_apps_detectados():
    mock_post = AsyncMock(return_value=_mock_response(200, {"chunks": []}))
    with patch("httpx.AsyncClient.post", new=mock_post):
        await retrieve_knowledge_for_chat("quiero alquilar un equipo de renting")
    assert mock_post.called
    body = mock_post.call_args.kwargs["json"]
    assert body["query"] == "quiero alquilar un equipo de renting"
    assert "renting" in body["app_names"]


async def test_retrieve_knowledge_for_chat_vacio_si_django_no_responde_200():
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_response(500, {}))):
        docs = await retrieve_knowledge_for_chat("cualquier pregunta", apps=["renting"])
    assert docs == []


async def test_retrieve_knowledge_for_chat_vacio_si_django_inalcanzable():
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=httpx.ConnectError("connection refused"))):
        docs = await retrieve_knowledge_for_chat("cualquier pregunta", apps=["renting"])
    assert docs == []
