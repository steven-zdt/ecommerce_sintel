"""
Consultas directas sobre el Dependency Graph. Extraido de ai_engine/
dependency_graph.py (Fase 6, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_
GRAPH, 2026-08-08).
"""
from project_knowledge_graph.dependency_graph.loader import get_dependency_graph


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
