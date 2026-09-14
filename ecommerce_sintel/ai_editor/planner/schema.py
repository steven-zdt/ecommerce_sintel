"""
`ChangePlan`/`PlanStep` -- POST-GRAPH 4 "Change Plan" (rediseno "AI
Editor Runtime", 2026-08-11).
"""
from dataclasses import dataclass, field

STATUS_PLANNED = "PLANNED"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class PlanStep:
    step: int
    file: str | None
    symbol: str | None
    line_start: int | None
    line_end: int | None
    operation: str
    reason: str
    dependencies: list[int]
    risk: str
    validation: str

    def to_dict(self) -> dict:
        return {
            "step": self.step, "file": self.file, "symbol": self.symbol,
            "line_start": self.line_start, "line_end": self.line_end,
            "operation": self.operation, "reason": self.reason,
            "dependencies": self.dependencies, "risk": self.risk,
            "validation": self.validation,
        }


@dataclass
class ChangePlan:
    context: dict
    steps: list[PlanStep] = field(default_factory=list)
    status: str = STATUS_BLOCKED
    blocked_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "context": self.context,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status,
            "blocked_reason": self.blocked_reason,
        }
