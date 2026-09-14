"""
what_breaks_if_i_change -- blast radius de una entidad. Extraido de ai_engine/
dependency_graph.py (Fase 6, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_
GRAPH, 2026-08-08).
"""
from project_knowledge_graph.dependency_graph.loader import get_dependency_graph


def what_breaks_if_i_change(entity_name: str) -> dict:
    """
    Devuelve el blast radius si entity_name cambia. entity_name puede ser
    'shop.Product', 'ProductSerializer', 'ProductViewSet', etc., o un nombre
    de app pelado ('renting') para agregar el impacto de todas las entidades
    de esa app.

    [CORREGIDO 2026-07-30, AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md S16 Fase 9]
    La rama de partial match envolvia el resultado en {"match:<key>": {...}} --
    una forma distinta a la del match exacto (dict[tipo] -> list[str]), y solo
    tomaba el PRIMER key que coincidiera (ej. preguntar por 'renting' devolvia
    solo el impacto de 'renting.Equipment', ignorando las otras ~150 entidades
    de esa app). build_impact_analysis_text() asumia siempre la forma plana y
    crasheaba (KeyError: slice(None, 4, None), blast[t] era un dict, no una
    lista, al intentar dict[:4]) -- encontrado probando GraphImpactAnalysisTool
    en vivo contra el caso real 'renting' que motivo toda esta auditoria,
    exactamente el escenario que debia funcionar.
    """
    dg = get_dependency_graph()
    change_impact = dg.get("change_impact", {})
    # Direct key match
    if entity_name in change_impact:
        return change_impact[entity_name]
    # Partial match -- agrega TODAS las coincidencias (no solo la primera) en
    # la misma forma plana que el match exacto, para que
    # build_impact_analysis_text() no necesite saber cual de las 2 ramas
    # produjo el resultado.
    merged: dict[str, list[str]] = {}
    for key, impact in change_impact.items():
        if entity_name.lower() not in key.lower():
            continue
        for node_type, items in impact.items():
            bucket = merged.setdefault(node_type, [])
            for item in items:
                if item not in bucket:
                    bucket.append(item)
    return merged
