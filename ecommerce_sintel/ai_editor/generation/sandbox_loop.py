"""
`run_sandbox_validation_loop()` -- FASE 32 "Sandbox Generation Loop"
(plan "AI Change Proposal Engine", 2026-08-11).

Flujo del prompt maestro, literal:
    PatchProposal -> Sandbox -> Apply -> Syntax Validation -> Tests
    "El repositorio principal permanece intacto."

Cero logica nueva de validacion -- esta fase solo ENCADENA piezas ya
reales y ya probadas por separado, ninguna reimplementada:
    repository.create_sandbox(plan)              (POST-GRAPH 7)
    generation.patch_integration.apply_proposal_to_sandbox()  (FASE 31)
    validation.engine.run_validation(sandbox, plan)            (POST-GRAPH 8, Nivel 1 sintaxis)
    validation.tests.build_test_validation_report(context)     (POST-GRAPH 10, clasifica sin ejecutar)

A diferencia de `apply_proposal_to_sandbox()` (FASE 31, que espera un
sandbox ya creado por el caller porque su ciclo de vida sigue mas alla,
hacia aprobacion/promocion), esta funcion CREA su propio sandbox --
representa un ciclo completo "probar esta propuesta de punta a punta" en
una sola llamada. El `Sandbox` resultante NO se limpia automaticamente
(mismo criterio que `create_sandbox()` en si): si `ready_for_approval`
es `True`, el caller lo necesita intacto para el siguiente paso
(`approval`/`repository.promote_to_workspace()`, ya existentes); si es
`False`, el caller decide si inspeccionarlo antes de `sandbox.cleanup()`.

`WORKSPACE_ROOT` (el checkout real) nunca se toca en ningun punto de
este flujo -- ni `create_sandbox()` ni `apply_proposal_to_sandbox()` ni
`run_validation()` escriben fuera del sandbox temporal.
"""
from dataclasses import dataclass

from ai_editor.generation.models import PatchApplicationResult
from ai_editor.generation.patch_integration import apply_proposal_to_sandbox
from ai_editor.repository import Sandbox, create_sandbox
from ai_editor.validation.engine import ValidationReport, run_validation
from ai_editor.validation.tests import build_test_validation_report


@dataclass
class SandboxLoopResult:
    proposal_id: str
    sandbox: Sandbox
    apply_result: PatchApplicationResult
    validation_report: ValidationReport | None
    test_report: dict | None
    ready_for_approval: bool

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "sandbox_root": str(self.sandbox.root),
            "apply_result": self.apply_result.to_dict(),
            "validation_report": self.validation_report.to_dict() if self.validation_report else None,
            "test_report": self.test_report,
            "ready_for_approval": self.ready_for_approval,
        }


def run_sandbox_validation_loop(proposal, plan, context=None) -> SandboxLoopResult:
    """`proposal` es una `generation.models.PatchProposal` YA generada
    (`generator.generate_patch_proposal()`/`retry.generate_with_retry()`)
    -- esta funcion no genera nada, solo prueba una propuesta que ya
    existe. `plan`/`context` son los mismos objetos que el resto del
    pipeline de `generation/` ya espera.

    `ready_for_approval=True` significa UNICAMENTE que el patch se aplico
    sobre el sandbox y paso sintaxis (Nivel 1) -- NO implica aprobacion
    humana, NO implica que los tests identificados pasen (nunca se
    ejecutan aca, mismo motivo documentado en POST-GRAPH 8/10: el sandbox
    parcial no provee Django/Postgres/Redis). El nombre es deliberado:
    "listo para que un humano lo revise", no "listo para promover"."""
    sandbox = create_sandbox(plan)

    apply_result = apply_proposal_to_sandbox(sandbox, proposal, plan, context)

    validation_report = run_validation(sandbox, plan) if apply_result.applied else None
    test_report = build_test_validation_report(context) if context is not None else None

    ready = bool(
        apply_result.applied
        and validation_report is not None
        and validation_report.level_1_passed
    )

    return SandboxLoopResult(
        proposal_id=proposal.proposal_id,
        sandbox=sandbox,
        apply_result=apply_result,
        validation_report=validation_report,
        test_report=test_report,
        ready_for_approval=ready,
    )


__all__ = ["run_sandbox_validation_loop", "SandboxLoopResult"]
