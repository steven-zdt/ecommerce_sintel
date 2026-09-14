"""
`run_validation()` -- POST-GRAPH 8 "Validation Engine" (rediseno "AI
Editor Runtime", 2026-08-11).

**Estado honesto de esta fase**: solo el NIVEL 1 (sintaxis) esta
implementado y es real. Los Niveles 2-5 del prompt maestro (tests reales,
contratos, comparacion de grafo antes/despues, impacto recalculado)
requieren correr Django/pytest y reconstruir `project_knowledge_graph`
DENTRO del sandbox -- pero el sandbox de POST-GRAPH 7 es una copia PARCIAL
(solo los archivos que el plan toca, no el proyecto completo): no tiene
`settings.py`, otras apps, migraciones, ni acceso a Postgres/Redis/Docker.
Correr tests reales o reconstruir el grafo ahi es estructuralmente
imposible con el diseno actual del sandbox -- haria falta un sandbox de
tipo distinto (copia completa del repo, o un git worktree real) mas
acceso a la infraestructura Docker, una decision de arquitectura mayor
que esta fase NO toma por su cuenta. Se documenta como `NOT_IMPLEMENTED`
explicito, nunca se finge un resultado.
"""
from dataclasses import dataclass, field

from ai_editor.validation.syntax import check_syntax

LEVELS_2_TO_5_REASON = (
    "El sandbox de POST-GRAPH 7 copia SOLO los archivos que el plan toca (no el proyecto "
    "completo) -- no tiene settings.py, otras apps Django, migraciones, ni acceso a "
    "Postgres/Redis/Docker. Correr tests reales (Nivel 2), validar contratos end-to-end "
    "(Nivel 3), reconstruir el grafo (Nivel 4) o recalcular impacto sobre codigo parcheado "
    "(Nivel 5) requeriria un sandbox de tipo distinto (copia completa del repo o git worktree "
    "real) mas acceso a la infraestructura Docker -- decision de arquitectura mayor, fuera de "
    "alcance de esta fase, no tomada por su cuenta ni fingida como resuelta."
)


@dataclass
class ValidationReport:
    level_1_syntax: dict = field(default_factory=dict)
    level_1_passed: bool = True
    levels_2_to_5_status: str = "NOT_IMPLEMENTED"
    levels_2_to_5_reason: str = LEVELS_2_TO_5_REASON

    def to_dict(self) -> dict:
        return {
            "level_1_syntax": self.level_1_syntax,
            "level_1_passed": self.level_1_passed,
            "levels_2_to_5_status": self.levels_2_to_5_status,
            "levels_2_to_5_reason": self.levels_2_to_5_reason,
        }


def run_validation(sandbox, plan) -> ValidationReport:
    """`sandbox` es un `ai_editor.repository.Sandbox` ya parcheado (via
    `ai_editor.patch.apply_operation`, POST-GRAPH 6/7). `plan` es el
    `ChangePlan` (POST-GRAPH 4) que origino esos archivos."""
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)

    results: dict[str, dict] = {}
    for step in plan_dict.get("steps", []):
        rel = step.get("file")
        if not rel or rel in results:
            continue
        ok, detail = check_syntax(sandbox.root, rel)
        results[rel] = {"ok": ok, "detail": detail}

    level_1_passed = all(r["ok"] for r in results.values())
    return ValidationReport(level_1_syntax=results, level_1_passed=level_1_passed)
