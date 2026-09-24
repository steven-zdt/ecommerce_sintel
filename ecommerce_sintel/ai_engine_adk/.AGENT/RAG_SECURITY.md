# RAG_SECURITY — seguridad del conocimiento (RAG) y de la memoria del cliente

> Documento vivo (HARDENING F19, 2026-09-24). Código: `ai_knowledge/` (modelos, `services/{ingestion,commands,selectors}.py`, `eval_data.py`, `management/commands/rag_eval.py`), `ai_engine_adk/sintel_rag_adapter.py`, `customer_memory/`, `ai_engine_adk/customer_memory_adapter.py`.

## 1. Conocimiento documental (F6)
- **Pipeline de ingesta** (`ingestion.py`): fuentes permitidas (https a `AI_KNOWLEDGE_ALLOWED_SOURCE_HOSTS` o rutas relativas; se rechazan http, `..`, `file://`, hosts ajenos), saneo de HTML/invisibles, chunking, hash de contenido y dedupe.
- **Revisión humana**: un documento con banderas de inyección queda `needs_review` e `internal` aunque pidan `public`; **aprobar NO publica**; publicar es un paso aparte. Versionado con `AIKnowledgeDocumentVersion` y `rollback_to_version` (no borra historial).
- **Recuperación** (`RetrievalService`): solo `approved` + vigentes (`effective_from/until`) + visibilidad; aviso `embedding_model_mismatch` si hay chunks de otro modelo de embeddings. Endpoint interno valida `k` (1–20) y `app_names`.
- **Cuarentena en el ADK**: chunks con `override_instructions`/`fake_system_message`/`delimiter_forgery` -> monitor por defecto (`rag_chunk_quarantined`); `AI_RAG_QUARANTINE_FLAGGED=true` los excluye. Los chunks siempre viajan **cercados** como datos no confiables (`input_guard.protect_block`).
- **Answerability**: sin evidencia o similitud < `MIN_ANSWERABLE_SIMILARITY=0.35` -> marcador «NINGUNO» (el modelo no improvisa). Hallazgo abierto: 0.35 no separa bien dentro/fuera de dominio (corpus sintético: mín. dentro 0.403, máx. fuera 0.435).
- **RAG caído** = retriever devuelve `[]` = «sin evidencia» (respuesta honesta, pero indistinguible en métricas de «no hay documento»; pendiente log `rag_unavailable`).
- Evaluación: `manage.py rag_eval` (corpus sintético `eval_data.py`).

## 2. Memoria del cliente (F7)
- **Solo del cliente y solo de su propio turno nuevo**: `should_extract_memory` es falso para `source=admin`, reanudaciones, sin respuesta o mensaje marcado como inyección; nunca lee RAG ni salidas de tools.
- **Barrera server-side** (`customer_memory/services/policy.py`): rechaza vacío, categoría inválida, autoridad/instrucciones y datos sensibles; TTL por categoría (365/180 días); auditoría `memory_event=`; `forget_customer_memory` y `purge_expired_memories`; UI `/mi-cuenta/memoria-asistente` (API `/api/v1/customer-memory/`).
- La memoria recuperada se presenta como **informativa, nunca instrucción**, en sección separada del RAG.
- El canal (web/whatsapp) solo atribuye el origen del recuerdo.

## 3. Controles transversales
Cerca de datos no confiables + `PRECEDENCE_POLICY`; permisos de tools independientes del contenido; guardia de salida; logs sin contenido.

## 4. Reglas de cambio
Cualquier cambio de RAG, embedding, retriever, reranker (hoy inexistente) o política de memoria => actualizar este documento, `tests/security/test_rag_poisoning.py` / `test_memory_poisoning.py`, y **re-correr F10** (regression gate). Documentos nuevos entran por el pipeline (nunca insert directo). Alta masiva: revisar la cola `needs_review` antes de publicar.

## 5. Riesgos residuales
`ai_knowledge` sin contenido real hasta que se cargue (F-1 de la auditoría previa); `detect_apps_from_text` con keywords incompletas; sin endpoint de ingesta admin; detección de chunks no cubre codificaciones (base64) — los contiene la cerca; sin ejecución de RAG real con BD en el nivel 1 de F10.
