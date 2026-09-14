"""
`review_and_promote()` -- encadena `generation/` (FASE 24-32) con
`approval/` (POST-GRAPH 11) y `repository.promote_to_workspace()`
(POST-GRAPH 12) en un unico flujo, tal como pide la seccion "OBJETIVO
FINAL" del prompt maestro: ... -> SANDBOX -> TEST -> ... -> HUMAN
APPROVAL -> PROMOTE.

Mapea conceptualmente a FASE 45 "Human Review UI/CLI" (sin UI, solo el
mecanismo de union) + FASE 46 "Promotion Gate" del plan de 60 fases --
ninguna de las dos se construyo formalmente todavia como fase numerada
propia con su propio checkpoint; esto es la version MINIMA pedida
explicitamente ("encadenar generation con approval/repository"), no una
implementacion completa de esas 2 fases futuras (sin interfaz de
revision real, sin Graph Reconciliation/Impact Recheck -- ambos siguen
`NOT_IMPLEMENTED`, heredado de POST-GRAPH 9, que FASE 46 completa
exigiria antes de promover).

REGLA FINAL DE SEGURIDAD del prompt maestro, cumplida literal aca:
"Nunca permitir LLM -> WRITE -> PRODUCTION." Esta funcion NUNCA decide
por su cuenta aprobar nada -- `decision`/`confirm` son parametros
OBLIGATORIOS que deben venir de una revision humana real; no hay ningun
default que permita promover sin que ambos se pasen explicitamente
(`confirm` default es `False`, nunca `True`). Las 5 capas de guardrail
de `promote_to_workspace()` (POST-GRAPH 12/20) siguen aplicando tal
cual, no se relajan ni se duplican aca.
"""
from dataclasses import dataclass

from ai_editor.approval.gate import build_change_summary, record_decision
from ai_editor.approval.schema import ApprovalRecord, ChangeSummary, DECISION_APPROVE
from ai_editor.repository.promote import PromoteResult, promote_to_workspace
from ai_editor.repository.rollback import RollbackResult, rollback_promotion


@dataclass
class PromotionOutcome:
    proposal_id: str
    promoted: bool
    change_summary: ChangeSummary
    approval: ApprovalRecord | None
    promote_result: PromoteResult | None
    blocked_reason: str | None

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "promoted": self.promoted,
            "change_summary": self.change_summary.to_dict(),
            "approval": self.approval.to_dict() if self.approval else None,
            "promote_result": self.promote_result.to_dict() if self.promote_result else None,
            "blocked_reason": self.blocked_reason,
        }


def review_and_promote(sandbox_loop_result, context, plan, workspace_root, decision: str,
                        reviewer_note: str | None = None, confirm: bool = False) -> PromotionOutcome:
    """`sandbox_loop_result` es un `generation.sandbox_loop.
    SandboxLoopResult` (FASE 32) YA calculado -- esta funcion no vuelve a
    aplicar ni a validar nada, solo compone el resumen para revision y
    encadena la decision hacia `promote_to_workspace()`.

    `decision`/`confirm` DEBEN venir de una revision humana real de
    `PromotionOutcome.change_summary.render_text()` -- esta funcion no
    los infiere ni los defaultea a un valor que permita avanzar solo.
    `workspace_root` es obligatorio y explicito (mismo criterio que
    `promote_to_workspace()`), nunca defaultea a `ai_editor.workspace.
    WORKSPACE_ROOT`."""
    summary = build_change_summary(
        context, plan, sandbox_loop_result.validation_report, sandbox_loop_result.test_report,
    )

    if not sandbox_loop_result.ready_for_approval:
        return PromotionOutcome(
            proposal_id=sandbox_loop_result.proposal_id, promoted=False, change_summary=summary,
            approval=None, promote_result=None,
            blocked_reason="La propuesta no quedo 'ready_for_approval' en el Sandbox Generation "
                            "Loop (FASE 32) -- no se aplico o fallo la validacion de sintaxis; no "
                            "hay nada seguro que someter a revision humana.",
        )

    approval = record_decision(decision, reviewer_note=reviewer_note)

    if approval.decision != DECISION_APPROVE:
        return PromotionOutcome(
            proposal_id=sandbox_loop_result.proposal_id, promoted=False, change_summary=summary,
            approval=approval, promote_result=None,
            blocked_reason=f"Decision humana registrada: {approval.decision} -- no se promueve.",
        )

    promote_result = promote_to_workspace(
        sandbox_loop_result.sandbox, approval, workspace_root, confirm=confirm,
        validation_report=sandbox_loop_result.validation_report,
    )
    promoted = promote_result.status == "PROMOTED"
    return PromotionOutcome(
        proposal_id=sandbox_loop_result.proposal_id, promoted=promoted, change_summary=summary,
        approval=approval, promote_result=promote_result,
        blocked_reason=None if promoted else promote_result.detail,
    )


def rollback_outcome(workspace_root, outcome: PromotionOutcome) -> RollbackResult:
    """FASE 47 "Rollback" -- reusa `repository.rollback.
    rollback_promotion()` (POST-GRAPH 16) tal cual, con la unica
    conveniencia de aceptar el `PromotionOutcome` de `review_and_
    promote()` directo en vez de que el caller tenga que extraer
    `.promote_result` a mano. `outcome.promoted` debe ser `True` -- si la
    propuesta nunca se promovio, no hay nada que revertir (mismo
    resultado `NOTHING_TO_ROLLBACK` que ya devuelve `rollback_
    promotion()` para ese caso, no se duplica esa logica aca)."""
    return rollback_promotion(workspace_root, outcome.promote_result)


__all__ = ["review_and_promote", "rollback_outcome", "PromotionOutcome"]
