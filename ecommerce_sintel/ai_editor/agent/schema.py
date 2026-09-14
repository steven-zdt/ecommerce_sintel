"""
`AgentRunResult` -- FASE 51 "AI Editor Agent" (plan "AI Change Proposal
Engine", 2026-08-11). Consolida TODO lo que produjo una corrida de
`loop.run_autonomous_change_loop()` -- cada campo es el objeto REAL de
la fase correspondiente (nunca una copia/resumen fabricado), `None` si
el loop se detuvo antes de llegar a esa etapa (ver `detail` para el
motivo exacto).

Ningun campo de aca es "la decision final" -- `status` (via
`generation.pipeline_states.classify_pipeline_state()`) es, como maximo,
`APPROVAL_REQUIRED`; convertir eso en un cambio promovido sigue siendo,
siempre, una llamada humana aparte a `generation.promotion.
review_and_promote()`.
"""
from dataclasses import dataclass, field


@dataclass
class AgentRunResult:
    request: str
    status: str
    detail: str

    intent: object | None = None
    context: object | None = None
    plan: object | None = None
    plan_validation: object | None = None
    retry_outcome: object | None = None
    sandbox_loop_result: object | None = None

    code_quality_report: object | None = None
    architecture_report: object | None = None
    dependency_report: object | None = None
    contract_report: object | None = None
    test_awareness_report: object | None = None
    documentation_report: object | None = None
    reconciliation_report: object | None = None
    impact_recheck_report: object | None = None
    confidence_report: object | None = None
    promotion_gate_result: object | None = None
    human_review_text: str | None = None

    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        def _d(obj):
            return obj.to_dict() if obj is not None and hasattr(obj, "to_dict") else obj

        return {
            "request": self.request, "status": self.status, "detail": self.detail,
            "intent": _d(self.intent), "context": _d(self.context), "plan": _d(self.plan),
            "plan_validation": _d(self.plan_validation), "retry_outcome": _d(self.retry_outcome),
            "sandbox_loop_result": _d(self.sandbox_loop_result),
            "code_quality_report": _d(self.code_quality_report),
            "architecture_report": _d(self.architecture_report),
            "dependency_report": _d(self.dependency_report),
            "contract_report": _d(self.contract_report),
            "test_awareness_report": _d(self.test_awareness_report),
            "documentation_report": _d(self.documentation_report),
            "reconciliation_report": _d(self.reconciliation_report),
            "impact_recheck_report": _d(self.impact_recheck_report),
            "confidence_report": _d(self.confidence_report),
            "promotion_gate_result": _d(self.promotion_gate_result),
            "human_review_text": self.human_review_text,
            "warnings": self.warnings,
        }


__all__ = ["AgentRunResult"]
