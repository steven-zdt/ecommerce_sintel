"""
`create_sandbox()` -- POST-GRAPH 7 "Repository Sandbox" (rediseno "AI
Editor Runtime", 2026-08-11).

"Nunca aplicar inicialmente los cambios directamente sobre el entorno
operativo" (prompt maestro) -- `create_sandbox(plan)` copia SOLO los
archivos reales que un `ChangePlan` (POST-GRAPH 4) toca (no el repo
completo, seria lento y la enorme mayoria irrelevante para ese cambio
puntual) a un directorio temporal aislado. El resultado (`Sandbox.root`)
es el UNICO `sandbox_root` legitimo para pasarle a
`ai_editor.patch.apply_operation()` -- `WORKSPACE_ROOT` (el checkout
real) permanece intacto durante todo el ciclo PATCH -> TEST ->
RECONCILIATION -> APPROVAL.

**Alcance explicito**: este sandbox aisla la ESCRITURA (garantiza que un
patch nunca toca el checkout real hasta que se apruebe explicitamente).
NO reproduce un entorno de ejecucion completo (Docker/Postgres/Redis/venv)
-- correr la suite de tests real de Django dentro de este sandbox
requeriria replicar esa infraestructura, que es un problema operativo
mucho mayor (mismo gap ya documentado en otras partes del proyecto:
pytest-django no disponible en el host, tests reales requieren Docker).
Esa decision queda para cuando se construya la ejecucion de tests
(POST-GRAPH 10), no se resuelve ni se finge resuelta aca.
"""
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.workspace import resolve_repo_file

# Nunca se copian al sandbox, incluso si aparecieran (por error o por un
# grafo desactualizado) en los archivos de un ChangePlan -- cumple la
# restriccion EXPLICITA de POST-GRAPH 18 ("Restricciones de seguridad":
# .env, secrets, credentials, certificados, deployment files, backups,
# DB dumps, claves privadas). Lista extendida en POST-GRAPH 18 (auditoria
# real): version original (POST-GRAPH 7) solo cubria env/secret/
# credential/claves privadas -- faltaban certificados, backups y dumps de
# base de datos, mencionados EXPLICITAMENTE en el prompt maestro.
_SENSITIVE_PATTERNS = (
    ".env", "secret", "credential", ".pem", ".key", "id_rsa", ".p12", ".pfx",
    ".crt", ".cer", "backup", ".dump", ".sql.gz", "id_ed25519", "id_ecdsa",
)

# POST-GRAPH 18 (Hardening): un ChangePlan con una cantidad de steps
# desproporcionada (ej. un `calculate_change_impact` con miles de nodos
# afectados, o un plan malformado) no deberia poder inflar el sandbox sin
# limite -- defensa en profundidad, no una situacion vista en el uso real
# hasta ahora (el caso Renting real usa 8 archivos).
MAX_SANDBOX_FILES = 500


def _is_sensitive(relative_path: str) -> bool:
    lowered = relative_path.lower()
    return any(pattern in lowered for pattern in _SENSITIVE_PATTERNS)


@dataclass
class Sandbox:
    root: Path
    copied_files: list[str] = field(default_factory=list)
    skipped_sensitive: list[str] = field(default_factory=list)
    # Fingerprint (sha256) del CONTENIDO COMPLETO de cada archivo en el
    # momento exacto de la copia -- usado por POST-GRAPH 12 (Commit
    # Control) para detectar si el archivo REAL cambio (edicion
    # concurrente) mientras el sandbox estaba siendo revisado/aprobado,
    # antes de promover cualquier cosa de vuelta al workspace real.
    original_fingerprints: dict[str, str] = field(default_factory=dict)
    files_over_limit: list[str] = field(default_factory=list)

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> "Sandbox":
        return self

    def __exit__(self, *exc_info) -> None:
        self.cleanup()


def create_sandbox(plan) -> Sandbox:
    """`plan` es un `ai_editor.planner.ChangePlan` (o su `.to_dict()`).
    Copia cada archivo real referenciado por los steps del plan (backend
    o frontend, resuelto via `ai_editor.workspace.resolve_repo_file`) a un
    directorio temporal nuevo. Archivos que matchean un patron sensible se
    SALTEAN (nunca se copian), registrados en `skipped_sensitive` -- no
    lanzan, para que un plan con un solo step problematico no tumbe todo
    el sandbox de los demas steps legitimos; el llamador decide si un
    `skipped_sensitive` no vacio debe bloquear el flujo."""
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    sandbox_dir = Path(tempfile.mkdtemp(prefix="ai_editor_sandbox_"))

    copied: list[str] = []
    skipped: list[str] = []
    over_limit: list[str] = []
    fingerprints: dict[str, str] = {}
    for step in plan_dict.get("steps", []):
        rel = step.get("file")
        if not rel or rel in copied or rel in skipped or rel in over_limit:
            continue
        if _is_sensitive(rel):
            skipped.append(rel)
            continue
        if len(copied) >= MAX_SANDBOX_FILES:
            over_limit.append(rel)
            continue
        real_path = resolve_repo_file(rel)
        if real_path is None:
            continue  # POST-GRAPH 5 (validate_plan) ya deberia haber bloqueado esto antes
        dest = sandbox_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(real_path, dest)
        copied.append(rel)
        fingerprints[rel] = compute_fingerprint(real_path.read_text(encoding="utf-8", errors="replace"))

    return Sandbox(root=sandbox_dir, copied_files=copied, skipped_sensitive=skipped,
                    original_fingerprints=fingerprints, files_over_limit=over_limit)
