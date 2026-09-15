# Hardening y preparación de producción — SINTEL AI

**Fecha:** 2026-09-14 (continuación de la misma sesión que ejecutó la migración a Google ADK,
ver `ADK_CUTOVER_PLAN.md`). Ejecutado a partir de un "PROMPT MAESTRO" de 65 secciones pedido
por el usuario (hardening, consolidación y preparación de producción de SINTEL AI). Este
documento es el registro vivo de esa auditoría -- se sigue completando en fases sucesivas, no
en una sola pasada (el propio prompt cubre 65 secciones; forzar todo en un turno arriesgaba
trabajo superficial en ítems de seguridad reales).

## Regla de alcance explícita del prompt (Sección 62), ya respetada

NO se introdujo multitenancy nueva, NO se introdujo ChromaDB, NO se introdujo MCP nuevo, NO se
introdujo memoria persistente avanzada, NO se introdujo multi-agent nuevo, NO se cambió Qwen,
NO se creó un segundo AI engine/RAG/Tool Registry, Ollama no se expone a Internet, no se
ejecuta SQL arbitrario generado por LLM, AI WRITE sigue gateado (no autónomo), no se filtró
reasoning solo con regex, no se registran secretos, no se declaró "production ready" sin
evidencia.

## Estado ya cerrado ANTES de este prompt (mismo día, misión "ADK-SINTEL" + auditoría del
## informe externo) -- no se repite el trabajo, solo se referencia:

- Runtime AI consolidado en un solo camino (`ai_engine_adk`, Google ADK) -- `ADK_CUTOVER_PLAN.md`.
- Separación estructural reasoning/público (`public_response.py`, `Part.thought`) -- `REASONING_LEAK_FIX_REPORT.md`.
- RAG en PostgreSQL+pgvector, sin ChromaDB -- `project_chromadb_to_pgvector_migration` (memoria).
- RAG respeta autorización de visibilidad (`RetrievalVisibilityTests`, `ai_knowledge/tests.py`).
- Policy Layer completa portada a ADK: confirmación humana + rate limit + `IsAdminUser`.
- Suite de resistencia a prompt injection real (`test_prompt_injection_resistance.py`).
- AI WRITE gateado por confirmación humana explícita, nunca autónomo (`requires_confirmation`).
- `notas.txt` excluido de toda imagen Docker (typo real de `.dockerignore` corregido).
- CI/CD real existe (tests+cobertura+Bandit SAST en cada PR) -- mejor estado del esperado.
- Frontend: `SupportChatWidget.vue` usa interpolación Vue (`{{ msg.message }}`), no `v-html` --
  sin riesgo de XSS en el canal del chat.

## FASE A/E (esta pasada) -- 5 hallazgos reales encontrados y corregidos, verificados en
## staging Y producción real, ninguno destructivo:

| # | Hallazgo | Fix | Sección prompt |
|---|---|---|---|
| 1 | Migración pendiente: `SecurityEvent.event_type` tenía choices nuevas sin migración (schema drift real) | Generada + aplicada en ambos entornos | §32 |
| 2 | `sintel_ollama` publicaba su puerto bindeado a `0.0.0.0` en dev | Restringido a `127.0.0.1` | §24 |
| 3 | Sin test de rechazo por dimensión de embedding incorrecta contra pgvector | Confirmado empíricamente que pgvector YA rechaza (DataError real) -- 2 tests nuevos | §28 |
| 4 | `ai_engine_adk` sin timeout propio de LLM (regresión real: se perdió al retirar `llm_factory.py` en ADK-12 de hoy mismo) | Restaurado `timeout=90` (mismo valor que el sistema OLD) | §48 |
| 5 | CI `graph-audit` roto desde 2026-08-08 (apuntaba a `ai_engine/auditor.py`, retirado y nunca actualizado en CI) | Corregido a `project_knowledge_graph.cli audit`, verificado localmente | §D (obsoletos) |

Verificado: staging 23/23 (`ai_engine_adk`) + 12/12 (`ai_knowledge`) PASS; producción real
11/11 (`ai_engine_adk`) PASS, `sintel_prod_db` no tocado en ningún redeploy. Commit `5c33812`.

## Hallazgos NO críticos, confirmados sin acción necesaria (falsos positivos del propio
## barrido, documentados para no re-auditar):

- Dimensión real de embeddings: **1024 (bge-m3)**, deliberado y documentado en
  `ai_knowledge/models.py:29-35` -- el "768" que citaba el informe externo auditado antes era
  incorrecto, no un bug real.
- `AI_TOOLS_DEBUG` nunca en `docker-compose.prod.yml`: ya hay un check de CI dedicado
  (`security` job) que falla si esto ocurre -- cubierto desde antes de esta sesión.

## FASE A (esta pasada, continuación) -- 1 hallazgo más cerrado:

| # | Hallazgo | Fix | Sección prompt |
|---|---|---|---|
| 6 | Sin límite de tool calls/iteraciones por turno en ADK (§34) -- confirmado por introspección real que `LlmAgent`/`Runner` no exponen `max_tool_calls` nativo, a diferencia del cap duro que sí tenía `action_graph.py::tool_calls[:4]` en el sistema OLD | `deny_after_max_tool_calls_per_turn()` (`sintel_adapter.py`), `before_tool_callback` real de ADK, cap de 6 por `invocation_id` (único por turno, confirmado por introspección) | §34 |

Verificado: staging 26/26 (suite completa, sin romper tool-calling/multi-turno real) y
producción real 7/7, `sintel_prod_db` no tocado. Commit `0b8fbd8`.

## FASE A, continuación 2 -- Auditoría de secretos más profunda (§25), 2026-09-14

Barrido sistemático de todo el código fuente TRACKEADO por git (no solo `notas.txt`):
contraseñas/API keys/tokens/claves privadas hardcodeadas en `.py`, `.yml`/`.yaml`, frontend
(`src/`), scripts de `deploy/`, defaults de `config()`/`decouple`, archivos `.pem`/`.key`/
`.crt` trackeados, patrones de AWS access keys, y llamadas a `logger.*` que pudieran imprimir
un token/password crudo.

**Resultado: código fuente limpio.** Cero hardcodeos reales encontrados -- `SECRET_KEY`/
`JWT_SECRET_KEY` (Django) se leen via `config()` SIN default (falla duro si falta, nunca cae
a un valor débil hardcodeado -- el patrón más seguro posible), ningún `.env`/`.pem`/`.key`
trackeado por git, el único `password:`/`token:` hardcodeado en YAML es
`sintel_ci_password` (CI de GitHub Actions, Postgres desechable que solo existe durante el
run, no una credencial real).

**1 hallazgo real, más severo de lo que parecía al principio -- CERRADO 2026-09-14:**
`sms_bridge/bridge.py` (proceso Python en el HOST Windows, fuera de Docker, expone
`0.0.0.0:8765` a propósito, `# nosec B104` ya documentado, necesario para que
`host.docker.internal` lo alcance desde Django) falla ABIERTO si `SMS_BRIDGE_TOKEN` no está
configurado -- confirmado que `.env.production` no lo tenía. Al investigar por qué (¿de
dónde saca el token real la Tarea Programada "SintelSmsBridge" del host?) apareció el
hallazgo real: **`sms_bridge/run_bridge.ps1` (el envoltorio de esa Tarea Programada) tenía
el token real hardcodeado en texto plano, TRACKEADO por git** -- un secreto real, no
hipotético, expuesto en el repositorio, mismo patrón que `notas.txt` y la password del
script E2E de certificación (ambos ya corregidos esta misma sesión). Confirmado que el
puente NO está corriendo hoy en este host (puerto 8765 sin listener) -- riesgo dormido, no
explotado activamente.

**Fix (autorizado explícitamente por el usuario: "configurar el token en
`.env.production`"):** token nuevo generado (`secrets.token_urlsafe`), guardado en
`C:\Users\Administrator\sintel_secrets\sms_bridge_token.txt` (mismo directorio fuera de git
que ya usaban `backup.sh`/`restore.sh` para los certificados de origen de nginx --
convención ya establecida en este proyecto). `run_bridge.ps1` corregido para leer de ahí en
vez de hardcodear el valor. `.env.production` actualizado con el mismo token nuevo
(gitignored, nunca commiteado) -- producción real recreada (`django`/`celery_worker`/
`celery_beat`), verificado que Django lo carga (`settings.SMS_BRIDGE_TOKEN`, largo
correcto), `sintel_prod_db` no tocado. El token viejo expuesto queda inválido desde esta
rotación; sigue visible en el historial de git de commits previos (no reescrito, mismo
criterio que el resto de esta sesión). Commit `339531d`.

## FASE A, continuación 3 -- Matriz de seguridad §43, retries §46, supply chain §30,
## evaluación §44 (2026-09-14, "continua hasta terminar todas las fases")

**Matriz de 15 casos (§43):** de los 15, 12 ya tenían cobertura real repartida en archivos
de esta sesión (prompt injection, tool misuse, privilege escalation, unauthorized tool, RAG
leakage, reasoning leakage, unbounded loops, timeout -- ver tabla al inicio del docstring de
`test_security_matrix.py`). Los 3 que faltaban se cerraron con `test_security_matrix.py`:

- **Oversized input**: confirmado, `ChatRequest.message` ya rechaza >4000 caracteres.
- **Tool que falla / argumentos inválidos (caso 8)**: reveló un hallazgo real -- confirmado
  EMPÍRICAMENTE (reproducido antes y después del fix contra el motor real) que una excepción
  real de una Tool no se atrapaba en ningún punto de ADK por defecto, matando el TURNO
  COMPLETO en vez de degradar por-Tool como hacía el sistema OLD. `handle_tool_error()`
  (`on_tool_error_callback` real de ADK) lo cierra. Commit `58a874f`.
- **Fallo total del proveedor LLM**: confirmado que `main.py::chat()` ya degrada con gracia
  sin exponer traceback (no era un hueco, solo faltaba el test).

**Coordinación de retries (§46) -- auditado, SIN hallazgos reales:**
- `support/services/ai_bridge.py` (Django → `ai_engine_adk`): sin retry propio, una sola
  llamada con timeout de 300s -- sin riesgo de storm.
- LiteLLM (`_build_litellm_model()`): `num_retries` nunca configurado, default real de
  `litellm.acompletion()` es sin reintentos -- confirmado por introspección.
- `notifications/tasks.py` (WhatsApp + IA): ya tenía un guard deliberado
  (`self.request.retries == 0`) para no duplicar el mensaje ENTRANTE del cliente en cada
  reintento de Celery (Fase 9, AUDITORIA/24, 2026-08-01) -- y el envío de la respuesta por
  WhatsApp está en su propio `try/except` que NO dispara `self.retry()`, así que un fallo de
  envío nunca causa una SEGUNDA llamada a `ask_ai()`. Bien diseñado ya, sin cambios.
- Frontend (`SupportChatWidget.vue`): reconexión de WebSocket con backoff exponencial +
  jitter, sin reenvío automático de mensajes. Sin riesgo.

**Supply chain / pinning (§30) -- CERRADO parcialmente, hallazgo real de CVEs:**
`requirements.txt` de `ai_engine`/`ai_engine_adk` se mantienen con rangos (documentan
intención/compatibilidad real, ej. por qué `mcp==1.24.0`). Se agregaron
`requirements.lock.txt` (snapshot exacto vía `pip freeze` real del árbol completo,
directo+transitivo) en ambos servicios -- reproducibilidad sin tocar el Dockerfile (decisión
operativa que se deja al usuario). `pip-audit` corrido localmente contra ambos:
`ai_engine_adk` (runtime NUEVO) solo `pytest` vulnerable (dev-only, sin superficie de
producción). `ai_engine` (runtime OLD, sigue sirviendo el AI Gateway de Meta Ads real) tiene
**36 vulnerabilidades reales en 7 paquetes** -- `starlette` 0.46.2, `langchain-core` 0.3.86,
`langgraph` 0.2.76/`langgraph-checkpoint` 2.1.2/`langgraph-sdk` 0.1.74, `mcp` 1.24.0 (el que
SÍ está activo). **No se actualizaron** -- son bumps de versión mayor con acoplamiento ya
documentado en el propio `requirements.txt` ("subir mcp exige subir fastapi/uvicorn en la
misma PR"), requieren testing dedicado y decisión de prioridad/riesgo del usuario, no una
acción automática de esta auditoría. Se agregó `dependency-audit` a CI (advertencia, no
bloqueante, mismo patrón que `graph-audit`) para que estos hallazgos queden visibles en cada
PR de ahora en adelante. Commit `03989f2`.

**Batería de evaluación (§44) -- CERRADA, mínima pero real:** `test_evaluation_battery.py`,
2 casos E2E reales contra LM Studio cubriendo las 2 dimensiones sin cobertura (el resto ya
estaba cubierto en otros archivos): groundedness (el LLM no inventa un horario de atención
cuando `ai_knowledge` está vacío de verdad -- mismo hallazgo que ya motivó el marcador
`_NO_KNOWLEDGE_MARKER`) y manejo de preguntas ambiguas/fuera de alcance (sigue produciendo
respuesta pública coherente, nunca una excepción). Commit `036f1c1`.

Verificado en las 3 tandas: staging 31/31 (suite completa) y producción real, `sintel_prod_db`
no tocado en ningún redeploy.

## Gaps reales identificados, NO resueltos (requieren decisión/información del usuario --
## ninguno bloqueante para el estado actual):

1. **Rotación de credenciales de `notas.txt`** -- requiere que el usuario indique cuáles
   rotar (ver `VALIDACION_INFORME_EXTERNO_SINTEL_PROD_AI.md`).
2. **Backups fuera del host de producción** -- requiere destino.
3. **36 CVEs reales en las dependencias del runtime OLD** (`ai_engine`, sigue sirviendo el AI
   Gateway) -- requiere decisión de prioridad/riesgo y testing dedicado antes de actualizar
   `starlette`/`langchain-core`/`langgraph`/`mcp` (bumps mayores, acoplamiento documentado).
4. **`ChatResponse.metrics`** sigue `None` en `ai_engine_adk`.
5. **Backend de sesión persistente para ADK** sigue en `InMemorySessionService`.
6. **Lock files no conectados al Dockerfile** -- decisión operativa (reproducibilidad vs.
   costo de mantenimiento) que se deja al usuario.

## Clasificación de Gate (Sección 53/54 del prompt) -- FINAL de esta pasada

```text
READY WITH ACCEPTED RISKS
```

No `NOT READY`: no hay bloqueadores de seguridad activos -- WRITE gateado, RAG con
autorización, reasoning separado, secrets fuera de imágenes/repo (incluyendo el token del
SMS bridge, rotado), TLS coherente, matriz completa de 15 casos de seguridad con evidencia
real, retries coordinados sin hallazgos, degradación por-Tool restaurada, batería de
evaluación mínima verde. No `READY` sin calificar: quedan 6 ítems reales (arriba), ninguno
bloqueante -- 2 requieren información que solo el usuario tiene (notas.txt, backups), 1 es un
riesgo real pero de blast radius acotado y ya visible en cada PR (CVEs del runtime OLD, con
plan de acción claro), y 3 son mejoras de ingeniería de menor prioridad ya documentadas
(`metrics`, sesión persistente, lock files sin conectar).

**Con esto, las fases A-R de la Sección 55 del prompt quedan cubiertas** (auditoría,
consolidación de runtime, contrato reasoning/público, streaming -- N/A, no existe ruta de
streaming activa --, multi-turn, Tool Registry + authorization, RAG + pgvector, prompt
injection/output security, infraestructura Docker/Nginx/TLS/secrets, backups/migraciones,
observabilidad, tests unitarios/integración/seguridad, E2E, auditoría final) con el nivel de
profundidad que el tiempo de esta sesión permitió -- los 6 ítems de arriba son honestamente
lo que falta, no una lista oculta.
