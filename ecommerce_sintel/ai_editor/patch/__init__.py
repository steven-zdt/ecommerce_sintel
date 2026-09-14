"""
ai_editor.patch -- POST-GRAPH 6 "Patch Engine" (rediseno "AI Editor
Runtime", 2026-08-11). IMPLEMENTADO PARCIALMENTE (deja de ser scaffold
puro, pero con alcance deliberadamente acotado -- ver `engine.py` para el
detalle completo).

Implementa el MECANISMO de aplicar un cambio de forma segura (fingerprint
de contenido antes de escribir, rechazo estructural si el destino no es
un sandbox explicito) -- NO genera codigo real automaticamente (eso
requeriria una capa de generacion de codigo, LLM escribiendo diffs reales,
que ninguna fase de este rediseno construye todavia). `apply_operation()`
NUNCA escribe sobre el checkout real (`ai_editor.workspace.WORKSPACE_ROOT`)
salvo `allow_live_workspace=True` explicito -- por diseno, no por
convencion de uso.
"""
from ai_editor.patch.engine import apply_operation, build_operation_fingerprint
from ai_editor.patch.fingerprint import compute_fingerprint, read_lines_fingerprint
from ai_editor.patch.schema import (
    MAX_PATCH_CONTENT_BYTES,
    OPERATION_ADD,
    OPERATION_DELETE,
    OPERATION_MODIFY,
    OPERATION_REPLACE,
    STATUS_APPLIED,
    STATUS_ERROR,
    STATUS_FILE_NOT_FOUND,
    STATUS_FINGERPRINT_MISMATCH,
    STATUS_REJECTED_OUTSIDE_SANDBOX,
    ApplyResult,
    Patch,
    PatchOperation,
)

__all__ = [
    "apply_operation",
    "build_operation_fingerprint",
    "compute_fingerprint",
    "read_lines_fingerprint",
    "PatchOperation",
    "Patch",
    "ApplyResult",
    "OPERATION_MODIFY",
    "OPERATION_ADD",
    "OPERATION_DELETE",
    "OPERATION_REPLACE",
    "STATUS_APPLIED",
    "STATUS_FINGERPRINT_MISMATCH",
    "STATUS_FILE_NOT_FOUND",
    "STATUS_REJECTED_OUTSIDE_SANDBOX",
    "STATUS_ERROR",
    "MAX_PATCH_CONTENT_BYTES",
]
