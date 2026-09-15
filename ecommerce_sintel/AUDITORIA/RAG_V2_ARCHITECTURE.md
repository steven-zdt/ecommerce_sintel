# RAG_V2_ARCHITECTURE — Misión "Perfeccionamiento Enterprise del RAG del Chat de Soporte"

2026-09-16. Arquitectura antes/después, y las 2 decisiones de fase que son documentación/juicio
técnico más que código nuevo (FASE 8 memoria conversacional, FASE 9 GraphRAG).

---

## 1. Arquitectura ANTES (ver `AUDITORIA/RAG_SUPPORT_BASELINE.md` para el detalle completo)

```
query -> retrieve_knowledge_for_chat() -> vector retrieval (coseno puro) -> context
       (chunks crudos, sin metadata) -> ADK Agent -> response
```

Sin metadata en el contexto ensamblado, sin capa exacta/léxica, sin reranking, sin señal de
confianza real (solo "hay chunks" vs "no hay chunks"), sin validación post-generación.

## 2. Arquitectura DESPUÉS (todas las piezas reales, verificadas con tests — commits `ec0146f`,
`cfefd77`, `5c56f43`, `34a2cb6`, `38c669d`, `890ee88`)

```
USER QUERY
    v
QUERY NORMALIZATION / CLASSIFICATION   -> detect_business_intents() (regex determinista, ya
                                           existia) + detect_apps_from_text() (FASE 2)
    v
METADATA FILTERING                     -> app_names (FASE 2, ya existia, ahora con checkpoint
                                           formal de test)
    v
HYBRID RETRIEVAL                       -> capa exacta (tokens tipo SKU/codigo/UUID) + capa
    +-- exact/lexical                     vectorial (HNSW/coseno) -- FASE 3
    +-- vector
    v
CANDIDATE MERGE + RERANKING            -> _rerank_score() = 85% similitud + 15% vigencia -- FASE 4
    v
CONTEXT ASSEMBLY                       -> cada fuente con encabezado real (título/dominio/fecha),
                                           ya no solo contenido crudo -- FASE 5
    v
RETRIEVAL CONFIDENCE / ANSWERABILITY   -> MIN_ANSWERABLE_SIMILARITY, marcador explícito si la
                                           evidencia es débil -- FASE 6
    v
GOOGLE ADK (LlmAgent, sin cambios de runtime/orquestador)
    v
GROUNDING / CLAIM VALIDATION           -> check_grounding(), 1 llamada litellm mínima, solo
                                           cuando hubo evidencia real -- FASE 7
    v
PUBLIC RESPONSE (public_response.py, intacto)
    v
FEEDBACK + EVALUATION + OBSERVABILIDAD -> ChatResponse.metrics real (antes None) -- FASE 11;
                                           dataset formal de evaluación -- FASE 10; RAG poisoning
                                           extendido con contenido real -- FASE 12
```

Coincide con la arquitectura conceptual objetivo de la misión (sección 3 del prompt maestro), con
2 desviaciones deliberadas y documentadas:
- No se implementó BM25/pg_trgm completo para la capa léxica (se evaluó, se usó coincidencia
  exacta de tokens técnicos en su lugar — ver commit `ec0146f`).
- Grounding es 1 llamada binaria/ternaria, no extracción de claims uno por uno (ver commit
  `34a2cb6`).

Ambas desviaciones están justificadas explícitamente en el código (Regla 19 de la misión:
"documenta la incompatibilidad y diseña la alternativa equivalente").

## 3. Reglas arquitectónicas no negociables — verificación final

| Regla | Estado |
|---|---|
| Google ADK sigue siendo el runtime | Intacto — ningún cambio a `LlmAgent`/`Runner`/`LiteLlm` |
| `ai_engine_adk/` sigue siendo el runtime real del soporte | Intacto |
| Routing determinista | Intacto — `resolve_turn_agent()` no se tocó |
| Nada nuevo entregado al LLM por accidente | Verificado — `check_grounding()` usa el mismo modelo, sin Tools nuevas |
| Sin llamadas ORM directas desde `ai_engine_adk` | Intacto — todo pasa por `retrievers.py` -> HTTP -> Django |
| Frontera Django/`ai_engine_adk` intacta | Intacto |
| `ai_engine_adk` no expuesto a Internet | Sin cambios de red/nginx |
| Policy Layer intacta | Intacta — `sintel_adapter.py` sin tocar |
| Filtrado de razonamiento antes de respuesta pública | Intacto — `public_response.py` sin tocar, grounding corre DESPUÉS de esa frontera |
| Restricciones de Tools intactas | Intactas |
| Sin reconexión `ai_engine` <-> `project_knowledge_graph` | Cumplido — FASE 9 (abajo) concluye NO construir GraphRAG |
| Sin uso de `PROJECT_MAP.json` | Cumplido |
| Sin ChromaDB | Cumplido — pgvector como único vector store |
| RAG basado en PostgreSQL+pgvector como punto de partida | Cumplido, evolucionado sobre esa base |
| Contrato público del chat | `ChatResponse` solo ganó contenido real en `metrics` (antes `None`) — aditivo, no rompe nada |
| Service Layer/Commands/Selectors/UUIDs/soft-delete/permisos | Respetados — `RetrievalService`/`AIKnowledgeDocumentCommands` sin violaciones |
| Toda modificación con tests | Cumplido — ver cada commit |
| Sin modelos/tablas/endpoints/Tools inventados | Cumplido — 0 modelos nuevos, 0 endpoints nuevos, 0 Tools nuevas |
| Cambios incrementales y reversibles | Cumplido — cada fase es un commit aislado, revertible sin afectar las demás |

---

## 4. FASE 8 — Memoria conversacional (auditoría + decisión, no código nuevo)

### Auditoría real del `SessionService` actual

`ai_engine_adk/sintel_root_workflow.py:227`: `_session_service = InMemorySessionService()` —
**confirmado, no asumido**: es el `SessionService` nativo de ADK, en memoria de proceso, **se
pierde en cada reinicio del contenedor**. Esto ya era un gap conocido y documentado antes de esta
misión (ver memoria de sesión `project_adk_migration_cutover_and_reasoning_fix`).

### Separación real KNOWLEDGE / STATE / MEMORY (la que pide la misión)

| Capa | Dónde vive | Estado real |
|---|---|---|
| **KNOWLEDGE** (verdad documental externa) | `ai_knowledge` (Postgres+pgvector) | Vacío (F-1), pipeline listo |
| **STATE** (estado operacional de la conversación) | `support.ChatRoom`/`support.ChatMessage` (Django, Postgres real) | **Ya persistente, ya funciona** — cada mensaje se guarda con remitente/timestamp, sobrevive reinicios, ya tiene tests reales (`support/tests.py`) |
| **MEMORY** (continuidad de sesión ADK dentro de una conversación activa) | `InMemorySessionService` | Funciona MIENTRAS el proceso vive (confirmado por `test_reasoning_separation.py::test_t6_e2e_multiturn_reasoning_never_leaks_across_turns`, 2 turnos reales en la misma sesión) — se pierde en un reinicio |

### Qué se pierde realmente

Únicamente el **estado interno de sesión de ADK** (historial de turnos tal como ADK lo modela
para construir el próximo prompt) si el contenedor se reinicia a mitad de una conversación activa
— el cliente vería que el asistente "olvida" el contexto inmediato de los últimos mensajes, pero
**nunca pierde la conversación en sí** (eso vive en `ChatMessage`, real, persistente, ya
funcionando). El caso "returning customer" / "previous unresolved issue" que pide el checkpoint
de FASE 8 ya está cubierto del lado de `support` (`test_ia_se_reactiva_en_sala_nueva_tras_cerrar_
el_ticket`, `AiOpenSupportTicketView` con `history` reenviado explícitamente al escalar a un
humano).

### Decisión: NO se implementa un backend de sesión persistente en esta misión

Razones:
1. Es un gap de **infraestructura de ADK/sesión**, no de **calidad del RAG** específicamente —
   tangencial al alcance real de esta misión.
2. Ya está documentado como pendiente desde antes (no es un descubrimiento nuevo que esta misión
   deba resolver por inercia).
3. Regla 20 de la misión ("prioriza cambios incrementales") + Regla 1 ("no sobrearquitecturar") —
   agregar un backend Redis/Postgres para `SessionService` es un cambio de infraestructura
   significativo que merece su propia misión con su propio checkpoint, no un apéndice de esta.

**Recomendación siguiente** (no ejecutada): evaluar `DatabaseSessionService`/`RedisSessionService`
de ADK cuando se decida abordar esto explícitamente — con la advertencia de seguridad ya
documentada en `sintel_adapter.py` (ADK-08: el JWT NUNCA debe sembrarse en `Session.state`,
por eso vive en `_EPHEMERAL_TOKENS` en memoria de proceso, un mecanismo aparte que SÍ seguiría
funcionando igual con cualquier backend de sesión).

---

## 5. FASE 9 — GraphRAG / Knowledge Graph (feasibility audit, decisión: NO construir)

### Feasibility audit real

La misión pide identificar qué preguntas de soporte requieren `entidad -> relación -> entidad
relacionada` (ej. producto -> categoría -> compatibilidad -> servicio relacionado). Esas
relaciones **sí existen** en el dominio real de SINTEL (FKs reales: `Product.category`,
`ServiceVariant.service`, `RentalRequest.equipment_variant`, etc.) — no es una pregunta hipotética.

### Por qué NO se construye un adaptador GraphRAG en esta misión

**Bloqueado por el mismo hallazgo F-1 que condiciona toda la misión**: la misión exige
explícitamente "Comparar: Vector RAG vs Vector + Graph. Solo mantener GraphRAG si existe mejora
medible." — con `ai_knowledge` completamente vacío, no hay ninguna base real (ni siquiera un
vector RAG con contenido) contra la cual medir si un grafo mejora algo. No hay experimento
posible, solo especulación — y la Regla 6 de la misión ("no inventar datos") y la Regla 2
("no crear Agentic RAG prematuramente... solo si las pruebas demuestran que el retrieval
monolítico actual es insuficiente") cierran la puerta a construir esto sin evidencia.

Adicionalmente, `project_knowledge_graph` es un sistema **deliberadamente desacoplado** de
`ai_engine`/`ai_engine_adk` desde una misión anterior (FASE 0 de desacoplamiento, 2026-08-10,
ver memoria `project_knowledge_graph_fase0_full_decoupling`) — reconectarlo, aunque fuera vía un
adaptador limpio (`ai_engine_adk -> graph adapter -> graph_sdk -> project_knowledge_graph`, como
sugiere la misión), es una reversión arquitectónica de una decisión explícita anterior que
requeriría autorización nueva, no algo que deba iniciarse sin evidencia de que hace falta.

### Decisión final

**NOT_IMPLEMENTED, explícito.** No se creó ningún adaptador, ningún import, ningún acoplamiento
nuevo hacia `project_knowledge_graph`. Se deja como recomendación futura, condicionada
explícitamente a: (1) que exista contenido real en `ai_knowledge` (F-1 resuelto), y (2) que un
experimento real con ese contenido muestre que el vector RAG solo pierde relaciones que el
cliente necesita y un grafo las recupera — ninguna de las dos condiciones se cumple hoy.
