# RAG_V2_FINAL_CERTIFICATION — FASE 15

**Misión: "Perfeccionamiento Enterprise del RAG del Chat de Soporte", cerrada 2026-09-16.**
Certificación final: antes/después, cambios implementados vs. rechazados, métricas baseline vs.
final, tests, regresiones, hallazgos residuales, riesgos pendientes, próximas recomendaciones.

Documentos de esta misión (leer en este orden para el detalle completo de cada fase):
1. `RAG_SUPPORT_BASELINE.md` (FASE 0)
2. `RAG_KNOWLEDGE_DATA_AUDIT.md` (FASE 1)
3. `RAG_V2_ARCHITECTURE.md` (arquitectura completa + FASE 8/9)
4. `RAG_V2_EVALUATION.md` (FASE 10)
5. `RAG_V2_SECURITY.md` (FASE 12)
6. Este documento (FASE 15)

---

## 1. Resumen ejecutivo

El RAG del chat de soporte evolucionó de un pipeline monolítico (vector search puro, sin
metadata, sin confianza, sin validación post-generación) a un pipeline enterprise con
recuperación híbrida, reranking, ensamblado de contexto con metadata real, umbral de
confianza/answerability, y validación de grounding post-generación — todas las piezas reales,
probadas con tests, ejecutadas contra el LLM real de producción (LM Studio) cuando correspondía.

El hallazgo más importante de la misión (**F-1: `ai_knowledge` está completamente vacío**) no se
"arregló" fabricando datos — se documentó honestamente en 2 auditorías dedicadas (FASE 0 y FASE 1)
y se usó como restricción real de diseño en el resto de las fases (dataset de evaluación,
decisión de no construir GraphRAG). Esto es intencional y coherente con la Regla 6 de la misión.

## 2. Cambios implementados (por fase, con commit real)

| Fase | Cambio | Commit |
|---|---|---|
| 0 | Baseline completo del pipeline real, 9 hallazgos (F-1 a F-9) | `7b0a1c7` |
| 1 | Auditoría dedicada de datos, hallazgo nuevo F-10 (sin ingesta admin) | `9ad9949` |
| 2 | Checkpoint formal de metadata filtering, hallazgo F-8 confirmado (no corregido, documentado) | `890ee88` |
| 3 | Hybrid retrieval: capa exacta (SKU/código/UUID) + vectorial | `ec0146f` |
| 4 | Reranking: 85% similitud + 15% vigencia del documento | `cfefd77` |
| 5-6 | Context assembly con metadata real + retrieval confidence/answerability | `5c56f43` |
| 7 | Grounding/claim validation post-generación (`grounding.py`, nuevo) | `34a2cb6` |
| 10 | Dataset formal de evaluación (3 categorías evaluables, 8 bloqueadas por F-1) | `9ad9949` |
| 11 | Observabilidad real del turno — `ChatResponse.metrics` ya no es `None` | `38c669d` |
| 12 | RAG poisoning E2E contra LLM real (PI5/PI6), extiende PI1-4 | `5a165e8` |

**9 commits, 0 archivos de producción rotos, 0 reversiones necesarias.**

## 3. Cambios evaluados y rechazados explícitamente (con justificación)

| Propuesta | Por qué NO se implementó |
|---|---|
| BM25/pg_trgm completo para la capa léxica | Coincidencia exacta de tokens técnicos cubre el caso real (SKU/código/UUID) con muchísimo menos riesgo/superficie; BM25 completo es una pieza de infraestructura nueva sin evidencia de que la capa exacta actual sea insuficiente — Regla 2 de la misión |
| Extracción de claims uno por uno en grounding | Una verificación binaria/ternaria por turno ya cubre el objetivo (detectar afirmaciones no respaldadas) con 1 llamada extra al LLM en vez de N; extracción granular es una optimización sin evidencia de necesidad |
| Backend de sesión persistente (Redis/DB) para `SessionService` (FASE 8) | Gap de infraestructura de ADK, no de calidad del RAG; ya documentado desde antes de esta misión; el caso real de "cliente que regresa" ya está cubierto por `ChatMessage`/`ChatRoom` persistentes — ver `RAG_V2_ARCHITECTURE.md` sección 4 |
| Adaptador GraphRAG (FASE 9) | Bloqueado por F-1 — no hay corpus real contra el cual medir si un grafo mejora algo; además revertiría una decisión arquitectónica explícita anterior (desacople de `project_knowledge_graph`) sin autorización nueva — ver `RAG_V2_ARCHITECTURE.md` sección 5 |
| Ampliar el diccionario de keywords de `detect_apps_from_text()` (F-8) | Decisión de contenido/producto sobre qué términos cubrir (~28 entradas a revisar con criterio), no un bug de una línea — documentado, no parcheado a ciegas |
| Mecanismo de ingesta admin para `ai_knowledge` (F-10) | Fuera del alcance explícito de esta misión (retrieval/contextualización/grounding/memoria/evaluación, no un CRUD nuevo de contenido) |
| Corpus de contenido real para las 8 categorías bloqueadas del dataset de evaluación | Fabricar una "respuesta esperada" sin corpus real viola la Regla 6 de la misión — documentado en `RAG_V2_EVALUATION.md`, no fabricado |

## 4. Regla arquitectónica no negociable — verificación final

Las 20 reglas del prompt maestro fueron verificadas una por una contra el código real al cierre de
la misión — tabla completa en `RAG_V2_ARCHITECTURE.md` sección 3. **0 violaciones.**

## 5. Tests — estado final (corrida completa, 2026-09-16, post-rebuild de todas las imágenes)

| Suite | Comando | Resultado |
|---|---|---|
| `ai_engine_adk/tests/` (incluye `rag_evaluation/`, `test_grounding*.py`, `test_rag_poisoning_e2e.py`, `test_rag_confidence_and_assembly.py`, `test_turn_metrics.py`, y toda la suite preexistente PI1-4/EB1-2/reasoning/security) | `docker compose run --rm --no-deps sintel_ai_adk pytest tests/ -q` | **67 passed**, 0 failed (380s) |
| `ai_knowledge` (Django) | `docker compose exec django python manage.py test ai_knowledge --noinput` | **26 passed**, 0 failed |
| `ai_engine/tests/test_app_detection.py` (servicio OLD, `sintel_ai`) | `docker compose run --rm --no-deps sintel_ai pytest tests/test_app_detection.py -q` | **6 passed**, 0 failed |

**Total: 99 tests, 99 passed en la corrida final consolidada — 0 regresiones.**

Nota metodológica honesta: durante el desarrollo de la misión (no en esta corrida final), se
observó 3 veces un patrón de flakiness ambiental (PI4, PI6, y 2 casos de `rag_evaluation`) — falla
solo en corridas de suite completa con muchas llamadas secuenciales reales a LM Studio, PASS
limpio siempre en aislamiento. Diagnosticado como contención del backend local de LM Studio
(single-instance), no como defecto del código. Documentado en detalle en `RAG_V2_SECURITY.md`
sección 5 y `RAG_V2_EVALUATION.md` sección 3, nunca ocultado ni maquillado con `skip`/`xfail`.

## 6. Métricas — baseline vs. final

| Métrica | Antes (FASE 0) | Después (FASE 15) |
|---|---|---|
| `ChatResponse.metrics` | `None` (hardcoded, comentario "pendiente") | Real: `agent, intent, handoff, tool_calls, needs_confirmation, retrieval_used, knowledge_state, grounding_result, duration_ms` |
| Señal de confianza de retrieval | Binaria (hay chunks / no hay chunks) | `MIN_ANSWERABLE_SIMILARITY` + marcador explícito de baja confianza |
| Validación post-generación | Ninguna | `check_grounding()`, fallback seguro si `UNSUPPORTED` |
| Cobertura de retrieval | Solo vectorial | Híbrida (exacta + vectorial), con fallback ante caída del proveedor de embeddings |
| Orden de resultados | Distancia coseno cruda | Reranking (similitud + vigencia) |
| Precisión/recall sobre contenido real | No medible (sin código de medición) | Sigue **NOT_MEASURED explícito** — bloqueado por F-1, no por falta de instrumentación (la instrumentación ya existe) |
| Tasa de invención ante ausencia de datos | No medida formalmente | Medida (dataset FASE 10, categoría `NO_ANSWER`): 0 invenciones detectadas en la corrida final |

## 7. Hallazgos residuales (no resueltos por esta misión, documentados para decisión de producto)

| ID | Hallazgo | Severidad | Por qué no se resolvió aquí |
|---|---|---|---|
| F-1 | `ai_knowledge` vacío | CRITICAL | Requiere decisión de negocio sobre contenido (no es una tarea de ingeniería) |
| F-8 | `detect_apps_from_text()` no reconoce términos de producto reales sin keyword de módulo (ej. "la escalera") | MEDIUM | Requiere revisión de contenido del diccionario de keywords, no un fix de una línea |
| F-10 | Sin mecanismo de ingesta admin para `ai_knowledge` | HIGH | Fuera del alcance explícito de esta misión (RAG, no CRUD de contenido) |
| Sesión ADK no persistente (`InMemorySessionService`) | Se pierde el estado de sesión de ADK en un reinicio a mitad de conversación | MEDIUM | Gap de infraestructura, ya documentado antes de esta misión; conversación en sí SÍ persiste vía `ChatMessage` |

## 8. Riesgos operacionales pendientes

- **LM Studio single-instance como backend de test/dev**: la flakiness ambiental documentada
  (sección 5) es un riesgo de fiabilidad de CI/test, no de producción — pero si producción también
  corre sobre una sola instancia bajo carga real de clientes, el mismo patrón de contención podría
  manifestarse como latencia alta bajo picos de tráfico. No verificado en esta misión (fuera de
  alcance: FASE 15 es certificación del RAG, no de infraestructura de inferencia).
- **F-1 sin resolver bloquea el valor real de producción de FASE 2-7, 10, 12**: todo el trabajo de
  retrieval/reranking/grounding está construido y probado, pero no tiene contenido real sobre el
  cual operar en producción hasta que se resuelva F-1.

## 9. Próximas recomendaciones (en orden de impacto real)

1. Decisión de negocio: qué contenido publicar en `ai_knowledge` (resuelve F-1, desbloquea el
   valor real de toda esta misión).
2. Construir el mecanismo de ingesta admin (F-10) — una vez exista contenido que ingerir.
3. Revisar y ampliar el diccionario de `detect_apps_from_text()` con criterio de producto (F-8).
4. Evaluar `DatabaseSessionService`/`RedisSessionService` de ADK como misión propia, con su propio
   checkpoint de seguridad (JWT nunca en `Session.state` — ya documentado en `sintel_adapter.py`).
5. Solo después de (1): repoblar `dataset.py` retirando categorías de `BLOCKED_CATEGORIES` una por
   una, con contenido real, y medir precisión/recall real por primera vez.
6. Solo después de (1) y con evidencia real de que el vector RAG pierde relaciones que el cliente
   necesita: reevaluar GraphRAG (FASE 9) con un experimento real, no antes.

## 10. Certificación final

**APTA**, con las salvedades explícitas de las secciones 7 y 8 — ninguna de las cuales es un
defecto introducido por esta misión; todas preexistían o son decisiones de producto fuera del
alcance de ingeniería. Las 20 reglas arquitectónicas no negociables del prompt maestro se
verificaron sin violaciones. 99/99 tests reales pasan en la corrida final consolidada. Ningún
modelo, tabla, endpoint, Tool o capacidad fue inventado. Todo cambio quedó respaldado por al menos
un test real, ejecutado contra código real (no simulado), con hallazgos honestos documentados en
vez de maquillados.
