import logging
from langchain_core.embeddings import Embeddings
from config import EMBEDDING_PROVIDER, EMBEDDING_MODEL, OLLAMA_BASE_URL, OPENAI_API_KEY

logger = logging.getLogger(__name__)


def get_embeddings() -> Embeddings:
    if EMBEDDING_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY requerida cuando EMBEDDING_PROVIDER=openai")
        from langchain_openai import OpenAIEmbeddings
        logger.info("[embeddings] Usando OpenAI: %s", EMBEDDING_MODEL)
        return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=OPENAI_API_KEY)

    from langchain_ollama import OllamaEmbeddings
    logger.info("[embeddings] Usando Ollama: %s @ %s", EMBEDDING_MODEL, OLLAMA_BASE_URL)
    return OllamaEmbeddings(model=EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL)
