"""
graph_tools.py - Fase 9 de AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md

A diferencia del resto de tools/ (que llaman a Django via
tools/http_bridge.py, porque ese es el dato que vive en Django), el
Knowledge Graph vive DENTRO del propio proceso de ai_engine
(knowledge_graph.py/dependency_graph.py, poblado por auditor.py) -- estas
Tools lo consultan directo en memoria, sin HTTP, sin JWT.

Deliberadamente de solo lectura: side_effects=False, requires_confirmation=False.
Nunca escribe nada -- responde preguntas de arquitectura/impacto con datos
reales del grafo, en vez de que el LLM tenga que inferir o alucinar una
respuesta.
"""
from dependency_graph import build_impact_analysis_text, what_breaks_if_i_change
from knowledge_graph import find_node_context
from tools.metadata import ToolContext, ToolMetadata
from tools.registry import register_tool

GRAPH_IMPACT_METADATA = ToolMetadata(
    name="GraphImpactAnalysisTool",
    description=(
        "Analiza el radio de impacto REAL (grafo de dependencias del codigo, "
        "construido por auditor.py -- no una aproximacion ni una suposicion) si "
        "se modifica una App/Model/Serializer/ViewSet/Endpoint especifico. "
        "Responde 'que se rompe si cambio X' con evidencia concreta (archivos, "
        "aristas IMPORTS reales). Usar SIEMPRE que la pregunta sea sobre "
        "dependencias o impacto estructural del codigo -- nunca inventar esa "
        "respuesta sin consultar esta Tool primero."
    ),
    owner="ai_engine",
    capabilities=["analizar_impacto_arquitectura"],
    permissions=["IsAdminUser"],
    risk="low",
    audit_level="none",
    args_schema={
        "type": "object",
        "properties": {
            "entidad": {
                "type": "string",
                "description": "Nombre de la App/Model/Serializer/ViewSet a analizar, "
                                "ej. 'renting', 'Equipment', 'RentalRequestViewSet'.",
            },
        },
        "required": ["entidad"],
    },
)


@register_tool(GRAPH_IMPACT_METADATA)
async def graph_impact_analysis_tool(ctx: ToolContext, entidad: str) -> dict:
    """Envuelve dependency_graph.py::what_breaks_if_i_change()/build_impact_analysis_text()
    y knowledge_graph.py::find_node_context() -- ninguna llamada nueva, son las mismas
    funciones ya verificadas manualmente en AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md §15.3
    contra el caso real de 'renting'."""
    context = find_node_context(entidad)
    blast = what_breaks_if_i_change(entidad)
    return {
        "found": context.get("found", False),
        "entidad": entidad,
        "nodo": context.get("node"),
        "impacto_por_tipo": blast,
        "resumen_legible": build_impact_analysis_text(entidad) or
                            f"No se encontraron dependientes de '{entidad}' en el grafo.",
    }
