# FASE 0 — Desacoplamiento ai_engine <-> project_knowledge_graph

**Fecha:** 2026-08-10
**Regla arquitectonica adoptada:** "AI Engine no conoce ni importa project_knowledge_graph" y
"project_knowledge_graph no conoce ni depende de ai_engine" -- separacion formal entre el
futuro **Site Knowledge Graph** (evolucion de `project_knowledge_graph`, consumido por un
futuro **AI Editor Runtime**, no construido todavia) y **AI Engine** (chatbot de soporte
puro: WebSocket, RAG, Action Graph).

Este documento es la matriz exacta pedida: que importaba cada archivo, que funcionalidad
perdio, y donde debe reubicarse esa funcionalidad en el futuro.

---

## 1. Matriz de imports eliminados

| Archivo | Importaba de `project_knowledge_graph` | Uso real (verificado, no supuesto) |
|---|---|---|
| `main.py` | `project_map.query.build_impact_report`, `.build_impact_context` | Endpoint `POST /impact` |
| `main.py` | `dependency_graph.blast_radius.what_breaks_if_i_change` | Endpoint `POST /breakage` |
| `main.py` | `dependency_graph.impact.build_impact_analysis_text` | Endpoint `POST /breakage` |
| `main.py` | `knowledge_graph.query.find_node_context` (import inline) | Endpoint `GET /graph/node/{entity}` |
| `main.py` | `knowledge_graph.query.impact_chain` (import inline) | Endpoint `GET /graph/impact/{entity}` |
| `main.py` | `audit.validator.run_all_validations` (import inline) | `POST /refresh` -- bloque de "gobernanza" |
| `main.py` | `knowledge_graph.enrichers.documentation.build_documentation_index` (inline) | `POST /refresh` -- `docs_to_review` |
| `planner.py` | `project_map.query.*` (8 funciones: find_affected_apps, build_impact_context, get_models_for_apps, get_viewsets_for_apps, get_endpoints_for_apps, get_frontend_consumers, get_stores_for_apps, get_serializers_for_apps) | `build_plan()` pasos 2, 6, 8 |
| `planner.py` | `dependency_graph.loader.get_dependency_graph` | `build_plan()` paso 9 (tests por app) |
| `planner.py` | `dependency_graph.blast_radius.what_breaks_if_i_change` | `build_plan()` paso 10 |
| `planner.py` | `dependency_graph.impact.build_impact_analysis_text` | Importada, **nunca usada** (dead import) |
| `planner.py` | `knowledge_graph.loader.get_knowledge_graph`, `.query.find_node_context` (inline, en `_get_kg_context`) | `build_plan()` paso 5 |
| `graph.py` | `project_map.query.build_impact_context`, `.find_affected_apps` | Importadas, **nunca usadas** (dead import -- `node_analyze_impact` solo llama a `build_plan()`) |
| `tools/graph_tools.py` | `dependency_graph.blast_radius.what_breaks_if_i_change`, `.impact.build_impact_analysis_text`, `knowledge_graph.query.find_node_context` | Todo el archivo -- implementaba `GraphImpactAnalysisTool` |
| `incremental_updater.py` | `incremental.diff.detect_changed_apps`, `incremental.updater.update_changed_apps` | `update_changed_apps()` -- delegaba PROJECT_MAP/KG/DG |
| `incremental_updater.py` | `audit.auditor.audit_full`, `config.DJANGO_APPS` (inline, rama `force_full`) | Full rebuild del grafo |
| `pkg_bootstrap.py` | (el modulo entero) | Agregaba `project_knowledge_graph` al `sys.path` para los 5 archivos de arriba |

**Ademas**, dos puntos donde `GraphImpactAnalysisTool` estaba conectado al chat de soporte
en vivo (no solo el archivo de la Tool, sino su cableado como capacidad conversacional):

| Archivo | Que tenia | Por que se quito |
|---|---|---|
| `tools/__init__.py` | `import tools.graph_tools` | Registraba la Tool -- ya no existe el archivo |
| `capabilities/registry.py` | `Capability(capability_id="analizar_impacto_arquitectura", tool_name="GraphImpactAnalysisTool", ...)` | Exponia la capacidad al LLM del chat |
| `action_graph.py` | Intent `"architecture_impact"` en `BUSINESS_INTENT_PATTERNS` + `INTENT_CAPABILITIES["architecture_impact"]` | Ruteaba mensajes de chat ("que se rompe si cambio X") a la capacidad de arriba (agregado 2026-08-04) |
| `agents/profiles/admin_agent.yaml` | `GraphImpactAnalysisTool` en `herramientas`, `analizar_impacto_arquitectura` en `capacidades`, `architecture_impact` en `intents` | AdminAgent podia disparar esta capacidad via chat |

---

## 2. Que funcionalidad se perdio (real, no teorica) y donde debe reubicarse

| Funcionalidad | Estado actual | Reubicacion futura |
|---|---|---|
| `POST /impact` -- mapa de impacto de una tarea antes de generar codigo | Devuelve estructura vacia valida (200, no error) -- documentado in-line como retirado | AI Editor Runtime, via su Graph SDK |
| `POST /breakage` -- blast radius de una entidad | Devuelve estructura vacia valida | AI Editor Runtime |
| `GET /graph/node/{entity}` | Responde **501** explicito con instruccion (`python -m project_knowledge_graph.cli node <entidad>`) | AI Editor Runtime, o uso directo de la CLI de `project_knowledge_graph` |
| `GET /graph/impact/{entity}` | Responde **501** explicito (`python -m project_knowledge_graph.cli impact <entidad>`) | Idem |
| `POST /refresh` -- gobernanza (`graph_validator`) + docs a revisar | Ya no corre -- el endpoint solo refresca memoria/manifiestos/indices ahora | `python -m project_knowledge_graph.cli validate`, fuera de ai_engine |
| `planner.py` pasos 2, 5, 6, 8, 9, 10 del pipeline de 17 pasos (deteccion de apps, KG, project map, frontend, tests, impacto) | Stubs que devuelven listas/strings vacios -- `build_plan()` sigue corriendo, con menos contexto real | AI Editor Runtime -- estos SON exactamente los pasos que la nueva arquitectura (Change Resolver, `resolve_change()`) debe reemplazar con algo mejor, no solo restaurar |
| `GraphImpactAnalysisTool` -- capacidad de chat "que se rompe si cambio X" | Retirada por completo (archivo borrado, capacidad desregistrada, intent desconectado) | AI Editor Runtime -- nunca debio ser una capacidad de chat de soporte, es una capacidad de ingenieria |

---

## 3. Limitacion real encontrada durante la ejecucion (no en el alcance original, documentada explicitamente)

`ai_manifest.py`, `memory_builder.py` y `specialized_retrieval.py` **no importan**
`project_knowledge_graph` (ya estaban limpios) -- pero los tres leen
`ai_engine/PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/`DEPENDENCY_GRAPH.json` **directo de
disco**, con rutas relativas a `ai_engine/`. Ese archivo:

- ya NO se regenera desde ningun lado dentro de ai_engine (el `auditor.py` que lo escribia
  se retiro cuando se extrajo `project_knowledge_graph`; la delegacion temporal que lo
  reemplazaba en Fase 17-18 tambien se retira en esta misma FASE 0);
- es una foto estatica del proyecto en el momento en que se genero por ultima vez.

**Esto es una limitacion real, no resuelta aca a proposito** -- reconstruir una fuente de
datos propia y genuinamente fresca para memoria/manifiestos de ai_engine (sin volver a
depender de `project_knowledge_graph`) es una decision de arquitectura (¿scanner propio
minimo? ¿lectura de archivo, no de codigo, del `data/` de `project_knowledge_graph`? ¿aceptar
que quede estatico?) que excede el alcance de "eliminar imports" pedido para FASE 0. Se deja
documentada aca para que se decida explicitamente, no se resuelve con un scanner duplicado
sin que se pida.

---

## 4. Verificacion realizada

- `grep -rn "project_knowledge_graph"` sobre todo `ai_engine/*.py` (fuera de `tests/` y
  comentarios explicativos): **cero imports reales**.
- `ai_engine/tests/test_pkg_decoupling.py` (nuevo, reemplaza a `test_pkg_compat_shims.py`,
  que verificaba lo contrario): recorre el AST de cada archivo `.py` de `ai_engine/` y falla
  si encuentra un `import`/`from` de `project_knowledge_graph` -- **PASS**.
- Import directo (con `project_knowledge_graph` bloqueado en `sys.path`) de `planner.py`,
  `incremental_updater.py`, `graph.py`, `tools` (paquete completo, 29 Tools registradas,
  antes 30): **todos importan limpio**.
- `capabilities/registry.py`: 29 capacidades registradas (antes 30) -- `analizar_impacto_
  arquitectura` confirmado ausente.
- `action_graph.py::detect_business_intents("que se rompe si cambio el modelo Product")`
  -> `["unknown"]` (antes: `["architecture_impact"]`) -- confirmado que el intent ya no
  se detecta, y que un intent no relacionado (`core_content`) sigue funcionando sin cambios.
- `project_knowledge_graph.dependency_graph.blast_radius.what_breaks_if_i_change("renting")`
  corrido de forma independiente, sin que `ai_engine` este siquiera importado en el proceso:
  **funciona identico** -- confirma "project_knowledge_graph no conoce ni depende de
  ai_engine" (ya era cierto antes de esta fase, no se toco ningun archivo de
  `project_knowledge_graph` en FASE 0).
- Suite de tests existente de `ai_engine` (`pytest tests/`): 15 pasan, 1 se saltea
  (limitacion de entorno -- `langchain.retrievers` no resuelve en este host fuera del
  contenedor, ver `conftest.py`), 3 fallan por no poder resolver el hostname `redis` (interno
  de Docker, no alcanzable desde el host) -- **ninguna falla relacionada con este cambio**.
  `test_intent_detection.py` se actualizo (se quitaron los 2 casos de `architecture_impact`,
  ya no existe).

---

## 5. Lo que NO se toco (deliberadamente, fuera de alcance de FASE 0)

- `project_knowledge_graph/` en si mismo -- cero archivos modificados.
- `action_graph.py`'s demas intents/capacidades/Tools -- solo se quito lo especifico de
  `architecture_impact`/`GraphImpactAnalysisTool`.
- `memory_builder.py`/`ai_manifest.py`/`specialized_retrieval.py` -- ver limitacion en
  seccion 3, decision pendiente.
- Los endpoints `/generate`, `/validate`, `/plan` de `main.py` -- siguen existiendo (usan
  `planner.py`/`graph.py`, ahora degradados pero funcionales); no se elimino la superficie de
  "generacion de codigo" de `ai_engine` completa, solo su dependencia de
  `project_knowledge_graph`. Si la arquitectura final quiere que estos endpoints tambien
  salgan de `ai_engine` (moverse al futuro AI Editor Runtime), esa es una decision distinta
  y mas grande que "FASE 0", no ejecutada aca.
