"""
Consultas sobre el Knowledge Graph. Extraido de ai_engine/knowledge_graph.py
(Fase 5, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).
Usado por el CLI (`project-graph node`/`project-graph impact`). [ACTUALIZADO
2026-08-10, FASE 0] GraphImpactAnalysisTool (ai_engine/tools/graph_tools.py,
el otro consumidor historico) se retiro por completo -- ver ai_engine/.AGENT/
AI_ENGINE_KG_DECOUPLING_FASE0.md.
"""
from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph


def find_node_context(entity_name: str, depth: int = 2) -> dict:
    """Vecindario del knowledge graph de una entidad por nombre."""
    kg = get_knowledge_graph()
    matches = kg.find_by_name(entity_name)
    if not matches:
        return {"found": False, "entity": entity_name}
    node = matches[0]
    return {
        "found": True,
        "node": node.to_dict(),
        "neighborhood": kg.neighborhood(node.id, depth),
        "depends_on": [kg.nodes[nid].to_dict() for nid in kg.what_this_uses(node.id) if nid in kg.nodes],
        "depended_by": [kg.nodes[nid].to_dict() for nid in kg.what_depends_on(node.id) if nid in kg.nodes],
    }


def impact_chain(entity_name: str) -> list[dict]:
    """Cadena completa de impacto transitivo: todos los nodos afectados si
    entity_name cambia."""
    kg = get_knowledge_graph()
    matches = kg.find_by_name(entity_name)
    if not matches:
        return []
    node = matches[0]
    affected_ids = kg.transitive_dependents(node.id, max_depth=5)
    return [kg.nodes[nid].to_dict() for nid in affected_ids if nid in kg.nodes]


def trace_data_flow(target: str) -> dict:
    """Fase 5 "Data Flow Graph" (Site Knowledge Graph, 2026-08-10): consulta
    obligatoria del plan (5.4) -- reconstruye `database -> serializer -> API
    -> frontend -> component` para un Model o `Model.campo` dado, SIN
    agregar node/edge types nuevos: compone aristas que ya existen
    (READS_FROM/WRITES_TO de esta misma fase, mas SERIALIZES/
    CONSUMES_ENDPOINT/USES_STORE/USES_COMPOSABLE/CONTAINS de fases
    anteriores). `target` acepta `"Product"` o `"Product.image"` -- con
    campo, se verifica (no se asume) que ese campo este realmente declarado
    en `Model.meta['fields']`, y el resultado incluye `field_verified` para
    que el llamador sepa si la verificacion fue posible o no.

    Ruta deliberada: Model <-SERIALIZES- Serializer <-SERIALIZES- Endpoint
    <-CONSUMES_ENDPOINT- Symbol(frontend), NO via `ViewSet -CALLS->
    Selector/Service` (esa arista es heuristica de coincidencia de nombre,
    menos confiable que SERIALIZES, que es 1:1 real). `backend_access`
    (quien LEE/ESCRIBE el modelo) se reporta aparte via READS_FROM/
    WRITES_TO -- son evidencia real pero no necesariamente pasan por el
    MISMO Serializer/Endpoint que expone el modelo al frontend (ver
    limitacion documentada en ARQUITECTURA_COMPLETA_GRAFO.md seccion 11)."""
    kg = get_knowledge_graph()
    model_name, _, field_name = target.partition(".")
    field_name = field_name or None

    model_candidates = [n for n in kg.nodes_of_type("Model") if n.name == model_name]
    if not model_candidates:
        return {"found": False, "target": target}
    model_node = model_candidates[0]

    # model_node.meta["fields"] es list[{"name": ..., "field_type": ..., ...}]
    # (ver django_scanner.py::extract_model_fields), no una lista de strings
    # -- comparar contra f["name"], no "in" directo sobre la lista de dicts.
    field_verified = (
        any(f.get("name") == field_name for f in model_node.meta.get("fields", []))
        if field_name else None
    )

    backend_access = []
    for p in kg.predecessors(model_node.id):
        if p["edge"] in ("READS_FROM", "WRITES_TO"):
            backend_access.append({"symbol": p["node"], "access": p["edge"]})

    serializers = [p["node"] for p in kg.predecessors(model_node.id) if p["edge"] == "SERIALIZES"]

    endpoints, endpoint_ids = [], set()
    for s in serializers:
        for p in kg.predecessors(s["id"]):
            if p["edge"] == "SERIALIZES" and p["node"]["type"] == "Endpoint" and p["node"]["id"] not in endpoint_ids:
                endpoint_ids.add(p["node"]["id"])
                endpoints.append(p["node"])

    frontend_consumers, fe_ids = [], set()
    for ep in endpoints:
        for p in kg.predecessors(ep["id"]):
            if p["edge"] == "CONSUMES_ENDPOINT" and p["node"]["id"] not in fe_ids:
                fe_ids.add(p["node"]["id"])
                frontend_consumers.append(p["node"])

    stores, composables, components, seen = [], [], [], set()
    for fs in frontend_consumers:
        for s in kg.successors(fs["id"]):
            if s["node"]["id"] in seen:
                continue
            if s["edge"] == "USES_STORE":
                seen.add(s["node"]["id"]); stores.append(s["node"])
            elif s["edge"] == "USES_COMPOSABLE":
                seen.add(s["node"]["id"]); composables.append(s["node"])
        for p in kg.predecessors(fs["id"]):
            if p["edge"] == "CONTAINS" and p["node"]["type"] in ("FrontendComponent", "FrontendView") \
                    and p["node"]["id"] not in seen:
                seen.add(p["node"]["id"])
                components.append(p["node"])

    return {
        "found": True,
        "target": target,
        "field": field_name,
        "field_verified": field_verified,
        "database": model_node.to_dict(),
        "backend_access": backend_access,
        "serializers": serializers,
        "api": endpoints,
        "frontend_consumers": frontend_consumers,
        "stores": stores,
        "composables": composables,
        "components": components,
    }


# ---- Execution Graph (Fase 6, Site Knowledge Graph, 2026-08-10) -----------

_EXECUTION_EDGE_PRIORITY = [
    "CONSUMES_ENDPOINT", "IMPLEMENTED_BY", "CALLS",
    "WRITES_TO", "READS_FROM", "TRIGGERS", "QUEUES",
]


def trace_execution(start: str, max_steps: int = 8) -> dict:
    """Fase 6 "Execution Graph" (Site Knowledge Graph, 2026-08-10): consulta
    obligatoria del plan (6.2) -- reconstruye un ExecutionPath numerado
    (6.1: "USER ACTION -> FRONTEND EVENT -> FUNCTION -> API -> VIEW ->
    SERVICE -> DATABASE -> EVENT -> NOTIFICATION") a partir de un punto de
    partida (`start`: nombre o id de un Symbol, tipicamente un handler de
    frontend como `RentalCheckout.submit`), SIN crear un node type
    "ExecutionPath" persistido -- 6.1 del plan lo llama explicitamente
    "entidad DERIVADA", y este grafo ya tiene todas las aristas reales
    necesarias (CONSUMES_ENDPOINT/IMPLEMENTED_BY/CALLS de fases 2-4,
    READS_FROM/WRITES_TO de fase 5, TRIGGERS/QUEUES de esta fase).

    Algoritmo: recorrido GREEDY por el camino PRINCIPAL, pero cada paso
    tambien reporta `also` -- el resto de aristas de ejecucion reales desde
    ese mismo nodo que NO se siguieron, sin las cuales una operacion real
    con mas de una consecuencia queda incompleta. [DISEÑO CORREGIDO durante
    la propia verificacion, no la primera version]: la primera version solo
    seguia una arista por nodo y se detenia en un callejon sin salida --
    verificado contra el caso real `NotificationCommands.
    dispatch_notification`, que ADEMAS de escribir `NotificationLog`
    (WRITES_TO, primer hop por prioridad) encola 5 tasks reales via QUEUES;
    sin `also`, esas 5 tasks (la parte mas relevante de "que pasa" para
    este caso) quedaban invisibles porque `NotificationLog` no tiene
    salida propia. El camino principal sigue eligiendo la PRIMERA arista
    disponible segun `_EXECUTION_EDGE_PRIORITY` (el orden real en que una
    peticion normalmente avanza), `also` lista el resto en el MISMO orden
    de prioridad. Una ejecucion real puede ramificarse mas alla de esto
    (un ViewSet.create puede CALL a mas de un Service) -- `also` solo
    reporta un nivel de profundidad, no recursivo; documentado, no
    aspiracional. Corta el camino principal al llegar a `max_steps` o
    cuando no queda ninguna arista de las 7 reconocidas.

    Desambiguacion IMPLEMENTED_BY por URL [encontrado y corregido durante
    la propia verificacion]: un `Endpoint` es el prefijo de router de TODO
    un ViewSet (ver Fase 4), asi que `IMPLEMENTED_BY` desde el Endpoint
    apunta a TODAS sus acciones (`get_object`, `check_availability`,
    `availability`, `calendar`, ...), no solo la que realmente llamo el
    Symbol de origen -- verificado real: `availabilityService.check()`
    elegia `EquipmentViewSet.get_object` (el primero por orden de
    aparicion) en vez de `.check_availability` (la accion real de esa URL
    especifica). Fix: si el Symbol de origen trae `api_calls` en su meta
    (Fase 4), se usa el ULTIMO segmento de esa URL (hyphen->underscore)
    como criterio de desempate SOLO para el primer hop `IMPLEMENTED_BY`
    inmediatamente despues de un `CONSUMES_ENDPOINT` -- no cambia el
    matching de Endpoint en si (eso sigue siendo Fase 4), solo la eleccion
    ENTRE las acciones ya vinculadas a ese mismo Endpoint."""
    kg = get_knowledge_graph()
    matches = kg.find_by_name(start)
    symbol_matches = [n for n in matches if n.type == "Symbol"]
    node = symbol_matches[0] if symbol_matches else (matches[0] if matches else None)
    if node is None:
        return {"found": False, "start": start}

    def _execution_hops(node_id: str, visited: set) -> list[dict]:
        raw = [{"via": s["edge"], "node": s["node"]} for s in kg.successors(node_id)
               if s["edge"] in _EXECUTION_EDGE_PRIORITY]
        # Fallback CALLS a nivel de clase [encontrado y corregido durante la
        # verificacion]: CALLS (Fase 0) vive a granularidad de CLASE
        # (ViewSet -> Service/Selector/Command completos), no de metodo --
        # sin este fallback, el recorrido se cortaba en CUALQUIER metodo de
        # ViewSet que no toque Model/Task directo, que es el caso NORMAL en
        # este proyecto (Service Layer obligatorio: "Prohibido logica de
        # negocio en ViewSets", ver .AGENT.md) -- verificado real:
        # EquipmentViewSet.check_availability no tiene READS_FROM/WRITES_TO
        # propio, la logica real vive en un Selector/Service que el ViewSet
        # (la CLASE, no el metodo) SI tiene linkeado via CALLS.
        this_node = kg.nodes.get(node_id)
        if this_node and this_node.type == "Symbol" and this_node.meta.get("class_name"):
            for p in kg.predecessors(node_id):
                if p["edge"] == "CONTAINS" and p["node"]["type"] == "ViewSet":
                    for s in kg.successors(p["node"]["id"]):
                        if s["edge"] == "CALLS":
                            raw.append({"via": "CALLS", "node": s["node"]})
        hops = [h for h in raw if h["node"]["id"] not in visited]
        hops.sort(key=lambda h: _EXECUTION_EDGE_PRIORITY.index(h["via"]))
        return hops

    def _pick_by_url_hint(hops: list[dict], url_hint: str) -> dict | None:
        target = url_hint.strip("/").split("/")[-1].replace("-", "_")
        for h in hops:
            if h["via"] == "IMPLEMENTED_BY" and h["node"]["name"].split(".")[-1] == target:
                return h
        return None

    steps = [{"step": 1, "node": node.to_dict(), "via": None, "also": []}]
    visited = {node.id}
    current_id = node.id
    url_hint = None
    if node.type == "Symbol":
        api_calls = node.meta.get("api_calls") or []
        if api_calls:
            url_hint = api_calls[0].get("url")

    for i in range(2, max_steps + 1):
        hops = _execution_hops(current_id, visited)
        if not hops:
            break
        primary = None
        if url_hint and hops[0]["via"] == "IMPLEMENTED_BY":
            primary = _pick_by_url_hint(hops, url_hint)
            url_hint = None  # se usa una sola vez, en el hop inmediato tras CONSUMES_ENDPOINT
        primary = primary or hops[0]
        also = [h for h in hops if h is not primary]
        steps.append({"step": i, "node": primary["node"], "via": primary["via"], "also": also})
        visited.add(primary["node"]["id"])
        current_id = primary["node"]["id"]

    return {"found": True, "start": start, "steps": steps}


# ---- Test Graph (Fase 7, Site Knowledge Graph, 2026-08-10) ----------------

def find_tests_for_change(target: str) -> dict:
    """Fase 7 "Test Graph" (Site Knowledge Graph, 2026-08-10): consulta
    obligatoria del plan (7.4) -- "que pruebas debo ejecutar si cambio este
    simbolo?". `target` puede ser un Symbol, Endpoint o Model (por nombre).

    `direct_tests`: tests con `TESTS`/`VALIDATES` apuntando DIRECTO al
    nodo -- evidencia real de que ese test llama a ese Symbol o pega a ese
    Endpoint.

    `indirect_tests`: cobertura de UN salto real mas alla de lo directo
    (no exhaustivo/transitivo completo, documentado -- una busqueda
    verdaderamente exhaustiva requeriria BFS por TODAS las aristas de
    ejecucion de Fase 6, mezclando conceptos de fases distintas):
      - Si `target` es un Symbol implementado por un Endpoint
        (`Endpoint -IMPLEMENTED_BY-> Symbol`), los tests que
        `VALIDATES` ese MISMO Endpoint tambien ejercitan este Symbol
        indirectamente (via HTTP, no llamada directa).
      - Si `target` es un Model: (a) tests que `TESTS` un Symbol que
        `READS_FROM`/`WRITES_TO` ese Model (unit-test-style, llama a la
        capa de Service directo) y (b) tests que `VALIDATES` un Endpoint
        cuyo `SERIALIZES` llega a ese Model (integration-test-style via
        API client) -- verificado real: `Product` tiene 0 resultados por
        (a) (ningun test llama `ProductSelector` directo) pero 5+ por (b),
        via `ProductSerializer` -> `endpoint:api/v1/shop/products` -> los
        tests reales de `shop/tests.py` que pegan a ese endpoint.

    Resolucion de `target` [CORREGIDO -- bug real encontrado, no una
    reescritura preventiva]: prefiere coincidencia EXACTA de nombre antes
    que la busqueda fuzzy de `find_by_name()`. Verificado real:
    `find_by_name('Product')` devuelve 460 matches por substring
    (`ProductVariant`, `AdminProductRelationViewSet`, `FeaturedProductCard
    Serializer`, ...) en orden de iteracion de diccionario, no de
    relevancia -- el primer resultado de tipo Symbol/Endpoint/Model no era
    nunca el Model `Product` real, siempre algo distinto que coincidia por
    casualidad de substring."""
    kg = get_knowledge_graph()
    exact = [n for n in kg.nodes.values()
             if n.name == target and n.type in ("Symbol", "Endpoint", "Model")]
    node = exact[0] if exact else next(
        (n for n in kg.find_by_name(target) if n.type in ("Symbol", "Endpoint", "Model")), None)
    if node is None:
        return {"found": False, "target": target}

    direct_tests = {p["node"]["id"]: p["node"] for p in kg.predecessors(node.id)
                     if p["edge"] in ("TESTS", "VALIDATES")}

    indirect_tests: dict = {}
    if node.type == "Symbol":
        for p in kg.predecessors(node.id):
            if p["edge"] != "IMPLEMENTED_BY":
                continue
            endpoint_id = p["node"]["id"]
            for pp in kg.predecessors(endpoint_id):
                if pp["edge"] == "VALIDATES" and pp["node"]["id"] not in direct_tests:
                    indirect_tests[pp["node"]["id"]] = pp["node"]
    elif node.type == "Model":
        # Ruta 1: tests que TESTS un Symbol que READS_FROM/WRITES_TO este
        # Model directo (unit-test-style, llama a la capa de Service).
        for p in kg.predecessors(node.id):
            if p["edge"] not in ("READS_FROM", "WRITES_TO"):
                continue
            accessor_id = p["node"]["id"]
            for pp in kg.predecessors(accessor_id):
                if pp["edge"] == "TESTS" and pp["node"]["id"] not in direct_tests:
                    indirect_tests[pp["node"]["id"]] = pp["node"]
        # Ruta 2: Model <-SERIALIZES- Serializer <-SERIALIZES- Endpoint
        # <-VALIDATES- Test (integration-test-style via API client) --
        # verificado real: Product tiene 0 resultados por Ruta 1 (ningun
        # test llama ProductSelector directo) pero 5+ por esta ruta
        # (ProductReviewDuplicatePreventionTestCase y otros, todos via
        # self.client contra /api/v1/shop/products/).
        for p in kg.predecessors(node.id):
            if p["edge"] != "SERIALIZES":
                continue
            serializer_id = p["node"]["id"]
            for pp in kg.predecessors(serializer_id):
                if pp["edge"] != "SERIALIZES":
                    continue
                endpoint_id = pp["node"]["id"]
                for ppp in kg.predecessors(endpoint_id):
                    if ppp["edge"] == "VALIDATES" and ppp["node"]["id"] not in direct_tests:
                        indirect_tests[ppp["node"]["id"]] = ppp["node"]

    return {
        "found": True,
        "target": target,
        "node": node.to_dict(),
        "direct_tests": list(direct_tests.values()),
        "indirect_tests": list(indirect_tests.values()),
    }


# ---- Documentation Graph (Fase 8, Site Knowledge Graph, 2026-08-10) -------

_DOC_SCOPE_TO_CATEGORY = {
    "nivel2": "implementation_docs",
    "arquitectura": "architecture_docs",
    "auditoria": "audit_docs",
}


def find_docs_for_change(query: str) -> dict:
    """Fase 8 "Documentation Graph" (Site Knowledge Graph, 2026-08-10):
    consulta obligatoria del plan (8.2) -- `find_docs_for_change("renting
    availability")` debe devolver "architecture docs, implementation docs,
    feature docs, audit docs". Combina 2 rutas reales, no solo una (el
    query del plan es texto libre de 2+ palabras, no siempre el nombre
    EXACTO de una entidad):

    1. **Estructural**: si `query` coincide EXACTO con el nombre de un
       Symbol/Endpoint/Model/File/App real, se devuelven los docs
       conectados via `REFERENCES` (cita directa de esa entidad) o
       `DOCUMENTED_BY` (doc de esa app).
    2. **Texto libre**: cada palabra de `query` (2+ caracteres) se busca
       (substring, case-insensitive) en el contenido crudo de cada
       `Documentation` -- el `query` del ejemplo del plan ("renting
       availability") no es el nombre de NINGUNA entidad real, es una
       descripcion de feature en prosa libre; sin esta ruta la consulta
       devolveria vacio para el ejemplo textual del propio plan.

    Categorizado por `meta.scope` de cada doc (`nivel2` -> `
    implementation_docs`, `arquitectura` -> `architecture_docs`,
    `auditoria` -> `audit_docs`) -- aproximacion de las 4 categorias del
    plan ("architecture/implementation/feature/audit docs"): este proyecto
    no distingue "feature docs" como scope propio, los docs de feature
    reales viven mezclados dentro de `nivel2` (docs por app) -- documentado,
    no una categoria inventada."""
    kg = get_knowledge_graph()
    matches_by_id: dict[str, dict] = {}

    # Ruta 1: estructural, coincidencia EXACTA de nombre (mismo criterio
    # que el fix de Fase 7 -- find_by_name() por si solo no es confiable).
    exact = [n for n in kg.nodes.values()
             if n.name == query and n.type in ("Symbol", "Endpoint", "Model", "File", "App")]
    for node in exact:
        if node.type == "App":
            # DOCUMENTED_BY va App -> Documentation: los docs de esta app
            # son SUCESORES del nodo App, no predecesores.
            for s in kg.successors(node.id):
                if s["edge"] == "DOCUMENTED_BY" and s["node"]["type"] == "Documentation":
                    matches_by_id[s["node"]["id"]] = s["node"]
            continue
        # REFERENCES va Documentation -> entidad: los docs que citan esta
        # entidad son PREDECESORES del nodo (Symbol/Endpoint/Model/File).
        for p in kg.predecessors(node.id):
            if p["edge"] == "REFERENCES" and p["node"]["type"] == "Documentation":
                matches_by_id[p["node"]["id"]] = p["node"]

    # Ruta 2: texto libre sobre el contenido crudo de cada doc. Puntaje
    # simple = ocurrencias totales de las palabras del query + bonus si el
    # NOMBRE del doc (no solo el cuerpo) contiene alguna -- sin esto,
    # palabras comunes ("availability" aparece en varias apps sin relacion
    # directa) devuelven una lista larga sin orden util; con el puntaje, el
    # doc realmente relevante (ej. ARQUITECTURA_COMPLETA_RENTIG.md para
    # "renting availability") queda primero, verificado real.
    scores: dict[str, int] = {}
    words = [w.lower() for w in query.split() if len(w) >= 2]
    if words:
        from project_knowledge_graph.knowledge_graph.enrichers.documentation import REPO_ROOT

        for doc_node in kg.nodes_of_type("Documentation"):
            if doc_node.id in matches_by_id:
                continue
            doc_path = REPO_ROOT / doc_node.file
            try:
                text = doc_path.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            if not all(w in text for w in words):
                continue
            matches_by_id[doc_node.id] = doc_node.to_dict()
            name_lower = doc_node.name.lower()
            scores[doc_node.id] = sum(text.count(w) for w in words) + \
                sum(10 for w in words if w in name_lower)

    categorized: dict[str, list] = {"architecture_docs": [], "implementation_docs": [], "audit_docs": []}
    for doc_id, doc in matches_by_id.items():
        category = _DOC_SCOPE_TO_CATEGORY.get(doc["meta"]["scope"], "implementation_docs")
        categorized[category].append(doc)
    for category in categorized:
        categorized[category].sort(key=lambda d: scores.get(d["id"], 1_000_000), reverse=True)

    return {"found": bool(matches_by_id), "query": query, **categorized}


# ---- Configuration/Infrastructure Graph (Fase 9, Site Knowledge Graph, ----
# 2026-08-10) -----------------------------------------------------------

def find_configuration_for(query: str) -> dict:
    """Fase 9 "Configuration/Infrastructure Graph" (Site Knowledge Graph,
    2026-08-10): consulta obligatoria (9.2) -- "¿donde esta configurada
    esta funcionalidad?". Combina, por substring case-insensitive contra
    `query`: `EnvVar` reales (Fase 2), `DockerService` (`docker-compose.yml`),
    `NginxRoute` (Fase 9, `nginx-common.conf`), y `File` de settings de
    Django (`*/settings*.py`) cuyo path menciona `query`. No incluye
    "frontend config" como categoria propia -- `import.meta.env.VITE_*` no
    esta escaneado todavia (misma limitacion documentada desde Fase 2 para
    `EnvVar`)."""
    kg = get_knowledge_graph()
    q = query.lower()

    env_vars = [n.to_dict() for n in kg.nodes_of_type("EnvVar") if q in n.name.lower()]
    docker_services = [n.to_dict() for n in kg.nodes_of_type("DockerService") if q in n.name.lower()]
    nginx_routes = [n.to_dict() for n in kg.nodes_of_type("NginxRoute") if q in n.name.lower()]
    settings_files = [n.to_dict() for n in kg.nodes_of_type("File")
                       if "settings" in n.file.lower() and q in n.file.lower()]

    return {
        "found": bool(env_vars or docker_services or nginx_routes or settings_files),
        "query": query,
        "env": env_vars,
        "docker": docker_services,
        "nginx": nginx_routes,
        "settings_files": settings_files,
    }


# ---- Change Graph (Fase 10, Site Knowledge Graph, 2026-08-10) -------------
#
# "Esta es la fase critica" (10 del plan). Alcance deliberado, no una
# omision silenciosa: NO se implementa un parser de lenguaje natural que
# convierta "Agregar alquiler por horas" en `ChangeIntent` estructurado
# (10.2) -- eso requiere un LLM real (el futuro "AI Editor Runtime", Fase
# 14 del plan, explicitamente fuera de `ai_engine` y de este modulo
# puramente estatico), no algo que un scanner AST/regex pueda hacer de
# forma honesta. Lo que SI es 100% real y demostrable con lo ya construido
# en Fases 0-9: `ChangeTarget` (10.3, resolver un nombre de entidad real) y
# `AffectedNode` (10.4, calcular impacto DIRECTO/INDIRECTO categorizado en
# frontend/backend/contract/test/documentation/configuration) --
# `calculate_change_impact()` abajo compone TODAS las consultas ya
# construidas (trace_data_flow/trace_execution/find_tests_for_change/
# find_docs_for_change/find_configuration_for + transitive_dependents ya
# existente desde antes de esta fase) en un solo resultado categorizado.

_FRONTEND_NODE_TYPES = {"FrontendComponent", "FrontendView", "PiniaStore", "Composable", "Route"}
_BACKEND_NODE_TYPES = {"Model", "Serializer", "ViewSet", "Command", "Selector", "Service",
                        "Signal", "Consumer", "Task", "Permission", "ManagementCommand"}
_CONTRACT_NODE_TYPES = {"Endpoint", "WebSocketRoute"}
_CONFIG_NODE_TYPES = {"EnvVar", "DockerService", "Port", "NginxRoute"}


def resolve_change_target(query: str) -> dict | None:
    """`ChangeTarget` (10.3 del plan): resuelve `query` a una entidad real
    del grafo. Mismo criterio EXACTO-antes-que-fuzzy que corrigio el bug
    real de Fase 7/8 (`find_by_name()` sola no es confiable con nombres
    comunes) -- no se reinventa, se reusa."""
    kg = get_knowledge_graph()
    exact = [n for n in kg.nodes.values() if n.name == query]
    if exact:
        return exact[0].to_dict()
    fuzzy = kg.find_by_name(query)
    return fuzzy[0].to_dict() if fuzzy else None


# CONTAINS/BELONGS_TO son ESTRUCTURALES (File contiene su Symbol, ViewSet
# contiene su propio metodo, Model pertenece a su App) -- no representan
# "esto se rompe si cambio el target". [ENCONTRADO Y CORREGIDO durante la
# propia verificacion, no en la primera pasada]: usar el `transitive_
# dependents()`/`what_depends_on()` genericos (que no filtran por tipo de
# arista) hacia un Symbol de metodo devolvia su propia clase ViewSet como
# "impacto directo" -- verificado real con `EquipmentViewSet.
# check_availability` (el ViewSet "depende" de contener el metodo, no es
# impacto funcional). `_functional_dependents()` excluye ambas explicitamente.
_STRUCTURAL_EDGE_LABELS = {"CONTAINS", "BELONGS_TO"}


def _functional_dependents(kg, node_id: str, max_depth: int = 5) -> tuple[set, set]:
    """Igual forma que `KnowledgeGraph.transitive_dependents()` pero
    devuelve (directos, todos) separados y excluye aristas estructurales.
    No se modifica `transitive_dependents()`/`what_depends_on()` en si
    (otros consumidores, ej. `impact_chain()`, siguen funcionando igual) --
    esta es una funcion NUEVA, propia de Fase 10."""
    direct = {e.source for e in kg.edges if e.target == node_id and e.label not in _STRUCTURAL_EDGE_LABELS}
    all_affected = set(direct)
    frontier = list(direct)
    for _ in range(max_depth - 1):
        next_frontier = []
        for nid in frontier:
            for d in {e.source for e in kg.edges if e.target == nid and e.label not in _STRUCTURAL_EDGE_LABELS}:
                if d not in all_affected:
                    all_affected.add(d)
                    next_frontier.append(d)
        frontier = next_frontier
        if not frontier:
            break
    return direct, all_affected


def calculate_change_impact(target: str) -> dict:
    """`AffectedNode` (10.4 del plan): impacto DIRECTO (1 salto real,
    excluyendo `CONTAINS`/`BELONGS_TO`) e INDIRECTO (resto, max_depth=5 --
    mismo limite que `impact_chain()` ya establecido) de cambiar `target`,
    categorizado por tipo de nodo real en frontend/backend/contract/test/
    documentation/configuration. `risk` es un heuristico simple y honesto
    (conteo de nodos afectados: HIGH >=30, MEDIUM >=10, LOW resto) -- NO un
    modelo predictivo, solo aritmetica sobre datos reales.
    `recommended_order` es una plantilla ESTATICA de convencion
    (Domain->Backend->Contract->Frontend->Tests->Docs), acorde a la
    disciplina de Service Layer que este proyecto ya exige (`.AGENT.md`)
    -- marcada explicitamente como convencion, no como algo CALCULADO
    desde el grafo (seria deshonesto presentarla como tal)."""
    kg = get_knowledge_graph()
    node = resolve_change_target(target)
    if node is None:
        return {"found": False, "target": target}

    node_id = node["id"]
    direct_ids, all_affected_ids = _functional_dependents(kg, node_id, max_depth=5)
    indirect_ids = all_affected_ids - direct_ids

    def _categorize(ids: set) -> dict:
        cats: dict[str, list] = {"frontend": [], "backend": [], "contract": [],
                                  "test": [], "documentation": [], "configuration": [], "other": []}
        for nid in ids:
            n = kg.nodes.get(nid)
            if n is None:
                continue
            d = n.to_dict()
            if n.type == "Symbol" and n.meta.get("is_test"):
                cats["test"].append(d)
            elif n.type == "Symbol" and n.meta.get("symbol_type") is not None:
                cats["frontend"].append(d)
            elif n.type == "Symbol":
                cats["backend"].append(d)
            elif n.type in _FRONTEND_NODE_TYPES:
                cats["frontend"].append(d)
            elif n.type in _BACKEND_NODE_TYPES:
                cats["backend"].append(d)
            elif n.type in _CONTRACT_NODE_TYPES:
                cats["contract"].append(d)
            elif n.type == "Documentation":
                cats["documentation"].append(d)
            elif n.type in _CONFIG_NODE_TYPES:
                cats["configuration"].append(d)
            else:
                cats["other"].append(d)
        return cats

    direct_impact = _categorize(direct_ids)
    indirect_impact = _categorize(indirect_ids)

    total_affected = len(all_affected_ids)
    risk = "HIGH" if total_affected >= 30 else "MEDIUM" if total_affected >= 10 else "LOW"

    return {
        "found": True,
        "target": node,
        "direct_impact": direct_impact,
        "indirect_impact": indirect_impact,
        "total_affected": total_affected,
        "risk": risk,
        "tests": find_tests_for_change(node["name"]),
        "documentation": find_docs_for_change(node["name"]),
        "configuration": find_configuration_for(node["name"]),
        "recommended_order": [
            "1. Domain (Model/Selector/Service/Command -- capa de datos y logica de negocio)",
            "2. Contract (Serializer/Endpoint -- lo que se expone)",
            "3. Frontend (Composable/Store/Component -- consumidor)",
            "4. Tests (validar cada capa afectada)",
            "5. Documentation (reflejar el cambio real)",
        ],
    }


# ---- Change Resolver (Fase 11, Site Knowledge Graph, 2026-08-10) ----------

def resolve_change(request: str) -> dict:
    """Fase 11 "Change Resolver" -- interfaz principal para una futura IA
    editora (el "AI Editor Runtime" de Fase 14, explicitamente separado de
    `ai_engine` y de este modulo). NO parsea lenguaje natural (`request`
    debe ser el nombre real de una entidad, igual que
    `resolve_change_target()` de Fase 10 -- mismo alcance deliberado
    documentado ahi: `ChangeIntent` en el sentido NLP del plan 10.2/11
    requiere un LLM real). Compone `calculate_change_impact()` (Fase 10) +
    `trace_data_flow()` (Fase 5, solo si el target es un Model) +
    `trace_execution()` (Fase 6, solo si el target es un Symbol) en el
    formato EXACTO que pide 11 del plan: `intent, target, primary_files,
    symbols, contracts, frontend_consumers, backend_dependencies,
    data_flows, execution_paths, tests, documentation, configuration,
    risk, change_order, validation_plan`. No se reimplementa nada -- cada
    campo reusa una funcion ya construida y verificada en una fase
    anterior."""
    impact = calculate_change_impact(request)
    if not impact.get("found"):
        return {"found": False, "request": request}

    kg = get_knowledge_graph()
    node = impact["target"]

    primary_files = []
    if node.get("file"):
        file_node = kg.nodes.get(f"file:{node['file']}")
        if file_node:
            primary_files.append(file_node.to_dict())

    symbols = [node] if node["type"] == "Symbol" else []
    contracts = impact["direct_impact"]["contract"] + impact["indirect_impact"]["contract"]
    frontend_consumers = impact["direct_impact"]["frontend"] + impact["indirect_impact"]["frontend"]
    backend_dependencies = impact["direct_impact"]["backend"] + impact["indirect_impact"]["backend"]

    data_flows = trace_data_flow(node["name"]) if node["type"] == "Model" else None
    execution_paths = trace_execution(node["name"]) if node["type"] == "Symbol" else None

    return {
        "found": True,
        "intent": {
            "raw_request": request,
            "note": ("Sin parsing de lenguaje natural (Regla 4 del plan: no fabricar lo que no "
                     "es demostrable) -- 'request' se resuelve como nombre de entidad real, "
                     "igual que resolve_change_target()."),
        },
        "target": node,
        "primary_files": primary_files,
        "symbols": symbols,
        "contracts": contracts,
        "frontend_consumers": frontend_consumers,
        "backend_dependencies": backend_dependencies,
        "data_flows": data_flows,
        "execution_paths": execution_paths,
        "tests": impact["tests"],
        "documentation": impact["documentation"],
        "configuration": impact["configuration"],
        "risk": impact["risk"],
        "change_order": impact["recommended_order"],
        "validation_plan": [
            "1. python -m project_knowledge_graph.cli validate (consistencia estructural del grafo)",
            "2. Ejecutar los tests reales listados en 'tests' (direct_tests + indirect_tests)",
            "3. Si hay 'contracts' afectados, confirmar Endpoint->Serializer->Model sigue consistente",
            "4. Actualizar la documentacion listada en 'documentation' si el comportamiento cambio",
        ],
    }


# ---- Graph Context Packet (Fase 12, Site Knowledge Graph, 2026-08-10) -----

def _compact_node(node: dict) -> dict:
    """Solo lo esencial para un consumidor LLM -- id/type/name/file/lineas
    (si es Symbol). NUNCA el `meta` completo (api_calls/hook_calls/fields/
    bases/etc.) -- eso es ruido de tokens que el LLM no necesita para saber
    QUE tocar, solo DONDE."""
    compact = {"id": node["id"], "type": node["type"], "name": node["name"]}
    if node.get("file"):
        compact["file"] = node["file"]
    meta = node.get("meta") or {}
    if "start_line" in meta and "end_line" in meta:
        compact["lines"] = f"{meta['start_line']}-{meta['end_line']}"
    return compact


def build_graph_context_packet(request: str) -> dict:
    """Fase 12 "Graph Context Packet" (Site Knowledge Graph, 2026-08-10):
    normaliza `resolve_change()` (Fase 11) a SOLO el subgrafo relevante --
    NO se entrega el grafo completo (miles de nodos) a un LLM, se entrega
    la version comprimida via `_compact_node()`. `stats` reporta
    `total_graph_nodes` (el grafo completo) vs `relevant_nodes` (lo que
    realmente importa para este cambio) -- responde literalmente el
    diagrama de la Fase 12 del plan (miles de nodos -> resolver -> decenas
    de nodos relevantes)."""
    resolved = resolve_change(request)
    if not resolved.get("found"):
        return {"found": False, "request": request}

    tests_all = resolved["tests"]["direct_tests"] + resolved["tests"]["indirect_tests"]
    docs_all = (resolved["documentation"]["architecture_docs"]
                + resolved["documentation"]["implementation_docs"]
                + resolved["documentation"]["audit_docs"])

    packet = {
        "found": True,
        "request": request,
        "target": _compact_node(resolved["target"]),
        "primary_files": [_compact_node(f) for f in resolved["primary_files"]],
        "symbols": [_compact_node(s) for s in resolved["symbols"]],
        "contracts": [_compact_node(c) for c in resolved["contracts"]],
        "frontend_consumers": [_compact_node(f) for f in resolved["frontend_consumers"]],
        "backend_dependencies": [_compact_node(b) for b in resolved["backend_dependencies"]],
        "tests": [_compact_node(t) for t in tests_all],
        "documentation": [_compact_node(d) for d in docs_all],
        "risk": resolved["risk"],
        "change_order": resolved["change_order"],
    }

    kg = get_knowledge_graph()
    relevant_files = {n["file"] for n in (packet["primary_files"] + packet["symbols"]
                                           + packet["backend_dependencies"] + packet["frontend_consumers"])
                       if n.get("file")}
    relevant_nodes = sum(len(packet[k]) for k in
                          ("primary_files", "symbols", "contracts", "frontend_consumers",
                           "backend_dependencies", "tests", "documentation")) + 1  # +1 target
    packet["stats"] = {
        "total_graph_nodes": len(kg.nodes),
        "relevant_nodes": relevant_nodes,
        "relevant_files": len(relevant_files),
        "relevant_symbols": len(packet["symbols"]) + len(
            [n for n in packet["backend_dependencies"] + packet["frontend_consumers"] if n["type"] == "Symbol"]
        ),
        "relevant_contracts": len(packet["contracts"]),
        "relevant_tests": len(packet["tests"]),
        "relevant_documents": len(packet["documentation"]),
    }
    return packet


# ---- Primitivos de busqueda directa (Fase 13 "Graph SDK", Site Knowledge --
# Graph, 2026-08-10) -- las consultas de mas alto nivel (resolve_change,
# calculate_change_impact) ya cubrian resolucion por nombre generico; estos
# 4 primitivos existen para busquedas ACOTADAS a un tipo de nodo especifico
# (lo que pide graph_sdk.find_symbol/find_file/find_endpoint), evitando que
# un consumidor tenga que filtrar el resultado de find_by_name() a mano.

def find_symbol(name: str) -> dict | None:
    """Symbol por `qualified_name` EXACTO (`Clase.metodo` o `funcion`) --
    fallback a substring solo si no hay match exacto."""
    kg = get_knowledge_graph()
    exact = [n for n in kg.nodes_of_type("Symbol") if n.name == name]
    if exact:
        return exact[0].to_dict()
    fuzzy = [n for n in kg.nodes_of_type("Symbol") if name.lower() in n.name.lower()]
    return fuzzy[0].to_dict() if fuzzy else None


def find_file(path: str) -> dict | None:
    """File por path EXACTO (relativo a `ecommerce_sintel/`, ej.
    `renting/api/views.py`) -- fallback a substring de path si no hay
    match exacto (util para buscar solo por nombre de archivo)."""
    kg = get_knowledge_graph()
    node = kg.nodes.get(f"file:{path}")
    if node:
        return node.to_dict()
    fuzzy = [n for n in kg.nodes_of_type("File") if path.lower() in n.file.lower()]
    return fuzzy[0].to_dict() if fuzzy else None


def find_endpoint(query: str) -> dict | None:
    """Endpoint por nombre/prefijo EXACTO (ej. `api/v1/renting/equipment`)
    -- fallback a substring."""
    kg = get_knowledge_graph()
    exact = [n for n in kg.nodes_of_type("Endpoint") if n.name == query.strip("/")]
    if exact:
        return exact[0].to_dict()
    fuzzy = [n for n in kg.nodes_of_type("Endpoint") if query.lower() in n.name.lower()]
    return fuzzy[0].to_dict() if fuzzy else None


_CONSUMPTION_EDGE_LABELS = {
    "CONSUMES_ENDPOINT", "USES_STORE", "USES_COMPOSABLE", "CALLS",
    "READS_FROM", "WRITES_TO", "IMPLEMENTED_BY", "SERIALIZES", "USES",
    "TESTS", "VALIDATES", "REFERENCES", "TRIGGERS", "QUEUES",
}


def find_consumers(target: str) -> list[dict]:
    """Quien CONSUME/LLAMA/LEE `target` -- predecesores via aristas
    FUNCIONALES unicamente (mismo criterio que `_functional_dependents()`
    de Fase 10: excluye `CONTAINS`/`BELONGS_TO`, que son estructurales, no
    consumo real). 1 salto directo, no transitivo (para eso esta
    `calculate_change_impact()`)."""
    node = resolve_change_target(target)
    if node is None:
        return []
    kg = get_knowledge_graph()
    return [kg.nodes[e.source].to_dict() for e in kg.edges
            if e.target == node["id"] and e.label in _CONSUMPTION_EDGE_LABELS and e.source in kg.nodes]


def build_change_plan(request: str) -> dict:
    """Fase 13 "Graph SDK": subconjunto de `resolve_change()` enfocado
    exclusivamente en EJECUTAR el cambio (orden, riesgo, validacion) -- sin
    el detalle completo de nodos afectados (eso es `resolve_change()`/
    `calculate_change_impact()` completos)."""
    resolved = resolve_change(request)
    if not resolved.get("found"):
        return {"found": False, "request": request}
    return {
        "found": True,
        "target": resolved["target"]["name"],
        "risk": resolved["risk"],
        "change_order": resolved["change_order"],
        "validation_plan": resolved["validation_plan"],
    }
