"""
`build_change_summary()`/`record_decision()` -- POST-GRAPH 11 "Human
Approval Gate" (rediseno "AI Editor Runtime", 2026-08-11).

Compone el `ChangeSummary` que pide el prompt maestro a partir de datos
YA REALES construidos en fases anteriores (`ChangeContext` de POST-GRAPH
3, `ChangePlan` de POST-GRAPH 4, `ValidationReport`/test report opcionales
de POST-GRAPH 8/10) -- cero consultas nuevas al grafo, cero logica de
negocio nueva, solo agregacion y formato para revision humana.

`record_decision()` es intencionalmente TRIVIAL (no hay UI, no hay
persistencia todavia) -- el punto de esta fase no es construir una
interfaz de aprobacion, es dejar el PUNTO DE PARADA explicito en el
codigo: nada de `patch/`/`repository/` avanza a "promover al repo real"
sin pasar antes por un `ApprovalRecord` con `decision == APPROVE`
construido aca (ver POST-GRAPH 12, Commit Control).
"""
from ai_editor.approval.schema import ApprovalRecord, ChangeSummary


def build_change_summary(context, plan, validation_report=None, test_report=None) -> ChangeSummary:
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    resolution = context_dict.get("resolution") or {}
    intent = context_dict.get("intent") or {}
    steps = plan_dict.get("steps", [])

    files = sorted({s["file"] for s in steps if s.get("file")})
    symbols = sorted({s["symbol"] for s in steps if s.get("symbol")})
    contracts = [c["name"] for c in resolution.get("contracts") or []]

    documentation: list[str] = []
    docs = resolution.get("documentation") or {}
    for category in ("architecture_docs", "implementation_docs", "audit_docs"):
        documentation.extend(d["name"] for d in docs.get(category) or [])

    # `resolve_change()` no expone `total_affected` directamente (esa
    # cifra vive en `calculate_change_impact()`) -- se aproxima sumando
    # los 3 buckets de impacto reales que SI trae el envelope, no se
    # vuelve a consultar el grafo para esto.
    total_affected = (
        len(resolution.get("contracts") or [])
        + len(resolution.get("frontend_consumers") or [])
        + len(resolution.get("backend_dependencies") or [])
    )

    patch_operations = sum(1 for s in steps if s.get("operation") == "MODIFY")

    validation_status = "NOT_RUN"
    validation_issues: list[str] = []
    if validation_report is not None:
        vr = validation_report.to_dict() if hasattr(validation_report, "to_dict") else dict(validation_report)
        validation_status = "PASS" if vr.get("level_1_passed") else "FAIL"
        validation_issues = [
            f"{file}: {result['detail']}"
            for file, result in (vr.get("level_1_syntax") or {}).items()
            if not result.get("ok")
        ]

    return ChangeSummary(
        request=intent.get("request", ""),
        interpretation=intent,
        files=files,
        symbols=symbols,
        contracts=contracts,
        risk=resolution.get("risk", "UNKNOWN"),
        total_affected=total_affected,
        patch_operations=patch_operations,
        tests=test_report or {},
        documentation=documentation,
        validation_status=validation_status,
        validation_issues=validation_issues,
    )


def record_decision(decision: str, reviewer_note: str | None = None) -> ApprovalRecord:
    """Lanza `ValueError` (via `ApprovalRecord.__post_init__`) si
    `decision` no es una de las 4 opciones validas -- no hay forma de
    registrar una decision ambigua."""
    return ApprovalRecord(decision=decision, reviewer_note=reviewer_note)
