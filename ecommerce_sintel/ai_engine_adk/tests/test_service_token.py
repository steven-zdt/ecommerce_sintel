"""
HARDENING F2 (2026-09-24) -- autenticacion servicio-a-servicio Django -> ADK (`X-AI-Service-Token`).

Plan: PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md sec. 6;
propuesta: ai_engine_adk/.AGENT/HARDENING_F2_PROPOSAL_2026-09-24.md.

Se prueba la dependencia `auth.require_service_token` aislada (sin LLM, sin red, sin JWT real) en una
app FastAPI minima, mas la conexion real en `main.app` (que la dependencia esta declarada en /chat y
que /health sigue sin auth).
"""
import logging

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

import auth
import config as ai_config

SECRET = "s3cr3t-service-token-de-prueba-0123456789"
PREVIOUS = "token-anterior-de-prueba-9876543210"


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN", SECRET)
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN_PREVIOUS", "")
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN_REQUIRED", True)
    app = FastAPI()

    @app.post("/protegido", dependencies=[Depends(auth.require_service_token)])
    async def protegido():
        return {"ok": True}

    return TestClient(app)


def test_sin_header_401_cuando_requerido(client):
    r = client.post("/protegido")
    assert r.status_code == 401
    assert r.json()["detail"] == "Servicio no autorizado."


def test_header_incorrecto_401_mismo_mensaje(client):
    r = client.post("/protegido", headers={"X-AI-Service-Token": "otro"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Servicio no autorizado."  # no revela si falto o fue incorrecto


def test_header_correcto_pasa(client):
    assert client.post("/protegido", headers={"X-AI-Service-Token": SECRET}).status_code == 200


def test_token_anterior_valido_durante_rotacion(client, monkeypatch):
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN_PREVIOUS", PREVIOUS)
    assert client.post("/protegido", headers={"X-AI-Service-Token": PREVIOUS}).status_code == 200
    assert client.post("/protegido", headers={"X-AI-Service-Token": SECRET}).status_code == 200


def test_requerido_sin_token_configurado_rechaza_todo(client, monkeypatch):
    """fail-closed: REQUIRED=true pero AI_SERVICE_TOKEN vacio => nadie pasa (incluido un header vacio)."""
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN", "")
    assert client.post("/protegido", headers={"X-AI-Service-Token": ""}).status_code == 401
    assert client.post("/protegido", headers={"X-AI-Service-Token": "x"}).status_code == 401


def test_modo_monitor_deja_pasar_pero_avisa(client, monkeypatch, caplog):
    """REQUIRED=false (fase de despliegue): no corta el chat, pero deja rastro sin valores del token."""
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN_REQUIRED", False)
    with caplog.at_level(logging.WARNING, logger="auth"):
        r = client.post("/protegido", headers={"X-AI-Service-Token": "incorrecto-secreto"})
    assert r.status_code == 200
    assert "ai_service_token_missing_or_invalid" in caplog.text
    assert "incorrecto-secreto" not in caplog.text and SECRET not in caplog.text


def test_token_no_aparece_en_logs_al_rechazar(client, caplog):
    with caplog.at_level(logging.WARNING, logger="auth"):
        client.post("/protegido", headers={"X-AI-Service-Token": "valor-sensible-enviado"})
    assert "ai_service_token_rejected" in caplog.text
    assert "valor-sensible-enviado" not in caplog.text and SECRET not in caplog.text


def test_main_chat_tiene_la_dependencia_y_health_no():
    """Cableado real: /chat exige el secreto de servicio; /health sigue abierto (healthcheck de Docker)."""
    from main import app

    chat = next(r for r in app.routes if getattr(r, "path", "") == "/chat")
    health = next(r for r in app.routes if getattr(r, "path", "") == "/health")
    assert any(d.call is auth.require_service_token for d in chat.dependant.dependencies)
    assert not any(d.call is auth.require_service_token for d in health.dependant.dependencies)


def test_main_chat_sin_header_401_antes_de_validar_jwt(monkeypatch):
    """El secreto de servicio se evalua ANTES que el JWT: sin header no se llega ni a decodificar el token."""
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN", SECRET)
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN_REQUIRED", True)
    from main import app

    r = TestClient(app).post("/chat", json={"message": "hola"}, headers={"Authorization": "Bearer no-importa"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Servicio no autorizado."
