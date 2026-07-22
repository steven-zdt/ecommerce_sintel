import logging
from langchain_core.language_models import BaseChatModel
from config import LLM_PROVIDER, LLM_MODEL, OLLAMA_BASE_URL, OPENAI_API_KEY, ANTHROPIC_API_KEY

logger = logging.getLogger(__name__)


def get_llm() -> BaseChatModel:
    if LLM_PROVIDER == "openai":
        from langchain_openai import ChatOpenAI
        logger.info("[llm] Usando OpenAI: %s", LLM_MODEL)
        return ChatOpenAI(model=LLM_MODEL, api_key=OPENAI_API_KEY, temperature=0.1)

    if LLM_PROVIDER == "anthropic":
        from langchain_anthropic import ChatAnthropic
        logger.info("[llm] Usando Anthropic: %s", LLM_MODEL)
        return ChatAnthropic(model=LLM_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0.1)

    from langchain_ollama import ChatOllama
    logger.info("[llm] Usando Ollama: %s @ %s", LLM_MODEL, OLLAMA_BASE_URL)
    return ChatOllama(
        model=LLM_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.1,
        num_predict=1500,
        num_ctx=8192,
    )
