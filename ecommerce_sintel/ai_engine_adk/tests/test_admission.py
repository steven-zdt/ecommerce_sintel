"""
HARDENING F13 (2026-09-24) -- control de admision de turnos (C2).
ESCRITO PERO NO EJECUTADO (regla vigente: el usuario ejecuta los tests a mano). Deterministas, sin LLM ni red.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

import admission
import config as ai_config


async def test_desactivado_no_limita_ni_espera():
    gate = admission.Admission(0, 5, 1)
    assert not gate.enabled
    assert [await gate.acquire() for _ in range(50)] == [0] * 50
    gate.release()  # no-op


async def test_respeta_el_maximo_concurrente_y_libera_en_orden():
    gate = admission.Admission(2, 5, 5)
    await gate.acquire()
    await gate.acquire()
    third = asyncio.ensure_future(gate.acquire())
    await asyncio.sleep(0.05)
    assert gate.active == 2 and gate.waiting == 1 and not third.done()
    gate.release()
    assert await asyncio.wait_for(third, 1) >= 0
    assert gate.active == 2 and gate.waiting == 0


async def test_cola_llena_rechaza_de_inmediato():
    gate = admission.Admission(1, 1, 5)
    await gate.acquire()
    waiter = asyncio.ensure_future(gate.acquire())  # ocupa el unico lugar de la cola
    await asyncio.sleep(0.05)
    with pytest.raises(admission.Rejected) as exc:
        await gate.acquire()
    assert exc.value.reason == "queue_full"
    waiter.cancel()


async def test_espera_vencida_rechaza_con_queue_timeout():
    gate = admission.Admission(1, 5, 0.05)
    await gate.acquire()
    with pytest.raises(admission.Rejected) as exc:
        await gate.acquire()
    assert exc.value.reason == "queue_timeout" and exc.value.waited_ms >= 40 and gate.waiting == 0


async def test_release_sin_acquire_no_rompe_el_contador():
    gate = admission.Admission(1, 1, 1)
    gate.release()
    assert gate.active == 0
    await gate.acquire()
    gate.release()
    gate.release()
    assert gate.active == 0


def test_los_defaults_dejan_la_admision_desactivada():
    assert ai_config.AI_MAX_CONCURRENT_TURNS == 0


def test_chat_responde_degradado_inmediato_cuando_no_hay_cupo(monkeypatch):
    import main
    from auth import get_validated_token, require_service_token

    async def nunca(**_kw):  # si se llegara al modelo, el test fallaria por no haber sido rechazado antes
        raise AssertionError("no debio llegar al workflow")

    class Llena:
        enabled = True

        async def acquire(self):
            raise admission.Rejected("queue_full")

        def release(self):
            raise AssertionError("no se admitio: no hay nada que liberar")

        def snapshot(self):
            return {}

    monkeypatch.setattr(main, "run_sintel_turn", nunca)
    monkeypatch.setattr(main, "_admission", Llena())
    main.app.dependency_overrides[get_validated_token] = lambda: "jwt"
    main.app.dependency_overrides[require_service_token] = lambda: None
    try:
        r = TestClient(main.app).post("/chat", json={"message": "hola", "conversation_id": "c1"})
    finally:
        main.app.dependency_overrides.clear()
    body = r.json()
    assert r.status_code == 200 and body["metrics"]["queue_rejected"] is True and body["metrics"]["queue_reason"] == "queue_full"
    assert "agente humano" in body["response"] and body["tool_calls"] == []


def test_el_cupo_se_libera_aunque_el_turno_falle(monkeypatch):
    import main
    from auth import get_validated_token, require_service_token

    events = []

    class Gate:
        enabled = True

        async def acquire(self):
            events.append("acquire")
            return 7

        def release(self):
            events.append("release")

        def snapshot(self):
            return {}

    async def falla(**_kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "run_sintel_turn", falla)
    monkeypatch.setattr(main, "_admission", Gate())
    main.app.dependency_overrides[get_validated_token] = lambda: "jwt"
    main.app.dependency_overrides[require_service_token] = lambda: None
    try:
        r = TestClient(main.app).post("/chat", json={"message": "hola"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.json()["metrics"]["engine_unavailable"] is True and events == ["acquire", "release"]
