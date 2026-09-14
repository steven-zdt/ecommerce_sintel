"""
`render_full_review()` -- FASE 45 "Human Review UI/CLI" (plan "AI
Change Proposal Engine", 2026-08-11).

Regla del prompt maestro: "Mostrar REQUEST/INTENT/PLAN/FILES/SYMBOLS/
PATCH/RISKS/TESTS/GRAPH DIFF/IMPACT/CONFIDENCE. Permitir APPROVE/REJECT/
REGENERATE/MODIFY PLAN."

**Alcance real, honesto**: "UI/CLI" aca es SOLO el render de texto --
no hay una interfaz interactiva real construida (ni web ni terminal),
consistente con `approval.gate.ChangeSummary.render_text()` (POST-GRAPH
11), que ya sigue el mismo criterio ("intencionalmente TRIVIAL, el
punto no es construir una interfaz de aprobacion"). Esta funcion
EXTIENDE ese render con todo lo que las fases FASE 33-44 agregaron
(patch/confidence/graph diff/impact/architecture/contracts/dependencias/
tests/documentacion) que `ChangeSummary` (cerrada, POST-GRAPH 11) no
conocia todavia.

Las decisiones que el prompt maestro pide permitir siguen siendo
exactamente las 4 de `approval.schema` (POST-GRAPH 11):
`APPROVE`/`REJECT`/`MODIFY_PLAN`/`REQUEST_EXPLANATION` -- "REGENERAR"
no es una decision que se registre aca, es una accion SEPARADA
(volver a llamar `retry.generate_with_retry()` o `generator.
generate_patch_proposal()`), documentada como tal al final del render.
"""
from ai_editor.generation.models import PatchProposal


def render_full_review(
    proposal: PatchProposal,
    change_summary=None,
    validation_report=None,
    reconciliation_report=None,
    impact_report=None,
    confidence_report=None,
    contract_report=None,
    architecture_report=None,
    dependency_report=None,
    test_awareness_report=None,
    documentation_report=None,
) -> str:
    """Todos los reportes son OPCIONALES salvo `proposal` -- cada
    seccion solo aparece si el caller ya corrio esa fase, nunca se
    fabrica una linea sobre un reporte que no existe. `validation_report`
    espera un `generation.validation_report.GenerationValidationReport`
    (FASE 33, `.syntax_passed`) -- NO el `ValidationReport` crudo de
    `SandboxLoopResult.validation_report` (`.level_1_passed`, otro tipo);
    mismo criterio que `confidence_engine.compute_composite_confidence()`."""
    lines: list[str] = ["=" * 70, "AI CHANGE PROPOSAL -- HUMAN REVIEW", "=" * 70]

    if change_summary is not None:
        lines.append(change_summary.render_text())
        lines.append("")

    lines.append(f"PATCH -- {len(proposal.operations)} operacion(es):")
    for op in proposal.operations:
        symbol_part = f" :: {op.symbol}" if op.symbol else ""
        lines.append(f"  [{op.operation}] {op.file}{symbol_part}")
        lines.append(f"    razon: {op.reason}")
    lines.append("")
    lines.append(f"REASONING: {proposal.reasoning_summary}")
    if proposal.risks:
        lines.append(f"RISKS: {'; '.join(proposal.risks)}")
    if proposal.assumptions:
        lines.append(f"ASSUMPTIONS: {'; '.join(proposal.assumptions)}")

    if confidence_report is not None:
        c = confidence_report.composite
        lines.append(f"CONFIDENCE: {c.level} ({c.score:.2f})")
        for factor in confidence_report.factors:
            lines.append(f"  - {factor.name}: {factor.score:.2f} ({factor.source})")

    if reconciliation_report is not None:
        r = reconciliation_report
        lines.append(
            f"GRAPH DIFF (scope): {r.status} -- predicho {r.predicted_files} archivo(s)/"
            f"{r.predicted_symbols} simbolo(s), real {r.actual_files}/{r.actual_symbols}"
        )
        if r.unexpected_impact:
            lines.append(f"  IMPACTO INESPERADO: {r.unexpected_impact}")

    if impact_report is not None:
        i = impact_report
        lines.append(
            f"IMPACT RECHECK: {i.status} -- predicho {i.predicted_risk}/"
            f"{i.predicted_total_affected}, actual {i.actual_risk}/{i.actual_total_affected}"
        )

    if validation_report is not None:
        syntax_label = (
            "PASS" if validation_report.syntax_passed
            else "FAIL" if validation_report.syntax_passed is False else "N/A"
        )
        lines.append(f"SYNTAX: {syntax_label}")

    if architecture_report is not None:
        lines.append(f"ARCHITECTURE COMPLIANCE: {architecture_report.status}")
        for issue in architecture_report.issues:
            lines.append(f"  - [{issue.severity}] {issue.message}")

    if contract_report is not None and contract_report.affects_contract:
        lines.append(f"CONTRACT COVERAGE: {contract_report.status} -- {contract_report.recommendation}")

    if dependency_report is not None and dependency_report.new_imports:
        lines.append(f"NEW DEPENDENCIES: {dependency_report.new_imports}")
        for issue in dependency_report.issues:
            lines.append(f"  - [{issue.severity}] {issue.message}")

    if test_awareness_report is not None and test_awareness_report.issues:
        lines.append("TEST AWARENESS:")
        for issue in test_awareness_report.issues:
            lines.append(f"  - [{issue.severity}] {issue.message}")

    if documentation_report is not None:
        lines.append(f"DOCUMENTATION: {documentation_report.recommendation}")

    lines.append("")
    lines.append("Decisiones validas: APPROVE / REJECT / MODIFY_PLAN / REQUEST_EXPLANATION")
    lines.append("(regenerar una propuesta rechazada es una accion separada: retry.generate_with_retry())")

    return "\n".join(lines)


__all__ = ["render_full_review"]
