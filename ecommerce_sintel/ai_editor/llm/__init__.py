"""
ai_editor.llm -- POST-GRAPH 2 "Change Intent" (rediseno "AI Editor
Runtime", 2026-08-11).

Acceso a un LLM TOTALMENTE INDEPENDIENTE del resto del proyecto -- decision
explicita del usuario (2026-08-11): "quiero que ai_editor acceda al llm de
forma totalmente independiente sin depender de ningun otro modulo mediante
api key o api pura, tambien poder cambiar de llm segun sea conveniente".

NO importa `ai_engine.llm_factory` (LangChain, exclusivo del chatbot de
soporte) ni ningun otro modulo del proyecto -- implementacion propia sobre
`urllib.request` (libreria estandar, cero dependencias nuevas). 3
proveedores intercambiables (`ollama`/`openai`/`anthropic`, ver
`providers.py`), seleccionables por variable de entorno
(`AI_EDITOR_LLM_PROVIDER`) o por argumento explicito en cada llamada --
cambiar de proveedor no requiere tocar ningun otro archivo de `ai_editor`.

Uso:
    from ai_editor.llm import complete
    response = complete("Interpreta esta solicitud: ...", system="...")
    response.text      # str
    response.provider  # "ollama" | "openai" | "anthropic"
    response.model     # nombre real del modelo usado
"""
from ai_editor.llm.config import LLMConfig, LLMConfigError, load_llm_config
from ai_editor.llm.providers import LLMRequestError, LLMResponse, PROVIDERS


def get_llm_client(provider: str | None = None):
    """Devuelve `(config, provider_instance)` para el proveedor resuelto
    (explicito, o `AI_EDITOR_LLM_PROVIDER`, o `ollama` por default). Lanza
    `LLMConfigError` si el proveedor pedido no es valido o le falta la API
    key requerida -- fallo explicito, nunca degrada en silencio a otro
    proveedor distinto del pedido."""
    config = load_llm_config(provider)
    return config, PROVIDERS[config.provider]()


def complete(user: str, system: str | None = None, max_tokens: int = 1024,
             temperature: float = 0.0, provider: str | None = None) -> LLMResponse:
    """Punto de entrada principal: una llamada de completion contra el
    proveedor configurado (o `provider` si se pasa explicito, permitiendo
    cambiar de LLM por-llamada sin tocar variables de entorno)."""
    config, client = get_llm_client(provider)
    return client.complete(config, system, user, max_tokens, temperature)


__all__ = [
    "complete",
    "get_llm_client",
    "LLMConfig",
    "LLMConfigError",
    "LLMRequestError",
    "LLMResponse",
]
