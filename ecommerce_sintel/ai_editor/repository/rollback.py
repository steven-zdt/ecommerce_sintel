"""
`rollback_promotion()` -- POST-GRAPH 16 "Rollback" (rediseno "AI Editor
Runtime", 2026-08-11).

Todo `PromoteResult` exitoso (POST-GRAPH 12) ya captura `files_before`:
el contenido COMPLETO de cada archivo real, tomado inmediatamente ANTES
de sobrescribirlo. Es la unica base que necesita `rollback_promotion()`
para revertir -- no depende de git (que podria no estar disponible, o
tener el archivo en un estado intermedio, en el momento del rollback),
solo del contenido que este mismo proceso ya vio y guardo en memoria.

**Alcance real**: revierte el CODIGO (los archivos reales al estado
previo a la promocion). Reconstruir el grafo despues de un rollback (la
otra mitad que pide el prompt maestro, "permitir reconstruir graph") es
tan simple como correr `python -m project_knowledge_graph.cli audit` de
nuevo -- no se agrega una funcion nueva para eso, ya existe y ya esta
probada (Fase 21 del Site Knowledge Graph), llamarla desde aca seria
duplicar una linea de CLI sin agregar valor real.
"""
from dataclasses import dataclass, field
from pathlib import Path

from ai_editor.workspace import resolve_repo_file

STATUS_ROLLED_BACK = "ROLLED_BACK"
STATUS_NOTHING_TO_ROLLBACK = "NOTHING_TO_ROLLBACK"


@dataclass
class RollbackResult:
    status: str
    files_restored: list[str] = field(default_factory=list)
    detail: str = ""

    def to_dict(self) -> dict:
        return {"status": self.status, "files_restored": self.files_restored, "detail": self.detail}


def rollback_promotion(workspace_root: Path, promote_result) -> RollbackResult:
    """`promote_result` es el `PromoteResult` REAL devuelto por la
    `promote_to_workspace()` que se quiere revertir -- no un dict
    reconstruido de otra fuente (necesita `files_before` con el contenido
    completo, que solo existe en el objeto real en memoria de esa misma
    corrida)."""
    if getattr(promote_result, "status", None) != "PROMOTED" or not promote_result.files_before:
        return RollbackResult(
            status=STATUS_NOTHING_TO_ROLLBACK,
            detail="El PromoteResult no promovio nada (o no tiene contenido previo capturado) -- nada que revertir.",
        )

    workspace_root = Path(workspace_root)
    restored: list[str] = []
    for rel, original_content in promote_result.files_before.items():
        real_path = resolve_repo_file(rel, base_root=workspace_root)
        if real_path is None:
            continue
        real_path.write_text(original_content, encoding="utf-8")
        restored.append(rel)

    return RollbackResult(
        status=STATUS_ROLLED_BACK, files_restored=restored,
        detail=f"{len(restored)} archivo(s) restaurado(s) a su contenido previo en {workspace_root}.",
    )
