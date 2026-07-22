"""
knowledge_graph.py - Sintel Knowledge Graph Builder (Phase 4 / Phase 7)

Builds a typed directed graph where every entity in the project is a node
and every relationship is a labeled edge. Built on top of PROJECT_MAP.json.

Node types:
  App | Model | Serializer | ViewSet | Command | Selector | Service |
  Signal | Consumer | Task | Permission | Endpoint | ManagementCommand |
  FrontendView | FrontendComponent | PiniaStore | Composable | Route

Edge labels:
  SERIALIZES | EXPOSES | REGISTERS_ON | EXTENDS | DEPENDS_ON |
  CALLS | TRIGGERS | PRODUCES | CONSUMES_ENDPOINT | STORES |
  NAVIGATES_TO | BELONGS_TO | USES_STORE | USES_COMPOSABLE
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAP_PATH     = Path(__file__).resolve().parent / "PROJECT_MAP.json"
KG_PATH      = Path(__file__).resolve().parent / "KNOWLEDGE_GRAPH.json"


# ---------------------------------------------------------------------------
# Node & Edge data structures
# ---------------------------------------------------------------------------

class Node:
    __slots__ = ("id", "type", "name", "app", "file", "meta")

    def __init__(self, id: str, type: str, name: str, app: str = "",
                 file: str = "", meta: dict | None = None):
        self.id   = id
        self.type = type
        self.name = name
        self.app  = app
        self.file = file
        self.meta = meta or {}

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "name": self.name,
                "app": self.app, "file": self.file, "meta": self.meta}


class Edge:
    __slots__ = ("source", "target", "label", "meta")

    def __init__(self, source: str, target: str, label: str, meta: dict | None = None):
        self.source = source
        self.target = target
        self.label  = label
        self.meta   = meta or {}

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target,
                "label": self.label, "meta": self.meta}


class KnowledgeGraph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge]      = []
        self._edge_set: set[tuple]  = set()

    def add_node(self, node: Node):
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def add_edge(self, source: str, target: str, label: str, meta: dict | None = None):
        key = (source, target, label)
        if key not in self._edge_set and source in self.nodes and target in self.nodes:
            self.edges.append(Edge(source, target, label, meta))
            self._edge_set.add(key)

    def node_id(self, app: str, type_prefix: str, name: str) -> str:
        return f"{app}:{type_prefix}:{name}"

    # ---- Neighbors ----------------------------------------------------------

    def successors(self, node_id: str) -> list[dict]:
        return [{"node": self.nodes[e.target].to_dict(), "edge": e.label}
                for e in self.edges if e.source == node_id and e.target in self.nodes]

    def predecessors(self, node_id: str) -> list[dict]:
        return [{"node": self.nodes[e.source].to_dict(), "edge": e.label}
                for e in self.edges if e.target == node_id and e.source in self.nodes]

    def neighborhood(self, node_id: str, depth: int = 2) -> dict:
        """BFS to depth returning all reachable nodes."""
        visited: set[str] = {node_id}
        frontier = [node_id]
        result_nodes = {node_id: self.nodes[node_id].to_dict()} if node_id in self.nodes else {}
        result_edges = []

        for _ in range(depth):
            next_frontier = []
            for nid in frontier:
                for e in self.edges:
                    if e.source == nid and e.target not in visited:
                        visited.add(e.target)
                        next_frontier.append(e.target)
                        if e.target in self.nodes:
                            result_nodes[e.target] = self.nodes[e.target].to_dict()
                        result_edges.append(e.to_dict())
                    elif e.target == nid and e.source not in visited:
                        visited.add(e.source)
                        next_frontier.append(e.source)
                        if e.source in self.nodes:
                            result_nodes[e.source] = self.nodes[e.source].to_dict()
                        result_edges.append(e.to_dict())
            frontier = next_frontier

        return {"center": node_id, "nodes": list(result_nodes.values()), "edges": result_edges}

    def find_by_name(self, name: str) -> list[Node]:
        name_l = name.lower()
        return [n for n in self.nodes.values() if name_l in n.name.lower()]

    def nodes_of_type(self, type_name: str) -> list[Node]:
        return [n for n in self.nodes.values() if n.type == type_name]

    def what_depends_on(self, node_id: str) -> list[str]:
        """Return IDs of all nodes that have an edge pointing TO this node."""
        return [e.source for e in self.edges if e.target == node_id]

    def what_this_uses(self, node_id: str) -> list[str]:
        """Return IDs of all nodes that this node has an edge pointing TO."""
        return [e.target for e in self.edges if e.source == node_id]

    def transitive_dependents(self, node_id: str, max_depth: int = 4) -> set[str]:
        """All nodes that (transitively) depend on node_id."""
        result = set()
        frontier = [node_id]
        for _ in range(max_depth):
            next_f = []
            for nid in frontier:
                deps = self.what_depends_on(nid)
                for d in deps:
                    if d not in result:
                        result.add(d)
                        next_f.append(d)
            frontier = next_f
            if not frontier:
                break
        return result

    # ---- Serialization ------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "edges": [e.to_dict() for e in self.edges],
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types": self._type_counts(),
            },
        }

    def _type_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for n in self.nodes.values():
            counts[n.type] = counts.get(n.type, 0) + 1
        return counts

    def save(self, path: Path = KG_PATH):
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[knowledge_graph] Saved %d nodes, %d edges to %s",
                    len(self.nodes), len(self.edges), path)


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

class KnowledgeGraphBuilder:
    def __init__(self, project_map: dict):
        self.pmap = project_map
        self.kg   = KnowledgeGraph()

    def build(self) -> KnowledgeGraph:
        self._add_apps()
        self._add_backend_entities()
        self._add_endpoints()
        self._add_frontend_entities()
        self._infer_backend_edges()
        self._infer_frontend_edges()
        return self.kg

    # ---- Apps ---------------------------------------------------------------

    def _add_apps(self):
        for app_name in self.pmap.get("apps", {}):
            nid = f"app:{app_name}"
            self.kg.add_node(Node(nid, "App", app_name, app=app_name))

    # ---- Backend entities ---------------------------------------------------

    def _add_backend_entities(self):
        for app_name, app_data in self.pmap.get("apps", {}).items():
            app_nid = f"app:{app_name}"

            # Models
            for m in app_data.get("models", []):
                nid = self.kg.node_id(app_name, "Model", m["name"])
                self.kg.add_node(Node(nid, "Model", m["name"], app=app_name,
                                      file=m.get("file", ""),
                                      meta={"bases": m.get("bases", []),
                                            "fields": m.get("fields", [])}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

                # FK relations → DEPENDS_ON edges (added later in infer)
                for field in m.get("fields", []):
                    if field.get("related_model"):
                        # Store for later resolution
                        m.setdefault("_fk_targets", []).append(field["related_model"])

            # Serializers
            for s in app_data.get("serializers", []):
                nid = self.kg.node_id(app_name, "Serializer", s["name"])
                self.kg.add_node(Node(nid, "Serializer", s["name"], app=app_name,
                                      file=s.get("file", ""),
                                      meta={"bases": s.get("bases", [])}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            # ViewSets
            for vs in app_data.get("viewsets", []):
                nid = self.kg.node_id(app_name, "ViewSet", vs["name"])
                self.kg.add_node(Node(nid, "ViewSet", vs["name"], app=app_name,
                                      file=vs.get("file", ""),
                                      meta={"bases": vs.get("bases", []),
                                            "actions": vs.get("actions", [])}))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            # Services/Commands/Selectors
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

            # Selectors
            for sel in app_data.get("selectors", []):
                nid = self.kg.node_id(app_name, "Selector", sel["name"])
                self.kg.add_node(Node(nid, "Selector", sel["name"], app=app_name,
                                      file=sel.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            # Management commands
            for cmd in app_data.get("management_commands", []):
                nid = self.kg.node_id(app_name, "ManagementCommand", cmd["name"])
                self.kg.add_node(Node(nid, "ManagementCommand", cmd["name"],
                                      app=app_name, file=cmd.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            # Consumers
            for c in app_data.get("consumers", []):
                nid = self.kg.node_id(app_name, "Consumer", c["name"])
                self.kg.add_node(Node(nid, "Consumer", c["name"], app=app_name,
                                      file=c.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            # Celery tasks
            for t in app_data.get("tasks", []):
                nid = self.kg.node_id(app_name, "Task", t["name"])
                self.kg.add_node(Node(nid, "Task", t["name"], app=app_name,
                                      file=t.get("file", "")))
                self.kg.add_edge(nid, app_nid, "BELONGS_TO")

            # Permissions
            for p in app_data.get("permissions", []):
                nid = self.kg.node_id(app_name, "Permission", p["name"])
                self.kg.add_node(Node(nid, "Permission", p["name"], app=app_name,
                                      file=p.get("file", "")))
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
            # Endpoint → App
            self.kg.add_edge(nid, f"app:{app}", "BELONGS_TO")
            # ViewSet → Endpoint (EXPOSES)
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
            for route in router_file.get("routes", []):
                path = route.get("path", "")
                name = route.get("name") or path.replace("/", "_")
                nid = f"frontend:Route:{path}"
                self.kg.add_node(Node(nid, "Route", path,
                                      meta={"component": route.get("component"),
                                            "name": route.get("name")}))

    # ---- Infer backend edges ------------------------------------------------

    def _infer_backend_edges(self):
        # FK: Model → Model via DEPENDS_ON
        for app_name, app_data in self.pmap.get("apps", {}).items():
            for m in app_data.get("models", []):
                src_nid = self.kg.node_id(app_name, "Model", m["name"])
                for field in m.get("fields", []):
                    related = field.get("related_model")
                    if not related or related in ("self", "settings.AUTH_USER_MODEL"):
                        continue
                    # Try to find the related model node
                    candidates = self.kg.find_by_name(related.split(".")[-1])
                    for c in candidates:
                        if c.type == "Model":
                            self.kg.add_edge(src_nid, c.id, "DEPENDS_ON",
                                             meta={"via_field": field.get("name")})

        # Serializer SERIALIZES Model (heuristic: ProductSerializer → Product)
        for app_name, app_data in self.pmap.get("apps", {}).items():
            for s in app_data.get("serializers", []):
                s_nid = self.kg.node_id(app_name, "Serializer", s["name"])
                # Strip common suffixes
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

        # ViewSet CALLS serializer (heuristic: ProductViewSet uses ProductSerializer)
        for app_name, app_data in self.pmap.get("apps", {}).items():
            for vs in app_data.get("viewsets", []):
                vs_nid = self.kg.node_id(app_name, "ViewSet", vs["name"])
                # Find matching serializer by stripping "ViewSet"/"APIView"
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

            # Service/Command CALLS pattern (ViewSet uses Commands, Commands call Selectors)
            for vs in app_data.get("viewsets", []):
                vs_nid = self.kg.node_id(app_name, "ViewSet", vs["name"])
                vs_base = vs["name"].replace("ViewSet", "").replace("APIView", "")
                # Heuristic: match by app
                for svc in app_data.get("services", []):
                    svc_name = svc["name"]
                    role = svc.get("role", "service")
                    node_type = "Command" if "command" in role.lower() else \
                                "Selector" if "selector" in role.lower() else "Service"
                    svc_nid = self.kg.node_id(app_name, node_type, svc_name)
                    if svc_nid in self.kg.nodes and vs_base.lower() in svc_name.lower():
                        self.kg.add_edge(vs_nid, svc_nid, "CALLS")

    # ---- Infer frontend edges -----------------------------------------------

    def _infer_frontend_edges(self):
        cross = self.pmap.get("cross_refs", {})
        fe_to_ep = cross.get("frontend_to_endpoint", {})

        # FrontendView/Component CONSUMES_ENDPOINT
        fe = self.pmap.get("frontend", {})
        all_fe_entries = (
            [(v, "FrontendView") for v in fe.get("views", [])] +
            [(c, "FrontendComponent") for c in fe.get("components", [])] +
            [(s, "PiniaStore") for s in fe.get("stores", [])] +
            [(c, "Composable") for c in fe.get("composables", [])]
        )

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
                # Match to endpoint node by URL similarity
                for ep_node in self.kg.nodes_of_type("Endpoint"):
                    ep_path = ep_node.name  # e.g. "api/v1/shop/products"
                    if ep_path in url or url.rstrip("/").endswith(ep_path.split("/")[-1]):
                        self.kg.add_edge(src_nid, ep_node.id, "CONSUMES_ENDPOINT",
                                         meta={"method": call.get("method")})

            # Store import edges
            for store_ref in entry.get("store_imports", []):
                for store_node in self.kg.nodes_of_type("PiniaStore"):
                    if store_ref.lower() in store_node.name.lower():
                        self.kg.add_edge(src_nid, store_node.id, "USES_STORE")


# ---------------------------------------------------------------------------
# Convenience loader
# ---------------------------------------------------------------------------

_cached_kg: KnowledgeGraph | None = None


def get_knowledge_graph(force_rebuild: bool = False) -> KnowledgeGraph:
    global _cached_kg
    if _cached_kg is not None and not force_rebuild:
        return _cached_kg

    if not MAP_PATH.exists():
        logger.warning("[knowledge_graph] PROJECT_MAP.json not found")
        _cached_kg = KnowledgeGraph()
        return _cached_kg

    pmap = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    builder = KnowledgeGraphBuilder(pmap)
    kg = builder.build()
    _cached_kg = kg
    return kg


def build_and_save_knowledge_graph() -> KnowledgeGraph:
    if not MAP_PATH.exists():
        raise FileNotFoundError(f"PROJECT_MAP.json not found at {MAP_PATH}")
    pmap = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    builder = KnowledgeGraphBuilder(pmap)
    kg = builder.build()
    kg.save(KG_PATH)
    return kg


# ---------------------------------------------------------------------------
# Query helpers for AI Engine
# ---------------------------------------------------------------------------

def find_node_context(entity_name: str, depth: int = 2) -> dict:
    """
    Returns the knowledge graph neighborhood of an entity by name.
    Used by the AI Engine reasoning step.
    """
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
    """
    Returns the full transitive impact chain: all nodes affected if entity_name changes.
    """
    kg = get_knowledge_graph()
    matches = kg.find_by_name(entity_name)
    if not matches:
        return []
    node = matches[0]
    affected_ids = kg.transitive_dependents(node.id, max_depth=5)
    return [kg.nodes[nid].to_dict() for nid in affected_ids if nid in kg.nodes]
