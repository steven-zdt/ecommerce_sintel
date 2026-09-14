"""
`check_promotion_gate()` -- FASE 46 "Promotion Gate" (plan "AI Change
Proposal Engine", 2026-08-11).

Regla del prompt maestro: "Solo permitir PROMOTE cuando: PatchProposal
valid AND Sandbox valid AND Tests pass AND Contracts pass AND Graph
reconciliation pass AND Impact acceptable AND Human approval."

**Cada condicion, mapeada a lo que este proyecto YA puede verificar de
verdad -- honesto sobre lo que no puede**:
  - `PatchProposal valid`   <- `SandboxLoopResult.apply_result.applied`
                               (FASE 29, re-validado en FASE 31)
  - `Sandbox valid`         <- `SandboxLoopResult.validation_report.
                               syntax_passed` (FASE 32/8, Nivel 1 real)
  - `Tests pass`            <- **NO VERIFICABLE hoy** -- los tests
                               identificados NUNCA se ejecutan (mismo
                               motivo estructural de siempre, sandbox
                               parcial sin Django/Postgres/Redis). Esta
                               funcion NO finge que "tests pass"; el
                               unico dato real disponible es "tests
                               requeridos identificados", ya visible en
                               `SandboxLoopResult.test_report`.
  - `Contracts pass`        <- `ContractCoverageReport.status` (FASE 41)
                               -- `PARTIAL_COVERAGE` es WARNING, no
                               bloquea por si solo (documentado, un
                               contrato puede cambiar retrocompatible)
  - `Graph reconciliation pass` <- `GraphReconciliationReport.status`
                               (FASE 34, version SCOPE) -- `FAIL` SI
                               bloquea
  - `Impact acceptable`     <- `ImpactRecheckReport.status` (FASE 35) --
                               `BLOCK` SI bloquea
  - `Human approval`        <- sigue siendo responsabilidad de
                               `promotion.review_and_promote()`
                               (`decision`/`confirm` obligatorios) --
                               este gate NO lo reemplaza, es un chequeo
                               PREVIO que un caller deberia correr antes
                               de siquiera pedirle a un humano que
                               revise.

Todos los reportes (salvo `sandbox_loop_result`) son OPCIONALES -- si el
caller no corrio esa fase, esa condicion simplemente no se evalua (no se
asume PASS ni FAIL de algo que nunca se calculo).
"""
from dataclasses import dataclass, field

STATUS_READY = "READY"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class PromotionGateResult:
    proposal_id: str
    status: str
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "status": self.status,
            "blocking_reasons": self.blocking_reasons, "warnings": self.warnings,
        }


def check_promotion_gate(
    sandbox_loop_result,
    reconciliation_report=None,
    impact_report=None,
    architecture_report=None,
    contract_report=None,
) -> PromotionGateResult:
    """NO reemplaza `promotion.review_and_promote()` -- es un chequeo
    PREVIO, mas amplio, que un caller puede correr antes de someter la
    propuesta a revision humana. `review_and_promote()` sigue exigiendo
    `decision`/`confirm` explicitos sin importar el resultado de aca."""
    blocking: list[str] = []
    warnings: list[str] = []

    if not sandbox_loop_result.ready_for_approval:
        blocking.append(
            "PatchProposal/Sandbox: no se aplico sobre el sandbox o fallo la validacion de "
            "sintaxis (FASE 29/31/32)."
        )

    if reconciliation_report is not None and reconciliation_report.status == "FAIL":
        blocking.append(
            f"Graph Reconciliation: FAIL -- impacto inesperado: {reconciliation_report.unexpected_impact}"
        )

    if impact_report is not None and impact_report.status == "BLOCK":
        blocking.append(f"Impact Recheck: BLOCK -- {impact_report.detail}")

    if architecture_report is not None and architecture_report.status == "FAIL":
        error_messages = [i.message for i in architecture_report.issues if i.severity == "ERROR"]
        blocking.append(f"Architectural Compliance: FAIL -- {error_messages}")

    if contract_report is not None and contract_report.status == "PARTIAL_COVERAGE":
        warnings.append(f"Contract Coverage: PARTIAL -- {contract_report.recommendation}")

    warnings.append(
        "Tests pass: NO VERIFICABLE -- los tests identificados nunca se ejecutan en este "
        "entorno (sandbox parcial); revisar test_report manualmente antes de aprobar."
    )

    status = STATUS_BLOCKED if blocking else STATUS_READY
    return PromotionGateResult(
        proposal_id=sandbox_loop_result.proposal_id, status=status,
        blocking_reasons=blocking, warnings=warnings,
    )


__all__ = ["check_promotion_gate", "PromotionGateResult", "STATUS_READY", "STATUS_BLOCKED"]
