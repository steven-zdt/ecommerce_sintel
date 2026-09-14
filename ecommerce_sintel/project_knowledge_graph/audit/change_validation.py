"""
Change Validation Report -- Fase 16 "Change Validation" (Site Knowledge
Graph, 2026-08-10).

El plan describe el flujo `PATCH -> SCAN -> GRAPH DIFF -> IMPACT ANALYSIS ->
TESTS -> CONTRACT VALIDATION -> GRAPH VALIDATION` DESPUES de que una IA
aplique un patch real. Ese `PATCH` no existe todavia (ver
`ai_editor/patch/`, Fase 14 -- deliberadamente no implementado, requiere
una decision humana separada dado el blast radius de modificar codigo
autonomamente). Lo que SI es real y verificable HOY: el estado actual del
working tree (`git diff` real, sin commitear) YA es un "cambio" en el
sentido que le importa a este reporte -- `build_change_validation_report()`
usa exactamente esa evidencia real (Fase 15: `detect_changed_symbols()`)
en vez de simular un patch hipotetico.

**Alcance deliberado sobre `tests_required`/`tests_passed`**: este modulo
CALCULA que tests son relevantes (evidencia real, Fase 7), pero NO los
ejecuta automaticamente -- muchos tests reales de este proyecto requieren
Postgres/Redis/Docker (ver limitacion ya documentada en sesiones previas:
"3 tests fallan porque redis... no es resoluble desde el host bare"),
correrlos automaticamente desde este modulo seria una operacion lenta y
potencialmente fallida por motivos ajenos al cambio real. Se reporta
`tests_required` (lista real) y `tests_run: false` con el motivo explicito
-- no se fabrica un resultado "tests_passed: true" sin haberlos corrido.
"""
import logging

from project_knowledge_graph.audit.validator import run_all_validations
from project_knowledge_graph.incremental.diff import detect_changed_symbols
from project_knowledge_graph.knowledge_graph.loader import get_knowledge_graph
from project_knowledge_graph.knowledge_graph.query import calculate_change_impact

logger = logging.getLogger(__name__)

_RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def build_change_validation_report() -> dict:
    """Compone TODO lo ya construido en fases anteriores (Fase 15:
    deteccion real de simbolos cambiados via git diff; Fase 10: impacto
    categorizado; validator ya existente: consistencia estructural del
    grafo) en el formato del "CHANGE VALIDATION REPORT" que pide 16 del
    plan. No reimplementa ninguna logica de deteccion/impacto -- solo
    agrega."""
    changed_symbols = detect_changed_symbols()

    files_changed = sorted({s["file"] for s in changed_symbols if s.get("file")})
    symbols_changed = [s["name"] for s in changed_symbols]

    contracts_changed: set[str] = set()
    frontend_affected: set[str] = set()
    backend_affected: set[str] = set()
    tests_required: set[str] = set()
    documentation_affected: set[str] = set()
    risk = "LOW"

    for sym in changed_symbols:
        impact = calculate_change_impact(sym["name"])
        if not impact.get("found"):
            continue

        for bucket in (impact["direct_impact"], impact["indirect_impact"]):
            contracts_changed.update(n["name"] for n in bucket["contract"])
            frontend_affected.update(n["name"] for n in bucket["frontend"])
            backend_affected.update(n["name"] for n in bucket["backend"])

        for t in impact["tests"]["direct_tests"] + impact["tests"]["indirect_tests"]:
            tests_required.add(t["name"])

        for cat in ("architecture_docs", "implementation_docs", "audit_docs"):
            documentation_affected.update(d["name"] for d in impact["documentation"][cat])

        if _RISK_ORDER.get(impact["risk"], 0) > _RISK_ORDER.get(risk, 0):
            risk = impact["risk"]

    graph_validation = run_all_validations()
    graph_consistency = {
        "summary": graph_validation["summary"],
        "consistent": all(count == 0 for count in graph_validation["summary"].values()),
    }

    contract_consistency = _check_contract_consistency(contracts_changed)

    return {
        "files_changed": files_changed,
        "symbols_changed": symbols_changed,
        "contracts_changed": sorted(contracts_changed),
        "frontend_affected": sorted(frontend_affected),
        "backend_affected": sorted(backend_affected),
        "tests_required": sorted(tests_required),
        "tests_run": False,
        "tests_run_note": (
            "No se ejecutan automaticamente -- muchos tests reales de este proyecto "
            "requieren Postgres/Redis/Docker no disponibles desde el host bare. "
            "Ejecutar manualmente: manage.py test <tests_required>"
        ),
        "documentation_affected": sorted(documentation_affected),
        "graph_consistency": graph_consistency,
        "contract_consistency": contract_consistency,
        "risk": risk,
    }


def _check_contract_consistency(contract_names: set) -> dict:
    """Para cada Endpoint afectado: sigue teniendo un Symbol real que lo
    implementa (`IMPLEMENTED_BY`) y al menos un Serializer real
    (`SERIALIZES`)? Reusa las aristas ya construidas (Fases 2/4), no
    inventa un chequeo nuevo de consistencia -- solo confirma que las
    aristas esperadas siguen presentes."""
    kg = get_knowledge_graph()
    inconsistent = []
    for name in contract_names:
        candidates = [n for n in kg.nodes_of_type("Endpoint") if n.name == name]
        if not candidates:
            inconsistent.append({"endpoint": name, "issue": "nodo Endpoint ya no existe"})
            continue
        ep = candidates[0]
        edges = {s["edge"] for s in kg.successors(ep.id)}
        if "IMPLEMENTED_BY" not in edges:
            inconsistent.append({"endpoint": name, "issue": "sin Symbol que lo implemente"})
        if "SERIALIZES" not in edges:
            inconsistent.append({"endpoint": name, "issue": "sin Serializer asociado"})
    return {"checked": len(contract_names), "consistent": not inconsistent, "issues": inconsistent}
