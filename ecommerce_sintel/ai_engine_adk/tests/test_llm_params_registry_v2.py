"""
PLAN_LLMDINAMICO (2026-09-25) -- parametros litellm por entrada (gemini, auth por cabecera, generacion, TLS, timeout), primario vigente para grounding/memoria
y traza con provider_id/config_version. Escritos, no ejecutados por instruccion del usuario (verificados con un script contra el Django dev). Sin red ni LLM.
"""
import asyncio

import pytest

import config as ai_config
import model_runtime as mr
import provider_registry as reg
from model_chain import VALID_KINDS, parse_local_model_chain


def test_gemini_es_kind_valido_y_sus_params():
    assert "gemini" in VALID_KINDS
    assert mr.llm_params_for_entry({"kind": "gemini", "model": "gemini-x", "api_key_value": "K"}) == {"model": "gemini/gemini-x", "api_key": "K"}
    assert mr.llm_params_for_entry({"kind": "gemini", "model": "gemini-x"}) == {"model": "gemini/gemini-x"}


def test_openai_bearer_header_y_none():
    base = {"kind": "openai-compatible", "model": "m", "base_url": "http://h/v1", "api_key_value": "K"}
    assert mr.llm_params_for_entry(base)["api_key"] == "K"
    hdr = mr.llm_params_for_entry({**base, "auth_type": "header", "api_key_header": "x-k"})
    assert hdr["api_key"] == "not-needed" and hdr["extra_headers"] == {"x-k": "K"}
    # auth_type=none: la key NO se envia como Bearer ni como cabecera
    assert mr.llm_params_for_entry({**base, "auth_type": "none"})["api_key"] == "not-needed"
    assert "extra_headers" not in mr.llm_params_for_entry({**base, "auth_type": "none"})


def test_generacion_tls_y_timeout_pero_nunca_max_tokens():
    p = mr.llm_params_for_entry({"kind": "ollama-nativo", "model": "m", "base_url": "http://h", "verify_tls": False, "timeout": 30,
                                 "generation": {"temperature": 0.3, "top_p": 0.9, "max_tokens": 99}})
    assert p["temperature"] == 0.3 and p["top_p"] == 0.9 and p["ssl_verify"] is False and p["timeout"] == 30 and "max_tokens" not in p


def test_entrada_sin_extras_queda_identica_a_antes():
    assert set(mr.llm_params_for_entry({"kind": "ollama-nativo", "model": "m", "base_url": "http://h"})) == {"model", "api_base"}


def test_kind_desconocido_falla_claro():
    with pytest.raises(RuntimeError):
        mr.llm_params_for_entry({"kind": "otro", "model": "m"})


@pytest.fixture
def _registry_on(monkeypatch):
    reg.reset_cache()
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_ENABLED", True)
    yield
    reg.reset_cache()


def test_registry_conserva_campos_nuevos(_registry_on):
    payload = {"enabled": True, "fallbacks": [], "primary": {
        "name": "lm", "kind": "openai-compatible", "base_url": "http://host.docker.internal:1234/v1", "model": "m", "provider_uuid": "u-1",
        "auth_type": "header", "api_key_header": "x-k", "verify_tls": False, "timeout": 30, "generation": {"temperature": 0.2}}}
    entry = reg.parse_registry_payload(payload)[0]
    assert entry["provider_uuid"] == "u-1" and entry["timeout"] == 30 and entry["generation"] == {"temperature": 0.2} and entry["verify_tls"] is False


def test_resolve_primary_sigue_al_registry_y_solo_devuelve_3_claves(monkeypatch, _registry_on):
    async def fake():
        return [{"name": "lm", "kind": "openai-compatible", "base_url": "http://h/v1", "model": "qwen", "api_key_value": "K",
                 "generation": {"temperature": 0.5}}]

    monkeypatch.setattr(reg, "get_registry_entries", fake)
    mr._chain_snapshot.set(None)
    params = asyncio.run(mr.resolve_primary_llm_params())
    assert params == {"model": "openai/qwen", "api_base": "http://h/v1", "api_key": "K"}  # sin temperature/top_p (check_grounding no los acepta)


def test_resolve_primary_sin_registry_usa_local_model_chain(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_ENABLED", False)
    monkeypatch.setattr(ai_config, "LOCAL_MODEL_CHAIN", "ollama|ollama-nativo|http://o:11434|qwen3.5:9b;lm|openai-compatible|http://l/v1|x")
    mr._chain_snapshot.set(None)
    assert asyncio.run(mr.resolve_primary_llm_params()) == {"model": "ollama_chat/qwen3.5:9b", "api_base": "http://o:11434"}


def test_resolve_primary_respeta_el_snapshot_del_turno(monkeypatch):
    monkeypatch.setattr(ai_config, "AI_PROVIDER_REGISTRY_ENABLED", False)
    key = object()
    mr._chain_snapshot.set((key, [({"kind": "ollama-nativo", "model": "del-turno", "base_url": "http://s:11434"}, object())]))
    assert asyncio.run(mr.resolve_primary_llm_params())["model"] == "ollama_chat/del-turno"
    mr._chain_snapshot.set(None)


class _Inner:
    def __init__(self, params):
        self.params = params

    async def generate_content_async(self, req, stream=False):
        yield "ok"


def test_traza_lleva_provider_id_y_config_version_sin_secretos(monkeypatch, _registry_on):
    async def fake():
        reg._state["version"] = 7
        return [{"name": "lm", "kind": "openai-compatible", "base_url": "http://h/v1", "model": "m", "api_key_value": "SECRETO-T", "provider_uuid": "pid-9"}]

    monkeypatch.setattr(reg, "get_registry_entries", fake)
    model = mr.FallbackLiteLlm(parse_local_model_chain("e|ollama-nativo|http://o:11434|m"), timeout=5,
                               breaker=mr.ProviderBreaker(store=mr.MemoryStore()), inner_factory=_Inner, use_registry=True)

    async def run():
        mr.begin_turn_trace()
        async for _ in model.generate_content_async(object()):
            pass
        return mr._trace()

    trace = asyncio.run(run())
    assert trace["provider_id"] == "pid-9" and trace["config_version"] == 7 and "SECRETO-T" not in str(trace)


def test_timeout_por_entrada_no_choca_con_el_global():
    model = mr.FallbackLiteLlm(parse_local_model_chain("e|ollama-nativo|http://o:11434|m"), timeout=5,
                               breaker=mr.ProviderBreaker(store=mr.MemoryStore()), inner_factory=_Inner)
    assert model._inner_for({"kind": "ollama-nativo", "model": "m", "base_url": "http://o:11434", "timeout": 30}).params["timeout"] == 30
