"""
Node/Edge/KnowledgeGraph -- estructuras de datos del grafo tipado. Extraido de
ai_engine/knowledge_graph.py (Fase 5, PLAN_MAESTRO_DE_SEPARACION_PROJECT_
KNOWLEDGE_GRAPH, 2026-08-08).

Node types:
  App | Model | Serializer | ViewSet | Command | Selector | Service |
  Signal | Consumer | Task | Permission | Endpoint | ManagementCommand |
  FrontendView | FrontendComponent | PiniaStore | Composable | Route |
  Documentation | DockerService | Agent | Tool | File | Symbol |
  WebSocketRoute | EnvVar | Port | NginxRoute
  (Port/NginxRoute: Fase 9 "Configuration/Infrastructure Graph",
  2026-08-10, ver enrichers/docker.py y enrichers/nginx.py)
  (File/Symbol: Fase 1, 2026-08-10, ver builder.py::_add_files_and_symbols.
  WebSocketRoute/EnvVar: Fase 2 "Contract Graph", 2026-08-10, ver
  builder.py::_infer_contract_edges/_add_env_vars. Fase 3, 2026-08-10:
  Symbol se extiende a frontend -- ver scanner/frontend_scanner.py::
  extract_frontend_symbols -- sin agregar node/edge types nuevos, solo mas
  cobertura de meta.language/symbol_type/role dentro del Symbol existente)

Edge labels realmente implementados (verificado, no aspiracional):
  BELONGS_TO | EXPOSES | SERIALIZES | USES | CALLS | DEPENDS_ON |
  CONSUMES_ENDPOINT | USES_STORE | USES_COMPOSABLE | DOCUMENTED_BY | IMPORTS |
  USES_COMPONENT | READS_FROM | WRITES_TO | TRIGGERS | QUEUES | VALIDATES |
  TESTS | REFERENCES | PROVIDES | ROUTES_TO |
  CONTAINS (File->Symbol, File->cualquier nodo en ese archivo, Clase->metodo) |
  IMPLEMENTED_BY (Endpoint->Symbol, WebSocketRoute->Consumer) |
  USES_ENV (File->EnvVar)
  (READS_FROM/WRITES_TO: Fase 5 "Data Flow Graph", 2026-08-10, Symbol->Model
  via evidencia real `Model.objects.verbo(...)`, ver builder.py::
  _link_model_usages y scanner/django_scanner.py::extract_model_manager_usages.
  TRIGGERS/QUEUES: Fase 6 "Execution Graph", 2026-08-10 -- TRIGGERS es
  Model->Signal via `sender=X` real de `@receiver(...)`; QUEUES es
  Symbol->Task via `nombre_task.delay(...)`/`.apply_async(...)` real, ver
  builder.py::_link_signal_triggers/_link_task_queue_calls.
  VALIDATES/TESTS: Fase 7 "Test Graph", 2026-08-10 -- Test-Symbol (marcado
  via meta.is_test, MISMO node type Symbol, sin Test/TestSuite/E2ETest
  aparte) -> Endpoint via `self.client.verbo(url)` real, o -> Symbol via
  llamada directa `ClaseX.metodo(...)` real dentro del test, ver
  builder.py::_link_test_endpoint_validations/_link_test_symbol_coverage.
  Alcance Fase 7: solo tests Python (Django TestCase/APITestCase + pytest
  `test_*`) -- tests frontend (Vitest `.test.js`) y E2E (Playwright) quedan
  PLANIFICADOS, no implementados, requieren un patron de scanner distinto.
  REFERENCES: Fase 8 "Documentation Graph", 2026-08-10 -- Documentation ->
  File|Symbol|Endpoint, via referencias reales citadas entre backticks en
  la prosa del doc (rutas de archivo, `Clase.metodo`, URLs de endpoint),
  ver knowledge_graph/enrichers/documentation.py::extract_doc_references.
  EXPOSES/PROVIDES/ROUTES_TO: Fase 9 "Configuration/Infrastructure Graph",
  2026-08-10 -- DockerService->Port (`ports:` real de docker-compose.yml),
  DockerService->EnvVar (`env_file:` real + nombres de
  `.env.production.example`, NUNCA valores ni el `.env` real con
  secretos), NginxRoute->DockerService (resuelto via `proxy_pass`, con o
  sin indireccion `set $var http://...`), ver enrichers/docker.py y
  enrichers/nginx.py)
  (USES_COMPOSABLE: Fase 4 "Contract Graph Frontend<->Backend", 2026-08-10,
  ver builder.py::_infer_frontend_backend_contract_edges. SERIALIZES tiene 2
  sentidos segun el nodo origen: Serializer->Model desde Fase 0, Endpoint->
  Serializer agregado en Fase 4 -- mismo label, no un tipo nuevo, porque
  ambos expresan la misma relacion semantica "esto serializa datos de eso".
  CONSUMES_ENDPOINT/USES_STORE ahora tambien salen de nodos Symbol
  individuales, no solo de FrontendComponent/View/Composable/PiniaStore a
  nivel de archivo completo -- ver
  builder.py::_infer_frontend_symbol_contract_edges)
"""
import json
import logging
from pathlib import Path

from project_knowledge_graph.config import KNOWLEDGE_GRAPH_PATH

logger = logging.getLogger(__name__)


class Node:
    __slots__ = ("id", "type", "name", "app", "file", "meta")

    def __init__(self, id: str, type: str, name: str, app: str = "",
                 file: str = "", meta: dict | None = None):
        self.id = id
        self.type = type
        self.name = name
        self.app = app
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
        self.label = label
        self.meta = meta or {}

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target,
                "label": self.label, "meta": self.meta}


class KnowledgeGraph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []
        self._edge_set: set[tuple] = set()

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
        """BFS a profundidad `depth` devolviendo todos los nodos alcanzables."""
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
        """IDs de todos los nodos que tienen una arista apuntando HACIA este nodo."""
        return [e.source for e in self.edges if e.target == node_id]

    def what_this_uses(self, node_id: str) -> list[str]:
        """IDs de todos los nodos hacia los que este nodo tiene una arista."""
        return [e.target for e in self.edges if e.source == node_id]

    def transitive_dependents(self, node_id: str, max_depth: int = 4) -> set[str]:
        """Todos los nodos que (transitivamente) dependen de node_id."""
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

    def save(self, path: Path = KNOWLEDGE_GRAPH_PATH):
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("[knowledge_graph] Guardados %d nodos, %d aristas en %s",
                    len(self.nodes), len(self.edges), path)

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        """Contraparte de to_dict()/save() -- deserializa el JSON persistido de
        vuelta a objetos Node/Edge reales."""
        kg = cls()
        for n in data.get("nodes", []):
            kg.add_node(Node(n["id"], n["type"], n["name"], app=n.get("app", ""),
                              file=n.get("file", ""), meta=n.get("meta") or {}))
        for e in data.get("edges", []):
            kg.add_edge(e["source"], e["target"], e["label"], meta=e.get("meta") or {})
        return kg
