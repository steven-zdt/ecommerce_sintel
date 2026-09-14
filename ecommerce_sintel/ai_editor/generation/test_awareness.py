"""
`check_test_awareness()` -- FASE 42 "Test-Aware Generation" (plan "AI
Change Proposal Engine", 2026-08-11).

Regla del prompt maestro: "El LLM debe conocer los tests relevantes
antes de generar... Si cambia comportamiento, PatchProposal debe indicar
tests_to_update/tests_to_add/tests_to_remove. No eliminar tests
simplemente porque dificultan el cambio."

"Conocer los tests relevantes ANTES de generar" ya ocurre desde
FASE 26 (`context.build_generation_context()` incluye `test_context`,
los tests reales identificados por el grafo, POST-GRAPH 10) -- esta
fase agrega la parte de VALIDACION posterior: `PatchProposal` ahora
distingue `tests_to_update`/`tests_to_add`/`tests_to_remove` (FASE 25
extendido) en vez de una sola lista fusionada, y esta funcion verifica
la regla explicita "no eliminar tests sin declararlo": una operacion
`DELETE` sobre un archivo que PARECE un archivo de test (convencion real
del proyecto: `tests.py`, `test_*.py`, `*_test.py`, `tests_*.py`) que NO
esta declarada en `tests_to_remove` es un `ERROR` bloqueante -- si SI
esta declarada, queda como `WARNING` (visible para revision humana, no
silenciosa, pero no bloquea: eliminar un test obsoleto de verdad es
legitimo si se declara por que).
"""
import re
from dataclasses import dataclass, field

SEVERITY_ERROR = "ERROR"
SEVERITY_WARNING = "WARNING"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"

_TEST_FILE_RE = re.compile(r"(^|/)(tests\.py|test_[\w]+\.py|[\w]+_test\.py|tests_[\w]+\.py)$")


@dataclass
class TestAwarenessIssue:
    file: str
    severity: str
    message: str

    def to_dict(self) -> dict:
        return {"file": self.file, "severity": self.severity, "message": self.message}


@dataclass
class TestAwarenessReport:
    proposal_id: str
    status: str
    issues: list[TestAwarenessIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "status": self.status,
            "issues": [i.to_dict() for i in self.issues],
        }


def _looks_like_test_file(file: str) -> bool:
    return bool(_TEST_FILE_RE.search(file))


def check_test_awareness(proposal) -> TestAwarenessReport:
    """`proposal` es la `generation.models.PatchProposal` a evaluar."""
    declared_removals = set(proposal.tests_to_remove or [])
    issues: list[TestAwarenessIssue] = []

    for op in proposal.operations:
        if op.operation != "DELETE" or not _looks_like_test_file(op.file):
            continue
        if op.file in declared_removals or any(op.file in name for name in declared_removals):
            issues.append(TestAwarenessIssue(
                file=op.file, severity=SEVERITY_WARNING,
                message=f"'{op.file}' se elimina, declarado en tests_to_remove -- confirmar que "
                        "la razon es real (test obsoleto), no solo que dificultaba el cambio.",
            ))
        else:
            issues.append(TestAwarenessIssue(
                file=op.file, severity=SEVERITY_ERROR,
                message=f"'{op.file}' es un archivo de test que se elimina SIN declararlo en "
                        "tests_to_remove -- regla explicita: no eliminar tests simplemente "
                        "porque dificultan el cambio.",
            ))

    status = STATUS_FAIL if any(i.severity == SEVERITY_ERROR for i in issues) else STATUS_PASS
    return TestAwarenessReport(proposal_id=proposal.proposal_id, status=status, issues=issues)


__all__ = ["check_test_awareness", "TestAwarenessReport", "TestAwarenessIssue", "STATUS_PASS", "STATUS_FAIL"]
