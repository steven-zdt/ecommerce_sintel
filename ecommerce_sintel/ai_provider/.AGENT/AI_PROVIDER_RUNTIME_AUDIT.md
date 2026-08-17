# AI_PROVIDER_RUNTIME_AUDIT

**Fecha:** 2026-08-13. FASE 0 del plan maestro "AI Provider Runtime" (47 fases).
Documento de solo lectura -- **ningun archivo de codigo fue modificado para
producir esta auditoria.** Cubre exactamente los items pedidos, con ruta de
archivo y linea donde aplica. La mayor parte de este contenido ya fue verificado
en vivo (no solo leido) durante la campaña anterior en esta misma sesion
("CONFIGURACION DINAMICA DE MODELOS LOCALES", FASE 0-6, ver
`ai_provider/.AGENT/FASE1_MODELOS.md` a `FASE5_FRONTEND.md`) -- esta auditoria
reusa esa evidencia donde aplica y la ampara con verificaciones nuevas donde el
plan actual pide mas detalle (patron de auditoria, cache Redis, secretos).

---

## 1. Variables de entorno

| Variable | Valor real (dev) | Definida en | Consumida en |
|---|---|---|---|
| `AI_ENGINE_URL` | `http://sintel_ai:8100` (default) | `.env` (nombre presente, valor no impreso aqui) / `ecommerce/settings/base.py:341` | `support/services/ai_bridge.py::ask_ai()` (`settings.AI_ENGINE_URL`) |
| `AI_SUPPORT_CHAT_ENABLED` | `True` (confirmado en runtime, PASO 4 de la certificacion E2E previa) | `ecommerce/settings/base.py:343`, default `False` | `support/services/ai_bridge.py::is_ai_mode_active()` |
| `AI_BOT_EMAIL` | `asistente.ia@sintel.internal` (default) | `ecommerce/settings/base.py:346` | `support/services/ai_bridge.py::get_ai_bot_user()` -- usuario `is_active=False`, password inutilizable, firma los `ChatMessage` del bot |
| `LOCAL_MODEL_CHAIN` | `ollama\|ollama-nativo\|http://sintel_ollama:11434\|llama3.1:8b` (default, formato `nombre\|tipo\|base_url\|modelo[\|api_key_env]`, entradas separadas por `;`) | `ai_engine/config.py:21-24` | `ai_engine/llm_factory.py::parse_local_model_chain()`/`get_llm()`/`get_dynamic_llm()` (fallback) |
| `OLLAMA_BASE_URL` | `http://sintel_ollama:11434` (default) | `ai_engine/config.py:20`; tambien inyectada inline en `docker-compose.yml` service `sintel_ai` | Default de `LOCAL_MODEL_CHAIN`, y usada por `_ensure_ollama_models()` en `ai_engine/main.py` (pre-carga de modelos al arrancar) |

`AI_PROVIDER_ENCRYPTION_KEY` (agregada en la campaña previa, FASE 1) **no esta
definida en `.env`** -- cae al fallback documentado (deriva de `SECRET_KEY`).
Confirmado por `grep` de nombres de variable en `.env`: no aparece.

---

## 2. Configuracion Redis (3 bases de datos separadas, mismo Redis)

| DB | Uso | Config exacta |
|---|---|---|
| `0` | Django Channels (WebSocket) + Celery broker/backend | `CHANNEL_LAYERS['default']['CONFIG']['hosts'] = [REDIS_URL]` (`ecommerce/settings/base.py:121-125`); `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND = REDIS_URL` (linea 290-291). `REDIS_URL` default `redis://localhost:6379/0` (dev real: `redis://redis:6379/0` via `.env`) |
| `1` | Cache de Django (`django.core.cache`) | `ecommerce/settings/base.py:159-163`: `_redis_cache_base = REDIS_URL.rsplit('/',1)[0]`, `CACHES['default']['LOCATION'] = f'{base}/1'`, backend `django.core.cache.backends.redis.RedisCache`. Alternable a `locmem` via `CACHE_BACKEND=locmem` (no usado en dev real) |
| `2` | Checkpointer del Action Graph (`ai_engine`, conversaciones multi-turno) | `ai_engine/config.py:37`: `CHECKPOINTER_REDIS_URL = redis://redis:6379/2` (hardcoded en `docker-compose.yml`, no via `.env`) |

**Hallazgo relevante para FASE 20 (Runtime Cache) del plan actual:** el cache
dinamico que ya existe (`ai_engine/llm_factory.py::get_dynamic_llm()`, agregado
en la campaña previa) es un **dict en memoria del proceso Python de `sintel_ai`**
con TTL de 15s (`_DYNAMIC_CHAIN_CACHE_TTL_SECONDS`) -- NO usa Redis. Logra "sin
reiniciar AI Engine" pero via *polling* (ventana de hasta 15s de staleness), no
via invalidacion push instantanea. Si FASE 20-21 exige invalidacion inmediata
(`ai_runtime:support` en Redis + invalidar en el momento del cambio), esto
requiere que `sintel_ai` (proceso FastAPI separado de Django) tambien se
conecte a Redis directamente -- hoy `sintel_ai` NO tiene ningun cliente Redis
para cache general, solo `CHECKPOINTER_REDIS_URL` para el checkpointer de
LangGraph (uso distinto, ya conectado via `redis_checkpointer.py`). Reusar esa
misma conexion para una clave de cache adicional es viable y no requeriria una
dependencia nueva.

---

## 3. Configuracion Docker

- **`docker-compose.yml`** (dev): 10 servicios -- `redis`, `db` (Postgres),
  `django` (bind-mount `.:/code`, `DEV_RELOAD` activo via `watchmedo`
  force-polling cada 2s -- necesario porque el filesystem de Docker Desktop en
  Windows no siempre propaga eventos nativos), `frontend` (bind-mount, Vite
  `--host`, `CHOKIDAR_USEPOLLING=true` por el mismo motivo, `restart:
  unless-stopped` agregado 2026-08-10 tras un incidente real de crash sin
  auto-recuperacion), `nginx`, `celery_worker`, `celery_beat`, `sintel_ollama`,
  `sintel_chromadb`, `sintel_ai`.
- **`sintel_ai` (AI Engine) -- hallazgo critico confirmado en la campaña
  previa:** `volumes: - .:/workspace:ro` (**solo lectura**, usado unicamente
  para que el motor indexe la base de conocimiento -- `CODEBASE_PATH=/workspace`)
  y `- ../docs/specs:/docs/specs:ro`. **NO hay bind-mount del codigo de
  `ai_engine/` a `/app`** -- la imagen se construye con `build: context:
  ./ai_engine` y el codigo vive horneado ahi. `uvicorn --reload` (ver
  `ai_engine/main.py` docstring) observa `/app` DENTRO del contenedor, que
  nunca cambia con ediciones del host. **Confirmado empiricamente:** un
  `docker restart` tras editar `llm_factory.py`/`main.py` NO reflejo los
  cambios (`grep` dentro del contenedor mostro el codigo viejo); un
  `docker compose build sintel_ai && docker compose up -d sintel_ai` real si
  los reflejo. Cualquier fase de este plan que modifique codigo Python de
  `ai_engine/` (FASE 7-12, 19, etc.) **debe terminar con un build real**, no
  un simple restart.
- **`docker-compose.prod.yml`:** header explicito (lineas 13-16) dice que
  `sintel_ai`/`sintel_ollama`/`sintel_chromadb` se excluyen deliberadamente de
  produccion -- **el motor de IA no corre en produccion hoy.** `nginx.prod.conf`
  incluye `nginx-common.conf`, que bloquea `location /api/v1/internal/`
  (`deny all`) -- el aislamiento real de `/internal/*` es de red, documentado
  explicitamente asi en `users/api/internal.py`.
- **Dev nginx** (`nginx.conf`, 56 lineas) no incluye `nginx-common.conf` y no
  tiene ningun bloque para `/internal/` -- en dev, `/api/v1/internal/*` es
  alcanzable directamente via `localhost:8000` (Django publica su puerto al
  host), sin ningun bloqueo adicional. Esto es una caracteristica preexistente
  de TODO el prefijo `/internal/ai/*` (no especifica de `ai_provider`) y ya
  estaba asi antes de esta campaña.

---

## 4. AI Engine (`ai_engine/`, proceso FastAPI separado de Django)

- **Arranque** (`main.py::lifespan`): `_ensure_ollama_models()` (pre-pull) ->
  `get_embeddings()` -> `get_vectorstore()` -> `get_llm()` (construye
  `_STATE['llm']` UNA vez, desde `LOCAL_MODEL_CHAIN` -- usado por `/generate`,
  AI Editor) -> carga/split de documentos (KB) -> indices especializados ->
  manifests. Sin `--workers` (proceso unico) -- por eso cualquier llamada
  bloqueante en el hilo principal degrada TODO el proceso (nota explicita en
  `llm_factory.py` sobre `LLM_TIMEOUT_SECONDS=90`).
- **`/chat`** (linea 265+): valida JWT (`decode_django_jwt`, misma
  `JWT_SECRET_KEY` que Django), resuelve `llm` real via `await
  get_dynamic_llm()` (agregado en la campaña previa -- consulta Postgres via
  Django, cae a `LOCAL_MODEL_CHAIN`/`_STATE['llm']` estatico si no hay config
  real), ejecuta `run_action_chat()` (Action Graph). Catch-all de excepcion no
  controlada -> `ChatResponse` con mensaje de degradacion +
  `metrics={"engine_unavailable": True}` (nunca un 500 crudo).
- **`llm_factory.py`** (ver seccion 6, detallado aparte por ser uno de los
  items pedidos explicitamente).
- **`get_dynamic_llm()`** ya existe (agregado en la campaña previa) -- FASE 19
  de este plan (`RuntimeConfigResolver`) puede reusarlo o reemplazarlo; el
  nombre/forma actual no coincide exactamente con lo que este plan describe
  (`get_llm(channel="support")` -> `RuntimeConfigResolver` -> ... -> `Provider
  Adapter` -> `LLM`) -- hoy no existe una clase `RuntimeConfigResolver` ni
  `ProviderAdapter` (`base.py`/`ollama.py`/`openai_compatible.py`/
  `anthropic.py` de FASE 7-10 de este plan tampoco existen aun) -- `_build_model()`
  en `llm_factory.py` es una funcion, no una jerarquia de adapters.

---

## 5. Frontend (Vue 3 + Vite + Pinia)

- **`SupportChatWidget.vue`** (`frontend/src/components/customer/ui/`):
  visible solo si `authStore.isAuthenticated && !authStore.isAdmin` (widget de
  cliente, no de admin). `connectWs()`: llama `await refreshAccessToken()`
  SIEMPRE antes de conectar (fix real de produccion 2026-07-31: el WS nunca
  pasaba por el interceptor de Axios, un tab abierto >15min reusaba un access
  token vencido en cada reintento) -> construye `ws://.../ws/support/chat/?token=<jwt>`
  (+ `context_type`/`context_uuid` si hay contexto pendiente) -> `onopen`
  (`wsReady=true`, resetea backoff, arranca heartbeat) -> `onmessage` maneja 3
  tipos: `history` (carga mensajes+contexts, resetea estado CSAT),
  `chat_message` (push a `messages`, incrementa `unreadCount` si viene de
  admin y el widget esta cerrado), `room_closed` (activa prompt CSAT) ->
  `onclose` reconecta con backoff exponencial+jitter (3s-30s). Heartbeat cada
  25s (`ping`/`pong`), fuerza cierre si no hay `pong` en 10s.
- **Dashboard/panel admin:** `frontend/src/apps/admin/router.js` importa
  route-files por dominio (`adminOps.routes.js`, etc.) -- `/panel/soporte`
  (`SupportDashboardView.vue`, analitica de chat) y `/panel/soporte/ia-config`
  (`AIProviderConfigView.vue`, agregado en la campaña previa) son rutas
  **distintas** bajo el mismo grupo de sidebar "Soporte". `useApi()` baseURL =
  `/api/v1/` -- servicios admin llaman rutas relativas con prefijo `dashboard/`
  explicito (confirmado contra `store/paymentAdmin.js`).

---

## 6. Dashboard (`dashboard/` app -- BFF administrativo)

- **Patron BFF confirmado** (`dashboard/api/views.py:1-6`, docstring literal):
  *"Unified administrative gateway (BFF) for the admin SPA. All ViewSets
  delegate to dashboard.services.admin_orchestrators. Zero ORM access in this
  layer."* -- las Views NUNCA tocan el ORM directo, siempre pasan por un
  `*Orchestrator` en `dashboard/services/admin_orchestrators.py`.
- **Rutas** (`dashboard/api/urls.py`): TODAS bajo `/api/v1/dashboard/`
  (`ecommerce/urls.py:76`: `path('api/v1/dashboard/', include('dashboard.api.urls'))`).
  Router `DefaultRouter()` central; el archivo principal `views.py` crecio
  demasiado (2900+ lineas) y el proyecto ya tiene precedente de dividirlo en
  archivos hermanos dentro de `dashboard/api/` (`services_catalog_views.py`,
  `renting_catalog_views.py`, `package_views.py`, `content_blocks_views.py`,
  `shop_catalog_views.py`, `catalog_child_views.py` -- y ahora tambien
  `ai_provider_views.py`/`ai_provider_serializers.py`, agregados en la
  campaña previa siguiendo ese mismo criterio de split).
- **`ADMIN_PERMISSIONS = [permissions.IsAuthenticated, IsAdminUser]`**
  (`dashboard/api/views.py:100`) -- constante compartida, importada por los
  archivos hermanos.
- **Rutas ya existentes para AI (de la campaña previa, no de este plan):**
  `/api/v1/dashboard/ai-providers/` (CRUD + `/test-connection/` +
  `/discover-models/` + `/models/`), `/api/v1/dashboard/ai-channel-config/`
  (`/set-primary/` + `/set-fallback-chain/`). **Difieren del esquema de rutas
  que pide FASE 14 de este plan** (`/api/v1/dashboard/support/ai/config/`,
  `/api/v1/dashboard/support/ai/providers/`, etc. -- namespace anidado bajo
  `support/`). Decision pendiente: renombrar/mover las rutas existentes al
  namespace `support/ai/...` que pide este plan, o mantener el namespace plano
  `ai-providers/`/`ai-channel-config/` ya construido y probado. Ver seccion
  "Decisiones a tomar" al final.

---

## 7. `support/services/ai_bridge.py` (linea por linea relevante)

- `get_ai_bot_user()`: usuario bot `get_or_create` por `AI_BOT_EMAIL`,
  `is_active=False` forzado, password inutilizable -- nunca puede
  autenticarse.
- `is_ai_mode_active(room)`: `AI_SUPPORT_CHAT_ENABLED and room.status ==
  STATUS_OPEN and not room.ai_paused and room.assigned_admin_id is None` --
  las 4 condiciones exactas, confirmadas en runtime (positivo y negativo) en
  la certificacion E2E previa.
- `is_ai_rate_limited(room)`: `cache.add` atomico (evita race condition),
  ventana fija de 600s, limite 20 turnos/sala -- usa el CACHE de Django (DB 1
  de Redis, seccion 2).
- `ask_ai(user, message, conversation_id)`: **sincrono** (`requests.post`).
  **CERRADO 2026-08-17**: ya NO es el punto de entrada del widget web --
  `SupportChatConsumer` usa la nueva `ask_ai_async()` (`httpx.AsyncClient`) para
  no ocupar el thread pool compartido de Channels durante la llamada al AI
  Engine. `ask_ai()` sincrono se mantiene, sin cambios, solo para WhatsApp
  (`notifications/tasks.py`, contexto de Celery, sin event loop que proteger).
  Log `[AI_BRIDGE] request/response` con latencia/tokens/tools vive en
  `_process_chat_response()`, compartido por ambas variantes -- sigue siendo el
  punto unico de trazabilidad real de `sintel_ai` (usado tanto por el widget web
  como por WhatsApp).
- `ai_response_opened_ticket(ai_response)`: helper para detectar handoff
  exitoso (`abrir_ticket_soporte` sin error) -- usado por el consumer para
  decidir si pausar la IA.

---

## 8. `support/consumers.py` -- `SupportChatConsumer` (flujo real)

- **Conexion:** `channels_auth.py` valida `?token=` -- si el usuario es
  `is_staff`, entra como ADMIN (`group_add('support_admins')`, no crea
  `ChatRoom`); si es cliente, `get_or_create_room()` (reusa la sala `OPEN`
  existente, nunca crea una segunda mientras haya una abierta), `group_add`
  a `chat_{user.uuid}`, envia `history` (mensajes+contexts de la sala).
  **Confirmado en runtime:** un usuario staff conectando al mismo endpoint
  WS NO recibe un frame `history` -- toma la rama admin, comportamiento
  distinto segun rol, mismo endpoint (hallazgo real de la certificacion
  previa, causo un timeout en un test propio hasta corregirlo).
- **Mensaje entrante (`receive()`):** guarda `ChatMessage` real (`sender=user,
  is_admin=False`) -> `group_send` inmediato del propio mensaje (eco a todos
  los conectados a esa sala, incluidos admins) -> si `is_ai_mode_active(room)`
  y no rate-limited: dispara `_ai_reply()` (async task).
- **`_ai_reply(room, text)`:** `await self._ask_ai(room, text)`
  (`database_sync_to_async` envolviendo la llamada sincrona de `ai_bridge`) ->
  si respuesta vacia/motor caido: `_save_ai_degraded_marker()` (mensaje fijo +
  `ai_metrics={"engine_unavailable": True}`) -- si respuesta real: guarda
  `ChatMessage(sender=AI_BOT)` con `ai_metrics` reales, y si
  `ai_response_opened_ticket()`: pausa la IA (`ai_paused=True`) -- luego
  `group_send` a AMBOS grupos (`chat_{user.uuid}` y `support_admins`) para que
  el panel admin vea la respuesta en vivo tambien. Tambien dispara WhatsApp
  fire-and-forget si aplica (Fase 16, no bloquea el WS).
- **Ping/pong:** responde `pong` sin consumir el limite de flood de mensajes
  normales (test dedicado ya existente).

---

## 9. `ai_engine/llm_factory.py` (estado actual completo)

- `parse_local_model_chain(raw)`: parsea `nombre|tipo|base_url|modelo[|api_key_env]`
  separado por `;`, ignora entradas invalidas con warning (no tumba el
  arranque).
- `_resolve_api_key(entry, default)` (agregado en la campaña previa):
  prioriza `entry['api_key_value']` (ya descifrado, viene de la config
  dinamica) sobre `entry['api_key_env']` (nombre de variable, camino legacy de
  `LOCAL_MODEL_CHAIN`) sobre `default`.
- `_build_model(entry)`: switch por `kind` (`ollama-nativo` -> `ChatOllama`,
  `anthropic` -> `ChatAnthropic`, cualquier otro -> `ChatOpenAI` asumido
  `openai-compatible`) -- **no es una jerarquia de adapters con interfaz
  comun** (`BaseProviderAdapter` de FASE 7 de este plan no existe todavia,
  esta logica vive como funcion plana).
- `get_llm()`: construye la cadena SOLO desde `LOCAL_MODEL_CHAIN`, llamada UNA
  vez en el `lifespan` de `main.py` -> `_STATE['llm']` -- usado por
  `/generate` (AI Editor). No modificado por este plan hasta ahora.
- `get_dynamic_llm(channel)` (agregado en la campaña previa): cache dict en
  memoria (15s TTL, NO Redis -- ver seccion 2), consulta `GET
  /api/v1/internal/ai/provider-config/` (`httpx.AsyncClient`, no bloqueante),
  cae a `LOCAL_MODEL_CHAIN` si la cadena dinamica esta vacia o Django es
  inalcanzable. Usado SOLO por `/chat`. Este es el punto de entrada que FASE
  19 (`RuntimeConfigResolver`) de este plan probablemente reemplazaria o
  envolveria -- decision pendiente (ver "Decisiones a tomar").

---

## 10. Patron Commands/Selectors (confirmado, consistente en todo el proyecto)

`<app>/services/selectors.py` (lecturas, static methods, sin efectos
secundarios) + `<app>/services/commands.py` (escrituras,
`@transaction.atomic`, whitelist explicito de campos editables). Las Views
(incluidas las del BFF de `dashboard`) nunca tocan el ORM directo -- siempre
via un Orchestrator (`dashboard/services/admin_orchestrators.py`) que a su vez
llama Selectors/Commands de la app dueña del dominio. Ya implementado para
`ai_provider` en la campaña previa: `AIProviderSelector`/`AIProviderCommands`,
`AIModelCommands` (falta `AIModelSelector` como clase separada -- hoy
`get_model()` vive en `AIProviderSelector`, no en su propia clase -- FASE 5 de
este plan pide `AIModelSelector` explicito, gap real a cerrar), y
`AIChannelConfigSelector`/`AIChannelConfigCommands`.

---

## 11. Patron de auditoria (confirmado, y gap real encontrado)

`security.SecurityEvent` (append-only, nunca editado/borrado) + `SecurityCommands.log_event(event_type, request=None, user=None, severity=INFO, metadata={})`
como UNICO punto de escritura (`security/CLAUDE.md`, regla explicita: nunca
`SecurityEvent.objects.create()` directo). Tipos ya existentes relevantes:
`AI_ACTION_EXECUTED` (acciones de escritura ejecutadas POR el AI Core/chatbot,
via `ecommerce/internal_ai_utils.py::log_ai_action(request, tool, metadata)` --
usado por las Tools de escritura del chatbot, ej. `core/api/internal_ai.py`),
`ADMIN_RESOURCE_DELETED` (tipo generico ya existente para cualquier borrado
desde el panel admin, agregado tras un hallazgo real de auditoria: "de las
decenas de acciones administrativas destructivas del BFF admin, solo 3 puntos
dejaban SecurityEvent").

**Gap real confirmado:** `AIProviderCommands`/`AIModelCommands`/
`AIChannelConfigCommands` (creados en la campaña previa) **no llaman
`SecurityCommands.log_event()` en ningun punto** -- crear/editar/eliminar/
activar/desactivar un proveedor, probar conexion, o cambiar el modelo
primario/fallback hoy **no dejan ningun rastro de auditoria**. FASE 34 de este
plan pide exactamente esto (`AI_PROVIDER_CREATED`, `AI_PROVIDER_UPDATED`,
etc.) -- **no existen como `EVENT_CHOICES` en `security/models.py` todavia**,
habria que agregarlos (mismo patron que `PAYMENT_FEATURE_FLAG_CHANGED`, un
tipo por accion relevante en vez de reusar `ADMIN_RESOURCE_DELETED` para todo).

---

## 12. Configuracion de secretos

- `python-decouple` (`config()`) en todos los `settings.py`/`config.py` --
  nunca `os.environ` directo. `.env` real tiene 60+ variables (nombres
  confirmados via `grep`, ningun valor impreso en este documento). Ningun
  secreto hardcodeado encontrado en `settings/base.py`/`ai_engine/config.py`.
- **Cifrado en reposo:** SOLO existe para `AIProvider.api_key`
  (`shared/fields.py::EncryptedTextField`, Fernet, agregado en la campaña
  previa -- **no existia ningun mecanismo de cifrado en el repo antes de
  eso**). El resto de credenciales del sistema (`OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, `DB_PASSWORD`, `JWT_SECRET_KEY`, etc.) siguen en texto
  plano en `.env` -- consistente con como Django siempre las trato, no es una
  regresion de este plan.
- **Nunca expuestas al frontend:** `AIProviderSerializer` (lectura, panel
  admin) solo serializa `has_api_key` (bool) -- confirmado con test real
  (`test_create_provider_never_returns_api_key_in_response`) y con
  verificacion manual en DevTools durante la prueba en vivo de la campaña
  previa.
- **Si expuestas al consumidor interno sancionado:** `GET
  /api/v1/internal/ai/provider-config/` SI devuelve `api_key` descifrada --
  necesaria para que `ai_engine` construya el cliente LLM real. Documentado
  explicitamente como decision deliberada (no un descuido) en el docstring de
  `ai_provider/api/internal_ai.py`.
- **En logs:** `ai_bridge.py`/`llm_factory.py` loguean `latency_ms`,
  `tokens`, nombre del motor/modelo -- nunca la API key ni el JWT completo.
  No verificado exhaustivamente linea-por-linea todavia (pendiente, coincide
  con el alcance de FASE 33 de este plan -- "Pen test de... logs").

---

## Resumen de gaps reales encontrados (para las fases siguientes de este plan)

1. **Sin auditoria** en las acciones de `ai_provider` (seccion 11) -- FASE 34.
2. **Cache dinamico en memoria, no Redis** -- logra "sin reiniciar" via TTL de
   15s, no invalidacion instantanea -- FASE 20-21 necesitaria conectar
   `sintel_ai` a Redis para cache general (hoy solo tiene el checkpointer).
3. ~~**`ai_bridge.ask_ai()` sigue siendo sincrono/bloqueante**~~ **CERRADO
   2026-08-17** (auditoria E2E de cierre del AI Engine): nueva `ask_ai_async()`
   (`httpx.AsyncClient`) reemplaza el uso de `ask_ai()` envuelto en
   `database_sync_to_async` dentro de `SupportChatConsumer` -- ya no ocupa el
   thread pool compartido de Channels durante la llamada al AI Engine. `ask_ai()`
   sincrono se mantiene solo para WhatsApp (Celery, sin event loop que proteger).
   Ver `ai_engine/.AGENT/SUPPORT_AI_CERTIFICATION.md`, Historial 2026-08-17, item 5,
   con test de regresion real (`test_ia_lenta_no_serializa_via_thread_pool_compartido`).
4. **No existe jerarquia de Provider Adapters** (`BaseProviderAdapter` +
   `ollama.py`/`openai_compatible.py`/`anthropic.py`) -- la logica vive como
   funcion plana en `llm_factory.py::_build_model()`. Funcionalmente
   equivalente pero no extensible del mismo modo que pide FASE 7-10 de este
   plan.
5. **`AIModelSelector` no existe como clase separada** -- FASE 5 de este plan
   la pide explicita; hoy sus responsabilidades viven mezcladas en
   `AIProviderSelector`.
6. **Rutas del dashboard no coinciden con el namespace que pide FASE 14**
   (`support/ai/...` anidado vs. `ai-providers/`/`ai-channel-config/` planos,
   ya construidos y probados en la campaña previa).
7. **Connection test / model discovery no diferencian codigos de error**
   como pide FASE 11 (`DNS`/`CONNECTION_REFUSED`/`TIMEOUT`/`UNAUTHORIZED`/
   `MODEL_NOT_FOUND`/etc.) -- hoy `connection_probe.py` devuelve
   `(ok: bool, latency_ms, error: str libre)`, sin codigo categorizado.
8. **No hay verificacion de "tool calling soportado"** por proveedor (FASE 27:
   "un proveedor que solamente genera texto NO debe marcarse PROVIDER READY")
   -- el test de conexion actual solo verifica disponibilidad HTTP, no
   `bind_tools()`.

Ninguno de estos gaps es un `BLOCKER` (nada roto, nada inseguro expuesto,
0 regresiones) -- son diferencias reales entre el nivel de rigor de la campaña
previa (funcional, probado end-to-end, pero pragmatico) y el nivel que este
plan de 47 fases pide (adapters formales, auditoria completa, cache Redis con
invalidacion instantanea, codigos de error categorizados, verificacion de tool
calling por proveedor).

---

## Decisiones a tomar antes de continuar (bloqueantes para elegir el camino)

1. **¿Refactorizar lo ya construido (FASE 1-6 previas) hacia la estructura
   exacta de este plan (namespaces de ruta, `AIModelSelector` separado,
   adapters formales), o extenderlo respetando lo que ya funciona y esta
   probado?** Recomendacion: extender, no reescribir -- lo existente pasa
   126+ tests reales y esta certificado en vivo; renombrar rutas ya
   consumidas por el frontend real es riesgo sin beneficio funcional.
2. **¿El cache Redis de FASE 20 reemplaza el TTL de 15s actual, o coexiste?**
   Recomendacion: agregar Redis como cache primario con invalidacion en el
   momento del cambio (Commands hacen `cache.delete()`/`cache.set()` en la
   misma transaccion), TTL de 15s como red de seguridad secundaria si Redis
   fallara -- no eliminar el fallback a `LOCAL_MODEL_CHAIN`.
3. **¿`ai_bridge.py` async (FASE 35) se hace en esta campaña o se documenta
   como deuda tecnica conocida?** El plan lo pide explicitamente y marca
   "Validar: throughput, timeout, concurrent users, fallback. No cambiar
   comportamiento funcional" -- es un cambio de infraestructura real
   (reemplazar `requests` por `httpx.AsyncClient` dentro de
   `database_sync_to_async`, o quitar ese wrapper y usar await nativo) que
   toca el path caliente de cada mensaje de chat -- amerita su propio ciclo
   de prueba dedicado, no un cambio de paso.

---

## CHECKPOINT

**Resultado: PASS**

- Ningun `BLOCKER` encontrado (nada roto, ningun secreto expuesto, ninguna
  regresion).
- 8 gaps reales identificados y documentados arriba, todos categorizados como
  "diferencia de rigor esperada", no como fallos.
- 3 decisiones de diseño identificadas que requieren eleccion explicita antes
  de FASE 1 de este plan (ver seccion anterior) -- de continuar automaticamente
  sin resolverlas, se tomaran las recomendaciones indicadas (extender no
  reescribir; Redis+invalidacion con TTL como red de seguridad; async bridge
  como fase propia).

**-> Continuar a FASE 1.**
