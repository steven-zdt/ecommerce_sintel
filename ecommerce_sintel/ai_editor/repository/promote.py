"""
`promote_to_workspace()`/`commit_changes()` -- POST-GRAPH 12 "Commit
Control" (rediseno "AI Editor Runtime", 2026-08-11).

Primera funcion de TODO `ai_editor` cuyo proposito explicito es escribir
sobre un checkout REAL (no un sandbox descartable) -- por eso lleva MAS
guardrails que cualquier pieza anterior, no menos:

1. Requiere un `ApprovalRecord` REAL con `decision == APPROVE`
   (POST-GRAPH 11) -- no un booleano suelto que se pueda pasar sin haber
   pasado por el flujo de aprobacion real.
2. Requiere ADEMAS `confirm=True` explicito -- separa deliberadamente "el
   CONTENIDO del cambio fue aprobado" (una decision sobre QUE cambiar) de
   "confirmo EJECUTAR la escritura ahora mismo" (una decision sobre
   CUANDO actuar). Un `ApprovalRecord` aprobado hace tiempo no autoriza
   por si solo una promocion automatica sin que alguien la dispare
   deliberadamente en el momento.
3. `workspace_root` es un argumento EXPLICITO obligatorio, sin default a
   `ai_editor.workspace.WORKSPACE_ROOT` -- mismo criterio que
   `ai_editor.patch.apply_operation(sandbox_root, ...)`: el llamador
   decide contra que directorio escribir, nunca un default implicito.
4. Re-verifica el fingerprint de CADA archivo contra el estado REAL
   actual de `workspace_root` (no el que tenia cuando se creo el sandbox)
   ANTES de escribir cualquiera -- todo-o-nada: si un solo archivo
   cambio desde que se genero el sandbox (edicion concurrente mientras se
   revisaba), se aborta la promocion COMPLETA sin escribir nada.
5. **[AGREGADO EN POST-GRAPH 20]** Si se pasa `validation_report`, y
   `level_1_passed` es `False`, la promocion se rechaza ESTRUCTURALMENTE
   -- sin importar que el `ApprovalRecord` diga `APPROVE`. Gap real
   encontrado auditando el invariante explicito del prompt maestro
   ("Patch NO se promociona si la validacion falla"): la version
   original de esta funcion solo dependia de que un humano no aprobara
   un cambio con sintaxis rota, sin ningun guardrail de codigo que lo
   impidiera si el humano se equivocaba o aprobaba sin revisar el
   `ValidationReport`. `validation_report` es OPCIONAL (retrocompatible
   con cualquier caller que ya lo estuviera usando sin ese parametro),
   pero si se pasa y fallo, bloquea sin excepcion.
6. `commit_changes()` como maximo hace `git add` + `git commit` LOCAL --
   nunca `git push`, nunca deploy, nunca reinicia servicios (regla
   explicita del prompt maestro, seccion POST-GRAPH 12).

**Esta sesion NO invoca `promote_to_workspace()` contra
`ai_editor.workspace.WORKSPACE_ROOT` real** -- verificado unicamente
contra directorios/repos git temporales (`tmp_path`). Promover un cambio
real al checkout de este proyecto requiere una instruccion explicita
separada del usuario en el momento, no una consecuencia automatica de
haber implementado esta fase del prompt maestro.
"""
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ai_editor.approval.schema import DECISION_APPROVE
from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.workspace import resolve_repo_file

STATUS_PROMOTED = "PROMOTED"
STATUS_NOT_APPROVED = "NOT_APPROVED"
STATUS_NOT_CONFIRMED = "NOT_CONFIRMED"
STATUS_WORKSPACE_DRIFT = "WORKSPACE_DRIFT"
STATUS_VALIDATION_FAILED = "VALIDATION_FAILED"


@dataclass
class PromoteResult:
    status: str
    files_promoted: list[str] = field(default_factory=list)
    detail: str = ""
    # Contenido COMPLETO de cada archivo, capturado inmediatamente ANTES
    # de sobrescribirlo -- unica base real para POST-GRAPH 16 (Rollback):
    # sin esto, revertir requeriria adivinar el contenido anterior o
    # depender de git (que no siempre esta disponible/limpio en el
    # momento del rollback).
    files_before: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status, "files_promoted": self.files_promoted,
            "detail": self.detail, "files_before_count": len(self.files_before),
        }


def promote_to_workspace(sandbox, approval, workspace_root: Path, confirm: bool = False,
                          validation_report=None) -> PromoteResult:
    if approval is None or getattr(approval, "decision", None) != DECISION_APPROVE:
        return PromoteResult(
            status=STATUS_NOT_APPROVED,
            detail="No hay un ApprovalRecord con decision=APPROVE -- nada se promueve.",
        )

    if not confirm:
        return PromoteResult(
            status=STATUS_NOT_CONFIRMED,
            detail="confirm=True es obligatorio ademas de la aprobacion -- ejecutar la escritura "
                   "real requiere una intencion explicita separada, no solo un plan aprobado.",
        )

    if validation_report is not None:
        vr = validation_report.to_dict() if hasattr(validation_report, "to_dict") else dict(validation_report)
        if not vr.get("level_1_passed", True):
            return PromoteResult(
                status=STATUS_VALIDATION_FAILED,
                detail="La validacion de sintaxis (Nivel 1) fallo -- rechazado estructuralmente, "
                       "sin importar la decision de aprobacion. Corregir la sintaxis y volver a "
                       "validar antes de reintentar.",
            )

    workspace_root = Path(workspace_root)

    # Todo-o-nada: primero verificar TODOS los fingerprints reales,
    # recien despues escribir cualquiera.
    drifted: list[str] = []
    real_paths: dict[str, Path] = {}
    for rel in sandbox.copied_files:
        real_path = resolve_repo_file(rel, base_root=workspace_root)
        if real_path is None:
            drifted.append(f"'{rel}': ya no existe en el workspace destino")
            continue
        current_fp = compute_fingerprint(real_path.read_text(encoding="utf-8", errors="replace"))
        expected_fp = sandbox.original_fingerprints.get(rel)
        if current_fp != expected_fp:
            drifted.append(f"'{rel}': cambio en el workspace destino desde que se creo el sandbox")
            continue
        real_paths[rel] = real_path

    if drifted:
        return PromoteResult(
            status=STATUS_WORKSPACE_DRIFT,
            detail="STOP -- no se promovio nada (todo-o-nada): " + "; ".join(drifted),
        )

    promoted: list[str] = []
    files_before: dict[str, str] = {}
    for rel, real_path in real_paths.items():
        # Capturar el contenido ANTERIOR completo ANTES de sobrescribir --
        # base real de POST-GRAPH 16 (Rollback).
        files_before[rel] = real_path.read_text(encoding="utf-8", errors="replace")
        sandbox_path = Path(sandbox.root) / rel
        real_path.write_text(sandbox_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        promoted.append(rel)

    return PromoteResult(
        status=STATUS_PROMOTED, files_promoted=promoted,
        detail=f"{len(promoted)} archivo(s) promovido(s) a {workspace_root}.",
        files_before=files_before,
    )


def commit_changes(workspace_root: Path, files: list[str], message: str) -> tuple[bool, str]:
    """`git add` + `git commit` LOCAL sobre `workspace_root` -- NUNCA
    `git push`, nunca toca un remoto. `workspace_root` es explicito, sin
    default -- el llamador decide contra que repo git correr esto."""
    try:
        subprocess.run(
            ["git", "add", *files], cwd=str(workspace_root),
            check=True, capture_output=True, text=True, timeout=30,
        )
        result = subprocess.run(
            ["git", "commit", "-m", message], cwd=str(workspace_root),
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError) as exc:
        return False, f"error ejecutando git: {exc}"

    if result.returncode != 0:
        return False, (result.stdout.strip() + " " + result.stderr.strip()).strip()
    return True, result.stdout.strip()
