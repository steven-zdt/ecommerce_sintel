"""
Carga del Knowledge Graph con cache in-process. Extraido de ai_engine/
knowledge_graph.py::get_knowledge_graph (Fase 5, PLAN_MAESTRO_DE_SEPARACION_
PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).
"""
import json
import logging

from project_knowledge_graph.config import KNOWLEDGE_GRAPH_PATH, PROJECT_MAP_PATH
from project_knowledge_graph.knowledge_graph.builder import KnowledgeGraphBuilder
from project_knowledge_graph.knowledge_graph.relations import KnowledgeGraph

logger = logging.getLogger(__name__)

_cached_kg: KnowledgeGraph | None = None


def get_knowledge_graph(force_rebuild: bool = False) -> KnowledgeGraph:
    """
    Prefiere el archivo KNOWLEDGE_GRAPH.json persistido (ya enriquecido con
    Documentation/DockerService/Agent) sobre reconstruir desde PROJECT_MAP.json
    en frio -- reconstruir en frio pierde el enriquecimiento y deja un grafo
    mas chico del que ya existe en disco. Solo reconstruye desde cero si el
    archivo persistido aun no existe (primera corrida, antes de auditar).
    """
    global _cached_kg
    if _cached_kg is not None and not force_rebuild:
        return _cached_kg

    if KNOWLEDGE_GRAPH_PATH.exists():
        data = json.loads(KNOWLEDGE_GRAPH_PATH.read_text(encoding="utf-8"))
        kg = KnowledgeGraph.from_dict(data)
        _cached_kg = kg
        return kg

    if not PROJECT_MAP_PATH.exists():
        logger.warning("[knowledge_graph] Ni KNOWLEDGE_GRAPH.json ni PROJECT_MAP.json existen")
        _cached_kg = KnowledgeGraph()
        return _cached_kg

    pmap = json.loads(PROJECT_MAP_PATH.read_text(encoding="utf-8"))
    builder = KnowledgeGraphBuilder(pmap)
    kg = builder.build()
    _cached_kg = kg
    return kg
