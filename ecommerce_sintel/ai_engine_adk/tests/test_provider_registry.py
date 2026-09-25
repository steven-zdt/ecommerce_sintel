"""
PLAN_LLMDINAMICO FASE 4 (2026-09-25) -- resolver de proveedores desde el Registry de Django. Escritos, no ejecutados por
instruccion del usuario. Sin red ni LLM: `_fetch` y el factory de LiteLlm se simulan.
"""
import asyncio

import pytest

import config as ai_config
import model_runtime
import provider_registry as reg
from model_runtime import FallbackLiteLlm, MemoryStore, ProviderBreaker, llm_params_for_entry

PAYLOAD = {
    "channel": "support_chat", "enabled": True,
    "primary": {"name": "ollama", "kind": "ollama-nativo", "base_url": "http://ollama:11434", "model": "qwen3.5:9b",
                "api_key_env": None, "api_key_value": None},
    "fallbacks": [{"name": "cloud", "kind": "openai-compatible", "base_url": "https://x.example/v1", "model": "m2",
                   "api_key_env": None, "api_key_value": "SECRETO-REGISTRY"}],
}


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    reg.reset_cache()
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_ENABLED", True)
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_TTL_SECONDS", 15)
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_STALE_SECONDS", 300)
    yield
    reg.reset_cache()


def test_parse_payload_orden_primario_y_fallbacks():
    entries = reg.parse_registry_payload(PAYLOAD)
    assert [e["name"] for e in entries] == ["ollama", "cloud"]
    assert entries[1]["api_key_value"] == "SECRETO-REGISTRY"


def test_parse_payload_canal_apagado_o_sin_primario_es_none():
    assert reg.parse_registry_payload({"enabled": False, "primary": PAYLOAD["primary"], "fallbacks": []}) is None
    assert reg.parse_registry_payload({"enabled": True, "primary": None, "fallbacks": []}) is None


def test_parse_payload_descarta_kind_invalido():
    bad = {"enabled": True, "primary": {"name": "x", "kind": "gemini-magico", "model": "m"}, "fallbacks": []}
    assert reg.parse_registry_payload(bad) is None


def test_params_usan_api_key_del_registry():
    entry = reg.parse_registry_payload(PAYLOAD)[1]
    assert llm_params_for_entry(entry)["api_key"] == "SECRETO-REGISTRY"
    assert llm_params_for_entry({**entry, "api_key_value": None})["api_key"] == "not-needed"


def test_apagado_por_defecto_no_consulta(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_ENABLED", False)

    async def boom():
        raise AssertionError("no debe consultar Django con el flag apagado")

    monkeypatch.setattr(reg, "_fetch", boom)
    assert asyncio.run(reg.get_registry_entries()) is None


def test_cache_ttl_una_sola_consulta(monkeypatch):
    calls = []

    async def fake():
        calls.append(1)
        return "ok", reg.parse_registry_payload(PAYLOAD)

    monkeypatch.setattr(reg, "_fetch", fake)

    async def run():
        await reg.get_registry_entries()
        return await reg.get_registry_entries()

    assert len(asyncio.run(run())) == 2
    assert len(calls) == 1


def test_error_de_django_conserva_ultima_cadena_buena(monkeypatch):
    answers = iter([("ok", reg.parse_registry_payload(PAYLOAD)), ("error", None)])

    async def fake():
        return next(answers)

    monkeypatch.setattr(reg, "_fetch", fake)

    async def run():
        first = await reg.get_registry_entries()
        reg._state["fetched_at"] = 0.0  # fuerza expirar el TTL
        second = await reg.get_registry_entries()
        return first, second

    first, second = asyncio.run(run())
    assert second == first and second is not None


def test_error_sin_cadena_previa_cae_a_none(monkeypatch):
    async def fake():
        return "error", None

    monkeypatch.setattr(reg, "_fetch", fake)
    assert asyncio.run(reg.get_registry_entries()) is None


def test_respuesta_vacia_de_django_vuelve_a_local_model_chain(monkeypatch):
    answers = iter([("ok", reg.parse_registry_payload(PAYLOAD)), ("empty", None)])

    async def fake():
        return next(answers)

    monkeypatch.setattr(reg, "_fetch", fake)

    async def run():
        await reg.get_registry_entries()
        reg._state["fetched_at"] = 0.0
        return await reg.get_registry_entries()

    assert asyncio.run(run()) is None


class _Inner:
    def __init__(self, params):
        self.params = params


def _model(use_registry):
    env_entries = [{"name": "env", "kind": "ollama-nativo", "base_url": "http://e:11434", "model": "envm", "api_key_env": None}]
    return FallbackLiteLlm(env_entries, timeout=5, breaker=ProviderBreaker(store=MemoryStore()),
                           inner_factory=_Inner, use_registry=use_registry)


def test_resolve_chain_usa_registry_y_hace_snapshot_por_turno(monkeypatch):
    seq = [reg.parse_registry_payload(PAYLOAD), [{"name": "otro", "kind": "ollama-nativo", "base_url": "http://o", "model": "z",
                                                   "api_key_env": None, "api_key_value": None}]]

    async def fake_get():
        return seq.pop(0)

    monkeypatch.setattr(reg, "get_registry_entries", fake_get)
    model = _model(True)

    async def run():
        model_runtime.begin_turn_trace()
        first = await model._resolve_chain()
        again = await model._resolve_chain()   # mismo turno: NO vuelve a consultar
        model_runtime.begin_turn_trace()
        nxt = await model._resolve_chain()     # turno nuevo: toma el cambio
        return first, again, nxt

    first, again, nxt = asyncio.run(run())
    assert [e["name"] for e, _ in first] == ["ollama", "cloud"]
    assert again is first
    assert [e["name"] for e, _ in nxt] == ["otro"]


def test_resolve_chain_sin_flag_usa_local_model_chain():
    async def run():
        model_runtime.begin_turn_trace()
        return await _model(False)._resolve_chain()

    chain = asyncio.run(run())
    assert [e["name"] for e, _ in chain] == ["env"]


def test_snapshot_no_se_filtra_entre_instancias():
    async def run():
        model_runtime.begin_turn_trace()
        a = await _model(False)._resolve_chain()
        b = _model(False)
        return a, await b._resolve_chain()

    a, b = asyncio.run(run())
    assert a is not b  # cada instancia arma su propia cadena


def test_api_key_del_registry_no_entra_a_la_traza():
    trace = model_runtime.begin_turn_trace()
    assert "SECRETO-REGISTRY" not in repr(trace)


#  F3: la URL de la BD no es de confianza para el ADK
def test_entrada_con_url_de_metadatos_se_descarta():
    payload = {"enabled": True, "fallbacks": [], "primary": {
        "name": "malo", "kind": "openai-compatible", "base_url": "http://169.254.169.254/v1", "model": "m"}}
    assert reg.parse_registry_payload(payload) is None


def test_primario_inseguro_ignora_todo_el_registro_sin_promover_un_fallback():
    payload = dict(PAYLOAD, primary={"name": "malo", "kind": "ollama-nativo", "base_url": "http://user:pw@x:11434", "model": "m"})
    assert reg.parse_registry_payload(payload) is None  # usa LOCAL_MODEL_CHAIN; "cloud" NO pasa a ser primario


def test_fallback_inseguro_se_descarta_pero_el_primario_sigue():
    payload = dict(PAYLOAD, fallbacks=[{"name": "malo", "kind": "openai-compatible", "base_url": "http://169.254.169.254/v1", "model": "m"}])
    assert [e["name"] for e in reg.parse_registry_payload(payload)] == ["ollama"]


@pytest.mark.parametrize("url", ["http://localhost:1234/v1", "http://127.0.0.1:1234/v1", "http://[::1]:11434"])
def test_url_loopback_se_descarta_en_el_adk(url):
    payload = {"enabled": True, "fallbacks": [], "primary": {"name": "lm", "kind": "openai-compatible", "base_url": url, "model": "m"}}
    assert reg.parse_registry_payload(payload) is None
    ok = dict(payload, primary=dict(payload["primary"], base_url="http://host.docker.internal:1234/v1"))
    assert [e["name"] for e in reg.parse_registry_payload(ok)] == ["lm"]


def test_fetch_envia_el_token_de_servicio(monkeypatch):
    seen = {}

    class _Resp:
        status_code = 200

        def json(self):
            return PAYLOAD

    class _Client:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def get(self, url, params=None, headers=None):
            seen["headers"] = headers
            return _Resp()

    monkeypatch.setattr(reg.httpx, "AsyncClient", _Client)
    monkeypatch.setattr(ai_config, "AI_SERVICE_TOKEN", "tok-interno", raising=False)
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_TIMEOUT_SECONDS", 3)
    status, entries = asyncio.run(reg._fetch())
    assert status == "ok" and len(entries) == 2
    assert seen["headers"]["X-AI-Service-Token"] == "tok-interno"


def test_las_dos_copias_del_guard_ssrf_no_divergen():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    if not (root / "ai_provider" / "services" / "url_guard.py").exists():
        pytest.skip("la imagen del ADK no incluye ai_provider/; se compara desde el host (scripts/verify/run_pending_tests.sh)")

    def body(p):
        text = (root / p).read_text(encoding="utf-8")
        return text[text.index("import ipaddress"):]

    assert body("ai_engine_adk/url_guard.py") == body("ai_provider/services/url_guard.py")
