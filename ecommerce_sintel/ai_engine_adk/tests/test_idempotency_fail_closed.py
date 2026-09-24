"""
HARDENING F14 (2026-09-24) -- idempotencia fail-closed (C2) y contratos de degradacion.
ESCRITO PERO NO EJECUTADO (regla vigente: el usuario ejecuta los tests a mano). Deterministas, sin Redis ni LLM.
"""
import inspect

import pytest

import config as ai_config
import idempotency


class _Boom:
    """Cliente Redis falso que siempre falla."""

    async def set(self, *a, **k):
        raise ConnectionError("redis caido")

    async def get(self, *a, **k):
        raise ConnectionError("redis caido")

    async def aclose(self):
        return None


async def test_por_defecto_fail_open_ejecuta_sin_deduplicar(monkeypatch):
    monkeypatch.setattr(idempotency, "_client", lambda: _Boom())
    monkeypatch.setattr(ai_config, "AI_TOOL_IDEMPOTENCY_FAIL_CLOSED", False)
    assert await idempotency.begin("k") == (None, True)


async def test_fail_closed_no_deja_ejecutar_sin_poder_deduplicar(monkeypatch):
    monkeypatch.setattr(idempotency, "_client", lambda: _Boom())
    monkeypatch.setattr(ai_config, "AI_TOOL_IDEMPOTENCY_FAIL_CLOSED", True)
    assert await idempotency.begin("k") == (idempotency.UNAVAILABLE, False)


def test_el_default_conserva_el_comportamiento_anterior():
    assert ai_config.AI_TOOL_IDEMPOTENCY_FAIL_CLOSED is False


def test_el_adapter_responde_503_con_handoff_cuando_el_almacen_no_esta():
    import sintel_adapter

    src = inspect.getsource(sintel_adapter.adapt_sintel_tool)
    assert "idempotency.UNAVAILABLE" in src and '"status_code": 503' in src and "idempotency_unavailable" in src


async def test_los_fallos_de_finish_y_abort_nunca_lanzan(monkeypatch):
    monkeypatch.setattr(idempotency, "_client", lambda: _Boom())
    await idempotency.finish("k", {"ok": True})
    await idempotency.abort("k")


def test_la_clave_pendiente_expira_sola_para_no_bloquear_reintentos_tras_un_reinicio():
    assert idempotency._PENDING_TTL_SECONDS <= 120


def test_el_chat_degrada_sin_5xx_cuando_el_workflow_falla(monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from auth import get_validated_token, require_service_token

    async def falla(**_kw):
        raise ConnectionError("db caida")

    monkeypatch.setattr(main, "run_sintel_turn", falla)
    main.app.dependency_overrides[get_validated_token] = lambda: "jwt"
    main.app.dependency_overrides[require_service_token] = lambda: None
    try:
        r = TestClient(main.app).post("/chat", json={"message": "hola"})
    finally:
        main.app.dependency_overrides.clear()
    body = r.json()
    assert r.status_code == 200 and body["metrics"]["engine_unavailable"] is True and "agente humano" in body["response"]
    assert "db caida" not in r.text and "ConnectionError" not in r.text  # sin fuga del error interno


def test_el_identity_error_falla_cerrado_con_401(monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from auth import get_validated_token, require_service_token
    from sintel_root_workflow import IdentityResolutionError

    async def sin_identidad(**_kw):
        raise IdentityResolutionError("django caido")

    monkeypatch.setattr(main, "run_sintel_turn", sin_identidad)
    main.app.dependency_overrides[get_validated_token] = lambda: "jwt"
    main.app.dependency_overrides[require_service_token] = lambda: None
    try:
        r = TestClient(main.app).post("/chat", json={"message": "hola"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 401
