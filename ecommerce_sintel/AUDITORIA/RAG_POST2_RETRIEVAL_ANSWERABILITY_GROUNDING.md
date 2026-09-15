# RAG_POST2 — FASE 2 (Retrieval Evaluation), FASE 3 (Answerability), FASE 4 (Grounding)

**Misión RAG-POST2, 2026-09-16.** Las tres fases comparten una misma restricción real: **F-1
(`ai_knowledge` vacío) sigue sin resolver**, verificado de nuevo en esta fase, no asumido del
baseline anterior. Esto determina qué es medible honestamente y qué no.

---

## FASE 2 — Retrieval Evaluation: RAG BASELINE vs RAG V2

| Métrica pedida | Estado |
|---|---|
| precision@k | **NOT MEASURABLE** — requiere un corpus real con juicios de relevancia (qué documento SÍ responde qué query). No existe ningún documento real indexado (F-1). |
| recall@k | **NOT MEASURABLE** — mismo motivo |
| MRR | **NOT MEASURABLE** — mismo motivo |
| relevance | **NOT MEASURABLE** — mismo motivo |
| noise ratio | **NOT MEASURABLE** — mismo motivo |
| source diversity | **NOT MEASURABLE** — mismo motivo |
| filter effectiveness | **PARCIALMENTE MEASURABLE** — el filtro de metadata (`app_names`) es una función pura y determinista (`detect_apps_from_text`), su efectividad de *matching de keywords* SÍ se probó con casos reales (`ai_engine/tests/test_app_detection.py`, 6 casos, incluye F-8 confirmado: falla en "la disponibilidad de la escalera"). Lo que NO se puede medir es si ese filtro mejora la *precisión del retrieval final* contra contenido real, por la misma razón de F-1. |
| reranking quality | **NOT MEASURABLE contra corpus real** — los pesos de `_rerank_score` (85% similitud, 15% vigencia) siguen sin calibrar, documentado explícitamente en el propio código desde su creación (FASE 4 de RAG Enterprise). `ai_knowledge/tests.py::RerankingTests` prueba que el mecanismo ordena correctamente dado un caso sintético controlado — no que los pesos sean los óptimos. |

**Comparación BASELINE vs V2**: la única comparación honesta posible hoy es **estructural**, no
de resultado numérico: V2 tiene una capa exacta que el baseline no tenía (`_extract_exact_
candidates`), reranking que el baseline no tenía (distancia cruda), confianza/umbral que el
baseline no tenía (siempre devolvía top-k sin piso de calidad). Estas 3 diferencias están
probadas con datos sintéticos (`HybridRetrievalTests`, `RerankingTests`,
`test_rag_confidence_and_assembly.py`) — el veredicto "mejora medible" queda **NOT MEASURABLE**
hasta que exista contenido real, exactamente como ya concluyó `RAG_KNOWLEDGE_DATA_AUDIT.md`.

## FASE 3 — Answerability Evaluation

La misión pide comportamiento diferenciado explícito para 5 niveles de evidencia. Estado real,
verificado contra el código (`ai_engine_adk/sintel_rag_adapter.py::fetch_and_assemble_knowledge`):

| Nivel de evidencia | Comportamiento real | Evidencia |
|---|---|---|
| Sin evidencia (`docs` vacío) | `_NO_KNOWLEDGE_MARKER` explícito — instruye al LLM a admitir que no tiene información verificada | `test_sin_resultados_devuelve_marcador_original_fase17` |
| Evidencia insuficiente (`best_similarity < 0.35`) | `_LOW_CONFIDENCE_MARKER` explícito — instruye a NO afirmar datos concretos, ofrecer escalar | `test_evidencia_lejana_no_supera_el_umbral_devuelve_marcador_baja_confianza` |
| Evidencia parcial/débil pero sobre el umbral | Contexto normal, pero el propio umbral (0.35, conservador) ya filtra la mayoría de evidencia realmente débil — no hay un tercer estado intermedio explícito entre "low confidence" y "answerable" | — (decisión de diseño: 2 umbrales, no 3, ver "Por qué NO 3 niveles" abajo) |
| Evidencia fuerte (un solo candidato fuerte entre varios débiles) | Answerable — la decisión usa el MEJOR candidato, no el promedio (evita que ruido de relleno degrade una respuesta que sí tiene una fuente fuerte) | `test_confianza_usa_el_mejor_candidato_no_el_promedio` |
| Evidencia contradictoria | No hay un estado de retrieval dedicado a "contradictorio" — eso lo captura la capa de GROUNDING (post-generación), no la de retrieval confidence (pre-generación). Ver FASE 4. | — |

### Por qué NO hay 3 niveles de confianza de retrieval (solo 2: sin evidencia / evidencia débil vs. evidencia suficiente)

Evaluado explícitamente para esta misión: un tercer nivel ("evidencia parcial → respuesta
calificada/aclaración") añadiría una rama de comportamiento nueva sin ningún dato real que
determine dónde debería ir el segundo umbral — con `ai_knowledge` vacío, cualquier segundo
umbral sería un número inventado, no calibrado (Regla 6 de la misión: "no inventar datos").
**Decisión: mantener 2 niveles hasta que exista evidencia real para calibrar un tercero.**
Documentado aquí como decisión activa, no como omisión.

### Regresión

Los 6 tests de `test_rag_confidence_and_assembly.py` (preexistentes, ver commit `5c56f43`) SON
la suite de regresión que pide esta fase — no se duplican aquí. Corridos de nuevo en esta misión
(FASE 5/6, ver commit `7ab67fe`): **10/10 pasando** junto a los 4 de `test_turn_metrics.py`.

## FASE 4 — Grounding Evaluation

### Estado real de los 4 casos que pide la misión

| Caso pedido | Estado real en `grounding.py` |
|---|---|
| `SUPPORTED` | Implementado — verdict real |
| `PARTIALLY_SUPPORTED` | Implementado — verdict real, también el fallback ante error/timeout del validador |
| `UNSUPPORTED` | Implementado — verdict real, dispara `UNGROUNDED_FALLBACK_RESPONSE` |
| `CONTRADICTED` | **NO implementado como estado separado** — una respuesta que contradice la evidencia cae en `UNSUPPORTED` (el prompt de `_GROUNDING_PROMPT_TEMPLATE` ya pregunta explícitamente si "afirma datos concretos que NO estan en la evidencia", lo cual incluye datos que la contradicen) |

### Decisión re-evaluada en esta fase (la misión pide explícitamente reconsiderar esto)

**Se mantiene la decisión original: NO se separa `CONTRADICTED` de `UNSUPPORTED`.** Razón
re-verificada, no solo heredada: desde la perspectiva del CLIENTE, el tratamiento correcto es
idéntico en ambos casos — la respuesta se reemplaza por `UNGROUNDED_FALLBACK_RESPONSE`, un
agente humano puede intervenir. Separar el estado solo agregaría valor si existiera un consumidor
real que necesitara reaccionar distinto a "no sustentado" vs. "contradice la evidencia" (por
ejemplo, alertar con más urgencia una contradicción activa) — hoy no existe ese consumidor
(`ChatMessage.ai_metrics` solo persiste el string, `AdminSupportChatViewSet` no distingue).
Agregar el 4º estado sin un consumidor real sería sobrearquitecturar (Regla 1 de la misión).

**Se agrega, sí**, un test que verifica explícitamente que una respuesta CONTRADICTORIA (no solo
"sin mencionar") es capturada por `UNSUPPORTED` — antes esto no estaba probado explícitamente,
solo se probaba el caso "no mencionado en absoluto".

### Checkpoint FASE 2-4 — Estado

**PASS**, con los límites `NOT MEASURABLE` declarados explícitamente donde corresponde (Regla de
la misión: "si una metrica no puede calcularse correctamente, marcar NOT MEASURABLE y explicar
por que") — ninguna métrica de precisión/recall/relevancia se fabricó para aparentar progreso.
