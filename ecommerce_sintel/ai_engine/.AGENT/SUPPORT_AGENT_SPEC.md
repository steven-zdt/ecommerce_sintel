# Support Agent Spec — Contrato funcional

> Fase 3 del `PLAN_DE_EJECUCION_SUPPORT_AGENT`. Este documento es el contrato del
> `SupportAgent`: qué componentes lo forman, qué garantías debe cumplir cada uno y qué
> queda explícitamente fuera. El alcance de negocio (permitido/prohibido) vive en
> [`AI_SUPPORT_SCOPE.md`](AI_SUPPORT_SCOPE.md); este documento es su contraparte técnica.
>
> **[Revisión 2026-08-08]** "SupportAgent" en el diagrama de abajo es el contrato
> **compartido** por los 9 Agent Profiles reales (`SupportAgent`, `AccountAgent`,
> `AdminAgent`, `MarketingAgent`, `OrderAgent`, `PaymentAgent`, `RentalAgent`,
> `SalesAgent`, `ServiceAgent` — ver `AI_SUPPORT_SCOPE.md` seccion 1). Cada Agent Profile
> personaliza `herramientas`/`permisos`/`capacidades`/`intents`/`tono`, pero los 9 pasan
> por el mismo `action_graph.py` y cumplen el mismo contrato de Identity/Context/
> Knowledge/Tools/Policy/Memory/Conversation/Handoff/Response.

---

## 1. Forma del contrato

```text
SupportAgent (== la plataforma de 9 Agent Profiles, ver AI_SUPPORT_SCOPE.md seccion 1)
│
├── Identity       -- JWT real de Django, resuelto por auth.py
├── Intent         -- Agent Registry (agents/profiles/*.yaml) + Agent Router
├── Context         -- Customer Context Builder (via Tools, nunca ORM directo)
├── Knowledge       -- RAG: retrievers.py sobre ChromaDB
├── Tools           -- Tool Registry (tools/registry.py) + http_bridge.py
├── Policy          -- Policy Layer sobre ToolMetadata (tools/metadata.py)
├── Memory          -- Conversación (Redis, TTL 7d) + cliente
├── Conversation     -- Conversation Manager (thread_id, ai_paused, historial)
├── Handoff          -- ChatRoom.ai_paused + transcripción a agente humano
└── Response         -- action_graph.py -- salida final de /chat
```

Cada nodo del contrato mapea a código que **ya existe** en `ecommerce_sintel/ai_engine/`
salvo que se indique lo contrario ("A CONSTRUIR").

## 2. Lo que el agente NO tiene

```text
CodeGenerator        -- chains.py / chains_frontend.py
CodePlanner           -- planner.py
CodeValidator          -- guardrails.py / guardrails_frontend.py
CodeEditor             -- no existe (bien)
RepositoryWriter       -- no existe (bien)
MigrationGenerator      -- no existe (bien)
FrontendGenerator       -- chains_frontend.py
```

El `SupportAgent` no importa ni invoca ninguno de estos módulos. Ver regla de dependencia
en `AI_SUPPORT_SCOPE.md` seccion 4.

## 3. Identity

- Autenticación vía JWT real de Django, validado con PyJWT (HS256) en `auth.py`.
- La identidad resuelta (`user_id`, `tenant`/organización, permisos) es lo único que el
  resto del grafo puede usar para autorizar Tools — nunca un dato provisto por el propio
  mensaje del usuario.

## 4. Intent

Registro de agentes por dominio en `agents/profiles/*.yaml` (Agent Registry, cargado y
validado al importar `agents/`). Cada profile declara: `name`, `herramientas`, `permisos`,
`capacidades`, `intents`, `memoria`, `reglas_escalamiento`, `tono`.

**[Revisión 2026-08-08]** La lista original de esta sección era un vocabulario propuesto
por el plan general, no lo que existe en código. Se reemplaza por el vocabulario real,
verificado contra `BUSINESS_INTENT_PATTERNS`/`INTENT_CAPABILITIES` en `action_graph.py` y
`intents:` de cada YAML en `agents/profiles/`:

```text
Intent                    -> Agent Profile   -> Capabilities (INTENT_CAPABILITIES)
support, rental_change,
  unknown                 -> SupportAgent    -- abrir_ticket_soporte, buscar_alquiler
kyc, kyc_upgrade          -> AccountAgent    -- consultar_kyc, solicitar_upgrade_profesional
core_content,
  maintenance_check,
  architecture_impact*    -> AdminAgent      -- ver/editar home+navbar+footer+brand_slider,
                                                 verificar_mantenimiento,
                                                 analizar_impacto_arquitectura*
marketing_admin,
  personal_recommendation -> MarketingAgent  -- ver_dashboard_marketing, alertas_stock_inactivo,
                                                 targets_campana, recomendar_al_cliente
order_status               -> OrderAgent      -- buscar_pedido
payment                    -> PaymentAgent    -- consultar_pago
rental_status,
  renting_search,
  rental_cancel, stock     -> RentalAgent     -- buscar_alquiler, buscar_equipos,
                                                 verificar_disponibilidad, crear_alquiler,
                                                 cancelar_alquiler, consultar_stock
promos, quote, knowledge   -> SalesAgent      -- consultar_promociones, cotizacion*, RAG
service_status              -> ServiceAgent    -- consultar_servicio, buscar_pedido
```

`*` `architecture_impact`/`analizar_impacto_arquitectura` es la única excepción
documentada en `AI_SUPPORT_SCOPE.md` seccion 4bis — toca `dependency_graph.py`/
`knowledge_graph.py`, aceptada deliberadamente, no replicar el patrón para intents nuevos.

No crear intents nuevos por sinónimo (p.ej. `pedido_status` junto a `order_status`) sin
verificar primero si `BUSINESS_INTENT_PATTERNS` ya lo cubre con otra frase regex — el
patrón del proyecto es regex amplio por intent, no 1:1 por frase.

## 5. Context

Regla no negociable:

```text
AI Agent -> Tool -> Django Internal API / Service -> Business Logic
```

El LLM nunca consulta el ORM directamente. Todo dato de negocio llega por una Tool
registrada en `tools/registry.py`, que a su vez llama a `tools/http_bridge.py` contra
endpoints internos de Django.

**Customer Context Builder — verificado 2026-08-08, existe y es más angosto que el
diagrama original de esta sección:**
`AiCustomerContextView` (`accounts/api/internal_ai.py`, `GET
/api/v1/internal/ai/customer-context/`) agrega `MarketingSelector.get_user_marketing_profile`
+ `ShippingAddressSelector.list_for_user` + tarjetas tokenizadas (marca/últimos 4, nunca el
token), cacheado en Redis 5 min (`CUSTOMER_CONTEXT_CACHE_TTL`). Solo trae **marketing +
addresses + payment_methods** — no orders/renting/services/quotes/support history
preempaquetados. `node_optimize_context` en `action_graph.py` solo lo pide para
`_CRM_CONTEXT_INTENTS = {"renting_search", "promos", "quote", "personal_recommendation"}`,
no en cada turno. Orders/renting/services/quotes se resuelven bajo demanda vía Tools
específicas (`buscar_pedido`, `buscar_alquiler`, `consultar_servicio`,
`consultar_plantillas_cotizacion`) cuando el intent correspondiente dispara esa
capability — no se preempaquetan como parte del Customer Context. Esto cumple mejor el
principio de "presupuesto explícito" de Fase 5 que el diagrama original (que sugería
traer todo el dominio de una vez); no es una brecha a cerrar, es una decisión de diseño
ya tomada y correcta.

## 6. Knowledge (RAG)

- Retrieval híbrido: `retrievers.py` (BM25 + MMR) sobre ChromaDB
  (`vectorstore_factory.py`). **Corrección 2026-08-08**: `specialized_retrieval.py`
  (índices especializados) **no** es parte del camino de `/chat` — solo lo importa
  `main.py` para `/search`/`/indices`, que son del mundo de generación de código. Ver
  `AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md` seccion 4.
- Debe indexar: productos, servicios, renting, cotizaciones, pagos, pedidos, garantías,
  políticas, FAQ, procedimientos de soporte, documentación comercial/operativa.
- No debe indexarse jamás como conocimiento conversacional: código fuente completo,
  credenciales, secretos, tokens, datos de otros clientes, datos sensibles innecesarios.
- **[Corregido 2026-08-08]** `bootstrap.py` sigue indexando `CODEBASE_PATH` (código
  fuente) en la misma colección ChromaDB que usa `chains.py` para generación de código —
  eso está bien, ese motor sí necesita ver código real. Lo que se corrigió fue el lado de
  `/chat`: `node_retrieve_knowledge` (`action_graph.py`) usaba `retrieve_context_for_task`
  sin filtrar, lo que además de código fuente Python/Vue inyectaba **siempre** 5 chunks
  fijos de "reglas globales criticas arquitectura service layer decimal soft-delete
  transaction.on_commit" en cada respuesta a un cliente. Ahora usa
  `retrieve_knowledge_for_chat` (nueva función en `retrievers.py`), que filtra por
  `metadata.language == "markdown"` (specs/architecture/drf_spec/frontend_spec
  únicamente) y no inyecta el bloque de reglas internas. `retrieve_context_for_task`
  queda intacta para `chains.py`/`chains_frontend.py`. Ver
  `AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md` hallazgo 1.

### 6bis. Knowledge Governance (Fase 17, PLAN_MAESTRO_SINTEL_AI_SUPPORT, auditado 2026-08-08)

**Gap real confirmado — no implementado.** `loaders.py::_infer_metadata` etiqueta cada
chunk únicamente con `app_name`, `doc_type`, `layer`, `language` (más el `source` =
ruta de archivo, que LangChain agrega implícitamente). No existe `version`, `updated_at`,
`visibility`, ni `domain` como campo separado de `app_name`. La ingesta
(`bootstrap.py`/`incremental_updater.py`) usa un hash por archivo
(`.file_hashes.json`) solo para *decidir* qué re-ingestar — ese hash nunca queda
expuesto como metadata del documento en sí.

**Consecuencia concreta**: `retrieve_knowledge_for_chat` (`retrievers.py`) solo pasa
`d.page_content` al LLM — nunca `d.metadata["source"]` ni ninguna otra traza. Ni el log
(`[retrievers] chat-knowledge query=... -> N chunks`) ni la respuesta al cliente
registran **qué documento específico** respaldó una respuesta dada. Hoy es imposible,
sin ir a grep manual, responder "¿de qué documento salió esa respuesta y qué tan
reciente es?" — el requisito de Fase 17 ("el AI debe poder determinar qué información
utilizó, de dónde provino, qué versión tenía") no se cumple.

**Qué haría falta** (no implementado en esta sesión — gobierno documental completo es
más grande que un fix puntual, requiere decisión de diseño):
1. Agregar `updated_at` (mtime del archivo) y `visibility` (`public`/`internal`) a
   `_infer_metadata`.
2. Loguear `d.metadata.get("source")` por chunk usado en `node_retrieve_knowledge`
   (a nivel debug alcanza), para poder auditar retroactivamente qué documento sustentó
   una respuesta.
3. Decidir un esquema de versión real (¿hash de contenido? ¿tag de doc?) — no existe
   hoy ni siquiera informalmente.

## 7. Tools

Tool Registry (`tools/registry.py`, decorador `@register_tool`) + Capability Registry
(`capabilities/registry.py`) + `ToolMetadata` (`tools/metadata.py`), que ya declara los
campos que sostienen Policy y Confirmación.

**Verificado 2026-08-08 — completo:** `register_tool` rechaza nombres duplicados y
funciones no-async al registrarse; `invoke()` nunca deja pasar un argumento desconocido
al callable (whitelist contra la firma o, para Tools `**kwargs`, contra
`args_schema.properties`) y nunca propaga una excepción cruda — siempre vuelve un dict
serializable con `error`/`status_code`. `CapabilityRegistry` (`capabilities/registry.py`)
versiona (`version`, `status: active|deprecated` — una capability deprecated sigue
respondiendo pero `list_active()` la excluye) y el LLM nunca ve una Tool concreta, solo
`description_for_llm` de la capability.

```text
permissions            list[str]   -- permission classes Django equivalentes
risk                   str         -- low | medium | high
rate_limit              str         -- ej. "10/hour/user", aplicado por la Policy Layer
requires_confirmation   bool
side_effects            bool        -- True = escritura: pasa SIEMPRE por Policy Layer
```

Clasificación operativa:

- **READ** — se ejecuta directamente (consultar pedido, disponibilidad, producto,
  servicio, cotización, estado de pago).
- **WRITE** — requiere Policy (crear solicitud de renting, crear ticket, iniciar
  cotización, solicitar upgrade KYC, cancelar solicitud).
- **HIGH RISK** — siempre policy + confirmation + audit + execution.

### 7bis. Cost Control (Fase 23, PLAN_MAESTRO_SINTEL_AI_SUPPORT, auditado 2026-08-08)

**Gap real confirmado.** Verificado contra el checklist de la Fase 23
(`requests/user`, `requests/conversation`, `tokens/request`, `tokens/day`,
`tool calls/request`):

| Control pedido | Estado real |
|---|---|
| Tokens por llamada al LLM | **Existe** — `num_predict=1500`, `num_ctx=8192` (`llm_factory.py`), `MAX_CONTEXT_CHARS=6000` por turno (`action_graph.py`) |
| Rate limit por Tool | **Parcial** — solo 5 de ~30 Tools declaran `rate_limit` (`request_upgrade_kyc` 3/hora, `start_quote` 5/hora, `create_rental` 10/hora, `cancel_rental` 5/hora, `abrir_ticket_soporte` 10/hora) — todas del lado **escritura**. Las Tools de lectura no tienen rate limit en ningún lado |
| `tokens/day`, `requests/conversation`, `requests/user` agregados | **No existen** — no hay ningún contador acumulado por día/usuario/conversación, solo el rate limit puntual por-Tool arriba |
| Rate limit a nivel Django (`internal_ai/*.py`) | **Solo 1 endpoint de 5**: `AiSupportTicketView` usa `ScopedRateThrottle` (`ai_support_ticket`). Los endpoints de lectura (`orders`, `renting/equipment`, `quotes`, `customer-context`, etc.) no declaran `throttle_classes` — sin `DEFAULT_THROTTLE_CLASSES` global en `REST_FRAMEWORK` (verificado en `ecommerce/settings/base.py`), quedan sin límite alguno |
| Rate limit persistente/distribuido | **No** — `_RATE_HITS` (`action_graph.py`) es un `dict` en memoria del proceso: se resetea en cada restart del contenedor y no serviría si `sintel_ai` alguna vez corre en más de una réplica |
| Límite de llamadas a Tools por turno | **No hay un tope explícito** — el grafo ejecuta como máximo 1 escritura por turno por diseño (`node_execute_write` comentario: "Ejecuta LA escritura pendiente"), pero no hay límite documentado de cuántas Tools de lectura puede encadenar el LLM en un solo turno antes de responder |

**Conclusión**: el costo por *llamada individual* está acotado (tokens/contexto), pero el
costo *agregado* (por usuario, por día, por conversación) no tiene ningún control real
hoy — un usuario autenticado podría, en teoría, generar tráfico de lectura ilimitado
hacia el LLM sin disparar ningún límite. No implementado en esta sesión — requiere
decidir dónde vive el contador agregado (¿Redis, ya usado para el checkpointer?) antes
de construirlo.

## 8. Policy / Confirmación / Audit

```text
Tool -> Policy -> Confirmation -> Execution -> Audit
```

Regla no negociable: nunca `LLM -> Django POST` directo. Siempre:

```text
LLM -> Capability -> Tool -> Policy -> Confirmation -> Django
```

**Verificado 2026-08-08 — las 3 etapas existen y están completas, no "A CONSTRUIR" como
decía la versión anterior de esta sección:**

- **Policy** (`node_evaluate_policy`, `action_graph.py`): `deny` si
  `"IsAdminUser" in metadata.permissions` y el usuario no es staff, o si excede
  `metadata.rate_limit` (rate limiter en memoria por `(user_id, tool)`, ventanas
  hora/día); `confirm` si `metadata.requires_confirmation`; si no, `allow`. La
  autorización real (permission classes) la vuelve a aplicar Django en el endpoint
  interno — esto es defensa temprana, nunca la única capa.
- **Confirmation** (`node_request_confirmation`): usa `langgraph.types.interrupt()` para
  pausar el grafo de verdad hasta que el cliente responda "sí"/"no" en la misma
  conversación — no es un flag simulado. Un "no" nunca ejecuta la escritura y deja un
  `tool_results` explícito ("nada fue cancelado ni creado").
- **Audit** (`node_execute_write` + `node_audit_log`): cada escritura ejecutada pasa por
  `log_ai_action()` (`ecommerce_sintel/ecommerce/internal_ai_utils.py`), llamado desde
  cada endpoint interno de escritura (`support`, `quotes`, `core`, `renting`, `kyc` —
  `api/internal_ai.py` de cada app) y crea un `SecurityEvent.AI_ACTION_EXECUTED`
  (`security/models.py`) con el usuario real del JWT. `node_audit_log` además deja un log
  estructurado del lado del motor. Cubierto por tests en `support/tests.py`.

`side_effects=True` en `ToolMetadata` es la señal que obliga a pasar por Policy.

### 8bis. Error Handling / Fallback (Fases 28-29, PLAN_MAESTRO_SINTEL_AI_SUPPORT, auditado 2026-08-08)

Checklist verificado contra código real:

| Escenario | Estado |
|---|---|
| LLM no disponible | **Cubierto** — `llm_factory.py::get_llm()` encadena fallback nativo de LangChain (`.with_fallbacks()`) sobre `LOCAL_MODEL_CHAIN`; si absolutamente todo falla, el `try/except` de `/chat` en `main.py` devuelve "nuestro asistente no esta disponible... un agente humano revisara tu mensaje" (handoff implícito) |
| RAG no disponible | **Cubierto** — `node_retrieve_knowledge` chequea `vectorstore is None or not all_docs` explícitamente, devuelve error sin intentar inventar conocimiento |
| Redis no disponible | **Cubierto solo genéricamente** — `redis_checkpointer.py` no tiene ningún `try/except` propio para errores de conexión; una caída de Redis se propaga como excepción cruda hasta el catch-all de `main.py` (mismo mensaje genérico que "LLM no disponible" — funciona, pero no diferencia la causa) |
| Django no disponible | **Cubierto** — `tools/http_bridge.py` (`django_internal_get`/`_post`) captura `httpx.HTTPError` explícitamente, devuelve `{"error": ..., "status_code": 502}`, nunca propaga la excepción cruda |
| Tool timeout | **Declarado pero NO enforced** — `ToolMetadata.timeout_ms` (default 8000ms) existe como campo, pero ni `tools/registry.py::invoke()` ni `action_graph.py` lo leen ni lo aplican (no hay `asyncio.wait_for`/`asyncio.timeout` en ningún lado). El único timeout real es el de `httpx.AsyncClient` dentro de `http_bridge.py`, con sus propios defaults hardcodeados (8000/10000ms), no leídos de `ToolMetadata`. Una Tool que no pase por `http_bridge.py` no tiene ninguna protección de timeout |
| Tool failure / resultado inválido | **Cubierto** — `tools/registry.py::invoke()` nunca deja escapar una excepción (siempre `{"error":..., "status_code":500}`); `node_validate_tool_result` marca errores/resultados vacíos como "Avisos" explícitos en el contexto para que el LLM responda honesto, nunca inventado |
| Confirmación inválida/ambigua | **Cubierto** — si el mensaje no matchea `_AFFIRM_RE`/`_NEGATE_RE` tras un `interrupt()` pendiente, `run_action_chat` descarta la acción pendiente y trata el mensaje como petición nueva (nunca ejecuta una escritura por una respuesta ambigua) |
| Conversación expirada (TTL Redis vencido) | **Cubierto por diseño de LangGraph** — un `thread_id` sin checkpoint simplemente arranca estado nuevo, no es un caso de error especial |
| Fallo de autenticación | **Cubierto** — `auth.py`/`get_validated_token` rechaza con 401 antes de llegar a `run_action_chat` |

**Único gap real de esta fase**: `ToolMetadata.timeout_ms` es metadata declarativa sin
aplicación real fuera de las Tools que llaman a Django vía `http_bridge.py`. No
corregido en esta sesión (requiere decidir el mecanismo de timeout genérico —
`asyncio.wait_for` alrededor de `tool.func(...)` en `tools/registry.py::invoke()` sería
el punto natural).

## 9. Memory / Conversation

- Estado conversacional en Redis vía `redis_checkpointer.py`
  (`RedisCheckpointSaver`, `CHECKPOINT_TTL_SECONDS = 7 * 24 * 60 * 60`).
- Memoria = conversación (Redis) + cliente (Customer Context, sección 5).

**Conversation Manager — verificado 2026-08-08: existe, pero repartido en dos sistemas
por diseño, no como una clase única.** No es una brecha — es consistente con la regla
final del plan general ("Django sigue siendo dueño de la lógica de negocio y los datos"):

```text
Django (support.ChatRoom)          ai_engine (action_graph.py / redis_checkpointer.py)
  status                             thread_id = f"{user_id}:{conversation_id}"  (Fase 3)
  ai_paused                          history (LangGraph checkpoint state)
  is_deleted                         TTL 7 dias (CHECKPOINT_TTL_SECONDS)
  (dueño del ciclo de vida del room) (dueño del estado de turno del grafo)
```

- `thread_id` se namespacea `{user_id}:{conversation_id}` (`run_action_chat`,
  `action_graph.py`) — esto es a la vez el mecanismo de continuidad conversacional Y el
  aislamiento de seguridad (Fase 14: nadie retoma la conversación de otro usuario
  adivinando `conversation_id`). **Verificado 2026-08-08**: `user_id` viene siempre del
  JWT validado server-side (`payload["user_id"]` en `main.py`), nunca del cliente —
  aunque un atacante adivine el `conversation_id` de otro, su propio `user_id` real
  prefija el `thread_id`, así que jamás puede colisionar con el hilo de otro usuario.
  Aislamiento de conversación (Fase 6, item 25) cerrado, sin gaps.
- `is_ai_mode_active(room)` (`support/services/ai_bridge.py`) chequea `not
  room.ai_paused` **antes** de llamar `/chat` — el gate de Handoff vive en Django, no en
  `action_graph.py`.
- `tenant_id`: no existe como concepto en `ai_engine` ni en Django — el sistema es
  single-tenant (una sola organización SINTEL). El campo de la Fase 9 original no aplica
  hoy; no crear un `tenant_id` ficticio solo para calzar con el diagrama del plan.

## 10. Handoff

```text
Cliente -> AI -> intenta resolver -> ¿puede resolver?
    si  -> respuesta
    no  -> Handoff -> AI PAUSED -> Agente humano
```

**Verificado 2026-08-08 — completo end-to-end, con dos capas:**

1. **Agent-to-agent (dentro del turno, Fase 6)**: `AgentRegistry.apply_escalation`
   (`agents/__init__.py`) — cada uno de los 8 agentes no-Support declara
   `reglas_escalamiento` (regex de queja/reclamo/molestia en su propio `profiles/*.yaml`)
   que, si matchean, redirigen el turno a `SupportAgent` antes de responder
   (`node_detect_intent`, `action_graph.py` linea ~192). `SupportAgent` es el único con
   `reglas_escalamiento: []` — es el destino final, no escala a nadie más.
2. **AI-to-human (`ChatRoom.ai_paused`)**: cuando `SupportAgent` invoca la capability
   `abrir_ticket_soporte`, el endpoint `AiSupportTicketView.post`
   (`support/api/internal_ai.py`) vuelca la transcripción completa
   (`_dump_ai_transcript`, nunca truncada), guarda el mensaje, pone `ai_paused=True` y
   notifica admins (`_notify_support_admins`). El WebSocket consumer
   (`support/consumers.py:277-278`) también puede setearlo. `support/tasks.py` corre un
   cron de seguridad para salas escaladas sin atender tras
   `_UNATTENDED_THRESHOLD_HOURS`. Todo cubierto por tests en `support/tests.py`
   (líneas 284, 670, 726-739).
- Índice compuesto `['status', 'ai_paused', 'updated_at', 'is_deleted']` en
  `ChatRoom` (`ecommerce_sintel/support/models.py`) soporta las queries de panel/cron.
- `support/services/ai_bridge.py::is_ai_mode_active` es el gate simétrico del lado
  Django: si `room.ai_paused`, ni siquiera se llama a `/chat`.

## 11. Response

Orquestado por `action_graph.py` (grafo paralelo a `graph.py`, no lo toca) y expuesto en
`POST /chat` (`main.py`). Esta es la única superficie de respuesta del Support Agent —
`/generate`, `/validate`, `/plan`, `/impact`, `/breakage` no son parte de este contrato
(ver `AI_SUPPORT_SCOPE.md`).

## 11bis. Inference Gateway (Fase 12)

**Verificado 2026-08-08 — ya implementado, no falta construir nada funcional.**
`llm_factory.py::get_llm()` arma la cadena `LOCAL_MODEL_CHAIN` (`config.py`) y usa el
fallback nativo de LangChain: `primary.with_fallbacks(fallbacks)`. El primer motor de la
cadena es el primario, el resto son fallback automático — exactamente el diseño
"Primary -> Fallback" que pide la Fase 12 ("no implementar todavía routing complejo por
inteligencia... Primary, Fallback es suficiente"). Solo falta el renombre conceptual
(de "LLM_PROVIDER" a "Inference Gateway"), que es cosmético — por eso `llm_factory.py`
queda `SUPPORT_REFACTOR` (nombre, no función) en `AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md`.

## 12. Multicanal

El Agent no debe saber si el mensaje llegó desde Web Chat o WhatsApp.

**[Corrección mayor 2026-08-08]** WhatsApp **no es trabajo futuro** — ya está
implementado y en producción, contrario a lo que asumía esta sección y el plan general
(Fase 11: "Primero Web Chat... Después WhatsApp"). `notifications/api/whatsapp_webhook.py`
(Meta Cloud API, verificación de firma HMAC fail-closed, dedupe por `message_id` vía
Redis) despacha `process_whatsapp_inbound_task` (`notifications/tasks.py`), que llama al
**mismo** `support.services.ai_bridge::ask_ai()` que usa Web Chat — confirma que el
Support Agent ya es agnóstico de canal en el nivel del motor de IA, tal como pide esta
sección.

**Gap real y ya reconocido por el propio código** (no inventado por esta auditoría, el
comentario en `notifications/tasks.py:298-302` ya lo documenta): el canal de WhatsApp
usa `conversation_id = f"wa-{user_id}"` (namespace fijo por usuario, separado de
`room-{uuid}` del canal web) y **no** consulta `ChatRoom.ai_paused`/
`is_ai_mode_active` antes de llamar a `ask_ai()`. Consecuencia: si un agente humano tomó
el control de la conversación web de un cliente (handoff activo, `ai_paused=True`), y ese
mismo cliente escribe por WhatsApp, **la IA le sigue respondiendo por WhatsApp** sin
enterarse del handoff — el Handoff de la Fase 10 no es cross-canal todavía. Esto rompe
parcialmente el principio de esta sección ("el Agent no debe saber por qué canal llegó")
en el sentido inverso: el *handoff* sí depende hoy de por qué canal llegó. Postergado
deliberadamente por el equipo (`AUDITORIA/19_AUDITORIA_COMMUNICATION_CENTER_CANALES.md`
§2) — requiere diseño cross-canal, no es un descuido. Debe resolverse antes de certificar
Fase 16 con WhatsApp incluido.

## 13bis. Observabilidad y Seguridad (Bloque 9, verificado 2026-08-08)

**Observabilidad (Fase 13).** `TurnMetrics` (`observability.py`) ya emite por turno, como
una línea JSON estructurada: `conversation_id`, `user_id`, `agent`, `intent`, `llm_calls`,
`llm_tokens_in/out`, `tool_calls`, `tool_errors`, `tools` (nombre+ms+ok por tool =
`tool_latency`), `fallback_used`, `handoff`, `needs_confirmation`, `write_executed`,
`duration_ms`. Cubre casi toda la lista de la Fase 13 salvo dos campos cosméticos, no
bloqueantes: `request_id` explícito (hoy solo hay `conversation_id`+timestamp del log) y
qué modelo concreto de `LOCAL_MODEL_CHAIN` respondió (útil cuando `fallback_used=true`
para saber cuál). Prometheus/OTel confirmado **no instalado** — el logger
`"observability"` ya está preparado para conectarle un exporter sin tocar el grafo
(comentario propio del archivo).

**Seguridad (Fase 14), checklist verificado contra código real:**

| Item | Estado |
|---|---|
| JWT | `auth.py`, PyJWT HS256, validado en cada request (`Depends(get_validated_token)`) |
| User identity | Siempre resuelta server-side, nunca confiada del payload del cliente |
| Tenant isolation | N/A — sistema single-tenant (confirmado seccion 9) |
| Permissions | `metadata.permissions` (`IsAdminUser` etc.) chequeado en `node_evaluate_policy` + reforzado de nuevo por Django en el endpoint interno |
| Tool permissions | Igual que arriba, por Tool via `ToolMetadata` |
| Write confirmation | `interrupt()` real, ver seccion 8 |
| Rate limit | Rate limiter en memoria por `(user_id, tool)` en `node_evaluate_policy`, ver seccion 8 |
| Audit | `SecurityEvent.AI_ACTION_EXECUTED`, ver seccion 8 |
| PII protection | `node_audit_log` solo audita **nombres** de argumentos (`sorted(args.keys())`), nunca los valores; `TurnMetrics` no registra argumentos de tools ni contenido de mensajes, solo metadata agregada |
| Secret protection | El JWT (`token`) viaja en `config["configurable"]`, nunca en `state` (lo que persiste el checkpointer) ni en `TurnMetrics.data` |

**Una observación menor, no un hallazgo bloqueante:** `action_graph.py` linea ~463
(`node_select_and_execute_tools`, rama de tool-call descartada por argumentos inválidos)
loguea `tc["args"]` completos a nivel INFO — si el LLM propuso una escritura con datos
personales del cliente (nombre, dirección) y esa llamada se descarta por inválida, esos
datos quedan en el log de aplicación. Bajo riesgo (son datos que el propio cliente ya
compartió en la conversación, y solo se loguea cuando la llamada se descarta, no en el
camino normal), pero si se endurece Fase 14 formalmente conviene revisarlo.

## 13ter. Tests unitarios (Bloque 10, agregado 2026-08-08)

**Hallazgo previo a este cambio**: `ai_engine` (el motor Python/LangGraph) no tenía
**ningún** test unitario — cero `pytest.ini`, cero `conftest.py`, cero archivo de test.
Toda la cobertura de IA vivía mockeada del lado Django
(`ecommerce_sintel/support/tests.py`, 27 tests, 5 de IA/handoff), que mockea la llamada
HTTP al AI Engine en vez de ejercitar `action_graph.py` real. El fix del Bloque 4
(`retrieve_knowledge_for_chat`) y toda la lógica de Policy/Escalamiento verificada en los
Bloques 3 y 5 no tenían ninguna red de regresión.

Se agregó `ai_engine/tests/` (pytest + pytest-asyncio, nuevos en `requirements.txt` —
**requiere rebuild de la imagen** `docker compose build sintel_ai`):

- `test_intent_detection.py` — fija el vocabulario real de `BUSINESS_INTENT_PATTERNS` +
  `AgentRegistry.route` de la seccion 4 (19 intents x su agente esperado).
- `test_agent_escalation.py` — `AgentRegistry.apply_escalation` (agente-a-agente por
  queja/reclamo, y que `SupportAgent` nunca escala más allá de sí mismo).
- `test_policy_layer.py` — `node_evaluate_policy` con capabilities reales
  (`abrir_ticket_soporte`=allow, `crear_alquiler`=confirm,
  `verificar_mantenimiento`=deny para no-staff) + `_rate_limit_exceeded` en aislamiento.
- `test_retrieve_knowledge_for_chat.py` — el fix del Bloque 4: garantiza que nunca se
  devuelve un doc con `language != "markdown"` y que no reaparece la inyección fija de
  "reglas globales" que tenía `retrieve_context_for_task`.

**[Verificado en runtime 2026-08-08]** Se reconstruyó la imagen (`docker compose build
sintel_ai`) y se corrió la suite dentro del contenedor:

```
docker compose exec sintel_ai pytest tests -v
======================== 56 passed, 1 warning in 0.98s =========================
```

56/56 tests pasan. Además se ejecutó `e2e_support_ai_chat_test.ps1` contra el motor real
(Ollama + ChromaDB + Redis): login real, `POST /chat` con intent `order_status` ->
`OrderAgent` -> `OrderStatusTool` (200 OK, `duration_ms=9364`). Y se probó a mano el
intent `knowledge` específicamente (el que usa el fix del Bloque 4):
`POST /chat {"message": "cual es el horario de atencion"}` -> `intent=knowledge`,
`agent=SalesAgent`, respuesta grounded y correcta. El log del motor confirma el fix
funcionando en producción real:

```
[retrievers] chat-knowledge query='cual es el horario de atencion...' apps=['shop'] -> 12 chunks (dedup de 14, solo markdown)
```

**Un paso del e2e falló, pero no es un problema de este código**: el Paso 4
(concurrencia, `ForEach-Object -Parallel`) requiere PowerShell 7+; este entorno tiene
Windows PowerShell 5.1, que no soporta ese parámetro. Limitación de entorno preexistente
del script, no una regresión — no se tocó.

No cubre el checklist completo de Bloque 10 (integración ya cubierta por `support/tests.py`;
carga/concurrencia real quedó sin probar por la limitación de PowerShell de arriba).

## 12bis. Matrices de prueba (Fases 30-34, PLAN_MAESTRO_SINTEL_AI_SUPPORT, auditado 2026-08-08)

Mapeo de las matrices del plan contra la cobertura real: `support/tests.py` (27 tests,
Django/Channels, mockea la respuesta del AI Engine), `ai_engine/tests/` (56 tests
nuevos de hoy, lógica pura sin mock) y `e2e_http/e2e_support_ai_chat_test.ps1`
(end-to-end contra el motor real).

| Matriz | Cobertura real |
|---|---|
| Chat básico / Funcional (Fase 30) | **Cubierto** — `ai_engine/tests/test_intent_detection.py` fija 19 frases reales por categoría (productos/pedido/renting/servicios/pagos/cotizaciones/soporte); `support/tests.py::test_inicio_conversacion_crea_sala_y_envia_historial` cubre el flujo de infraestructura; e2e cubre `order_status` y `knowledge` reales contra Ollama |
| Aislamiento cliente A/B (IDOR) | **Cubierto** — `test_recuperacion_contexto_order_propia_y_ajena`, `test_ai_open_support_ticket_adjunta_orden_propia_y_rechaza_ajena`, `test_rate_conversation_endpoint_sala_ajena_da_404_sin_distincion` |
| Write sin confirmación / confirmación incorrecta | **Cubierto** — `test_flujo_confirmacion_escritura_dos_turnos`; `ai_engine/tests/test_policy_layer.py` (decision confirm/allow/deny) |
| Tool no autorizada (permisos) | **Cubierto a nivel unitario** (`test_deny_admin_only_para_usuario_no_staff`), no hay equivalente end-to-end vía `/chat` real con un usuario no-staff |
| Token expirado / token inválido | **Hueco real** — no encontré un test explícito de esto contra `/chat` ni contra el WebSocket de soporte (sí hay manejo de código, ver seccion 8bis "Fallo de autenticación", pero sin test dedicado) |
| Context leakage / prompt injection / tool injection | **Hueco real, sin ningún test** — ninguna prueba intenta manipular al LLM para que ejecute una Tool no solicitada, revele contexto de otro usuario, o ignore sus instrucciones vía el mensaje del cliente |
| Tools: matriz input/permission/policy/execution/result/audit por Tool (success/failure/timeout/unauthorized/not-found/invalid-state/duplicate) | **Hueco real** — existen tests puntuales (policy allow/confirm/deny sobre 3 Tools reales), pero no una matriz sistemática por cada una de las ~30 Tools registradas |
| Human Handoff (AI inicia → escala → transcripción → AI paused → humano responde) | **Cubierto** — `test_human_handoff_pausa_sala_y_detiene_ia`, `test_room_closed_avisa_al_cliente_por_ws`, `test_cliente_no_puede_escribir_en_sala_cerrada` |
| Handoff: humano cierra → AI puede reactivarse | **No encontrado explícitamente** — no hay un test que verifique la reactivación de la IA tras el cierre humano de una sala |
| Carga / concurrencia | **Parcial** — `test_concurrencia_multiples_chats_simultaneos` (lado Django/Channels, mockeado); `e2e_support_ai_chat_test.ps1` Paso 4 mide concurrencia real contra Ollama pero **falló hoy** por incompatibilidad de `ForEach-Object -Parallel` con PowerShell 5.1 de este entorno (ver Bloque 10) — sin dato real de carga contra el motor hoy. `CHANNEL_LAYERS capacity=1000/expiry=60` no tiene un test de estrés dedicado |

**Huecos genuinos que quedan, no cerrados en esta sesión** (por alcance/tiempo, no por
imposibilidad): prompt/tool injection, token expirado/inválido contra `/chat` real,
matriz sistemática por Tool, reactivación de IA post-handoff, carga real medida.

## 13. Estado: qué ya existe vs. qué falta

| Bloque del contrato | Estado |
|---|---|
| Identity (`auth.py`) | Existe |
| Tool Registry / Capability Registry / ToolMetadata | Existe |
| Memory (Redis TTL 7d) | Existe |
| Handoff (agent-to-agent + `ChatRoom.ai_paused`) | Existe, completo y con tests (`support/tests.py`) |
| Agent Registry (`agents/profiles/*.yaml`) | Existe (9 profiles — alcance ampliado formalmente 2026-08-08, ver `AI_SUPPORT_SCOPE.md` seccion 1) |
| Excepción `AdminAgent`/`architecture_impact` sobre `dependency_graph.py`/`knowledge_graph.py` | Aceptada deliberadamente 2026-08-08 (`AI_SUPPORT_SCOPE.md` seccion 4bis) — no replicar el patrón |
| RAG (retrievers + specialized_retrieval) | Existe |
| Policy Layer + Confirmation (`interrupt()`) + Audit (`SecurityEvent.AI_ACTION_EXECUTED`) | Existe, completo, con tests — verificado 2026-08-08 |
| Customer Context Builder (`AiCustomerContextView`) | Existe — marketing+addresses+payment_methods, cache Redis 5 min, solo para 4 intents |
| Conversation Manager | Existe, repartido Django (`ChatRoom.ai_paused`/status) + ai_engine (`thread_id`/Redis TTL 7d) por diseño — no requiere consolidarse en una clase única |
| `tenant_id` | No aplica — sistema single-tenant |
| Multicanal (Web Chat + WhatsApp) | **Ambos ya existen** (verificado 2026-08-08, corrige la premisa "WhatsApp es futuro") — gap conocido: handoff no es cross-canal, ver seccion 12 |
| Model Router / Inference Gateway explícito | Existe y funciona (`LOCAL_MODEL_CHAIN` + `.with_fallbacks()`) — verificado 2026-08-08, solo falta el renombre conceptual (cosmético) |
| Observability con Prometheus/OTel | No instalado — solo métricas internas por turno (`observability.py`) |
| Separación física de Code Engineering | No hecha — Fase 17 |
| Filtro RAG `/chat` solo-documentación (`retrieve_knowledge_for_chat`) | Corregido 2026-08-08 — ver `AI_SUPPORT_SCOPE.md` seccion 6 |
| Tests unitarios Python de `ai_engine` | **Agregados 2026-08-08** — `tests/` (intent detection, agent escalation, policy layer, RAG filter). Antes: cero. Ver seccion 13ter |

Este documento se debe actualizar cada vez que un bloque cambie de estado, para que
Fase 16 (Certificación) tenga una fuente confiable de qué falta.

La clasificación componente-por-componente que sostiene esta tabla está en
[`AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md`](AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md)
(Fase 2, Bloque 2 del plan).
