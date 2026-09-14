import logging
from langchain_core.embeddings import Embeddings
from config import EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_BASE_URL, OLLAMA_BASE_URL, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def get_embeddings() -> Embeddings:
    if EMBEDDING_PROVIDER == "openai":
        # CERRADO 2026-08-17: base_url configurable -- antes esta rama SIEMPRE
        # hablaba con la API real de OpenAI, sin forma de apuntarla a un motor
        # OpenAI-compatible local (LM Studio, vLLM, etc.). Sin EMBEDDING_BASE_URL
        # definida, se comporta exactamente igual que antes (OpenAI real, exige
        # OPENAI_API_KEY). Con ella definida, motores locales no exigen key real
        # -- mismo criterio que _resolve_api_key() en llm_factory.py.
        if not EMBEDDING_BASE_URL and not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY requerida cuando EMBEDDING_PROVIDER=openai sin EMBEDDING_BASE_URL")
        from langchain_openai import OpenAIEmbeddings
        api_key = OPENAI_API_KEY or "not-needed"
        logger.info(
            "[embeddings] Usando OpenAI-compatible: %s @ %s",
            EMBEDDING_MODEL, EMBEDDING_BASE_URL or "api.openai.com (default)",
        )
        kwargs = {"model": EMBEDDING_MODEL, "api_key": api_key}
        if EMBEDDING_BASE_URL:
            kwargs["base_url"] = EMBEDDING_BASE_URL
        return OpenAIEmbeddings(**kwargs)

    from langchain_ollama import OllamaEmbeddings
    logger.info("[embeddings] Usando Ollama: %s @ %s", EMBEDDING_MODEL, OLLAMA_BASE_URL)
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
