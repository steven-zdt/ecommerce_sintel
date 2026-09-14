"""
Texto legible de analisis de impacto para inyeccion en prompts de LLM.
Extraido de ai_engine/dependency_graph.py::build_impact_analysis_text
(Fase 6, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).
"""
from project_knowledge_graph.dependency_graph.blast_radius import what_breaks_if_i_change


def build_impact_analysis_text(entity_name: str) -> str:
    """Analisis de impacto legible por humanos/LLM."""
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
