# RAG_SUPPORT_BASELINE — FASE 0

**Misión: "Perfeccionamiento Enterprise del RAG del Chat de Soporte", 2026-09-16.**
Checkpoint 0: demostrar entendimiento real del RAG actual antes de modificar nada. Todo lo
documentado aquí viene de leer el código real (`ai_knowledge/`, `ai_engine/retrievers.py`,
`ai_engine_adk/sintel_rag_adapter.py`, `ai_engine_adk/sintel_root_workflow.py`,
`ai_engine/routing.py`, `ai_engine/agents/profiles/*.yaml`) y de consultar el estado real de la
base de datos de desarrollo — nunca asumido desde la documentación de sesiones anteriores.

---

## 1. Pipeline real, extremo a extremo

```
mensaje del cliente
  ↓
resolve_turn_agent(message)                         [ai_engine_adk/sintel_root_workflow.py:154]
  → detect_business_intents(message)                [ai_engine/routing.py — regex, determinista]
  → intent == "knowledge" solo si matchea:
      r"\b(como funciona|política|garantía|qué es|horario|términos|compatible)\w*"
  ↓
AgentRegistry.route("knowledge")                    [ai_engine/agents/__init__.py]
  → SalesAgent (único perfil que declara "knowledge" en su YAML — ver hallazgo F-2)
  ↓
intent == "knowledge" → build_knowledge_context(message)   [sintel_rag_adapter.py]
  ↓
retrieve_knowledge_for_chat(query, apps=None, k=8)          [ai_engine/retrievers.py]
  → apps = detect_apps_from_text(query) si no se pasan explícitos
      (keyword-substring matching sobre un diccionario fijo de ~28 apps,
      ai_engine/retrievers.py:28-61 — NO es clasificación de intención real)
  → POST /api/v1/internal/ai/knowledge/retrieve/ {query, app_names, k}
    (AllowAny — frontera real es de red: nginx bloquea /internal/ desde Internet)
  ↓
RetrievalService.retrieve_public_knowledge()        [ai_knowledge/services/selectors.py]
  → EmbeddingService.embed_text(query)               [HTTP a AIChannelConfig.CHANNEL_EMBEDDINGS]
  → AIKnowledgeChunk.objects.filter(
        embedding__isnull=False,
        document__is_active=True, document__visibility='public', document__is_deleted=False
    ).order_by(CosineDistance('embedding', query_vector))[:k]
  → SOLO similitud coseno HNSW — sin BM25/lexical, sin reranking, sin metadata filtering
    más allá de app_name/visibility/is_active (ya declarado "fuera de alcance FASE 1" en
    el propio código, selectors.py líneas 73-78)
  ↓
build_knowledge_context(): trunca a MAX_KNOWLEDGE_CHUNKS=6, cada chunk a 800 chars,
  join con "\n---\n", total a MAX_CONTEXT_CHARS=6000
  → si NO hay chunks: _NO_KNOWLEDGE_MARKER = "NINGUNO -- no se encontro informacion
    verificada sobre este tema." (Fase 17 histórica, previene alucinación confirmada)
  → **title/source/app_name/updated_at se piden a Django pero se DESCARTAN aquí — solo
    `content` sobrevive al ensamblado** (ver hallazgo F-5)
  ↓
state_delta[SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY] → ADK Runner
  ↓
instruction_provider (LlmAgent de ADK): antepone "\n\nConocimiento relevante:\n{knowledge}"
  a la instrucción base del agente — el LLM recibe el contexto de RAG mezclado en el
  system prompt, no como evidencia estructurada/etiquetada
  ↓
LlmAgent (Qwen3.5 via LM Studio, litellm) genera respuesta
  ↓
public_response.py filtra Part.thought (razonamiento interno) antes de la respuesta pública
```

---

## 2. Componentes reales por capa

| Capa | Archivo real | Responsabilidad |
|---|---|---|
| Routing (decide SI hacer RAG) | `ai_engine/routing.py::detect_business_intents` | Regex determinista, intent `"knowledge"` |
| Selección de agente | `ai_engine/agents/__init__.py::AgentRegistry` | `SalesAgent` maneja `"knowledge"` (ver F-2) |
| Adapter ADK↔retrieval | `ai_engine_adk/sintel_rag_adapter.py::build_knowledge_context` | Trunca/formatea, inyecta marcador de "sin conocimiento" |
| Cliente HTTP del retrieval | `ai_engine/retrievers.py::retrieve_knowledge_for_chat` | Detecta `apps` por keyword, llama a Django, degrada con gracia |
| Endpoint interno | `ai_knowledge/api/views.py::AiKnowledgeRetrieveView` | `POST /internal/ai/knowledge/retrieve/`, `AllowAny` (frontera de red) |
| Retrieval real | `ai_knowledge/services/selectors.py::RetrievalService` | Embed query + `CosineDistance` sobre pgvector HNSW |
| Embeddings | `ai_knowledge/services/embedding_service.py::EmbeddingService` | Resuelve proveedor activo (`AIChannelConfig.CHANNEL_EMBEDDINGS`), HTTP a Ollama/OpenAI-compatible |
| Ingesta | `ai_knowledge/services/commands.py::AIKnowledgeDocumentCommands/AIKnowledgeEmbeddingCommands` | Upsert + chunking simple (párrafos, 1200/150 chars) + embedding diferido |
| Modelos | `ai_knowledge/models.py` | `AIKnowledgeDocument` (title/app_name/source/language/visibility/content/is_active), `AIKnowledgeChunk` (document FK, chunk_index, content, embedding VectorField(1024), embedding_model, embedded_at) |

---

## 3. Estado real de los datos (verificado contra la BD de desarrollo, no asumido)

```
documentos totales:          0
documentos activos+públicos: 0
documentos activos+internos: 0
chunks totales:               0
chunks con embedding:         0
chunks sin embedding:         0
```

**La base de conocimiento está completamente vacía.** No es una simplificación retórica: se
verificó con una consulta real contra `ecommerce_sintel_django` (dev). Cada pregunta de intent
`"knowledge"` hoy golpea el camino `_NO_KNOWLEDGE_MARKER` sin excepción — el único test que
existe contra este flujo (`ai_engine_adk/tests/test_evaluation_battery.py::test_eb1_...`) prueba
exactamente eso: que el sistema NO alucina cuando no hay conocimiento, no que el retrieval
funcione bien con contenido real, porque **no hay contenido real que recuperar.**

Esto reencuadra toda la misión — ver sección 6.

**Proveedor de embeddings SÍ está configurado y activo** (verificado, no asumido):
`AIChannelConfig.CHANNEL_EMBEDDINGS` → modelo `bge-m3:latest` vía proveedor `Ollama Dev (bge-m3)`
(kind `ollama-nativo`, activo). Dimensión fija de columna: 1024 (`ai_knowledge/models.py:35`),
coincide con bge-m3. El pipeline de embeddings en sí está listo para recibir contenido.

---

## 4. Configuración real (no inferida)

| Parámetro | Valor real | Archivo |
|---|---|---|
| `MAX_KNOWLEDGE_CHUNKS` | 6 | `ai_engine/routing.py:30` |
| `MAX_CONTEXT_CHARS` | 6000 | `ai_engine/routing.py:28` |
| Truncado por chunk | 800 chars | `sintel_rag_adapter.py:57` |
| `k` (top-k retrieval) | 8 (default de `retrieve_knowledge_for_chat`) | `ai_engine/retrievers.py:73` |
| Chunk size / overlap (ingesta) | 1200 / 150 chars | `ai_knowledge/services/commands.py:20-21` |
| Índice vectorial | HNSW, `m=16, ef_construction=64`, `vector_cosine_ops` | `ai_knowledge/models.py:114-120` |
| Distancia | Coseno (`CosineDistance`, ascendente = más similar) | `ai_knowledge/services/selectors.py:101` |
| Dimensión de embedding | 1024 (fija, `AI_KNOWLEDGE_EMBEDDING_DIMENSIONS`) | `ai_knowledge/models.py:35` |
| Filtro de gobernanza | `visibility='public' AND is_active=True AND is_deleted=False` | `ai_knowledge/services/selectors.py:85-93` |
| App detection (pre-filtro) | `detect_apps_from_text()` — keyword-substring sobre ~28 apps | `ai_engine/retrievers.py:28-70` |

---

## 5. Agent profiles que consumen RAG

Solo un perfil declara el intent `"knowledge"` en su YAML:

```yaml
# ai_engine/agents/profiles/sales_agent.yaml
intents: [promos, quote, knowledge]
```

`support_agent.yaml` declara `intents: [support, rental_change, unknown]` — **NO incluye
`"knowledge"`**. Esto significa que hoy, preguntas tipo FAQ ("¿cómo funciona la garantía?",
"¿cuál es el horario?") las responde **`SalesAgent`**, no `SupportAgent` — un hecho real, no un
bug necesariamente (podría ser una decisión de producto de una fase anterior), pero vale la pena
que el usuario confirme si es intencional. Ver hallazgo F-2.

---

## 6. Tests existentes relacionados con RAG

| Archivo | Qué cubre realmente |
|---|---|
| `ai_knowledge/tests.py` (170 líneas) | Chunking, upsert/re-chunk, **filtro de visibilidad** (el hallazgo histórico real: una pregunta de horario recuperó arquitectura interna antes de este fix), degradación sin proveedor de embeddings, endpoint E2E — todo con `EmbeddingService` mockeado (vector determinista, no un modelo real) |
| `ai_engine_adk/tests/test_evaluation_battery.py` | `test_eb1`: groundedness cuando `ai_knowledge` está vacío (confirma que NO alucina). `test_eb2`: pregunta ambigua no rompe el turno. Ambos E2E reales contra LM Studio. |
| `ai_engine_adk/tests/test_prompt_injection_resistance.py` | `pi3` confirma que el routing (incluida la rama que activa RAG) es regex determinista, no semántico — el LLM no puede activar/desactivar retrieval por instrucción. Ningún test inyecta contenido malicioso REAL dentro de `ai_knowledge` (RAG poisoning con datos reales) — ver hallazgo F-7. |

**No existe ningún test de:** precisión de retrieval, ranking, hybrid search, reranking,
metadata filtering, context assembly con metadata real, confidence/answerability, grounding
post-generación — porque ninguno de esos componentes existe todavía en el código real.

---

## 7. Observabilidad existente

`ChatMessage.ai_metrics` (JSONField) ya captura, por turno de IA: `agent`, `intent`, `tools`,
`llm_tokens_in/out`, `duration_ms`, `fallback_used`, `handoff`, `needs_confirmation`,
`write_executed` (ver `support/services/selectors.py::ChatAnalyticsSelector`). **No captura
nada específico de retrieval**: no hay `retrieval_used`, `candidate_count`, `sources`,
`confidence`, `answerability` ni `grounding_result`. La observabilidad de RAG como tal no existe
hoy — es puramente observabilidad de turno/agente/tool.

---

## 8. Hallazgos de FASE 0 (clasificados, para orientar las fases siguientes)

| ID | Hallazgo | Severidad |
|---|---|---|
| **F-1** | **La base de conocimiento está vacía (0 documentos, 0 chunks).** Ninguna mejora de retrieval/ranking/hybrid/GraphRAG es medible ni útil en producción hasta que exista contenido real. Este es el hallazgo que más debe condicionar el orden de ejecución de la misión. | **CRITICAL** |
| F-2 | El intent `"knowledge"` lo maneja `SalesAgent`, no `SupportAgent` — posible desalineación de producto (preguntas de FAQ respondidas por el agente de ventas). No se toca sin confirmación: podría ser intencional. | MEDIUM |
| F-3 | Retrieval es 100% semántico (coseno/HNSW) — sin lexical/exact match. El propio código ya lo señala como gap conocido, no descubierto ahora (`selectors.py:73-78`). Términos exactos (SKUs, nombres de producto, códigos) dependen enteramente de que el embedding los capture bien. | HIGH (una vez haya datos) |
| F-4 | Sin reranking — orden final es puramente distancia coseno cruda. | HIGH (una vez haya datos) |
| F-5 | **Context assembly descarta metadata real ya disponible** (`title`, `source`, `app_name`, `updated_at` se piden a Django y se tiran antes de llegar al LLM — `sintel_rag_adapter.py:57` solo usa `d["content"]`). Esto es corregible YA, sin depender de que haya contenido real (aunque su beneficio solo se observa con contenido real). | HIGH |
| F-6 | Sin retrieval confidence / answerability score — la única señal es "hay chunks" vs "no hay chunks" (booleano implícito). | MEDIUM (bloqueado por F-1 para medir con datos reales, pero el mecanismo se puede construir ya) |
| F-7 | Sin grounding/claim validation post-generación, y sin test de RAG poisoning con documentos reales insertados (los tests de prompt-injection existentes son estructurales, no inyectan contenido malicioso real en `ai_knowledge`). | MEDIUM |
| F-8 | `detect_apps_from_text()` es un filtro de metadata pre-vectorial real (keyword-substring), pero es un mecanismo de 2026-08 heredado de la era ChromaDB, nunca reevaluado desde la migración a pgvector — podría fallar en producir un buen filtro `app_names` para preguntas de conocimiento genéricas (garantías, políticas) que no mencionan ningún módulo. | LOW |
| F-9 | `AIKnowledgeChunkSelector.count_stale_embeddings()`/`reembed_stale_chunks()` existen (mecanismo de re-embedding tras cambio de modelo) pero no hay ningún documento embebido para ejercitarlos — no probado contra datos reales. | LOW |

---

## 9. Cómo esto reencuadra la misión (sin desviarse de las reglas no negociables)

La Regla 6 de la misión ("No inventar datos. Si una fuente no existe, el sistema debe
reconocerlo") y la Regla de decisión ("CÓDIGO REAL primero") obligan a ser honesto: **las FASE
2-9 del plan original (metadata filtering, hybrid retrieval, reranking, context assembly,
confidence, grounding, memoria, GraphRAG) son arquitectónicamente válidas y se pueden construir
y probar con datos sintéticos/de test — igual que ya hace `ai_knowledge/tests.py` con vectores
deterministas — pero NINGUNA puede evaluarse con datos reales de producción hasta que exista
contenido real ingerido.** Construir el mecanismo no requiere autorización adicional (ya está
cubierto por "cuando exista una mejora técnicamente justificable... procede sin pedir
autorización adicional"); demostrar la mejora con datos de producción sí depende de una decisión
de contenido que no puedo tomar por mi cuenta (qué documentos, qué políticas, qué FAQs reales
publicar — eso es una decisión de negocio, no técnica).

**Plan de ejecución ajustado, dentro del loop de la misión:**
1. FASE 1 (auditoría de datos) — ya respondida arriba: el hallazgo es F-1, no hace falta un
   documento aparte con hallazgos adicionales inventados sobre datos que no existen.
2. Construir las mejoras de pipeline (F-5 en adelante) que sean seguras, reversibles y
   verificables con datos de prueba reales (mismo patrón que los tests existentes) — metadata en
   context assembly, retrieval confidence/answerability, hybrid retrieval (lexical vía
   `pg_trgm`/`SearchVector`, ya sugerido en el propio código), reranking simple, grounding
   check — todo probado con corpus de test controlado, nunca "demostrado" con producción vacía.
3. Dejar explícito en la certificación final que la ganancia real en producción está bloqueada
   por F-1, y que ingerir contenido real es un prerequisito operativo separado (no técnico) para
   que el trabajo de esta misión se traduzca en mejor experiencia de cliente.

---

## Checkpoint 0 — Estado

**PASS.** El RAG real fue inspeccionado de punta a punta contra el código fuente y el estado
real de la base de datos de desarrollo, no contra documentación de sesiones anteriores. Hallazgo
crítico (F-1) registrado. No se ha modificado ninguna arquitectura todavía. Continúa FASE 2 en
adelante con el plan ajustado de la sección 9.
