# Flujo Completo — Sintel AI Engine

> Microservicio FastAPI autónomo. Puerto **8100**. Genera y valida código para el proyecto
> Sintel E-Commerce REST v5 mediante RAG (LangChain + LangGraph + ChromaDB + Ollama).

---

## 1. Servicios externos requeridos

| Servicio        | Container Docker        | Puerto | Rol                            |
|-----------------|-------------------------|--------|--------------------------------|
| ChromaDB        | `sintel_chromadb`       | 8200   | Vector store (embeddings)      |
| Ollama          | `sintel_ollama`         | 11434  | LLM + Embeddings locales       |
| AI Engine (self)| `ecommerce_sintel_ai`   | 8100   | FastAPI (este servicio)        |

---

## 2. Estructura de archivos

```
ai_engine/
├── main.py                  # FastAPI app + lifespan + endpoints (motor de codigo + monta el AI Gateway)
├── config.py                # Variables de entorno (python-decouple)
├── graph.py                 # LangGraph workflow de GENERACION DE CODIGO (StateGraph)
├── action_graph.py          # [AI CORE] LangGraph workflow de ACCIONES DE NEGOCIO (/chat) -- grafo paralelo, no toca graph.py
├── auth.py                  # [AI CORE] Valida JWT real de Django (PyJWT, HS256) + resuelve identidad via Django
├── observability.py         # [AI CORE] Metricas por turno de /chat (logger "observability", tag [metrics])
├── gateway/                 # [AI CORE] AI Gateway -- router.py: /api/v1/ai/context, /api/v1/ai/tools/debug
├── agents/                  # [AI CORE] Agent Registry -- carga y valida agents/profiles/*.yaml al importarse
│   └── profiles/            #   9 Agent Profiles YAML (uno por dominio, ver seccion 5bis)
├── capabilities/            # [AI CORE] Capability Registry -- registry.py: 29 Capabilities (intencion -> tool)
├── tools/                   # [AI CORE] Tool Registry -- 29 Tools en 10 archivos por dominio + http_bridge.py
│   ├── registry.py          #   @register_tool decorator + list_tools()/get_tool()/invoke()
│   ├── metadata.py          #   ToolMetadata (side_effects, risk, requires_confirmation, rate_limit, permissions)
│   ├── http_bridge.py       #   Cliente HTTP hacia los endpoints internos read-only de Django
│   └── <dominio>_tools.py   #   core_tools/inventory_tools/kyc_tools/marketing_tools/orders_tools/
│                            #   payment_tools/quotes_tools/renting_tools/services_tools/support_tools
├── chains.py                # Chain backend (Django/DRF) -- generacion de codigo
├── chains_frontend.py       # Chain frontend (Vue 3) -- generacion de codigo
├── guardrails.py            # Guardian arquitectura backend (8 reglas CRITICAL + 3 WARNING)
├── guardrails_frontend.py   # Guardian frontend Vue (6 CRITICAL + 3 WARNING)
├── retrievers.py            # Ensemble BM25 + MMR + detección de apps/tipo
├── specialized_retrieval.py # 9 índices especializados (Model/Serializer/ViewSet/...)
├── planner.py               # build_plan() — pipeline de 14 pasos implementados (de 17 documentados)
├── project_map.py           # Query interface sobre PROJECT_MAP.json
├── knowledge_graph.py       # Construye KNOWLEDGE_GRAPH.json desde PROJECT_MAP.json
├── dependency_graph.py      # Blast-radius/impacto desde KNOWLEDGE_GRAPH.json
├── memory_builder.py        # GLOBAL_MEMORY.json + APP_MEMORY/*.json (conocimiento estático por app)
├── ai_manifest.py           # AI_MANIFESTS/*.json + MASTER_MANIFEST.json (manifiestos por app)
├── incremental_updater.py   # Re-auditoría incremental (detect_changed_apps/update_changed_apps)
├── auditor.py               # Genera PROJECT_MAP.json auditando todo el codebase (+ encadena KG/DG/memory/manifests)
│                            #   **CRITICO: correr SIEMPRE desde el HOST** (`cd ecommerce_sintel_rest && python
│                            #   ai_engine/auditor.py`), NUNCA con `docker exec` dentro del contenedor -- su
│                            #   `BASE_DIR` se calcula relativo a `__file__` y espera encontrar
│                            #   `ecommerce_sintel_rest/ecommerce_sintel/` en disco; dentro del contenedor esa
│                            #   ruta no existe (el codigo Django vive montado en `/workspace`, no en `/ecommerce_sintel`)
│                            #   y el auditor calla el error, reportando 0 apps/modelos/endpoints en vez de fallar
│                            #   ruidosamente (hallazgo real 2026-07-19, ver seccion 17.2).
├── PROJECT_MAP.json         # Grafo completo del proyecto (auto-generado, ~960 KB)
├── KNOWLEDGE_GRAPH.json     # Grafo tipado de entidades de código (auto-generado)
├── DEPENDENCY_GRAPH.json    # Blast-radius precalculado (auto-generado)
├── GLOBAL_MEMORY.json       # Conocimiento estático global (auto-generado)
├── AI_MANIFESTS/            # Un manifest JSON por app + MASTER_MANIFEST.json (auto-generado)
├── APP_MEMORY/              # Memoria estática por app (auto-generado)
├── .file_hashes.json        # Hash tracker para re-auditoría incremental (auto-generado)
├── loaders.py               # Carga Markdown, Python, Vue/JS con metadata
├── splitters.py             # Fragmentación por tipo (MD / Python / Vue SFC)
├── embeddings_factory.py    # Ollama bge-m3 | OpenAI
├── vectorstore_factory.py   # ChromaDB HTTP client
├── llm_factory.py           # Ollama llama3.1:8b | OpenAI | Anthropic
├── bootstrap.py             # Script de ingesta inicial (ejecutar 1 vez)
├── requirements.txt
├── Dockerfile               # python:3.12-slim, EXPOSE 8100 -- `COPY . .` hornea TODO ai_engine/ (incluidos los
│                            #   JSON de auditoria) dentro de la imagen; no son un volumen live, un rebuild
│                            #   (`docker compose build sintel_ai && docker compose up -d sintel_ai`) es
│                            #   obligatorio para que el contenedor sirva un PROJECT_MAP.json regenerado
├── e2e_http/                # Tests HTTP PowerShell (accounts, home, rental)
└── e2e_ui/                  # Tests UI Playwright (Node.js, home_config)
```

**[NOTA 2026-07-19 — auditoría de alineación]** Este documento describía hasta
ahora solo el motor de **generación de código** (`/generate`, `/validate`,
`/plan`, `/impact`, el auditor y sus JSON). El **AI Core** (`action_graph.py`,
`auth.py`, `gateway/`, `agents/`, `capabilities/`, `tools/`) — el "cerebro
operativo" multiagente descrito en `PLAN_DE_ACCION_AI_CORE.md` — completó sus
8 fases el 2026-07-16 y **ya está en el codebase y verificado corriendo**
(29 Tools + 29 Capabilities + 9 Agent Profiles confirmados en runtime el
2026-07-19, ver sección 5bis). Este documento y el plan ya no describen mundos
separados: el plan documenta el *porqué* y el *cómo se construyó* cada fase,
este documento (secciones 5 y 5bis) documenta *lo que existe hoy*. Para el uso
práctico día a día (como llamar cada endpoint, ejemplos de `/chat`, como
regenerar el auditor correctamente) ver **`ai_engine/.AGENT/GUIA_USO.md`**.

---

## 3. Configuración (`config.py`)

Todas las variables via **`python-decouple`** (`.env` o entorno Docker):

| Variable                 | Default                      | Descripción                        |
|--------------------------|------------------------------|------------------------------------|
| `LLM_PROVIDER`           | `ollama`                     | `ollama` / `openai` / `anthropic`  |
| `LLM_MODEL`              | `llama3.1:8b`                | Modelo LLM                         |
| `EMBEDDING_PROVIDER`     | `ollama`                     | `ollama` / `openai`                |
| `EMBEDDING_MODEL`        | `bge-m3`                     | Modelo de embeddings               |
| `OLLAMA_BASE_URL`        | `http://sintel_ollama:11434` | URL Ollama                         |
| `CHROMA_HOST`            | `sintel_chromadb`            | Host ChromaDB                      |
| `CHROMA_PORT`            | `8000`                       | Puerto ChromaDB                    |
| `CHROMA_AUTH_TOKEN`      | `""`                         | Token auth (vacío = sin auth)      |
| `CHROMA_COLLECTION_NAME` | `sintel_kb`                  | Colección ChromaDB                 |
| `DOCS_SPECS_PATH`        | `/docs/specs`                | Specs Markdown por app             |
| `CODEBASE_PATH`          | `/workspace/ecommerce_sintel`| Raíz del codebase Django+Vue       |
| `INGESTION_BATCH_SIZE`   | `50`                         | Chunks por batch en ingesta        |
| `MAX_RETRIEVER_CHUNKS`   | `50`                         | Límite chunks devueltos al LLM     |
| `VALIDATION_MAX_RETRIES` | `3`                          | Intentos antes de escalar          |
| `OPENAI_API_KEY`         | `""`                         | Solo si `LLM_PROVIDER=openai`      |
| `ANTHROPIC_API_KEY`      | `""`                         | Solo si `LLM_PROVIDER=anthropic`   |

---

## 4. Arranque / Lifespan (`main.py`)

```
startup →
  [si Ollama] _ensure_ollama_models()  ← pre-pull LLM + embedding models (timeout 300s)
  get_embeddings()                     ← Ollama OllamaEmbeddings / OpenAI
  get_vectorstore(embeddings)          ← ChromaDB HTTP client
  get_llm()                            ← ChatOllama / ChatOpenAI / ChatAnthropic
  load_all_documents(DOCS_SPECS_PATH, CODEBASE_PATH)
  split_all(raw_docs)
  get_registry()                       ← [NUEVO] pre-construye los 10 índices especializados (specialized_retrieval.py)
  build_all_manifests()                ← [NUEVO] pre-construye AI_MANIFESTS/*.json desde PROJECT_MAP.json (ai_manifest.py)
  → _STATE = { vectorstore, all_docs, llm }
  → LOG: "Motor listo. Chunks en memoria: N"
```

**Nota**: los chunks se almacenan en `_STATE["all_docs"]` en RAM para BM25. ChromaDB persiste los embeddings en disco.

**Nota 2 [2026-07-15]**: `get_registry()`/`build_all_manifests()` leen
`PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/`DEPENDENCY_GRAPH.json` **ya
generados en disco** (no los regeneran) — si esos archivos están
desactualizados (ej. tras agregar un modelo nuevo sin correr
`python ai_engine/auditor.py`), el motor arranca sin error pero sirve datos
estructurales obsoletos vía `/manifest/{app}`, `/graph/*`, `/memory`. No hay
ninguna validación de "frescura" en el startup — es responsabilidad de
quien despliega correr el auditor antes de reconstruir la imagen (ver
sección 17.2).

---

## 5. Endpoints REST

> **[2026-07-16 — AI Core Fase 1]** El motor ahora tiene DOS mundos de
> endpoints que no se mezclan: (a) los históricos de generación de código de
> abajo, **sin autenticación** (solo accesibles dentro de la red Docker), y
> (b) el **AI Gateway** (`gateway/`, prefijo `/api/v1/ai/*`) que exige el JWT
> real de Django en cada request (`auth.py`: PyJWT valida firma HS256 +
> expiración con la misma `JWT_SECRET_KEY` de SimpleJWT, y resuelve la
> identidad reenviando el token a
> `GET http://django:8000/api/v1/internal/ai-context/`, endpoint interno en
> `users/api/internal.py` protegido por `IsAuthenticatedActiveUser`).
> Ver `ai_engine/.AGENT/PLAN_DE_ACCION_AI_CORE.md` (Fase 1).

### `GET /api/v1/ai/context` (AI Gateway — requiere JWT)
```json
// Authorization: Bearer <access token de Django>  → 200
{ "user_id": 4, "uuid": "...", "email": "...", "full_name": "...",
  "user_type": "CUSTOMER", "is_staff": false, "is_superuser": false,
  "is_verified": false, "kyc_status": "APPROVED" }
// Sin header o token inválido/expirado → 401 explícito (nunca 200 anónimo)
```

### `POST /chat` (Action Graph — requiere JWT)
**[2026-07-16 — Fase 3]** Grafo de acciones de negocio (`action_graph.py`),
PARALELO al de generación de código (no toca `graph.py`). Nodos:
`resolve_customer_context → detect_intent → optimize_context →
(retrieve_knowledge | select_and_execute_tools → validate_tool_result) →
generate_response`, compilado con checkpointer `MemorySaver` (thread
namespaceado por user_id; el JWT viaja por config, nunca en el estado).
Primera vez que el proyecto usa `llm.bind_tools()` — el LLM solo ve
Capabilities. Request: `{"message": "...", "conversation_id": "..."?}` →
`{conversation_id, intent, tool_calls, tool_results, response}`.

> **[2026-07-16 — Fase 4]** El Action Graph ahora tiene Policy Layer y
> escrituras con confirmación: `select_and_execute_tools` separa lecturas
> (ejecutan directo) de escrituras (`ToolMetadata.side_effects=true`), que
> pasan por `evaluate_policy` (admin-check, rate limit del metadata) →
> `request_confirmation` (`interrupt()` de langgraph — el payload se lee
> con `graph.get_state()`, `ainvoke` no lo expone en 0.2.x) →
> `execute_write` → `audit_log`. `/chat` acepta `confirm: true|false` o un
> "si"/"no" simple para reanudar. 6 write-tools: CreateRentalRequestTool,
> CancelRentalTool, QuoteTemplatesTool (lectura), StartQuotationTool,
> RequestKycUpgradeTool, OpenSupportTicketTool (gap #1: cambiar fechas de
> alquiler = escalar a soporte, decisión del usuario). Los endpoints
> internos POST de Django auditan cada escritura en
> `SecurityEvent.AI_ACTION_EXECUTED` (migración security.0006).

> **[2026-07-16 — Fase 5]** Customer Context Builder completo: para intents
> de personalización (`renting_search`/`promos`/`quote`) el nodo
> `optimize_context` trae el CRM Context desde
> `GET /api/v1/internal/ai/customer-context/` (agregador en
> `accounts/api/internal_ai.py`: marketing profile + direcciones + tarjetas
> sin token, cacheado en Redis TTL 300s — sin tabla nueva). Datos vivos
> jamás se indexan al RAG (Componente 10). Conversación: `MemorySaver` +
> `history` (últimos 3 turnos al prompt).

> **[2026-07-16 — Fase 6]** Multiagente: 7 Agent Profiles YAML en
> `agents/profiles/` (validados al arranque contra Capability/ToolRegistry;
> un YAML roto impide el boot). `detect_intent` ahora también rutea
> intención→agente y aplica reglas de escalamiento (handoff a SupportAgent
> por queja, registrado en métricas). El scope del agente limita qué
> capabilities ve el LLM; su personalidad/tono entra al prompt de
> `generate_response`. Observabilidad: `observability.py` emite una línea
> JSON por turno (logger `observability`, tag `[metrics]`) con tokens,
> latencia por tool, handoff, write_executed — Prometheus/OTel preparado,
> no instalado. `/chat` devuelve además `agent`; GET `/tools/debug` lista
> los agentes.

> **[2026-07-16 — Fase 7]** Multicanal: el widget de soporte web y WhatsApp
> llegan al Action Graph A TRAVÉS de Django (sintel_ai nunca se expone):
> `support/services/ai_bridge.py` acuña un access token efímero del usuario
> y llama a `/chat`. Modo AI en `SupportChatConsumer` (cero cambios de
> frontend; bot = usuario `AI_BOT_EMAIL` inactivo). Human Handoff: al abrir
> ticket se vuelca la transcripción + `ChatRoom.ai_paused=True`
> (support.0005) + aviso a `support_admins`. WhatsApp:
> `/api/v1/notifications/whatsapp-webhook/` → Celery → `/chat` →
> `WhatsAppClient.send_text()` (pendiente config Meta para prod). Event Bus:
> `AI_PROACTIVE_SLUGS` en `dispatch_notification` → mensaje proactivo del
> bot en la sala.

### `GET|POST /api/v1/ai/tools/debug` (AI Gateway — requiere JWT + flag, SOLO dev)
**[2026-07-16 — Fase 2, crecido en Fases 4/8]** Detrás del flag
`AI_TOOLS_DEBUG` (default false → 404; solo el docker-compose de dev lo
enciende). GET lista las Tools (`tools/registry.py` + 10 archivos
`tools/<dominio>_tools.py`), las Capabilities (`capabilities/registry.py`) y
los Agent Profiles (`agents/`) — **29 Tools, 29 Capabilities, 9 Agents**
confirmados en runtime el 2026-07-19 (arrancaban 9 Tools/9 Capabilities en
Fase 2; crecieron con las Tools de escritura de Fase 4 y las 9 Tools de Core
Content + Marketing/Maintenance de Fase 8). POST `{"tool": "...", "args":
{...}, "confirmed": false}` invoca una Tool directo (acepta nombre de Tool o
capability_id) — si la Tool tiene `side_effects=true` exige `confirmed:true`
tambien aquí (la Policy Layer aplica incluso en debug manual). Cada Tool
reenvía el JWT a los endpoints internos read-only de Django (fachadas de los
Selectors reales) vía `tools/http_bridge.py` — el motor jamás toca los
modelos ni el ORM directamente.

> **[2026-07-16 — Fase 8]** AI Business Automation: 4 Tools nuevas de
> lectura (`PersonalRecommendationTool`, `MarketingDashboardTool`,
> `StaleStockAlertsTool`, `CampaignTargetsTool`, `MaintenanceCheckTool`) más
> 5 Tools de escritura sobre contenido de `core` con confirmación obligatoria
> y `risk=high` (`CoreBannerCreateTool`, `CoreBannerUpdateTool`,
> `CoreNavbarLinkCreateTool`, `CoreNavbarLinkUpdateTool`,
> `CoreBrandSliderUpdateTool`), todas envolviendo Commands ya existentes de
> `core` (`HomeConfigCommands`/`NavbarLinkCommands`/`BrandSliderCommands`) —
> el AI nunca escribe Vue/JS ni toca el ORM. Nuevo `AdminAgent` (Core Content
> + mantenimiento) y `MarketingAgent` (dashboard/stock/campañas/
> recomendaciones), completando los 9 Agent Profiles. Intents nuevos:
> `marketing_admin`, `personal_recommendation`, `maintenance_check`,
> `core_content`. El seguimiento postventa/renovaciones/recordatorios
> reutiliza el mecanismo de Fase 7 (`AI_PROACTIVE_SLUGS`) sin código nuevo.
> Detalle completo en `PLAN_DE_ACCION_AI_CORE.md` (Fase 8).

### `GET /health`
```json
{ "status": "ok", "chunks_indexed": 1234, "vectorstore": "chromadb" }
```

### `POST /generate`
**Request:**
```json
{
  "task": "Crear ViewSet de categorías con soft-delete",
  "apps": ["shop"],          // opcional — auto-detectado si se omite
  "task_type": "backend"     // opcional: "backend" | "frontend" | null (auto)
}
```
**Response:**
```json
{
  "final_code": "class CategoryViewSet(...): ...",
  "escalated": false,
  "escalation_reason": "",
  "iterations": 2,
  "apps_detected": ["shop"],
  "task_type": "backend",
  "validation_report": { "passed": true, "violations": [], "warnings": [] }
}
```

### `POST /validate`
Valida código sin generarlo (útil para CI).
```json
// Request
{ "code": "class MyView(APIView):\n    def post(self, req):\n        obj.delete()", "app_context": "shop" }

// Response
{ "passed": false, "violations": [{"rule_id": "PHYSICAL_DELETE", ...}], "warnings": [] }
```

### `POST /ingest`
Recarga y re-indexa todos los documentos. Invocar tras cambios en specs o código.
```json
{ "status": "ok", "chunks_ingested": 1234 }
```

### `POST /impact` (NUEVO)
Analiza qué componentes del proyecto se ven afectados por una tarea. No genera código.
**Request:**
```json
{ "task": "Agrega descuentos dinámicos al checkout", "apps": null }
```
**Response:**
```json
{
  "apps": ["shop", "orders", "marketing"],
  "models": [{"app": "shop", "model": "Product", "fk_relations": ["vendor -> AUTH_USER_MODEL"]}],
  "serializers": [{"app": "shop", "serializer": "ProductSerializer", "file": "shop/api/serializers.py"}],
  "viewsets": [{"app": "shop", "viewset": "ProductViewSet", "actions": ["reviews"]}],
  "endpoints": [{"endpoint": "api/v1/shop/products", "viewset": "ProductViewSet", "http_methods": ["GET","POST","PUT","PATCH","DELETE"]}],
  "frontend_files": [{"file": "views/customer/shop/ShopView.vue", "api_calls": [{"method":"GET","url":"/api/v1/shop/products/"}]}],
  "stores": [{"store": "useShopStore", "calls": [...]}],
  "services": [...],
  "impact_summary": "=== IMPACTO EN EL PROYECTO ..."
}
```

### `POST /plan` (NUEVO, no documentado hasta 2026-07-15)
Corre el pipeline de 14 pasos de `planner.py::build_plan()` (de los 17
documentados en su docstring, los pasos 15-17 son generación/validación/
memoria que ocurren fuera del planner, en `graph.py`) y devuelve el
`CodePlan` sin generar código.
```json
// Request
{ "task": "Agrega descuentos dinámicos al checkout", "apps": null }

// Response — CodePlan completo
{
  "intent": "create", "task_type": "backend", "apps": ["shop", "orders"],
  "affected_models": [...], "affected_viewsets": [...], "affected_serializers": [...],
  "affected_endpoints": [...], "affected_frontend": [...], "affected_stores": [...],
  "blast_radius": {...}, "plan_steps": ["[Backend] Model Product en shop/models.py", ...],
  "enriched_context": "...", "warnings": []
}
```

### `POST /breakage`
Dado un identificador de entidad (ej. `"shop.Product"`), devuelve qué se
rompe si se modifica (blast-radius).
```json
// Request
{ "entity": "shop.Product" }
// Response
{ "entity": "shop.Product", "affected_viewsets": [...], "affected_serializers": [...],
  "affected_frontend": [...], "affected_tests": [...] }
```

### `GET /memory`
Devuelve `GLOBAL_MEMORY.json` completo, o el de una app específica con
`?app=shop` (`APP_MEMORY/shop_MEMORY.json`).

### `GET /graph/node/{entity_name}`
Devuelve el nodo de `KNOWLEDGE_GRAPH.json` para una entidad (ej.
`BrandSliderItem`) más su vecindario inmediato (edges entrantes/salientes).

### `GET /graph/impact/{entity_name}`
Devuelve la cadena de impacto transitivo (no solo el vecindario inmediato)
para una entidad, vía `dependency_graph.py`.

### `POST /search`
Enruta una consulta a los índices especializados (`specialized_retrieval.py`)
y devuelve los documentos más relevantes de los 3 índices con mayor score
(`ModelIndex`, `SerializerIndex`, `ViewSetIndex`, `CommandIndex`,
`SelectorIndex`, `ServiceIndex`, `FrontendIndex`, `DocumentationIndex`,
`BusinessRulesIndex`, `DependencyIndex`).

### `GET /indices`
Lista los 10 índices especializados y su cantidad de documentos cada uno —
útil para diagnosticar si la ingesta realmente pobló todos.

### `GET /manifest/{app_name}`
Devuelve el manifest completo de una app (`AI_MANIFESTS/{app_name}_MANIFEST.json`):
`api_prefix`, `architecture` (modelos/serializers/viewsets con FKs),
`endpoints`, `frontend_consumers`, `dependencies`, `blast_radius`,
`service_contracts`, `events`, `constraints`, `known_issues`,
`business_rules`, `url_patterns`, `patterns`, `TODO`/`BUG`/`HOT_FIX`,
`decisions`.

### `GET /refresh/detect`
Detecta qué apps cambiaron desde la última auditoría (por hash de archivo,
`incremental_updater.py::detect_changed_apps()`), sin re-auditar todavía.

### `POST /refresh`
Re-audita **solo** las apps detectadas como cambiadas
(`incremental_updater.py::update_changed_apps()`) y actualiza
`PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/`DEPENDENCY_GRAPH.json`/
`APP_MEMORY`/`GLOBAL_MEMORY` de forma incremental — más rápido que
`python auditor.py` completo, pero solo cubre las apps marcadas como
cambiadas por el detector de hashes.

---

## 6. Pipeline de Ingesta de Documentos

### 6.1 Carga (`loaders.py` → `load_all_documents`)

7 fuentes cargadas en orden:

| # | Fuente                              | Loader                       | Tipo doc   |
|---|-------------------------------------|------------------------------|------------|
| 1 | `DOCS_SPECS_PATH/**/*.md`           | UnstructuredMarkdownLoader   | `spec`     |
| 2 | `**/.AGENT/docs/**/*.md`            | UnstructuredMarkdownLoader   | `architecture` |
| 3 | `**/services/commands.py` etc.      | PythonLoader                 | `command`  |
| 3 | `**/api/views.py`, `serializers.py` | PythonLoader                 | `view`/`serializer` |
| 3 | `**/models.py`                      | PythonLoader                 | `model`    |
| 4 | `frontend/src/modules/**/*.vue`     | TextLoader (UTF-8)           | `component`/`view` |
| 4 | `frontend/src/composables/*.js`     | TextLoader                   | `composable` |
| 4 | `frontend/src/store/*.js`           | TextLoader                   | `store`    |
| 5 | `ai_skills/frontend/*.md`           | UnstructuredMarkdownLoader   | `frontend_spec` |
| 6 | `frontend/.AGENT/doc/*.md`          | UnstructuredMarkdownLoader   | `frontend_spec` |

**Deduplicación por ruta fuente** (última etapa).

**Metadatos inferidos** de la ruta del archivo:
- `app_name`: detectado de segmentos de path (shop, inventory, orders, payment, wompi, etc.)
- `doc_type`: spec / architecture / command / selector / model / view / serializer / component / composable / store / router
- `layer`: service_layer / api / frontend / architecture
- `language`: markdown / python / vue / javascript

### 6.2 Fragmentación (`splitters.py` → `split_all`)

| Tipo       | Estrategia                                   | Tamaño  | Overlap |
|------------|----------------------------------------------|---------|---------|
| Markdown   | MarkdownHeaderTextSplitter → RecursiveChar   | 1800    | 300     |
| Python     | `Language.PYTHON` RecursiveChar              | 2200    | 200     |
| Vue SFC    | Extrae bloques `<template>` + `<script>`     | 1600    | 150     |
| JS         | RecursiveChar                                | 1600    | 150     |

**Vue SFC**: los bloques `<style>` se descartan (no aportan contexto semántico).

### 6.3 Bootstrap (ingesta inicial)

```bash
# Dentro del container:
docker exec ecommerce_sintel_ai python bootstrap.py

# Desde el host:
python ai_engine/bootstrap.py
```

Flujo: `load_all_documents → split_all → get_embeddings → get_vectorstore → vectorstore.add_documents(batch)`

---

## 7. Pipeline de Recuperación (`retrievers.py`)

### 7.1 Detección automática

**`detect_task_type(text)`**
- Puntúa keywords `FRONTEND_TASK_KEYWORDS` vs `BACKEND_TASK_KEYWORDS`
- Si frontend_score > backend_score → `"frontend"`, si no → `"backend"`

**`detect_apps_from_text(text)`**
- Mapea el texto a 25+ apps/módulos via `APP_KEYWORDS_MAP`
- Apps backend: shop, inventory, orders, payment, wompi, technical_services, renting, cart, notifications, users, accounts, dashboard, quotes, marketing, support, core
- Apps frontend: `frontend_shop`, `frontend_renting`, `frontend_technical_services`, `frontend_orders`, `frontend_inventory`, `frontend_customer`, `frontend_landing`, `frontend_support`, `frontend_core`

### 7.2 Ensemble Retriever

Por cada app detectada se construye:
```
BM25Retriever (corpus filtrado por app, k=6)    ← 35% peso
+
ChromaDB MMR retriever (k=8, fetch_k=25, λ=0.6) ← 65% peso
= EnsembleRetriever(weights=[0.35, 0.65])
```

Además se agregan siempre los **docs de reglas globales** (`app_name: global_rules | architecture_contracts`, k=5).

**Deduplicación** por hash de los primeros 200 caracteres. Límite: `MAX_RETRIEVER_CHUNKS=50`.

---

## 8. LangGraph Workflow (`graph.py`)

### 8.1 Estado (`SintelCodeState`)

```python
{
    "task":              str,    # Texto de la tarea (mutado con feedback en retry)
    "task_type":         str,    # "backend" | "frontend"
    "apps":              list,   # Apps detectadas (enriquecido por analyze_impact)
    "impact_context":    str,    # AUTO-ANALISIS desde PROJECT_MAP.json (nuevo)
    "retrieved_context": str,    # Contexto RAG formateado
    "generated_code":    str,    # Código generado en la iteración actual
    "validation_report": dict,   # { passed, violations, warnings }
    "iteration":         int,    # Incrementa en cada validate_code (empieza en 0)
    "final_code":        str,    # Código final aprobado
    "escalated":         bool,
    "escalation_reason": str,
}
```

### 8.2 Grafo de nodos

```
ENTRY
  ↓
[analyze_impact]             ← NUEVO: consulta PROJECT_MAP.json
  ↓
[generate_code] ← ← ← ← ← ← ←
  ↓                             ↑
[validate_code]                  |
  ↓                             |
  ├─ passed=True → [emit_result] → END
  ├─ iteration < MAX_RETRIES   ─────┘  (feedback reinyectado en state["task"])
  └─ iteration ≥ MAX_RETRIES → [escalate] → END
```

### 8.3 Nodos

**`node_analyze_impact`** (NUEVO — nodo 1)
- Llama `find_affected_apps(task)` de `project_map.py` para detectar apps via keyword matching bidireccional (dominio + AST estructural)
- Llama `build_impact_context(task)` para generar un bloque de texto con modelos, serializers, viewsets, endpoints y archivos Vue afectados
- Enriquece `state["apps"]` fusionando apps auto-detectadas con las pasadas por el cliente
- Guarda el bloque en `state["impact_context"]`

**`node_generate_code`**
- Selecciona `editor_chain` (backend) o `fe_chain` (frontend) según `task_type`
- Inyecta `impact_context` al final de la tarea antes de pasarla al chain
- Invoca: `chain.invoke({"task": enriched_task, "apps": apps})`
- En error LLM: `escalated=True, escalation_reason="LLM error..."`

**`node_validate_code`**
- Backend → `SintelArchitectureGuard.validate(code, app_ctx)`
- Frontend → `SintelFrontendGuard.validate(code, app_ctx)`
- Si falla: construye `feedback_prompt` y lo reinyecta en `state["task"]`
- Incrementa `state["iteration"]`

**`node_emit_result`**: pass-through en éxito.

**`node_escalate`**: marca `escalated=True` con resumen de violaciones persistentes.

**`route_after_validation`** (edge condicional):
```python
if passed:         return "emit_result"
if iter < MAX:     return "generate_code"   # con feedback en state["task"]
else:              return "escalate"
```

---

## 9. Chains de Generación

### 9.1 Backend (`chains.py` — `build_editor_chain`)

**Pipeline**: `inject_context → ChatPromptTemplate → LLM → StrOutputParser`

**Sistema**: 14 reglas críticas en el system prompt:
1. Dinero siempre `Decimal('X.XX')`, jamás float
2. Soft-delete: `obj.is_active=False; obj.is_deleted=True; obj.save(...)` (excepto BaseCommand / CartItem)
3. Sin emojis en `.py`
4. ViewSets solo orquestan — mutaciones en Commands con `@transaction.atomic`
5. Selectores de solo lectura (sin side-effects)
6. Notificaciones solo dentro de `transaction.on_commit`
7. `IsAdminUser` de `users.api.permissions` (no de DRF)
8. Wompi webhook debe verificar firma SHA256
9. Sin campo `role` en User — usar `accounts.UserProfile.user_type`
10. UUID en URLs públicas, nunca PK entero
11. Stock: usar `stock_record.stock` con `select_for_update` (nunca `InventorySelector.get_current_stock()`)
12. Cupones: filtrar por `active=True + valid_from + valid_to`
13. Confirmación de pago: siempre `confirm_order_payment()` de `payment/shared/commands.py`
14. `confirm_order_payment` es idempotente (verifica `order.status == 'paid'` con `select_for_update`)

**`build_feedback_prompt`**: en retry, reemplaza `state["task"]` con:
```
CORRECCIONES OBLIGATORIAS (intento N):
  - [RULE_ID] descripción
...
Tarea original: ...
```

### 9.2 Frontend (`chains_frontend.py` — `build_frontend_chain`)

**Sistema**: 15 reglas críticas para Vue 3:
1. `<script setup>` siempre — nunca Options API
2. HTTP siempre via `useApi()` — nunca `import axios`
3. GET → endpoints públicos; POST/PATCH/DELETE → `dashboard/`
4. FKs en payload → `.uuid`; URL de escritura → `.id`
5. CRUD con `useOffcanvas()` + `SintelOffcanvas`
6. Confirmación borrado: fila inline, no modal flotante
7. Toasts: `useToast()` — nunca `alert()`
8. Try/catch obligatorio en toda llamada async
9. Debounce 400ms en búsqueda
10. Lazy loading en router
11. Solo componentes del `FRONTEND_COMPONENT_REGISTRY.md`
12. Sin TypeScript — solo JS puro
13. Bootstrap 5 + Bootstrap Icons (`bi-*`)
14. Precios: `new Intl.NumberFormat('es-CO').format(num)`
15. Stores globales: solo `useAuthStore`, `useAppConfigStore`, `useCartStore`

---

## 10. Guardrails de Validación

### 10.1 Backend (`SintelArchitectureGuard`) — `guardrails.py`

#### Reglas CRITICAL (bloquean la generación):

| Rule ID                        | Qué detecta                                                                 |
|-------------------------------|-----------------------------------------------------------------------------|
| `FLOAT_MONEY`                 | Campos monetarios con literal float (`price=19.99` sin `Decimal(...)`)      |
| `PHYSICAL_DELETE`             | `.delete()` fuera de `BaseCommand` o contexto CartItem                      |
| `EMOJI_IN_PY`                 | Cualquier emoji en código Python                                            |
| `WRONG_ADMIN_PERMISSION_IMPORT`| `from rest_framework.permissions import IsAdminUser`                       |
| `INCOMPLETE_ADMIN_CHECK`      | `is_staff` sin `is_superuser` en lógica de permisos                        |
| `NOTIFY_OUTSIDE_ON_COMMIT`    | `dispatch_notification`/`ws_notify` fuera de `transaction.on_commit`        |
| `WOMPI_MISSING_SIGNATURE_CHECK`| Webhook Wompi sin verificación de firma (solo si `app_context="wompi"`)   |
| `VIEWSET_DIRECT_DB_WRITE`     | ViewSet llamando `.create()/.save()/.delete()/.update()` directamente (AST) |

#### Reglas WARNING (no bloquean):

| Rule ID                      | Qué detecta                                              |
|-----------------------------|----------------------------------------------------------|
| `MISSING_TRANSACTION_ATOMIC` | Clase Commands sin `@transaction.atomic`                 |
| `MISSING_SELECT_FOR_UPDATE`  | Operaciones sobre stock sin `select_for_update()`        |
| `SELECTOR_HAS_SIDE_EFFECTS`  | Selector con `.save()`/`.create()`/`.delete()`           |

### 10.2 Frontend (`SintelFrontendGuard`) — `guardrails_frontend.py`

#### Reglas CRITICAL:

| Rule ID                  | Qué detecta                                                             |
|--------------------------|-------------------------------------------------------------------------|
| `VUE_OPTIONS_API`        | `export default { data(), methods: {} }` (Options API)                  |
| `VUE_DIRECT_AXIOS`       | `import axios from 'axios'` directo                                     |
| `VUE_WRITE_NOT_DASHBOARD`| `api.post/patch/delete` a endpoint que no es `dashboard/`, `auth/`, `cart/`, `support/` |
| `VUE_MISSING_TRY_CATCH`  | `await api.*` sin `try {` en el código                                  |
| `VUE_ID_IN_FK_PAYLOAD`   | `{ category: item.id }` — FK debe usar `.uuid`                          |
| `VUE_INVENTED_IMPORT`    | Import de componentes no existentes (Button.vue, Modal.vue, Spinner.vue...) |

#### Reglas WARNING:

| Rule ID              | Qué detecta                                                      |
|----------------------|------------------------------------------------------------------|
| `VUE_MISSING_DEBOUNCE`| Input de búsqueda sin `setTimeout`/`debounce`                  |
| `VUE_NO_LAZY_ROUTE`   | Componente de ruta sin lazy loading (`() => import(...)`)       |
| `VUE_BAD_PRICE_FORMAT`| `.toFixed()` / `Math.round` para precios — usar `Intl.NumberFormat` |

**Lógica `passed`** (compartida): `passed = not any(v.severity == "CRITICAL" for v in violations)`

---

## 11. Factories

### `embeddings_factory.py` — `get_embeddings()`
- `EMBEDDING_PROVIDER=ollama` → `OllamaEmbeddings(model="bge-m3", base_url=OLLAMA_BASE_URL)`
- `EMBEDDING_PROVIDER=openai` → `OpenAIEmbeddings(model=..., api_key=...)`

### `llm_factory.py` — `get_llm()`
- `LLM_PROVIDER=ollama` → `ChatOllama(model="llama3.1:8b", temperature=0.1, num_predict=1500, num_ctx=8192)`
- `LLM_PROVIDER=openai` → `ChatOpenAI(temperature=0.1)`
- `LLM_PROVIDER=anthropic` → `ChatAnthropic(temperature=0.1)`

### `vectorstore_factory.py` — `get_vectorstore(embeddings)`
- `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)` (con o sin auth token)
- `Chroma(client=client, collection_name=CHROMA_COLLECTION, embedding_function=embeddings)`

---

## 12. Flujo completo de una petición `/generate`

```
POST /generate { task, apps?, task_type? }
  │
  ├─ detect_task_type(task)  →  "backend" | "frontend"
  │
  └─ run_code_generation(task, vectorstore, all_docs, llm, apps, task_type)
       │
       └─ build_sintel_graph(vectorstore, all_docs, llm)
            │
            ├─ build_editor_chain(...)   ← backend
            └─ build_frontend_chain(...) ← frontend
            │
            graph.invoke(initial_state)
            │
            ┌─────────────────────────────────────────────────────────┐
            │ ITER 1                                                    │
            │  generate_code:                                           │
            │    inject_context → retrieve_context_for_task             │
            │      → BM25 + MMR ensemble por app                        │
            │      → +global_rules k=5                                  │
            │      → dedup → limit MAX_RETRIEVER_CHUNKS                 │
            │    prompt + LLM + StrOutputParser → generated_code        │
            │                                                           │
            │  validate_code:                                           │
            │    SintelArchitectureGuard.validate() o                   │
            │    SintelFrontendGuard.validate()                         │
            │    → CRITICAL? → FAIL → build_feedback_prompt             │
            │                         → state["task"] = feedback         │
            │    → NO CRITICAL? → PASS → state["final_code"] = code     │
            │                                                           │
            │  route: passed? → emit_result → END                       │
            │         iter < 3? → generate_code (loop con feedback)     │
            │         iter ≥ 3? → escalate → END                        │
            └─────────────────────────────────────────────────────────┘
            │
            return { final_code, escalated, escalation_reason,
                     iterations, apps_detected, validation_report }
```

---

## 13. Apps y módulos detectados (mapa completo)

### Backend (Django)
`shop` · `inventory` · `orders` · `payment` · `wompi` · `technical_services` · `renting` · `cart` · `notifications` · `users` · `accounts` · `dashboard` · `quotes` · `marketing` · `support` · `core` · `kyc` · `security` · `operations` · `shipping` · `organization` *(las últimas 5 agregadas 2026-07-15 — `kyc`/`security` faltaban desde su creación 2026-07-06, `organization` desde la suya 2026-07-12; `shipping` es un app-stub sin modelos/vistas propias, el auditor la reporta "not found" al auditar pero sí participa en la detección de keywords)*

### Frontend (Vue)
`frontend_shop` · `frontend_renting` · `frontend_technical_services` · `frontend_orders` · `frontend_inventory` · `frontend_customer` · `frontend_landing` · `frontend_support` · `frontend_core` · `frontend_organization` *(agregado 2026-07-15)*

---

## 14. Testing

### Tests HTTP (`e2e_http/`)
```powershell
./e2e_http/e2e_accounts_users_test.ps1
./e2e_http/e2e_home_config_test.ps1
./e2e_http/e2e_rental_http_test.ps1
```

### Tests UI Playwright (`e2e_ui/`)
```bash
cd ai_engine/e2e_ui
npx playwright test tests/home_config_ui.spec.js
```
Config: `playwright.config.js`. Resultados: `test-results/`.

---

## 15. Comandos de operación

```bash
# Arrancar en desarrollo (desde host)
uvicorn main:app --host 0.0.0.0 --port 8100 --reload

# Ingesta inicial (una vez, o tras cambios en specs/código)
docker exec ecommerce_sintel_ai python bootstrap.py

# Re-ingesta manual via API
curl -X POST http://localhost:8100/ingest

# Health check
curl http://localhost:8100/health

# Generar código backend
curl -X POST http://localhost:8100/generate \
  -H "Content-Type: application/json" \
  -d '{"task": "Crear Command para crear una categoría con soft-delete", "apps": ["shop"]}'

# Generar componente Vue
curl -X POST http://localhost:8100/generate \
  -H "Content-Type: application/json" \
  -d '{"task": "Crear lista CRUD de categorías en Vue 3", "task_type": "frontend", "apps": ["shop"]}'

# Validar código directamente
curl -X POST http://localhost:8100/validate \
  -H "Content-Type: application/json" \
  -d '{"code": "...", "app_context": "shop"}'
```

---

## 16. Invariantes críticos del motor

1. **El LLM nunca se invoca sin contexto RAG** — siempre se inyecta `retrieved_context`
2. **El grafo reintenta hasta `VALIDATION_MAX_RETRIES=3`** antes de escalar
3. **En retry**, `state["task"]` se reemplaza por el feedback prompt — el texto original se incluye al final
4. **`passed=False`** solo si hay al menos una violación CRITICAL — los warnings no bloquean
5. **La detección de tipo** (frontend/backend) es automática por keywords pero sobrescribible via `task_type` en el request
6. **ChromaDB** solo persiste embeddings — los chunks en RAM (`_STATE["all_docs"]`) alimentan BM25 y se recargan en cada `/ingest`
7. **El `VIEWSET_DIRECT_DB_WRITE`** es la única regla que usa AST parsing — el resto son regex
8. **Startup**: si Ollama no responde al pre-pull, el motor continúa (warning, no error fatal)
9. **`analyze_impact`** es el primer nodo del grafo — enriquece `apps` y genera `impact_context` ANTES de llamar al LLM
10. **PROJECT_MAP.json** se carga en memoria con `@lru_cache(maxsize=1)` — no hay I/O en cada petición; regenerar con `python ai_engine/auditor.py`

---

## 17. Auditor del proyecto (`auditor.py`) y PROJECT_MAP.json

### 17.1 Propósito

El auditor transforma el codebase completo en un grafo de dependencias estructurado.
Cuando el usuario escribe "Agrega descuentos dinámicos", el motor **sabe automáticamente**:
- Qué modelos cambian (`Product`, `Order`, `Coupon`)
- Qué serializers actualizar
- Qué ViewSets se ven afectados
- Qué endpoints sirven esa data
- Qué componentes Vue consumen esos endpoints
- Qué stores Pinia hacen las llamadas

### 17.2 Uso

```bash
# Regenerar PROJECT_MAP.json (ejecutar cada vez que hay cambios estructurales)
cd ecommerce_sintel_rest
python ai_engine/auditor.py
```

Resultado: `ai_engine/PROJECT_MAP.json` (~500 KB).

### 17.3 Estadísticas del mapa (regenerado 2026-07-19)

| Categoría             | Cantidad |
|-----------------------|----------|
| Apps en `DJANGO_APPS` | 21       |
| Apps auditadas con éxito | 20 (`shipping` es un stub sin `models.py`/`views.py` propios — el auditor la reporta "not found", no cuenta como auditada aunque sigue en la lista de detección de keywords) |
| Modelos totales       | 166      |
| ViewSets totales      | 131      |
| Endpoints REST        | 118      |
| Archivos frontend     | 385      |
| Entradas cross-ref    | 271      |

Regenerar en cualquier momento con `python ai_engine/auditor.py` desde la
raíz del repo (ver sección 17.2) — los números de esta tabla quedan
obsoletos apenas se agrega un modelo/endpoint/componente nuevo, exactamente
igual que le pasó a esta tabla entre 2026-06-29 y 2026-07-15 (18→21 apps,
103→147 modelos) y entre 2026-07-15 y 2026-07-19 (147→166 modelos, 113→131
viewsets, 299→385 archivos frontend — reflejando, entre otras cosas, todo el
trabajo de `components/base/*` y las migraciones de Organization/Operations/
Support de esa sesión). **Recordatorio critico (2026-07-19):** correr el
auditor siempre desde el HOST, nunca con `docker exec` — ver la nota en la
sección 2 sobre `BASE_DIR`. Tras regenerar, el contenedor `sintel_ai` no ve
los JSON nuevos hasta un rebuild (`docker compose build sintel_ai && docker
compose up -d sintel_ai`) porque `Dockerfile` los hornea con `COPY . .`, no
los monta como volumen.

### 17.4 Estructura del JSON

```json
{
  "meta": { "generated_at": "...", "apps": [...] },
  "apps": {
    "shop": {
      "api_prefix": "api/v1/shop",
      "models": [{ "name": "Product", "fields": [...], "fk_relations": [...] }],
      "serializers": [...],
      "viewsets": [{ "name": "ProductViewSet", "actions": ["reviews", "review"] }],
      "url_patterns": [{ "type": "router", "prefix": "products", "viewset": "ProductViewSet" }],
      "management_commands": [...],
      "services": [...],
      "selectors": [...],
      "migrations": [...]
    }
  },
  "frontend": {
    "views": [...],
    "components": [...],
    "composables": [...],
    "stores": [...],
    "router": [{ "routes": [{ "path": "/tienda", "component": "ShopView" }] }]
  },
  "endpoints": [
    { "endpoint": "api/v1/shop/products", "viewset": "ProductViewSet",
      "http_methods": ["GET","POST","PUT","PATCH","DELETE"] }
  ],
  "cross_refs": {
    "endpoint_to_viewset": { "api/v1/shop/products": { "viewset": "ProductViewSet", "app": "shop" } },
    "model_to_viewset":    { "shop.Product": ["shop.ProductViewSet"] },
    "frontend_to_endpoint": { "views/customer/shop/ShopView.vue": [{"method":"GET","url":"/api/v1/shop/products/"}] },
    "store_to_endpoint":   { "useShopStore": [...] }
  }
}
```

### 17.5 `project_map.py` — API de consulta

```python
from project_map import (
    find_affected_apps,    # task -> list[str] (apps relevantes)
    build_impact_context,  # task -> str (bloque para inyectar al LLM)
    build_impact_report,   # task -> dict (estructurado para frontend)
    get_models_for_apps,   # apps -> list[dict]
    get_viewsets_for_apps, # apps -> list[dict]
    get_endpoints_for_apps,# apps -> list[dict]
    get_frontend_consumers,# apps -> list[dict] (Vue files que consumen esos endpoints)
    get_stores_for_apps,   # apps -> list[dict]
)
```

**Detección de apps** (`find_affected_apps`): combina dos pasos:
1. **Domain keywords**: mapa estático de ~200 términos por app (`_DOMAIN_KEYWORDS`)
2. **Structural pass**: busca nombres de modelos/viewsets del proyecto en el texto de la tarea

Scores > 0 → app incluida; se devuelven top 5 por score descendente.
