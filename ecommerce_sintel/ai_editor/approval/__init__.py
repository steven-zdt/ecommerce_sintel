"""
ai_editor.approval -- POST-GRAPH 11 "Human Approval Gate" (rediseno "AI
Editor Runtime", 2026-08-11). NUEVO submodulo (no estaba en los 7 + `llm`
originales -- justificado igual que `llm/` en POST-GRAPH 2: el prompt
maestro lo pide explicito y no encaja limpio dentro de ninguno de los
7 originales).

`build_change_summary()` compone el resumen legible para revision humana.
`record_decision()` valida y registra la decision
(`APPROVE`/`REJECT`/`MODIFY_PLAN`/`REQUEST_EXPLANATION`) -- el punto de
parada estructural antes de que cualquier cosa se promueva al repo real
(POST-GRAPH 12).
"""
from ai_editor.approval.gate import build_change_summary, record_decision
from ai_editor.approval.schema import (
    DECISION_APPROVE,
    DECISION_MODIFY_PLAN,
    DECISION_REJECT,
    DECISION_REQUEST_EXPLANATION,
    ApprovalRecord,
    ChangeSummary,
)

__all__ = [
    "build_change_summary",
    "record_decision",
    "ChangeSummary",
    "ApprovalRecord",
    "DECISION_APPROVE",
    "DECISION_REJECT",
    "DECISION_MODIFY_PLAN",
    "DECISION_REQUEST_EXPLANATION",
]
