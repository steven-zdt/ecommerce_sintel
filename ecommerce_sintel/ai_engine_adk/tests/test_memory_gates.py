"""
HARDENING F7/C6 (2026-09-24) -- compuertas de la extraccion de memoria en el ADK. Propuesta: ai_engine_adk/.AGENT/HARDENING_F7_PROPOSAL_2026-09-24.md.
Sin red ni LLM.
"""
import inspect
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import customer_memory_adapter as cma
import sintel_root_workflow as wf


@pytest.mark.parametrize("kwargs,expected", [
    (dict(is_resume=False, final_text="hola", source="customer", injection_flags={}), True),
    (dict(is_resume=True, final_text="hola", source="customer", injection_flags={}), False),          # resume de confirmacion
    (dict(is_resume=False, final_text="", source="customer", injection_flags={}), False),            # sin respuesta
    (dict(is_resume=False, final_text="hola", source="admin", injection_flags={}), False),           # la memoria es del CLIENTE
    (dict(is_resume=False, final_text="hola", source="customer", injection_flags={"user": ["role_impersonation"]}), False),  # F5: fail-closed
    (dict(is_resume=False, final_text="hola", source="customer", injection_flags={"rag": ["override_instructions"]}), True),  # un chunk RAG marcado no impide extraer del mensaje del usuario
])
def test_should_extract_memory(kwargs, expected):
    assert wf.should_extract_memory(**kwargs) is expected


def test_el_workflow_usa_la_compuerta_y_pasa_el_canal():
    src = inspect.getsource(wf.run_sintel_turn)
    assert "should_extract_memory(" in src
    assert "channel=channel" in src


def test_la_extraccion_solo_lee_el_mensaje_del_usuario():
    """El prompt de extraccion se arma UNICAMENTE con `message` (nunca conocimiento RAG ni salidas de Tools)."""
    src = inspect.getsource(cma.extract_and_store_memory)
    assert "_EXTRACTION_PROMPT_TEMPLATE.format(message=message" in src
    assert "knowledge" not in src.lower() and "tool_result" not in src.lower()


async def test_el_canal_viaja_hasta_el_store_de_django():
    completion = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="contact_preference|prefiere WhatsApp"))])
    resp = MagicMock(status_code=201)
    resp.json.return_value = {"stored": True}
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(return_value=resp)
    with patch("litellm.acompletion", new=AsyncMock(return_value=completion)), patch("httpx.AsyncClient", return_value=client):
        out = await cma.extract_and_store_memory(message="prefiero whatsapp", token="t", conversation_id="c1", model="m",
                                                 channel="whatsapp")
    assert out == "contact_preference"
    assert client.post.call_args.kwargs["json"]["channel"] == "whatsapp"


def _client(monkeypatch):
    import main
    from auth import get_validated_token, require_service_token

    seen = {}

    async def fake_turn(**kw):
        seen.update(kw)
        return {"conversation_id": "c", "intent": "x", "agent": "SupportAgent", "tool_calls": [], "tool_results": [],
                "needs_confirmation": False, "confirmation": None, "response": "ok", "metrics": {}}

    monkeypatch.setattr(main, "run_sintel_turn", fake_turn)
    main.app.dependency_overrides[get_validated_token] = lambda: "jwt"
    main.app.dependency_overrides[require_service_token] = lambda: None
    return TestClient(main.app), main, seen


@pytest.mark.parametrize("sent,expected", [("whatsapp", "whatsapp"), ("web", "web"), ("hackeado", "unknown"), (None, "web")])
def test_main_normaliza_el_canal(monkeypatch, sent, expected):
    client, main, seen = _client(monkeypatch)
    try:
        body = {"message": "hola"}
        if sent is not None:
            body["channel"] = sent
        assert client.post("/chat", json=body).status_code == 200
    finally:
        main.app.dependency_overrides.clear()
    assert seen["channel"] == expected
