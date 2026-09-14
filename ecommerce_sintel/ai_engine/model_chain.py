"""
Parseo de `LOCAL_MODEL_CHAIN` -- extraido de `llm_factory.py` (mision
"ADK-SINTEL", ADK-11, 2026-09-14) por el mismo motivo real que
`routing.py`: `llm_factory.py` importa `langchain_core` a nivel de modulo
(necesario para construir los clientes `BaseChatModel` reales), pero el
PARSEO en si (`parse_local_model_chain`) es puro -- solo `logging` y
`str.split`. El nuevo runtime ADK (`ai_engine_adk/`) necesita leer el MISMO
`LOCAL_MODEL_CHAIN` (mismo formato real, ver `config.py`) para elegir su
proveedor LiteLLM, sin poder importar `langchain-core` (conflicto de
dependencias real con `litellm`, confirmado en ADK-10).

Extraccion mecanica -- CERO cambio de comportamiento, mismo codigo,
byte-a-byte.
"""
import logging

logger = logging.getLogger(__name__)

VALID_KINDS = {"ollama-nativo", "openai-compatible", "anthropic"}


def parse_local_model_chain(raw: str) -> list[dict]:
    """Parsea LOCAL_MODEL_CHAIN (ver config.py para el formato). Entradas invalidas se
    ignoran con un warning en vez de tumbar el arranque -- un typo en una entrada de
    fallback no deberia impedir que el motor arranque con las demas."""
    entries: list[dict] = []
    for chunk in (raw or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = [p.strip() for p in chunk.split("|")]
        if len(parts) not in (4, 5):
            logger.warning("[model_chain] entrada invalida en LOCAL_MODEL_CHAIN, se ignora: %r", chunk)
            continue
        name, kind, base_url, model = parts[:4]
        if kind not in VALID_KINDS:
            logger.warning("[model_chain] tipo desconocido '%s' en LOCAL_MODEL_CHAIN, se ignora: %r", kind, chunk)
            continue
        entries.append({
            "name": name, "kind": kind, "base_url": base_url, "model": model,
            "api_key_env": parts[4] if len(parts) == 5 else None,
        })
    return entries
