# Graph Client (`ai_editor/graph_client/`)

La FRONTERA OFICIAL entre `ai_editor` y `project_knowledge_graph`
(POST-GRAPH 1). Wrapper de SOLO LECTURA -- re-exporta
`project_knowledge_graph.graph_sdk` por identidad de objeto (no copia,
verificado por `is`), sin agregar logica propia.

**Regla**: ningun otro submodulo de `ai_editor` debe importar
`project_knowledge_graph.knowledge_graph.*`/`.internal.*` directo --
siempre a traves de este modulo.

## Las 16 operaciones

13 de Fase 14 (Site Knowledge Graph) + 3 agregadas en POST-GRAPH 1:

```python
resolve_change(request)          # envelope completo: files/symbols/contracts/tests/docs/risk
find_symbol(name)                # exacto-antes-que-fuzzy
find_file(path)                  # exacto-antes-que-fuzzy
find_endpoint(query)             # exacto-antes-que-fuzzy
find_consumers(target)           # quien consume/llama/lee el target
trace_data_flow(target)          # database -> serializer -> API -> frontend
trace_execution(start)           # FUNCTION -> API -> SERVICE -> DATABASE -> TASK
find_tests(target)               # tests directos e indirectos
find_docs(query)                 # documentacion relevante, con scoring
calculate_impact(target)         # impacto directo/indirecto categorizado + riesgo
build_change_plan(request)       # subconjunto de resolve_change enfocado en riesgo/orden
build_context_packet(request)    # version COMPRIMIDA para consumo LLM
find_configuration(query)        # donde esta configurada una funcionalidad
find_node(name)                  # [POST-GRAPH 1] resolucion generica EXACTA
get_app_summary(app_name)        # [POST-GRAPH 1] modelos/viewsets/endpoints/tests de una app
get_graph_status()               # [POST-GRAPH 1] conteos + timestamp del ultimo snapshot
```

Todas devuelven dicts planos (JSON-serializables), nunca instancias de
`Node`/`KnowledgeGraph`. Todas quedan instrumentadas con logging de
auditoria (`project_knowledge_graph.audit.query_log`, Fase 18 del Site
Knowledge Graph) -- nunca persiste `meta` completo de un nodo.

## Por que `find_node()` NO usa `find_node_context()`

Pese al nombre parecido, `find_node()` reusa
`knowledge_graph.query.resolve_change_target()` (exacto-antes-que-fuzzy,
mismo criterio que `find_symbol`/`find_endpoint`/`find_file`), NO
`find_node_context()` (que hace matching FUZZY puro, sin preferencia por
coincidencia exacta -- un bug conocido y deliberadamente no corregido en
Fase 10 del Site Knowledge Graph, para no regresionar `impact_chain()`).
Probado real: `find_node("Product")` resuelve exacto al Model real; si
usara `find_node_context()`, "Equipment" (mencion de negocio real pero
sin Model correspondiente en Renting) devolveria un match FUZZY
irrelevante (`FeaturedEquipmentCardSerializer`) en vez de `None`.

## Ejemplo real

```python
from ai_editor import graph_client

node = graph_client.find_node("EquipmentViewSet.check_availability")
# {'id': 'symbol:renting/api/views.py:EquipmentViewSet.check_availability', 'type': 'Symbol', ...}

summary = graph_client.get_app_summary("renting")
# {'models': [], 'viewsets': ['EquipmentViewSet', ...], 'endpoints': [...], 'tests': [...]}

status = graph_client.get_graph_status()
# {'kg_nodes': 9575, 'kg_edges': 20335, 'timestamp': '...', ...}
```
