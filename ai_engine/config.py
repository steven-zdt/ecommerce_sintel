from decouple import config

LLM_PROVIDER        = config("LLM_PROVIDER", default="ollama")
LLM_MODEL           = config("LLM_MODEL", default="llama3.1:8b")
EMBEDDING_PROVIDER  = config("EMBEDDING_PROVIDER", default="ollama")
EMBEDDING_MODEL     = config("EMBEDDING_MODEL", default="bge-m3")
OLLAMA_BASE_URL     = config("OLLAMA_BASE_URL", default="http://sintel_ollama:11434")

CHROMA_HOST         = config("CHROMA_HOST", default="sintel_chromadb")
CHROMA_PORT         = config("CHROMA_PORT", default=8000, cast=int)
CHROMA_AUTH_TOKEN   = config("CHROMA_AUTH_TOKEN", default="")
CHROMA_COLLECTION   = config("CHROMA_COLLECTION_NAME", default="sintel_kb")

DOCS_SPECS_PATH     = config("DOCS_SPECS_PATH", default="/docs/specs")
CODEBASE_PATH       = config("CODEBASE_PATH", default="/workspace/ecommerce_sintel")
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
