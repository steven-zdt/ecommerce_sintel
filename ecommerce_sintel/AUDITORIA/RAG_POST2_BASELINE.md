# RAG_POST2_BASELINE — FASE 0

**Misión RAG-POST2 ("Certificación Enterprise del Chat de Soporte + Evaluación + Observabilidad +
Memoria Persistente"), 2026-09-16.** Auditoría contra código real (no contra documentación) de
todo lo que la misión anterior ("RAG Enterprise") dice haber implementado. Cada fila de la matriz
está verificada leyendo el archivo real citado en "Evidencia", no asumida de `RAG_V2_*.md`.

---

## Matriz de capacidades

| Capacidad | Código real | Tests | Producción | Evidencia |
|---|---|---|---|---|
| Query normalization | **PARCIAL, implícita** — cada regex de `BUSINESS_INTENT_PATTERNS` usa `re.I` (case-insensitive) individualmente; no hay una función/paso centralizado de normalización, ni normalización de acentos (los patrones listan ambas formas literalmente, ej. `cotizacion\|cotización`) | Ninguno dedicado — cubierto solo indirectamente por los tests de intent existentes | Sí, en producción | `ai_engine/routing.py:38-49`, `detect_business_intents` línea 117-119 |
| Metadata filtering | **Real** — `detect_apps_from_text()` deriva `app_names` de la query; `RetrievalService.retrieve_public_knowledge(app_names=...)` filtra el queryset | `ai_engine/tests/test_app_detection.py` (6), `ai_knowledge/tests.py::MetadataFilteringTests` (4) | Sí | `ai_engine/retrievers.py`, `ai_knowledge/services/selectors.py:156-157` |
| Hybrid retrieval | **Real** — capa exacta (`_extract_exact_candidates`, `_EXACT_TOKEN_PATTERN`) + capa vectorial (pgvector `CosineDistance`), fusión sin pisar matches exactos | `ai_knowledge/tests.py::HybridRetrievalTests` (5) | Sí | `ai_knowledge/services/selectors.py:50-68,159-178` |
| Reranking | **Real, pero NO calibrado** — `_rerank_score()` combina similitud (85%) + vigencia (15%), pesos fijos documentados como punto de partida, nunca medidos contra corpus real (F-1: `ai_knowledge` vacío) | `ai_knowledge/tests.py::RerankingTests` (2) | Sí | `ai_knowledge/services/selectors.py:39-48` |
| Context assembly | **Real** — cada fuente lleva encabezado `[Fuente i] título (dominio, actualizado)` + contenido, antes se enviaba contenido crudo sin metadata (hallazgo F-5 del baseline anterior) | `ai_engine_adk/tests/test_rag_confidence_and_assembly.py` | Sí | `ai_engine_adk/sintel_rag_adapter.py:103-109` |
| Confidence / Answerability | **Real, umbral NO calibrado** — `MIN_ANSWERABLE_SIMILARITY=0.35`, documentado explícitamente como "no calibrado", `_LOW_CONFIDENCE_MARKER` explícito | `ai_engine_adk/tests/test_rag_confidence_and_assembly.py` | Sí | `ai_engine_adk/sintel_rag_adapter.py:62,99-101` |
| Grounding | **Real, ternario** (`SUPPORTED`/`PARTIALLY_SUPPORTED`/`UNSUPPORTED`) — **NO existe un 4º estado `CONTRADICTED` separado** (una respuesta contradictoria cae en `UNSUPPORTED`, decisión explícita documentada en el propio código, ver FASE 4 de esta misión para la re-evaluación) | `ai_engine_adk/tests/test_grounding.py` (13), `test_grounding_integration.py` (3) | Sí, acotado a turnos `intent=="knowledge"` con evidencia real | `ai_engine_adk/grounding.py:43-45`, `sintel_root_workflow.py:384-399` |
| Feedback | **PARCIAL, desconectado del RAG** — existe CSAT real (`ChatRoom.csat_rating/csat_comment/csat_rated_at`), pero es feedback de la CONVERSACIÓN completa, no por-respuesta ni ligado a qué fuentes/confianza/grounding se usaron. No hay ningún mecanismo que alimente retrieval/reranking con señal de feedback real | `support/tests.py` (CSAT, no específico de RAG) | Sí (CSAT), No (feedback de RAG) | `support/models.py:35-39` |
| Metrics/Observabilidad | **Real, pero básica** — `ChatResponse.metrics` (antes `None`) ahora trae `agent/intent/handoff/tool_calls/needs_confirmation/retrieval_used/knowledge_state/grounding_result/duration_ms`. **Faltan** (pedidos explícitamente por esta misión, FASE 5): `request_id`, `metadata_filters` usados, conteo de `retrieval_candidates`/`reranked_candidates`, `selected_sources`, desglose de latencia (`retrieval_latency`/`reranking_latency`/`llm_latency` separados — solo existe `duration_ms` total), `input_token_count`/`output_token_count`/`estimated_cost` (ADK no expone `usage_metadata` por Event de forma directa, gap ya documentado) | `ai_engine_adk/tests/test_turn_metrics.py` (4) | Sí (shape básico) | `ai_engine_adk/sintel_root_workflow.py:420-430` |
| Session persistence | **NO implementado** — `InMemorySessionService`, se pierde en cada reinicio de contenedor. `google-adk==2.9.0` (versión real instalada, verificada) trae `DatabaseSessionService`/`sqlite_session_service`/`vertex_ai_session_service` de fábrica, pero **`sqlalchemy` no está en `requirements.txt`** — intentar importar `DatabaseSessionService` hoy falla con `ModuleNotFoundError` (confirmado en vivo contra el contenedor real) | Ninguno | No | `ai_engine_adk/sintel_root_workflow.py:249`, `ai_engine_adk/requirements.txt` |
| Customer memory | **NO implementado** — no existe ningún modelo, tabla, ni mecanismo de memoria semántica del cliente. La misión anterior (FASE 8/9 de RAG Enterprise) documentó esto como decisión deliberada de no construirlo sin una definición previa de qué merece recordarse — ver FASE 8 de esta misión | Ninguno | No | — |
| RAG poisoning / prompt injection (seguridad) | **Real** — PI1-PI4 (canal mensaje), PI5-PI6 (canal RAG, documento envenenado) | `test_prompt_injection_resistance.py`, `test_rag_poisoning_e2e.py`, `ai_knowledge/tests.py::RAGPoisoningRetrievalTests` | Sí | — |
| Multi-turn / multi-session isolation | **NO probado formalmente** — existe un test de separación de razonamiento multi-turno (`test_reasoning_separation.py::test_t6...`) que usa la MISMA sesión 2 veces, pero no hay ningún test de aislamiento cruzado entre 2 clientes distintos, ni de continuidad tras reinicio de contenedor (imposible de probar significativamente hasta resolver `session persistence`) | Parcial (`test_reasoning_separation.py`) | N/A | — |

## Hallazgos nuevos de esta fase (no estaban en el baseline anterior)

| ID | Hallazgo | Severidad |
|---|---|---|
| **PG-1** | `sqlalchemy` no está en `ai_engine_adk/requirements.txt` — bloquea directamente el objetivo prioritario de esta misión (FASE 7, sesión persistente) hasta agregarlo | HIGH (bloqueante de FASE 7, no de producción actual) |
| **PG-2** | No existe normalización de query centralizada — cada regex de intent maneja mayúsculas/acentos por su cuenta, riesgo de "miss" silencioso si un patrón nuevo olvida cubrir una variante (misma clase de riesgo que F-8 del baseline anterior) | MEDIUM |
| **PG-3** | El feedback (CSAT) existe pero está completamente desconectado del pipeline de RAG — no hay forma de saber, con datos reales, si una respuesta con `grounding_result=SUPPORTED` tuvo mejor CSAT que una `PARTIALLY_SUPPORTED` | MEDIUM |
| **PG-4** | `grounding.py` no distingue `CONTRADICTED` de `UNSUPPORTED` — decisión explícita pre-existente, pero esta misión (FASE 4) pide evaluarla de nuevo explícitamente | LOW (documentado, decisión deliberada, a re-evaluar) |
| **PG-5** | No existe ninguna vista/mecanismo de observabilidad de producción dedicado (FASE 18) más allá de los logs estructurados (`logger.info('[CHAT]...')`) y `ChatMessage.ai_metrics` expuesto vía `AdminSupportChatViewSet` — no hay un lugar único para reconstruir "qué pasó en este turno" sin cruzar logs + DB manualmente | MEDIUM |

## Confirmación de lo que NO cambió (reglas no negociables)

Verificado contra código real, no reafirmado por inercia:
- Google ADK sigue siendo el runtime (`LlmAgent`/`Runner`/`LiteLlm`, sin cambios estructurales).
- Routing sigue siendo 100% determinista (`resolve_turn_agent()` → regex → `AgentRegistry`).
- `ai_engine_adk` sigue sin tocar el ORM directo — todo pasa por `retrievers.py` → HTTP interno.
- El JWT sigue sin sembrarse en `Session.state` (`_EPHEMERAL_TOKENS`, proceso, no persistente) —
  **relevante para FASE 7**: el backend de sesión persistente que se elija NO debe cambiar esto.
- `ChromaDB` no reapareció en ninguna dependencia (`requirements.txt` limpio).
- `ai_engine` no importa nada de `project_knowledge_graph`.

## CHECKPOINT 0 — Estado

**PASS**, con hallazgos reales documentados (PG-1 a PG-5) que se convierten en el backlog real de
esta misión — no se avanza fingiendo que algo ya funciona cuando el propio código demuestra lo
contrario (ej. `DatabaseSessionService` falla al importar HOY, verificado en vivo, no asumido).
