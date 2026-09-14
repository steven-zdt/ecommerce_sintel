"""
`reconcile_change_scope()` -- FASE 34 "Graph Reconciliation" (plan "AI
Change Proposal Engine", 2026-08-11) -- version SCOPE, NO reconstruccion
completa del grafo.

`ai_editor.validation.reconciliation.reconcile_graph()` (POST-GRAPH 9)
documenta `NOT_IMPLEMENTED` por DOS motivos reales:
  1. El sandbox (POST-GRAPH 7) es una copia PARCIAL de archivos -- no se
     puede reconstruir `project_knowledge_graph` completo ahi para
     comparar "grafo antes" vs "grafo despues" via re-scanning real.
  2. En ese momento, `ai_editor.patch` no generaba contenido real (POST-
     GRAPH 6, alcance deliberado) -- no habia un escenario real de
     "impacto inesperado" que reconciliar.

**Motivo #1 sigue aplicando sin cambios** -- reconstruir el grafo
COMPLETO desde el sandbox sigue siendo estructuralmente imposible con el
diseno actual, esta funcion NO lo intenta.

**Motivo #2 YA NO APLICA** -- desde FASE 25-33, `generation/` SI produce
`PatchProposal` reales atribuibles a un LLM. Eso habilita una version MAS
ACOTADA de reconciliacion que NO requiere reconstruir el grafo: comparar
el SCOPE PREDICHO (`ChangePlan`/`ChangeContext.resolution`, calculados
ANTES del patch contra el grafo real completo, Fase 10/11 del Site
Knowledge Graph) contra el SCOPE REAL de la `PatchProposal` (que archivos/
simbolos declara tocar). Es exactamente el formato del EJEMPLO del
prompt maestro: "Plan: 3 files, 5 symbols, 1 endpoint" vs "Resultado: 3
files, 5 symbols, 1 endpoint" -> PASS; si difiere -> FAIL, UNEXPECTED
IMPACT.

**Honestidad sobre que detecta esto de verdad**: los conteos "actual"
vienen de lo que la PatchProposal DECLARA (`operations[].file`/`.symbol`),
no de un re-scan del codigo real -- si una propuesta touchea un archivo
fuera del plan, FASE 29 (`validate_proposal_against_repo`) YA lo detecta
como `FILE_OUTSIDE_PLAN`/`OPERATION_NOT_ALLOWED_FOR_STEP`/
`UNDECLARED_CONTRACT_CHANGE`; esta funcion no duplica esa deteccion, la
REUSA (via `SandboxLoopResult.apply_result.pre_validation_issues`, ya
calculado) y la empaqueta en el formato PREDICHO-vs-REAL con conteos que
pide el prompt maestro. No es deteccion nueva, es un reporte nuevo sobre
datos ya reales.
"""
from dataclasses import dataclass, field

FULL_GRAPH_REBUILD_NOT_IMPLEMENTED_REASON = (
    "Reconstruir el grafo COMPLETO desde el sandbox (para comparar GRAPH BEFORE vs GRAPH AFTER "
    "via re-scanning real, no solo contar el scope declarado) sigue NOT_IMPLEMENTED -- el sandbox "
    "(POST-GRAPH 7) es una copia PARCIAL de archivos, no el proyecto completo, mismo motivo "
    "estructural documentado en POST-GRAPH 9 (ai_editor.validation.reconciliation.reconcile_"
    "graph()). La razon #2 de esa fase ('ai_editor.patch no genera contenido real') ya NO aplica "
    "desde que generation/ (FASE 25-33) produce PatchProposal reales -- por eso esta funcion SI "
    "puede comparar el SCOPE predicho vs el scope real de una propuesta, sin necesitar "
    "reconstruir el grafo completo."
)

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

_UNEXPECTED_IMPACT_CODES = ("FILE_OUTSIDE_PLAN", "OPERATION_NOT_ALLOWED_FOR_STEP", "UNDECLARED_CONTRACT_CHANGE")


@dataclass
class GraphReconciliationReport:
    proposal_id: str
    status: str
    predicted_files: int
    predicted_symbols: int
    predicted_endpoints: int
    actual_files: int
    actual_symbols: int
    unexpected_impact: list[str] = field(default_factory=list)
    full_graph_rebuild_status: str = "NOT_IMPLEMENTED"
    full_graph_rebuild_reason: str = FULL_GRAPH_REBUILD_NOT_IMPLEMENTED_REASON

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "status": self.status,
            "predicted": {
                "files": self.predicted_files, "symbols": self.predicted_symbols,
                "endpoints": self.predicted_endpoints,
            },
            "actual": {"files": self.actual_files, "symbols": self.actual_symbols},
            "unexpected_impact": self.unexpected_impact,
            "full_graph_rebuild_status": self.full_graph_rebuild_status,
            "full_graph_rebuild_reason": self.full_graph_rebuild_reason,
        }


def reconcile_change_scope(proposal, sandbox_loop_result, plan, context=None) -> GraphReconciliationReport:
    """`proposal` es la `generation.models.PatchProposal` que se aplico.
    `sandbox_loop_result` es el `SandboxLoopResult` (FASE 32) de esa
    misma propuesta -- reusa `apply_result.pre_validation_issues` (FASE
    29, ya calculado) en vez de volver a validar. `plan`/`context` son
    los mismos objetos que el resto del pipeline ya espera."""
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    steps = plan_dict.get("steps") or []
    predicted_files = len({s["file"] for s in steps if s.get("file")})
    predicted_symbols = len({s["symbol"] for s in steps if s.get("symbol")})

    context_dict = (context.to_dict() if hasattr(context, "to_dict") else dict(context)) if context else {}
    resolution = context_dict.get("resolution") or {}
    predicted_endpoints = len([c for c in (resolution.get("contracts") or []) if c.get("type") == "Endpoint"])

    actual_files = len({op.file for op in proposal.operations})
    actual_symbols = len({op.symbol for op in proposal.operations if op.symbol})

    # FASE 38 (2026-08-11): UNDECLARED_CONTRACT_CHANGE se degrado a WARNING
    # en proposal_validator.py (un contrato REVIEW real ya no es "impacto
    # inesperado", es cross-stack legitimo) -- filtrar por severidad ERROR
    # evita que un cambio cross-stack valido reporte RECONCILIATION=FAIL.
    pre_validation_issues = sandbox_loop_result.apply_result.pre_validation_issues
    unexpected_impact = [
        i.message for i in pre_validation_issues
        if i.code in _UNEXPECTED_IMPACT_CODES and i.severity == "ERROR"
    ]

    status = STATUS_FAIL if unexpected_impact else STATUS_PASS
    return GraphReconciliationReport(
        proposal_id=proposal.proposal_id, status=status,
        predicted_files=predicted_files, predicted_symbols=predicted_symbols,
        predicted_endpoints=predicted_endpoints,
        actual_files=actual_files, actual_symbols=actual_symbols,
        unexpected_impact=unexpected_impact,
    )


__all__ = [
    "reconcile_change_scope",
    "GraphReconciliationReport",
    "FULL_GRAPH_REBUILD_NOT_IMPLEMENTED_REASON",
    "STATUS_PASS",
    "STATUS_FAIL",
]
