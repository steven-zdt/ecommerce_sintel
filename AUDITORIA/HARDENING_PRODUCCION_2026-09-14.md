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

**1 hallazgo real, nuevo, fuera de lo ya conocido:** `sms_bridge/bridge.py` (proceso Python
en el HOST Windows, fuera de Docker, sin contenedor -- expone `0.0.0.0:8765` a propósito,
`# nosec B104` ya documentado, necesario para que `host.docker.internal` lo alcance desde
Django) **falla ABIERTO si `SMS_BRIDGE_TOKEN` no está configurado** -- el código solo
advierte (`logger.warning`) y sigue aceptando peticiones sin autenticación, en vez de
rechazarlas. Confirmado que `.env` (dev) SÍ tiene `SMS_BRIDGE_TOKEN` configurado, pero
**`.env.production` NO** -- si el bridge llegara a correr en el host de producción real, hoy
aceptaría enviar SMS reales (costo real, abuso real) a cualquiera que lo alcance en esa red,
sin ningún token. **No se modificó el código** (cambiar el comportamiento de un puente que
corre en el host de producción real, fuera de Docker, sin poder verificar por este medio si
está corriendo ahora mismo ni cómo lo usa el flujo real, es una acción que requiere
confirmación explícita del usuario antes de tocarla -- mismo criterio que el resto de esta
sesión para acciones de blast radius alto e imposibles de verificar del todo).

## Gaps reales identificados, NO resueltos todavía (requieren más diseño o decisión del
## usuario -- ninguno bloqueante para el estado actual, documentados para la próxima fase):

1. **Rotación de credenciales de `notas.txt`** -- sigue pendiente, requiere que el usuario
   indique cuáles rotar (ver `VALIDACION_INFORME_EXTERNO_SINTEL_PROD_AI.md`).
2. **Backups fuera del host de producción** -- sigue pendiente, requiere destino.
3. **Batería de evaluación del modelo** (§44) -- no existe todavía (correctness, groundedness,
   retrieval relevance medidos sistemáticamente). Los tests actuales prueban comportamiento
   estructural/seguridad, no calidad de respuesta.
4. ~~Auditoría de secretos más profunda~~ -- **CERRADA 2026-09-14** (ver "FASE A, continuación
   2" abajo). Resultado: código fuente limpio; 1 hallazgo real encontrado (SMS bridge).
5. **Coordinación de retries** (§46) -- no auditado en esta pasada si LLM retry + Celery
   retry + HTTP retry pueden solaparse y producir duplicados.
6. **Supply chain / pinning de versiones** (§30) -- `requirements.txt` de `ai_engine`/
   `ai_engine_adk` usan rangos (`>=X,<Y`), no pines exactos. No es `latest`, pero tampoco
   reproducible al 100%. Pendiente de decisión (¿vale la pena el costo de mantenimiento de
   pines exactos?).
7. **`ChatResponse.metrics`** sigue `None` en `ai_engine_adk` (ya documentado, sin cambios).
8. **Backend de sesión persistente para ADK** sigue en `InMemorySessionService` (ya
   documentado, sin cambios).
9. **`sms_bridge/bridge.py` falla abierto sin `SMS_BRIDGE_TOKEN`** -- `.env.production` no lo
   tiene configurado. Requiere decisión explícita del usuario antes de tocar el
   comportamiento de un proceso que corre en el host de producción real, fuera de Docker
   (¿fail-closed si falta el token, o simplemente configurarlo en `.env.production`?).

## Clasificación de Gate (Sección 53/54 del prompt, provisional -- auditoría en curso)

```text
READY WITH ACCEPTED RISKS
```

No `NOT READY`: no hay bloqueadores de seguridad activos (WRITE gateado, RAG con
autorización, reasoning separado, secrets fuera de imágenes, TLS coherente -- ya confirmado
en la auditoría del informe externo). No `READY` sin calificar: quedan 9 ítems reales sin
cerrar (arriba), ninguno crítico pero todos genuinos, más ~40 secciones del prompt original
(evaluación, retries, supply chain pinning, batería de seguridad completa de 15 casos) que
esta pasada no alcanzó a cubrir en profundidad.

## Próxima fase sugerida (no iniciada, a la espera de indicación)

Por orden de riesgo real: (a) decisión sobre `sms_bridge` (fail-open sin token), (b) batería
de seguridad de 15 casos del §43, (c) coordinación de retries, (d) supply chain pinning.
