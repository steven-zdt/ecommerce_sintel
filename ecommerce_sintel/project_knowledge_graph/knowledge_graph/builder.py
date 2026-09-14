"""
KnowledgeGraphBuilder -- construye el grafo tipado de entidades a partir de
PROJECT_MAP. Extraido de ai_engine/knowledge_graph.py (Fase 5, PLAN_MAESTRO_
DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).

PROJECT_MAP -> KNOWLEDGE_GRAPH. Representa entidades y relaciones (a
diferencia de project_map/, que solo responde "que existe").
"""
import json
import logging
import re
from pathlib import Path

from project_knowledge_graph.config import KNOWLEDGE_GRAPH_PATH, PROJECT_MAP_PATH
from project_knowledge_graph.knowledge_graph.relations import KnowledgeGraph, Node

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder:
    def __init__(self, project_map: dict):
        self.pmap = project_map
        self.kg = KnowledgeGraph()

    def build(self) -> KnowledgeGraph:
        self._add_apps()
        self._add_backend_entities()
        self._add_endpoints()
        self._add_frontend_entities()
        self._add_files_and_symbols()
        self._infer_backend_edges()
        self._infer_frontend_edges()
        self._infer_real_import_edges()
        self._infer_component_usage_edges()
        self._infer_contract_edges()
        self._infer_frontend_backend_contract_edges()
        self._link_signal_triggers()
        return self.kg

    # ---- Apps ---------------------------------------------------------------

    # Modulos no-Django que documentation_graph ya trata como "app" valido al
    # etiquetar sus docs, pero que nunca ganaban un nodo App real porque
    # _add_apps() solo iteraba PROJECT_MAP["apps"] (exclusivamente apps Django).
    NON_DJANGO_APP_MODULES = ("frontend", "ai_engine")

    def _add_apps(self):
        for app_name in self.pmap.get("apps", {}):
            nid = f"app:{app_name}"
            self.kg.add_node(Node(nid, "App", app_name, app=app_name))
        for app_name in self.NON_DJANGO_APP_MODULES:
            nid = f"app:{app_name}"
            if nid in self.kg.nodes:
                continue
            self.kg.add_node(Node(nid, "App", app_name, app=app_name,
                                  meta={"kind": "non_django_module"}))

    # ---- Backend entities ---------------------------------------------------

    def _add_backend_entities(self):
        for app_name, app_data in self.pmap.get("apps", {}).items():
            app_nid = f"app:{app_name}"

            for m in app_data.get("models", []):
                nid = self.kg.node_id(app_name, "Model", m["name"])
                self.kg.add_node(Node(nid, "Model", m["name"], app=app_name,
                                      file=m.get("file", ""),
                                      meta={"bases": m.get("bases", []),
                                            "fields": m.get("fields", [])}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

                for field in m.get("fields", []):
                    if field.get("related_model"):
                        m.setdefault("_fk_targets", []).append(field["related_model"])

            for s in app_data.get("serializers", []):
                nid = self.kg.node_id(app_name, "Serializer", s["name"])
                self.kg.add_node(Node(nid, "Serializer", s["name"], app=app_name,
                                      file=s.get("file", ""),
                                      meta={"bases": s.get("bases", [])}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for vs in app_data.get("viewsets", []):
                nid = self.kg.node_id(app_name, "ViewSet", vs["name"])
                self.kg.add_node(Node(nid, "ViewSet", vs["name"], app=app_name,
                                      file=vs.get("file", ""),
                                      meta={"bases": vs.get("bases", []),
                                            "actions": vs.get("actions", [])}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for svc in app_data.get("services", []):
                role = svc.get("role", "service").capitalize()
                type_map = {"Service": "Service", "Command": "Command",
                            "Selector": "Selector", "Pricing": "Service",
                            "Commands": "Command", "Selectors": "Selector"}
                node_type = type_map.get(role, "Service")
                nid = self.kg.node_id(app_name, node_type, svc["name"])
                self.kg.add_node(Node(nid, node_type, svc["name"], app=app_name,
                                      file=svc.get("file", ""),
                                      meta={"methods": svc.get("methods", [])}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for sel in app_data.get("selectors", []):
                nid = self.kg.node_id(app_name, "Selector", sel["name"])
                self.kg.add_node(Node(nid, "Selector", sel["name"], app=app_name,
                                      file=sel.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for cmd in app_data.get("management_commands", []):
                nid = self.kg.node_id(app_name, "ManagementCommand", cmd["name"])
                self.kg.add_node(Node(nid, "ManagementCommand", cmd["name"],
                                      app=app_name, file=cmd.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for c in app_data.get("consumers", []):
                nid = self.kg.node_id(app_name, "Consumer", c["name"])
                self.kg.add_node(Node(nid, "Consumer", c["name"], app=app_name,
                                      file=c.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for t in app_data.get("tasks", []):
                nid = self.kg.node_id(app_name, "Task", t["name"])
                self.kg.add_node(Node(nid, "Task", t["name"], app=app_name,
                                      file=t.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for p in app_data.get("permissions", []):
                nid = self.kg.node_id(app_name, "Permission", p["name"])
                self.kg.add_node(Node(nid, "Permission", p["name"], app=app_name,
                                      file=p.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            for sig in app_data.get("signals", []):
                nid = self.kg.node_id(app_name, "Signal", sig["name"])
                self.kg.add_node(Node(nid, "Signal", sig["name"], app=app_name,
                                      file=sig.get("file", ""),
                                      meta={"trigger": sig.get("trigger"),
                                            "sender": sig.get("sender"),
                                            "signal_name": sig.get("signal_name")}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            # WebSocket Contract (Fase 2, Site Knowledge Graph, 2026-08-10):
            # un nodo por cada `path(route, XConsumer.as_asgi())` real de un
            # routing.py -- el Consumer real se linkea despues en
            # _link_websocket_routes(), una vez que todos los nodos Consumer
            # de todas las apps ya existen (una ruta puede apuntar a un
            # Consumer de OTRA app, ej. ecommerce/routing.py -> support.
            # SupportChatConsumer).
            for ws in app_data.get("websocket_patterns", []):
                nid = f"ws:{ws['route']}"
                self.kg.add_node(Node(nid, "WebSocketRoute", ws["route"], app=app_name,
                                      meta={"consumer": ws.get("consumer")}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

    # ---- Endpoints ----------------------------------------------------------

    def _add_endpoints(self):
        for ep in self.pmap.get("endpoints", []):
            app = ep.get("app", "")
            ep_str = ep.get("endpoint", "")
            vs_name = ep.get("viewset", "")
            nid = f"endpoint:{ep_str}"
            self.kg.add_node(Node(nid, "Endpoint", ep_str, app=app,
                                  meta={"http_methods": ep.get("http_methods", []),
                                        "viewset": vs_name,
                                        "basename": ep.get("basename")}))
            self.kg.add_edge(nid, f"app:{app}", "BELONGS_TO")
            vs_nid = self.kg.node_id(app, "ViewSet", vs_name)
            if vs_nid in self.kg.nodes:
                self.kg.add_edge(vs_nid, nid, "EXPOSES")

    # ---- Frontend entities --------------------------------------------------

    def _add_frontend_entities(self):
        fe = self.pmap.get("frontend", {})

        for view in fe.get("views", []):
            nid = f"frontend:View:{view['path']}"
            self.kg.add_node(Node(nid, "FrontendView", Path(view["path"]).stem,
                                  file=view["path"],
                                  meta={"api_calls": view.get("api_calls", []),
                                        "props": view.get("props", []),
                                        "emits": view.get("emits", [])}))

        for comp in fe.get("components", []):
            nid = f"frontend:Component:{comp['path']}"
            self.kg.add_node(Node(nid, "FrontendComponent", Path(comp["path"]).stem,
                                  file=comp["path"],
                                  meta={"api_calls": comp.get("api_calls", [])}))

        for store in fe.get("stores", []):
            store_id = store.get("store_info", {}).get("store_id", Path(store["path"]).stem)
            nid = f"frontend:Store:{store_id}"
            self.kg.add_node(Node(nid, "PiniaStore", store_id,
                                  file=store.get("path", ""),
                                  meta={"api_calls": store.get("api_calls", []),
                                        "store_info": store.get("store_info", {})}))

        for comp in fe.get("composables", []):
            nid = f"frontend:Composable:{comp['path']}"
            self.kg.add_node(Node(nid, "Composable", Path(comp["path"]).stem,
                                  file=comp["path"],
                                  meta={"api_calls": comp.get("api_calls", [])}))

        for layout in fe.get("layouts", []):
            nid = f"frontend:Layout:{layout['path']}"
            self.kg.add_node(Node(nid, "Layout", Path(layout["path"]).stem,
                                  file=layout["path"]))

        for router_file in fe.get("router", []):
            router_path = router_file.get("path", "")
            for route in router_file.get("routes", []):
                path = route.get("path", "")
                name = route.get("name") or path.replace("/", "_")
                # Namespacing por archivo de origen: dos arboles de rutas
                # distintos (admin vs publico) pueden reusar el mismo segmento
                # relativo montado bajo prefijos distintos.
                nid = f"frontend:Route:{router_path}:{path}"
                self.kg.add_node(Node(nid, "Route", path,
                                      meta={"component": route.get("component"),
                                            "component_resolved": route.get("component_resolved"),
                                            "name": route.get("name")}))

    # ---- File / Symbol (Fase 1, Site Knowledge Graph, 2026-08-10) -----------
    #
    # File: un nodo por archivo escaneado (backend Python + frontend Vue/JS),
    # con language/lines/hash/role. Symbol: un nodo por funcion/metodo Python
    # con rango de lineas exacto -- responde "que lineas exactas tocar", no
    # solo "que archivo" (el objetivo explicito del plan: "AvailabilityEngine.
    # calculate_availability() lines 82-147", no solo el nombre del archivo).
    # CodeSegment del plan original NO es un node type aparte aca a proposito:
    # el scanner es de una sola pasada (sin tracking de identidad entre
    # commits), asi que Symbol (qualified_name + file + rango de lineas) y
    # CodeSegment (symbol + hash + rango) serian casi 1:1 -- el hash de
    # contenido de cada Symbol se guarda en su propio meta, sin duplicar el
    # nodo. Separarlos de verdad solo tiene sentido cuando exista fingerprint
    # semantico real (embeddings) o tracking de identidad cross-commit, ninguno
    # construido todavia -- ver Fase 3/6 del roadmap.
    #
    # [ACTUALIZADO Fase 3, 2026-08-10] Frontend tambien genera Symbol ahora
    # (ver scanner/frontend_scanner.py::extract_frontend_symbols) -- MISMO
    # node type "Symbol" que Python, no un tipo "FrontendSymbol" aparte
    # (decision de scope documentada en frontend_scanner.py): evita
    # fragmentar queries/tests entre dos tipos que significan lo mismo
    # conceptualmente. Se distinguen via meta.language ("python" vs "vue"/
    # "javascript"/"typescript") y los campos nuevos meta.symbol_type/role,
    # ausentes en simbolos Python (kind sigue siendo function/method en
    # ambos casos, para que la logica de CONTAINS de abajo sea identica).

    def _add_files_and_symbols(self):
        # file path -> [ids de nodos existentes que viven ahi] -- reusa el
        # atributo .file que casi todos los node types ya cargan, no vuelve a
        # escanear nada.
        nodes_by_file: dict[str, list[str]] = {}
        for node in self.kg.nodes.values():
            if node.file:
                nodes_by_file.setdefault(node.file, []).append(node.id)

        for app_name, app_data in self.pmap.get("apps", {}).items():
            for f in app_data.get("files", []):
                self._add_one_file(f, app_name, nodes_by_file)

        fe = self.pmap.get("frontend", {})
        for group in ("views", "components", "composables", "stores", "router", "layouts", "misc"):
            for f in fe.get(group, []):
                self._add_one_file(f, "frontend", nodes_by_file)

    def _add_one_file(self, f: dict, app_name: str, nodes_by_file: dict[str, list[str]]):
        path = f.get("path", "")
        if not path:
            return

        file_nid = f"file:{path}"
        self.kg.add_node(Node(
            file_nid, "File", Path(path).name, app=app_name, file=path,
            meta={
                "role": f.get("role"),
                "language": f.get("language", "python"),
                "lines": f.get("lines"),
                "hash": f.get("hash"),
            },
        ))

        existing_here = nodes_by_file.get(path, [])
        class_nid_by_name: dict[str, str] = {}
        for existing_nid in existing_here:
            self.kg.add_edge(file_nid, existing_nid, "CONTAINS")
            node = self.kg.nodes.get(existing_nid)
            if node:
                class_nid_by_name[node.name] = existing_nid

        sym_nid_by_qualified_name: dict[str, str] = {}
        for sym in f.get("symbols", []):
            sym_nid = f"symbol:{path}:{sym['qualified_name']}"
            sym_nid_by_qualified_name[sym["qualified_name"]] = sym_nid
            meta = {
                "kind": sym["kind"],
                "class_name": sym.get("class_name"),
                "start_line": sym["start_line"],
                "end_line": sym["end_line"],
                "is_async": sym.get("is_async", False),
                # is_test (Fase 7 "Test Graph", 2026-08-10): False para
                # frontend tambien (.get() con default, ver
                # scanner/project_scanner.py -- solo Python lo marca por
                # ahora, ver scope documentado).
                "is_test": sym.get("is_test", False),
            }
            # symbol_type/role/hash (Fase 3, Site Knowledge Graph, 2026-08-10):
            # solo FrontendSymbol los trae (ver scanner/frontend_scanner.py::
            # _make_frontend_symbol) -- Python's extract_symbols() no los
            # genera, por eso .get() con None en vez de asumir la clave.
            if "symbol_type" in sym:
                meta["symbol_type"] = sym["symbol_type"]
                meta["role"] = sym.get("role")
                meta["hash"] = sym.get("hash")
                # api_calls/hook_calls (Fase 4, 2026-08-10): que endpoints/
                # hooks llama ESTE simbolo especificamente -- consumidos por
                # _infer_frontend_backend_contract_edges() abajo.
                meta["api_calls"] = sym.get("api_calls", [])
                meta["hook_calls"] = sym.get("hook_calls", [])
            self.kg.add_node(Node(
                sym_nid, "Symbol", sym["qualified_name"], app=app_name, file=path,
                meta=meta,
            ))
            self.kg.add_edge(file_nid, sym_nid, "CONTAINS")
            owner_nid = class_nid_by_name.get(sym.get("class_name"))
            if sym["kind"] == "method" and owner_nid:
                self.kg.add_edge(owner_nid, sym_nid, "CONTAINS")

        self._link_model_usages(f.get("model_usages", []), sym_nid_by_qualified_name)
        self._link_task_queue_calls(f.get("task_queue_calls", []), sym_nid_by_qualified_name)
        self._link_test_endpoint_validations(f.get("api_test_calls", []), sym_nid_by_qualified_name)
        self._link_test_symbol_coverage(f.get("direct_symbol_calls", []), sym_nid_by_qualified_name)

    def _link_test_endpoint_validations(self, calls: list, sym_nid_by_qualified_name: dict[str, str]):
        """VALIDATES (Fase 7 'Test Graph', Site Knowledge Graph,
        2026-08-10): Test-Symbol -> Endpoint, usando
        `extract_api_test_calls()` (`self.client.verbo(url)` real,
        verificado en shop/tests.py). Solo se linkea si el Symbol origen
        esta marcado `is_test` -- `direct_symbol_calls`/`api_test_calls` se
        escanean en todo archivo (ver scanner), el filtro real de "esto es
        un test" pasa aca, no en el scanner. Reusa
        `_match_endpoints_for_url()` de Fase 4, mismo criterio de matching
        por prefijo real de router."""
        if not calls:
            return
        for call in calls:
            sym_nid = sym_nid_by_qualified_name.get(call["qualified_name"])
            sym_node = self.kg.nodes.get(sym_nid) if sym_nid else None
            if not sym_node or not sym_node.meta.get("is_test"):
                continue
            for ep_node in self._match_endpoints_for_url(call["url"]):
                self.kg.add_edge(sym_nid, ep_node.id, "VALIDATES", meta={"method": call.get("method")})

    def _link_test_symbol_coverage(self, calls: list, sym_nid_by_qualified_name: dict[str, str]):
        """TESTS (Fase 7 'Test Graph', Site Knowledge Graph, 2026-08-10):
        Test-Symbol -> Symbol, usando `extract_direct_symbol_calls()`
        (`ClaseX.metodo(...)` real dentro del test, verificado en
        renting/tests_endpoints.py:
        `RentalRequestCommands.create_request(...)`). Matching por
        `Symbol.name == target_qualified_name` EXACTO (Symbol.name YA es
        el qualified_name, ver builder.py::_add_one_file) -- mismo criterio
        de nombre exacto que Model/Task en Fases 5-6, no substring."""
        if not calls:
            return
        for call in calls:
            sym_nid = sym_nid_by_qualified_name.get(call["qualified_name"])
            sym_node = self.kg.nodes.get(sym_nid) if sym_nid else None
            if not sym_node or not sym_node.meta.get("is_test"):
                continue
            target_candidates = [c for c in self.kg.find_by_name(call["target_qualified_name"])
                                  if c.type == "Symbol" and c.name == call["target_qualified_name"]]
            for target in target_candidates:
                self.kg.add_edge(sym_nid, target.id, "TESTS")

    def _link_task_queue_calls(self, usages: list, sym_nid_by_qualified_name: dict[str, str]):
        """QUEUES (Fase 6 'Execution Graph', Site Knowledge Graph,
        2026-08-10): Symbol -> Task, usando `extract_task_queue_calls()`
        (`nombre_task.delay(...)`/`.apply_async(...)`, verificado real en
        notifications/services/commands.py::dispatch_notification, que
        encola 5 tasks distintas segun el canal). Mismo matching por
        `qualified_name` + nombre EXACTO de Task (via find_by_name filtrado)
        que ya evito el bug de homonimos en `_link_model_usages` -- la task
        puede vivir en OTRA app (import cruzado real, ej. notifications ->
        support), find_by_name no se limita a la app actual."""
        if not usages:
            return
        for usage in usages:
            sym_nid = sym_nid_by_qualified_name.get(usage["qualified_name"])
            if not sym_nid:
                continue
            task_candidates = [c for c in self.kg.find_by_name(usage["task"])
                                if c.type == "Task" and c.name == usage["task"]]
            for task_node in task_candidates:
                self.kg.add_edge(sym_nid, task_node.id, "QUEUES")

    def _link_model_usages(self, usages: list, sym_nid_by_qualified_name: dict[str, str]):
        """READS_FROM/WRITES_TO (Fase 5 'Data Flow Graph', Site Knowledge
        Graph, 2026-08-10): Symbol -> Model, usando la evidencia real de
        `extract_model_manager_usages()` (ver django_scanner.py para el
        alcance exacto -- solo `Model.objects.verbo(...)` directo, no
        cadenas ni `instancia.save()`). Matching por `qualified_name` 1:1
        contra el Symbol real -- [CORREGIDO] la version anterior matcheaba
        por nombre crudo de funcion y mezclaba metodos homonimos de clases
        distintas en el mismo archivo (`ProductSelector.list_active` vs
        `TaxSelector.list_active`, bug real encontrado contra el repo).
        Matching de Model por nombre EXACTO (no substring de find_by_name)
        para no confundir `Product` con `ProductVariant`."""
        if not usages:
            return
        for usage in usages:
            sym_nid = sym_nid_by_qualified_name.get(usage["qualified_name"])
            if not sym_nid:
                continue
            model_candidates = [c for c in self.kg.find_by_name(usage["model"])
                                 if c.type == "Model" and c.name == usage["model"]]
            if not model_candidates:
                continue
            label = "WRITES_TO" if usage["kind"] == "write" else "READS_FROM"
            for model_node in model_candidates:
                self.kg.add_edge(sym_nid, model_node.id, label, meta={"verb": usage["verb"]})

    # ---- Infer backend edges ------------------------------------------------

    def _infer_backend_edges(self):
        for app_name, app_data in self.pmap.get("apps", {}).items():
            for m in app_data.get("models", []):
                src_nid = self.kg.node_id(app_name, "Model", m["name"])
                for field in m.get("fields", []):
                    related = field.get("related_model")
                    if not related or related in ("self", "settings.AUTH_USER_MODEL"):
                        continue
                    candidates = self.kg.find_by_name(related.split(".")[-1])
                    for c in candidates:
                        if c.type == "Model":
                            self.kg.add_edge(src_nid, c.id, "DEPENDS_ON",
                                             meta={"via_field": field.get("name")})

        for app_name, app_data in self.pmap.get("apps", {}).items():
            for s in app_data.get("serializers", []):
                s_nid = self.kg.node_id(app_name, "Serializer", s["name"])
                model_name = s["name"]
                for suffix in ("Serializer", "InputSerializer", "OutputSerializer",
                               "ListSerializer", "DetailSerializer"):
                    if model_name.endswith(suffix):
                        model_name = model_name[:-len(suffix)]
                        break
                candidates = self.kg.find_by_name(model_name)
                for c in candidates:
                    if c.type == "Model" and c.app == app_name:
                        self.kg.add_edge(s_nid, c.id, "SERIALIZES")
                        break

        for app_name, app_data in self.pmap.get("apps", {}).items():
            for vs in app_data.get("viewsets", []):
                vs_nid = self.kg.node_id(app_name, "ViewSet", vs["name"])
                vs_base = vs["name"]
                for suffix in ("ViewSet", "APIView", "View"):
                    if vs_base.endswith(suffix):
                        vs_base = vs_base[:-len(suffix)]
                        break
                for s in app_data.get("serializers", []):
                    if s["name"].startswith(vs_base):
                        s_nid = self.kg.node_id(app_name, "Serializer", s["name"])
                        if s_nid in self.kg.nodes:
                            self.kg.add_edge(vs_nid, s_nid, "USES")

            for vs in app_data.get("viewsets", []):
                vs_nid = self.kg.node_id(app_name, "ViewSet", vs["name"])
                vs_base = vs["name"].replace("ViewSet", "").replace("APIView", "")
                for svc in app_data.get("services", []):
                    svc_name = svc["name"]
                    role = svc.get("role", "service")
                    node_type = "Command" if "command" in role.lower() else \
                                "Selector" if "selector" in role.lower() else "Service"
                    svc_nid = self.kg.node_id(app_name, node_type, svc_name)
                    if svc_nid in self.kg.nodes and vs_base.lower() in svc_name.lower():
                        self.kg.add_edge(vs_nid, svc_nid, "CALLS")

    # ---- Infer frontend edges -----------------------------------------------

    def _match_endpoints_for_url(self, url: str) -> list["Node"]:
        """[REESCRITO Fase 4, 2026-08-10 -- defecto real encontrado y
        corregido, no una reescritura preventiva]. La version anterior
        (heredada de antes de Fase 3) matcheaba por "el ultimo segmento de
        la URL coincide con el ultimo segmento del endpoint" -- esto produce
        falsos positivos reales y verificables: `renting/equipment/{uuid}/
        check-availability/` (llamado por `availabilityService.check()`)
        matcheaba contra `endpoint:api/v1/auth/availability` (dominio
        completamente distinto) solo porque ambas strings terminan en el
        substring literal "availability". La causa raiz: `Endpoint.name` es
        el PREFIJO del router (`api/v1/renting/equipment`, uno por
        ViewSet -- ver project_map/builder.py::build_endpoints_list), no la
        URL completa de cada `@action` individual (`check-availability`,
        `availability`, `calendar`, etc. son metodos de ESE MISMO ViewSet,
        alcanzables via la arista `IMPLEMENTED_BY` ya existente desde Fase
        2, no via una URL propia). El fix real: la URL del frontend debe
        EMPEZAR por el prefijo del endpoint (con o sin el `api/v1/` que el
        cliente Axios ya no repite via `baseURL`), no solo compartir un
        fragmento en cualquier posicion -- responde 4.4 del plan ("no
        limitar el analisis a coincidencias literales") sin necesitar
        reconstruir cada `@action` como su propio Endpoint (cambio de
        alcance mayor, no requerido para que el matching sea correcto).
        Factorizado a metodo propio para reusarlo tanto a nivel de archivo
        (_infer_frontend_edges) como de Symbol
        (_infer_frontend_symbol_contract_edges, Fase 4)."""
        url_norm = url.strip("/")
        matches = []
        for ep_node in self.kg.nodes_of_type("Endpoint"):
            ep_path = ep_node.name.strip("/")
            ep_no_prefix = re.sub(r"^api/v\d+/", "", ep_path)
            for candidate in (ep_path, ep_no_prefix):
                if url_norm == candidate or url_norm.startswith(candidate + "/"):
                    matches.append(ep_node)
                    break
        return matches

    def _build_pinia_hook_lookup(self) -> dict:
        """hook_name real (`useAvailabilityStore`) -> nodo PiniaStore -- ver
        extract_pinia_store()/extract_use_hook_calls() en frontend_scanner.py
        para el bug real que este matching EXACTO corrige (Fase 4,
        2026-08-10): la logica anterior comparaba por substring un nombre
        derivado del hook contra el store_id de negocio (`rentalAvailability`),
        strings sin relacion textual garantizada -- 0 aristas USES_STORE en
        todo el repo real antes de este fix."""
        lookup = {}
        for node in self.kg.nodes_of_type("PiniaStore"):
            hook_name = node.meta.get("store_info", {}).get("hook_name")
            if hook_name:
                lookup[hook_name] = node
        return lookup

    def _build_composable_name_lookup(self) -> dict:
        """nombre de archivo (`useAuth`, `useToast`, ...) -> nodo Composable
        -- Composable.name ya es el stem del archivo (ver
        _add_frontend_entities), que coincide exactamente con como se llama
        el hook en el codigo real por convencion de este proyecto (un
        composable por archivo, mismo nombre)."""
        return {node.name: node for node in self.kg.nodes_of_type("Composable")}

    def _link_hook_calls(self, src_nid: str, hook_names: list, pinia_hooks: dict,
                          composables_by_name: dict):
        """USES_STORE si el hook es un PiniaStore real, USES_COMPOSABLE si es
        un Composable real -- mutuamente excluyentes por construccion (un
        nombre de hook no puede ser ambos). Hooks nativos de Vue/vue-router
        (`useRoute`, `useSlots`, ...) no matchean ninguno de los dos lookups
        y quedan sin arista, correctamente (no son nodos de este grafo)."""
        for hook_name in hook_names:
            store_node = pinia_hooks.get(hook_name)
            if store_node:
                self.kg.add_edge(src_nid, store_node.id, "USES_STORE")
                continue
            composable_node = composables_by_name.get(hook_name)
            if composable_node and composable_node.id != src_nid:
                self.kg.add_edge(src_nid, composable_node.id, "USES_COMPOSABLE")

    def _infer_frontend_edges(self):
        fe = self.pmap.get("frontend", {})
        all_fe_entries = (
            [(v, "FrontendView") for v in fe.get("views", [])] +
            [(c, "FrontendComponent") for c in fe.get("components", [])] +
            [(s, "PiniaStore") for s in fe.get("stores", [])] +
            [(c, "Composable") for c in fe.get("composables", [])]
        )
        pinia_hooks = self._build_pinia_hook_lookup()
        composables_by_name = self._build_composable_name_lookup()

        for entry, expected_type in all_fe_entries:
            fe_path = entry.get("path", "")
            if expected_type == "PiniaStore":
                store_id = entry.get("store_info", {}).get("store_id", Path(fe_path).stem)
                src_nid = f"frontend:Store:{store_id}"
            elif expected_type in ("FrontendView", "FrontendComponent"):
                node_type_prefix = "View" if expected_type == "FrontendView" else "Component"
                src_nid = f"frontend:{node_type_prefix}:{fe_path}"
            else:
                src_nid = f"frontend:Composable:{fe_path}"

            if src_nid not in self.kg.nodes:
                continue

            for call in entry.get("api_calls", []):
                url = call.get("url", "")
                for ep_node in self._match_endpoints_for_url(url):
                    self.kg.add_edge(src_nid, ep_node.id, "CONSUMES_ENDPOINT",
                                     meta={"method": call.get("method")})

            self._link_hook_calls(src_nid, entry.get("hook_calls", []), pinia_hooks, composables_by_name)

    # ---- Real edges -----------------------------------------------------------

    def _infer_real_import_edges(self):
        """IMPORTS real (AST, no heuristica de nombre) a nivel de App -- App A
        importa algo de App B en al menos un archivo real. Base de la deteccion
        de ciclos del validador (audit/validator.py)."""
        pair_evidence: dict[tuple, list[str]] = {}
        for app_name, app_data in self.pmap.get("apps", {}).items():
            for imp in app_data.get("cross_app_imports", []):
                key = (app_name, imp["target_app"])
                pair_evidence.setdefault(key, [])
                if len(pair_evidence[key]) < 5:
                    pair_evidence[key].append(f"{imp['via_file']} -> {imp['import']}")

        for (src_app, dst_app), examples in pair_evidence.items():
            src_nid, dst_nid = f"app:{src_app}", f"app:{dst_app}"
            if src_nid in self.kg.nodes and dst_nid in self.kg.nodes:
                self.kg.add_edge(src_nid, dst_nid, "IMPORTS", meta={"examples": examples})

    def _infer_component_usage_edges(self):
        """USES_COMPONENT: FrontendView/FrontendComponent -> FrontendComponent.
        Dos senales combinadas (una sola no basta -- el proyecto auto-importa
        componentes via unplugin-vue-components):
          1. component_imports -- import X from '...vue' explicito.
          2. template_tags -- el tag <X ...> aparece en el <template>, cubre
             el auto-import."""
        fe = self.pmap.get("frontend", {})
        all_entries = (
            [(v, "FrontendView") for v in fe.get("views", [])] +
            [(c, "FrontendComponent") for c in fe.get("components", [])] +
            [(l, "Layout") for l in fe.get("layouts", [])]
        )
        comp_by_name: dict[str, list] = {}
        for comp_node in self.kg.nodes_of_type("FrontendComponent"):
            comp_by_name.setdefault(comp_node.name, []).append(comp_node)
        for view_node in self.kg.nodes_of_type("FrontendView"):
            comp_by_name.setdefault(view_node.name, []).append(view_node)

        node_prefix_by_type = {"FrontendView": "View", "FrontendComponent": "Component", "Layout": "Layout"}
        for entry, expected_type in all_entries:
            fe_path = entry.get("path", "")
            prefix = node_prefix_by_type[expected_type]
            src_nid = f"frontend:{prefix}:{fe_path}"
            if src_nid not in self.kg.nodes:
                continue
            referenced_names = set(entry.get("component_imports", [])) | \
                set(entry.get("template_tags", []))
            for name in referenced_names:
                for target in comp_by_name.get(name, []):
                    if target.id != src_nid:
                        self.kg.add_edge(src_nid, target.id, "USES_COMPONENT")

    # ---- Contract edges (Fase 2, Site Knowledge Graph, 2026-08-10) ----------
    #
    # "Contract Graph" del plan original tenia 7 sub-tipos (APIContract,
    # WebSocketContract, PayloadSchema, ResponseSchema, EventContract,
    # DatabaseContract, EnvironmentContract). Alcance deliberado de esta
    # pasada -- documentado, no una omision silenciosa:
    #   - APIContract: SI, ver _link_endpoints_to_symbols() abajo.
    #   - PayloadSchema/ResponseSchema: NO nuevo -- ya cubierto por el node
    #     type Serializer existente (fields en su meta) + la arista SERIALIZES
    #     hacia Model; no se duplica como concepto aparte.
    #   - EventContract: NO nuevo -- ambiguo en el plan original, parcialmente
    #     cubierto por el node type Signal ya existente (Django signals).
    #     Eventos de aplicacion (ej. 'chat_message'/'history' del WS de
    #     soporte) quedan para una pasada futura si se pide explicitamente.
    #   - DatabaseContract: NO nuevo -- ya cubierto por Model.fields (meta) +
    #     la arista DEPENDS_ON via FK real.
    #   - WebSocketContract: SI, ver _link_websocket_routes() (metodo aparte,
    #     llamado desde aca).
    #   - EnvironmentContract: SI, ver _add_env_vars() (metodo aparte).

    def _infer_contract_edges(self):
        self._link_endpoints_to_symbols()
        self._link_websocket_routes()
        self._add_env_vars()

    def _link_endpoints_to_symbols(self):
        """API Contract: conecta cada Endpoint al Symbol (metodo real del
        ViewSet) que lo implementa -- 'GET /api/v1/renting/availability/'
        -IMPLEMENTED_BY-> Symbol 'AvailabilityViewSet.list' con sus lineas
        exactas, no solo la arista EXPOSES (ViewSet -> Endpoint) que ya
        existia a nivel de clase completa."""
        for ep in self.pmap.get("endpoints", []):
            app = ep.get("app", "")
            ep_str = ep.get("endpoint", "")
            vs_name = ep.get("viewset", "")
            ep_nid = f"endpoint:{ep_str}"
            vs_node = self.kg.nodes.get(self.kg.node_id(app, "ViewSet", vs_name))
            if not vs_node or not vs_node.file:
                continue
            for action_name in ep.get("actions", []):
                sym_nid = f"symbol:{vs_node.file}:{vs_name}.{action_name}"
                if sym_nid in self.kg.nodes:
                    self.kg.add_edge(ep_nid, sym_nid, "IMPLEMENTED_BY")

    def _link_websocket_routes(self):
        """WebSocket Contract: conecta cada nodo WebSocketRoute (agregado por
        _add_backend_entities via app_data['websocket_patterns'], ver
        scanner/django_scanner.py::extract_websocket_patterns) al Consumer
        real que lo implementa -- 'ws/support/chat/' -IMPLEMENTED_BY->
        Consumer 'SupportChatConsumer'."""
        for node in list(self.kg.nodes.values()):
            if node.type != "WebSocketRoute":
                continue
            consumer_name = node.meta.get("consumer")
            if not consumer_name:
                continue
            for cand in self.kg.find_by_name(consumer_name):
                if cand.type == "Consumer" and cand.name == consumer_name:
                    self.kg.add_edge(node.id, cand.id, "IMPLEMENTED_BY")
                    break

    def _add_env_vars(self):
        """Environment Contract: un nodo EnvVar por cada variable leida via
        env()/config() (python-decouple, el patron real de este proyecto --
        confirmado en ecommerce/settings/base.py) en un archivo Python
        escaneado, con arista File -USES_ENV-> EnvVar. Responde el ejemplo
        del plan: 'AI_SUPPORT_CHAT_ENABLED -> que archivos la leen'. Solo
        Python por ahora (deliberado, mismo criterio que Symbol en Fase 1):
        el patron equivalente en frontend es `import.meta.env.VITE_*`, una
        sintaxis distinta que el scanner de Vue/JS no reconoce todavia."""
        for app_name, app_data in self.pmap.get("apps", {}).items():
            for f in app_data.get("files", []):
                self._add_env_vars_for_file(f, app_name)

    def _add_env_vars_for_file(self, f: dict, app_name: str):
        path = f.get("path", "")
        env_vars = f.get("env_vars", [])
        if not path or not env_vars:
            return
        file_nid = f"file:{path}"
        if file_nid not in self.kg.nodes:
            return
        for var_name in env_vars:
            env_nid = f"envvar:{var_name}"
            self.kg.add_node(Node(env_nid, "EnvVar", var_name, meta={}))
            self.kg.add_edge(file_nid, env_nid, "USES_ENV")

    # ---- Frontend<->Backend Contract Graph (Fase 4, Site Knowledge Graph, --
    # 2026-08-10) -------------------------------------------------------------
    #
    # Extiende CONSUMES_ENDPOINT/USES_STORE (ya existentes a nivel de archivo,
    # ver _infer_frontend_edges arriba) a nivel de Symbol individual -- "que
    # funcion especifica" en vez de "que archivo". Agrega USES_COMPOSABLE
    # (edge label nuevo) y Endpoint->SERIALIZES->Serializer. De las 5
    # relaciones que pide 4.3 del plan (CONSUMES_ENDPOINT, IMPLEMENTED_BY,
    # SERIALIZES, USES_STORE, USES_COMPOSABLE) las 5 quedan cubiertas --
    # IMPLEMENTED_BY (Endpoint->BackendSymbol) ya existia desde Fase 2, sin
    # cambios aca.

    def _infer_frontend_symbol_contract_edges(self):
        """CONSUMES_ENDPOINT/USES_STORE/USES_COMPOSABLE a nivel de Symbol.
        Reusa api_calls/hook_calls que cada Symbol frontend ya trae en su
        meta (ver scanner/frontend_scanner.py::_make_frontend_symbol) --
        Symbol Python no tiene esas claves (symbol_type is None), se
        excluye explicitamente en vez de fallar en silencio con listas
        vacias por casualidad."""
        pinia_hooks = self._build_pinia_hook_lookup()
        composables_by_name = self._build_composable_name_lookup()

        for sym_node in self.kg.nodes_of_type("Symbol"):
            if sym_node.meta.get("symbol_type") is None:
                continue

            for call in sym_node.meta.get("api_calls", []):
                url = call.get("url", "")
                for ep_node in self._match_endpoints_for_url(url):
                    self.kg.add_edge(sym_node.id, ep_node.id, "CONSUMES_ENDPOINT",
                                     meta={"method": call.get("method")})

            self._link_hook_calls(sym_node.id, sym_node.meta.get("hook_calls", []),
                                  pinia_hooks, composables_by_name)

    def _link_endpoints_to_serializers(self):
        """Endpoint -SERIALIZES-> Serializer: reusa la arista ViewSet -USES->
        Serializer que _infer_backend_edges() ya calcula (matching por
        prefijo de nombre de clase) -- no reinventa ese matching, solo lo
        propaga un salto mas abajo hasta el Endpoint real, que es lo que
        pide 4.3 del plan."""
        for ep in self.pmap.get("endpoints", []):
            app = ep.get("app", "")
            ep_str = ep.get("endpoint", "")
            vs_name = ep.get("viewset", "")
            ep_nid = f"endpoint:{ep_str}"
            vs_nid = self.kg.node_id(app, "ViewSet", vs_name)
            if vs_nid not in self.kg.nodes or ep_nid not in self.kg.nodes:
                continue
            for s in self.kg.successors(vs_nid):
                if s["edge"] == "USES" and s["node"]["type"] == "Serializer":
                    self.kg.add_edge(ep_nid, s["node"]["id"], "SERIALIZES")

    def _infer_frontend_backend_contract_edges(self):
        self._infer_frontend_symbol_contract_edges()
        self._link_endpoints_to_serializers()

    # ---- Execution Graph (Fase 6, Site Knowledge Graph, 2026-08-10) ---------
    #
    # Diferencia DEPENDENCY (DEPENDS_ON/IMPORTS, "que necesita que para
    # existir") de EXECUTION (orden real en que algo ocurre en tiempo de
    # ejecucion). No se crean node types nuevos para "ExecutionPath" --
    # 6.1 del plan lo llama "entidad DERIVADA", y con el resto de la cadena
    # ya construido en Fases 0-5 (CONSUMES_ENDPOINT/IMPLEMENTED_BY/CALLS/
    # READS_FROM/WRITES_TO), el unico eslabon real que faltaba para
    # continuar la cadena hasta "EVENT -> NOTIFICATION" era Model->Signal
    # (que evento dispara que handler) y Symbol->Task (que funcion encola
    # que trabajo async) -- ver TRIGGERS/QUEUES abajo. trace_execution()
    # en knowledge_graph/query.py compone todo esto en un recorrido, igual
    # que trace_data_flow() hizo con Fase 5.

    def _link_signal_triggers(self):
        """TRIGGERS: Model -> Signal, usando el `sender=X` real capturado en
        `extract_signal_registrations()` -- verificado contra
        `@receiver(post_save, sender=UserProfile)` real en accounts/
        models.py (dispara create_technician_profile). Solo se linkea
        cuando `sender` se pudo resolver (no todo `.connect()` pasa
        `sender=` explicito) -- sin sender no hay evidencia real de que
        Model, no se adivina."""
        for app_name, app_data in self.pmap.get("apps", {}).items():
            for sig in app_data.get("signals", []):
                sender = sig.get("sender")
                if not sender:
                    continue
                sig_nid = self.kg.node_id(app_name, "Signal", sig["name"])
                if sig_nid not in self.kg.nodes:
                    continue
                model_candidates = [c for c in self.kg.find_by_name(sender)
                                     if c.type == "Model" and c.name == sender]
                for model_node in model_candidates:
                    self.kg.add_edge(model_node.id, sig_nid, "TRIGGERS",
                                     meta={"signal_name": sig.get("signal_name")})


def build_and_save_knowledge_graph() -> KnowledgeGraph:
    """PROJECT_MAP -> KnowledgeGraphBuilder -> enrichers (documentation/docker/
    agents) -> KNOWLEDGE_GRAPH.json. Cada enricher es defensivo: un error ahi
    no debe tumbar el grafo estructural, que es el dato mas critico."""
    if not PROJECT_MAP_PATH.exists():
        raise FileNotFoundError(f"PROJECT_MAP.json no encontrado en {PROJECT_MAP_PATH}")
    pmap = json.loads(PROJECT_MAP_PATH.read_text(encoding="utf-8"))
    builder = KnowledgeGraphBuilder(pmap)
    kg = builder.build()

    try:
        from project_knowledge_graph.knowledge_graph.enrichers.documentation import enrich_with_documentation
        doc_stats = enrich_with_documentation(kg)
        logger.info("[knowledge_graph] Documentation: %s", doc_stats)
    except Exception:
        logger.exception("[knowledge_graph] Documentation enrichment fallo, continuando sin el")

    try:
        from project_knowledge_graph.knowledge_graph.enrichers.docker import enrich_with_docker
        docker_stats = enrich_with_docker(kg)
        logger.info("[knowledge_graph] Docker: %s", docker_stats)
    except Exception:
        logger.exception("[knowledge_graph] Docker enrichment fallo, continuando sin el")

    try:
        # Requiere que enrich_with_docker() ya haya corrido -- ROUTES_TO
        # matchea contra nodos DockerService ya existentes.
        from project_knowledge_graph.knowledge_graph.enrichers.nginx import enrich_with_nginx
        nginx_stats = enrich_with_nginx(kg)
        logger.info("[knowledge_graph] Nginx: %s", nginx_stats)
    except Exception:
        logger.exception("[knowledge_graph] Nginx enrichment fallo, continuando sin el")

    try:
        from project_knowledge_graph.knowledge_graph.enrichers.agents import enrich_with_agents
        agent_stats = enrich_with_agents(kg)
        logger.info("[knowledge_graph] Agents: %s", agent_stats)
    except Exception:
        logger.exception("[knowledge_graph] Agent enrichment fallo, continuando sin el")

    kg.save(KNOWLEDGE_GRAPH_PATH)
    return kg
