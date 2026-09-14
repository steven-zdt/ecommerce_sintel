# ARQUITECTURA COMPLETA — project_knowledge_graph

**Ultima revision:** 2026-08-10

Modulo independiente de analisis estructural del proyecto Sintel E-Commerce (Django+Vue+
ai_engine). Escanea el codigo fuente real (AST Python + regex Vue/JS), construye un Project Map,
un Knowledge Graph tipado y un Dependency Graph, corre validaciones automaticas de gobernanza,
y expone todo eso via una CLI propia. No es una app Django ni un servicio HTTP — es una libreria
Python que se ejecuta on-demand (o se importa) desde el host, desde `ai_engine`, o desde su propia
CLI.

**No confundir con el RAG vectorial** (`ai_engine/retrievers.py` + ChromaDB) — ese sigue siendo la
fuente de contexto narrativo para el chat. Este modulo estructura metadata verificable (que
modelo/viewset/endpoint/componente existe, que depende de que) como un grafo consultable.

---

## 1. Por que existe (y por que no vive dentro de `ai_engine`)

Hasta el 2026-08-08, todo esto (`project_map.py`, `knowledge_graph.py`, `dependency_graph.py`,
`incremental_updater.py`, `auditor.py`, mas la familia "Graphify" — `agent_graph.py`/
`docker_graph.py`/`documentation_graph.py`/`graph_validator.py`/`graph_visualizer.py`) vivia como
archivos planos dentro de `ai_engine/`, con dos problemas reales:

1. **Acoplamiento oculto.** `auditor.py::ProjectAuditor.run()` encadenaba 8 pasos distintos
   (PROJECT_MAP, Knowledge Graph, Dependency Graph, Memory, AI Manifests, Validator, Visualizer,
   hash tracker) en un solo metodo de ~120 lineas, cada uno con su propio `try/except`
   silencioso. `incremental_updater.py` alcanzaba atributos/metodos PRIVADOS de una instancia de
   `ProjectAuditor` para reauditar apps individuales — funcionaba solo porque ambos archivos
   vivian en el mismo namespace plano.
2. **Confusion de responsabilidad.** El analisis estructural del PROYECTO ENTERO (incluido
   `ai_engine` mismo, como un modulo mas) vivia DENTRO de `ai_engine`, como si fuera parte del
   motor de chat. No lo es: `project_knowledge_graph` puede correr, y se sigue construyendo,
   sin que `ai_engine` este siquiera levantado.

La migracion (`PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH`, ejecutada completa, fase por
fase, con 2 checkpoints, el 2026-08-09) extrajo todo a este modulo independiente y **borro** los 9
archivos planos viejos de `ai_engine/` (no quedaron shims permanentes). Ver seccion 9 para el
detalle de que consume esto hoy y como.

---

## 2. Estructura de archivos

```
project_knowledge_graph/
├── __init__.py              # Vacio a proposito -- cada submodulo importa config.py cuando lo
│                             #   necesita, para no forzar la resolucion de BASE_DIR (que puede
│                             #   lanzar RuntimeError, ver Regla 13 mas abajo) solo por importar
│                             #   el paquete
├── config.py                # BASE_DIR/DATA_DIR/rutas de artefactos JSON, DJANGO_APPS,
│                             #   ROLE_PATTERNS (Python), VUE_ROLE_PATTERNS, API_PREFIXES
├── pytest.ini                # testpaths = tests
│
├── scanner/                  # SOURCE CODE -> datos crudos (AST/regex). No interpreta Django,
│                             #   no arma el grafo -- solo extrae hechos sintacticos
│   ├── python_scanner.py     #   safe_parse/get_base_names/extract_classes/extract_imports/
│                             #   extract_symbols/file_stats (Fase 1)/extract_env_var_calls (Fase 2)
│   ├── django_scanner.py     #   detect_python_role/is_model_class/is_viewset_class/
│                             #   is_serializer_class/is_permission_class/is_test_class (Fase 7)/
│                             #   extract_url_patterns/extract_websocket_patterns (Fase 2)/
│                             #   extract_model_fields/extract_signal_registrations (sender, Fase 6)/
│                             #   extract_task_queue_calls (Fase 6)/extract_model_manager_usages
│                             #   (Fase 5)/extract_api_test_calls, extract_direct_symbol_calls
│                             #   (Fase 7)/is_task_function
│   ├── frontend_scanner.py   #   detect_vue_role/extract_vue_api_calls (+ patron useApi().verb(),
│                             #   Fase 4)/extract_use_hook_calls (Fase 4, reemplaza a
│                             #   extract_vue_store_imports -- retirada, 0 aristas reales)/
│                             #   extract_vue_component_imports/extract_vue_template_tags/
│                             #   extract_vue_emits_props/extract_pinia_store (+ hook_name, Fase 4)/
│                             #   extract_router_component_aliases/extract_router_routes/
│                             #   extract_frontend_symbols/isolate_vue_script (Fase 3, extraccion de
│                             #   Symbol frontend heuristica via regex + balance de parentesis)/
│                             #   _extract_flat_exported_object_methods (Fase 4)
│   └── project_scanner.py    #   scan_app()/scan_frontend()/scan_frontend_file() -- orquesta
│                             #   los 3 de arriba por app/archivo, marca is_test por simbolo (Fase 7)
│
├── project_map/              # scanner -> PROJECT_MAP.json ("que existe en el proyecto")
│   ├── builder.py            #   ProjectMapBuilder -- build_cross_refs/build_endpoints_list/
│                             #   _infer_http_methods/build(). NO encadena KG/DG/audit -- eso es
│                             #   responsabilidad de audit/auditor.py
│   ├── loader.py             #   get_map() -- cache in-process (lru_cache)
│   └── query.py               #   find_affected_apps/get_models_for_apps/get_viewsets_for_apps/
│                             #   get_endpoints_for_apps/get_frontend_consumers/get_stores_for_apps/
│                             #   get_serializers_for_apps/get_services_for_apps/
│                             #   build_impact_context/build_impact_report
│
├── knowledge_graph/          # PROJECT_MAP -> grafo tipado (entidades + relaciones)
│   ├── relations.py          #   Node/Edge/KnowledgeGraph -- ver seccion 4 para tipos/aristas
│   ├── builder.py            #   KnowledgeGraphBuilder (_add_apps/_add_backend_entities/
│                             #   _add_endpoints/_add_frontend_entities/_infer_*_edges) +
│                             #   build_and_save_knowledge_graph() (encadena los 3 enrichers)
│   ├── loader.py             #   get_knowledge_graph() -- prefiere KNOWLEDGE_GRAPH.json
│                             #   persistido (ya enriquecido) sobre reconstruir en frio
│   ├── query.py               #   find_node_context()/impact_chain() (originales) +
│                             #   trace_data_flow (Fase 5)/trace_execution (Fase 6)/
│                             #   find_tests_for_change (Fase 7)/find_docs_for_change (Fase 8)/
│                             #   find_configuration_for (Fase 9)/resolve_change_target,
│                             #   calculate_change_impact (Fase 10)/resolve_change (Fase 11)/
│                             #   build_graph_context_packet (Fase 12)/find_symbol, find_file,
│                             #   find_endpoint, find_consumers, build_change_plan (Fase 13)
│   └── enrichers/             # Agregan nodos/aristas que NO salen de PROJECT_MAP
│       ├── documentation.py  #   Nodos Documentation + arista App-DOCUMENTED_BY->Documentation
│                             #   (+ REFERENCES desde texto libre, Fase 8), desde <app>/.AGENT/docs/
│                             #   *.md + AUDITORIA/ + Documentacion/ + este mismo archivo
│       ├── docker.py         #   Nodos DockerService desde docker-compose.yml (solo lectura,
│                             #   nunca ejecuta Docker) + DEPENDS_ON/DEPLOYS_TO/EXPOSES (Port)/
│                             #   PROVIDES (EnvVar) (Fase 9)
│       ├── nginx.py          #   Nodos derivados de nginx.conf (Fase 9): rutas proxy_pass reales,
│                             #   solo lectura, nunca ejecuta nginx
│       └── agents.py         #   Nodos Agent/Tool desde ai_engine/agents/profiles/*.yaml +
│                             #   ai_engine/tools/*_tools.py + arista USES -- UNICO punto donde
│                             #   este modulo lee (solo lectura) archivos de ai_engine
│
├── dependency_graph/          # Vistas derivadas del KG optimizadas para consulta directa
│   ├── builder.py            #   build_dependency_graph()/save_dependency_graph()
│   ├── loader.py             #   get_dependency_graph() -- cache in-process
│   ├── blast_radius.py       #   what_breaks_if_i_change() -- ver nota historica en el archivo
│                             #   sobre el bug real que motivo toda la auditoria original ('renting')
│   ├── impact.py             #   build_impact_analysis_text() -- texto legible para prompt LLM
│   └── query.py               #   who_consumes_endpoint()/what_tests_cover_app()/get_app_summary()
│
├── incremental/                # Deteccion de cambios + reconstruccion selectiva
│   ├── hashing.py             #   hash_file()/load_hash_db()/save_hash_db()/collect_app_files()/
│                             #   collect_frontend_files()/initialize_hash_tracker() -- publicas
│                             #   a proposito (el acoplamiento con funciones PRIVADAS de
│                             #   auditor.py era justo el problema que este modulo resuelve)
│   ├── diff.py                #   detect_changed_apps() -- git diff primero, hash como fallback;
│                             #   + parse_diff_hunks/get_git_diff_text/symbols_touched_by_diff/
│                             #   detect_changed_symbols (Fase 15, deteccion symbol-level real)
│   └── updater.py             #   update_changed_apps()/refresh_after_change() -- PROJECT_MAP/KG/
│                             #   DG solamente (Memory/indices especializados quedan en ai_engine,
│                             #   ver seccion 9)
│
├── audit/                     # Gobernanza + orquestacion de la corrida completa
│   ├── auditor.py             #   audit_full() -- reemplaza a ProjectAuditor.run(): PROJECT_MAP
│                             #   -> KG -> DG -> validaciones -> viz HTML -> hash tracker ->
│                             #   snapshot, cada paso explicito y defensivo (un fallo no tumba
│                             #   los pasos anteriores, ya escritos en disco)
│   ├── validator.py           #   run_all_validations() -- 6 chequeos, ver seccion 5
│   ├── change_validation.py   #   build_change_validation_report() (Fase 16) -- compone
│                             #   detect_changed_symbols + calculate_change_impact + validator en
│                             #   el "CHANGE VALIDATION REPORT" sobre el git diff actual
│   ├── query_log.py           #   log_query()/read_recent_queries() (Fase 18) -- auditoria
│                             #   append-only de consultas via graph_sdk, nunca `meta` de nodo
│   └── visualizer.py          #   build_html() -- GRAPH_VIEW.html autocontenido (vis-network via
│                             #   CDN, sin servidor nuevo)
│
├── snapshots/                  # Historial ligero de cada corrida (NUEVO -- no existia en el
│   └── manager.py              #   ai_engine original). Guarda SOLO conteos+timestamp+resumen de
│                             #   validacion en SNAPSHOT_META.json, nunca una copia del grafo
│                             #   completo (eso ya vive versionado en los otros JSON)
│
├── graph_sdk/                  # Fachada estable para consumidores futuros (Fase 13)
│   └── __init__.py             #   13 operaciones (resolve_change/find_symbol/find_file/
│                             #   find_endpoint/find_consumers/trace_data_flow/trace_execution/
│                             #   find_tests/find_docs/calculate_impact/build_change_plan/
│                             #   build_context_packet/find_configuration), cada una envuelta con
│                             #   logging de auditoria (Fase 18) -- devuelve dicts planos, nunca
│                             #   Node/KnowledgeGraph
│
├── cli/                        # Punto de entrada unico (NUEVO)
│   ├── main.py                #   argparse: audit/incremental/validate/viz/node/impact/
│                             #   app-summary/snapshots/data-flow/execution/tests-for/docs-for/
│                             #   config-for/change-impact/resolve-change/context-packet/
│                             #   changed-symbols/validation-report/query-log
│   ├── __main__.py             #   `python -m project_knowledge_graph.cli ...`
│   └── __init__.py
│
├── tests/                      # pytest (NUEVO -- el ai_engine original no tenia ningun test de
│   ├── conftest.py             #   esta capa) -- fixture `audited_project` (session-scoped) corre
│                             #   la auditoria completa una vez, todos los tests de integracion la
│                             #   reusan
│   ├── test_relations.py       #   Unit tests puros de Node/Edge/KnowledgeGraph (sin I/O)
│   ├── test_scanners.py        #   Unit tests puros de scanner/ con AST/regex sintetico (sin I/O)
│   ├── test_documentation_enricher.py  # Unit tests de enrichers/documentation.py (Fase 8)
│   ├── test_infrastructure_enrichers.py  # Unit tests de enrichers/docker.py + nginx.py (Fase 9)
│   ├── test_incremental_symbol_diff.py  # Unit tests de incremental/diff.py::parse_diff_hunks (Fase 15)
│   ├── test_ai_editor_scaffold.py  # Verifica que ai_editor/ (fuera de este paquete) respeta su
│                             #   propio alcance de scaffold (Fase 14/17) -- AST, 0 logica ejecutable
│   ├── test_change_validation.py  # Unit tests de audit/change_validation.py con mocks (Fase 16)
│   ├── test_query_log.py       #   Unit tests de audit/query_log.py con log temporal (Fase 18)
│   └── test_pipeline_equivalence.py  # Integracion contra el repo REAL (no mockeado) -- 1 modulo,
│                             #   crece cada fase con al menos 1 prueba real por fase (Fases 1-18)
│
└── data/                        # Artefactos generados (untracked -- nunca se hizo `git add`,
                                #   NO es un patron de .gitignore -- ver seccion 10)
    ├── PROJECT_MAP.json
    ├── KNOWLEDGE_GRAPH.json
    ├── DEPENDENCY_GRAPH.json
    ├── GRAPH_VALIDATION_REPORT.json
    ├── GRAPH_VIEW.html
    ├── SNAPSHOT_META.json
    ├── QUERY_AUDIT_LOG.jsonl     # Fase 18 -- log de auditoria de consultas
    └── .file_hashes.json
```

---

## 3. `config.py` — resolucion de rutas (leer antes de tocar cualquier cosa)

`BASE_DIR` se resuelve via `CODEBASE_PATH` (variable de entorno) si esta seteada y existe, si no
cae a `Path(__file__).resolve().parent.parent` (es decir, `ecommerce_sintel/`, ya que
`config.py` vive un nivel mas abajo). **Regla 13 del plan de separacion:** si `BASE_DIR` no
existe, el modulo **falla explicito** (`RuntimeError` al importar `config.py`) — nunca reporta
0 apps/modelos en silencio, que era exactamente el bug historico de la version en `ai_engine`
(ver `AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md`, hallazgo H2).

`DATA_DIR` es siempre `Path(__file__).resolve().parent / "data"` (relativo a este modulo, no a
`BASE_DIR`) — los artefactos JSON viven dentro de `project_knowledge_graph/data/`, no dispersos
por el repo.

**Cuidado con `Path(__file__).resolve().parents[N]`:** cada submodulo que necesita llegar a la
raiz del repo (`REPO_ROOT`, un nivel arriba de `ecommerce_sintel/`) o a `ai_engine/` (los
enrichers de `agents.py`) calcula `N` segun su propia profundidad de anidamiento — **no es el
mismo `N` para un archivo en `knowledge_graph/enrichers/` que para uno en `dependency_graph/`**.
Durante la migracion se encontro un bug real de este tipo exacto en los primeros 2 enrichers
escritos (`agents.py`/`docker.py` usaban `parents[4]`/`parents[5]` en vez de `parents[3]`/
`parents[4]`) — resolvia a un directorio que no existia y habria devuelto resultados vacios SIN
error visible (`if dir.exists(): ...` los enmascara). Se corrigio y se verifico contra datos
reales antes de continuar; si se agrega un nuevo archivo con esta necesidad, verificar el valor
de `parents[N]` con `Path(__file__).resolve().parents[N]` en una sesion interactiva antes de
confiar en el, no solo por lectura.

---

## 4. Knowledge Graph — tipos de nodo y aristas implementadas

**Node types:** `App | Model | Serializer | ViewSet | Command | Selector | Service | Signal |
Consumer | Task | Permission | Endpoint | ManagementCommand | FrontendView | FrontendComponent |
PiniaStore | Composable | Layout | Route | Documentation | DockerService | Agent | Tool | File |
Symbol | WebSocketRoute | EnvVar`

`File`/`Symbol` agregados en **Fase 1 (Site Knowledge Graph, 2026-08-10)**: `File` es un nodo por
archivo escaneado (backend Python + frontend Vue/JS) con `language`/`lines`/`hash`/`role` en su
`meta`. `Symbol` es un nodo por funcion/metodo con rango de lineas exacto
(`start_line`/`end_line`) y `qualified_name` (`Clase.metodo` para metodos, `funcion` para
funciones de modulo) -- responde "que lineas exactas tocar", no solo "que archivo". `CodeSegment`
del plan original de separacion **no es un node type aparte a proposito**: con un scanner de una
sola pasada (sin tracking de identidad entre commits), `Symbol` (`qualified_name` + archivo +
rango de lineas + hash de contenido en su `meta`) y `CodeSegment` (`symbol` + hash + rango) serian
casi 1:1 -- separarlos de verdad solo tiene sentido con fingerprint semantico real (embeddings) o
tracking de identidad cross-commit, ninguno construido todavia.

**Fase 3 "Frontend Symbol Intelligence" (Site Knowledge Graph, 2026-08-10)** extendio `Symbol` a
`.vue`/`.js`/`.ts` -- MISMO node type que Python, no un `FrontendSymbol` aparte (decision de
scope documentada en `scanner/frontend_scanner.py`: dos tipos que significan lo mismo solo
fragmentan queries/tests). Se distingue por `meta.language` mas 2 campos nuevos ausentes en
Symbol Python: `meta.symbol_type` (`function | method | computed | watch | lifecycle` -- forma
sintactica) y `meta.role` (`api_call | emit | event_handler | null` -- tag semantico por
contenido del cuerpo, independiente de `symbol_type`). Sin parser JS/TS real disponible (no hay
esprima/tree-sitter instalado, deliberado no agregar esa dependencia para una sola pasada de
escaneo), la extraccion es heuristica: regex ancladas a inicio de linea (`function NAME(...) {`,
`const/let NAME = (...) => {`, `const/let NAME = computed|watch|watchEffect(...)`, hooks de
lifecycle sueltos `onMounted(...)`/etc., y -- solo para Pinia option-stores, unico lugar real del
proyecto con `NAME(args) { ... }` de metodo de objeto, dado que `frontend/CLAUDE.md` prohibe
Options API en componentes -- metodos de `actions:`/`getters:`) mas balance de parentesis/llaves
consciente de strings/comentarios (mismo criterio pragmatico que ya usaba
`extract_router_routes()`). A diferencia de Python (que ignora funciones anidadas dentro de otra
funcion), frontend SI captura anidamiento: es el patron dominante real de un composable Vue (toda
la logica vive dentro de la funcion exportada, ver `useOperationTracking.js`). Verificado con
lineas exactas contra 3 archivos reales del dominio Renting/Availability -- ver seccion 11.

`WebSocketRoute`/`EnvVar` agregados en **Fase 2 "Contract Graph" (Site Knowledge Graph,
2026-08-10)**: `WebSocketRoute` es un nodo por cada `path()`/`re_path()` de un `routing.py` de
Django Channels cuyo segundo argumento es literalmente `Algo.as_asgi()` (asi se distingue de una
URL HTTP normal). `EnvVar` es un nodo por cada variable leida via `config()`/`env()`
(python-decouple, confirmado como el patron real del proyecto en `ecommerce/settings/base.py`)
en cualquier archivo Python escaneado -- no solo `settings.py`. De los 7 sub-tipos de "Contract
Graph" del plan original solo estos 2 se construyeron como node types nuevos; el resto ya estaba
cubierto o quedo fuera a proposito (ver el detalle completo en `IMPLEMENTED_BY`/`USES_ENV` abajo
y en la seccion 11, entrada Fase 2).

**Edge labels realmente implementados** (verificado, no aspiracional): `BELONGS_TO | EXPOSES |
SERIALIZES | USES | CALLS | DEPENDS_ON | CONSUMES_ENDPOINT | USES_STORE | USES_COMPOSABLE |
DOCUMENTED_BY | IMPORTS | USES_COMPONENT | DEPENDS_ON (docker) | DEPLOYS_TO | CONTAINS |
IMPLEMENTED_BY | USES_ENV | READS_FROM | WRITES_TO | TRIGGERS | QUEUES | VALIDATES | TESTS |
REFERENCES`

**Fase 4 "Contract Graph Frontend<->Backend" (Site Knowledge Graph, 2026-08-10)** extiende
`CONSUMES_ENDPOINT`/`USES_STORE` (ya existian a nivel de archivo) a nivel de `Symbol` individual,
agrega `USES_COMPOSABLE` (edge label nuevo) y `Endpoint -SERIALIZES-> Serializer`. Verificacion
contra el repo real encontro y corrigio **2 defectos reales**, no hipoteticos:
1. **`USES_STORE` tenia 0 aristas en TODO el grafo** antes de este fix. Causa raiz: el matching
   comparaba por substring un nombre derivado del hook (`useAvailabilityStore()` -> capturaba
   solo `"AvailabilityStore"`) contra el `store_id` de negocio del store (`"rentalAvailability"`)
   -- strings sin relacion textual garantizada por convencion de este proyecto. Fix: `Symbol`/
   `PiniaStore` ahora capturan el **hook_name real** (`extract_pinia_store()` gano `hook_name` via
   `export const useX = defineStore(...)`; el lado consumidor via `extract_use_hook_calls()`
   captura el nombre COMPLETO del hook llamado) y el builder matchea EXACTO, no por substring.
2. **La capa de "custom API wrapper" del proyecto (`frontend/src/services/**/*.js`, 10 archivos
   reales, 69 llamadas) era invisible para el grafo**: `extract_vue_api_calls()` no reconocia el
   patron encadenado `useApi().get(url)` (solo `const api = useApi(); api.get(url)`), y esos
   archivos son objetos exportados planos (`export const xService = { check(...) {...} }`), no
   Pinia stores, asi que tampoco generaban ningun `Symbol`. Fix: nuevo patron regex en
   `extract_vue_api_calls()` + `_extract_flat_exported_object_methods()` en
   `frontend_scanner.py`.

Un tercer defecto se encontro DURANTE la verificacion del fix anterior: el matching de URL a
Endpoint (`_match_endpoints_for_url()`, usado desde antes de Fase 3) comparaba por "el ultimo
segmento de la URL coincide" -- `renting/equipment/{uuid}/check-availability/` matcheaba contra
`endpoint:api/v1/auth/availability` (dominio no relacionado) solo por compartir el substring
literal `"availability"`. Causa raiz real: `Endpoint.name` es el PREFIJO del router de UN
ViewSet completo (`api/v1/renting/equipment`), no la URL de cada `@action` individual (esas viven
como `Symbol` alcanzables via `IMPLEMENTED_BY`, no como su propio `Endpoint`). Fix: matching por
PREFIJO real (la URL del frontend debe empezar por el prefijo del endpoint, con o sin el
`api/v1/` que Axios ya no repite via `baseURL`) -- responde 4.4 del plan ("no limitar el analisis
a coincidencias literales") sin reconstruir cada `@action` como su propio node type (cambio de
alcance mayor, no necesario).

`CONTAINS` (Fase 1, extendido Fase 3): `File -> Symbol`, `File -> cualquier nodo existente cuyo
archivo coincida` (Model/ViewSet/FrontendComponent/etc. -- reusa el atributo `.file` que casi
todos los node types ya cargaban, no requiere escanear de nuevo), y `Clase -> su propio metodo`
cuando la clase tiene nodo propio en el grafo (ej. `ViewSet -> ViewSet.metodo`,
`FrontendComponent -> FrontendComponent.metodo`, `PiniaStore -> PiniaStore.accion` desde Fase 3
-- misma logica exacta, sin cambios en `builder.py::_add_one_file`, solo mas simbolos entrando
por `f["symbols"]`).

`IMPLEMENTED_BY` (Fase 2): `Endpoint -> Symbol` (el metodo REAL del ViewSet que atiende ese
endpoint, usando la lista `actions` ya existente en cada Endpoint -- responde exactamente el
ejemplo del plan del usuario: `GET /api/v1/renting/availability/` -> `AvailabilityViewSet.list`
con lineas exactas) y `WebSocketRoute -> Consumer` (ej. `ws/support/chat/` ->
`SupportChatConsumer`, verificado contra el mismo consumer auditado en vivo en la sesion de
diagnostico del chatbot, 2026-08-10).

`USES_ENV` (Fase 2): `File -> EnvVar`, ej. `ecommerce/settings/base.py` -USES_ENV->
`AI_SUPPORT_CHAT_ENABLED` -- responde el ejemplo del plan "`AI_SUPPORT_CHAT_ENABLED` -> que
archivos la leen".

`USES_STORE`/`USES_COMPOSABLE` (Fase 4): `FrontendComponent|FrontendView|Composable|PiniaStore|
Symbol -> PiniaStore` o `-> Composable`, segun si el hook llamado matchea el `hook_name` real de
un store o el nombre de archivo de un composable -- ej. `ProductList.vue -USES_COMPOSABLE->
useToast.js/useErrorHandler.js/useOffcanvas.js` + `-USES_STORE-> shopAdmin` (verificado real).

`CONSUMES_ENDPOINT`/`SERIALIZES` (Fase 4, a nivel de Symbol): ej.
`availabilityService.check` (Symbol real de `services/renting/availabilityService.js`)
`-CONSUMES_ENDPOINT-> endpoint:api/v1/renting/equipment -IMPLEMENTED_BY->
EquipmentViewSet.check_availability` y `endpoint:api/v1/renting/equipment -SERIALIZES->
EquipmentSerializer` (y las ~35 otras Serializer de esa app) -- cadena completa Frontend Symbol
-> Endpoint -> Backend Symbol -> Serializer, sin busqueda manual (criterio 4.5 del plan).

`READS_FROM`/`WRITES_TO` (Fase 5 "Data Flow Graph", 2026-08-10): `Symbol -> Model`, evidencia
real via AST del patron `Model.objects.verbo(...)` (`filter`/`get`/`all`/... clasificado
`READS_FROM`; `create`/`update`/`delete`/`get_or_create`/... clasificado `WRITES_TO`) dentro de
Selectors/Services/Commands/ViewSets -- ver `scanner/django_scanner.py::
extract_model_manager_usages`. Alcance deliberado: NO cubre cadenas donde el verbo de escritura
llega despues de un verbo de lectura en la misma expresion (`Product.objects.filter(x=1)
.update(y=2)`) ni `instancia.save()`/`.delete()` sobre variables ya tipadas -- ambos requieren
seguimiento de cadenas de llamada o inferencia de tipos, fuera de alcance de un scanner AST de
una sola pasada. `READS_FROM`/`WRITES_TO` es por lo tanto un PISO real verificado, no el 100% de
los accesos reales del proyecto.

`trace_data_flow(target)` (consulta obligatoria 5.4 del plan, `knowledge_graph/query.py`):
reconstruye `database -> serializer -> API -> frontend -> componente` para un `Model` o
`Model.campo` (ej. `"Product"` o `"Product.name"`), componiendo aristas YA existentes
(`READS_FROM`/`WRITES_TO` nuevas + `SERIALIZES`/`CONSUMES_ENDPOINT`/`USES_STORE`/
`USES_COMPOSABLE`/`CONTAINS` de fases anteriores) -- sin agregar node/edge types nuevos, la
prioridad de esta fase es la relacion, no la entidad (5.1 del plan). Con campo, `field_verified`
confirma (no asume) que el campo este realmente declarado en `Model.meta.fields` -- verificado
honesto: `trace_data_flow("Product.name")` -> `True` (campo real), `trace_data_flow("Product.
image")` -> `False` (las imagenes viven en el modelo relacionado `ProductImage`, no como campo
directo de `Product` -- el ejemplo `Product.image` del plan original no es literalmente
reproducible en el esquema real de este proyecto, reportado honestamente en vez de simulado).
Disponible via CLI: `python -m project_knowledge_graph.cli data-flow <Model|Model.campo>`.

`TRIGGERS`/`QUEUES` (Fase 6 "Execution Graph", 2026-08-10): `Model -> Signal` (via `sender=X` real
de `@receiver(post_save, sender=UserProfile)`, verificado en accounts/models.py) y `Symbol ->
Task` (via `nombre_task.delay(...)`/`.apply_async(...)` real, verificado en
`NotificationCommands.dispatch_notification`, que encola 5 tasks reales segun canal). **Bug real
pre-existente encontrado y corregido durante esta fase, no introducido por ella:**
`is_task_function()` solo reconocia `@algo.shared_task(...)` (decorador via atributo) -- el patron
REAL y dominante del proyecto es `@shared_task(bind=True, ...)` (llamada directa a un `Name`), que
devolvia `False` para las 8 tasks reales de `notifications/tasks.py` -- 0 nodos `Task` para toda
esa app pese a que el rol de archivo ya se detectaba correctamente. Corregido, ver
`scanner/django_scanner.py::is_task_function`.

`trace_execution(start)` (consulta obligatoria 6.2 del plan, `knowledge_graph/query.py`):
reconstruye un ExecutionPath numerado (`FUNCTION -> API -> VIEW -> SERVICE -> DATABASE -> EVENT ->
NOTIFICATION`) desde un Symbol de partida, componiendo TODAS las aristas ya existentes
(`CONSUMES_ENDPOINT`/`IMPLEMENTED_BY`/`CALLS`/`READS_FROM`/`WRITES_TO`/`TRIGGERS`/`QUEUES`) --
recorrido greedy por un camino principal, con `also` listando el resto de aristas reales desde
cada nodo (sin esto, casos reales con mas de una consecuencia -- como `dispatch_notification`,
que escribe `NotificationLog` Y encola 5 tasks -- perdian silenciosamente la rama mas relevante).
2 correcciones encontradas verificando contra casos reales: (1) `IMPLEMENTED_BY` desde un
`Endpoint` apunta a TODAS las acciones de su ViewSet (Fase 4: el Endpoint es el prefijo de router
completo, no una URL de `@action` individual) -- se desambigua por el ultimo segmento de la URL
real del Symbol de origen (`availabilityService.check()` -> `EquipmentViewSet.check_availability`,
no `.get_object` por casualidad de orden). (2) `CALLS` (Fase 0) vive a granularidad de CLASE
(`ViewSet -> Service` completos), no de metodo -- sin fallback via `CONTAINS` a la clase dueña, el
recorrido se cortaba en CUALQUIER metodo de ViewSet que no toque Model/Task directo, el caso
NORMAL en este proyecto (Service Layer obligatorio, `.AGENT.md`: "Prohibido logica de negocio en
ViewSets"). Disponible via CLI: `python -m project_knowledge_graph.cli execution <simbolo>`.

`VALIDATES`/`TESTS` (Fase 7 "Test Graph", 2026-08-10): sin node types nuevos (Test/TestSuite/
E2ETest) -- un metodo de test YA es un `Symbol` real (mismo criterio que Fase 3 con
`FrontendSymbol`), solo se marca `meta.is_test` (clase con base `*TestCase`/`APITestCase`, o
funcion de modulo `test_*` estilo pytest). `Test-Symbol -VALIDATES-> Endpoint` via
`self.client.verbo(url)` real (DRF `APITestCase`, soporta f-strings); `Test-Symbol -TESTS->
Symbol` via llamada directa `ClaseX.metodo(...)` dentro del test (unit-test-style, sin pasar por
HTTP). `find_tests_for_change(target)` (consulta obligatoria 7.4 del plan): responde "que tests
ejecutar si cambio esto" para un Symbol/Endpoint/Model, con `direct_tests` (aristas directas) e
`indirect_tests` (un salto real: Symbol implementado por un Endpoint -> tests que VALIDATES ese
Endpoint; Model -> tests que TESTS un accesor directo O que VALIDATES un Endpoint cuyo SERIALIZES
llega a ese Model). **Bug real encontrado y corregido durante la propia verificacion:**
`find_by_name('Product')` devuelve **460 matches** por substring en orden de iteracion de
diccionario (no de relevancia) -- el primer resultado de tipo Symbol/Endpoint/Model NUNCA era el
Model `Product` real. Corregido priorizando coincidencia EXACTA de nombre antes de caer a la
busqueda fuzzy. Alcance deliberado de esta fase: solo tests **Python** (Django TestCase/
APITestCase + pytest `test_*`) -- tests frontend (Vitest `.test.js`, ej. `useToast.test.js`) y
E2E (Playwright, `frontend/playwright.config.js` existe) quedan **PLANIFICADOS**, no
implementados, requieren un patron de scanner de bloques (`describe`/`it`/`test(...)`) distinto
al de funciones que ya tiene `frontend_scanner.py`. Disponible via CLI:
`python -m project_knowledge_graph.cli tests-for <Symbol|Endpoint|Model>`.

`REFERENCES` (Fase 8 "Documentation Graph", 2026-08-10): `Documentation -> File|Symbol|Endpoint`,
via referencias reales citadas entre backticks en la prosa del doc (rutas de archivo,
`Clase.metodo`, URLs de endpoint) -- ver `knowledge_graph/enrichers/documentation.py::
extract_doc_references`. Responde 8.1 del plan ("no confiar unicamente en nombres"). Verificado
real: `ARQUITECTURA_COMPLETA_RENTIG.md` tiene 48 referencias reales (26 Symbol, 17 Endpoint, 5
File), incluyendo `AvailabilityEngine.is_available` (mismo dominio usado en Fases 3-7).
`find_docs_for_change(query)` (consulta obligatoria 8.2 del plan): combina resolucion
ESTRUCTURAL (si `query` coincide EXACTO con el nombre de una entidad real, devuelve solo los docs
conectados via `REFERENCES`/`DOCUMENTED_BY`) con busqueda de TEXTO LIBRE (cada palabra del query
buscada en el contenido crudo de cada doc, con un puntaje simple para que el doc mas relevante
quede primero) -- el ejemplo textual EXACTO del plan, `find_docs_for_change("renting
availability")`, devuelve `ARQUITECTURA_COMPLETA_RENTIG.md` como resultado #1, verificado real.
Categorizado por `scope` (`nivel2`->`implementation_docs`, `arquitectura`->`architecture_docs`,
`auditoria`->`audit_docs`) -- aproximacion de las 4 categorias del plan; este proyecto no
distingue "feature docs" como scope propio, esos docs viven mezclados dentro de `nivel2`.
Disponible via CLI: `python -m project_knowledge_graph.cli docs-for <query>`.

`EXPOSES`/`PROVIDES`/`ROUTES_TO` + node types `Port`/`NginxRoute` (Fase 9 "Configuration/
Infrastructure Graph", 2026-08-10): `DockerService -EXPOSES-> Port` (puerto HOST real de
`ports:` en `docker-compose.yml`, ej. `docker:django -> port:8000/tcp`); `DockerService
-PROVIDES-> EnvVar` (solo servicios con `env_file:` real -- el patron DOMINANTE de este proyecto,
no `environment:` por variable -- matcheado contra nombres de `.env.production.example`, la
PLANTILLA sin secretos; nunca se lee `.env`/`.env.production` reales); `NginxRoute -ROUTES_TO->
DockerService` (resuelto via `proxy_pass`, con indireccion real `set $var http://servicio:puerto;`
+ `proxy_pass $var;`, el patron dominante de `nginx-common.conf`). **2 bugs reales encontrados y
corregidos verificando contra datos reales:** (1) `.env.production.example` vive DENTRO de
`ecommerce_sintel/`, no en la raiz del repo -- la primera version buscaba en la raiz, nunca
encontraba el archivo, `PROVIDES` quedaba en 0 aristas en TODO el grafo en silencio. (2) el regex
de `location` no anclaba a inicio de linea: matcheaba como SUBSTRING dentro de
`geolocation=()` (un header `Permissions-Policy` real), y la captura no-greedy se extendia
CIENTOS de lineas (incluyendo un header CSP completo) hasta el proximo `{` real -- un
`NginxRoute` con todo ese texto como "path". `find_configuration_for(query)` (consulta
obligatoria 9.2 del plan): combina `EnvVar`/`DockerService`/`NginxRoute`/`File` de settings por
substring. Disponible via CLI: `python -m project_knowledge_graph.cli config-for <query>`.

**Fase 10 "Change Graph" (2026-08-10, "la fase critica" del plan)**: `calculate_change_impact
(target)` (`knowledge_graph/query.py`) -- compone TODAS las consultas de Fases 5-9 en un impacto
categorizado DIRECTO/INDIRECTO (frontend/backend/contract/test/documentation/configuration), con
`risk` (heuristico honesto por conteo: HIGH/MEDIUM/LOW, no un modelo predictivo) y
`recommended_order` (plantilla ESTATICA de convencion, marcada explicitamente como tal, no
calculada). **Alcance deliberado, no omitido en silencio**: NO se implementa un parser de
lenguaje natural para `ChangeIntent` (10.2 del plan, ej. convertir "Agregar alquiler por horas"
en JSON estructurado) -- eso requiere un LLM real (la futura Fase 14 "AI Editor Runtime",
explicitamente separada de este modulo puramente estatico), no algo que un scanner AST/regex
pueda hacer honestamente. `ChangeTarget` (10.3) SI se implementa (`resolve_change_target()`,
mismo criterio exacto-antes-que-fuzzy de Fases 7-9) y `AffectedNode` (10.4) SI se implementa
completo. **Bug real encontrado y corregido durante la propia verificacion**: los primitivos
genericos `transitive_dependents()`/`what_depends_on()` (pre-existentes, usados por
`impact_chain()`) no distinguen aristas ESTRUCTURALES (`CONTAINS`, `BELONGS_TO`) de FUNCIONALES
-- verificado real: cambiar `EquipmentViewSet.check_availability` mostraba `EquipmentViewSet` (su
propia clase) como "impacto DIRECTO" (el ViewSet "depende" de contener su propio metodo, un
artefacto estructural sin sentido para "que se rompe"), inflando el total de 42 a 797 nodos.
Corregido con `_functional_dependents()`, una funcion NUEVA que excluye ambas aristas (no se
modifico `transitive_dependents()` en si, para no afectar a `impact_chain()`). Disponible via
CLI: `python -m project_knowledge_graph.cli change-impact <target>`.

**Fase 11 "Change Resolver" (2026-08-10)**: `resolve_change(request)` -- interfaz principal para
la futura IA editora (Fase 14), compone `calculate_change_impact()` + `trace_data_flow()` (solo
si el target es Model) + `trace_execution()` (solo si es Symbol) en el envelope EXACTO del plan
(`intent, target, primary_files, symbols, contracts, frontend_consumers, backend_dependencies,
data_flows, execution_paths, tests, documentation, configuration, risk, change_order,
validation_plan`). `intent` no parsea lenguaje natural -- mismo alcance documentado en Fase 10.
Verificado real: `resolve_change("EquipmentViewSet.check_availability")` produce
`primary_files=[renting/api/views.py]`, `contracts=[api/v1/renting/equipment]`, 11
`frontend_consumers` reales, `execution_paths` poblado (es Symbol) y `data_flows=None`
(correctamente, no es Model). Disponible via CLI:
`python -m project_knowledge_graph.cli resolve-change <request>`.

**Fase 12 "Graph Context Packet" (2026-08-10)**: `build_graph_context_packet(request)` --
comprime `resolve_change()` (Fase 11) a SOLO el subgrafo relevante (`_compact_node()`: id/type/
name/file/lineas, NUNCA el `meta` completo con api_calls/hook_calls/fields/etc.) mas `stats`
(`total_graph_nodes` del grafo completo vs `relevant_nodes` de este cambio) -- responde
literalmente el diagrama de 12 del plan (miles de nodos -> resolver -> decenas relevantes).
Verificado real: `EquipmentViewSet.check_availability` -> **9575 nodos totales -> 20 relevantes**
(7 archivos, 8 simbolos, 1 contrato, 4 tests). Disponible via CLI:
`python -m project_knowledge_graph.cli context-packet <request>`.

**Fase 13 "Graph SDK" (2026-08-10)**: nuevo paquete `project_knowledge_graph/graph_sdk/`, capa
ESTABLE que oculta JSON/internals de `KnowledgeGraph`/`Node`/storage a cualquier consumidor
futuro (la Fase 14 "AI Editor Runtime" en particular) -- ningun consumidor deberia necesitar
`from knowledge_graph.relations import Node`. Expone las 11 operaciones EXACTAS del plan (`resolve_
change/find_symbol/find_file/find_endpoint/find_consumers/trace_data_flow/trace_execution/
find_tests/find_docs/calculate_impact/build_change_plan`), cada una re-exportando (posiblemente
renombrada) una funcion YA construida en fases anteriores -- sin reimplementar logica. 4
primitivos nuevos (`find_symbol`/`find_file`/`find_endpoint`/`find_consumers`, busqueda EXACTA
con fallback a substring, mismo criterio de Fases 7-10) mas `build_change_plan()` (subconjunto de
`resolve_change()` enfocado solo en riesgo/orden/validacion). Verificado real contra las 11
operaciones sobre el dominio Renting/Availability. Sin CLI nuevo -- el SDK es para consumo
PROGRAMATICO (`import`), los comandos CLI ya existentes llaman a las mismas funciones subyacentes.

**Escala real del proyecto** (corrida completa, 2026-08-10, verificado vigente hasta Fase 18 --
Fases 11-18 son todas capa de consulta/reporte/logging pura sobre el grafo ya construido en Fase
10, ninguna agrega/quita nodos o aristas): **9575 nodos / 20335 aristas** sobre **21 apps Django**
auditadas, **150 endpoints**, **1161 archivos** escaneados.
`Symbol` **6396** (sin nuevos en Fase 5/6/7/8, solo mas aristas y meta.is_test). **857 Symbol
marcados `is_test`** (Python). `Task` **19** (subio de 8 tras el fix de `is_task_function`, 11
tasks reales recuperadas en varias apps, no solo notifications). Aristas nuevas de Fase 4: **275
CONSUMES_ENDPOINT** (nivel Symbol, antes 0), **147 USES_STORE** (antes **0 en todo el repo**, bug
real corregido), **505 USES_COMPOSABLE** (edge nueva), **325 SERIALIZES** Endpoint->Serializer
(edge nueva, antes solo existia Serializer->Model). Aristas nuevas de Fase 5: **648 READS_FROM**
+ **616 WRITES_TO** (edges nuevas, Symbol->Model). Aristas nuevas de Fase 6: **16 TRIGGERS** +
**10 QUEUES** (edges nuevas). Aristas nuevas de Fase 7: **96 VALIDATES** + **429 TESTS** (edges
nuevas). Aristas nuevas de Fase 8: **1316 REFERENCES** (edge nueva). Desglose de nodos por tipo:

| Tipo | Cantidad | | Tipo | Cantidad |
|------|---------:|-|------|---------:|
| Symbol | 6396 | | Serializer | 432 |
| File | 1161 | | ViewSet | 168 |
| FrontendComponent | 321 | | Model | 167 |
| Documentation | 167 | | Endpoint | 150 |
| EnvVar | 68 | | Command | 94 |
| Route | 89 | | FrontendView | 84 |
| Selector | 61 | | PiniaStore | 29 |
| Tool | 29 | | App | 23 |
| Composable | 26 | | Signal | 16 |
| Service | 15 | | Permission | 11 |
| DockerService | 10 | | Agent | 9 |
| Task | 19 | | ManagementCommand | 5 |
| WebSocketRoute | 4 | | Layout | 4 |
| Consumer | 3 | | | |

(`Tool` bajo de 30 a 29 el 2026-08-10: `GraphImpactAnalysisTool` se retiro de `ai_engine`, ver
FASE 0 de desacoplamiento, seccion 9. `PiniaStore` faltaba en esta tabla en la revision anterior
del documento -- omision de la tabla, no del grafo, corregida aca.)

Estos numeros son un snapshot puntual — se regeneran en cada corrida de `audit_full()`, no
hardcodear en codigo nuevo, solo sirven como referencia de escala en este documento.

---

## 5. Validador de gobernanza (`audit/validator.py`) — 6 chequeos

| # | Chequeo | Que responde | Resultado en la ultima corrida real |
|---|---------|---------------|--------------------------------------|
| 1 | `find_orphaned_app_docs` | Doc de Nivel 2 con app declarada pero sin nodo `App` real que lo reciba | 0 |
| 2 | `find_stale_documentation` | Fecha declarada en el encabezado del doc mas vieja que el ultimo commit real del codigo de esa app | 12 |
| 3 | `find_service_layer_violations` | `selectors.py` (deberia ser solo lectura) con una escritura real (`.save(`/`.create(`/`.delete(`/`.update(`/`@transaction.atomic`) | 2 |
| 4 | `find_import_cycles` | Grupos de Apps mutuamente acopladas en circulo (SCC/Tarjan sobre aristas `IMPORTS` reales) | 1 grupo |
| 5 | `find_dead_frontend_components` | `FrontendComponent`/`FrontendView` sin ninguna arista `USES_COMPONENT` entrante ni uso como `component:` de una Route | 25 |
| 6 | `find_contradictory_counts` | "N modelos/viewsets/endpoints" declarado en prosa vs. el conteo real del grafo | 43 (leer con cautela — regex sobre prosa libre, revisar cada uno antes de actuar) |

Los chequeos 2/6 son sensibles al tiempo (fechas de commit, fechas declaradas en docs) — sus
conteos cambian con normalidad a medida que el repo evoluciona, no son una señal de regresion del
propio validador.

---

## 6. CLI

```bash
python -m project_knowledge_graph.cli audit [--quiet]
python -m project_knowledge_graph.cli incremental [--full]
python -m project_knowledge_graph.cli validate
python -m project_knowledge_graph.cli viz
python -m project_knowledge_graph.cli node <nombre> [--depth N]
python -m project_knowledge_graph.cli impact <entidad>
python -m project_knowledge_graph.cli app-summary <app>
python -m project_knowledge_graph.cli snapshots [--limit N]
python -m project_knowledge_graph.cli data-flow <Model|Model.campo>
python -m project_knowledge_graph.cli execution <simbolo>
python -m project_knowledge_graph.cli tests-for <Symbol|Endpoint|Model>
python -m project_knowledge_graph.cli docs-for <query>
python -m project_knowledge_graph.cli config-for <query>
python -m project_knowledge_graph.cli change-impact <target>
python -m project_knowledge_graph.cli resolve-change <request>
python -m project_knowledge_graph.cli context-packet <request>
python -m project_knowledge_graph.cli changed-symbols
python -m project_knowledge_graph.cli validation-report
python -m project_knowledge_graph.cli query-log [--limit N]
```

Corre desde el host, con cwd en `ecommerce_sintel/` (o con `ecommerce_sintel/` en el
`PYTHONPATH`). No requiere Docker levantado ni `ai_engine` corriendo — es un modulo
autocontenido, solo depende de `PyYAML` fuera de la libreria estandar.

---

## 7. Tests

```bash
python -m pytest project_knowledge_graph/tests -v
```

`test_relations.py`/`test_scanners.py` son unit tests puros (sin I/O, fixtures sinteticas) —
corren en cualquier entorno con Python 3.12+, sin dependencias del proyecto. `test_pipeline_
equivalence.py` corre `audit_full()` contra el codigo REAL del repo (no un fixture mockeado —
un mock del scanner no habria detectado el bug de `parents[N]` que la migracion encontro) y
verifica invariantes concretos sobre cada capa agregada Fases 1-18.

**[CORREGIDO, Fase 19, 2026-08-10]** Este mismo archivo decia "pytest no esta instalado en el
Python del host" -- **eso ya no es cierto en este checkout**: `python -m pytest
project_knowledge_graph/tests -q` corre y pasa 120/120 directo desde el host, sin Docker. Se deja
esta correccion documentada en vez de solo borrar la frase vieja, para que quede registro de que
el entorno cambio (probablemente `pytest` se agrego al Python del host en algun momento entre la
nota original y esta fase) -- si vuelve a fallar por falta de `pytest`, seguir usando
`docker compose exec sintel_ai python -m pytest /workspace/project_knowledge_graph/tests` como
fallback conocido.
**Referencia retirada, tambien corregida aca**: esta seccion mencionaba una "prueba de
equivalencia literal contra `GraphImpactAnalysisTool` (`ai_engine/tools/graph_tools.py`)" -- ese
archivo fue BORRADO en la Fase 0 de este mismo rediseno (ver Historial, entrada 2026-08-10 FASE 0)
y el test que lo comparaba fue reemplazado por
`test_ai_engine_does_not_import_this_module` (verifica lo contrario: que ya no existe).

---

## 8. Snapshots (`snapshots/manager.py`)

Cada `audit_full()` (y cada `update_changed_apps()` incremental, via `incremental/updater.py`)
agrega una entrada a `data/SNAPSHOT_META.json`: timestamp, `kind` (`full`/`incremental`), conteos
de apps/endpoints/frontend/nodos-KG-por-tipo/entradas-de-blast-radius, y el resumen del
validador si corrio en esa pasada. Guarda solo metadata liviana (nunca una copia del grafo
completo) y retiene como maximo `MAX_SNAPSHOTS = 50` entradas. No existia en el `ai_engine`
original — antes no habia forma de responder "cuando crecio el grafo" o "cuando fue el ultimo
full rebuild" sin buscar en el historial de git de los JSON.

**Query/audit log** (`audit/query_log.py`, Fase 18 "Observability", 2026-08-10): cada una de las
13 funciones de `graph_sdk` queda envuelta en logging append-only a `data/QUERY_AUDIT_LOG.jsonl` --
operacion, args (truncados a 200 chars), resumen del resultado (found/id/name/counts, NUNCA `meta`
completo de un nodo) y `graph_snapshot` (timestamp del ultimo snapshot de esta seccion, referencia
de contra que build del grafo se corrio la consulta). Logging best-effort: un fallo de escritura
(disco lleno, permisos) nunca hace fallar la consulta real. CLI: `project-graph query-log
[--limit N]`.

---

## 9. Quien consume esto hoy (y como)

**[ACTUALIZADO 2026-08-10, FASE 0] Ningun consumidor real, ni dentro ni fuera de
`ai_engine`.** Este modulo no expone HTTP, no tiene Django app propia, se consulta
exclusivamente por import directo de Python o por su CLI.

Entre el 2026-08-09 y el 2026-08-10 hubo una version intermedia (Fase 17-18 del plan de
separacion original) donde 4 archivos de `ai_engine` (`main.py`, `planner.py`, `graph.py`,
`tools/graph_tools.py`) importaban este modulo directo, mas `ai_engine/pkg_bootstrap.py` (que
agregaba `project_knowledge_graph` al `sys.path` del proceso de `ai_engine`) y
`ai_engine/incremental_updater.py` (que delegaba la reconstruccion de PROJECT_MAP/KG/DG aca).
**Esa version quedo superada por una regla arquitectonica mas estricta** (separacion formal
Site Knowledge Graph / AI Editor Runtime, ver `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_
FASE0.md` para la matriz exacta de que se quito y donde debe reubicarse):

> **AI Engine no conoce ni importa `project_knowledge_graph`.**
> **`project_knowledge_graph` no conoce ni depende de `ai_engine`.**

`ai_engine/pkg_bootstrap.py` se borro. Los 4 archivos ya no importan este modulo (sus llamadas
se reemplazaron por stubs locales que devuelven "sin datos" en vez de fallar --
`GraphImpactAnalysisTool`/`tools/graph_tools.py` se borro por completo, no se degrado).
`ai_engine/incremental_updater.py` ya no delega nada aca -- solo reconstruye APP_MEMORY/
AI_MANIFESTS/indices especializados, su propia responsabilidad nativa.

**Consumidor real hoy:** ninguno propio del proyecto. El unico consumo previsto es el futuro
**AI Editor Runtime** (no construido todavia), via un Graph SDK/API todavia por definir --
nunca via `from project_knowledge_graph import ...` directo desde otro servicio de Python del
monorepo, ese es exactamente el patron que esta regla prohibe repetir.

---

## 10. Gaps conocidos / seguimiento pendiente

- **Documentacion desactualizada en otros lugares del repo (no corregido en esta revision):**
  `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md`, `AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md`
  (raiz del repo, `ecommerce_sintel_rest/AUDITORIA/`, fuera de `ecommerce_sintel/`) y este mismo
  directorio -- `AUDITORIA_KNOWLEDGE_GRAPH_SSOT_2026-08-04.md` (2026-08-04, previo a la
  migracion) -- todavia describen la arquitectura vieja (archivos planos dentro de `ai_engine/`,
  `auditor.py` corriendo `ProjectAuditor.run()`, endpoints citados por linea de `main.py` que ya
  cambiaron de numero). No son incorrectos sobre el pasado, pero no reflejan el estado actual del
  codigo.
- **`find_contradictory_counts`/`find_stale_documentation` (validador, chequeos 2 y 6)**
  seguiran marcando este mismo archivo y otros docs del repo con normalidad a medida que pase el
  tiempo desde esta revision — no es un bug, es la funcion cumpliendo su proposito.
- **`memory_builder.py`/`ai_manifest.py`/`specialized_retrieval.py`** (ai_engine) leen
  `ai_engine/PROJECT_MAP.json`/`KNOWLEDGE_GRAPH.json`/`DEPENDENCY_GRAPH.json` directo de disco,
  sin importar ningun modulo de `project_knowledge_graph` -- nunca dependieron de el mas alla
  de ese JSON. **[ACTUALIZADO 2026-08-10, FASE 0]** Ese JSON ya NO se regenera desde ningun
  lado dentro de `ai_engine` (la delegacion que lo mantenia fresco tambien se retiro) -- queda
  como una foto estatica. Es una limitacion real, documentada y sin resolver a proposito en
  `ai_engine/.AGENT/AI_ENGINE_KG_DECOUPLING_FASE0.md` seccion 3 -- decidir si se resuelve con
  lectura de archivo (no de codigo) del `data/` de este modulo, un scanner propio minimo de
  `ai_engine`, o aceptar el snapshot estatico, es una decision de arquitectura pendiente.
- **`data/` no esta en `.gitignore`** (encontrado y corregido en la documentacion durante Fase 19,
  2026-08-10 -- la seccion 2 de este archivo decia "gitignored" de forma incorrecta): `git status`
  muestra el directorio completo como `??` (untracked), pero `git check-ignore` no matchea ningun
  patron real -- simplemente nunca se hizo `git add` sobre el. Comportamiento actual correcto (no
  se versiona), pero por la razon equivocada; agregar un patron real a `.gitignore` para que sea
  intencional (no accidental) queda como limitacion sin resolver, no corregida en esta pasada por
  ser un cambio a un archivo compartido (`.gitignore` raiz) fuera del alcance de "documentacion".

---

## 11. Historial

**[NUEVO PLAN, 2026-08-11]** Con el Site Knowledge Graph cerrado (FASE 0-21), arranco un plan
separado "PROMPT MAESTRO — EVOLUCION DE AI_EDITOR" (POST-GRAPH 0-23) que construye SOBRE este
modulo sin reabrirlo -- vive en `ecommerce_sintel/ai_editor/.AGENT/AI_EDITOR_BASELINE.md`, no en
este archivo. `graph_sdk/__init__.py` gano 3 operaciones nuevas (`find_node`/`get_app_summary`/
`get_graph_status`, POST-GRAPH 1, 2026-08-11) -- unico cambio de codigo de este modulo por ese
plan hasta ahora, documentado alli con el detalle completo (por que se agregaron, por que
`find_node` reusa `resolve_change_target` y no `find_node_context`). Este Historial sigue siendo
la fuente de verdad de las FASE 0-21 propias del Site Knowledge Graph; no se reabren esas fases.

**[CIERRE 2026-08-11]** Las 22 fases (FASE 0-21) del rediseno "Site Knowledge Graph / AI Editor
Runtime" estan completas. Reporte de cierre ejecutivo (que se construyo, decisiones de alcance
deliberadas, estado final verificado, limitaciones conocidas):
`SITE_KNOWLEDGE_GRAPH_CIERRE_FINAL.md` (mismo directorio).

- **2026-08-10** — FASE 21 "Validacion Global" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases -- FASE 21, penultima). Pasada final end-to-end sobre las 19 fases de codigo
  (Fases 1-18, la 19/20 fueron documentacion pura): `cli audit` (full rebuild real, ~2 min, 21
  apps/1161 archivos/9575 nodos/20335 aristas -- identico a las cifras citadas en toda la seccion
  4, sin drift), `cli validate` (6 chequeos, mismo resultado que el ultimo `audit`), `cli viz`
  (GRAPH_VIEW.html 5465.8 KB generado sin error), `cli snapshots` (historial real con conteos por
  tipo de nodo, incluye `EnvVar`/`NginxRoute`/`WebSocketRoute`/`Task` de Fases 2/6/9), `cli
  validation-report` (Fase 16, corrido sobre el grafo RECIEN reconstruido: 16 contratos/59
  frontend/31 backend/38 tests afectados, risk HIGH, mismo comportamiento que la verificacion
  original de Fase 16) y `cli query-log` (Fase 18, confirma que las llamadas de arriba SI quedaron
  registradas con `graph_snapshot` poblado). Suite completa: **120/120 tests pasan**, corrida DOS
  veces (antes y despues del `cli audit` de esta fase) sin diferencia -- confirma que la suite no
  depende de un estado de grafo "congelado" accidentalmente. **0 regresiones encontradas** en
  ninguna de las 18 fases de codigo. Datos generados durante la verificacion (`QUERY_AUDIT_LOG.jsonl`
  de las corridas de prueba) se limpiaron despues, no forman parte del estado real del proyecto.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 20 "Limpieza Documental" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 20 unicamente). Objetivo: buscar en TODO el repo (no solo
  `project_knowledge_graph/`) referencias a los 9 archivos de `ai_engine` retirados en la
  extraccion de 2026-08-09 (`project_map.py`/`knowledge_graph.py`/`dependency_graph.py`/
  `auditor.py`/`agent_graph.py`/`docker_graph.py`/`documentation_graph.py`/`graph_validator.py`/
  `graph_visualizer.py`) y a `GraphImpactAnalysisTool`/`pkg_bootstrap.py` (retirados en Fase 0,
  2026-08-10), clasificando cada hallazgo como HISTORICA (documenta correctamente el pasado, no
  tocar) / ACTUAL-PERO-INCORRECTA (corregir) / OBSOLETA (candidata a borrar). **Metodo real**:
  `grep -rl` con los 11 nombres exactos sobre TODO el repo (excluyendo `node_modules`/`.git`) --
  34 archivos con al menos 1 match. Los matches en CODIGO Python (`ai_engine/main.py`,
  `capabilities/registry.py`, `tools/__init__.py`, `action_graph.py`,
  `tests/test_intent_detection.py`) se verificaron TODOS como comentarios historicos correctos
  (documentan que algo se retiro, con fecha, no lo describen como existente) -- CERO bugs de
  codigo real encontrados. Los matches en `AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md`,
  `AUDITORIA/16_AUDITORIA_AI_ENGINE_SYNC.md` y `Documentacion/Arquitectura_general/
  IMPLEMENTATION_SUMMARY.md` son auditorias/narrativas fechadas, correctamente HISTORICAS (ya
  reconocido en la seccion 10 de este mismo archivo antes de esta fase).
  **4 archivos ACTUAL-PERO-INCORRECTA encontrados y corregidos** (los 4 viven en
  `ai_engine/.AGENT/`, el directorio de referencia VIVA que el propio `CLAUDE.md` raiz manda leer
  antes de tocar codigo de `ai_engine` -- por eso importaba corregirlos, a diferencia de
  `AUDITORIA/`):
  1. **`FLIJO_COMPLETO_IA_ENGINE.md`**: seccion 2 (arbol de archivos) listaba `project_map.py`/
     `knowledge_graph.py`/`dependency_graph.py`/`auditor.py` como archivos ACTUALES de
     `ai_engine/` -- verificado con `ls`: ninguno existe. Corregido marcandolos RETIRADOS (sin
     borrar la referencia, con puntero a donde vive la funcionalidad ahora). Ademas: 4
     instrucciones operativas (`python ai_engine/auditor.py`, que fallaria con
     `FileNotFoundError` si alguien la sigue literalmente) corregidas con el comando real
     (`python -m project_knowledge_graph.cli audit`); y la descripcion de `node_analyze_impact`
     (seccion 8.3) que afirmaba que llama `find_affected_apps()` de `project_map.py` --
     verificado con `grep` en `graph.py`/`planner.py` reales: ya no es asi, `find_affected_apps`
     es hoy un stub LOCAL dentro de `planner.py` (Fase 0), llamado indirecto via `build_plan()`.
  2. **`GUIA_USO.md`**: seccion 7 completa ("El auditor del proyecto") describia un comando que ya
     no existe como si fuera el flujo operativo actual. Corregida con banner de retiro + comando
     real; fila de troubleshooting que tambien citaba el comando retirado, corregida.
  3. **`AI_SUPPORT_SCOPE.md`**: seccion 4bis presentaba la excepcion `tools/graph_tools.py`
     (`GraphImpactAnalysisTool`) como **vigente** -- verificado: el archivo fue eliminado por
     completo en Fase 0 (no solo degradado), la excepcion esta CERRADA, la regla de la seccion 4
     es hoy absoluta sin excepciones. Corregido con banner explicito de que no es precedente
     reutilizable.
  4. **`AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md`**: tabla de clasificacion de 2026-08-08 seguia
     marcando 9 archivos ya eliminados como `ENGINEERING_SEPARATE` (implicando que solo estaban
     "separados conceptualmente", no fisicamente borrados) y la fila de `graph_tools.py` como
     "SUPPORT_KEEP, excepcion documentada" vigente. Corregido con banner antes de la tabla
     (tabla original preservada por valor historico, no reescrita fila por fila).
  **Verificado real**: cada correccion se confirmo contra el filesystem real (`ls`/`test -f`
  sobre los 9 archivos + `.file_hashes.json`) y contra el codigo real (`grep` en `graph.py`/
  `planner.py` para la cadena de llamadas de `node_analyze_impact`), no contra suposiciones. 0
  archivos borrados (nada se clasifico como OBSOLETA-para-borrar; el criterio "documentar en vez
  de eliminar sin necesidad" del plan se siguio estrictamente). 0 tests nuevos (documentacion
  pura) -- 120/120 siguen pasando.
  **Limitacion documentada, no omitida en silencio**: no se corrigieron TODAS las menciones
  individuales dentro de `FLIJO_COMPLETO_IA_ENGINE.md` (956 lineas, ej. seccion 17.5 "`project_
  map.py` — API de consulta" sigue con su contenido original detallado) -- se opto por un banner
  de retiro prominente al inicio de cada seccion afectada en vez de reescribir cada subseccion
  individualmente, criterio de proporcionalidad (el banner ya redirige a la fuente de verdad
  actual antes de que el lector llegue al detalle obsoleto).
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 19 "Documentacion" del rediseno "Site Knowledge Graph / AI Editor Runtime"
  (22 fases, FASE 19 unicamente -- consolidacion, no codigo). El proceso de actualizar este mismo
  archivo + `ecommerce_sintel/MEMORY.md` en cada fase (Fases 1-18) ya cumplia la disciplina de
  documentacion incremental que pide el plan; esta fase es la pasada de CONSOLIDACION que verifica
  que las secciones "estaticas" (2 "Estructura de archivos", 4 "Escala real del proyecto", 7
  "Tests") no se hayan quedado atras respecto al detalle que si se actualizaba en el Historial cada
  fase. **4 defectos reales de documentacion encontrados y corregidos (no reescritura preventiva):**
  1. Seccion 2 listaba funciones de `scanner/frontend_scanner.py`/`django_scanner.py` de ANTES de
     Fase 3-7 (`extract_vue_store_imports`, retirada en Fase 4, seguia listada; faltaban
     `extract_frontend_symbols`/`extract_model_manager_usages`/etc.), y omitia `enrichers/nginx.py`
     (Fase 9), `graph_sdk/` (Fase 13), `audit/change_validation.py` (Fase 16),
     `audit/query_log.py` (Fase 18), y 6 archivos de test nuevos.
  2. `knowledge_graph/query.py` en seccion 2 seguia listado con SOLO sus 2 funciones originales
     (`find_node_context`/`impact_chain`) pese a que Fases 5-13 agregaron 16 funciones mas al mismo
     archivo.
  3. Seccion 7 afirmaba **"pytest no esta instalado en el Python del host"** -- verificado FALSO
     en este checkout ahora mismo (`python -m pytest project_knowledge_graph/tests -q` corre y
     pasa 120/120 directo, sin Docker). Corregido con nota explicita de que el entorno cambio,
     dejando el fallback de Docker documentado por si vuelve a fallar en otro checkout.
  4. Misma seccion citaba una "prueba de equivalencia literal contra `GraphImpactAnalysisTool`
     (`ai_engine/tools/graph_tools.py`)" -- ese archivo fue BORRADO en la Fase 0 de este mismo
     rediseno; el test real que existe hoy verifica lo contrario
     (`test_ai_engine_does_not_import_this_module`).
  5. Seccion 2 afirmaba que `data/` esta "gitignored" -- verificado FALSO: `git check-ignore` no
     matchea ningun patron real, el directorio esta simplemente `??` (untracked, nunca se hizo
     `git add`), no por `.gitignore`. Documentado en seccion 10 como limitacion sin resolver (agregar
     un patron real de `.gitignore` es un cambio a un archivo compartido, fuera de alcance de una
     pasada de documentacion).
  **Verificado real**: cada correccion se confirmo contra el codigo/comandos reales (`grep -n "^def "`
  sobre los 3 scanners, `ls` de `audit/`/`tests/`/`data/`/`graph_sdk/`, corrida real de pytest,
  `git status`/`git check-ignore` reales), no contra suposiciones. 0 tests nuevos (documentacion
  pura, ningun comportamiento nuevo que probar) -- 120/120 siguen pasando (verificado de nuevo tras
  los cambios de tests de Fase 18, no hubo regresion).
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 18 "Observability" del rediseno "Site Knowledge Graph / AI Editor Runtime"
  (22 fases, FASE 18 unicamente). Objetivo: registro real de "que se consulto, que nodo, y contra
  que version del grafo", sin guardar secretos/tokens. `audit/query_log.py::log_query()`/
  `read_recent_queries()` (append-only JSONL, `data/QUERY_AUDIT_LOG.jsonl`); `graph_sdk/__init__.py`
  envuelve las 13 funciones exportadas con un decorador `_logged()` que registra operacion/
  args/duracion/`graph_snapshot` (timestamp del ultimo snapshot, Fase 10) y un RESUMEN del
  resultado -- nunca el `meta` completo de un nodo. Ninguna de las 13 funciones cambio su logica;
  el decorador solo envuelve. **Regla de seguridad seguida explicitamente** (pedida por el propio
  plan): se probo que los nodos `EnvVar` (Fase 9) ya solo guardan NOMBRES de variables de entorno,
  nunca valores (el `.env.production.example` fuente es una plantilla) -- pero el resumen de
  resultado poda `meta` para TODO tipo de nodo, no solo `EnvVar`, para no depender de esa garantia
  especifica si un enricher futuro cambia. Logging best-effort: un fallo de escritura nunca hace
  fallar la consulta real (verificado con un `Path` que lanza `OSError` en `.open()`).
  **Verificado contra el repo real**: `graph_sdk.find_symbol('EquipmentViewSet.check_availability')`
  y `calculate_impact('Product')` corridos contra el grafo real completo (9575+ nodos) escriben
  lineas reales al log con `graph_snapshot` poblado desde el ultimo snapshot real registrado, sin
  incluir ningun campo `meta`; `cli query-log --limit N` responde el historial real. Disponible
  via CLI: `project-graph query-log [--limit N]`. 9 tests nuevos (7 unit aislados con log temporal
  + 2 integracion real: escritura real desde `graph_sdk` contra el grafo real, mas 1 fix a un test
  de Fase 14 que no excluia el directorio `.AGENT` nuevo de esta fase), 120/120 pasan.
  **Limitacion documentada, no omitida en silencio**: el resumen de resultado solo cuenta listas
  TOP-LEVEL del dict de resultado (ej. `recommended_order_count`) -- no recorre recursivamente
  dicts anidados como `direct_impact`/`indirect_impact` (serian `contract`/`frontend`/`backend`
  por separado); limite deliberado para mantener el summarizer simple y predecible, no un intento
  fallido de cobertura completa.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 17 "Autonomous Change Loop" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 17 unicamente). **SOLO documentacion, mismo criterio de Fase 14**: un
  loop que encadene automaticamente `detect -> resolve -> plan -> patch -> validate -> rollback`
  necesita el paso `patch` (aplicar modificaciones reales a archivos), que Fase 14 dejo
  deliberadamente sin implementar por ser una accion de alto impacto y dificil de revertir que
  requiere decision humana separada -- construir el LOOP de orquestacion alrededor de un paso que
  no existe todavia no aporta nada real, y construirlo asumiendo un `patch/` futuro seria la
  decision de alto impacto que ya se dejo fuera de alcance. Se documenta el diseno completo del
  loop en `ai_editor/.AGENT/AUTONOMOUS_CHANGE_LOOP.md`, marcando explicitamente cuales pasos ya
  son reales (1-DETECT/2-RESOLVE/3-IMPACT/4-PLAN via Fases 10/11/13/15, y 7-VALIDATE via Fase 16)
  y cual es el punto de corte obligatorio (paso 5, "HUMAN GATE": ningun patch se aplica sin
  aprobacion humana explicita). 0 archivos de codigo nuevos, 0 tests nuevos -- no hay
  comportamiento ejecutable nuevo que verificar. **CHECKPOINT: PASS** (alcance: documentacion).
- **2026-08-10** — FASE 16 "Change Validation" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 16 unicamente). Objetivo: el "CHANGE VALIDATION REPORT" que pide el
  plan (files/symbols/contracts changed, frontend/backend afectado, tests requeridos, consistencia
  de grafo/contratos, riesgo agregado) DESPUES de que una IA aplique un patch. Ese `PATCH` no
  existe todavia (Fase 14, scaffold deliberado, no implementado) -- en su lugar,
  `audit/change_validation.py::build_change_validation_report()` usa como "cambio" el estado REAL
  del working tree (git diff sin commitear), la unica evidencia real disponible hoy, componiendo
  3 piezas YA construidas sin reimplementar nada: `detect_changed_symbols()` (Fase 15) ->
  `calculate_change_impact()` por simbolo (Fase 10, agregado/deduplicado) ->
  `run_all_validations()` (validator ya existente, 6 chequeos). Se agrega `_check_contract_consistency()`
  (nueva, pequena): para cada Endpoint dentro de `contracts_changed`, verifica que sus aristas
  `IMPLEMENTED_BY`/`SERIALIZES` sigan presentes en el grafo ya construido.
  **Decision de alcance deliberada sobre `tests_required`**: se CALCULA (evidencia real, Fase 7)
  pero NO se ejecuta automaticamente -- muchos tests reales de este proyecto requieren Postgres/
  Redis/Docker no disponibles desde el host bare (limitacion ya documentada en sesiones previas);
  el reporte devuelve `tests_run: false` con el motivo explicito en vez de fabricar un resultado
  pass/fail sin haberlo corrido.
  **Verificado contra el repo real**: corriendo `project-graph validation-report` contra el diff
  real actual del repo (72 archivos, ~200 simbolos incluyendo `AccountViewSet.register_verify`,
  `ContractorSpecialtyViewSet.get_queryset`, etc. de Fase 15) produce 16 `contracts_changed`, 59
  `frontend_affected`, 31 `backend_affected`, 38 `tests_required`, `risk: HIGH` (>=30 nodos
  afectados, heuristico ya establecido en Fase 10). `contract_consistency` detecto real y
  correctamente 8 endpoints reales sin arista `SERIALIZES` (ej. `api/v1/cart/wishlist` -- verificado
  a mano contra el grafo: solo tiene `BELONGS_TO`+`IMPLEMENTED_BY`, sin `SERIALIZES`) -- gap real
  y preexistente de cobertura del enricher de contrato (Fase 4), NO introducido por esta fase, no
  corregido aqui (fuera de alcance de "Change Validation": este modulo REPORTA inconsistencias
  reales, no las arregla). Disponible via CLI: `project-graph validation-report` (exit code 1 si
  `risk == HIGH`, para uso en pipelines). 5 tests nuevos (3 unit con mocks aislados +
  2 integracion real: forma estable del reporte sea cual sea el git diff del momento, y agregacion
  verificada contra `calculate_change_impact()` para `EquipmentViewSet.check_availability`
  inyectado via monkeypatch), 114/114 pasan.
  **Limitacion documentada, no omitida en silencio**: `graph_consistency` reusa
  `run_all_validations()` tal cual (chequeo del ESTADO GLOBAL del grafo, no del diff especifico) --
  un `stale_documentation`/`import_cycles` preexistente y no relacionado con el cambio actual
  tambien aparece en el reporte; es el comportamiento correcto (honestidad sobre el estado real
  del grafo), pero significa que `graph_consistency.consistent` puede ser `false` incluso si el
  cambio en si no rompio nada nuevo.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 15 "Incremental Semantic Graph" del rediseno "Site Knowledge Graph / AI
  Editor Runtime" (22 fases, FASE 15 unicamente). Objetivo: `git diff -> changed files -> changed
  symbols` (el nivel de detalle que faltaba -- lo existente solo llegaba a `changed apps`).
  Agregado `incremental/diff.py::detect_changed_symbols()`/`parse_diff_hunks()`/
  `symbols_touched_by_diff()`: parsea hunks de `git diff -U0 HEAD` (`@@ -a,b +c,d @@`) y los cruza
  contra `Symbol.start_line`/`end_line` REALES del Knowledge Graph ya construido -- sin
  reconstruir nada, solo lectura. **Alcance deliberado, documentado, no una implementacion
  completa del REQUISITO del plan** ("un cambio en una funcion no deberia requerir reconstruccion
  completa"): esto agrega DETECCION a nivel de simbolo, pero el REBUILD (`_rebuild_derived_
  artifacts()` en `updater.py`) sigue reconstruyendo el grafo COMPLETO -- convertir
  `KnowledgeGraphBuilder` en un builder que recalcula solo el subgrafo afectado es un cambio de
  arquitectura mayor (tocaria cada `_link_*`/`_infer_*`), fuera de alcance de esta pasada.
  **Bug real encontrado y corregido verificando contra el repo real**: `subprocess.run(...,
  text=True)` sin `encoding=` explicito usa la codepage ANSI de Windows (cp1252) para decodificar
  stdout -- `git diff -U0` incluye el CONTENIDO real del codigo (a diferencia del `--name-only`
  ya existente, que solo pide rutas), y este proyecto tiene comentarios/strings en español con
  acentos (UTF-8) por todo el codebase. `UnicodeDecodeError: 'charmap' codec can't decode byte
  0x8d` real al correr contra el repo. Corregido con `encoding="utf-8", errors="replace"`, mismo
  criterio que el resto del modulo ya usaba para leer archivos. **Verificado contra el repo
  real**: un hunk sintetico en lineas 155-158 de `renting/api/views.py` identifica exacto
  `EquipmentViewSet.check_availability` (rango real 151-168, verificado en Fases 3-14) sin
  confundirlo con metodos vecinos del mismo ViewSet; `changed-symbols` corriendo contra el
  estado real del repo devuelve Symbols reales sin crashear. Disponible via CLI:
  `project-graph changed-symbols`. 6 tests nuevos (4 unit + 2 integracion real), 108/108 pasan.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 14 "AI Editor Runtime" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 14 unicamente -- SCAFFOLD DELIBERADO, no una implementacion
  funcional). Nuevo paquete `ecommerce_sintel/ai_editor/` con los 7 submodulos exactos del plan
  (`intent/resolver/planner/repository/patch/validation/graph_client`). **Decision de alcance
  explicita, no una omision silenciosa**: construir un sistema que MODIFICA CODIGO
  autonomamente (`patch/` en particular) es una capacidad de alto impacto -- dificil de
  revertir, con blast radius sobre todo el repositorio -- que requiere una decision humana
  explicita y separada, no una consecuencia implicita de "evolucionar el grafo de
  conocimiento". Por eso: `graph_client/` es el UNICO submodulo con codigo real (wrapper de
  SOLO LECTURA sobre `project_knowledge_graph.graph_sdk`, Fase 13 -- re-exportacion directa,
  cero logica propia, cero riesgo); los otros 6 (`intent/resolver/planner/repository/patch/
  validation`) son EXCLUSIVAMENTE docstrings de arquitectura -- ni una funcion, clase, ni
  declaracion ejecutable, verificado por AST en los tests. Mantiene la regla arquitectonica de
  Fase 0: `ai_editor` no importa `ai_engine`, verificado por el mismo AST-walk que ya protegia
  esa frontera. 5 tests nuevos (estructura de directorios, 0 logica ejecutable en los stubs,
  `graph_client` es re-exportacion exacta -- mismos objetos, no copias --, frontera con
  `ai_engine`, documentacion honesta de estado real), 102/102 pasan.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 13 "Graph SDK" del rediseno "Site Knowledge Graph / AI Editor Runtime"
  (22 fases, FASE 13 unicamente). Nuevo paquete `project_knowledge_graph/graph_sdk/` (`__init__.py`)
  -- capa ESTABLE que oculta internals de `KnowledgeGraph`/`Node`/JSON/storage a futuros
  consumidores (principio explicito de 13 del plan). 11 operaciones exactas del plan, cada una
  re-exportando (algunas renombradas) funciones YA construidas en Fases 5-12 -- sin reimplementar
  logica. 4 primitivos NUEVOS (`find_symbol`/`find_file`/`find_endpoint`/`find_consumers`,
  busqueda exacta-antes-que-fuzzy) + `build_change_plan()` (subconjunto de `resolve_change()`
  enfocado en riesgo/orden/validacion). Verificado real: las 11 operaciones sobre el dominio
  Renting/Availability, devolviendo dicts planos (nunca instancias de `Node`). 1 test nuevo de
  integracion real, 97/97 pasan. Sin cambios de nodos/aristas ni CLI nuevo (el SDK es para
  consumo programatico via `import`).
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 12 "Graph Context Packet" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 12 unicamente). `build_graph_context_packet(request)` comprime
  `resolve_change()` (Fase 11) a solo el subgrafo relevante -- `_compact_node()` reduce cada nodo
  a id/type/name/file/lineas, NUNCA el `meta` completo (evita ruido de tokens para un futuro
  consumidor LLM). `stats` reporta `total_graph_nodes` vs `relevant_nodes` -- responde
  literalmente el diagrama de 12 del plan (miles de nodos -> resolver -> decenas relevantes).
  Verificado real: `EquipmentViewSet.check_availability` -> **9575 nodos totales reducidos a 20
  relevantes** (7 archivos, 8 simbolos, 1 contrato, 4 tests). Disponible via CLI:
  `project-graph context-packet <request>`. 1 test nuevo de integracion real, 96/96 pasan. Sin
  cambios de nodos/aristas -- capa de consulta pura.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 11 "Change Resolver" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 11 unicamente). `resolve_change(request)` -- interfaz principal para
  la futura IA editora (Fase 14), compone `calculate_change_impact()` (Fase 10) +
  `trace_data_flow()`/`trace_execution()` (Fases 5/6, solo cuando aplica al tipo de target) en el
  envelope EXACTO del plan (`intent/target/primary_files/symbols/contracts/frontend_consumers/
  backend_dependencies/data_flows/execution_paths/tests/documentation/configuration/risk/
  change_order/validation_plan`) -- ningun campo reimplementado, todos reusan funciones ya
  verificadas en fases anteriores. `intent` sigue sin parsing de lenguaje natural (mismo alcance
  documentado en Fase 10 -- requiere un LLM real). Verificado contra
  `EquipmentViewSet.check_availability`: `primary_files`/`contracts`/`frontend_consumers`
  correctos, `execution_paths` poblado (es Symbol), `data_flows=None` (correctamente, no es
  Model). Disponible via CLI: `project-graph resolve-change <request>`. 1 test nuevo de
  integracion real, 95/95 pasan. Sin cambios de nodos/aristas -- capa de consulta pura.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 10 "Change Graph" del rediseno "Site Knowledge Graph / AI Editor Runtime"
  (22 fases, FASE 10 unicamente -- "esta es la fase critica" segun el plan original). Objetivo:
  pasar de "conocimiento" a "Change Intelligence". Alcance deliberado, documentado, no omitido en
  silencio: NO se implemento `ChangeIntent` (10.2, parsear lenguaje natural como "Agregar alquiler
  por horas" a JSON estructurado) -- requiere un LLM real, corresponde a la futura Fase 14 "AI
  Editor Runtime" (explicitamente fuera de este modulo puramente estatico), no algo honesto para
  un scanner AST/regex. SI se implemento `ChangeTarget` (10.3, `resolve_change_target()`, mismo
  criterio exacto-antes-que-fuzzy de Fases 7-9) y `AffectedNode` completo (10.4,
  `calculate_change_impact()`) -- compone TODAS las consultas ya construidas en Fases 5-9
  (`find_tests_for_change`/`find_docs_for_change`/`find_configuration_for`) en un impacto
  categorizado DIRECTO/INDIRECTO por frontend/backend/contract/test/documentation/configuration,
  con `risk` (heuristico honesto por conteo de nodos, no un modelo predictivo) y
  `recommended_order` (plantilla ESTATICA marcada explicitamente como convencion, no como algo
  calculado). **Bug real encontrado y corregido durante la propia verificacion, no en la primera
  pasada**: los primitivos genericos `transitive_dependents()`/`what_depends_on()`
  (pre-existentes, usados por `impact_chain()`) no distinguen aristas ESTRUCTURALES (`CONTAINS`,
  `BELONGS_TO`) de FUNCIONALES -- verificado real: cambiar `EquipmentViewSet.check_availability`
  mostraba a `EquipmentViewSet` (su propia clase contenedora) como "impacto DIRECTO", inflando el
  total de 42 a 797 nodos afectados sin sentido real. Corregido con `_functional_dependents()`,
  una funcion NUEVA (no se toco `transitive_dependents()` en si, para no afectar a
  `impact_chain()`, consumidor pre-existente). **Verificado contra el mismo dominio Renting/
  Availability de Fases 3-9:** el impacto indirecto de `EquipmentViewSet.check_availability`
  incluye correctamente `availabilityService.check` (frontend real) y
  `ARQUITECTURA_COMPLETA_RENTIG` (documentacion real); `calculate_change_impact("Product")`
  resuelve al Model real (no a otro de los 459 matches por substring) con risk HIGH (496 nodos
  afectados, un modelo core de comercio). Disponible via CLI:
  `project-graph change-impact <target>`. 1 test nuevo de integracion real (sin unit tests
  sinteticos -- esta funcion es intrinsecamente una composicion de datos reales del grafo, no una
  logica de parsing aislada), 94/94 pasan. Sin cambios de nodos/aristas -- capa de consulta pura.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 9 "Configuration/Infrastructure Graph" del rediseno "Site Knowledge Graph
  / AI Editor Runtime" (22 fases, FASE 9 unicamente -- checkpoint obligatorio, continuando sin
  pausa de confirmacion por autorizacion previa del usuario). Objetivo: extender `EnvVar`/
  `DockerService` para conocer Environment, Docker, Nginx, Ports (9.1 del plan). Agregados 2 node
  types nuevos (`Port`, `NginxRoute`) y 3 aristas (`EXPOSES` DockerService->Port, `PROVIDES`
  DockerService->EnvVar, `ROUTES_TO` NginxRoute->DockerService), mas la consulta obligatoria
  `find_configuration_for(query)` (9.2). Nuevo enricher `knowledge_graph/enrichers/nginx.py`
  (lee `nginx-common.conf`, resuelve `proxy_pass` con o sin indireccion `set $var
  http://servicio:puerto;`). Extendido `enrichers/docker.py` para `ports:`/`env_file:` reales.
  **2 bugs reales encontrados y corregidos verificando contra datos reales, no en la primera
  pasada:**
  1. `.env.production.example` (la plantilla SIN secretos, unica fuente permitida para nombres
     de variable -- nunca `.env`/`.env.production` reales, que contienen secretos) vive DENTRO de
     `ecommerce_sintel/`, no en la raiz del repo -- la primera version buscaba en la raiz,
     nunca encontraba el archivo, `PROVIDES` quedaba en **0 aristas en TODO el grafo** en
     silencio hasta verificar explicitamente.
  2. El regex de `location` no anclaba a inicio de linea: matcheaba "location" como SUBSTRING
     dentro de `geolocation=()` (un header `Permissions-Policy` real de `nginx-common.conf`), y
     la captura no-greedy del path se extendia CIENTOS de lineas (incluyendo un header CSP
     completo con URLs de Wompi/Cloudflare) hasta el proximo `{` real -- un `NginxRoute` con todo
     ese texto como "path". Corregido anclando a inicio de linea y prohibiendo `\n` en la
     captura.
  **Verificado contra la configuracion real completa:** 8 `Port` (django:8000, db:5432,
  redis:6380, frontend:5173, nginx:80, sintel_ai:8100, sintel_ollama:11434,
  sintel_chromadb:8200); `django` PROVIDES 55 `EnvVar` reales (incluye `ANTHROPIC_API_KEY`,
  `DB_*`, `AI_SUPPORT_CHAT_ENABLED`); `nginx:/` -ROUTES_TO-> `docker:django` (correcto),
  `nginx:/api/v1/internal/` sin ROUTES_TO (bloqueado con `deny all`, correctamente sin
  enrutar). Grafo: 9561/20106 -> **9575/20335** (+14 nodos, +229 aristas). Disponible via CLI:
  `project-graph config-for <query>`. 9 tests nuevos (8 unit + 1 integracion real), 93/93 pasan.
  **Limitacion documentada**: "Feature Flags" (9.1 del plan) no se modelan aparte -- ya son
  `EnvVar` normales (ej. `AI_SUPPORT_CHAT_ENABLED`), sin distincion estructural de "esto es un
  flag" vs "esto es config regular" (ambos son variables booleanas leidas via `config()`, sin
  señal real en el codigo para diferenciarlas). "Configuracion frontend"
  (`import.meta.env.VITE_*`) sigue sin escanear, misma limitacion heredada de Fase 2 para
  `EnvVar` Python.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 8 "Documentation Graph" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 8 unicamente -- checkpoint obligatorio; a partir de aqui el usuario
  autorizo continuar el resto de fases sin pausa de confirmacion por fase, manteniendo el mismo
  rigor de evidencia real + checkpoint documentado). Objetivo: conectar documentacion con
  entidades concretas via `paths, symbols, endpoints` (8.1 del plan), no solo por coincidencia de
  nombre de app (`App -> DOCUMENTED_BY -> Documentation`, ya existente desde antes). Agregada
  `extract_doc_references()` (`knowledge_graph/enrichers/documentation.py`): extrae rutas de
  archivo, `Clase.metodo` y URLs de endpoint citadas entre BACKTICKS en la prosa de cada doc --
  convencion real verificada en `renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md`. Nueva
  arista `REFERENCES` (`Documentation -> File|Symbol|Endpoint`). Agregada la consulta obligatoria
  `find_docs_for_change(query)` (8.2), combinando resolucion estructural (nombre EXACTO de
  entidad real) con busqueda de texto libre sobre el contenido crudo de cada doc + scoring simple
  por relevancia -- **verificado con el ejemplo TEXTUAL EXACTO del plan**,
  `find_docs_for_change("renting availability")`, que devuelve `ARQUITECTURA_COMPLETA_RENTIG.md`
  como resultado #1. Un ajuste de diseño encontrado durante la propia verificacion: la primera
  version del scoring devolvia 41 resultados sin orden util (palabras comunes como
  "availability" aparecen en muchos docs no relacionados) -- corregido con un puntaje por
  ocurrencias + bonus si el query aparece en el NOMBRE del doc. Grafo: 9561/18790 -> **9561/20106**
  (sin nodos nuevos, +1316 aristas REFERENCES). Disponible via CLI:
  `project-graph docs-for <query>`. 7 tests nuevos (6 unit + 1 integracion real), 85/85 pasan.
  **Limitacion documentada**: no resuelve la forma abreviada real
  `` `EquipmentMarketingCommands.upsert()`/`.delete()` `` (el segundo metodo reusa
  implicitamente la clase del primero) -- solo la referencia EXPLICITA `Clase.metodo` se captura.
  Categorias del plan ("architecture/implementation/feature/audit docs") aproximadas via `scope`
  existente -- este proyecto no distingue "feature docs" como scope propio.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 7 "Test Graph" del rediseno "Site Knowledge Graph / AI Editor Runtime"
  (22 fases, FASE 7 unicamente -- checkpoint obligatorio, no se avanzo a FASE 8 en la misma
  pasada). Objetivo: conectar codigo, contratos y pruebas. Sin node types nuevos (Test/TestSuite/
  E2ETest/IntegrationTest/UnitTest, mencionados en 7.2 del plan) -- mismo criterio que Fase 3 con
  `FrontendSymbol`: un metodo de test YA es un `Symbol` real (`extract_symbols()` ya lo capturaba),
  solo faltaba marcarlo (`meta.is_test`, via `is_test_class()` -- clase con base `*TestCase`/
  `APITestCase`, o funcion de modulo `test_*` estilo pytest) y conectar 2 relaciones reales:
  `VALIDATES` (`Test-Symbol -> Endpoint`, via `self.client.verbo(url)` real -- DRF `APITestCase`,
  soporta f-strings via `extract_api_test_calls()`) y `TESTS` (`Test-Symbol -> Symbol`, via llamada
  directa `ClaseX.metodo(...)` dentro del test -- `extract_direct_symbol_calls()`, verificado en
  `renting/tests_endpoints.py`: `RentalRequestCommands.create_request(...)`).
  Agregada la consulta obligatoria `find_tests_for_change(target)` (`knowledge_graph/query.py`) --
  responde "que tests ejecutar si cambio esto" para un Symbol/Endpoint/Model, con `direct_tests`
  (aristas `TESTS`/`VALIDATES` directas) e `indirect_tests` (un salto real: Symbol implementado
  por un Endpoint -> tests que `VALIDATES` ese Endpoint; Model -> tests que `TESTS` un accesor
  directo O que `VALIDATES` un Endpoint cuyo `SERIALIZES` llega a ese Model).
  **Bug real encontrado y corregido durante la propia verificacion, no en la primera pasada**:
  `find_by_name('Product')` devuelve **460 matches** por substring en orden de iteracion de
  diccionario (no de relevancia: `ProductVariant`, `AdminProductRelationViewSet`,
  `FeaturedProductCardSerializer`, ...) -- el primer resultado de tipo Symbol/Endpoint/Model NUNCA
  era el Model `Product` real, siempre algo distinto que coincidia por casualidad de substring.
  Corregido priorizando coincidencia EXACTA de nombre antes de caer a la busqueda fuzzy.
  **Verificado contra 2 dominios reales distintos:** `ProductReviewDuplicatePreventionTestCase.
  test_second_review_blocked_by_serializer_validation` (`shop/tests.py`, `VALIDATES ->
  endpoint:api/v1/shop/products`, via `self.client.post(f'/api/v1/shop/products/{uuid}/review/',
  ...)`) y `RentalRequestAdminActionsTestCase.setUp` (`renting/tests_endpoints.py`, `TESTS ->
  RentalRequestCommands.create_request`/`.process_payment_selection`, llamadas directas). Muestreo
  aleatorio de 16 aristas reales (8 TESTS + 8 VALIDATES) sin ningun falso positivo. `find_tests_
  for_change('Product')` encuentra 0 tests por la ruta directa (ningun test llama
  `ProductSelector` directo -- honesto, no forzado) pero 5+ por la ruta `Serializer->Endpoint`
  (los tests reales de `shop/tests.py` que pegan al endpoint). Grafo: 9561/18265 -> **9561/18790**
  (sin nodos nuevos, +525 aristas: 96 VALIDATES + 429 TESTS). 857 Symbol marcados `is_test`.
  Disponible via CLI: `project-graph tests-for <Symbol|Endpoint|Model>`. 11 tests nuevos (10 unit +
  1 integracion real), 78/78 pasan.
  **Limitacion documentada, no omitida en silencio (7.1 del plan pedia "no limitarse a una
  carpeta... pytest, unittest, Django TestCase, API tests, integration tests, E2E, frontend
  tests")**: esta fase cubre SOLO tests **Python** (Django TestCase/APITestCase + pytest
  `test_*`, el patron dominante real verificado en las 21 apps). Tests frontend (Vitest
  `.test.js`, ej. `useToast.test.js`/`useTheme.test.js`/`usePaymentPolling.test.js` ya existentes
  en el repo) y E2E (Playwright, `frontend/playwright.config.js` + `ai_engine/e2e_ui/
  playwright.config.js` existen) quedan **PLANIFICADOS**, no implementados -- ambos usan sintaxis
  de bloque (`describe`/`it`/`test('...', () => {...})`) distinta a los patrones de funcion que
  ya reconoce `frontend_scanner.py`, requerirían un extractor nuevo dedicado.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 6 "Execution Graph" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 6 unicamente -- checkpoint obligatorio, no se avanzo a FASE 7 en la
  misma pasada). Objetivo: diferenciar DEPENDENCY (`DEPENDS_ON`/`IMPORTS`, "que necesita que para
  existir") de EXECUTION (orden real en que algo ocurre). Sin node type "ExecutionPath" persistido
  -- 6.1 del plan lo llama explicitamente "entidad DERIVADA", y con la cadena de Fases 0-5 ya
  construida, los 2 eslabones reales que faltaban eran `Model -> Signal` (que evento dispara que
  handler) y `Symbol -> Task` (que funcion encola que trabajo async). Agregadas 2 aristas:
  `TRIGGERS` (via `sender=X` real de `@receiver(...)`, ver `scanner/django_scanner.py::
  extract_signal_registrations`) y `QUEUES` (via `nombre_task.delay(...)`/`.apply_async(...)`
  real, ver `extract_task_queue_calls`). **Bug real PRE-EXISTENTE encontrado y corregido durante
  esta fase** (no introducido por ella): `is_task_function()` solo reconocia `@algo.shared_task
  (...)` (decorador via atributo) -- el patron REAL y dominante del proyecto es `@shared_task
  (bind=True, ...)` (llamada directa a un `Name`, no un `Attribute`), verificado en
  `notifications/tasks.py`: 8 funciones reales decoradas asi, TODAS invisibles (0 nodos `Task`
  para toda esa app) pese a que la deteccion de rol de archivo (`role=='task'`) ya funcionaba
  correctamente. Corregido: `Task` paso de 8 a **19** nodos (11 recuperados en varias apps, no
  solo notifications).
  Agregada la consulta obligatoria `trace_execution(start)` (`knowledge_graph/query.py`) --
  recorrido greedy que compone `CONSUMES_ENDPOINT -> IMPLEMENTED_BY -> CALLS -> WRITES_TO/
  READS_FROM -> TRIGGERS -> QUEUES`, con `also` listando en cada paso el resto de aristas reales
  no seguidas (sin esto, casos con mas de una consecuencia real perdian la rama mas relevante).
  **2 correcciones de diseño encontradas verificando contra casos reales, no en la primera
  version:**
  1. `IMPLEMENTED_BY` desde un `Endpoint` apunta a TODAS las acciones de su ViewSet (Fase 4: el
     Endpoint es el prefijo de router completo, no la URL de una `@action` individual) --
     `trace_execution('availabilityService.check')` elegia `EquipmentViewSet.get_object` (primero
     por orden de aparicion) en vez de `.check_availability` (la accion real de esa URL
     especifica). Corregido desambiguando por el ultimo segmento de la URL real que trae el
     Symbol de origen en su propio `meta.api_calls` (Fase 4).
  2. `CALLS` (Fase 0) vive a granularidad de CLASE (`ViewSet -> Service/Selector/Command`
     completos), no de metodo -- sin fallback, el recorrido se cortaba en CUALQUIER metodo de
     ViewSet que no toque Model/Task directo, el caso NORMAL en este proyecto (Service Layer
     obligatorio, ver `.AGENT.md`: "Prohibido logica de negocio en ViewSets"). Corregido con un
     fallback via `CONTAINS` (Fase 1) desde el Symbol-metodo hacia su clase ViewSet dueña, luego
     `CALLS` desde ahi.
  **Verificado contra 2 dominios reales distintos:** `NotificationCommands.dispatch_notification`
  (WRITES_TO `NotificationLog` + QUEUES 5 tasks reales segun canal -- las 5 solo visibles gracias
  a `also`, ya que `NotificationLog` no tiene salida propia y el algoritmo original se detenia
  ahi) y `availabilityService.check` (CONSUMES_ENDPOINT -> IMPLEMENTED_BY `EquipmentViewSet.
  check_availability` -- desambiguado correctamente -- -> CALLS `EquipmentCommands`, 4 pasos
  reales verificados). Grafo: 9550/18217 -> **9561/18265** (nodos +11 por el fix de Task,
  +48 aristas). Disponible via CLI: `project-graph execution <simbolo>`. 7 tests nuevos (6 unit +
  1 integracion real), 72/72 pasan.
  **Limitacion documentada, no omitida en silencio:** `trace_execution()` es un recorrido GREEDY
  de un solo camino principal (mas `also` de un nivel de profundidad), no un arbol exhaustivo de
  todas las ramas posibles; y el recorrido puede plateau en un nodo de CLASE (Command/Selector/
  Service) cuando no se sabe cual metodo especifico fue invocado dentro de esa clase (sin
  inferencia adicional, se detiene ahi en vez de adivinar).
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 5 "Data Flow Graph" del rediseno "Site Knowledge Graph / AI Editor
  Runtime" (22 fases, FASE 5 unicamente -- checkpoint obligatorio, no se avanzo a FASE 6 en la
  misma pasada). Objetivo: reconstruir `Model -> Selector -> Service/Command -> Serializer ->
  Endpoint -> Frontend API client -> Composable -> Store -> Component`. Siguiendo 5.1 del plan
  ("no necesariamente todos deben ser nodos nuevos... la prioridad es crear relaciones de
  flujo"): NO se agregaron node types nuevos -- la mayor parte de la cadena ya existia desde
  Fases 0-4 (Serializer->Model, ViewSet->Serializer, Endpoint->Serializer/Symbol,
  Symbol->Endpoint/Store/Composable). El unico eslabon real y demostrable que faltaba era
  `Selector/Service/Command -> Model` (nadie sabia que Model tocaba cada uno). Agregadas 2
  aristas nuevas: `READS_FROM`/`WRITES_TO` (`Symbol -> Model`, evidencia AST real del patron
  `Model.objects.verbo(...)`, ver `scanner/django_scanner.py::extract_model_manager_usages`) y
  la consulta obligatoria `trace_data_flow(target)` (`knowledge_graph/query.py`), que compone
  TODAS las aristas ya existentes (nuevas y previas) en un recorrido legible, sin logica nueva de
  grafo. De las 8 relaciones sugeridas en 5.2 del plan (READS_FROM, WRITES_TO, TRANSFORMS,
  SERIALIZES, DESERIALIZES, PASSES_TO, CONSUMES, RETURNS_TO) solo 2 se construyeron --
  TRANSFORMS/DESERIALIZES/PASSES_TO/CONSUMES/RETURNS_TO quedan fuera, documentado (Regla 3: "no
  agregar relaciones que no puedan demostrarse" -- estas requieren seguimiento de flujo de datos
  real entre expresiones, no solo presencia de un nombre en el AST). **1 bug real encontrado y
  corregido durante la propia implementacion** (no en la corrida final, sino verificando el
  primer resultado): la version inicial atribuia usos de modelo por nombre CRUDO de funcion
  (`func.name`), lo que mezclaba metodos homonimos de clases distintas en el mismo archivo --
  `shop/services/selectors.py` tiene tanto `ProductSelector.list_active()` como
  `TaxSelector.list_active()`, y la version con nombre crudo le atribuia lectura de `Tax` tambien
  a `ProductSelector.list_active()` (que nunca menciona `Tax`). Corregido matcheando por
  `qualified_name` (`Clase.metodo`), el MISMO esquema de identidad que ya usa `extract_symbols()`
  -- elimina la colision por construccion, no por parche puntual.
  **Verificado contra shop real** (dominio distinto de Renting/Availability usado en Fases 3-4,
  confirma el fix fuera de un solo caso): `ProductSelector.list_active` -READS_FROM-> `Product`
  (solo), `TaxSelector.list_active` -READS_FROM-> `Tax` (solo);
  `_get_or_create_stock_record` (`shop/services/commands.py`) -WRITES_TO-> `StockRecord`
  (cross-app real, modelo de `inventory`). `trace_data_flow("Product")` reconstruye la cadena
  completa real: 28 accesos backend, `ProductSerializer`, endpoint `api/v1/shop/products`,
  6 consumidores frontend reales incluyendo `shopService.js` (equivalente de shop al
  `availabilityService.js` de renting). `trace_data_flow("Product.name")` -> `field_verified:
  true` (campo real); `trace_data_flow("Product.image")` -> `field_verified: false` -- el
  ejemplo `Product.image` del plan original NO es literalmente reproducible en el esquema real
  de este proyecto (las imagenes viven en el modelo relacionado `ProductImage`, no como campo
  directo de `Product`), reportado honestamente en vez de simulado. Grafo: 9550/16953 ->
  **9550/18217** (nodos sin cambio, +1264 aristas). Disponible via CLI:
  `project-graph data-flow <Model|Model.campo>`. 9 tests nuevos (8 unit sintetico + 1
  integracion real), 65/65 pasan.
  **Limitacion documentada, no omitida en silencio**: `READS_FROM`/`WRITES_TO` no cubre cadenas
  donde el verbo de escritura llega despues de un verbo de lectura en la misma expresion
  (`Product.objects.filter(x=1).update(y=2)`) ni `instancia.save()`/`.delete()` sobre variables
  ya tipadas -- ambos requieren seguimiento de cadenas de llamada o inferencia de tipos, fuera de
  alcance de un scanner AST de una sola pasada. Es un PISO real verificado, no el 100% de los
  accesos reales del proyecto.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 4 "Contract Graph Frontend<->Backend" del rediseno "Site Knowledge Graph
  / AI Editor Runtime" (22 fases, FASE 4 unicamente -- checkpoint obligatorio, no se avanzo a
  FASE 5 en la misma pasada). Objetivo: conectar `Vue -> Composable/Store/API Client -> HTTP
  Contract -> Django Endpoint -> ViewSet/Symbol` a nivel de `Symbol` individual, no solo de
  archivo. Cubre las 5 relaciones de 4.3 del plan: `CONSUMES_ENDPOINT`/`USES_STORE` extendidas a
  `Symbol`, `USES_COMPOSABLE` (edge nueva), `SERIALIZES` (Endpoint->Serializer, edge nueva; ya
  existia Serializer->Model desde antes), `IMPLEMENTED_BY` (sin cambios, ya cubierta desde Fase
  2). **3 defectos reales encontrados y corregidos, verificados contra el repo real (no
  fixtures):**
  1. **`USES_STORE` tenia 0 aristas en TODO el grafo** -- el matching comparaba por substring un
     nombre derivado del hook (`useAvailabilityStore()` -> `"AvailabilityStore"`) contra el
     `store_id` de negocio (`"rentalAvailability"`), strings sin relacion textual garantizada.
     Fix: `extract_pinia_store()` gana `hook_name` real, `extract_use_hook_calls()` (reemplaza a
     `extract_vue_store_imports()`, retirada) captura el nombre completo del hook llamado, y el
     builder matchea EXACTO contra ambos lados.
  2. **La capa de "custom API wrapper" del proyecto (`frontend/src/services/**/*.js`, 10
     archivos, 69 llamadas reales) era invisible para el grafo**: `extract_vue_api_calls()` no
     reconocia el patron encadenado `useApi().get(url)` (solo `const api = useApi(); api.get()`),
     y esos archivos son objetos exportados planos (no Pinia stores), asi que tampoco generaban
     ningun `Symbol`. Fix: nuevo patron regex + `_extract_flat_exported_object_methods()`.
  3. **Encontrado verificando el fix del #2**: `_match_endpoints_for_url()` (heredado de antes de
     Fase 3) matcheaba `renting/equipment/{uuid}/check-availability/` contra
     `endpoint:api/v1/auth/availability` -- dominio no relacionado, solo por compartir el
     substring literal `"availability"` al final de ambas URLs. Causa raiz: `Endpoint.name` es el
     PREFIJO de router de un ViewSet completo, no la URL de cada `@action` individual. Fix:
     matching por PREFIJO real de la URL (no por ultimo-segmento-coincide) -- responde 4.4 del
     plan sin reconstruir cada `@action` como su propio Endpoint.
  **Verificado contra la cadena real completa** del mismo dominio Renting/Availability de Fase 3:
  `availabilityService.check` (Symbol) `-CONSUMES_ENDPOINT-> endpoint:api/v1/renting/equipment`
  `-IMPLEMENTED_BY-> EquipmentViewSet.check_availability` + `-SERIALIZES-> EquipmentSerializer` (y
  ~35 mas); y `ProductList.vue -USES_COMPOSABLE-> useToast/useErrorHandler/useOffcanvas` +
  `-USES_STORE-> shopAdmin` (dominio CRUD admin, distinto de Renting, confirma el fix fuera de un
  solo caso). Grafo: 9481/15863 -> **9550/16953** (nodos/aristas). 9 tests nuevos (9 unit sintetico
  + 1 integracion real), 60/60 pasan.
  **Limitacion documentada, no omitida en silencio**: `FrontendSymbol -> CALLS -> FrontendSymbol`
  (store action que delega a un service, ej. `availabilityStore.check()` -> llama a
  `availabilityService.check()`) NO se construyo -- fuera del alcance de 4.3 del plan, y el
  Symbol de la store action en si queda sin `CONSUMES_ENDPOINT` propio (solo lo tiene el Symbol
  del service al que delega). Tambien: `USES_STORE`/`USES_COMPOSABLE` a nivel de Symbol solo
  detectan un hook llamado DENTRO del cuerpo de ESE simbolo especifico -- el patron dominante real
  en componentes (`const toast = useToast();` a nivel de script, fuera de toda funcion) sigue sin
  atribuirse a ningun Symbol individual, solo al `File`/`FrontendComponent` completo (cobertura de
  archivo, no de funcion, para ese caso).
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 3 "Frontend Symbol Intelligence" del rediseno "Site Knowledge Graph / AI
  Editor Runtime" (nuevo prompt maestro de 22 fases, FASE 3 unicamente -- checkpoint obligatorio
  por fase, no se avanzo a FASE 4 en la misma pasada). `Symbol` se extiende a `.vue`/`.js`/`.ts`
  -- MISMO node type que Python (decision documentada: evita fragmentar queries entre `Symbol` y
  un `FrontendSymbol` aparte), distinguido por `meta.language` + 2 campos nuevos
  `meta.symbol_type`/`meta.role`. `scanner/frontend_scanner.py` gana
  `extract_frontend_symbols()`/`isolate_vue_script()` (extraccion heuristica via regex + balance
  de parentesis/llaves consciente de strings/comentarios -- no hay parser JS/TS real disponible
  ni se agrego una dependencia nueva solo para esto). `knowledge_graph/builder.py` NO cambio su
  logica de `CONTAINS` en `_add_one_file()` -- los simbolos frontend entran por el mismo
  `f["symbols"]` genérico que ya usaba Python, reusando el 100% de la maquinaria existente.
  **Bug real encontrado y corregido durante la propia implementacion** (no en la corrida contra
  el repo, sino en el primer test contra un patron real): el mecanismo de "skip overlapping
  matches" (necesario para que `catch`/`finally` anidados dentro de un metodo de Pinia no se
  contaran como simbolos propios) tambien suprimia funciones nombradas anidadas DENTRO de otra
  funcion exportada -- exactamente el patron dominante real de los composables de este proyecto
  (`useOperationTracking.js`: toda la logica vive anidada dentro de la funcion exportada). A
  diferencia de Python (que ignora deliberadamente el anidamiento), frontend SI debe capturarlo.
  Corregido quitando el overlap-skip de los 5 loops generales (cada patron tiene su propio
  anclaje/palabra clave, mutuamente excluyentes entre si, asi que no hay riesgo real de doble
  conteo) y dejandolo SOLO donde es necesario: `_extract_store_block_methods()` (metodos de
  `actions:`/`getters:` de un Pinia option-store, el unico lugar real del proyecto con sintaxis
  de metodo de objeto, ya que `frontend/CLAUDE.md` prohibe Options API en componentes). Segundo
  ajuste real, encontrado inspeccionando los datos reales tras la primera corrida completa: los
  lifecycle hooks (`onMounted`/`onUnmounted`) tambien matcheaban el patron de nombre de
  `event_handler` (`on` + mayuscula) y quedaban con `role` redundante ademas de
  `symbol_type="lifecycle"` -- corregido para que `symbol_type == "lifecycle"` tenga prioridad y
  no se evalue el nombre como event handler.
  **Verificado contra 3 archivos reales del dominio Renting/Availability** (el mismo dominio del
  ejemplo del plan): `store/renting/availabilityStore.js` (Pinia option-store real, 2 actions
  `check`/`fetchAvailability` con lineas exactas 10-15/16-21), `composables/
  useOperationTracking.js` (composable real: funcion exportada linea 5-81 + 5 funciones internas
  nombradas con `role="api_call"` correcto + 2 lifecycle hooks `onMounted`/`onUnmounted`, TODAS
  las lineas coinciden exactamente con el archivo real), `components/customer/renting/
  AvailabilityCard.vue` (componente real: `formattedDate` computed + 2 funciones planas, lineas
  exactas). Verificacion sistemica sobre los 2549 Symbol frontend reales: 0 rangos de linea
  invertidos, 0 nombres vacios, 0 palabras reservadas de JS coladas como simbolo, 0 IDs
  duplicados. Grafo completo: 6932/10833 -> **9481/15863** (nodos/aristas). `CLI node
  fetchAvailability` responde archivo+simbolo+lineas exactas sin busqueda manual (criterio de
  aceptacion 3.6 del plan), sin codigo de query nuevo -- `find_by_name()` ya generalizaba. 12
  tests nuevos (12 unit sinteticos + 1 integracion contra el repo real), 51/51 pasan.
  **Limitacion documentada, no omitida en silencio:** de los 9 `symbol_type` del plan se
  implementan 4 (`function`/`computed`/`watch`/`lifecycle`) + 3 `role` semanticos
  (`api_call`/`emit`/`event_handler`); `callback` (argumento anonimo sin nombre estable, sin
  `qualified_name` util) queda fuera. Getters de Pinia SI se implementaron (no estaban en el
  scope original del plan, agregado por ser la misma sintaxis que `actions:` con costo marginal
  bajo). `FrontendSymbol -> CALLS -> FrontendSymbol`, `CONSUMES_ENDPOINT`/`USES_STORE`/
  `USES_COMPOSABLE` desde `FrontendSymbol` (seccion 3.4 del plan) quedan para FASE 4 "Contract
  Graph Frontend<->Backend" -- no se avanzo a esa fase en esta pasada.
  **CHECKPOINT: PASS.**
- **2026-08-10** — FASE 2 "Contract Graph" del rediseno "Site Knowledge Graph / AI Editor
  Runtime": agregados los node types `WebSocketRoute` y `EnvVar` + arista `IMPLEMENTED_BY`
  (Endpoint->Symbol, WebSocketRoute->Consumer) y `USES_ENV` (File->EnvVar) -- ver seccion 4.
  De los 7 sub-tipos del plan original solo estos 2 se construyeron; PayloadSchema/
  ResponseSchema ya estaban cubiertos por `Serializer`, EventContract/DatabaseContract quedaron
  fuera (ambiguos en el plan, parcialmente cubiertos por `Signal`/`DEPENDS_ON`), decision
  documentada en el codigo (`knowledge_graph/builder.py::_infer_contract_edges`), no omitida en
  silencio. **Bug real encontrado y corregido en la primera corrida contra el repo:**
  `extract_websocket_patterns()` solo reconocia `path()` -- `operations/routing.py` (el unico
  consumer real de `operations`, `OperationTrackingConsumer`) usa `re_path()` con una ruta con
  parametro, y quedaba fuera del grafo en silencio hasta que se verifico contra datos reales
  (no contra un fixture sintetico). Verificado: `ws/support/chat/` -> `SupportChatConsumer`
  (el mismo consumer auditado en vivo en la sesion de diagnostico del chatbot), 4
  `WebSocketRoute` reales, `AI_SUPPORT_CHAT_ENABLED` -> `ecommerce/settings/base.py` (el flag
  real que `is_ai_mode_active()` lee). Grafo completo: 6860/10283 -> 6932/10833 (nodos/aristas).
  7 tests nuevos (26 previos de Fase 0-1 + 6 unit + 1 integracion), 40/40 pasan.
- **2026-08-10** — FASE 1 del rediseno "Site Knowledge Graph / AI Editor Runtime": agregados
  los node types `File` y `Symbol` (ver seccion 4) + arista `CONTAINS`. `scanner/python_scanner.py`
  gano `extract_symbols()` (funciones/metodos con rango de lineas exacto) y `file_stats()`
  (lineas + hash de contenido); `scanner/project_scanner.py` los conecta en `scan_app()`/
  `scan_frontend_file()`; `knowledge_graph/builder.py::_add_files_and_symbols()` construye los
  nodos y las aristas `File->Symbol`/`File->cualquier nodo en ese archivo`/`Clase->su metodo`.
  Verificado contra el repo real: 1161 File, 3778 Symbol, KG paso de 1923/3291 a 6860/10283
  nodos/aristas. `CodeSegment` del plan original se dejo fuera a proposito (ver seccion 4,
  seria casi 1:1 con `Symbol` sin fingerprint semantico real). Frontend no tiene `Symbol`
  todavia, tambien a proposito. 33 tests (26 previos + 7 nuevos) pasan.
- **2026-08-10** — FASE 0 del rediseno "Site Knowledge Graph / AI Editor Runtime": se retiro
  la dependencia que `ai_engine` tenia de este modulo desde Fase 17-18 (4 archivos +
  `pkg_bootstrap.py` + delegacion en `incremental_updater.py`). Regla adoptada: "AI Engine no
  conoce ni importa project_knowledge_graph". Cero archivos de `project_knowledge_graph` se
  tocaron -- el trabajo fue enteramente del lado de `ai_engine` (ver `ai_engine/.AGENT/
  AI_ENGINE_KG_DECOUPLING_FASE0.md` para la matriz exacta). Ver seccion 9 (actualizada) para el
  estado final: cero consumidores reales hoy.
- **2026-08-09** — Extraccion completa desde `ai_engine/` (`PLAN_MAESTRO_DE_SEPARACION_PROJECT_
  KNOWLEDGE_GRAPH`, ejecutado completo fase por fase con 2 checkpoints, verificado end-to-end
  contra el repo real en cada fase). Los 9 archivos planos viejos de `ai_engine` (`project_map.py`,
  `knowledge_graph.py`, `dependency_graph.py`, `auditor.py`, `agent_graph.py`, `docker_graph.py`,
  `documentation_graph.py`, `graph_validator.py`, `graph_visualizer.py`) se borraron. Ver
  `PROJECT_KNOWLEDGE_GRAPH_INVENTORY.md` (este mismo directorio) para el inventario fisico previo
  a mover cualquier archivo, y `ecommerce_sintel/MEMORY.md` (entrada 2026-08-09) para el resumen
  de continuidad entre sesiones.
