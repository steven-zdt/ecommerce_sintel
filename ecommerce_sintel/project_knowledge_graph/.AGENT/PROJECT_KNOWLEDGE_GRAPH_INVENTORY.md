# Project Knowledge Graph — Inventario Físico

> Fase 1 del `PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH` (2026-08-08). Auditoría
> real del checkout (no la lista de ejemplo del plan) — cada import verificado con grep,
> no asumido. Este documento es el prerrequisito obligatorio antes de mover un solo
> archivo, tal como el propio plan lo exige en su Fase 25.
>
> **Alcance de la búsqueda**: todo `ecommerce_sintel/` (no solo `ai_engine/`) — **cero
> consumidores fuera de `ai_engine/`** confirmados. Django, frontend y el resto del
> proyecto nunca importan estos módulos Python ni tocan estos JSON directamente; el
> único puente hacia el exterior es HTTP (`/graph/*`, `/impact`, `/plan`, `/breakage`,
> etc. en `main.py`), y de esos, **solo `/chat` tiene un consumidor real** (Django,
> `AI_ENGINE_URL`) — el resto son herramientas de desarrollo sin caller automatizado
> (ver `AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md` seccion 1, ya confirmado en la
> auditoría anterior de hoy).

## 1. Matriz de archivos

| Archivo | Responsabilidad | Importado por (Python) | Lee (runtime) | Genera | Destino |
|---|---|---|---|---|---|
| `project_map.py` | Consulta `PROJECT_MAP.json` (`build_impact_report`, `build_impact_context`, `find_affected_apps`) | `graph.py`, `main.py` (`/impact`,`/plan`), `planner.py` | `PROJECT_MAP.json` | — | `project_knowledge_graph/project_map/` |
| `knowledge_graph.py` | Construye `KNOWLEDGE_GRAPH.json` desde `PROJECT_MAP.json`; orquesta el enriquecimiento con la familia Graphify | `dependency_graph.py`, `auditor.py` (dinámico), `incremental_updater.py` (dinámico), `main.py` (dinámico, `/graph/node`,`/graph/impact`), `tools/graph_tools.py` | `PROJECT_MAP.json` | `KNOWLEDGE_GRAPH.json` | `project_knowledge_graph/knowledge_graph/` |
| `dependency_graph.py` | Blast radius / impacto transitivo desde `KNOWLEDGE_GRAPH.json` | `auditor.py` (dinámico), `incremental_updater.py` (dinámico), `main.py` (`/breakage`), `planner.py`, `tools/graph_tools.py` | `KNOWLEDGE_GRAPH.json` (via `get_knowledge_graph()`) | `DEPENDENCY_GRAPH.json` | `project_knowledge_graph/dependency_graph/` |
| `incremental_updater.py` | Detecta archivos cambiados por hash, re-audita solo lo afectado | `auditor.py` (dinámico, reutiliza **funciones privadas**: `_detect_via_hashes`, `_save_hash_db`, `_collect_app_files`, `_collect_frontend_files`, `_hash_file`, `HASH_DB_PATH`, `DJANGO_APPS`, `BASE_DIR` — acoplamiento real, no solo conceptual), `main.py` (`/refresh`,`/refresh/detect`) | `.file_hashes.json` | Dispara rebuild de KG/DG/memory/manifests | `project_knowledge_graph/incremental/` |
| `auditor.py` | Pipeline que genera `PROJECT_MAP.json` y encadena KG/DG/memory/manifests/gobernanza | `incremental_updater.py` (dinámico, importa `auditor` completo) | Codebase fuente (AST) | `PROJECT_MAP.json` + dispara KG/DG/memory/manifests | **Dividir** — ver seccion 3 |
| `agent_graph.py` (Graphify) | Nodos `Agent` en el KG, desde `agents/profiles/*.yaml` | `knowledge_graph.py` (dinámico) | `agents/profiles/*.yaml` | Enriquece KG en memoria | `project_knowledge_graph/knowledge_graph/` (sub-builder) |
| `docker_graph.py` (Graphify) | Nodos `DockerService` en el KG, desde `docker-compose.yml` | `knowledge_graph.py` (dinámico) | `docker-compose.yml` | Enriquece KG en memoria | `project_knowledge_graph/knowledge_graph/` (sub-builder) |
| `documentation_graph.py` (Graphify) | Nodos `Documentation` en el KG, desde archivos `.md` | `knowledge_graph.py` (dinámico), `main.py` (`/refresh`) | Árbol de docs `.md` | Enriquece KG en memoria; índice standalone | `project_knowledge_graph/knowledge_graph/` (sub-builder) |
| `graph_validator.py` (Graphify) | Validaciones automáticas de gobernanza sobre el KG | `auditor.py` (dinámico), `main.py` (`/refresh`, dinámico) | `KNOWLEDGE_GRAPH.json` | `GRAPH_VALIDATION_REPORT.json` | `project_knowledge_graph/audit/` |
| `graph_visualizer.py` (Graphify) | Exporta el KG a HTML navegable | `auditor.py` (dinámico) | `KNOWLEDGE_GRAPH.json` | `GRAPH_VIEW.html` | `project_knowledge_graph/snapshots/` o similar (visualización, no núcleo) |
| `tools/graph_tools.py` (`GraphImpactAnalysisTool`) | Única Tool de `/chat` que toca el grafo — capability `analizar_impacto_arquitectura`, `AdminAgent`, `IsAdminUser` | — (es el consumidor final) | `dependency_graph.py`, `knowledge_graph.py` | — | Permanece en `ai_engine/tools/` pero pasa a importar `project_knowledge_graph` en vez de los módulos locales (Fase 17 del plan) |
| `ai_manifest.py` | Genera `AI_MANIFESTS/*.json` desde `PROJECT_MAP.json` | `main.py` (`/manifest`), `auditor.py` | `PROJECT_MAP.json` | `AI_MANIFESTS/*.json` | **No mover** — artefacto derivado (Fase 19 del plan), se queda en `ai_engine` o pasa a consumir la API nueva |
| `memory_builder.py` | Genera `GLOBAL_MEMORY.json`/`APP_MEMORY/*.json` | `planner.py`, `main.py` (`/memory`) | `PROJECT_MAP.json` | `GLOBAL_MEMORY.json`, `APP_MEMORY/*.json` | **No mover** — mismo criterio que `ai_manifest.py` |
| `specialized_retrieval.py` | 9 índices especializados (Model/Serializer/ViewSet/...) para `/search` | `main.py` (`/search`,`/indices`) | `PROJECT_MAP.json` (indirecto, via docs ya cargados) | Índices en memoria | **No mover** — es RAG de código para `/generate`, no el grafo estructural en sí (aunque lee `PROJECT_MAP.json`, ver nota) |

## 2. Corrección a un supuesto del plan

El plan asume una relación bidireccional entre `knowledge_graph.py` y la familia
Graphify ("agent_graph/docker_graph/documentation_graph"). **Verificado: es
unidireccional.** `knowledge_graph.py` importa dinámicamente a los 3 (dentro de su
función de build, para enriquecer el grafo); ninguno de los 3 importa de vuelta a
`knowledge_graph.py` — solo lo mencionan en comentarios/docstrings. No hay ciclo de
imports ahí.

**Sí hay un acoplamiento real y más preocupante** entre `auditor.py` e
`incremental_updater.py`: `auditor.py` importa **funciones privadas** (prefijo `_`) de
`incremental_updater.py` para su propio flujo interno (línea 1026), mientras
`incremental_updater.py` importa `auditor` completo para detectar cambios. Esto es
exactamente el tipo de acoplamiento que la Fase 8 del plan ("dividir el auditor") busca
resolver — no es solo que "auditor.py hace demasiado", es que dos módulos se filtran
internals mutuamente.

## 3. JSON leídos directamente (sin pasar por una API Python)

Confirmado que **10 archivos** leen `PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/
`DEPENDENCY_GRAPH.json` directamente vía `open()`/`json.load()`, no via una función de
consulta encapsulada: `ai_manifest.py`, `auditor.py`, `dependency_graph.py`,
`graph_validator.py`, `graph_visualizer.py`, `incremental_updater.py`,
`knowledge_graph.py`, `memory_builder.py`, `project_map.py`, `specialized_retrieval.py`.
Esto confirma el diagnóstico de la Fase 14 del plan ("no usar JSON como API interna") —
es un problema real, no hipotético.

## 4. Hallazgo adicional no anticipado por el plan: la ingesta RAG también depende de `CODEBASE_PATH`

No es parte del alcance de este módulo, pero relevante para no romper nada al mover: la
ingesta de RAG (`bootstrap.py`/`loaders.py`) lee el código fuente completo del proyecto
vía `CODEBASE_PATH`, igual que `auditor.py` (via AST). Son dos escáneres independientes
del mismo codebase con propósitos distintos — separar `auditor.py` no debe tocar
`bootstrap.py`/`loaders.py`, que ya están fuera de alcance del grafo (Fase 20 del plan lo
confirma explícitamente: RAG queda fuera).

## 5. Endpoints HTTP ligados a estos módulos (`main.py`)

| Endpoint | Módulo(s) detrás | Consumidor real |
|---|---|---|
| `POST /impact`, `POST /plan` | `project_map.py`, `dependency_graph.py` | Ninguno automatizado — herramienta de desarrollo |
| `POST /breakage` | `dependency_graph.py` | Ninguno automatizado |
| `GET /graph/node/{entity}`, `GET /graph/impact/{entity}` | `knowledge_graph.py` (dinámico) | Ninguno automatizado — y `tools/graph_tools.py` (`GraphImpactAnalysisTool`), que sí es real y llega desde `/chat` |
| `GET /memory` | `memory_builder.py` | Ninguno automatizado |
| `GET /manifest/{app}` | `ai_manifest.py` | Ninguno automatizado |
| `POST /refresh`, `GET /refresh/detect` | `incremental_updater.py` + dinámicamente `graph_validator.py`/`documentation_graph.py` | Invocación manual post-cambio (documentado en `main.py` mismo) |
| `POST /search`, `GET /indices` | `specialized_retrieval.py` | Ninguno automatizado |
| `POST /ingest` | `bootstrap.py`/`loaders.py` (RAG, fuera de alcance) | Invocación manual |

**Confirma lo ya sabido**: de todos estos, solo `GraphImpactAnalysisTool` (via `/chat`,
intent `architecture_impact`, `AdminAgent`) tiene un camino de invocación real desde
producción. Todo lo demás son herramientas de desarrollo sin caller automatizado — lo
cual **baja el riesgo** de esta migración: no hay tráfico de producción que proteger,
solo flujos de desarrollo que no deben romperse.

## 6. Qué NO se hizo en esta sesión

No se movió ni un archivo. Este documento es el insumo para la Fase 2 (mapa de
dependencias, ya construido arriba realmente) y la Fase 3 (definir el contrato del
nuevo módulo) — pendientes de decisión del usuario sobre alcance y ritmo de ejecución
antes de tocar código, dado que esta es una migración de ~20 fases que toca el pipeline
completo de generación de código (`/generate`, `/validate`, `auditor.py`).
