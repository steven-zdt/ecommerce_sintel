"""
Configuracion del LLM independiente de ai_editor -- POST-GRAPH 2 "Change
Intent" (rediseno "AI Editor Runtime", 2026-08-11).

Decision explicita del usuario (2026-08-11): ai_editor accede a un LLM de
forma TOTALMENTE INDEPENDIENTE, sin importar `ai_engine.llm_factory` (que
usa LangChain y pertenece exclusivamente al chatbot de soporte) ni ningun
otro modulo del proyecto. Este archivo NO reusa codigo de `ai_engine` --
es una implementacion nueva y separada, con su propio formato de
configuracion (variables `AI_EDITOR_*`, distintas de `LOCAL_MODEL_CHAIN`/
`OPENAI_API_KEY`/`ANTHROPIC_API_KEY` que usa `ai_engine`) para que ambos
puedan cambiar de proveedor de forma independiente sin pisarse.

Todo por variables de entorno via `os.environ` (sin `python-decouple`
u otra dependencia -- `ai_editor` no depende de Django ni de ningun otro
paquete del proyecto, es un modulo standalone).
"""
import os
from dataclasses import dataclass

DEFAULT_PROVIDER = "ollama"

_DEFAULTS = {
    "ollama": {
        "base_url": "http://localhost:11434",
        "model": "llama3.1:8b",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com/v1",
        "model": "claude-3-5-sonnet-latest",
    },
}

_SUPPORTED_PROVIDERS = tuple(_DEFAULTS.keys())


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    model: str
    api_key: str | None
    timeout_seconds: float


class LLMConfigError(RuntimeError):
    """Configuracion invalida o incompleta (ej. falta API key para un
    proveedor de nube). Falla explicito -- nunca degrada en silencio a un
    proveedor distinto del que se pidio (mismo criterio que el resto del
    proyecto: fallar ruidoso, no silencioso, ver `.AGENT.md`)."""


def load_llm_config(provider: str | None = None) -> LLMConfig:
    """Resuelve la configuracion real para `provider` (o
    `AI_EDITOR_LLM_PROVIDER`, default `ollama`, si no se pasa explicito --
    permite cambiar de LLM en tiempo de ejecucion sin tocar variables de
    entorno, pedido explicito del usuario: "poder cambiar de llm segun sea
    conveniente")."""
    resolved_provider = (provider or os.environ.get("AI_EDITOR_LLM_PROVIDER") or DEFAULT_PROVIDER).lower()
    if resolved_provider not in _SUPPORTED_PROVIDERS:
        raise LLMConfigError(
            f"AI_EDITOR_LLM_PROVIDER='{resolved_provider}' no soportado -- "
            f"proveedores validos: {', '.join(_SUPPORTED_PROVIDERS)}"
        )

    prefix = f"AI_EDITOR_{resolved_provider.upper()}_"
    defaults = _DEFAULTS[resolved_provider]
    base_url = os.environ.get(f"{prefix}BASE_URL", defaults["base_url"])
    model = os.environ.get(f"{prefix}MODEL", defaults["model"])
    api_key = os.environ.get(f"{prefix}API_KEY")
    timeout_seconds = float(os.environ.get("AI_EDITOR_LLM_TIMEOUT_SECONDS", "60"))

    if resolved_provider in ("openai", "anthropic") and not api_key:
        raise LLMConfigError(
            f"{prefix}API_KEY no esta configurada -- requerida para el proveedor "
            f"'{resolved_provider}'. `ollama` (local, sin API key) es el default si "
            "no se configura ningun proveedor."
        )

    return LLMConfig(
        provider=resolved_provider,
        base_url=base_url.rstrip("/"),
        model=model,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
