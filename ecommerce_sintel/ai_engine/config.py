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

# HARDENING F2 (2026-09-24, plan PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md
# sec. 6, propuesta ai_engine_adk/.AGENT/HARDENING_F2_PROPOSAL_2026-09-24.md): secreto de servicio Django -> ADK
# (cabecera X-AI-Service-Token en /chat). REQUIRED=false (default) solo AVISA en logs si falta/no coincide, para
# desplegar en 2 pasos sin cortar el chat; REQUIRED=true responde 401. PREVIOUS permite rotar sin corte.
AI_SERVICE_TOKEN          = config("AI_SERVICE_TOKEN", default="")
AI_SERVICE_TOKEN_PREVIOUS = config("AI_SERVICE_TOKEN_PREVIOUS", default="")
AI_SERVICE_TOKEN_REQUIRED = config("AI_SERVICE_TOKEN_REQUIRED", default=False, cast=bool)

# HARDENING F3 (2026-09-24, propuesta ai_engine_adk/.AGENT/HARDENING_F3_PROPOSAL_2026-09-24.md).
# C1 -- presupuesto de turno (calibrar tras la prueba de carga F13). AI_*_MAX_OUTPUT_TOKENS cuentan tambien los
# tokens de RAZONAMIENTO de Qwen3.5 (num_predict): 1024/2048 en vez de los 512/1024 propuestos, para no cortar
# respuestas legitimas ni dejar el contenido vacio cuando el razonamiento consume el limite.
AI_TURN_MAX_SECONDS          = config("AI_TURN_MAX_SECONDS", default=120, cast=int)
AI_TURN_MAX_LLM_CALLS        = config("AI_TURN_MAX_LLM_CALLS", default=6, cast=int)
AI_SUPPORT_MAX_OUTPUT_TOKENS = config("AI_SUPPORT_MAX_OUTPUT_TOKENS", default=1024, cast=int)
AI_ADMIN_MAX_OUTPUT_TOKENS   = config("AI_ADMIN_MAX_OUTPUT_TOKENS", default=2048, cast=int)
# C2 -- circuit breaker por proveedor de la cadena de modelos (model_runtime.py).
AI_BREAKER_ENABLED        = config("AI_BREAKER_ENABLED", default=True, cast=bool)
AI_BREAKER_FAILURES       = config("AI_BREAKER_FAILURES", default=3, cast=int)
AI_BREAKER_WINDOW_SECONDS = config("AI_BREAKER_WINDOW_SECONDS", default=60, cast=int)
AI_BREAKER_OPEN_SECONDS   = config("AI_BREAKER_OPEN_SECONDS", default=60, cast=int)

# HARDENING F4 (2026-09-24, propuesta ai_engine_adk/.AGENT/HARDENING_F4_PROPOSAL_2026-09-24.md).
# AI_TOOL_STRICT_ARGS=false (default) = MONITOR: valida argumentos y solo loguea `ai_tool_args_invalid`; true = rechaza (400).
AI_TOOL_STRICT_ARGS             = config("AI_TOOL_STRICT_ARGS", default=False, cast=bool)
AI_TOOL_IDEMPOTENCY_ENABLED     = config("AI_TOOL_IDEMPOTENCY_ENABLED", default=True, cast=bool)
AI_TOOL_IDEMPOTENCY_TTL_SECONDS = config("AI_TOOL_IDEMPOTENCY_TTL_SECONDS", default=600, cast=int)

# FASE 4b/5 (mision de simplificacion arquitectonica, 2026-09-14): CHROMA_*/
# EMBEDDING_*/DOCS_SPECS_PATH/INGESTION_BATCH_SIZE/MAX_RETRIEVER_CHUNKS/
# CODEBASE_PATH retirados -- este proceso ya no calcula embeddings ni
# mantiene un vector store propio (ChromaDB eliminado, FASE 4b), y ya no
# escanea el codigo fuente del repo para memoria/manifiestos/indices
# (incremental_updater.py/memory_builder.py/ai_manifest.py/
# specialized_retrieval.py retirados, FASE 5 -- alimentaban exclusivamente
# el pipeline de generacion de codigo ya retirado en FASE 4a). El RAG del
# chat vive en Django/ai_knowledge (PostgreSQL+pgvector); su propia
# configuracion de embeddings (AIChannelConfig.CHANNEL_EMBEDDINGS) es
# independiente de este archivo. El volumen `.:/workspace:ro` (docker-compose.yml)
# ya no tiene consumidor -- retirado en el mismo cambio. Ver
# AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md.

# B2 (AUDITORIA/16): checkpointer del Action Graph (redis_checkpointer.py) -- DB separada de
# Django (Channels=0, Cache=1) para no compartir namespace de claves con nada mas.
CHECKPOINTER_REDIS_URL = config("CHECKPOINTER_REDIS_URL", default="redis://redis:6379/2")

OPENAI_API_KEY      = config("OPENAI_API_KEY", default="")
ANTHROPIC_API_KEY   = config("ANTHROPIC_API_KEY", default="")

# Mision RAG-POST2 (FASE 7, 2026-09-16): backend de sesion de google-adk,
# solo relevante para ai_engine_adk (sintel_root_workflow.py) -- el sistema
# OLD (este mismo config.py, compartido) no lee estas dos variables. Default
# "memory" a proposito: cualquier entorno que no las configure explicitamente
# (tests, un checkout nuevo sin la DB de sesiones provisionada) se comporta
# EXACTAMENTE igual que antes de esta fase (InMemorySessionService), cero
# cambio de comportamiento silencioso. Ver AUDITORIA/RAG_POST2_BASELINE.md
# hallazgo PG-1 y ai_engine_adk/tests/conftest.py (fuerza "memory" siempre
# en tests, nunca depende de un Postgres real).
ADK_SESSION_BACKEND = config("ADK_SESSION_BACKEND", default="memory")
ADK_SESSION_DB_URL  = config("ADK_SESSION_DB_URL", default="")

# ─── AI Core Fase 1: puente seguro Django <-> AI Engine ──────────────────────
# JWT_SECRET_KEY es la MISMA SIGNING_KEY de SimpleJWT en Django (settings/base.py,
# SIMPLE_JWT["SIGNING_KEY"]) -- llega por env_file compartido, nunca hardcodeada.
# El motor solo VALIDA tokens emitidos por Django; jamas emite los propios.
JWT_SECRET_KEY          = config("JWT_SECRET_KEY", default="")
DJANGO_INTERNAL_API_URL = config("DJANGO_INTERNAL_API_URL", default="http://django:8000/api/v1")

# 2 bugs reales encontrados en produccion (2026-09-14, migracion ADK-11, ver
# AUDITORIA/ADK_CUTOVER_PLAN.md) -- ninguno detectado antes porque
# AI_SUPPORT_CHAT_ENABLED esta en false en produccion desde siempre: ninguna
# Tool ni resolucion de identidad se habia ejecutado ahi hasta hoy.
#
# 1. ALLOWED_HOSTS estricto (settings/base.py): una llamada interna con
#    Host: django:8000 (nombre de servicio Docker) la rechaza Django con
#    DisallowedHost -- el propio healthcheck de sintel_prod_django ya
#    trabaja alrededor de esto con "-H Host: api.sintel.net.co".
# 2. SECURE_SSL_REDIRECT=True + SECURE_PROXY_SSL_HEADER (settings/
#    production.py): Django confia en X-Forwarded-Proto (que nginx agrega
#    normalmente) para saber si la request original fue HTTPS. Una llamada
#    interna que bypasea nginx (como esta, directo al servicio "django")
#    nunca trae ese header -- Django la redirige con 301 a HTTPS, rompiendo
#    la llamada (httpx no sigue redirects por defecto).
#
# Vacio por defecto (sin cambio de comportamiento en dev/staging, donde
# ALLOWED_HOSTS/SECURE_SSL_REDIRECT ya son permisivos) -- se define
# explicitamente en docker-compose.prod.yml para sintel_ai/sintel_ai_adk.
DJANGO_INTERNAL_HOST_HEADER = config("DJANGO_INTERNAL_HOST_HEADER", default="")


def internal_django_headers(extra: dict | None = None) -> dict:
    """Headers para CUALQUIER llamada HTTP interna a Django
    (DJANGO_INTERNAL_API_URL) -- unico punto que agrega los overrides que
    produccion necesita para que Django trate la llamada como legitima
    (ver DJANGO_INTERNAL_HOST_HEADER arriba). Vacio por defecto: en
    dev/staging esto es un no-op, `extra` se devuelve tal cual."""
    headers = dict(extra or {})
    if DJANGO_INTERNAL_HOST_HEADER:
        headers["Host"] = DJANGO_INTERNAL_HOST_HEADER
        # Mismo valor que nginx.prod.conf agrega para trafico real -- sin
        # esto, SECURE_SSL_REDIRECT redirige la llamada interna con 301
        # (ver hallazgo 2 arriba). No debilita seguridad real: esta llamada
        # nunca sale del network interno de Docker.
        headers["X-Forwarded-Proto"] = "https"
    return headers

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
