"""
`PatchOperation`/`Patch`/`ApplyResult` -- POST-GRAPH 6 "Patch Engine"
(rediseno "AI Editor Runtime", 2026-08-11).
"""
from dataclasses import dataclass, field

OPERATION_MODIFY = "MODIFY"
OPERATION_ADD = "ADD"
OPERATION_DELETE = "DELETE"
OPERATION_REPLACE = "REPLACE"
_VALID_OPERATIONS = {OPERATION_MODIFY, OPERATION_ADD, OPERATION_DELETE, OPERATION_REPLACE}

STATUS_APPLIED = "APPLIED"
STATUS_FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
STATUS_FILE_NOT_FOUND = "FILE_NOT_FOUND"
STATUS_REJECTED_OUTSIDE_SANDBOX = "REJECTED_OUTSIDE_SANDBOX"
STATUS_ERROR = "ERROR"

# POST-GRAPH 18 (Hardening): sin limite, un `new_content` desproporcionado
# (por error o por una entrada maliciosa) podria escribirse sin aviso --
# defensa en profundidad, 5 MB es generoso para codigo fuente real (el
# archivo mas grande de este repo hoy son ~35 KB).
MAX_PATCH_CONTENT_BYTES = 5 * 1024 * 1024


@dataclass
class PatchOperation:
    file: str
    operation: str
    line_start: int | None
    line_end: int | None
    old_fingerprint: str | None
    new_content: str | None
    reason: str

    def __post_init__(self) -> None:
        if self.operation not in _VALID_OPERATIONS:
            raise ValueError(f"operation invalida: '{self.operation}' -- validas: {_VALID_OPERATIONS}")
        if self.new_content is not None and len(self.new_content.encode("utf-8")) > MAX_PATCH_CONTENT_BYTES:
            raise ValueError(
                f"new_content excede el limite de {MAX_PATCH_CONTENT_BYTES} bytes -- "
                "revisar si es intencional antes de forzarlo."
            )

    def to_dict(self) -> dict:
        return {
            "file": self.file, "operation": self.operation,
            "line_start": self.line_start, "line_end": self.line_end,
            "old_fingerprint": self.old_fingerprint, "new_content": self.new_content,
            "reason": self.reason,
        }


@dataclass
class Patch:
    id: str
    operations: list[PatchOperation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"id": self.id, "operations": [op.to_dict() for op in self.operations]}


@dataclass
class ApplyResult:
    operation: PatchOperation
    status: str
    detail: str

    def to_dict(self) -> dict:
        return {"operation": self.operation.to_dict(), "status": self.status, "detail": self.detail}
