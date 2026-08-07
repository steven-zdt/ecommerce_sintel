from decouple import config

# --- Motores locales/Docker intercambiables (Nivel A, auditoria 2026-08-07) ---
# LOCAL_MODEL_CHAIN reemplaza el LLM_PROVIDER cerrado de antes (un solo valor de un
# set fijo). Es una lista ORDENADA de motores -- el primero es el primario, el resto
# son fallback automatico (llm_factory.py::get_llm() los encadena con with_fallbacks()
# nativo de langchain-core). Formato por entrada, separadas por ';':
#   nombre|tipo|base_url|modelo[|api_key_env]
# tipo in {ollama-nativo, openai-compatible, anthropic}:
#   - ollama-nativo: usa ChatOllama (tuneado con num_predict/num_ctx). Pensado para
#     Ollama especificamente -- si se prioriza rendimiento sobre uniformidad total.
#   - openai-compatible: cubre CUALQUIER motor que hable /v1/chat/completions sin
#     una clase de Python por motor -- LM Studio, vLLM, llama.cpp (modo servidor),
#     text-generation-webui, LocalAI, DeepSeek, OpenAI real. api_key_env (opcional)
#     nombra la variable de entorno con la key real; motores locales no la necesitan.
#   - anthropic: usa ChatAnthropic (Claude), la unica familia que no habla el
#     protocolo OpenAI-compatible.
# Agregar/quitar/reordenar motores es editar esta variable, nunca llm_factory.py.
LLM_MODEL           = config("LLM_MODEL", default="llama3.1:8b")
OLLAMA_BASE_URL     = config("OLLAMA_BASE_URL", default="http://sintel_ollama:11434")
LOCAL_MODEL_CHAIN   = config(
    "LOCAL_MODEL_CHAIN",
    default=f"ollama|ollama-nativo|{OLLAMA_BASE_URL}|{LLM_MODEL}",
)
EMBEDDING_PROVIDER  = config("EMBEDDING_PROVIDER", default="ollama")
EMBEDDING_MODEL     = config("EMBEDDING_MODEL", default="bge-m3")

CHROMA_HOST         = config("CHROMA_HOST", default="sintel_chromadb")
CHROMA_PORT         = config("CHROMA_PORT", default=8000, cast=int)
CHROMA_AUTH_TOKEN   = config("CHROMA_AUTH_TOKEN", default="")
CHROMA_COLLECTION   = config("CHROMA_COLLECTION_NAME", default="sintel_kb")

DOCS_SPECS_PATH     = config("DOCS_SPECS_PATH", default="/docs/specs")
CODEBASE_PATH       = config("CODEBASE_PATH", default="/workspace/ecommerce_sintel")
# B2 (AUDITORIA/16): checkpointer del Action Graph (redis_checkpointer.py) -- DB separada de
# Django (Channels=0, Cache=1) para no compartir namespace de claves con nada mas.
CHECKPOINTER_REDIS_URL = config("CHECKPOINTER_REDIS_URL", default="redis://redis:6379/2")
INGESTION_BATCH_SIZE = config("INGESTION_BATCH_SIZE", default=50, cast=int)
MAX_RETRIEVER_CHUNKS = config("MAX_RETRIEVER_CHUNKS", default=50, cast=int)
VALIDATION_MAX_RETRIES = config("VALIDATION_MAX_RETRIES", default=3, cast=int)

OPENAI_API_KEY      = config("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY   = config("ANTHROPIC_API_KEY", default="")

# ─── AI Core Fase 1: puente seguro Django <-> AI Engine ──────────────────────
# JWT_SECRET_KEY es la MISMA SIGNING_KEY de SimpleJWT en Django (settings/base.py,
# SIMPLE_JWT["SIGNING_KEY"]) -- llega por env_file compartido, nunca hardcodeada.
# El motor solo VALIDA tokens emitidos por Django; jamas emite los propios.
JWT_SECRET_KEY          = config("JWT_SECRET_KEY", default="")
DJANGO_INTERNAL_API_URL = config("DJANGO_INTERNAL_API_URL", default="http://django:8000/api/v1")

# Fase 2: habilita /api/v1/ai/tools/debug (SOLO dev — default cerrado; prod
# nunca define esta variable, asi el endpoint responde 404 alli).
AI_TOOLS_DEBUG          = config("AI_TOOLS_DEBUG", default=False, cast=bool)
