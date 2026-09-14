"""
Carga del Dependency Graph con cache in-process. Extraido de ai_engine/
dependency_graph.py::get_dependency_graph (Fase 6, PLAN_MAESTRO_DE_SEPARACION_
PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).
"""
import json

from project_knowledge_graph.config import DEPENDENCY_GRAPH_PATH
from project_knowledge_graph.dependency_graph.builder import build_dependency_graph

_cached_dg: dict | None = None


def get_dependency_graph(force_reload: bool = False) -> dict:
    global _cached_dg
    if _cached_dg is not None and not force_reload:
        return _cached_dg
    if DEPENDENCY_GRAPH_PATH.exists():
        _cached_dg = json.loads(DEPENDENCY_GRAPH_PATH.read_text(encoding="utf-8"))
    else:
        _cached_dg = build_dependency_graph()
    return _cached_dg
