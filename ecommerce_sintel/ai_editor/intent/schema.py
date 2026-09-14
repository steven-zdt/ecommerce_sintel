"""
`ChangeIntent` -- POST-GRAPH 2 "Change Intent" (rediseno "AI Editor
Runtime", 2026-08-11). Representacion estructurada de una solicitud
humana, tal como la pide la seccion 2 del prompt maestro: id/request/
domain/intent/entities/scope/confidence/ambiguities.
"""
from dataclasses import dataclass, field

STATUS_RESOLVED = "RESOLVED"
STATUS_NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


@dataclass
class ChangeIntent:
    id: str
    request: str
    domain: str | None
    intent: str | None
    entities: list[str] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)
    confidence: float = 0.0
    ambiguities: list[str] = field(default_factory=list)
    status: str = STATUS_NEEDS_CLARIFICATION

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request": self.request,
            "domain": self.domain,
            "intent": self.intent,
            "entities": self.entities,
            "scope": self.scope,
            "confidence": self.confidence,
            "ambiguities": self.ambiguities,
            "status": self.status,
        }
