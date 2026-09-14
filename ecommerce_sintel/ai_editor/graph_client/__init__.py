"""
ai_editor.graph_client -- Fase 14 "AI Editor Runtime" (Site Knowledge
Graph, 2026-08-10), extendido en POST-GRAPH 1 "AI Editor Graph Client"
(rediseno "AI Editor Runtime", 2026-08-11). UNICO submodulo de
`ai_editor/` con codigo real -- el resto son stubs documentales (ver
`ai_editor/__init__.py`).

Esta es LA FRONTERA OFICIAL entre `ai_editor` y `project_knowledge_graph`
(seccion "ARQUITECTURA OBLIGATORIA" del prompt maestro POST-GRAPH): el
resto de `ai_editor/` (cuando `intent/`/`resolver/`/`planner/` dejen de
ser scaffold) DEBE importar `ai_editor.graph_client`, nunca
`project_knowledge_graph.knowledge_graph.*`/`.internal.*` directo. Wrapper
de SOLO LECTURA sobre `project_knowledge_graph.graph_sdk` -- no agrega
logica propia, aisla el punto de contacto real con el grafo en UN solo
lugar (si `graph_sdk` cambia de forma, solo este archivo necesita
actualizarse). Cero riesgo: ninguna funcion de aca escribe nada, ni en el
grafo ni en el filesystem del repo.

16 operaciones (13 de Fase 14 + 3 de POST-GRAPH 1: `find_node`,
`get_app_summary`, `get_graph_status` -- ver `graph_sdk/__init__.py` para
el detalle de cada una y por que `find_node` usa `resolve_change_target`
en vez de `find_node_context`).
"""
from project_knowledge_graph.graph_sdk import (
    build_change_plan,
    build_context_packet,
    calculate_impact,
    find_configuration,
    find_consumers,
    find_docs,
    find_endpoint,
    find_file,
    find_node,
    find_symbol,
    find_tests,
    get_app_summary,
    get_graph_status,
    resolve_change,
    trace_data_flow,
    trace_execution,
)

__all__ = [
    "resolve_change",
    "find_node",
    "find_symbol",
    "find_file",
    "find_endpoint",
    "find_consumers",
    "trace_data_flow",
    "trace_execution",
    "find_tests",
    "find_docs",
    "calculate_impact",
    "build_change_plan",
    "build_context_packet",
    "find_configuration",
    "get_app_summary",
    "get_graph_status",
]
