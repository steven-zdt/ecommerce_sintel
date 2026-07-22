"""
dependency_graph.py - Sintel Dependency Graph Builder (Phase 8)

Answers:
  - What breaks if I change X?
  - What files depend on model Y?
  - What frontend files consume endpoint Z?
  - What serializer uses model W?
  - What tests must run after changing app A?
  - What ViewSet exposes endpoint E?

Output: DEPENDENCY_GRAPH.json
"""
import json
import logging
from pathlib import Path
from collections import defaultdict

from knowledge_graph import get_knowledge_graph, KnowledgeGraph

logger = logging.getLogger(__name__)

DEPGRAPH_PATH = Path(__file__).resolve().parent / "DEPENDENCY_GRAPH.json"
MAP_PATH      = Path(__file__).resolve().parent / "PROJECT_MAP.json"


def build_dependency_graph() -> dict:
    kg = get_knowledge_graph()
    pmap: dict = {}
    if MAP_PATH.exists():
        pmap = json.loads(MAP_PATH.read_text(encoding="utf-8"))

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

    # ---- model_dependents: Model → [things that use it] --------------------
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

    # ---- endpoint_consumers: Endpoint → [frontend files / stores] ----------
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
    # For each Model, Serializer, ViewSet, Endpoint — compute transitive blast radius
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
    DEPGRAPH_PATH.write_text(json.dumps(dg, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("[dependency_graph] Saved DEPENDENCY_GRAPH.json (%d KB)",
                DEPGRAPH_PATH.stat().st_size // 1024)
    return dg


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

_cached_dg: dict | None = None


def get_dependency_graph(force_reload: bool = False) -> dict:
    global _cached_dg
    if _cached_dg is not None and not force_reload:
        return _cached_dg
    if DEPGRAPH_PATH.exists():
        _cached_dg = json.loads(DEPGRAPH_PATH.read_text(encoding="utf-8"))
    else:
        _cached_dg = build_dependency_graph()
    return _cached_dg


def what_breaks_if_i_change(entity_name: str) -> dict:
    """
    Returns the blast radius if entity_name changes.
    entity_name can be 'shop.Product', 'ProductSerializer', 'ProductViewSet', etc.
    """
    dg = get_dependency_graph()
    # Direct key match
    if entity_name in dg.get("change_impact", {}):
        return dg["change_impact"][entity_name]
    # Partial match
    for key in dg.get("change_impact", {}):
        if entity_name.lower() in key.lower():
            return {f"match:{key}": dg["change_impact"][key]}
    return {}


def who_consumes_endpoint(endpoint_path: str) -> list[dict]:
    dg = get_dependency_graph()
    for ep_key, consumers in dg.get("endpoint_consumers", {}).items():
        if endpoint_path in ep_key or ep_key in endpoint_path:
            return consumers
    return []


def what_tests_cover_app(app_name: str) -> list[str]:
    return get_dependency_graph().get("tests", {}).get(app_name, [])


def get_app_summary(app_name: str) -> dict:
    dg = get_dependency_graph()
    return {
        "models":    dg.get("app_to_models", {}).get(app_name, []),
        "viewsets":  dg.get("app_to_viewsets", {}).get(app_name, []),
        "endpoints": dg.get("app_to_endpoints", {}).get(app_name, []),
        "tests":     dg.get("tests", {}).get(app_name, []),
    }


def build_impact_analysis_text(entity_name: str) -> str:
    """
    Human-readable impact analysis for LLM prompt injection.
    """
    blast = what_breaks_if_i_change(entity_name)
    if not blast:
        return ""

    lines = [f"=== ANALISIS DE RUPTURA: cambiar '{entity_name}' afecta ==="]
    type_order = ["FrontendView", "FrontendComponent", "PiniaStore", "Composable",
                  "ViewSet", "Serializer", "Command", "Selector", "Service",
                  "Consumer", "Task", "Signal", "Model", "Endpoint", "Permission"]
    for t in type_order:
        items = blast.get(t, [])
        if items:
            lines.append(f"  {t}: {', '.join(items[:6])}")
    leftovers = [t for t in blast if t not in type_order]
    for t in leftovers:
        lines.append(f"  {t}: {', '.join(blast[t][:4])}")
    lines.append("=== FIN ANALISIS DE RUPTURA ===")
    return "\n".join(lines)
