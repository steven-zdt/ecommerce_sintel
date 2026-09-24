# HARDENING — FASE 6 (RAG: seguridad + calidad)

**Estado: C0-C6 APROBADOS (2026-09-24, corpus sintetico en DEV, monitor primero en cuarentena, alta de contenido solo por Django admin), IMPLEMENTADOS Y VERIFICADOS EN DEV; PRODUCCION SIN DESPLEGAR (incluye una migracion de BD).** Ver "Resultado en DEV" al final.

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §10. Nada implementado. Incluye una migracion de BD
(`ai_knowledge`) y cambios de politica de contenido => `SECURITY_REVIEW_REQUIRED` + aprobacion humana (§0.3, §26.2).

## Estado real (codigo + BD de dev, 2026-09-24)
| Control del plan (§10) | Estado |
|---|---|
| Filtro ANTES del ranking (§10.2) | **OK**: `RetrievalService.retrieve_public_knowledge` filtra `is_deleted`, `is_active`, `visibility=public`, `app_name` sobre el queryset y solo despues aplica coseno/HNSW; la capa exacta usa el mismo queryset filtrado |
| Seguro por defecto | **OK**: `visibility` default `INTERNAL`; ningun documento llega a `/chat` hasta marcarlo `public` |
| Metadata obligatoria (§10.1) | Parcial: hay `title`, `app_name`, `source`, `visibility`, `updated_at`, `embedding_model`/`embedded_at` por chunk. **Faltan** `document_version`, `hash`, `effective_from/until`, `authority`, `classification`/estado de revision |
| Vigencia | Solo como factor de reranking (`_rerank_score` con `updated_at`); **no hay exclusion** de documentos fuera de vigencia |
| Pipeline de ingesta (§10.3: validar->sanear->clasificar->hash->versionar->indexar->evaluar->publicar) | **No existe**: `AIKnowledgeDocumentCommands.upsert_document` guarda el texto tal cual, borra los chunks previos (`document.chunks.all().delete()`) y no conserva la version anterior |
| Answerability (§10.4) | **OK**: `MIN_ANSWERABLE_SIMILARITY` + marcadores `_NO_KNOWLEDGE_MARKER` / `_LOW_CONFIDENCE_MARKER` (ya existia) |
| Dataset dorado (§10.5, 200+ casos) | **Muy corto**: `rag_evaluation/dataset.py` tiene ~8 casos (NO_ANSWER 3, AMBIGUOUS 2, ADVERSARIAL/MULTI_TOPIC/PROMPT_INJECTION 1); y en DEV el corpus esta **vacio** (0 documentos, 0 chunks) |
| Alta de contenido | Solo por Django admin (`ai_knowledge/admin.py`); no hay API ni panel `/panel/*` para documentos |

## Hallazgos adicionales de seguridad
- **H1**: `AiKnowledgeRetrieveView` (`/api/v1/internal/ai/knowledge/retrieve/`) usa `AllowAny`; la unica barrera es la red (nginx bloquea `/api/v1/internal/`, verificado en `nginx-common.conf`) — es la direccion ADK -> Django que quedo fuera de F2 (F2b).
- **H2**: `k = int(request.data.get('k') or 8)` sin tope ni validacion: un `k` enorme fuerza consultas pesadas y un valor no numerico produce 500. Correccion trivial (acotar 1..20, 400 si invalido).
- **H3**: el contenido se puede envenenar en la ingesta (Django admin/manual) y hoy no hay ningun analisis; F5 detecta inyeccion en RETRIEVAL (monitor) pero no al publicar.

## Cambios propuestos (dev primero)

### C0 — Correccion inmediata H2 (riesgo bajo)
Validar `k` (entero 1..20, 400 si no) y `app_names` (lista de strings acotada) en `AiKnowledgeRetrieveView`. Test de regresion.

### C1 — Metadata de gobierno (migracion aditiva, riesgo bajo)
En `AIKnowledgeDocument`: `document_version` (int, +1 por cambio de contenido), `content_hash` (sha256), `effective_from`/`effective_until` (nullable),
`authority` (`official`/`internal`/`third_party`), `review_status` (`draft`/`needs_review`/`approved`), `injection_flags` (JSON). En `AIKnowledgeChunk`: `content_hash`.
Nueva tabla `AIKnowledgeDocumentVersion` (documento, version, contenido, hash, autor, fecha) para historial y rollback. Todas las columnas nuevas nullable/con default:
compatible con produccion sin reescribir datos.

### C2 — Pipeline de ingesta (riesgo medio) — `ai_knowledge/services/ingestion.py`
Etapas dentro de `upsert_document` (misma firma): 1) validar fuente (allowlist: `manual`, rutas bajo el repo, dominios https permitidos; rechazar el resto);
2) sanear (`sanitize_text` de F5 + retirar HTML/`<script>`/atributos `on*`); 3) clasificar (detector de F5: si hay `override_instructions`/`fake_system_message`/`delimiter_forgery`
=> `review_status=needs_review` y NO publicable); 4) hash + deduplicar contra el mismo `content_hash`; 5) versionar (guardar la version previa en `AIKnowledgeDocumentVersion`
antes de rechunkear); 6) indexar (chunks + hash); 7) evaluar (humo: el propio titulo recupera al documento y no dispara banderas); 8) publicar solo por accion explicita
(`visibility=public` + `review_status=approved`). `visibility` por defecto sigue siendo `INTERNAL`.

### C3 — Vigencia como filtro previo (riesgo bajo)
`retrieve_public_knowledge` excluye documentos con `effective_from > ahora` o `effective_until < ahora` (y `review_status != approved`) ANTES de rankear; se conserva el reranking por
`updated_at` para el resto.

### C4 — Cuarentena en retrieval (riesgo medio, primero monitor)
`AI_RAG_QUARANTINE_FLAGGED` (default `false` = solo monitor): al ensamblar el contexto del ADK, los chunks con banderas de F5 (`override_instructions`, `fake_system_message`, `delimiter_forgery`)
se excluyen y se registra `security_event=rag_chunk_quarantined` (sin contenido). Con `true` se aplica. Defensa en profundidad para contenido que llegue sin pasar por C2.

### C5 — Dataset dorado y metricas por componente (riesgo bajo, alcance a acordar)
Ampliar `rag_evaluation` por fases: (a) corpus sintetico publico de prueba en DEV (politicas de garantia, envios, pagos, renting, servicios, WhatsApp — sin datos reales) + 60 casos
segmentados (`general`, `productos`, `pedidos`, `pagos`, `renting`, `servicios`, `envios`, `WhatsApp`, `escalamiento`, `fuera de dominio`, `adversarial`); (b) subir hacia 200+ con los documentos
reales una vez se decida cuales publicar. Metricas: retrieval recall@k, context relevance, faithfulness (ya hay grounding), answer correctness, abstencion correcta. Umbrales SOLO despues
de medir el baseline (§14.3). Nota: sin corpus real el resultado mide el mecanismo, no la calidad del contenido de produccion.

### C6 — Version de embeddings (riesgo bajo)
Chequeo de arranque/health que avise si `count_stale_embeddings` > 0 (mezcla de modelos en la misma columna). Hoy consistente: `bge-m3` / 1024 dim.

## Tests
C0 (k invalido/enorme), C1 (migracion aplica y revierte; versionado incrementa y conserva la anterior), C2 (fuente rechazada, HTML saneado, documento con inyeccion => `needs_review` no
recuperable, duplicado detectado, publicacion explicita), C3 (fuera de vigencia no se recupera), C4 (cuarentena solo con flag), C5 (harness mide recall/abstencion sobre el corpus sintetico),
C6 (aviso de stale). Regresion: suites `ai_knowledge` (Django) y del ADK sin cambios de resultado.

## Riesgos / rollback
La migracion toca `ai_knowledge` en produccion (aditiva): probar en dev y con un backup previo. `review_status` obliga a re-aprobar documentos ya publicados: valor por defecto `approved`
para lo existente (no cambia su comportamiento). Rollback: revertir la migracion y los flags (`AI_RAG_QUARANTINE_FLAGGED=false`).

## Preguntas para aprobar
1. ¿Apruebas C0-C4 y C6 (dev primero), incluida la migracion aditiva de `ai_knowledge`?
2. C5: ¿corpus sintetico en DEV para medir el mecanismo, y despues los documentos reales? ¿Que documentos de produccion estan hoy publicados (`visibility=public`)? No puedo consultarlo sin tocar la BD de produccion.
3. C4: ¿monitor primero y cuarentena activa solo tras observar falsos positivos?
4. Alta de contenido: ¿quieres solo Django admin, o una vista `/panel/*` + API (fuera de este alcance, otra fase)?

## Resultado en DEV (2026-09-24)
Implementado: migracion aditiva `ai_knowledge/migrations/0002_governance_metadata_and_versions.py` (sin DROP/DELETE; `manage.py makemigrations --check` limpio);
`services/ingestion.py` (validar fuente, sanear, clasificar con el detector de F5 importado de `ai_engine_adk.input_guard`, hash); `commands.py`
(`upsert_document` con el pipeline + dedupe por hash + versionado, `approve_document`, `publish_document`, `rollback_to_version`); `selectors.py` (filtro previo por
`review_status=approved` y vigencia; aviso `embedding_model_mismatch`); `api/views.py` (validacion de `k` 1..20 y `app_names`);
`ai_engine_adk/sintel_rag_adapter.py` (cuarentena de chunks, `AI_RAG_QUARANTINE_FLAGGED=false` = monitor); `eval_data.py` + `manage.py rag_eval` (corpus SINTETICO, solo DEBUG);
setting `AI_KNOWLEDGE_ALLOWED_SOURCE_HOSTS`.
Cambio de contrato deliberado: `ai_knowledge/tests.py::RAGPoisoningRetrievalTests` afirmaba que un documento publico malicioso era recuperable (y avisaba de un cambio de
contrato si alguien agregaba un filtro); ahora la INGESTA lo pone en `needs_review`/interno y no se recupera. El test se reescribio con esa explicacion.
Tests: Django `ai_knowledge` 26 -> 45 (`test_hardening.py`: C0 endpoint, C1 versionado/dedupe/rollback, C2 fuentes/saneo/inyeccion/aprobacion/publicacion, C3 vigencia, C6 mezcla de
embeddings); ADK `test_rag_quarantine.py` (5). Regresion ADK: 31 fallos identicos a la linea base (preexistentes), 154 -> 159 aprobados.
Medicion (`manage.py rag_eval`, embeddings reales `bge-m3` en dev, 12 docs sinteticos, 48 consultas de dominio + 12 fuera de dominio + 4 adversariales, k=5):
recall@1 0.938 | recall@3 0.979 | recall@5 0.979 | MRR 0.958 | falsa abstencion 0.0 | abstencion fuera de dominio 5/12 | adversariales 1/4.
Similitud top-1: dominio mediana 0.643, min 0.403, p10 0.505; fuera de dominio mediana 0.353, max 0.435; adversarial max 0.462.
Hallazgo: `MIN_ANSWERABLE_SIMILARITY=0.35` no separa dominio de fuera de dominio en este corpus (rangos solapados 0.403-0.435): un umbral unico de coseno no basta; calibrar con
documentos REALES y apoyarse en el grounding (F0/RAG-POST2) en vez de subirlo a ciegas. No se cambio el umbral. Misses top-1: 3 de 48 (escalamiento x2, cotizaciones x1).
Limites: el corpus es inventado y corto (mide el mecanismo, no la calidad del contenido real); el dataset dorado de 200+ casos requiere los documentos publicados en produccion (no consultables
sin tocar su BD); faithfulness/answer-correctness end-to-end con LLM no se midieron aqui (ver `rag_evaluation`, que necesita el modelo).

## Pasos pendientes para PRODUCCION (no ejecutados)
1. Backup de BD y despliegue de `django` (aplica `ai_knowledge.0002`, aditiva); rebuild de `sintel_ai_adk` (cuarentena en monitor). 2. Revisar los documentos ya publicados: quedan
`approved` por defecto; pasar el detector sobre ellos (re-guardar) para ver cuales quedarian `needs_review`. 3. Observar `rag_chunk_quarantined` y luego decidir `AI_RAG_QUARANTINE_FLAGGED=true`.
4. Rollback: `manage.py migrate ai_knowledge 0001` (elimina columnas y la tabla de versiones), flags a `false`, imagen anterior.
