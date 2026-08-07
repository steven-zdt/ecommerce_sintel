import logging
from decouple import config as env
from langchain_core.language_models import BaseChatModel
from config import LOCAL_MODEL_CHAIN, OPENAI_API_KEY, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)

# G2 (AUDITORIA/16, 2026-08-01): ninguna llamada al LLM tenia timeout propio -- el unico corte
# end-to-end era el timeout de Django esperando /chat completo (AI_CHAT_TIMEOUT_SECONDS=300,
# support/services/ai_bridge.py). Con un solo proceso uvicorn (Dockerfile, sin --workers), una
# llamada colgada al proveedor degradaba la capacidad practica del proceso entero sin que el
# motor mismo pudiera cortar nada.
LLM_TIMEOUT_SECONDS = 90

_VALID_KINDS = {"ollama-nativo", "openai-compatible", "anthropic"}


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
            logger.warning("[llm_factory] entrada invalida en LOCAL_MODEL_CHAIN, se ignora: %r", chunk)
            continue
        name, kind, base_url, model = parts[:4]
        if kind not in _VALID_KINDS:
            logger.warning("[llm_factory] tipo desconocido '%s' en LOCAL_MODEL_CHAIN, se ignora: %r", kind, chunk)
            continue
        entries.append({
            "name": name, "kind": kind, "base_url": base_url, "model": model,
            "api_key_env": parts[4] if len(parts) == 5 else None,
        })
    return entries


def _build_model(entry: dict) -> BaseChatModel:
    kind = entry["kind"]

    if kind == "ollama-nativo":
        from langchain_ollama import ChatOllama
        logger.info("[llm] motor '%s' (ollama-nativo): %s @ %s", entry["name"], entry["model"], entry["base_url"])
        return ChatOllama(
            model=entry["model"], base_url=entry["base_url"], temperature=0.1,
            num_predict=1500, num_ctx=8192, client_kwargs={"timeout": LLM_TIMEOUT_SECONDS},
        )

    if kind == "anthropic":
        from langchain_anthropic import ChatAnthropic
        api_key = env(entry["api_key_env"], default=ANTHROPIC_API_KEY) if entry["api_key_env"] else ANTHROPIC_API_KEY
        logger.info("[llm] motor '%s' (anthropic): %s", entry["name"], entry["model"])
        return ChatAnthropic(
            model=entry["model"], api_key=api_key, temperature=0.1,
            default_request_timeout=LLM_TIMEOUT_SECONDS,
        )

    # openai-compatible: cubre CUALQUIER motor que hable /v1/chat/completions -- LM Studio,
    # vLLM, llama.cpp (modo servidor), text-generation-webui, LocalAI, DeepSeek, OpenAI real --
    # sin una clase de Python por motor. Motores locales no exigen una key real.
    from langchain_openai import ChatOpenAI
    api_key = env(entry["api_key_env"], default="not-needed") if entry["api_key_env"] else (OPENAI_API_KEY or "not-needed")
    logger.info("[llm] motor '%s' (openai-compatible): %s @ %s", entry["name"], entry["model"], entry["base_url"])
    return ChatOpenAI(
        model=entry["model"], base_url=entry["base_url"], api_key=api_key, temperature=0.1,
        request_timeout=LLM_TIMEOUT_SECONDS,
    )


def get_llm() -> BaseChatModel:
    """
    Nivel A (auditoria 2026-08-07): ya no hay un unico proveedor fijo. LOCAL_MODEL_CHAIN
    describe una cadena ordenada de motores -- locales, en Docker, o cloud -- el primero
    es el primario y el resto son fallback automatico via .with_fallbacks() (nativo de
    langchain-core, sin dependencia nueva). Si el motor primario no responde, LangChain
    conmuta al siguiente por request, no solo al arrancar el proceso. Verificado que
    .bind_tools() (action_graph.py) sigue funcionando sobre la cadena completa sin
    modificarse -- aplica el binding a cada motor encadenado.

    Agregar, quitar o reordenar motores es editar LOCAL_MODEL_CHAIN, nunca este archivo.
    """
    entries = parse_local_model_chain(LOCAL_MODEL_CHAIN)
    if not entries:
        raise ValueError("LOCAL_MODEL_CHAIN no tiene ninguna entrada valida -- revisa el formato en config.py.")

    models = [_build_model(entry) for entry in entries]
    primary, *fallbacks = models
    if not fallbacks:
        return primary

    logger.info("[llm] cadena con fallback (%d motores): %s", len(entries), " -> ".join(e["name"] for e in entries))
    return primary.with_fallbacks(fallbacks)
