"""
`ChangeContext` -- POST-GRAPH 3 "Change Resolver" (rediseno "AI Editor
Runtime", 2026-08-11).
"""
from dataclasses import dataclass, field

STATUS_RESOLVED = "RESOLVED"
STATUS_PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
STATUS_UNRESOLVED = "UNRESOLVED"


@dataclass
class ChangeContext:
    intent: dict
    status: str
    primary_target: dict | None = None
    resolved_entities: list[dict] = field(default_factory=list)
    unresolved_entities: list[str] = field(default_factory=list)
    resolution: dict | None = None
    context_packet: dict | None = None

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "status": self.status,
            "primary_target": self.primary_target,
            "resolved_entities": self.resolved_entities,
            "unresolved_entities": self.unresolved_entities,
            "resolution": self.resolution,
            "context_packet": self.context_packet,
        }
