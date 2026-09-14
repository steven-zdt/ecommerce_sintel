# ARCHITECTURE_SIMPLIFICATION_AUDIT.md — FASE 0

**Fecha:** 2026-09-14. Mision: "Depuracion y consolidacion arquitectonica de Sintel"
(eliminar ChromaDB, migrar RAG a PostgreSQL+pgvector, reducir infraestructura/codigo
redundante). Este documento es FASE 0 — auditoria de solo lectura, cero codigo modificado.
Metodologia: 3 investigaciones en paralelo (docker/BD, dependencias/config/codigo muerto,
mapa de duplicacion de AI Engine + endpoints + tools) contra el codigo real en
`ecommerce_sintel/`, mas verificacion en vivo contra los contenedores corriendo.

## 0. Dos desviaciones del prompt original frente al codigo real (bloqueantes, ya resueltas con el usuario)

1. **No existe infraestructura multi-tenant en este repo** (`django_tenants`, `TenantProfile`,
   schema-per-tenant: cero coincidencias). Sintel es de instalacion unica por negocio, decision
   deliberada y documentada (`AUDITORIA/WHITE_LABEL/WHITE_LABEL_DECISION_RECORD.md`, Decision 2,
   2026-08-14), reconfirmada en vivo por el usuario en esta sesion ("no apliques multitenant a
   este proyecto"). **Toda la seccion 6 del prompt original (aislamiento cross-tenant, tests de
   sede/area) queda fuera de alcance — no se adapta, se ignora.**
2. **No existe ninguna pieza de la arquitectura objetivo que el prompt asume ya construida.**
   `pgvector`, `AIKnowledgeDocument`, `AIKnowledgeChunk`, `RetrievalService`, `EmbeddingService`,
   `AIEmbeddingProvider`, `apps/tenant/ai_knowledge/`, `apps/services/ai/` — cero coincidencias
   en todo el repo. Esto no es "migrar entre dos sistemas existentes", es **construir desde cero**
   el reemplazo antes de poder retirar Chroma. Confirmado con el usuario: se trata como build
   nuevo, no como refactor menor. Los paths reales de este proyecto son `ecommerce_sintel/ai_engine/`
   (chatbot + RAG) y `ecommerce_sintel/ai_provider/` (config de proveedores LLM, ya construido
   2026-08-31, no relacionado con el vector store).

## 1. Vector store — ChromaDB (seccion 3-4 del prompt)

**Uso real, no residual.** `ai_engine/vectorstore_factory.py` importa `chromadb` y
`langchain_chroma.Chroma` directamente; `CHROMA_HOST/PORT/AUTH_TOKEN/COLLECTION_NAME`
(`ai_engine/config.py:33-36`) alimentan un `HttpClient`. El pipeline de ingestion real es
`ai_engine/bootstrap.py` (script manual, `docker exec ... python bootstrap.py`, nunca
automatizado): `loaders.load_all_documents` -> `splitters.split_all` ->
`embeddings_factory.get_embeddings` -> `vectorstore_factory.get_vectorstore` ->
`vectorstore.add_documents`. **Este es el archivo de referencia para la migracion.**

**Pero el impacto de eliminarlo es mucho menor de lo que el prompt asume:**
- El servicio Docker `sintel_chromadb` existe **solo en dev** (`docker-compose.yml`); no esta
  en `docker-compose.prod.yml`.
- **La coleccion real `sintel_kb` tiene 0 documentos** (verificado en vivo contra el contenedor
  corriendo: `GET /api/v1/collections/.../count` -> `0`). Nunca se corrio `bootstrap.py` con
  contenido real indexado, o se limpio. No hay migracion de datos que planificar (seccion 5 del
  prompt queda trivial: 0 documentos, 0 chunks, 0 metadata que exportar).
- **En produccion, `sintel_ai` ya apunta `CHROMA_HOST=sintel_chromadb` a un host que no existe**
  en `docker-compose.prod.yml` — el RAG ya esta degradado en produccion hoy, silenciosamente
  (`retrievers.py::retrieve_knowledge_for_chat` se degrada con gracia si Chroma es inalcanzable).
  Retirar Chroma no cambia el comportamiento observable de produccion.
- Ninguna variable `CHROMA_*`/`EMBEDDING_*`/`RAG_*` esta en `.env.production.example` — el
  feature nunca se aprovisiono para produccion.

**Conclusion FASE 0 sobre el vector store:** el riesgo de "romper produccion" al retirar Chroma
es minimo (ya esta efectivamente apagado ahi). El trabajo real es 100% hacia adelante: construir
`AIKnowledgeDocument`/`AIKnowledgeChunk`/`EmbeddingService`/`RetrievalService` sobre pgvector,
validarlos con contenido real indexado (ya que hoy no hay ninguno que migrar), y solo entonces
apagar Chroma.

## 2. Bases de datos (seccion 8)

**Una unica base de datos persistente y genuinamente usada: PostgreSQL 16** (dev y prod).
`db.sqlite3` en la raiz de `ecommerce_sintel/` **pesa 0 bytes** — es el fallback de
`development.py` para el caso "sin Docker, sin `DB_HOST`", camino que este proyecto no usa
(`notas.txt`/`COMANDOS.txt` asumen Docker siempre). No es una segunda base de datos con datos
reales, es peso muerto documentable. Cero coincidencias de MySQL/MongoDB/Neo4j/Qdrant/FAISS en
todo el repo. `project_knowledge_graph/` es 100% basado en archivos JSON (su propio `data/`,
~57MB), no habla con ninguna base de datos.

**Conclusion:** no hay "dos bases de datos" que consolidar en el sentido que el prompt
sugiere — ya hay una sola. El unico segundo almacen con estado real es Chroma (seccion 1).

## 3. Servicios Docker (seccion 9)

13 servicios entre `docker-compose.yml` (dev) y `docker-compose.prod.yml` (prod). Sin
duplicados de responsabilidad (un solo Postgres, un solo Redis por entorno). Clasificacion:

| Servicio | Clase | Nota |
|---|---|---|
| `db` (Postgres 16) | CORE | unico en cada entorno |
| `redis` | CACHE/CORE | prod con `requirepass` (fix ya commiteado esta sesion) |
| `django`, `celery_worker`, `celery_beat` | CORE/ASYNC | misma imagen, tag `prod-runtime` exclusivo en prod |
| `nginx` | INFRA | prod-only expone 80/443 internos, tunel via cloudflared |
| `cloudflared` | INFRA | **prod-only**, unico camino de ingreso |
| `frontend` (Vite) | DEV-ONLY | prod hornea el bundle en la imagen Django, sin duplicar pipeline |
| `sintel_ollama` | AI / DEV-ONLY | prod usa LM Studio externo (`LOCAL_MODEL_CHAIN`, decision 2026-08-17), no Ollama |
| `sintel_chromadb` | AI / **objetivo de eliminacion** | dev-only, coleccion vacia (seccion 1) |
| `sintel_ai` (ai_engine) | AI | unico servicio AI Engine; en prod corre con RAG ya degradado |

**Conclusion:** no hay servicios "duplicados" que consolidar mas alla de Chroma mismo. El
inventario esta limpio — cada servicio tiene una responsabilidad y consumidores reales.

## 4. AI Engine — mapa de duplicacion (seccion 10) — HALLAZGO PRINCIPAL DE ESTA FASE

`ai_engine/main.py` expone **16 rutas FastAPI**, pero solo **2 tienen algun consumidor real**:
`POST /chat` (unico endpoint que Django llama, via `support/services/ai_bridge.py`) y
`GET /health`. Las otras **14 rutas alimentan un segundo pipeline completo, "Engineering
Agent" / generador de codigo, que quedo huerfano y sin retirar tras la Fase 0 de desacople
del Knowledge Graph (2026-08-10, `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md`) y la
construccion posterior de `ai_editor/` + `project_knowledge_graph/` (commiteados en esta
misma sesion) como su reemplazo real:**

```
Flujo VIVO (el unico que Django usa):
  ai_bridge.py --POST /chat--> main.py:chat()
    -> llm_factory.get_dynamic_llm()
    -> action_graph.py:run_action_chat()   [923 lineas]
         -> retrievers.py:retrieve_knowledge_for_chat()  [linea 184, unica funcion viva del archivo]
         -> tools/*.py -> http_bridge.py -> Django /api/v1/internal/ai/*
```

```
Flujo MUERTO (huerfano, cero consumidores fuera de main.py):
  main.py: /generate /validate /plan /impact /breakage /refresh
           /graph/node /graph/impact /search /indices /manifest/{app} /memory /ingest
    -> graph.py (220 li­neas) -> chains.py (110) + chains_frontend.py (260)
    -> guardrails.py (302) + guardrails_frontend.py (238)
    -> planner.py (376)
    -> specialized_retrieval.py (446)  [NO usado por action_graph.py]
    -> memory_builder.py (550)          [NO usado por action_graph.py]
```

**Evidencia de "cero consumidores":** grep de `/generate`, `/plan`, `/impact`, `/breakage`,
`/refresh`, `/search`, `/indices`, `/manifest/`, `/memory`, `/ingest` en todo `.py`/`.js`/`.vue`
del repo, excluyendo `main.py` mismo -> 0 resultados. `/graph/node` y `/graph/impact` ya son
stubs explicitos `HTTPException(501, "Retirado...")` desde la Fase 0 de 2026-08-10 (documentado
en su momento, nunca completado con la eliminacion real). `/impact`/`/breakage` llaman
funciones locales (`main.py:51-67`) que devuelven estructuras vacias incondicionalmente.

**Tamano del bloque muerto:** ~1,952 lineas entre `graph.py` + `chains.py` +
`chains_frontend.py` + `guardrails.py` + `guardrails_frontend.py` + `planner.py` +
`specialized_retrieval.py` + `memory_builder.py`, mas 14 rutas FastAPI y sus schemas Pydantic
asociados en `main.py`.

`retrievers.py` requiere triage a nivel de funcion, no de archivo: `retrieve_knowledge_for_chat`
(linea 184) esta viva; `retrieve_context_for_task`, `build_ensemble_retriever`,
`retrieve_context_for_frontend_task`, `detect_task_type`, `detect_apps_from_text` solo son
alcanzables desde el cluster muerto de arriba.

**No hay otras duplicaciones reales:** `llm_factory.py` (LLM) y `embeddings_factory.py`
(embeddings) son fabricas unicas sin bifurcar. `chains.py` vs `chains_frontend.py` no son
duplicados entre si (editor vs. frontend, ambos parte del mismo cluster muerto).

## 5. Endpoints internos `/api/v1/internal/ai/*` (seccion 15)

**34 rutas** (no exactamente 31, cercano) en `ecommerce/internal_ai_urls.py`, sobre 12 apps.
**Corrección de encuadre respecto al prompt:** estas NO son candidatas a "Tool -> selector
directo" (seccion 14) porque `ai_engine` corre como **proceso separado** (FastAPI, puerto 8100,
contenedor propio) — no puede importar un selector de Django in-process. `http_bridge.py`
documenta explicitamente ser "el UNICO lugar donde las Tools hacen HTTP". Cada endpoint
muestreado es una fachada fina sobre un Selector/Command existente **por diseno correcto**, no
por descuido: agrega paso de JWT, chequeo de permisos, auditoria via `SecurityEvent` en
escrituras. **Clasificacion: las 34 rutas -> KEEP.** El bloat real esta en la seccion 4
(`main.py`), no aqui.

## 6. Tools de `ai_engine/tools/` (seccion 14)

~29-31 tools registradas en un unico registry (`registry.py`, con guard anti-duplicado),
cada una con `ToolMetadata` (permisos/riesgo/side_effects/confirmacion) + una llamada a
`http_bridge.py`. Sin wrappers triviales, sin tools duplicadas, sin bypass del bridge. Capa
limpia, sin cambios recomendados.

## 7. Dependencias (seccion 18)

**Django (`pyproject.toml`):** cero dependencias chroma/langchain/vector/neo4j/networkx —
separacion limpia, todo el stack RAG vive en el microservicio `ai_engine`, no en Django.

**`ai_engine/requirements.txt`:** todas las dependencias langchain*/chromadb/rank-bm25/
unstructured tienen consumidor real verificado (import directo o transitivo confirmado, ver
tabla completa del sub-informe). **Cero dependencias huerfanas** — el `requirements.txt` no
tiene grasa hoy; la tendra despues de retirar el cluster muerto de la seccion 4 (langchain-chroma,
chromadb, y posiblemente rank-bm25/unstructured si sus unicos consumidores viven en el codigo
muerto — pendiente confirmar en FASE 4/7).

## 8. Configuracion (seccion 17)

11 variables `CHROMA_*`/`EMBEDDING_*`/`RAG_*`-adyacentes en `ai_engine/config.py`, todas con
consumidor real. Ninguna esta en `.env.production.example` (ver seccion 1). Ninguna variable
"definida pero nunca leida" encontrada.

## 9. Codigo muerto — resumen consolidado

| Elemento | Lineas | Consumidores reales | Accion FASE 4/5 |
|---|---|---|---|
| `graph.py`, `chains.py`, `chains_frontend.py`, `guardrails.py`, `guardrails_frontend.py`, `planner.py` | 1,506 | 0 (solo `main.py`, que es huerfano el mismo) | ELIMINAR |
| `specialized_retrieval.py` | 446 | 0 (no lo importa `action_graph.py`) | ELIMINAR |
| `memory_builder.py` | 550 | 0 (idem) | ELIMINAR |
| 14 rutas FastAPI en `main.py` (`/generate` ... `/ingest`) | — | 0 externos | ELIMINAR |
| Funciones muertas dentro de `retrievers.py` | parcial del archivo | 0 (solo desde el cluster de arriba) | ELIMINAR (funcion por funcion, `retrieve_knowledge_for_chat` se queda) |
| `db.sqlite3` (0 bytes) | — | fallback no usado | documentar como vestigial o eliminar el archivo (no el fallback de settings, que es legitimo) |
| `project_knowledge_graph/data/` (~57MB generado) | — | regenerable via CLI propio | **decision pendiente del usuario** (gitignore vs. commitear vs. dejar como esta — pausada la sesion anterior) |

## 10. Riesgos identificados para las fases siguientes

1. **Falso sentido de urgencia en la migracion de datos** (seccion 5 del prompt): con 0
   documentos en Chroma, no hay backup/checksum/conteo que hacer — pero esto tambien significa
   que **nadie ha validado el RAG con contenido real todavia**. La FASE 1-2 (pgvector) debe
   incluir cargar contenido real y validar calidad de retrieval antes de considerar el feature
   "migrado", no solo mover infraestructura vacia.
2. **`rank-bm25`/`unstructured` podrian quedar huerfanas** tras eliminar el cluster muerto si
   sus unicos consumidores (via `langchain_community`) resultan ser funciones del cluster
   muerto de `retrievers.py`/`specialized_retrieval.py` — confirmar en FASE 4, no asumir ahora.
3. **`ai_editor/`/`project_knowledge_graph/` ya cubren el proposito original del cluster
   muerto** (analisis de impacto, blast radius, planificacion de cambios) con una arquitectura
   mas nueva y ya certificada (FASE61). Eliminar el cluster muerto de `ai_engine` no pierde
   capacidad real — la capacidad real ya vive en otro lado desde antes.
4. **Ningun endpoint interno de Django debe tocarse** en esta mision — estan bien disenados
   (seccion 5). Cualquier "reduccion de endpoints" debe enfocarse exclusivamente en las 14
   rutas muertas de `ai_engine/main.py`, no en `internal_ai_urls.py`.

## 11. Orden de ejecucion recomendado (ajuste sobre la seccion 26 del prompt)

Dado que el hallazgo principal es un cluster de codigo muerto sin relacion directa con Chroma
(mas grande en volumen que el propio vectorstore), se recomienda invertir el orden de dos
fases del prompt original:

1. **FASE 4a (adelantada, antes que pgvector): eliminar el cluster "Engineering Agent" muerto**
   de `ai_engine` (seccion 4/9 de este documento) — riesgo casi nulo (cero consumidores
   verificados), gana ~2,500 lineas de simplificacion inmediata, sin depender de que pgvector
   exista todavia.
2. **FASE 1-2: construir pgvector + EmbeddingService + RetrievalService desde cero**, validar
   con contenido real indexado (no hay nada que migrar de Chroma, seccion 1).
3. **FASE 3: cambiar `action_graph.py`/`retrievers.retrieve_knowledge_for_chat` para usar el
   nuevo RetrievalService.**
4. **FASE 4b: retirar Chroma** (servicio Docker, dependencias, config) — impacto en produccion
   ya es minimo (seccion 1).
5. FASE 6-9 del prompt original sin cambios (documentacion, validacion final) salvo que la
   seccion 6 (multi-tenant) se omite por completo (seccion 0 de este documento).

---

## 12. Cierre de la mision (2026-09-14)

Todas las fases se ejecutaron con aprobacion explicita del usuario en cada paso ("si procede"
/ "procede" / "si" / "decide y continua"). Commits en `fix/audit-p0-remediation`:

| Fase | Commit | Resultado |
|---|---|---|
| 0 — Auditoria | (este documento) | Sin cambios de codigo |
| 4a — Cluster muerto de codegen | `cf50009` | -1,900 lineas (6 modulos + 7 endpoints) |
| 1 — pgvector desde cero | `aa3dd41` | App `ai_knowledge` nueva, `CREATE EXTENSION vector`, imagen `pgvector/pgvector:pg16` |
| 3 — Consumidores a RetrievalService | `9957179` | `retrieve_knowledge_for_chat` ya no toca Chroma |
| 4b — Retiro de ChromaDB | `ae45755` | Servicio Docker + 5 modulos + dependencias + config, todo retirado |
| 5 — Resto del tooling huerfano + decisiones abiertas | `f3c8638` | -142,684 lineas (4 modulos mas + artefactos JSON generados), `project_knowledge_graph/data/` gitignorado, contenido de prueba fabricado eliminado de la BD |

**Estado final verificado en vivo:**
- `docker ps -a` / `docker volume ls`: cero rastro de ChromaDB en el proyecto.
- Arranque de `sintel_ai`: de ~2.5 min (escaneo completo del codebase en cada arranque) a
  **menos de 1 segundo** (el lifespan ya no pre-construye nada salvo el cliente LLM).
- `main.py` pasa de 16 rutas FastAPI a **2** (`/chat`, `/health`) + el AI Gateway
  (`/api/v1/ai/*`, MCP de Meta Ads, feature vigente y sin tocar).
- Suite de tests de `ai_engine`: 162 passed / 16 skipped / 0 failed.
- RAG validado end-to-end contra pgvector real (embeddings via Ollama/bge-m3 en dev),
  incluyendo la llamada real contenedor-a-contenedor `ai_engine -> Django -> Postgres`.

**Pendiente, fuera del alcance de esta mision (no son decisiones tecnicas mias):**
- Contenido publico real para el RAG (FAQs/politicas de Sintel) -- hoy la tabla
  `ai_knowledge.AIKnowledgeDocument` esta vacia a proposito, el documento de prueba fabricado
  durante la validacion se elimino explicitamente para no dejar contenido ficticio sin marcar
  como tal en un sistema que puede llegar a hablarle a un cliente real.
- Activar `AI_SUPPORT_CHAT_ENABLED`/el canal de embeddings en produccion -- sigue en `false`,
  decision de negocio explicita ya documentada en commits anteriores a esta mision.
