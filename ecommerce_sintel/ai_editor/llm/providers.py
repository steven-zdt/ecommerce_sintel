"""
Proveedores de LLM para ai_editor -- POST-GRAPH 2 "Change Intent"
(rediseno "AI Editor Runtime", 2026-08-11).

3 proveedores (Ollama local, OpenAI, Anthropic) implementados con HTTP
"puro" (`urllib.request` de la libreria estandar, cero dependencias
nuevas) -- decision explicita del usuario de no depender de ningun otro
modulo del proyecto (en particular, no de `ai_engine.llm_factory`, que
usa LangChain). Cada proveedor implementa la MISMA interfaz
(`complete(system, user, max_tokens, temperature) -> LLMResponse`), lo
que permite cambiar de proveedor sin tocar el codigo que los consume
(`ai_editor/llm/__init__.py::get_llm_client()`).

Nunca se loguea `api_key` -- ni en excepciones, ni en ningun log. Los
errores HTTP incluyen el status code y el nombre del proveedor, nunca los
headers de la request (que llevarian la key).
"""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from ai_editor.llm.config import LLMConfig


@dataclass(frozen=True)
class LLMResponse:
    text: str
    provider: str
    model: str
    raw: dict


class LLMRequestError(RuntimeError):
    """Fallo real de red/HTTP contra el proveedor -- nunca incluye la
    API key en el mensaje."""


def _post_json(url: str, payload: dict, headers: dict, timeout: float, provider: str) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LLMRequestError(f"[{provider}] HTTP {exc.code} llamando a {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise LLMRequestError(f"[{provider}] no se pudo conectar a {url}: {exc.reason}") from exc


class OllamaProvider:
    """Ollama local -- `POST {base_url}/api/chat`, sin API key (motor
    corriendo en la red local/host, mismo servicio `sintel_ollama` que ya
    usa `ai_engine`, pero accedido aca de forma independiente via HTTP
    puro, sin importar nada de `ai_engine`)."""

    def complete(self, config: LLMConfig, system: str | None, user: str,
                 max_tokens: int, temperature: float) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        payload = {
            "model": config.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        raw = _post_json(
            f"{config.base_url}/api/chat", payload,
            headers={"Content-Type": "application/json"},
            timeout=config.timeout_seconds, provider="ollama",
        )
        text = raw.get("message", {}).get("content", "")
        return LLMResponse(text=text, provider="ollama", model=config.model, raw=raw)


class OpenAIProvider:
    """API REST de OpenAI (o cualquier endpoint OpenAI-compatible via
    `AI_EDITOR_OPENAI_BASE_URL`) -- `POST {base_url}/chat/completions`."""

    def complete(self, config: LLMConfig, system: str | None, user: str,
                 max_tokens: int, temperature: float) -> LLMResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})

        payload = {
            "model": config.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        raw = _post_json(
            f"{config.base_url}/chat/completions", payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
            timeout=config.timeout_seconds, provider="openai",
        )
        text = raw["choices"][0]["message"]["content"]
        return LLMResponse(text=text, provider="openai", model=config.model, raw=raw)


class AnthropicProvider:
    """API REST de Anthropic -- `POST {base_url}/messages` (Messages API)."""

    def complete(self, config: LLMConfig, system: str | None, user: str,
                 max_tokens: int, temperature: float) -> LLMResponse:
        payload = {
            "model": config.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user}],
        }
        if system:
            payload["system"] = system

        raw = _post_json(
            f"{config.base_url}/messages", payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": config.api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=config.timeout_seconds, provider="anthropic",
        )
        text = "".join(block.get("text", "") for block in raw.get("content", []) if block.get("type") == "text")
        return LLMResponse(text=text, provider="anthropic", model=config.model, raw=raw)


PROVIDERS = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}
