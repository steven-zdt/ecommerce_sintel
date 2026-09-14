"""
`run_code_quality_checks()` -- FASE 36 "Code Quality Validation" (plan
"AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro, aplicada literal: "No ejecutar herramientas
que no existan realmente en el proyecto. Primero detectar cuales estan
configuradas."

**Auditoria real del repo (2026-08-11, verificada antes de escribir una
sola linea de codigo)**: `pyproject.toml` solo declara `[tool.bandit]`
real -- sin `[tool.black]`/`[tool.ruff]`/`[tool.mypy]`, sin `.flake8`,
sin `.eslintrc*`/`prettier.config.*`/`tsconfig.json` en `frontend/`. De
lo declarado, `bandit` (1.9.4) SI esta instalado y resoluble en PATH del
mismo entorno Python que corre `ai_editor` -- verificado con `bandit
--version` antes de asumir que la llamada real funciona (no solo
`grep`-eando el archivo de config). Ninguna herramienta JS/Vue esta ni
declarada ni instalada -- se reporta `NOT_CONFIGURED` explicito para esos
archivos, nunca se inventa un resultado ni se asume eslint "por
convencion".

`bandit` es un linter de SEGURIDAD (no de estilo/formato) -- coherente
con el resto de la disciplina de `ai_editor`: codigo generado por un LLM
merece el MISMO escaneo de seguridad que el CI real le exige a codigo
escrito por un humano. Se reusa la MISMA config real
(`.github/workflows/ci.yml`: `bandit -c pyproject.toml -r . -ll`) --
mismo archivo de config (`pyproject.toml` real del `WORKSPACE_ROOT`,
nunca una copia), misma severidad (`-ll` = MEDIUM+), pero apuntando al
archivo dentro del SANDBOX (nunca al repo real), consistente con el
resto de `generation/`.
"""
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ai_editor.workspace import WORKSPACE_ROOT

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_CONFIGURED = "NOT_CONFIGURED"
STATUS_TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"

_BANDIT_CONFIG = WORKSPACE_ROOT / "pyproject.toml"


@dataclass
class ToolCheckResult:
    tool: str
    file: str
    status: str
    detail: str

    def to_dict(self) -> dict:
        return {"tool": self.tool, "file": self.file, "status": self.status, "detail": self.detail}


@dataclass
class CodeQualityReport:
    proposal_id: str
    overall_status: str
    checks: list[ToolCheckResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id, "overall_status": self.overall_status,
            "checks": [c.to_dict() for c in self.checks],
        }


def _run_bandit(rel_path: str, real_path: Path) -> ToolCheckResult:
    if not _BANDIT_CONFIG.exists():
        return ToolCheckResult(
            "bandit", rel_path, STATUS_NOT_CONFIGURED,
            f"'{_BANDIT_CONFIG}' no existe -- [tool.bandit] no se puede confirmar configurado.",
        )
    try:
        result = subprocess.run(
            ["bandit", "-c", str(_BANDIT_CONFIG), "-ll", str(real_path)],
            capture_output=True, text=True, timeout=30,
        )
    except FileNotFoundError:
        return ToolCheckResult(
            "bandit", rel_path, STATUS_TOOL_UNAVAILABLE,
            "bandit esta declarado en pyproject.toml pero el binario no esta instalado/en PATH "
            "de este entorno -- no se finge un resultado.",
        )
    except subprocess.TimeoutExpired:
        return ToolCheckResult("bandit", rel_path, STATUS_FAIL, "timeout ejecutando bandit (30s)")

    if result.returncode == 0:
        return ToolCheckResult("bandit", rel_path, STATUS_PASS, "sin hallazgos de severidad MEDIUM+ (bandit -ll)")
    return ToolCheckResult(
        "bandit", rel_path, STATUS_FAIL, (result.stdout.strip() or result.stderr.strip())[-800:],
    )


def run_code_quality_checks(sandbox, proposal) -> CodeQualityReport:
    """`sandbox` es un `Sandbox` (POST-GRAPH 7) YA parcheado (ej. el de
    un `SandboxLoopResult.sandbox` con `apply_result.applied=True`).
    Solo evalua los archivos que `proposal.operations` declara tocar --
    nunca escanea el sandbox completo (mismo criterio de contexto minimo
    de todo `generation/`)."""
    checks: list[ToolCheckResult] = []
    touched_files = sorted({op.file for op in proposal.operations})
    sandbox_root = Path(sandbox.root).resolve()

    for rel in touched_files:
        # FASE 49 "Security Hardening" -- gap real encontrado en la propia
        # auditoria: faltaba el mismo chequeo anti-traversal que
        # `patch.engine.apply_operation()` (POST-GRAPH 6) ya aplica antes
        # de tocar el sandbox. En la practica `rel` viene de un
        # `PatchOperation.file` que ya tuvo que matchear un `PlanStep.file`
        # real (derivado del grafo, nunca del LLM directo -- ver
        # `proposal_validator.find_matching_step()`), asi que no deberia
        # poder ser `../..` -- pero este check nunca debe depender
        # UNICAMENTE de esa garantia upstream, mismo criterio de defensa en
        # profundidad que el resto de `ai_editor`.
        real_path = (sandbox_root / rel).resolve()
        try:
            real_path.relative_to(sandbox_root)
        except ValueError:
            checks.append(ToolCheckResult(
                "bandit", rel, STATUS_FAIL, f"'{rel}' resuelve fuera del sandbox ({sandbox_root})",
            ))
            continue
        if not real_path.exists():
            continue  # ej. resultado de un DELETE -- nada que analizar
        suffix = real_path.suffix
        if suffix == ".py":
            checks.append(_run_bandit(rel, real_path))
        elif suffix in (".vue", ".js", ".ts"):
            checks.append(ToolCheckResult(
                "eslint", rel, STATUS_NOT_CONFIGURED,
                "ningun linter JS/Vue (eslint/prettier/tsc) esta declarado ni instalado en este "
                "proyecto -- verificado, no asumido.",
            ))

    # Bug real encontrado en la propia verificacion de esta fase: si TODOS
    # los checks eran NOT_CONFIGURED/TOOL_UNAVAILABLE (ej. un archivo .vue
    # sin eslint instalado), un `else` demasiado amplio reportaba
    # overall_status=PASS -- implicando falsamente "se reviso y esta bien"
    # cuando en realidad NINGUNA herramienta corrio de verdad. Corregido:
    # PASS exige al menos un check que realmente se haya ejecutado.
    if not checks:
        overall_status = STATUS_NOT_CONFIGURED
    elif any(c.status == STATUS_FAIL for c in checks):
        overall_status = STATUS_FAIL
    elif all(c.status in (STATUS_NOT_CONFIGURED, STATUS_TOOL_UNAVAILABLE) for c in checks):
        overall_status = STATUS_NOT_CONFIGURED
    else:
        overall_status = STATUS_PASS

    return CodeQualityReport(proposal_id=proposal.proposal_id, overall_status=overall_status, checks=checks)


__all__ = [
    "run_code_quality_checks", "CodeQualityReport", "ToolCheckResult",
    "STATUS_PASS", "STATUS_FAIL", "STATUS_NOT_CONFIGURED", "STATUS_TOOL_UNAVAILABLE",
]
