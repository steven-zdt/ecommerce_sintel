"""
`compute_composite_confidence()` -- FASE 44 "Confidence Engine" (plan
"AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro: "Calcular confianza de la propuesta. Factores:
graph certainty, target certainty, contract certainty, test coverage,
architecture compliance, LLM confidence, validation results."

**Cada factor de aca es un dato YA REAL, calculado por una fase
anterior -- ninguno se inventa para esta fase**:
  - `llm_confidence`      <- `PatchProposal.confidence.score` (FASE 25/28,
                             auto-reportada por el LLM)
  - `target_certainty`    <- `ChangeContext.status` (POST-GRAPH 3):
                             `RESOLVED`=1.0, `PARTIALLY_RESOLVED`=0.5,
                             cualquier otra cosa=0.0
  - `syntax_validation`   <- `GenerationValidationReport.syntax_passed`
                             (FASE 33, Nivel 1 real): `True`=1.0,
                             `False`=0.0, `None` (no corrido)=excluido
  - `architecture_compliance` <- `ArchitecturalComplianceReport.status`
                             (FASE 37): `PASS`=1.0, `FAIL`=0.0
  - `contract_coverage`   <- `ContractCoverageReport.status` (FASE 41):
                             `FULL_COVERAGE`/`NOT_APPLICABLE`=1.0,
                             `PARTIAL_COVERAGE`=0.5

**Cada factor es OPCIONAL** -- si el caller no corrio esa fase todavia
(ej. solo tiene la `PatchProposal` recien generada, sin sandbox ni
reportes de validacion), ese factor simplemente NO participa, no se
fabrica un valor por default. El score final es el PROMEDIO SIMPLE de
los factores disponibles -- nunca una ponderacion con numeros inventados
sin una justificacion real detras (una ponderacion "correcta" requeriria
datos historicos de que factores predicen mejor un resultado real, que
este proyecto no tiene todavia).

"graph certainty" del prompt maestro se cubre con `target_certainty`
(la unica certeza real que el grafo aporta hoy es si pudo resolver el
target exacto o no, POST-GRAPH 3) -- no hay una metrica separada de
"certeza del grafo en si" mas alla de eso.
"""
from dataclasses import dataclass, field

from ai_editor.generation.models import GenerationConfidence


@dataclass
class ConfidenceFactor:
    name: str
    score: float
    source: str

    def to_dict(self) -> dict:
        return {"name": self.name, "score": self.score, "source": self.source}


@dataclass
class CompositeConfidenceReport:
    proposal_id: str
    composite: GenerationConfidence
    factors: list[ConfidenceFactor] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "composite": self.composite.to_dict(),
            "factors": [f.to_dict() for f in self.factors],
        }


def compute_composite_confidence(
    proposal, context=None, validation_report=None,
    architecture_report=None, contract_report=None,
) -> CompositeConfidenceReport:
    """Todos los reportes son OPCIONALES salvo `proposal` (siempre
    tiene su propio `confidence` auto-reportado). `validation_report`
    espera especificamente un `generation.validation_report.
    GenerationValidationReport` (FASE 33, atributo `.syntax_passed`) --
    NO el `ai_editor.validation.engine.ValidationReport` crudo de
    `SandboxLoopResult.validation_report` (atributo `.level_1_passed`,
    otro tipo). Construir el primero con `build_generation_validation_
    report(sandbox_loop_result, context)` antes de llamar aca."""
    factors: list[ConfidenceFactor] = [
        ConfidenceFactor("llm_confidence", proposal.confidence.score, "PatchProposal.confidence (FASE 28)"),
    ]

    if context is not None:
        context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
        status = context_dict.get("status")
        target_score = 1.0 if status == "RESOLVED" else 0.5 if status == "PARTIALLY_RESOLVED" else 0.0
        factors.append(ConfidenceFactor("target_certainty", target_score, "ChangeContext.status (POST-GRAPH 3)"))

    if validation_report is not None and validation_report.syntax_passed is not None:
        syntax_score = 1.0 if validation_report.syntax_passed else 0.0
        factors.append(ConfidenceFactor(
            "syntax_validation", syntax_score, "GenerationValidationReport.syntax_passed (FASE 33)",
        ))

    if architecture_report is not None:
        arch_score = 1.0 if architecture_report.status == "PASS" else 0.0
        factors.append(ConfidenceFactor(
            "architecture_compliance", arch_score, "ArchitecturalComplianceReport.status (FASE 37)",
        ))

    if contract_report is not None:
        contract_score = 0.0 if contract_report.status == "PARTIAL_COVERAGE" else 1.0
        factors.append(ConfidenceFactor(
            "contract_coverage", contract_score, "ContractCoverageReport.status (FASE 41)",
        ))

    composite_score = sum(f.score for f in factors) / len(factors)
    composite = GenerationConfidence.from_score(composite_score)

    return CompositeConfidenceReport(proposal_id=proposal.proposal_id, composite=composite, factors=factors)


__all__ = ["compute_composite_confidence", "CompositeConfidenceReport", "ConfidenceFactor"]
