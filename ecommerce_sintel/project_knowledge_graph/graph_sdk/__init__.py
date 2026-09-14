"""
Graph SDK -- Fase 13 "Graph SDK" (Site Knowledge Graph, 2026-08-10).

Interfaz ESTABLE entre `project_knowledge_graph` y cualquier consumidor
futuro (la futura Fase 14 "AI Editor Runtime" en particular). Principio del
plan: "el SDK debe ocultar JSON/Graph internals/scanner internals/builder
internals/storage al consumidor" -- un consumidor de este paquete NUNCA
deberia necesitar `from project_knowledge_graph.knowledge_graph.relations
import Node` ni saber que existe `KNOWLEDGE_GRAPH.json` en disco. Cada
funcion de aca devuelve dicts planos (ya serializables a JSON), nunca
instancias de `Node`/`KnowledgeGraph`.

No reimplementa nada -- cada funcion es una re-exportacion (posiblemente
renombrada, para calzar con los 11 nombres exactos que pide 13 del plan)
de una funcion ya construida y verificada en `knowledge_graph/query.py`
durante las Fases 5-13. Reglas 1/2 del plan siguen aplicando: este paquete
vive DENTRO de `project_knowledge_graph`, no en `ai_engine` -- un futuro
`ai_editor/` (Fase 14) importaria `project_knowledge_graph.graph_sdk`,
nunca al reves, y `ai_engine` sigue sin importar nada de aca (ver Fase 0).

Las 11 operaciones que pide el plan, cada una linea 1:1 a su fuente real:
  resolve_change()      -> knowledge_graph.query.resolve_change (Fase 11)
  find_symbol()          -> knowledge_graph.query.find_symbol (Fase 13, nuevo)
  find_file()             -> knowledge_graph.query.find_file (Fase 13, nuevo)
  find_endpoint()         -> knowledge_graph.query.find_endpoint (Fase 13, nuevo)
  find_consumers()        -> knowledge_graph.query.find_consumers (Fase 13, nuevo)
  trace_data_flow()       -> knowledge_graph.query.trace_data_flow (Fase 5)
  trace_execution()       -> knowledge_graph.query.trace_execution (Fase 6)
  find_tests()            -> knowledge_graph.query.find_tests_for_change (Fase 7)
  find_docs()              -> knowledge_graph.query.find_docs_for_change (Fase 8)
  calculate_impact()      -> knowledge_graph.query.calculate_change_impact (Fase 10)
  build_change_plan()     -> knowledge_graph.query.build_change_plan (Fase 13, nuevo)

Extra (no pedido explicitamente por el nombre en 13, pero forma parte
natural del SDK): `build_context_packet()` -> query.build_graph_context_packet
(Fase 12) y `find_configuration()` -> query.find_configuration_for (Fase 9).

Fase 18 "Observability" (Site Knowledge Graph, 2026-08-10) agrega logging
de auditoria: cada una de las 13 funciones de aca queda envuelta en
`_logged()`, que registra operacion/args/resumen del resultado/version del
grafo consultado via `audit/query_log.py::log_query()` -- ver ese modulo
para la regla explicita de que NO se persiste (nunca el `meta` completo de
un nodo, nunca nada que pudiera ser un secreto). El logging es best-effort
y no cambia el valor de retorno ni el comportamiento de ninguna funcion.

POST-GRAPH 1 "AI Editor Graph Client" (rediseno "AI Editor Runtime",
2026-08-11) agrega 3 operaciones mas, pedidas explicitamente por ese plan
y ausentes hasta ahora -- mismo criterio que las 13 anteriores, CERO logica
nueva, solo re-exportacion de funciones YA construidas y verificadas:
  find_node()        -> knowledge_graph.query.resolve_change_target (Fase 10)
  get_app_summary()  -> dependency_graph.query.get_app_summary (extraccion 2026-08-08)
  get_graph_status() -> snapshots.manager.latest_snapshot (extraccion 2026-08-08)

`find_node()` usa DELIBERADAMENTE `resolve_change_target()` y NO
`knowledge_graph.query.find_node_context()` (a pesar del nombre mas
parecido) -- `find_node_context()` resuelve con `kg.find_by_name()` puro
(substring sin preferencia por coincidencia EXACTA, el mismo bug que Fase
7 del rediseno anterior encontro y corrigio en `find_symbol`/`find_endpoint`/
`find_file`, pero que DELIBERADAMENTE nunca se aplico a `find_node_context`/
`impact_chain` para no regresionarlos -- ver Fase 10 del Historial en
`ARQUITECTURA_COMPLETA_GRAFO.md`). `resolve_change_target()` SI hace
exacto-antes-que-fuzzy y es la misma funcion que ya usa
`calculate_change_impact()`/`resolve_change()` internamente -- reusarla
aca evita heredar un bug conocido en la nueva frontera oficial, documentado
en `ai_editor/.AGENT/AI_EDITOR_BASELINE.md` seccion 4 "Riesgo 1".
"""
import functools
import time

from project_knowledge_graph.audit.query_log import latest_graph_snapshot, log_query
from project_knowledge_graph.dependency_graph.query import get_app_summary as _get_app_summary
from project_knowledge_graph.knowledge_graph.query import (
    build_graph_context_packet,
    build_change_plan as _build_change_plan,
    calculate_change_impact,
    find_configuration_for,
    find_consumers as _find_consumers,
    find_docs_for_change,
    find_endpoint as _find_endpoint,
    find_file as _find_file,
    find_symbol as _find_symbol,
    find_tests_for_change,
    resolve_change as _resolve_change,
    resolve_change_target as _find_node,
    trace_data_flow as _trace_data_flow,
    trace_execution as _trace_execution,
)
from project_knowledge_graph.snapshots.manager import latest_snapshot as _get_graph_status


def _logged(operation: str):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            result = fn(*args, **kwargs)
            duration_ms = (time.perf_counter() - start) * 1000
            log_query(operation, args, kwargs, result, duration_ms, latest_graph_snapshot())
            return result
        return wrapper
    return decorator


resolve_change = _logged("resolve_change")(_resolve_change)
find_symbol = _logged("find_symbol")(_find_symbol)
find_file = _logged("find_file")(_find_file)
find_endpoint = _logged("find_endpoint")(_find_endpoint)
find_consumers = _logged("find_consumers")(_find_consumers)
trace_data_flow = _logged("trace_data_flow")(_trace_data_flow)
trace_execution = _logged("trace_execution")(_trace_execution)
find_tests = _logged("find_tests")(find_tests_for_change)
find_docs = _logged("find_docs")(find_docs_for_change)
calculate_impact = _logged("calculate_impact")(calculate_change_impact)
build_change_plan = _logged("build_change_plan")(_build_change_plan)
build_context_packet = _logged("build_context_packet")(build_graph_context_packet)
find_configuration = _logged("find_configuration")(find_configuration_for)
find_node = _logged("find_node")(_find_node)
get_app_summary = _logged("get_app_summary")(_get_app_summary)
get_graph_status = _logged("get_graph_status")(_get_graph_status)

__all__ = [
    "resolve_change",
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
    "find_node",
    "get_app_summary",
    "get_graph_status",
]
