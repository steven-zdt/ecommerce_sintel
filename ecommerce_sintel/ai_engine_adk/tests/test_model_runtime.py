"""
HARDENING F3 (2026-09-24) -- C1 (presupuesto de turno) y C2 (fallback + circuit breaker por proveedor).

Sin red, sin Redis, sin LLM: MemoryStore con reloj inyectado, modelos internos falsos y una app FastAPI real
(`main.app`) con las dependencias de auth anuladas. Propuesta: ai_engine_adk/.AGENT/HARDENING_F3_PROPOSAL_2026-09-24.md.
"""
import asyncio
import logging

import pytest
from fastapi.testclient import TestClient

import config as ai_config
import model_runtime as mr
from model_runtime import (
    CLOSED, HALF_OPEN, OPEN, FallbackLiteLlm, MemoryStore, ModelUnavailableError, ProviderBreaker,
    begin_turn_trace,
)

ENTRIES = [
    {"name": "ollama", "kind": "ollama-nativo", "base_url": "http://sintel_ollama:11434", "model": "qwen3.5:9b", "api_key_env": None},
    {"name": "lmstudio", "kind": "openai-compatible", "base_url": "http://host.docker.internal:1234/v1", "model": "qwen/qwen3.5-9b", "api_key_env": None},
]


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class FakeInner:
    """Modelo interno falso: emite `chunks` o lanza `error`; cuenta llamadas."""

    def __init__(self, label, chunks=("ok",), error=None, fail_after=0):
        self.label, self.chunks, self.error, self.fail_after, self.calls = label, chunks, error, fail_after, 0

    async def generate_content_async(self, llm_request, stream=False):
        self.calls += 1
        if self.error and not self.fail_after:
            raise self.error
        for i, c in enumerate(self.chunks):
            if self.error and i == self.fail_after:
                raise self.error
            yield c


def make(monkeypatch, inners, entries=ENTRIES, failures=3, window=60, open_seconds=60, clock=None):
    monkeypatch.setattr(ai_config, "AI_BREAKER_ENABLED", True)
    clock = clock or Clock()
    breaker = ProviderBreaker(store=MemoryStore(clock=clock), failures=failures, window=window, open_seconds=open_seconds)
    it = iter(inners)
    model = FallbackLiteLlm(entries, timeout=5, breaker=breaker, inner_factory=lambda params: next(it))
    return model, breaker, clock


async def collect(model):
    return [r async for r in model.generate_content_async(object())]


#  Breaker 
async def test_breaker_abre_tras_n_fallos_y_bloquea():
    clock = Clock()
    b = ProviderBreaker(store=MemoryStore(clock=clock), failures=3, window=60, open_seconds=60)
    for _ in range(2):
        await b.record_failure("ollama")
        assert (await b.allow("ollama"))[0] is True
    await b.record_failure("ollama")
    assert await b.state("ollama") == OPEN
    assert (await b.allow("ollama")) == (False, OPEN)


async def test_breaker_ventana_los_fallos_viejos_no_cuentan():
    clock = Clock()
    b = ProviderBreaker(store=MemoryStore(clock=clock), failures=3, window=60, open_seconds=60)
    await b.record_failure("ollama")
    await b.record_failure("ollama")
    clock.t += 61  # la ventana expira
    await b.record_failure("ollama")
    assert await b.state("ollama") == CLOSED


async def test_breaker_half_open_deja_pasar_una_sola_prueba():
    clock = Clock()
    b = ProviderBreaker(store=MemoryStore(clock=clock), failures=1, window=60, open_seconds=60)
    await b.record_failure("ollama")
    assert await b.state("ollama") == OPEN
    clock.t += 61
    assert await b.state("ollama") == HALF_OPEN
    assert (await b.allow("ollama")) == (True, HALF_OPEN)   # la prueba
    assert (await b.allow("ollama")) == (False, HALF_OPEN)  # el resto espera


async def test_breaker_half_open_exito_cierra_y_fallo_reabre():
    clock = Clock()
    b = ProviderBreaker(store=MemoryStore(clock=clock), failures=1, window=60, open_seconds=60)
    await b.record_failure("ollama")
    clock.t += 61
    await b.allow("ollama")
    await b.record_success("ollama")
    assert await b.state("ollama") == CLOSED
    await b.record_failure("ollama")            # vuelve a abrir (failures=1)
    clock.t += 61
    await b.allow("ollama")
    await b.record_failure("ollama")            # la prueba falla => OPEN otra vez
    assert await b.state("ollama") == OPEN


#  FallbackLiteLlm 
async def test_primario_ok_no_usa_fallback(monkeypatch):
    p, f = FakeInner("p"), FakeInner("f")
    model, _, _ = make(monkeypatch, [p, f])
    trace = begin_turn_trace()
    assert await collect(model) == ["ok"]
    assert (p.calls, f.calls) == (1, 0)
    assert trace["provider"] == "ollama" and trace["fallback_used"] is False and trace["model"] == "qwen3.5:9b"


async def test_primario_falla_usa_fallback_y_lo_registra(monkeypatch):
    p, f = FakeInner("p", error=ConnectionError("refused")), FakeInner("f", chunks=("del-fallback",))
    model, _, _ = make(monkeypatch, [p, f])
    trace = begin_turn_trace()
    assert await collect(model) == ["del-fallback"]
    assert trace["provider"] == "lmstudio" and trace["fallback_used"] is True
    assert "ConnectionError" in trace["fallback_reason"] and "ollama" in trace["fallback_reason"]


async def test_breaker_abierto_salta_al_fallback_sin_llamar_al_primario(monkeypatch):
    p, f = FakeInner("p"), FakeInner("f", chunks=("fb",))
    model, breaker, _ = make(monkeypatch, [p, f], failures=1)
    await breaker.record_failure("ollama")
    trace = begin_turn_trace()
    assert await collect(model) == ["fb"]
    assert p.calls == 0 and trace["fallback_used"] is True
    assert trace["fallback_reason"].startswith("breaker_open")


async def test_todos_fallan_lanza_model_unavailable(monkeypatch):
    p, f = FakeInner("p", error=TimeoutError()), FakeInner("f", error=ConnectionError())
    model, _, _ = make(monkeypatch, [p, f])
    with pytest.raises(ModelUnavailableError):
        await collect(model)
    assert (p.calls, f.calls) == (1, 1)  # exactamente un intento por proveedor


async def test_presupuesto_de_reintentos_nunca_supera_dos_intentos(monkeypatch):
    entries = ENTRIES + [{"name": "extra", "kind": "openai-compatible", "base_url": "http://x/v1", "model": "m", "api_key_env": None}]
    a, b_, c = FakeInner("a", error=TimeoutError()), FakeInner("b", error=TimeoutError()), FakeInner("c")
    model, _, _ = make(monkeypatch, [a, b_, c], entries=entries)
    with pytest.raises(ModelUnavailableError):
        await collect(model)
    assert c.calls == 0  # el 3er proveedor no se prueba: maximo primario + 1 fallback


async def test_cadena_de_un_solo_proveedor_con_breaker_abierto_falla_rapido(monkeypatch):
    only = FakeInner("solo")
    model, breaker, _ = make(monkeypatch, [only], entries=ENTRIES[:1], failures=1)
    await breaker.record_failure("ollama")
    with pytest.raises(ModelUnavailableError):
        await collect(model)
    assert only.calls == 0


async def test_fallo_a_mitad_de_respuesta_no_cambia_de_proveedor(monkeypatch):
    p = FakeInner("p", chunks=("a", "b"), error=ConnectionError("cortado"), fail_after=1)
    f = FakeInner("f")
    model, _, _ = make(monkeypatch, [p, f])
    got = []
    with pytest.raises(ConnectionError):
        async for r in model.generate_content_async(object()):
            got.append(r)
    assert got == ["a"] and f.calls == 0  # no se mezcla una respuesta parcial con otro modelo


async def test_traza_no_contiene_prompts(monkeypatch):
    p = FakeInner("p")
    model, _, _ = make(monkeypatch, [p, FakeInner("f")])
    trace = begin_turn_trace()
    await collect(model)
    assert set(trace) == {"provider", "model", "fallback_used", "fallback_reason", "breaker_state", "attempts"}


async def test_breaker_deshabilitado_no_consulta_estado(monkeypatch):
    p, f = FakeInner("p"), FakeInner("f")
    model, breaker, _ = make(monkeypatch, [p, f], failures=1)
    await breaker.record_failure("ollama")
    monkeypatch.setattr(ai_config, "AI_BREAKER_ENABLED", False)
    assert await collect(model) == ["ok"]
    assert p.calls == 1


async def test_logs_de_fallo_sin_secretos(monkeypatch, caplog):
    p, f = FakeInner("p", error=ConnectionError("password=SECRETO")), FakeInner("f")
    model, _, _ = make(monkeypatch, [p, f])
    with caplog.at_level(logging.INFO, logger="model_runtime"):
        await collect(model)
    assert "provider_failed" in caplog.text
    assert "SECRETO" not in caplog.text  # solo el nombre de la excepcion, nunca su mensaje


#  C1: presupuesto de turno 
def test_max_output_tokens_por_superficie(monkeypatch):
    import sintel_root_workflow as wf

    monkeypatch.setattr(ai_config, "AI_SUPPORT_MAX_OUTPUT_TOKENS", 111)
    monkeypatch.setattr(ai_config, "AI_ADMIN_MAX_OUTPUT_TOKENS", 222)
    assert wf._max_output_tokens_for("SupportAgent") == 111
    assert wf._max_output_tokens_for("CatalogAgent") == 222


def test_max_llm_calls_configurable(monkeypatch):
    import sintel_root_workflow as wf

    monkeypatch.setattr(ai_config, "AI_TURN_MAX_LLM_CALLS", 3)
    assert wf._turn_max_llm_calls() == 3


def _chat_client(monkeypatch, run_turn):
    import main
    from auth import get_validated_token, require_service_token

    monkeypatch.setattr(main, "run_sintel_turn", run_turn)
    main.app.dependency_overrides[get_validated_token] = lambda: "jwt"
    main.app.dependency_overrides[require_service_token] = lambda: None
    return TestClient(main.app), main


def test_timeout_total_del_turno_responde_handoff_seguro(monkeypatch):
    async def lento(**_kw):
        await asyncio.sleep(5)

    monkeypatch.setattr(ai_config, "AI_TURN_MAX_SECONDS", 0.05)
    client, main = _chat_client(monkeypatch, lento)
    try:
        r = client.post("/chat", json={"message": "hola", "conversation_id": "c1"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200
    body = r.json()
    assert body["metrics"] == {"engine_unavailable": True, "turn_timeout": True}
    assert "agente humano" in body["response"] and body["tool_calls"] == []


def test_model_unavailable_termina_en_respuesta_degradada(monkeypatch):
    async def sin_modelo(**_kw):
        raise ModelUnavailableError("todos caidos")

    client, main = _chat_client(monkeypatch, sin_modelo)
    try:
        r = client.post("/chat", json={"message": "hola"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.status_code == 200 and r.json()["metrics"]["engine_unavailable"] is True


def test_turno_dentro_del_limite_no_se_corta(monkeypatch):
    async def rapido(**_kw):
        return {"conversation_id": "c1", "intent": "x", "agent": "SupportAgent", "tool_calls": [], "tool_results": [],
                "needs_confirmation": False, "confirmation": None, "response": "hola!", "metrics": {}}

    monkeypatch.setattr(ai_config, "AI_TURN_MAX_SECONDS", 5)
    client, main = _chat_client(monkeypatch, rapido)
    try:
        r = client.post("/chat", json={"message": "hola", "conversation_id": "c1"})
    finally:
        main.app.dependency_overrides.clear()
    assert r.json()["response"] == "hola!"
