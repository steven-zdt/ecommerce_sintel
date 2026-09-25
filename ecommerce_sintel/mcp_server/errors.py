"""
mcp_server/errors.py -- errores de herramienta con codigo estable. Nunca llevan trazas ni valores sensibles.
"""
import json


class McpToolError(Exception):
    """Error controlado de una Tool: `code` estable (para el cliente/LLM), `message` corto y `details` opcionales (ya saneados)."""

    def __init__(self, code: str, message: str, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def as_text(self) -> str:
        return json.dumps({"ok": False, "error": {"code": self.code, "message": self.message, **self.details}}, ensure_ascii=False, default=str)


# Codigos usados en todo el servidor (documentados en .AGENT/TOOL_REGISTRY.md)
UNAUTHENTICATED = "UNAUTHENTICATED"
FORBIDDEN_TOOL = "FORBIDDEN_TOOL"
RESOURCE_NOT_ALLOWED = "RESOURCE_NOT_ALLOWED"
OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
INVALID_ARGUMENT = "INVALID_ARGUMENT"
RATE_LIMITED = "RATE_LIMITED"
LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"
CONFIRMATION_INVALID = "CONFIRMATION_INVALID"
VERSION_CONFLICT = "VERSION_CONFLICT"
IDEMPOTENCY_KEY_REQUIRED = "IDEMPOTENCY_KEY_REQUIRED"
IDEMPOTENCY_KEY_REUSED = "IDEMPOTENCY_KEY_REUSED"
UPSTREAM_ERROR = "UPSTREAM_ERROR"
UPSTREAM_DENIED = "UPSTREAM_DENIED"
NOT_FOUND = "NOT_FOUND"
CODE_PLANE_DISABLED = "CODE_PLANE_DISABLED"
PATH_NOT_ALLOWED = "PATH_NOT_ALLOWED"
