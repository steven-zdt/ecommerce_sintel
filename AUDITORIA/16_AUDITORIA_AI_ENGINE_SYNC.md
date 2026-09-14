# 16 — Auditoría Enterprise: sincronización `support` ↔ `ai_engine` (Fase 2)

> **Fase 2 completada 2026-08-01** — diagnóstico de solo lectura, cero cambios de código.
> Continúa el plan de 16 fases iniciado en [15_AUDITORIA_SUPPORT_OMNICANAL.md](15_AUDITORIA_SUPPORT_OMNICANAL.md)
> (Fase 1, cerrada completa el 2026-07-31). No repite hallazgos ya confirmados/cerrados ahí
> (contrato `ask_ai()`↔`/chat`, bugs de rutas `REPO_ROOT` del move de `ai_engine/`, bug de
> `loaders.py::load_hidden`).

## Mapeo de componentes pedidos → archivos reales

| Concepto pedido | Archivo(s) real(es) | Existe? |
|---|---|---|
| Agents/Profiles | `agents/__init__.py` (`AgentRegistry`) + `agents/profiles/*.yaml` (9 archivos) | Sí |
| Tools | `tools/registry.py` + `tools/*_tools.py` (11 archivos, **30 Tools**, no 29 — ver E1) | Sí |
| Action Graph | `action_graph.py` (`/chat`, negocio) — separado de `graph.py` (generación de código) | Sí |
| "Execution Engine/Planning" | No existe como componente aparte; `agent_graph.py` solo extrae metadatos Agent/Tool para el Knowledge Graph, no ejecuta nada en runtime | Parcial |
| Memory/Conversation State | `MemorySaver` de LangGraph en `action_graph.py` — solo RAM, sin backend externo | Sí, pero limitado (B2) |
| RAG/Knowledge Graph | `loaders.py`, `bootstrap.py`, `retrievers.py`, `knowledge_graph.py`, `KNOWLEDGE_GRAPH.json` | Sí |
| Intent Detection | `BUSINESS_INTENT_PATTERNS` en `action_graph.py` (regex, no LLM) | Sí |
| Observability | `observability.py` (`TurnMetrics`) — sin costo real ni export externo (I1) | Sí, limitado |
| **Prompt Manager / Policies** | **No existe como componente separado** — prompts hardcodeados inline (§H) | **No** |
| Capabilities | `capabilities/registry.py` (`CapabilityRegistry`, 30 entradas) | Sí |

---

## A. Contrato `support` ↔ `ai_engine`

**A1/A2 (info, no bug).** Verificado campo por campo: `OpenSupportTicketTool` ↔
`AiOpenSupportTicketView` coincide exactamente (payload `{message, order_uuid?, rental_uuid?,
history?}`). `tool_results`/`metrics` que `ChatAnalyticsSelector`/`ai_bridge.py` leen coinciden
1:1 con lo que `observability.py::TurnMetrics` y `action_graph.py::_execute_capability` producen.
**Sin mismatch real en ningún punto verificado.**

**A3. Acoplamiento latente entre `ai_response_opened_ticket()` y el flujo de rechazo de confirmación.** (P3, no reproducible con la config actual)
`ai_bridge.py::ai_response_opened_ticket()` interpreta cualquier `tool_results` de
`abrir_ticket_soporte` **sin clave `error`** como "éxito" → pausa la IA. `action_graph.py
::node_request_confirmation` agrega ese mismo shape (sin `error`) cuando el cliente responde "no"
a CUALQUIER escritura pendiente. Hoy inofensivo porque `abrir_ticket_soporte` es la única
write-tool con `requires_confirmation=False` — nunca pasa por ese nodo. Si algún día se le exige
confirmación, un "no" del cliente pausaría la IA como si el ticket se hubiera abierto de verdad.
*Sugerencia:* que el nodo de rechazo marque explícitamente `"declined": true`, o que
`ai_response_opened_ticket()` chequee `action_executed` en vez de solo ausencia de `error`.

---

## B. Memory / Conversation State

**B1 (info, no bug).** Aislamiento real confirmado: `thread_id` = `f"{user_id}:{conversation_id}"`
con `user_id` del JWT validado (nunca del cliente) — memoria correctamente aislada entre salas.

**B2. `MemorySaver` es 100% RAM del proceso — sin backend persistente, sin resiliencia a reinicios.** (P2)
Ningún checkpointer Redis/Postgres/SQLite en todo `ai_engine/`. Un reinicio del contenedor
`sintel_ai` (deploy, crash, `--reload` de uvicorn en cada cambio de archivo) borra TODAS las
conversaciones activas, incluidas confirmaciones de escritura a mitad de curso (el cliente
responde "sí"/"no" a un `interrupt()` que ya no existe → se trata como mensaje nuevo sin
contexto). El rate-limiter de escrituras por usuario (`_RATE_HITS`, dict en memoria) tiene el
mismo problema. Bloquea cualquier plan de escalar `sintel_ai` a más de una réplica (Fase 10 del
roadmap) — hoy ninguna réplica vería el estado de otra.
*Sugerencia:* checkpointer persistente (Redis/Postgres, LangGraph ya trae adaptadores) antes de
escalar horizontalmente o de activar IA ampliamente en producción.

---

## C. Duplicación dentro de `ai_engine`

**C1. Dos Agent Profiles reclaman el mismo intent (`"promos"`) — el router silencia uno por orden alfabético de archivo.** (P3)
`marketing_agent.yaml` y `sales_agent.yaml` declaran ambos el intent `promos`.
`agents/__init__.py::_load_profiles` itera `sorted(glob("*.yaml"))` y sobreescribe la clave sin
validar colisión — `sales_agent.yaml` (`s` > `m`... se carga después y gana) siempre responde,
`marketing_agent.yaml` nunca es alcanzable vía ese intent pese a declararlo y tener la capability.
No rompe funcionalidad (`SalesAgent` también resuelve promociones) pero es dead-code encubierto,
frágil ante un simple rename de archivo.
*Sugerencia:* que `_load_profiles()` falle el arranque si dos perfiles declaran el mismo intent
(mismo criterio que ya usa para capability/tool inexistente).

---

## D. Manejo de errores silencioso

**D1. `except Exception` genérico sin logging en `action_graph.py::_pending_interrupt`.** (P3)
Mismo patrón ya corregido en Fase 1 (`channels_auth.py`, `customer360.py`). Se llama en cada
turno de `/chat` (antes y después de procesar); un fallo real del checkpointer se trata
exactamente igual que "no hay interrupción pendiente", sin ningún log.
*Sugerencia:* loguear antes de devolver `None`, igual que el resto del archivo ya hace en otros puntos.

---

## E. Documentación desactualizada

**E1. Conteo de Tools/Capabilities desactualizado en `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md`.** (P4)
Doc dice "29 Tools, 29 Capabilities" (snapshot 2026-07-19); real hoy: **30/30** —
`GraphImpactAnalysisTool` se agregó el 2026-07-29 (Fase 9 de AUDITORIA/14) y el doc nunca se
actualizó. Conteo de 9 Agents sigue correcto.

---

## F. Seguridad

**F1. `/tools/debug` no reusa la Policy Layer del Action Graph normal.** (P3, no explotable hoy)
`gateway/router.py::tools_debug_invoke` solo valida `side_effects`+`confirmed`, no chequea
`metadata.permissions` ni pasa por `node_audit_log` como sí hace el flujo `/chat` normal
(`node_evaluate_policy`). No explotable: los endpoints internos de Django re-validan permisos de
forma independiente (defensa en profundidad real, segunda capa). Además `AI_TOOLS_DEBUG=true`
solo está en `docker-compose.yml` (dev) — `docker-compose.prod.yml` ni siquiera define el
servicio `sintel_ai`. Riesgo real: cero hoy, pero sin ningún check de CI que lo garantice si se
fusionan los compose files a futuro.
*Sugerencia:* aplicar el chequeo de `permissions` también en `tools_debug_invoke`, y un check de
CI que falle si `AI_TOOLS_DEBUG=true` aparece en un compose usado para prod.

**F2 (info, no bug).** Ownership scoping confirmado real y correcto: vive en los endpoints
internos de Django (ej. `AiOrderStatusView`), nunca confiado al LLM/Tool — se sostiene incluso
bajo el gap de F1.

---

## G. Costos / límites

**G1. Ningún límite de longitud/tokens sobre el mensaje del cliente en toda la cadena.** (P2)
Verificado extremo a extremo sin ningún tope: `consumers.py` (sin `max_length`) →
`ChatMessage.message` (`TextField` sin límite) → `ChatRequest.message` (Pydantic sin
`max_length`) → entra crudo a las 2 llamadas al LLM del turno. Solo el contexto RAG tiene tope
(`MAX_CONTEXT_CHARS=6000`); el mensaje real del usuario no. Inofensivo hoy con Ollama local
(costo marginal ~0); riesgo de costo real y directo si se migra a `openai`/`anthropic`
(ya soportado en `llm_factory.py`) sin cerrar esto antes. El rate-limit de 20 turnos/10min
(Fase 1) protege *frecuencia*, no *tamaño* de cada mensaje.
*Sugerencia:* `Field(max_length=...)` en `ChatRequest` y/o truncar en `consumers.py` antes de
llamar a `ask_ai()` (ej. 4000 caracteres).

**G2. Ninguna llamada al LLM tiene timeout explícito propio.** (P3)
`llm_factory.py` no pasa `timeout`/`request_timeout` a ningún provider. El único corte end-to-end
es el timeout de Django esperando `/chat` completo (300s) — dentro de `ai_engine` (un solo
proceso uvicorn sin `--workers`) una llamada colgada al proveedor no tiene corte propio.
*Sugerencia:* `timeout=` explícito en `get_llm()` (ej. 60-90s).

---

## H. Prompt Manager / Policies — confirmado que NO existe como componente

Prompts de sistema hardcodeados como f-strings inline en 3 lugares (`action_graph.py` x2,
`chains.py`/`chains_frontend.py` para el motor de generación de código). Sin campo de versión
sobre los prompts (a diferencia de `ToolMetadata.version`/`Capability.version`, que sí
versionan). `chains.py`/`chains_frontend.py` además duplican sus reglas críticas como texto libre
en el prompt Y como reglas AST/regex en `guardrails.py`/`guardrails_frontend.py` — riesgo de
divergencia si se agrega una regla en un lado y se olvida el otro. Reportado como ausencia real
(el brief pedía verificarlo explícitamente), no como urgencia a corregir.

---

## I. Observabilidad real vs aspiracional

**I1 (info, no bug).** `observability.py` es honesto sobre su propio alcance: el docstring dice
explícitamente "Prometheus/Grafana/OpenTelemetry preparado pero NO instalado", y el código
coincide — `TurnMetrics.emit()` solo escribe a un logger estándar, sin exporter real. No se
calcula costo en dólares en ningún punto (solo tokens crudos) — irrelevante con Ollama, relevante
si se activa un proveedor de pago.

---

## Lo que SÍ está bien (no re-litigar en fases siguientes)

- Contrato `support`↔`ai_engine` verificado campo por campo — sin mismatch real (A1, A2).
- Aislamiento de memoria conversacional por sala/usuario es real, no solo logueado (B1).
- Ownership scoping vive en Django, nunca confiado al LLM — se sostiene incluso bajo F1 (F2).
- El loader de Agent Profiles y el Tool Registry fallan el arranque (no silenciosamente en
  runtime) si un YAML referencia algo inexistente — invariante fuerte bien implementada.
- `observability.py` documenta su propio alcance limitado con precisión (I1).

---

## B2 — Resuelto (2026-08-01, mismo día)

**Bloqueador real encontrado al implementar** (no visible desde solo lectura de código): el
paquete oficial `langgraph-checkpoint-redis` requiere el módulo **RediSearch** — confirmado en
vivo contra el Redis real del proyecto (`redis:7.2-alpine`, la misma instancia de
Channels/Celery/Cache): `redis.exceptions.ResponseError: unknown command 'FT._LIST'`. La
alternativa oficial `langgraph-checkpoint-postgres` tampoco resuelve limpio: exige degradar
`langgraph-checkpoint` a `<2.0.0`, lo que choca con el requisito propio de `langgraph==0.2.76`
(`langgraph-checkpoint<3.0.0,>=2.0.10`) ya fijado en `requirements.txt`. Subir `langgraph` en sí
es un cambio de mayor riesgo (API de grafo distinta entre versiones), fuera de alcance de
"agregar persistencia".

**Solución implementada:** `ai_engine/redis_checkpointer.py` — checkpointer propio (~250 líneas)
que implementa la interfaz `BaseCheckpointSaver` de `langgraph-checkpoint` 2.1.2 (sync + async
completos: `get_tuple`/`aget_tuple`, `list`/`alist`, `put`/`aput`, `put_writes`/`aput_writes`,
`delete_thread`/`adelete_thread`, `get_next_version`) sobre el Redis YA existente del proyecto —
DB 2, separada de Channels (0) y Cache (1) de Django (`CHECKPOINTER_REDIS_URL`, default
`redis://redis:6379/2`). Sin índices de búsqueda ni deduplicación de `channel_values` entre
checkpoints (esa optimización de los checkpointers oficiales no compensa la complejidad para
conversaciones de decenas de turnos, no miles) — cada checkpoint completo con TTL de 7 días
(misma convención de "vida de sesión" que `REFRESH_TOKEN_LIFETIME` de Django), así que
conversaciones abandonadas expiran solas.

**Verificado end-to-end contra el motor real (no mockeado), incluyendo el escenario exacto que
motivó el hallazgo:**
1. `POST /chat` real → respuesta 200, checkpoints reales confirmados en Redis (`redis-cli KEYS`).
2. Segundo turno en la misma conversación → el motor recordó el dato del primer turno (memoria
   funcionando).
3. **`docker restart` del contenedor `sintel_ai`** (simula un crash/redeploy real) → tercer turno
   en la MISMA conversación → **el motor seguía recordando el dato**, confirmando que la memoria
   ya sobrevive un reinicio (el problema exacto que B2 documentaba).
4. `py_compile` limpio en los 3 archivos tocados; build de Docker sin conflictos de dependencias
   (`redis>=5.0.0,<7.0.0` plano, sin el paquete oficial `langgraph-checkpoint-redis`).

`sintel_ai` no está en `docker-compose.prod.yml` (excluido a propósito) — este fix vive solo en
desarrollo, sin despliegue a producción pendiente.

## Matriz de prioridad (P0-P4)

| # | Hallazgo | Severidad | Riesgo de regresión al corregir |
|---|----------|-----------|----------------------------------|
| B2 | Memoria de conversación solo en RAM, sin persistencia | **P2** | **Resuelto** — checkpointer propio sobre Redis existente, verificado con reinicio real de contenedor |
| G1 | Sin límite de longitud en el mensaje del cliente | **P2** | **Resuelto** — `Field(max_length=4000)` en `ChatRequest`, verificado con `HTTP 422` real |
| A3 | Acoplamiento latente confirmación-rechazo ↔ "ticket abierto" | P3 | Pendiente (latente, no reproducible hoy) |
| C1 | Colisión de intent `promos` entre 2 Agent Profiles | P3 | **Resuelto** — quitado de `marketing_agent.yaml` + validación de arranque que falla ante cualquier colisión futura |
| D1 | `except Exception` silencioso en `_pending_interrupt` | P3 | **Resuelto** — logging agregado |
| F1 | `/tools/debug` sin Policy Layer completa (no explotable hoy) | P3 | **Resuelto** — chequeo de `IsAdminUser` agregado + check de CI que falla si `AI_TOOLS_DEBUG` aparece en compose de prod |
| G2 | Sin timeout propio en llamadas al LLM | P3 | **Resuelto** — 90s explícito en los 3 providers |
| E1 | Conteo de Tools/Capabilities desactualizado en doc | P4 | **Resuelto** — actualizado a 30/30 |

**7 de 8 hallazgos cerrados** (2026-08-01, mismo día). Solo A3 queda pendiente — es un
acoplamiento latente y hoy no reproducible (`abrir_ticket_soporte` es la única write-tool sin
`requires_confirmation`), sin urgencia real hasta que esa configuración cambie.

**Verificado end-to-end contra el motor real tras todos los fixes:** mensaje normal de vuelta a
`/chat` con `intent="promos"` enrutando correctamente a `SalesAgent` (confirma C1 en un request
real, no solo en aislamiento), respuesta 200 completa con tool call ejecutado
(`ActivePromosTool`). `py_compile` limpio en los 5 archivos Python tocados
(`redis_checkpointer.py`, `action_graph.py`, `agents/__init__.py`, `gateway/router.py`,
`llm_factory.py`, `main.py`). Build de Docker limpio, sin conflictos de dependencias nuevos.

## Resumen ejecutivo

El AI Engine tiene una arquitectura de negocio sólida (Action Graph, Capability/Tool Registry,
Policy Layer con confirmación humana, Agent Profiles) con buenas invariantes de arranque, y el
contrato con `support` está genuinamente alineado en los tres puntos donde se pidió verificación
exacta — sin mismatch real. El hallazgo más importante es de **resiliencia, no correctitud**: la
memoria de conversación vive solo en RAM del proceso (B2), lo que bloquea escalar `sintel_ai` a
más de una réplica y pierde confirmaciones pendientes en cada reinicio. El segundo hallazgo real
de impacto es la ausencia total de límite de tamaño sobre el mensaje del cliente en toda la
cadena (G1) — inofensivo hoy con Ollama local, riesgo de costo directo si se migra a un proveedor
de pago. Se encontró una colisión real de configuración entre dos Agent Profiles (C1) y un
acoplamiento frágil-pero-hoy-inofensivo en el flujo de confirmación (A3). El endpoint de debug
tiene una asimetría de defensa-en-profundidad pero no es explotable hoy (F1: Django es la
autoridad final). Ninguno de estos hallazgos es crítico mientras `AI_SUPPORT_CHAT_ENABLED` siga
apagado en producción y `sintel_ai` no esté desplegado allí — pero B2 y G1 deberían resolverse
antes de activar el chat con IA ampliamente, en línea con la Fase 10 (Escalabilidad) del roadmap
original.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1 — Auditoría global de `support` | **Hecha, 11/11 hallazgos cerrados** |
| 2 — Sincronización con AI Engine | **Hecha, 7/8 hallazgos cerrados** (A3 pendiente, latente y no urgente) |
| 3-16 | Pendientes |
