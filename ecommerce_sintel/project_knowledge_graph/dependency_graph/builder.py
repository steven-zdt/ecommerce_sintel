"""
Construccion del Dependency Graph -- vistas derivadas del Knowledge Graph
optimizadas para consulta directa (sin recorrer aristas en cada pregunta).
Extraido de ai_engine/dependency_graph.py::build_dependency_graph/
save_dependency_graph (Fase 6, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_
GRAPH, 2026-08-08).

Responde:
  - Que se rompe si cambio X?
  - Que archivos dependen del modelo Y?
  - Que archivos de frontend consumen el endpoint Z?
  - Que serializer usa el modelo W?
  - Que tests hay que correr despues de cambiar la app A?
  - Que ViewSet expone el endpoint E?
"""
import json
import logging
from collections import defaultdict

from project_knowledge_graph.config import DEPENDENCY_GRAPH_PATH, PROJECT_MAP_PATH
from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph

logger = logging.getLogger(__name__)


def build_dependency_graph() -> dict:
    kg = get_knowledge_graph()
    pmap: dict = {}
    if PROJECT_MAP_PATH.exists():
        pmap = json.loads(PROJECT_MAP_PATH.read_text(encoding="utf-8"))

    dg: dict = {
        "model_dependents":    {},
        "endpoint_consumers":  {},
        "viewset_to_endpoint": {},
        "serializer_to_model": {},
        "app_to_models":       {},
        "app_to_viewsets":     {},
        "app_to_endpoints":    {},
        "frontend_to_endpoint":{},
        "store_to_endpoint":   {},
        "change_impact":       {},
        "tests":               {},
    }

    # ---- model_dependents: Model -> [things that use it] --------------------
    for node in kg.nodes_of_type("Model"):
        dependents = []
        for dep_id in kg.what_depends_on(node.id):
            if dep_id in kg.nodes:
                dependents.append({
                    "id": dep_id,
                    "type": kg.nodes[dep_id].type,
                    "name": kg.nodes[dep_id].name,
                    "app":  kg.nodes[dep_id].app,
                })
        dg["model_dependents"][f"{node.app}.{node.name}"] = dependents

    # ---- endpoint_consumers: Endpoint -> [frontend files / stores] ----------
    for node in kg.nodes_of_type("Endpoint"):
        consumers = []
        for dep_id in kg.what_depends_on(node.id):
            if dep_id in kg.nodes:
                n = kg.nodes[dep_id]
                if n.type in ("FrontendView", "FrontendComponent", "PiniaStore", "Composable"):
                    consumers.append({"type": n.type, "name": n.name, "file": n.file})
        dg["endpoint_consumers"][node.name] = consumers

    # ---- viewset_to_endpoint -----------------------------------------------
    for node in kg.nodes_of_type("ViewSet"):
        endpoints = []
        for succ in kg.successors(node.id):
            if succ["node"]["type"] == "Endpoint":
                endpoints.append(succ["node"]["name"])
        dg["viewset_to_endpoint"][f"{node.app}.{node.name}"] = endpoints

    # ---- serializer_to_model -----------------------------------------------
    for node in kg.nodes_of_type("Serializer"):
        for succ in kg.successors(node.id):
            if succ["node"]["type"] == "Model" and succ["edge"] == "SERIALIZES":
                dg["serializer_to_model"][f"{node.app}.{node.name}"] = \
                    f"{succ['node']['app']}.{succ['node']['name']}"
                break

    # ---- app_to_* (direct lookup) ------------------------------------------
    for app_name, app_data in pmap.get("apps", {}).items():
        dg["app_to_models"][app_name]    = [m["name"] for m in app_data.get("models", [])]
        dg["app_to_viewsets"][app_name]  = [v["name"] for v in app_data.get("viewsets", [])]
        dg["app_to_endpoints"][app_name] = [
            ep["endpoint"] for ep in pmap.get("endpoints", []) if ep.get("app") == app_name
        ]

    # ---- frontend_to_endpoint (from cross_refs) ----------------------------
    cross = pmap.get("cross_refs", {})
    dg["frontend_to_endpoint"] = cross.get("frontend_to_endpoint", {})
    dg["store_to_endpoint"]    = cross.get("store_to_endpoint", {})

    # ---- change_impact: what changes if entity X changes -------------------
    # For each Model, Serializer, ViewSet, Endpoint -- compute transitive blast radius
    for node_type in ("Model", "Serializer", "ViewSet", "Endpoint"):
        for node in kg.nodes_of_type(node_type):
            affected = kg.transitive_dependents(node.id, max_depth=5)
            if affected:
                summary = defaultdict(list)
                for aid in affected:
                    if aid in kg.nodes:
                        an = kg.nodes[aid]
                        summary[an.type].append(f"{an.app}.{an.name}" if an.app else an.name)
                dg["change_impact"][f"{node.app}.{node.name}"] = dict(summary)

    # ---- tests: which test files relate to each app -----------------------
    for app_name, app_data in pmap.get("apps", {}).items():
        test_files = [f["path"] for f in app_data.get("files", []) if f.get("role") == "test"]
        if test_files:
            dg["tests"][app_name] = test_files

    return dg


def save_dependency_graph() -> dict:
    dg = build_dependency_graph()
    DEPENDENCY_GRAPH_PATH.write_text(json.dumps(dg, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("[dependency_graph] Guardado DEPENDENCY_GRAPH.json (%d KB)",
                DEPENDENCY_GRAPH_PATH.stat().st_size // 1024)
    return dg
