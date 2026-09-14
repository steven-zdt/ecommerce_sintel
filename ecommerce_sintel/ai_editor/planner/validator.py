"""
`validate_plan()` -- POST-GRAPH 5 "Change Plan Validator" (rediseno "AI
Editor Runtime", 2026-08-11).

Antes de permitir cualquier patch, valida el `ChangePlan` (POST-GRAPH 4)
contra el FILESYSTEM REAL -- no solo contra lo que el grafo decia en el
momento de resolver. El grafo (`KNOWLEDGE_GRAPH.json`) es una foto de la
ULTIMA auditoria (`cli audit`), puede estar desactualizado respecto al
disco real en este mismo instante (alguien edito el archivo despues del
ultimo rebuild) -- este validador es la unica capa de todo `ai_editor`
que efectivamente lee archivos reales del repo (nunca escribe), por eso
usa `ai_editor.workspace` en vez de confiar ciegamente en las lineas que
el grafo reporto.

Regla del prompt maestro aplicada aca: "Si el plan contiene unknown/
ambiguous/missing/high-risk unresolved -> NO permitir patch automatico.
Estado: BLOCKED."
"""
from dataclasses import dataclass, field

from ai_editor.workspace import WorkspaceViolation, resolve_repo_doc_path, resolve_repo_file

STATUS_APPROVED = "APPROVED"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class PlanValidationResult:
    status: str
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"status": self.status, "issues": self.issues, "warnings": self.warnings}


def _count_lines(path) -> int:
    with path.open(encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def validate_plan(plan) -> PlanValidationResult:
    """`plan` es un `ai_editor.planner.ChangePlan`."""
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    issues: list[str] = []
    warnings: list[str] = []

    if plan_dict["status"] != "PLANNED":
        issues.append(
            f"El plan no esta en estado PLANNED (esta en {plan_dict['status']}): "
            f"{plan_dict.get('blocked_reason')}"
        )
        return PlanValidationResult(status=STATUS_BLOCKED, issues=issues, warnings=warnings)

    context = plan_dict["context"]
    for unresolved in context.get("unresolved_entities") or []:
        issues.append(f"Entidad mencionada en la solicitud pero NO confirmada en el grafo: {unresolved}")

    known_steps = {s["step"] for s in plan_dict["steps"]}
    for step in plan_dict["steps"]:
        for dep in step["dependencies"]:
            if dep not in known_steps:
                issues.append(f"Step {step['step']}: depende del step {dep}, que no existe en este plan")

        if step["file"] is None:
            continue  # nodo sin archivo asociado (Endpoint/App/etc.) -- nada que verificar en disco

        try:
            real_path = resolve_repo_file(step["file"])
        except WorkspaceViolation as exc:
            issues.append(f"Step {step['step']}: {exc}")
            continue

        if real_path is None:
            # Bug real encontrado en FASE 24 (plan "AI Change Proposal Engine",
            # 2026-08-11): los nodos `Documentation` (pasos REVIEW sobre un
            # `.md`) guardan su path relativo al repo GIT completo, no a
            # WORKSPACE_ROOT (ver docstring de `REPO_ROOT` en workspace.py) --
            # por eso `resolve_repo_file()` nunca los encuentra, aunque el
            # archivo si exista realmente. No es el mismo caso que un Symbol/
            # File/Endpoint desactualizado: ai_editor jamas escribe sobre un
            # `.md` de REVIEW, asi que degradar a warning en vez de bloquear
            # todo el plan por una referencia de solo-lectura fuera de su
            # alcance de escritura.
            if step["file"].endswith(".md") and resolve_repo_doc_path(step["file"]) is not None:
                warnings.append(
                    f"Step {step['step']}: '{step['file']}' es documentacion que vive fuera de "
                    "WORKSPACE_ROOT (nivel repo) -- fuera del alcance de escritura de ai_editor, "
                    "informativo solamente."
                )
                continue
            issues.append(
                f"Step {step['step']}: archivo '{step['file']}' no existe en disco (probado como "
                "path de backend y de frontend) -- el grafo esta desactualizado respecto al repo "
                "real, correr `cli audit` de nuevo"
            )
            continue

        if step["line_start"] is not None:
            if step["line_start"] < 1 or step["line_end"] < step["line_start"]:
                issues.append(f"Step {step['step']}: rango de lineas invalido ({step['line_start']}-{step['line_end']})")
            else:
                line_count = _count_lines(real_path)
                if step["line_end"] > line_count:
                    issues.append(
                        f"Step {step['step']}: rango de lineas ({step['line_start']}-{step['line_end']}) "
                        f"excede el archivo real ({line_count} lineas) -- el grafo esta desactualizado, "
                        "correr `cli audit` de nuevo antes de continuar"
                    )

    if plan_dict["steps"] and plan_dict["steps"][0]["risk"] == "HIGH":
        warnings.append("El target principal tiene riesgo HIGH (calculate_change_impact) -- revision extra recomendada.")

    if not any(s["operation"] == "RUN" for s in plan_dict["steps"]):
        warnings.append("No se identifico ningun test real que cubra este cambio.")

    status = STATUS_BLOCKED if issues else STATUS_APPROVED
    return PlanValidationResult(status=status, issues=issues, warnings=warnings)
