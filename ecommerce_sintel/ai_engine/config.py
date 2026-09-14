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
# CERRADO 2026-08-17 (auditoria LM Studio): antes EMBEDDING_PROVIDER="openai" solo
# podia hablarle a la API real de OpenAI (embeddings_factory.py no aceptaba
# base_url) -- inservible para un motor OpenAI-compatible local como LM Studio.
# Mismo patron que OLLAMA_BASE_URL: solo se usa cuando EMBEDDING_PROVIDER != "ollama".
EMBEDDING_BASE_URL  = config("EMBEDDING_BASE_URL", default="")

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

# ─── FASE 10: Meta Ads MCP (https://mcp.facebook.com/ads) ────────────────────
# Servidor MCP remoto y de primera parte de Meta (lanzado 2026-04-29). Auth:
# OAuth 2.1 authorization-code + PKCE + dynamic client registration. Las
# credenciales del MCP son INDEPENDIENTES del META_ACCESS_TOKEN de la API
# directa de Django -- el ai_engine nunca conoce ese token, y Django nunca
# conoce el refresh token del MCP.
# Ver Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md
# (FASE 10) y ai_engine/mcp_client/.
MCP_META_ADS_URL        = config("MCP_META_ADS_URL", default="https://mcp.facebook.com/ads")
# El MCP de Meta NO soporta dynamic client registration ("Dynamic registration
# is not available for this client", verificado 2026-08-31 contra el endpoint
# real). Hace falta un App de Meta (developers.facebook.com): su App ID es el
# client_id OAuth (auth method "none" + PKCE S256, sin secret). El App debe
# tener http://localhost:{MCP_OAUTH_CALLBACK_PORT}/callback en "Valid OAuth
# Redirect URIs". Cae a META_APP_ID si no se define uno propio para el MCP.
MCP_META_ADS_CLIENT_ID  = config("MCP_META_ADS_CLIENT_ID", default=config("META_APP_ID", default=""))
# Scopes OAuth solicitados. FASE 10 = lectura: ads_read + lo minimo para que el
# MCP opere. `ads_mcp_management` es especifico del connector de Meta.
MCP_META_ADS_SCOPE      = config(
    "MCP_META_ADS_SCOPE",
    default="ads_read,business_management,pages_show_list,ads_mcp_management",
)
# El cliente MCP solo se usa si esta habilitado Y hay un refresh token guardado.
MCP_META_ADS_ENABLED    = config("MCP_META_ADS_ENABLED", default=False, cast=bool)
# FASE 10 es SOLO LECTURA. Los writes (pause/resume/budget/create) llegan en las
# FASE 16-18, detras de la Policy Layer del Action Graph + aprobacion humana.
MCP_META_ADS_ALLOW_WRITES = config("MCP_META_ADS_ALLOW_WRITES", default=False, cast=bool)
# Directorio donde mcp_client/storage.py persiste el registro de cliente OAuth y
# el refresh token. DEBE ser un volumen montado y NO versionado. Nunca en logs.
MCP_TOKEN_STORE_DIR     = config("MCP_TOKEN_STORE_DIR", default="/data/mcp")
# Puerto local para el callback del flujo de autorizacion one-shot
# (python -m mcp_client.authorize). Solo se usa durante esa autorizacion manual.
MCP_OAUTH_CALLBACK_PORT = config("MCP_OAUTH_CALLBACK_PORT", default=8765, cast=int)
# Timeout (s) de cada operacion MCP (list_tools / call_tool).
MCP_CALL_TIMEOUT_S      = config("MCP_CALL_TIMEOUT_S", default=30, cast=int)
