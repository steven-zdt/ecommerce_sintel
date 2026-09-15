# SUPPORT AI CERTIFICATION

> **[Actualizado 2026-09-14 — migracion de runtime a Google ADK, ver
> `AUDITORIA/ADK_CUTOVER_PLAN.md`]** El chat de soporte real dejo de correr en
> `ai_engine` (puerto 8100, `action_graph.py`/LangGraph) y ahora corre enteramente en
> `ai_engine_adk/` (puerto 8101, Google ADK) -- mismo dia, migracion completa
> ADK-00 a ADK-13, cutover verificado en staging Y produccion real
> (`sintel.net.co`, `AI_SUPPORT_CHAT_ENABLED=True`). `e2e_http/
> e2e_support_ai_chat_test.ps1` (citado abajo como evidencia del Bloque 10/Load
> Test) quedo apuntando al puerto/proceso viejo (404 real) hasta hoy -- corregido
> para apuntar a `ai_engine_adk` (mismo flujo, `metrics` ahora opcional: ese campo
> sigue `None` en el runtime nuevo, gap documentado, no bloqueante). La
> certificacion de abajo (APTA) sigue siendo valida -- el comportamiento
> certificado no cambio, solo el proceso/puerto que lo sirve. Evidencia E2E
> adicional del runtime nuevo, corrida contra infraestructura real en ambos
> entornos el mismo dia: `ai_engine_adk/tests/test_reasoning_separation.py` (11
> tests, incluye el fix del leak de razonamiento de Qwen3.5 -- ver
> `AUDITORIA/REASONING_LEAK_FIX_REPORT.md`), `test_rate_limit.py`/
> `test_permissions.py` (Policy Layer portada), y
> `test_prompt_injection_resistance.py` (4 tests, cierra el hueco de pruebas
> adversariales que este documento senalaba como pendiente para el runtime
> nuevo). Ver `AUDITORIA/ADK_CUTOVER_PLAN.md` seccion 6 para el detalle
> completo.
>
> **[Actualizado 2026-08-17, mas tarde — CORREGIDO la misma noche]** Migracion del
> proveedor LLM: **Ollama -> LM Studio Server** (Windows HOST, puerto 1234, API
> OpenAI-compatible). Modelo real: `qwen/qwen3.5-9b` (confirmado via `GET /v1/models`,
> no inventado — es un modelo "razonador" que emite `reasoning_content` antes de la
> respuesta final). Embeddings tambien migrados (`text-embedding-nomic-embed-text-v1.5`,
> 768-dim, coleccion ChromaDB vieja de 1024-dim limpiada). Conectividad
> `Docker -> host.docker.internal:1234 -> LM Studio` verificada (127.0.0.1, sin
> exposicion LAN/Internet).
>
> **Hallazgo real y no resuelto todavia**: la primera pasada de esta certificacion
> reporto un E2E y una matriz de concurrencia "exitosos" que en realidad corrieron
> contra **Ollama**, no LM Studio — una configuracion dinamica preexistente en
> `ai_provider` (de otra sesion) tenia precedencia sobre `LOCAL_MODEL_CHAIN` y el
> canal `support_chat` seguia apuntando a Ollama. Corregido (ver
> `LM_STUDIO_MIGRATION_2026-08-17.md` seccion 10). **Con LM Studio genuino, un turno
> real tarda ~100-289s y termina en fallback** (`node_generate_response` excede
> `LLM_TIMEOUT_SECONDS=90` de forma consistente, confirmado con traceback real) — el
> mecanismo de fallback funciona bien, pero la latencia es inaceptable para un chat en
> vivo. **NO se corrio una matriz de concurrencia real contra LM Studio** (cada turno
> ya tarda demasiado individualmente). Esto es un hallazgo de viabilidad de
> modelo/hardware, no un bug de configuracion — pendiente de decision (modelo mas
> liviano, mejor hardware, o timeouts mas altos). Detalle completo en
> `ai_engine/.AGENT/LM_STUDIO_MIGRATION_2026-08-17.md`.
>
> Fase 35 del `PLAN_MAESTRO_SINTEL_AI_SUPPORT`. Checklist de certificación del Support
> Agent, consolidado a partir de la auditoría completa hecha el 2026-08-08 (11 Bloques
> del plan original de separación Support/Engineering + las fases genuinamente nuevas
> del plan maestro: Knowledge Governance, Cost Control, Error Handling, matrices de
> prueba). Cada ítem enlaza a la evidencia real (código, test, o hallazgo), no es una
> afirmación sin verificar.
>
> **[Actualizado 2026-08-08, misma tarde]** Los 6 huecos reales encontrados en la
> primera pasada de esta certificación fueron corregidos e implementados, con tests
> nuevos (todos runtime-verificados: `docker compose exec sintel_ai pytest tests -v`
> -> 117 passed, 16 skipped) y verificación en vivo contra el motor real. Ver
> "Historial de correcciones" al final.
>
> **[Actualizado 2026-08-17]** Auditoria E2E completa del flujo Customer -> Support
> Chat -> ai_bridge -> AI Engine (prompt maestro de cierre E2E). No se re-certifico
> todo desde cero (esta certificacion + `CERTIFICACION_E2E_CHAT_IA_2026-08-13.md` ya
> cubrian casi todo con evidencia real) -- se cerraron especificamente los gaps
> reales que ambas certificaciones habian dejado abiertos. Ver "Historial de
> correcciones (2026-08-17)" al final.
>
> **Estado de esta certificación: APTA, con 1 limitacion de escala conocida** (no
> es un hueco de seguridad/correctitud — ver seccion final).

## Checklist

- [x] **Gateway** — `gateway/router.py`, `/api/v1/ai/*`, nunca expuesto a Internet (solo
      red Docker interna). Ver `AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md` seccion 1.
- [x] **JWT** — `auth.py`, PyJWT HS256, validado en cada request. Ver
      `SUPPORT_AGENT_SPEC.md` seccion 3. Casos expirado/invalido/malformado/refresh
      cubiertos por test (`test_auth_tokens.py`, 6 tests).
- [x] **Identity** — siempre resuelta server-side desde el JWT, nunca confiada del
      mensaje del usuario (Regla 12 del plan maestro). Ver seccion 3 y 9.
- [x] **Customer Context** — `AiCustomerContextView`, cache Redis 5 min, solo para 4
      intents que lo necesitan. Ver seccion 5.
- [x] **Intent Detection** — 19 intents reales fijados por test
      (`ai_engine/tests/test_intent_detection.py`). Ver seccion 4.
- [x] **Agent Routing** — 9 Agent Profiles + escalamiento agente-a-agente, con tests.
      Ver `AI_SUPPORT_SCOPE.md` seccion 1 y `test_agent_escalation.py`.
- [x] **RAG** — `retrieve_knowledge_for_chat` filtra por `language=="markdown"` Y
      `visibility=="public"`. Ver seccion 6.
- [x] **Knowledge Governance** — **CERRADO 2026-08-08**: `loaders.py` agrega
      `updated_at` (mtime) y `visibility` a cada documento; `retrieve_knowledge_for_chat`
      solo devuelve `visibility=="public"`; cada consulta loguea la fuente exacta usada
      (`sources=[...]` en el log de `retrievers`). Hallazgo real que motivo el fix:
      una pregunta de cliente sobre "horario de atencion" recupero un fragmento de
      documentacion tecnica interna (agendamiento de servicios) y el LLM fabrico una
      respuesta de todos modos. Verificado en runtime real post-fix: la misma pregunta
      ahora devuelve `0 chunks (solo markdown+public)` y el LLM responde honestamente
      "no tengo esa informacion especifica ahora mismo" en vez de inventar. Ver
      seccion 6bis.
- [x] **Tools** — Tool Registry defensivo (rechaza args desconocidos, nunca deja escapar
      excepciones), y ahora tambien aplica `ToolMetadata.timeout_ms` de verdad (ver
      Error Handling abajo). Ver seccion 7.
- [x] **Capabilities** — Capability Registry versionado, LLM nunca ve una Tool directa.
      Ver seccion 7.
- [x] **Policy** — `node_evaluate_policy` (deny/confirm/allow real), con tests para las
      **30 capabilities activas** (`test_tool_policy_matrix.py`, parametrizado, no solo
      una muestra). Ver seccion 8.
- [x] **Confirmation** — `interrupt()` real de LangGraph, nunca ejecuta ante respuesta
      ambigua. Ver seccion 8 y 8bis.
- [x] **Conversation** — `thread_id={user_id}:{conversation_id}`, aislamiento probado.
      Ver seccion 9.
- [x] **Redis** — `RedisCheckpointSaver`, TTL 7 dias. Ver seccion 9.
- [x] **Memory** — conversación (Redis) + cliente (Customer Context) separados sin
      mezclarse. Ver seccion 9 y Fase 18 del plan maestro.
- [x] **Human Handoff** — 2 capas (agente-a-agente + `ChatRoom.ai_paused`), con tests.
      Ver seccion 10.
- [x] **Web Chat** — funcional end-to-end, verificado con pruebas UI reales en
      navegador (2026-08-08).
- [x] **WhatsApp** — ya en producción, reutiliza el mismo `ask_ai()`. **Gap conocido, no
      cerrado en esta sesion**: el handoff no es cross-canal (ver seccion 12) — postergado
      deliberadamente por el equipo, no es parte de los 6 huecos de esta certificacion.
- [x] **Model Fallback** — `llm_factory.py` con `.with_fallbacks()` nativo sobre
      `LOCAL_MODEL_CHAIN`. Ver seccion 11bis.
- [x] **Rate Limit** — **CERRADO 2026-08-08**: agregado `cost_control.py`, limite diario
      de turnos por usuario respaldado en Redis (distribuido de verdad, sobrevive
      restarts) — capa adicional sobre el rate limit por-Tool existente (que sigue
      cubriendo solo escrituras). Verificado con test real contra Redis
      (`test_cost_control.py`, 3 tests). El rate limit por-Tool sigue siendo en memoria
      (limitacion conocida, ver "Limitaciones de escala" abajo).
- [x] **Audit** — `SecurityEvent.AI_ACTION_EXECUTED` via `log_ai_action()`, una sola
      implementación centralizada. Ver seccion 8.
- [x] **Observability** — `TurnMetrics` cubre casi todo el checklist de la Fase 24
      (faltan `request_id` explícito y qué modelo respondió en fallback, ambos
      cosméticos, no cerrados en esta sesion). Ver seccion 13bis.
- [x] **Security** — checklist item-por-item verificado (JWT/permisos/rate-limit/audit/
      PII) + **pruebas adversariales nuevas** (`test_security_adversarial.py`):
      tool injection fuera del scope del agente, capability inventada/inexistente, y
      contenido adversarial del mensaje sin efecto sobre la decision de Policy — las 3
      demuestran que la seguridad es estructural (no depende de que el LLM se porte
      bien), que es la defensa real contra prompt injection.
- [x] **Customer Isolation** — `thread_id` namespacing a prueba de colisión, verificado.
      Ver seccion 9.
- [x] **Error Handling** — **CERRADO 2026-08-08**: `tools/registry.py::invoke()` ahora
      envuelve cada ejecucion en `asyncio.wait_for(..., timeout=metadata.timeout_ms)`,
      devuelve `{"error":..., "status_code":504}` si se excede. Verificado con test
      (`test_tool_timeout.py`, Tool de prueba que duerme mas que su timeout declarado).
      Resto del checklist (LLM/RAG/Redis/Django caídos, tool failure, confirmación
      ambigua) ya estaba cubierto. Ver seccion 8bis.
- [x] **E2E** — cubierto para los recorridos principales (`order_status`, `knowledge`,
      handoff) + token expirado/invalido (unit, `test_auth_tokens.py`) + tool/prompt
      injection (unit, `test_security_adversarial.py`). **Sigue sin cubrir**:
      reactivación de IA post-handoff humano (no priorizado en esta sesion). Ver
      seccion 12bis.
- [x] **Load Test** — **CERRADO 2026-08-08**: arreglado `e2e_support_ai_chat_test.ps1`
      Paso 4 (`Start-Job` en vez de `ForEach-Object -Parallel`, incompatible con
      PowerShell 5.1 de este entorno). Corrido contra el motor real: **5/5 chats
      concurrentes exitosos, latencia min=9556ms avg=21140ms max=32585ms**. Primer dato
      real de carga de esta plataforma — ver "Limitaciones de escala" abajo, la
      degradacion bajo concurrencia es real y esperable con Ollama local, no un bug.

## Historial de correcciones (2026-08-08, misma sesion que encontro los huecos)

| # | Hueco | Fix | Archivo(s) | Test |
|---|---|---|---|---|
| 1 | Knowledge Governance | `visibility`/`updated_at` por doc + filtro real + logging de fuente + marcador explicito "NINGUNO" cuando no hay conocimiento | `loaders.py`, `retrievers.py`, `action_graph.py` | `test_retrieve_knowledge_for_chat.py` (+2 tests) |
| 2 | Tool timeout | `asyncio.wait_for` real sobre `ToolMetadata.timeout_ms` | `tools/registry.py` | `test_tool_timeout.py` (nuevo) |
| 3 | Rate Limit agregado | Limite diario por usuario en Redis (`cost_control.py`), enganchado en `run_action_chat` | `cost_control.py` (nuevo), `action_graph.py` | `test_cost_control.py` (nuevo) |
| 4 | Pruebas adversariales | Tool injection / capability inventada / mensaje adversarial vs Policy | `tests/test_security_adversarial.py` (nuevo) | 3 tests |
| 4b | Token expirado/invalido | Sin fix de codigo (ya estaba bien) — solo faltaba el test | `tests/test_auth_tokens.py` (nuevo) | 6 tests |
| 5 | Matriz por Tool | Parametrizado sobre las 30 capabilities activas reales, no una muestra | `tests/test_tool_policy_matrix.py` (nuevo) | 60 casos (30 x 2 variantes) |
| 6 | Load test real | `Start-Job` en vez de `ForEach-Object -Parallel` (PS7-only) | `e2e_http/e2e_support_ai_chat_test.ps1` | Corrido en vivo, ver resultado arriba |

Todo verificado con `docker compose build sintel_ai && docker compose exec sintel_ai
pytest tests -v` (117 passed, 16 skipped) + una llamada real a `/chat` confirmando el
comportamiento honesto post-fix de Knowledge Governance + el load test real de arriba.

## Limitaciones de escala conocidas (no son huecos de seguridad/correctitud)

1. **Latencia bajo concurrencia real es alta** con la configuracion actual (Ollama local,
   `llama3.1:8b`): 5 chats simultaneos promediaron 21s, con un maximo de 32.5s. No es un
   bug — es el costo real de inferencia local sin GPU dedicada ni motor cloud. Si el
   volumen de soporte crece, esto es lo primero a revisar (motor cloud como fallback via
   `LOCAL_MODEL_CHAIN`, o mas capacidad de computo para Ollama). **Distinto de la
   concurrencia estructural** (ver Historial 2026-08-17, item 5): esta limitacion es
   sobre cuanto tarda CADA turno bajo carga (Ollama), no sobre si turnos concurrentes
   se bloquean entre si (eso ya no ocurre).

## Historial de correcciones (2026-08-17, auditoria E2E de cierre)

Gaps que quedaron abiertos en `SUPPORT_AI_CERTIFICATION.md` (2026-08-08) y
`CERTIFICACION_E2E_CHAT_IA_2026-08-13.md`, cerrados con codigo + test real en esta
sesion. `sintel_ai` reconstruido (`docker compose build sintel_ai`) y verificado
runtime: `docker compose exec sintel_ai pytest tests -v` -> **134 passed, 16
skipped** (subio de 117 el 2026-08-08 por los tests nuevos de esta sesion).
`docker compose exec django pytest support/tests.py notifications/tests.py -v` ->
**67 passed** (subio de 60 antes de esta sesion).

| # | Gap | Fix | Archivo(s) | Test |
|---|---|---|---|---|
| 1 | WhatsApp no respetaba `ai_paused`/`is_ai_mode_active` de la sala — un cliente escalado a humano por el chat web seguia recibiendo auto-respuestas de la IA si escribia por WhatsApp | `process_whatsapp_inbound_task` ahora chequea `is_ai_mode_active(room)` e `is_ai_rate_limited(room)` antes de llamar a `ask_ai()`, mismo criterio que `SupportChatConsumer` | `notifications/tasks.py` | `notifications/tests.py::WhatsAppInboundHandoffGateTestCase` (4 tests nuevos) |
| 2 | Entrega real a `support_admins` con una segunda sesion admin conectada en simultaneo no estaba verificada (Paso 18 "PARCIAL" de la certificacion 2026-08-13) | Sin cambio de codigo — solo faltaba el test | `support/consumers.py` (sin cambios) | `support/tests.py::test_admin_ve_respuesta_de_ia_en_vivo` (nuevo) |
| 3 | Reactivacion de la IA tras cerrar un handoff humano nunca se habia probado | Sin cambio de codigo — se confirmo que el mecanismo real es una sala NUEVA (`close_room` + `get_or_create_room` en la siguiente conexion), no un "unpause" en la misma sala (ese mecanismo no existe en el codigo) | — | `support/tests.py::test_ia_se_reactiva_en_sala_nueva_tras_cerrar_el_ticket` (nuevo) |
| 4 | Rate limit por-Tool (`_RATE_HITS`) seguia en memoria del proceso — impreciso si `sintel_ai` corriera en mas de una replica | Migrado a Redis (mismo `CHECKPOINTER_REDIS_URL` que `cost_control.py`), `INCR` atomico, fail-open ante Redis caido | `ai_engine/action_graph.py` (`_rate_limit_exceeded` ahora async) | `ai_engine/tests/test_policy_layer.py`, `test_tool_policy_matrix.py` (30 capabilities), nuevo fixture autouse en `conftest.py` que flushea `ai:tool_rate:*` entre tests |
| 5 | **B2 — bloqueador explicito del prompt maestro**: `ask_ai()` (requests.post sincrono, timeout 300s) corria envuelto en `@database_sync_to_async` dentro de `SupportChatConsumer`, ocupando un worker del thread pool COMPARTIDO de Channels durante toda la llamada — un turno de IA lento podia afectar operaciones de DB de otras conexiones WS concurrentes | Nueva `ask_ai_async()` (`httpx.AsyncClient`, espera nativa del event loop, sin ocupar threads del pool); `SupportChatConsumer._ask_ai` ya no usa `database_sync_to_async` | `support/services/ai_bridge.py`, `support/consumers.py` | `support/tests.py::test_ia_lenta_no_serializa_via_thread_pool_compartido` (nuevo — 12 turnos de IA de 0.5s concurrentes terminan en ~0.5s, no ~6s) |

**`AI_SUPPORT_CHAT_ENABLED` re-confirmado en runtime**: `True` en este entorno de
desarrollo (`ecommerce/settings/base.py`, `.env`) — consistente con
`AI_PROVIDER_RUNTIME_AUDIT.md`. Produccion sigue sin correr `sintel_ai` en absoluto
(`docker-compose.prod.yml` lo excluye deliberadamente), asi que el flag no aplica
hoy en produccion real, pero el gap B2 que bloqueaba activarlo ampliamente en
desarrollo/staging ya esta cerrado.
