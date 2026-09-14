"""
`check_documentation_awareness()` -- FASE 43 "Documentation-Aware
Generation" (plan "AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro, aplicada literal: "Si el cambio afecta una
funcionalidad documentada, PatchProposal debe identificar
documentation_to_update. La documentacion NO debe modificarse
automaticamente en esta fase si eso aumenta el riesgo -- primero
producir propuesta."

**Ya garantizado por FASE 38 (verificado por test)**: ninguna operacion
de una `PatchProposal` puede escribir sobre un archivo `.md` -- el
guardrail de `proposal_validator._check_scope_and_operation()` excluye
documentacion explicitamente. Esta funcion agrega DOS capas mas, ambas
de solo lectura/reporte, nunca de escritura:
  1. Compara la documentacion que el GRAFO ya sabe que referencia el
     target (`context.resolution.documentation`, real, POST-GRAPH 3)
     contra lo que la propuesta declaro en `documentation_to_update`
     (FASE 43, campo nuevo) -- informativo, nunca bloquea (a veces un
     cambio genuinamente no afecta ninguna doc real).
  2. Defensa en profundidad: confirma que efectivamente NINGUNA
     operacion de la propuesta toca un `.md` -- si alguna vez esto
     ocurriera (ej. un bug futuro en la relajacion de FASE 38), esta
     funcion lo reportaria como ERROR en vez de fallar en silencio.
"""
from dataclasses import dataclass, field

SEVERITY_ERROR = "ERROR"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"


@dataclass
class DocumentationAwarenessReport:
    proposal_id: str
    status: str
    known_documentation: list[str] = field(default_factory=list)
    declared_documentation_to_update: list[str] = field(default_factory=list)
    undeclared_known_docs: list[str] = field(default_factory=list)
    unexpected_doc_writes: list[str] = field(default_factory=list)
    recommendation: str = ""

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "status": self.status,
            "known_documentation": self.known_documentation,
            "declared_documentation_to_update": self.declared_documentation_to_update,
            "undeclared_known_docs": self.undeclared_known_docs,
            "unexpected_doc_writes": self.unexpected_doc_writes,
            "recommendation": self.recommendation,
        }


def check_documentation_awareness(proposal, context=None) -> DocumentationAwarenessReport:
    """`proposal` es la `generation.models.PatchProposal`, `context` el
    `ChangeContext` (POST-GRAPH 3) opcional -- sin el, solo se corre la
    defensa en profundidad (punto 2 del docstring del modulo)."""
    unexpected_doc_writes = [op.file for op in proposal.operations if op.file.lower().endswith(".md")]

    known_docs: list[str] = []
    if context is not None:
        context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
        resolution = context_dict.get("resolution") or {}
        docs = resolution.get("documentation") or {}
        for category in ("architecture_docs", "implementation_docs", "audit_docs"):
            known_docs.extend(d["name"] for d in docs.get(category) or [] if d.get("name"))
    known_docs = sorted(set(known_docs))

    declared = sorted(set(proposal.documentation_to_update or []))
    undeclared_known_docs = sorted(set(known_docs) - set(declared))

    if unexpected_doc_writes:
        status = STATUS_FAIL
        recommendation = (
            f"La propuesta intenta ESCRIBIR sobre documentacion ({unexpected_doc_writes}) -- "
            "esto nunca deberia pasar (FASE 38 lo excluye estructuralmente); rechazar."
        )
    elif known_docs and undeclared_known_docs:
        status = STATUS_PASS
        recommendation = (
            f"El grafo conoce {len(known_docs)} documento(s) que referencian el target, la "
            f"propuesta no declaro {len(undeclared_known_docs)} en documentation_to_update: "
            f"{undeclared_known_docs}. Revisar si necesitan actualizarse."
        )
    else:
        status = STATUS_PASS
        recommendation = "Sin documentacion conocida pendiente de declarar."

    return DocumentationAwarenessReport(
        proposal_id=proposal.proposal_id, status=status,
        known_documentation=known_docs, declared_documentation_to_update=declared,
        undeclared_known_docs=undeclared_known_docs, unexpected_doc_writes=unexpected_doc_writes,
        recommendation=recommendation,
    )


__all__ = ["check_documentation_awareness", "DocumentationAwarenessReport", "STATUS_PASS", "STATUS_FAIL"]
