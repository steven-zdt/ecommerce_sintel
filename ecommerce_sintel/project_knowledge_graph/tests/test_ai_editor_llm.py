"""
Unit tests para ai_editor/llm/ -- POST-GRAPH 2 "Change Intent" (rediseno
"AI Editor Runtime", 2026-08-11). Aislados: mockean `urllib.request.urlopen`
para no depender de red real (Ollama/OpenAI/Anthropic vivos) -- verifican
que CADA proveedor arma la request correcta (URL, headers, payload) y
parsea la respuesta real de cada API tal como la documenta cada proveedor
(formato exacto de cada API, no inventado).
"""
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from ai_editor.llm.config import LLMConfigError, load_llm_config
from ai_editor.llm.providers import (
    AnthropicProvider,
    LLMRequestError,
    OllamaProvider,
    OpenAIProvider,
)


class _FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._body = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_load_llm_config_defaults_to_ollama_without_any_env(monkeypatch):
    for var in ("AI_EDITOR_LLM_PROVIDER", "AI_EDITOR_OLLAMA_BASE_URL", "AI_EDITOR_OLLAMA_MODEL"):
        monkeypatch.delenv(var, raising=False)

    config = load_llm_config()

    assert config.provider == "ollama"
    assert config.base_url == "http://localhost:11434"
    assert config.model == "llama3.1:8b"
    assert config.api_key is None


def test_load_llm_config_rejects_unsupported_provider():
    with pytest.raises(LLMConfigError):
        load_llm_config("not-a-real-provider")


def test_load_llm_config_fails_closed_when_cloud_provider_missing_api_key(monkeypatch):
    monkeypatch.delenv("AI_EDITOR_OPENAI_API_KEY", raising=False)

    with pytest.raises(LLMConfigError):
        load_llm_config("openai")


def test_load_llm_config_explicit_provider_argument_overrides_env(monkeypatch):
    """Permite cambiar de LLM en tiempo de ejecucion sin tocar variables
    de entorno -- pedido explicito del usuario."""
    monkeypatch.setenv("AI_EDITOR_LLM_PROVIDER", "ollama")
    monkeypatch.setenv("AI_EDITOR_ANTHROPIC_API_KEY", "sk-fake-test-key")

    config = load_llm_config("anthropic")

    assert config.provider == "anthropic"
    assert config.api_key == "sk-fake-test-key"


def test_load_llm_config_never_exposes_missing_key_value_in_error(monkeypatch):
    monkeypatch.delenv("AI_EDITOR_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMConfigError) as exc_info:
        load_llm_config("anthropic")
    assert "AI_EDITOR_ANTHROPIC_API_KEY" in str(exc_info.value)


@patch("ai_editor.llm.providers.urllib.request.urlopen")
def test_ollama_provider_builds_correct_request_and_parses_response(mock_urlopen, monkeypatch):
    monkeypatch.delenv("AI_EDITOR_LLM_PROVIDER", raising=False)
    config = load_llm_config("ollama")
    mock_urlopen.return_value = _FakeHTTPResponse(
        {"message": {"role": "assistant", "content": "respuesta real de ollama"}}
    )

    response = OllamaProvider().complete(config, system="eres util", user="hola", max_tokens=100, temperature=0.0)

    assert response.text == "respuesta real de ollama"
    assert response.provider == "ollama"
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "http://localhost:11434/api/chat"
    body = json.loads(request.data.decode("utf-8"))
    assert body["messages"] == [
        {"role": "system", "content": "eres util"},
        {"role": "user", "content": "hola"},
    ]
    assert body["stream"] is False


@patch("ai_editor.llm.providers.urllib.request.urlopen")
def test_openai_provider_sends_bearer_auth_and_parses_choices(mock_urlopen, monkeypatch):
    monkeypatch.setenv("AI_EDITOR_OPENAI_API_KEY", "sk-test-123")
    config = load_llm_config("openai")
    mock_urlopen.return_value = _FakeHTTPResponse(
        {"choices": [{"message": {"role": "assistant", "content": "respuesta de openai"}}]}
    )

    response = OpenAIProvider().complete(config, system=None, user="hola", max_tokens=100, temperature=0.2)

    assert response.text == "respuesta de openai"
    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "https://api.openai.com/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer sk-test-123"


@patch("ai_editor.llm.providers.urllib.request.urlopen")
def test_anthropic_provider_sends_x_api_key_header_and_parses_content_blocks(mock_urlopen, monkeypatch):
    monkeypatch.setenv("AI_EDITOR_ANTHROPIC_API_KEY", "sk-ant-test-456")
    config = load_llm_config("anthropic")
    mock_urlopen.return_value = _FakeHTTPResponse(
        {"content": [{"type": "text", "text": "respuesta de anthropic"}]}
    )

    response = AnthropicProvider().complete(config, system="system prompt", user="hola", max_tokens=100, temperature=0.0)

    assert response.text == "respuesta de anthropic"
    request = mock_urlopen.call_args[0][0]
    assert request.headers["X-api-key"] == "sk-ant-test-456"
    assert request.headers["Anthropic-version"] == "2023-06-01"
    body = json.loads(request.data.decode("utf-8"))
    assert body["system"] == "system prompt"


@patch("ai_editor.llm.providers.urllib.request.urlopen")
def test_provider_raises_llm_request_error_on_http_failure_without_leaking_api_key(mock_urlopen, monkeypatch):
    monkeypatch.setenv("AI_EDITOR_OPENAI_API_KEY", "sk-super-secret-key")
    config = load_llm_config("openai")
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="https://api.openai.com/v1/chat/completions", code=401,
        msg="Unauthorized", hdrs=None, fp=MagicMock(read=lambda: b'{"error": "invalid key"}'),
    )

    with pytest.raises(LLMRequestError) as exc_info:
        OpenAIProvider().complete(config, system=None, user="hola", max_tokens=10, temperature=0.0)

    assert "sk-super-secret-key" not in str(exc_info.value)
    assert "401" in str(exc_info.value)


def test_complete_facade_switches_provider_per_call(monkeypatch):
    """`ai_editor.llm.complete(..., provider=...)` debe poder cambiar de
    LLM llamada a llamada sin tocar configuracion global."""
    from ai_editor import llm

    monkeypatch.setenv("AI_EDITOR_LLM_PROVIDER", "ollama")
    config, client = llm.get_llm_client()
    assert config.provider == "ollama"

    monkeypatch.setenv("AI_EDITOR_ANTHROPIC_API_KEY", "sk-ant-fake")
    config2, client2 = llm.get_llm_client("anthropic")
    assert config2.provider == "anthropic"
