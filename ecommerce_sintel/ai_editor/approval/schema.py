"""
`ChangeSummary`/`ApprovalRecord` -- POST-GRAPH 11 "Human Approval Gate"
(rediseno "AI Editor Runtime", 2026-08-11).
"""
import datetime
from dataclasses import dataclass, field

DECISION_APPROVE = "APPROVE"
DECISION_REJECT = "REJECT"
DECISION_MODIFY_PLAN = "MODIFY_PLAN"
DECISION_REQUEST_EXPLANATION = "REQUEST_EXPLANATION"
_VALID_DECISIONS = {DECISION_APPROVE, DECISION_REJECT, DECISION_MODIFY_PLAN, DECISION_REQUEST_EXPLANATION}


@dataclass
class ChangeSummary:
    request: str
    interpretation: dict
    files: list[str] = field(default_factory=list)
    symbols: list[str] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)
    risk: str = "UNKNOWN"
    total_affected: int = 0
    patch_operations: int = 0
    tests: dict = field(default_factory=dict)
    documentation: list[str] = field(default_factory=list)
    validation_status: str = "UNKNOWN"
    validation_issues: list[str] = field(default_factory=list)
    unexpected_changes_note: str = "No verificado -- Graph Reconciliation (POST-GRAPH 9) esta NOT_IMPLEMENTED."

    def to_dict(self) -> dict:
        return {
            "request": self.request, "interpretation": self.interpretation,
            "files": self.files, "symbols": self.symbols, "contracts": self.contracts,
            "risk": self.risk, "total_affected": self.total_affected,
            "patch_operations": self.patch_operations, "tests": self.tests,
            "documentation": self.documentation, "validation_status": self.validation_status,
            "validation_issues": self.validation_issues,
            "unexpected_changes_note": self.unexpected_changes_note,
        }

    def render_text(self) -> str:
        lines = [
            "CHANGE SUMMARY", "",
            f"Request: {self.request}",
            f"Interpretation: {self.interpretation.get('intent')} "
            f"(dominio: {self.interpretation.get('domain')}, "
            f"confianza: {self.interpretation.get('confidence')})",
            f"Files: {', '.join(self.files) or '(ninguno)'}",
            f"Symbols: {', '.join(self.symbols) or '(ninguno)'}",
            f"Contracts: {', '.join(self.contracts) or '(ninguno)'}",
            f"Impact: {self.total_affected} nodos afectados",
            f"Risk: {self.risk}",
            f"Patch: {self.patch_operations} operacion(es) propuesta(s)",
            f"Tests: {self.tests.get('required_count', 0)} requeridos, "
            f"{self.tests.get('recommended_count', 0)} recomendados "
            f"(tests_run={self.tests.get('tests_run')})",
            f"Documentation: {', '.join(self.documentation) or '(ninguna)'}",
            f"Validation: {self.validation_status}"
            + (f" -- {'; '.join(self.validation_issues)}" if self.validation_issues else ""),
            f"Unexpected changes: {self.unexpected_changes_note}",
        ]
        return "\n".join(lines)


@dataclass
class ApprovalRecord:
    decision: str
    reviewer_note: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if self.decision not in _VALID_DECISIONS:
            raise ValueError(f"decision invalida: '{self.decision}' -- validas: {_VALID_DECISIONS}")

    def to_dict(self) -> dict:
        return {"decision": self.decision, "reviewer_note": self.reviewer_note, "timestamp": self.timestamp}
