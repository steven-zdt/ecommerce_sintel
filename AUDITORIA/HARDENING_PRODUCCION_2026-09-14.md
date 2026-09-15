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

## Gaps reales identificados, NO resueltos todavía (requieren más diseño o decisión del
## usuario -- ninguno bloqueante para el estado actual, documentados para la próxima fase):

1. **Sin límite explícito de tool calls/iteraciones por turno en ADK** (§34). Introspección
   real confirmó que `LlmAgent`/`Runner` de Google ADK no exponen un `max_tool_calls`/
   `max_iterations` nativo -- solo hooks (`before_tool_callback`, etc.) donde SINTEL tendría
   que implementar su propio contador. El sistema OLD sí tenía un cap duro (`tool_calls[:4]`
   en `action_graph.py`). Mitigado parcialmente por el límite diario de turnos
   (`cost_control.py`) pero no por turno individual. Pendiente de diseño.
2. **Rotación de credenciales de `notas.txt`** -- sigue pendiente, requiere que el usuario
   indique cuáles rotar (ver `VALIDACION_INFORME_EXTERNO_SINTEL_PROD_AI.md`).
3. **Backups fuera del host de producción** -- sigue pendiente, requiere destino.
4. **Batería de evaluación del modelo** (§44) -- no existe todavía (correctness, groundedness,
   retrieval relevance medidos sistemáticamente). Los tests actuales prueban comportamiento
   estructural/seguridad, no calidad de respuesta.
5. **Auditoría de secretos más profunda** (§25) -- más allá de `notas.txt`, no se hizo un
   grep sistemático de todo el código fuente buscando credenciales hardcodeadas. Pendiente.
6. **Coordinación de retries** (§46) -- no auditado en esta pasada si LLM retry + Celery
   retry + HTTP retry pueden solaparse y producir duplicados.
7. **Supply chain / pinning de versiones** (§30) -- `requirements.txt` de `ai_engine`/
   `ai_engine_adk` usan rangos (`>=X,<Y`), no pines exactos. No es `latest`, pero tampoco
   reproducible al 100%. Pendiente de decisión (¿vale la pena el costo de mantenimiento de
   pines exactos?).
8. **`ChatResponse.metrics`** sigue `None` en `ai_engine_adk` (ya documentado, sin cambios).
9. **Backend de sesión persistente para ADK** sigue en `InMemorySessionService` (ya
   documentado, sin cambios).

## Clasificación de Gate (Sección 53/54 del prompt, provisional -- auditoría en curso)

```text
READY WITH ACCEPTED RISKS
```

No `NOT READY`: no hay bloqueadores de seguridad activos (WRITE gateado, RAG con
autorización, reasoning separado, secrets fuera de imágenes, TLS coherente -- ya confirmado
en la auditoría del informe externo). No `READY` sin calificar: quedan 9 ítems reales sin
cerrar (arriba), ninguno crítico pero todos genuinos, más ~40 secciones del prompt original
(evaluación, retries, supply chain pinning, batería de seguridad completa de 15 casos,
auditoría de secretos exhaustiva) que esta pasada no alcanzó a cubrir en profundidad.

## Próxima fase sugerida (no iniciada, a la espera de indicación)

Por orden de riesgo real: (a) límite de tool calls por turno en ADK, (b) auditoría de
secretos más profunda, (c) batería de seguridad de 15 casos del §43, (d) coordinación de
retries, (e) supply chain pinning.
