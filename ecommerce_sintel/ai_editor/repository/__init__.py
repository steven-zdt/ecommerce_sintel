"""
ai_editor.repository -- POST-GRAPH 7 "Repository Sandbox" + POST-GRAPH 12
"Commit Control" + POST-GRAPH 16 "Rollback" (rediseno "AI Editor Runtime",
2026-08-11).

`create_sandbox(plan)` aisla la ESCRITURA de un cambio: copia solo los
archivos reales que un `ChangePlan` toca a un directorio temporal, que es
el UNICO `sandbox_root` legitimo para `ai_editor.patch.apply_operation()`.
El checkout real (`ai_editor.workspace.WORKSPACE_ROOT`) nunca se toca
durante esa etapa. La parte de LECTURA (resolver `file`/`Symbol.file` a
un path real) ya la cubre `ai_editor.workspace`/`graph_client` desde
POST-GRAPH 1/5.

`promote_to_workspace()`/`commit_changes()` (POST-GRAPH 12) SI escriben
sobre un checkout real -- ver `promote.py` para los guardrails completos
(aprobacion + confirmacion explicita + re-verificacion de fingerprint,
todo-o-nada). Esta sesion nunca los invoca contra `WORKSPACE_ROOT` real,
solo contra directorios de prueba.

`rollback_promotion()` (POST-GRAPH 16) revierte un `PromoteResult`
exitoso al contenido real que cada archivo tenia justo antes de
promoverse (`PromoteResult.files_before`, capturado por
`promote_to_workspace()` mismo -- no depende de git).
"""
from ai_editor.repository.promote import (
    STATUS_NOT_APPROVED,
    STATUS_NOT_CONFIRMED,
    STATUS_PROMOTED,
    STATUS_VALIDATION_FAILED,
    STATUS_WORKSPACE_DRIFT,
    PromoteResult,
    commit_changes,
    promote_to_workspace,
)
from ai_editor.repository.rollback import (
    STATUS_NOTHING_TO_ROLLBACK,
    STATUS_ROLLED_BACK,
    RollbackResult,
    rollback_promotion,
)
from ai_editor.repository.sandbox import Sandbox, create_sandbox

__all__ = [
    "create_sandbox",
    "Sandbox",
    "promote_to_workspace",
    "commit_changes",
    "PromoteResult",
    "STATUS_PROMOTED",
    "STATUS_NOT_APPROVED",
    "STATUS_NOT_CONFIRMED",
    "STATUS_WORKSPACE_DRIFT",
    "STATUS_VALIDATION_FAILED",
    "rollback_promotion",
    "RollbackResult",
    "STATUS_ROLLED_BACK",
    "STATUS_NOTHING_TO_ROLLBACK",
]
