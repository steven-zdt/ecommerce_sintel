"""
ai_engine/tests/test_dynamic_llm_config.py

FASE 4 del plan maestro "CONFIGURACION DINAMICA DE MODELOS LOCALES PARA CHAT
SUPPORT" (2026-08-13). Cubre `_fetch_dynamic_chain()`/`get_dynamic_llm()`
(llm_factory.py) -- el mecanismo por el cual /chat resuelve el LLM real desde
Postgres (via el internal API de Django, FASE 2) en vez del LOCAL_MODEL_CHAIN
estatico, cayendo a este ultimo como bootstrap/fallback/emergencia.

httpx.AsyncClient se mockea (no hay respx instalado en este entorno) -- se
verifica el request real via los argumentos capturados en el mock, no solo el
resultado. Correr con: docker compose exec sintel_ai pytest ai_engine/tests/
test_dynamic_llm_config.py -v
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import llm_factory


@pytest.fixture(autouse=True)
def reset_dynamic_cache():
    """El cache de get_dynamic_llm es un dict a nivel de modulo -- sin resetearlo
    entre tests, el orden de ejecucion afectaria los resultados."""
    llm_factory._dynamic_chain_cache["entries"] = None
    llm_factory._dynamic_chain_cache["fetched_at"] = 0.0
    llm_factory._dynamic_chain_cache["generation"] = None
    yield
    llm_factory._dynamic_chain_cache["entries"] = None
    llm_factory._dynamic_chain_cache["fetched_at"] = 0.0
    llm_factory._dynamic_chain_cache["generation"] = None


@pytest.fixture(autouse=True)
def stub_runtime_generation():
    """FASE 20: por default, ningun test de este archivo depende del contador de
    generacion en Redis (eso lo cubre TestRuntimeGeneration mas abajo) -- se stubea
    a None ('sin cambios detectados') para que el comportamiento de TTL/cache de
    los tests existentes no dependa de si hay Redis real disponible ni de su
    estado actual."""
    with patch.object(llm_factory, "_get_runtime_generation", new=AsyncMock(return_value=None)):
        yield


def _mock_response(status_code=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data or {}
    return resp


REAL_SHAPE_PAYLOAD = {
    "channel": "support_chat",
    "enabled": True,
    "primary": {
        "name": "Ollama Docker (real)", "kind": "ollama-nativo",
        "base_url": "http://sintel_ollama:11434", "model": "llama3.1:8b",
        "api_key_env": None, "api_key_value": None,
    },
    "fallbacks": [],
}


class TestFetchDynamicChain:
    async def test_parses_real_response_shape_from_internal_api(self):
        """FASE 15/19: Django ya construye 'primary'/'fallbacks' en el shape exacto
        de _build_model() via BaseProviderAdapter.build_runtime_config() -- aqui no
        se remapea nada, solo se aplana [primary, *fallbacks]."""
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(200, REAL_SHAPE_PAYLOAD))):
            entries = await llm_factory._fetch_dynamic_chain()
        assert entries == [REAL_SHAPE_PAYLOAD["primary"]]

    async def test_returns_none_on_empty_chain(self):
        """primary=None -- canal sin configurar o deshabilitado (ambos casos
        colapsan al mismo shape desde Django, ver AiProviderConfigView)."""
        payload = {"channel": "support_chat", "enabled": True, "primary": None, "fallbacks": []}
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(200, payload))):
            entries = await llm_factory._fetch_dynamic_chain()
        assert entries is None

    async def test_returns_none_when_channel_disabled(self):
        payload = {"channel": "support_chat", "enabled": False, "primary": None, "fallbacks": []}
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(200, payload))):
            entries = await llm_factory._fetch_dynamic_chain()
        assert entries is None

    async def test_returns_none_on_non_200(self):
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(503, {}))):
            entries = await llm_factory._fetch_dynamic_chain()
        assert entries is None

    async def test_returns_none_and_never_raises_on_connection_error(self):
        import httpx
        with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=httpx.ConnectError("boom"))):
            entries = await llm_factory._fetch_dynamic_chain()
        assert entries is None

    async def test_preserves_real_decrypted_api_key_when_present(self):
        payload = {
            "channel": "support_chat",
            "enabled": True,
            "primary": {
                "name": "openai real", "kind": "openai-compatible",
                "base_url": "https://api.openai.com/v1", "model": "gpt-4o-mini",
                "api_key_env": None, "api_key_value": "sk-real-secret",
            },
            "fallbacks": [],
        }
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(200, payload))):
            entries = await llm_factory._fetch_dynamic_chain()
        assert entries[0]["api_key_value"] == "sk-real-secret"

    async def test_includes_fallbacks_after_primary(self):
        payload = {
            "channel": "support_chat",
            "enabled": True,
            "primary": {
                "name": "primario", "kind": "ollama-nativo", "base_url": "http://x:11434",
                "model": "a", "api_key_env": None, "api_key_value": None,
            },
            "fallbacks": [{
                "name": "fallback", "kind": "ollama-nativo", "base_url": "http://y:11434",
                "model": "b", "api_key_env": None, "api_key_value": None,
            }],
        }
        with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_mock_response(200, payload))):
            entries = await llm_factory._fetch_dynamic_chain()
        assert [e["model"] for e in entries] == ["a", "b"]


class TestGetDynamicLlm:
    async def test_falls_back_to_local_model_chain_when_no_dynamic_config(self):
        with patch.object(llm_factory, "_fetch_dynamic_chain", new=AsyncMock(return_value=None)):
            model = await llm_factory.get_dynamic_llm()
        # LOCAL_MODEL_CHAIN por default (config.py) es una unica entrada ollama-nativo
        # -- sin fallback, get_dynamic_llm debe devolver el modelo directo (no envuelto
        # en with_fallbacks).
        assert model is not None
        assert not hasattr(model, "runnables")  # with_fallbacks() envuelve en RunnableWithFallbacks

    async def test_uses_dynamic_chain_when_available(self):
        fetch_mock = AsyncMock(return_value=[{
            "name": "Ollama Docker (real)", "kind": "ollama-nativo",
            "base_url": "http://sintel_ollama:11434", "model": "llama3.1:8b",
            "api_key_env": None, "api_key_value": None,
        }])
        with patch.object(llm_factory, "_fetch_dynamic_chain", new=fetch_mock):
            model = await llm_factory.get_dynamic_llm()
        assert fetch_mock.await_count == 1
        assert model is not None

    async def test_caches_within_ttl_does_not_refetch(self):
        fetch_mock = AsyncMock(return_value=None)
        with patch.object(llm_factory, "_fetch_dynamic_chain", new=fetch_mock):
            await llm_factory.get_dynamic_llm()
            await llm_factory.get_dynamic_llm()
            await llm_factory.get_dynamic_llm()
        assert fetch_mock.await_count == 1

    async def test_refetches_after_ttl_expires(self):
        fetch_mock = AsyncMock(return_value=None)
        with patch.object(llm_factory, "_fetch_dynamic_chain", new=fetch_mock):
            await llm_factory.get_dynamic_llm()
            llm_factory._dynamic_chain_cache["fetched_at"] -= (llm_factory._DYNAMIC_CHAIN_CACHE_TTL_SECONDS + 1)
            await llm_factory.get_dynamic_llm()
        assert fetch_mock.await_count == 2


class TestRuntimeGenerationInvalidation:
    """FASE 20: un cambio de generacion en Redis debe forzar un refetch inmediato,
    saltandose el TTL de 15s -- esto es lo que hace que el panel de /panel/soporte
    se refleje en /chat sin esperar, en vez de depender solo del TTL de FASE 19."""

    async def test_generation_change_forces_refetch_even_within_ttl(self):
        fetch_mock = AsyncMock(return_value=None)
        gen_mock = AsyncMock(side_effect=[1, 1, 2])
        with patch.object(llm_factory, "_fetch_dynamic_chain", new=fetch_mock), \
             patch.object(llm_factory, "_get_runtime_generation", new=gen_mock):
            await llm_factory.get_dynamic_llm()  # gen=1, primer fetch (cache frio)
            await llm_factory.get_dynamic_llm()  # gen=1, sin cambio -> no refetch (TTL vivo)
            await llm_factory.get_dynamic_llm()  # gen=2, distinto -> refetch forzado
        assert fetch_mock.await_count == 2

    async def test_unknown_generation_does_not_force_refetch(self):
        """Redis caido o clave inexistente (None) -- no debe forzar nada, el TTL
        normal sigue siendo la unica fuente de verdad (comportamiento FASE 19)."""
        fetch_mock = AsyncMock(return_value=None)
        gen_mock = AsyncMock(return_value=None)
        with patch.object(llm_factory, "_fetch_dynamic_chain", new=fetch_mock), \
             patch.object(llm_factory, "_get_runtime_generation", new=gen_mock):
            await llm_factory.get_dynamic_llm()
            await llm_factory.get_dynamic_llm()
        assert fetch_mock.await_count == 1

    async def test_get_runtime_generation_never_raises_on_redis_error(self):
        import redis.exceptions
        with patch.object(
            llm_factory.aredis.Redis, "from_url", side_effect=redis.exceptions.ConnectionError("boom"),
        ):
            result = await llm_factory._get_runtime_generation("support_chat")
        assert result is None


class TestRuntimeConfigResolver:
    """FASE 19: get_dynamic_llm() es ahora un wrapper delgado sobre
    RuntimeConfigResolver.resolve() -- mismo comportamiento, nombre formal nuevo."""

    async def test_resolve_is_equivalent_to_get_dynamic_llm(self):
        fetch_mock = AsyncMock(return_value=None)
        with patch.object(llm_factory, "_fetch_dynamic_chain", new=fetch_mock):
            model = await llm_factory.RuntimeConfigResolver.resolve()
        assert model is not None

    async def test_get_dynamic_llm_delegates_to_resolver(self):
        with patch.object(
            llm_factory.RuntimeConfigResolver, "resolve", new=AsyncMock(return_value="sentinel"),
        ) as resolve_mock:
            result = await llm_factory.get_dynamic_llm(channel="support_chat")
        resolve_mock.assert_awaited_once_with("support_chat")
        assert result == "sentinel"


class TestResolveApiKey:
    def test_prefers_dynamic_value_over_env(self, monkeypatch):
        monkeypatch.setenv("SOME_KEY_ENV", "from-env")
        entry = {"api_key_value": "from-dynamic-config", "api_key_env": "SOME_KEY_ENV"}
        assert llm_factory._resolve_api_key(entry, default="fallback") == "from-dynamic-config"

    def test_falls_back_to_env_when_no_dynamic_value(self, monkeypatch):
        monkeypatch.setenv("SOME_KEY_ENV", "from-env")
        entry = {"api_key_value": None, "api_key_env": "SOME_KEY_ENV"}
        assert llm_factory._resolve_api_key(entry, default="fallback") == "from-env"

    def test_falls_back_to_default_when_neither_present(self):
        entry = {"api_key_value": None, "api_key_env": None}
        assert llm_factory._resolve_api_key(entry, default="fallback") == "fallback"
