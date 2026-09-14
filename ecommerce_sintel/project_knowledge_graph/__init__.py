"""
project_knowledge_graph -- analisis estructural del proyecto (Project Map,
Knowledge Graph, Dependency Graph, Auditoria) como modulo independiente de
ai_engine. Ver PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH y
PROJECT_KNOWLEDGE_GRAPH_INVENTORY.md.

Deliberadamente sin imports aca: cada submodulo (scanner, project_map,
knowledge_graph, ...) importa project_knowledge_graph.config directamente
cuando lo necesita, para no forzar la resolucion de BASE_DIR (que puede
lanzar RuntimeError, Regla 13 del plan) solo por importar el paquete.
"""
