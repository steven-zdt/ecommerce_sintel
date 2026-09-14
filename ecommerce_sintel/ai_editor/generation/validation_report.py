"""
`build_generation_validation_report()` -- FASE 33 "Automated Test Impact
Execution" (plan "AI Change Proposal Engine", 2026-08-11).

OBJETIVO real del prompt maestro: "Usar el conocimiento del grafo para
decidir que tests ejecutar" (`Changed Symbol -> TESTS/VALIDATES ->
Required Tests -> Execute`) y producir un `GenerationValidationReport`
con `syntax`/`tests`/`contracts`/`errors`/`warnings`.

**Lo que esta fase SI hace**: consolida en un unico reporte datos que YA
existen, calculados por fases anteriores -- cero logica de validacion
nueva, es agregacion y clasificacion honesta:
  - `syntax`      <- `SandboxLoopResult.validation_report` (FASE 32, que
                      a su vez reusa `validation.engine.run_validation()`,
                      POST-GRAPH 8, Nivel 1 real)
  - `tests`        <- `SandboxLoopResult.test_report` (FASE 32, que
                      reusa `validation.tests.build_test_validation_
                      report()`, POST-GRAPH 10, clasificacion real
                      required/recommended, sin ejecutar)
  - `contracts`    <- `context.resolution['contracts']` (ya resuelto,
                      POST-GRAPH 3/Fase 11) + cualquier `GenerationIssue`
                      con codigo `UNDECLARED_CONTRACT_CHANGE` que la
                      pre-validacion de FASE 29 ya haya encontrado
  - `errors`/`warnings` <- split por severidad de
                      `PatchApplicationResult.pre_validation_issues`
                      (FASE 29, ya calculado dentro del SandboxLoopResult)

**Lo que esta fase NO hace, honesto y explicito**: "Execute" de la parte
"Required Tests -> Execute" del diagrama del prompt maestro sigue
`NOT_IMPLEMENTED` -- MISMO motivo estructural documentado sin cambios
desde POST-GRAPH 8/10/FASE 32: el sandbox (POST-GRAPH 7) es una copia
PARCIAL de archivos, sin `settings.py`, otras apps, migraciones, ni
acceso a Postgres/Redis/Docker -- correr `manage.py test <nombre>` (el
test runner real del proyecto, no pytest -- ver nota de MEMORY.md sobre
`pytest-django` no instalado) requeriria un sandbox de tipo distinto
(copia completa del repo o git worktree real) mas la infraestructura
Docker, una decision de arquitectura mayor que ninguna fase de este plan
toma por su cuenta. `tests_executed` queda `False` explicito en todo
reporte, nunca se fabrica un resultado pass/fail de un test que nunca
corrio.
"""
from dataclasses import dataclass, field

TESTS_NOT_EXECUTED_REASON = (
    "El sandbox (POST-GRAPH 7) es una copia PARCIAL de archivos -- sin settings.py, otras apps "
    "Django, migraciones, ni acceso a Postgres/Redis/Docker. Ejecutar manage.py test requeriria "
    "un sandbox de tipo distinto (copia completa del repo o git worktree real) mas "
    "infraestructura Docker -- decision de arquitectura mayor, no tomada por su cuenta ni "
    "fingida como resuelta. Ejecutar manualmente: manage.py test <nombre_del_test>."
)

STATUS_PASS = "PASS"
STATUS_PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
STATUS_FAIL = "FAIL"


@dataclass
class GenerationValidationReport:
    proposal_id: str
    overall_status: str
    syntax_passed: bool | None
    syntax_details: dict = field(default_factory=dict)
    tests_required: list[str] = field(default_factory=list)
    tests_recommended: list[str] = field(default_factory=list)
    tests_executed: bool = False
    tests_not_executed_reason: str = TESTS_NOT_EXECUTED_REASON
    contracts_known: list[str] = field(default_factory=list)
    contracts_undeclared_changes: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "overall_status": self.overall_status,
            "syntax": {"passed": self.syntax_passed, "details": self.syntax_details},
            "tests": {
                "required": self.tests_required, "recommended": self.tests_recommended,
                "executed": self.tests_executed, "not_executed_reason": self.tests_not_executed_reason,
            },
            "contracts": {
                "known": self.contracts_known, "undeclared_changes": self.contracts_undeclared_changes,
            },
            "errors": self.errors,
            "warnings": self.warnings,
        }


def build_generation_validation_report(sandbox_loop_result, context=None) -> GenerationValidationReport:
    """`sandbox_loop_result` es un `generation.sandbox_loop.
    SandboxLoopResult` (FASE 32) YA calculado. `context` es el
    `ChangeContext` opcional (habilita la lista de `contracts_known`; sin
    el, esa lista simplemente queda vacia, no falla)."""
    validation_report = sandbox_loop_result.validation_report
    syntax_passed = validation_report.level_1_passed if validation_report else None
    syntax_details = validation_report.level_1_syntax if validation_report else {}

    test_report = sandbox_loop_result.test_report or {}
    tests_required = list(test_report.get("required") or [])
    tests_recommended = list(test_report.get("recommended") or [])

    context_dict = (context.to_dict() if hasattr(context, "to_dict") else dict(context)) if context else {}
    resolution = context_dict.get("resolution") or {}
    contracts_known = [c["name"] for c in (resolution.get("contracts") or [])]

    pre_validation_issues = sandbox_loop_result.apply_result.pre_validation_issues
    errors = [i.message for i in pre_validation_issues if i.severity == "ERROR"]
    warnings = [i.message for i in pre_validation_issues if i.severity == "WARNING"]
    contracts_undeclared_changes = [
        i.message for i in pre_validation_issues if i.code == "UNDECLARED_CONTRACT_CHANGE"
    ]

    if not sandbox_loop_result.ready_for_approval or errors:
        overall_status = STATUS_FAIL
    elif warnings:
        overall_status = STATUS_PASS_WITH_WARNINGS
    else:
        overall_status = STATUS_PASS

    return GenerationValidationReport(
        proposal_id=sandbox_loop_result.proposal_id,
        overall_status=overall_status,
        syntax_passed=syntax_passed,
        syntax_details=syntax_details,
        tests_required=tests_required,
        tests_recommended=tests_recommended,
        contracts_known=contracts_known,
        contracts_undeclared_changes=contracts_undeclared_changes,
        errors=errors,
        warnings=warnings,
    )


__all__ = [
    "build_generation_validation_report",
    "GenerationValidationReport",
    "TESTS_NOT_EXECUTED_REASON",
    "STATUS_PASS",
    "STATUS_PASS_WITH_WARNINGS",
    "STATUS_FAIL",
]
