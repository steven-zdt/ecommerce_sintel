# Guía de Uso — Sintel AI Engine

> Guía práctica de "cómo se usa" el motor, día a día. Para la referencia
> arquitectónica completa (cómo está construido cada pieza) ver
> `FLIJO_COMPLETO_IA_ENGINE.md`. Para el porqué y el histórico de cómo se
> construyó el AI Core (fases 1-8) ver `PLAN_DE_ACCION_AI_CORE.md`. Este
> documento no repite esas explicaciones — asume que el motor ya existe y
> responde "¿cómo lo prendo, lo consulto, lo actualizo y lo depuro?".

Verificado en runtime el 2026-07-19: **29 Tools, 29 Capabilities, 9 Agent
Profiles**, `PROJECT_MAP.json` con 166 modelos / 131 ViewSets / 118
endpoints / 385 archivos frontend.

---

## 1. Dos motores en un solo servicio

El mismo proceso FastAPI (`ecommerce_sintel_ai`, puerto **8100**) expone dos
sistemas independientes que **no comparten estado ni rutas**:

| | Motor de generación de código | AI Core (acciones de negocio) |
|---|---|---|
| **Para qué sirve** | Generar/validar código Django/Vue nuevo respetando las reglas de arquitectura del proyecto | Responder preguntas y ejecutar acciones reales sobre datos reales de un usuario autenticado (buscar mi pedido, cancelar mi alquiler, ver el dashboard de marketing...) |
| **Endpoints** | `/generate`, `/validate`, `/plan`, `/impact`, `/breakage`, `/ingest`, `/search`, `/indices`, `/manifest/*`, `/memory`, `/graph/*`, `/refresh*` | `POST /chat`, `GET /api/v1/ai/context`, `GET|POST /api/v1/ai/tools/debug` |
| **Autenticación** | Ninguna — solo accesible dentro de la red Docker | **JWT real de Django obligatorio** (`Authorization: Bearer <access token>`) |
| **Quién lo usa hoy** | Nadie en producción todavía (herramienta de desarrollo/copiloto) | El widget de soporte web y WhatsApp, vía Django (nunca directo desde el navegador) |
| **Motor interno** | `graph.py` (LangGraph) + `chains.py`/`chains_frontend.py` | `action_graph.py` (LangGraph, grafo distinto) + `tools/` + `capabilities/` + `agents/` |

Ambos comparten el mismo LLM, el mismo vectorstore (ChromaDB) y el mismo
proceso de arranque (`main.py::lifespan`) — pero un bug o cambio en uno no
debería, en teoría, afectar al otro.

---

## 2. Arrancar, parar y reconstruir el motor

Todo se hace desde `ecommerce_sintel_rest/ecommerce_sintel/` (donde vive el
`docker-compose.yml`), no desde `ai_engine/`.

```bash
cd ecommerce_sintel_rest/ecommerce_sintel

# Arrancar (o recrear si ya existe, con la imagen actual)
docker compose up -d sintel_ai

# Ver logs en vivo (util para ver el boot: carga de docs, indices, manifests)
docker logs -f ecommerce_sintel_ai

# Parar sin borrar el contenedor
docker compose stop sintel_ai

# Health check rapido
curl http://localhost:8100/health
# {"status":"ok","chunks_indexed":2551,"vectorstore":"chromadb"}
```

### 2.1 Cuándo hace falta un **rebuild** (no solo un restart)

`ai_engine/Dockerfile` usa `COPY . .` — todo el contenido de `ai_engine/`
(código Python **y** los JSON de auditoría: `PROJECT_MAP.json`,
`KNOWLEDGE_GRAPH.json`, `AI_MANIFESTS/`, etc.) queda horneado dentro de la
imagen en el momento del build. **No es un volumen live.** Un
`docker compose restart sintel_ai` sigue sirviendo el código/datos de la
imagen ya construida.

Hace falta rebuild cuando:
- Cambiaste cualquier archivo `.py` de `ai_engine/` (nueva Tool, nuevo nodo
  del Action Graph, cambio en un guardrail, etc.)
- Regeneraste `PROJECT_MAP.json` con el auditor (sección 7) y querés que el
  motor sirva los datos frescos vía `/manifest/*`, `/graph/*`, `/memory`,
  `/impact`, `/plan`
- Agregaste o modificaste un Agent Profile YAML (`agents/profiles/*.yaml`)

```bash
cd ecommerce_sintel_rest/ecommerce_sintel
docker compose build sintel_ai
docker compose up -d sintel_ai

# Confirmar que arranco limpio (sin excepciones) y que los indices tienen
# los numeros esperados:
docker logs ecommerce_sintel_ai --tail 40
curl http://localhost:8100/indices
```

Un rebuild **no** re-hace la ingesta a ChromaDB automáticamente — la carga
de documentos (`load_all_documents`) corre en cada boot desde el
`lifespan`, así que sí se re-indexa en RAM (BM25) y se reconecta a ChromaDB,
pero si además cambiaste specs/`.md` y querés forzar una re-escritura de los
embeddings en disco, usar `POST /ingest` (sección 6).

---

## 3. Motor de generación de código

Sin autenticación — pensado para invocarse desde herramientas de desarrollo
(otro agente, un script, CI), no desde el navegador del cliente final.

### 3.1 Generar código

```bash
curl -X POST http://localhost:8100/generate \
  -H "Content-Type: application/json" \
  -d '{
        "task": "Crear un Command para crear una categoria con soft-delete",
        "apps": ["shop"],
        "task_type": "backend"
      }'
```

`apps` y `task_type` son opcionales — si se omiten, el motor los detecta
solo por keywords (`retrievers.py::detect_task_type` /
`detect_apps_from_text`). La respuesta trae `final_code`, `escalated`
(true si tras 3 reintentos el código sigue violando una regla CRITICAL),
`validation_report`, y desde 2026-07-15 también `impact_context` y
`plan_steps` (el análisis de impacto que se inyectó al prompt).

Generar un componente Vue es la misma llamada con `"task_type": "frontend"`.

### 3.2 Validar código ya escrito (sin generarlo)

Útil en un pipeline de CI o para revisar un diff antes de commitear:

```bash
curl -X POST http://localhost:8100/validate \
  -H "Content-Type: application/json" \
  -d '{"code": "class Foo(APIView):\n    def post(self, r):\n        obj.delete()", "app_context": "shop"}'
# {"passed": false, "violations": [{"rule_id": "PHYSICAL_DELETE", ...}], "warnings": []}
```

### 3.3 Saber qué se rompe ANTES de tocar algo

```bash
# Impacto de una tarea en lenguaje natural
curl -X POST http://localhost:8100/impact \
  -H "Content-Type: application/json" \
  -d '{"task": "Agregar descuentos dinamicos al checkout"}'

# Blast-radius de una entidad puntual ya identificada
curl -X POST http://localhost:8100/breakage \
  -H "Content-Type: application/json" \
  -d '{"entity": "shop.Product"}'

# Plan de 14 pasos sin generar codigo todavia (para revisar antes de /generate)
curl -X POST http://localhost:8100/plan \
  -H "Content-Type: application/json" \
  -d '{"task": "Agregar descuentos dinamicos al checkout"}'
```

### 3.4 Refrescar la base de conocimiento

```bash
# Re-indexa TODO en ChromaDB (lento, usar tras cambios grandes en specs/código)
curl -X POST http://localhost:8100/ingest

# Ver que apps cambiaron desde el ultimo refresh (rapido, solo hashes)
curl http://localhost:8100/refresh/detect

# Re-auditar SOLO las apps marcadas como cambiadas (mas rapido que el auditor completo)
curl -X POST http://localhost:8100/refresh -H "Content-Type: application/json" -d '{}'
```

`/refresh` actualiza `PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/etc. de forma
incremental sin salir del contenedor — pero **sigue estando horneado en la
imagen actual**, así que no sirve como sustituto de un rebuild si lo que
necesitás es que un *nuevo despliegue* arranque ya con los datos frescos
(ver sección 2.1). Sirve para refrescar el contenedor que ya está corriendo.

### 3.5 Introspección del proyecto

```bash
curl http://localhost:8100/indices                     # tamano de los 9 indices especializados
curl "http://localhost:8100/manifest/shop"              # manifest completo de una app
curl "http://localhost:8100/memory?app=renting"         # memoria estatica de una app
curl "http://localhost:8100/graph/node/Product"         # vecindario del knowledge graph
curl "http://localhost:8100/graph/impact/Product"       # cadena de impacto transitivo
curl -X POST http://localhost:8100/search -H "Content-Type: application/json" \
  -d '{"query": "como funciona ProductSerializer"}'
```

---

## 4. AI Core — acciones de negocio (`/chat`)

Este es el motor conversacional que usan el widget de soporte y WhatsApp.
**Requiere un JWT real de Django** — nunca acepta un request anónimo.

### 4.1 Conseguir un JWT para probar

En dev, la forma más simple es loguearte contra Django y copiar el
`access` token de la respuesta:

```bash
curl -X POST http://localhost:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "cliente@ejemplo.com", "password": "..."}'
# { "access": "eyJhbGci...", "refresh": "..." }
```

### 4.2 Conversación simple (solo lectura)

```bash
curl -X POST http://localhost:8100/chat \
  -H "Authorization: Bearer eyJhbGci..." \
  -H "Content-Type: application/json" \
  -d '{"message": "cual es el estado de mi ultimo pedido?"}'
```

```json
{
  "conversation_id": "a1b2c3d4e5f6",
  "intent": "order_status",
  "agent": "OrderAgent",
  "tool_calls": [{"tool": "OrderStatusTool", "args": {}}],
  "tool_results": [{"capability": "buscar_pedido", "result": {...}}],
  "needs_confirmation": false,
  "confirmation": null,
  "response": "Tu ultimo pedido (#1234) esta en camino, llega el..."
}
```

Reenviar el mismo `conversation_id` en el siguiente mensaje continúa la
misma conversación (memoria de los últimos 3 turnos + estado del grafo).
Si se omite, el motor genera uno nuevo — pero entonces **cada mensaje es una
conversación nueva sin memoria**, así que para cualquier prueba de varios
turnos hay que guardar y reenviar el `conversation_id` de la primera
respuesta.

### 4.3 Conversación con escritura (requiere confirmación humana)

Ninguna acción irreversible se ejecuta sin que el usuario diga "sí" en el
mismo hilo — es una restricción dura del motor, no una opción.

```bash
# 1) El usuario pide cancelar un alquiler
curl -X POST http://localhost:8100/chat \
  -H "Authorization: Bearer eyJhbGci..." -H "Content-Type: application/json" \
  -d '{"conversation_id": "abc123", "message": "cancela mi alquiler del equipo XYZ"}'
```
```json
{
  "conversation_id": "abc123",
  "needs_confirmation": true,
  "confirmation": {
    "action": "cancelar_alquiler",
    "args": {"rental_uuid": "..."},
    "risk": "high",
    "question": "Vas a ejecutar: Cancela una solicitud de alquiler... Responde 'si' para confirmar o 'no' para cancelar."
  },
  "response": "Vas a ejecutar: ... Responde 'si' para confirmar o 'no' para cancelar."
}
```
```bash
# 2) El usuario confirma -- MISMO conversation_id, o bien {"confirm": true}
curl -X POST http://localhost:8100/chat \
  -H "Authorization: Bearer eyJhbGci..." -H "Content-Type: application/json" \
  -d '{"conversation_id": "abc123", "message": "si"}'
# equivalente: -d '{"conversation_id": "abc123", "message": "", "confirm": true}'
```

Cualquier mensaje que no sea un "sí"/"no" (regex `_AFFIRM_RE`/`_NEGATE_RE`
en `action_graph.py`) mientras hay una confirmación pendiente **descarta**
la acción pendiente y se trata como un mensaje nuevo — no queda "colgado"
esperando una respuesta exacta.

Cada escritura ejecutada queda auditada en Django
(`SecurityEvent.AI_ACTION_EXECUTED`, ver `security/` app) con el usuario
real del JWT — nunca un usuario genérico "bot".

### 4.4 Debug de Tools sin pasar por el LLM (solo dev)

Útil para verificar que una Tool puntual funciona antes de confiar en que
el LLM la va a elegir bien. Requiere `AI_TOOLS_DEBUG=true` (ya activo en el
compose de dev) — en cualquier otro entorno responde `404`.

```bash
# Listar todo lo registrado
curl http://localhost:8100/api/v1/ai/tools/debug \
  -H "Authorization: Bearer eyJhbGci..."
# { "tools": [...29...], "capabilities": [...29...], "agents": [...9...] }

# Invocar una Tool de lectura directamente
curl -X POST http://localhost:8100/api/v1/ai/tools/debug \
  -H "Authorization: Bearer eyJhbGci..." -H "Content-Type: application/json" \
  -d '{"tool": "OrderStatusTool", "args": {}}'

# Invocar una Tool de escritura -- exige confirmed:true tambien aqui
curl -X POST http://localhost:8100/api/v1/ai/tools/debug \
  -H "Authorization: Bearer eyJhbGci..." -H "Content-Type: application/json" \
  -d '{"tool": "cancelar_alquiler", "args": {"rental_uuid": "..."}, "confirmed": true}'
```

### 4.5 Smoke-test del puente de identidad

```bash
curl http://localhost:8100/api/v1/ai/context -H "Authorization: Bearer eyJhbGci..."
# 200 con el perfil real del usuario, o 401 explicito si el token es invalido/esta vencido
```

---

## 5. Qué puede hacer el AI Core hoy (mapa rápido)

### 5.1 Los 9 agentes (uno por dominio, `agents/profiles/*.yaml`)

| Agente | Cubre | Herramientas propias |
|---|---|---|
| `SupportAgent` | Reclamos, escalamiento a humano, `unknown` (agente por defecto) | Abrir ticket, ver pedido/alquiler |
| `OrderAgent` | Estado de pedidos, envíos | `OrderStatusTool` |
| `PaymentAgent` | Estado de pagos/transacciones | `PaymentStatusTool` |
| `RentalAgent` | Buscar/reservar/cancelar alquileres, disponibilidad | `RentalStatusTool`, `RentalAvailabilityTool`, `EquipmentSearchTool`, `CreateRentalRequestTool`, `CancelRentalTool` |
| `ServiceAgent` | Estado de servicios técnicos, mantenimiento de equipos | `ServiceStatusTool`, `MaintenanceCheckTool` |
| `AccountAgent` | KYC, upgrade a perfil profesional | `KycStatusTool`, `RequestKycUpgradeTool` |
| `SalesAgent` | Cotizaciones, promociones, recomendaciones personalizadas | `QuoteTemplatesTool`, `StartQuotationTool`, `ActivePromosTool`, `PersonalRecommendationTool` |
| `MarketingAgent` | Dashboard/stock inactivo/campañas (solo admin) | `MarketingDashboardTool`, `StaleStockAlertsTool`, `CampaignTargetsTool` |
| `AdminAgent` | Home Builder / Navbar / Footer / Slider de marcas por conversación (solo admin) | `CoreHomeTool`, `CoreNavbarTool`, `CoreFooterTool`, `CoreBrandSliderTool` + 5 Tools de escritura |

El ruteo intención→agente es automático (`detect_business_intents` en
`action_graph.py`); el usuario nunca elige un agente explícitamente.

### 5.2 Intents reconocidos (regex sobre el mensaje)

`order_status` · `rental_status` · `rental_cancel` · `rental_change` (siempre
escala a soporte — decisión de producto, cambiar fechas de un alquiler
nunca es self-service) · `renting_search` · `payment` · `service_status` ·
`maintenance_check` · `kyc` · `kyc_upgrade` · `quote` · `stock` · `promos` ·
`personal_recommendation` · `support` · `marketing_admin` (solo admin) ·
`core_content` (solo admin) · `knowledge` (cae al RAG de specs/FAQ) ·
`unknown` (fallback → `SupportAgent`).

### 5.3 Tools de escritura (requieren confirmación SIEMPRE)

`CreateRentalRequestTool` · `CancelRentalTool` · `StartQuotationTool` ·
`RequestKycUpgradeTool` · `OpenSupportTicketTool` · `CoreBannerCreateTool` ·
`CoreBannerUpdateTool` · `CoreNavbarLinkCreateTool` ·
`CoreNavbarLinkUpdateTool` · `CoreBrandSliderUpdateTool` — las 5 últimas
exigen además `IsAdminUser` (doble barrera: Policy Layer + permission del
endpoint interno de Django).

---

## 6. Cómo llega el AI Core al usuario final (sin exponer `sintel_ai`)

`ecommerce_sintel_ai` nunca se expone directo al navegador ni a WhatsApp —
Django siempre media:

- **Chat de soporte web**: `support/services/ai_bridge.py` acuña un access
  token efímero del usuario y llama a `/chat` en nombre suyo dentro de
  `SupportChatConsumer` (modo AI). Al abrir un ticket humano, se vuelca la
  transcripción y `ChatRoom.ai_paused=True` (Human Handoff).
- **WhatsApp**: `POST /api/v1/notifications/whatsapp-webhook/` → tarea
  Celery → `/chat` → `WhatsAppClient.send_text()` con la respuesta.
- **Mensajes proactivos**: cualquier slug en `.env:AI_PROACTIVE_SLUGS`
  dispara un mensaje del bot en la sala vía `dispatch_notification()` — sin
  tocar el motor.

Si algo del AI Core no responde en el widget de soporte, el primer lugar a
mirar es **Django** (¿`ai_bridge.py` está acuñando el token?, ¿el usuario
`AI_BOT_EMAIL` existe y está activo?), no necesariamente `sintel_ai`.

---

## 7. El auditor del proyecto (`auditor.py`) — cómo correrlo bien — **RETIRADO 2026-08-09**

> **[CORREGIDO, Fase 20 "Limpieza Documental", 2026-08-10]** `ai_engine/auditor.py` **ya no
> existe** -- fue eliminado por completo el 2026-08-09 al extraerse a `project_knowledge_graph/`
> (paquete independiente, `ai_engine` no lo importa). Todos los comandos `python
> ai_engine/auditor.py` de esta seccion **fallarian con `FileNotFoundError`** si se corren hoy.
> El equivalente real y actual es:
> ```bash
> cd ecommerce_sintel   # (no ecommerce_sintel_rest -- distinto cwd que el auditor.py original)
> python -m project_knowledge_graph.cli audit
> ```
> Se deja el resto de la seccion sin borrar por valor historico (explica CORRECTAMENTE, aunque ya
> no aplique al comando de arriba, el bug real de `BASE_DIR` relativo a `__file__` que motivo la
> regla "correr siempre desde el host" -- `project_knowledge_graph/config.py` sigue el mismo
> criterio hoy, ver `project_knowledge_graph/.AGENT/ARQUITECTURA_COMPLETA_GRAFO.md` seccion 3).

El auditor lee **todo** el codebase (Django + Vue) y genera
`PROJECT_MAP.json` + los demás JSON derivados (Knowledge Graph, Dependency
Graph, memoria, manifests). Es lo que le da al motor su "mapa" del proyecto
para `/impact`, `/plan`, `/manifest/*`, `/graph/*`.

```bash
# CORRECTO -- desde el HOST, parado en la raiz del repo
cd ecommerce_sintel_rest
python ai_engine/auditor.py
```

```
# INCORRECTO -- NUNCA hacer esto
docker exec ecommerce_sintel_ai python auditor.py
```

**Por qué falla silenciosamente dentro del contenedor:** `auditor.py`
calcula `BASE_DIR = Path(__file__).resolve().parent.parent / "ecommerce_sintel"`.
Corrido desde el host, `__file__` es
`.../ecommerce_sintel_rest/ai_engine/auditor.py`, así que `BASE_DIR`
resuelve a `.../ecommerce_sintel_rest/ecommerce_sintel/` (el código Django
real). Corrido con `docker exec` dentro del contenedor, `__file__` es
`/app/auditor.py`, así que `BASE_DIR` resuelve a `/ecommerce_sintel` — una
ruta que no existe ahí (el código Django está montado en `/workspace`, no en
`/`). El auditor no lanza una excepción — reporta cada app como
`"(not found)"` y escribe un `PROJECT_MAP.json` vacío de 0.4 KB, sobre el
`PROJECT_MAP.json` real de casi 1 MB. **Este error ya ocurrió una vez (sesión
2026-07-19) y se corrigió re-corriendo el comando correcto desde el host** —
si el motor de golpe empieza a reportar 0 modelos/apps en `/indices` o
`/manifest/*`, sospechar primero de esto antes de cualquier otra cosa.

Después de regenerar, **el contenedor no ve los archivos nuevos hasta un
rebuild** (sección 2.1) — el auditor solo escribe en el filesystem del host,
y `ai_engine/Dockerfile` los hornea con `COPY . .`, no los monta como
volumen.

```bash
# Flujo completo tras un cambio estructural grande (nuevo modelo, nueva app...)
cd ecommerce_sintel_rest
python ai_engine/auditor.py                         # 1. regenerar en el host
cd ecommerce_sintel
docker compose build sintel_ai                      # 2. hornear los JSON nuevos en la imagen
docker compose up -d sintel_ai                       # 3. recrear el contenedor
curl http://localhost:8100/indices                   # 4. confirmar numeros frescos
```

Para cambios pequeños/incrementales, `POST /refresh` (sección 3.4) es más
rápido y no requiere rebuild — pero solo actualiza el contenedor que ya está
corriendo, no deja rastro en la imagen para el próximo `docker compose up`.

---

## 8. Variables de entorno relevantes (dev)

Ya configuradas en `docker-compose.yml` — normalmente no hace falta
tocarlas, pero son las que importan si algo no conecta:

| Variable | Valor en dev | Para qué |
|---|---|---|
| `AI_TOOLS_DEBUG` | `true` | Habilita `/api/v1/ai/tools/debug` (sección 4.4) |
| `DJANGO_INTERNAL_API_URL` | `http://django:8000/api/v1` | Base para resolver identidad y llamar Tools de lectura |
| `JWT_SECRET_KEY` | (compartida vía `.env`) | Sin ella, **todo** el AI Core falla cerrado con 503 — nunca deja pasar un request sin poder validarlo |
| `LOCAL_MODEL_CHAIN` | `ollama\|ollama-nativo\|http://sintel_ollama:11434\|llama3.1:8b` (default calculado, no seteado explícito) | **[Nivel A, 2026-08-07]** Reemplaza `LLM_PROVIDER` — lista ordenada de motores con fallback automático (`get_llm()` los encadena con `.with_fallbacks()`). Agregar un motor es agregar una entrada `nombre\|tipo\|base_url\|modelo[\|api_key_env]` separada por `;`, sin tocar código. Ver `FLIJO_COMPLETO_IA_ENGINE.md` sección 3bis. |
| `CHROMA_HOST` / `CHROMA_PORT` | `sintel_chromadb` / `8000` | Vectorstore — si no conecta, `/health` sigue respondiendo pero `chunks_indexed` puede quedar en 0 |

---

## 9. Troubleshooting rápido

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `/chat` devuelve 401 en todos los requests | JWT vencido, o `JWT_SECRET_KEY` no coincide entre Django y `sintel_ai` | Sacar un token nuevo (sección 4.1); confirmar que ambos servicios comparten el mismo `.env` |
| `/chat` devuelve 503 | `JWT_SECRET_KEY` no configurada en el motor | Revisar `config.py`/env del contenedor |
| `/api/v1/ai/tools/debug` da 404 siempre | `AI_TOOLS_DEBUG` no está en `true` en ese entorno (correcto en prod) | Solo esperado fuera de dev — no es un bug |
| `/indices`, `/manifest/*` devuelven todo en 0 o "not found" | `ai_engine/PROJECT_MAP.json` es una foto estatica (el auditor que lo regeneraba fue retirado 2026-08-09, sección 7) | No hay forma de regenerarlo desde `ai_engine` hoy -- si el gap real es "el grafo esta desactualizado", regenerar `project_knowledge_graph/data/PROJECT_MAP.json` con `python -m project_knowledge_graph.cli audit` (sección 7), que es un artefacto DISTINTO, no compartido con `ai_engine` |
| Cambié código de una Tool/agente y `/chat` sigue con el comportamiento viejo | Falta un rebuild — el código está horneado en la imagen | `docker compose build sintel_ai && docker compose up -d sintel_ai` |
| El widget de soporte no responde con IA | El problema suele estar en Django (`ai_bridge.py`, usuario `AI_BOT_EMAIL`), no en `sintel_ai` | Revisar logs de `ecommerce_sintel_django`, luego los de `sintel_ai` |
| Un Agent Profile YAML con un typo tumba el arranque | `agents/__init__.py::_load_profiles()` valida los 9 YAML al importarse — un YAML roto impide el boot (a propósito) | Ver el traceback en `docker logs`, corregir el YAML, rebuild |

---

## 10. Referencias

- `FLIJO_COMPLETO_IA_ENGINE.md` — arquitectura completa del motor (ambos mundos), pipeline de ingesta/recuperación, guardrails, invariantes.
- `PLAN_DE_ACCION_AI_CORE.md` — historia y razonamiento de las 8 fases del AI Core, gaps de negocio, restricciones duras, estado de cierre de cada fase.
- `ai_engine/tools/metadata.py` — campos de `ToolMetadata` (`side_effects`, `risk`, `requires_confirmation`, `rate_limit`, `permissions`).
- `ai_engine/capabilities/registry.py` — las 29 Capabilities y a qué Tool resuelve cada una.
- `security/` (Django) — `SecurityEvent.AI_ACTION_EXECUTED`, el registro durable de cada escritura ejecutada por el AI.
