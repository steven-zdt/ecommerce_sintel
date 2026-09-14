"""
`apply_operation()` -- POST-GRAPH 6 "Patch Engine" (rediseno "AI Editor
Runtime", 2026-08-11).

**Alcance explicito de esta fase**: implementa el MECANISMO de aplicar un
cambio de forma segura (verificacion de fingerprint antes de escribir,
rechazo si el contenido real cambio, rechazo estructural si el destino no
es un sandbox) -- NO genera el `new_content` de un cambio real
automaticamente. Generar codigo real (un diff real sobre
`renting/api/views.py` que implemente "alquiler por horas", por ejemplo)
requeriria una capa de generacion (un LLM escribiendo codigo real sobre un
codebase Django/Vue real) que NINGUNA fase de este prompt maestro
construye explicitamente todavia -- es un salto de riesgo/alcance mucho
mayor que "aplicar un patch ya decidido", y no se fabrica aca sin que el
plan lo pida explicito. Probado con contenido SINTETICO (fixtures de
test), nunca contra codigo real de la aplicacion.

**Guardrail estructural** (no solo una convencion de uso): `sandbox_root`
es un argumento OBLIGATORIO, nunca defaultea a
`ai_editor.workspace.WORKSPACE_ROOT` (el checkout real) -- si alguien
llama esto con `sandbox_root == WORKSPACE_ROOT`, se rechaza con
`REJECTED_OUTSIDE_SANDBOX` salvo `allow_live_workspace=True` explicito.
Esto hace que un bug futuro (ej. un caller que olvida crear el sandbox de
POST-GRAPH 7 y pasa el workspace real por error) falle CERRADO, no
escriba en silencio sobre el repo real.
"""
from pathlib import Path

from ai_editor.patch.fingerprint import read_lines_fingerprint
from ai_editor.patch.schema import (
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
    PatchOperation,
)
from ai_editor.workspace import WORKSPACE_ROOT


def build_operation_fingerprint(sandbox_root: Path, operation: PatchOperation) -> str | None:
    """Fingerprint REAL actual del rango de lineas que `operation` dice
    modificar -- solo lectura, para comparar contra
    `operation.old_fingerprint` antes de decidir si aplicar."""
    if operation.line_start is None:
        return None
    real_path = (Path(sandbox_root) / operation.file).resolve()
    return read_lines_fingerprint(real_path, operation.line_start, operation.line_end)


def apply_operation(sandbox_root: Path, operation: PatchOperation,
                     allow_live_workspace: bool = False) -> ApplyResult:
    sandbox_root = Path(sandbox_root).resolve()

    if sandbox_root == WORKSPACE_ROOT and not allow_live_workspace:
        return ApplyResult(
            operation=operation, status=STATUS_REJECTED_OUTSIDE_SANDBOX,
            detail=(
                "sandbox_root apunta al checkout REAL (WORKSPACE_ROOT) -- rechazado por diseno. "
                "El Patch Engine solo debe escribir sobre un sandbox aislado (POST-GRAPH 7), "
                "nunca directo sobre el repo real."
            ),
        )

    real_path = (sandbox_root / operation.file).resolve()
    try:
        real_path.relative_to(sandbox_root)
    except ValueError:
        return ApplyResult(
            operation=operation, status=STATUS_REJECTED_OUTSIDE_SANDBOX,
            detail=f"'{operation.file}' resuelve fuera de sandbox_root ({sandbox_root})",
        )

    if operation.operation in (OPERATION_MODIFY, OPERATION_DELETE, OPERATION_REPLACE):
        if not real_path.exists():
            return ApplyResult(operation=operation, status=STATUS_FILE_NOT_FOUND,
                                detail=f"'{operation.file}' no existe en el sandbox")
        current_fingerprint = read_lines_fingerprint(real_path, operation.line_start, operation.line_end)
        if current_fingerprint != operation.old_fingerprint:
            return ApplyResult(
                operation=operation, status=STATUS_FINGERPRINT_MISMATCH,
                detail=(
                    f"El contenido real de '{operation.file}' lineas {operation.line_start}-"
                    f"{operation.line_end} no coincide con el fingerprint esperado -- el archivo "
                    "cambio desde que se genero el plan. STOP, no se aplica; re-resolver el "
                    "cambio contra el estado actual."
                ),
            )

    lines = (
        real_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        if real_path.exists() else []
    )

    if operation.operation == OPERATION_DELETE:
        new_lines = lines[:operation.line_start - 1] + lines[operation.line_end:]
    elif operation.operation in (OPERATION_MODIFY, OPERATION_REPLACE):
        replacement = operation.new_content or ""
        if not replacement.endswith("\n"):
            replacement += "\n"
        new_lines = lines[:operation.line_start - 1] + [replacement] + lines[operation.line_end:]
    elif operation.operation == OPERATION_ADD:
        insert_at = (operation.line_start - 1) if operation.line_start else len(lines)
        addition = operation.new_content or ""
        if not addition.endswith("\n"):
            addition += "\n"
        new_lines = lines[:insert_at] + [addition] + lines[insert_at:]
    else:
        return ApplyResult(operation=operation, status=STATUS_ERROR,
                            detail=f"operacion desconocida: {operation.operation}")

    real_path.parent.mkdir(parents=True, exist_ok=True)
    real_path.write_text("".join(new_lines), encoding="utf-8")

    return ApplyResult(operation=operation, status=STATUS_APPLIED, detail=f"Aplicado sobre {real_path}")
