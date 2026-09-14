"""
`run_autonomous_change_loop()` -- FASE 51 "AI Editor Agent" + FASE 53
"Autonomous Controlled Loop" (plan "AI Change Proposal Engine",
2026-08-11). Primera vez en todo el desarrollo de este plan de 60 fases
que se ejecuta contra un LLM REAL (Ollama local, `llama3.1:8b`,
verificado alcanzable en `localhost:11434` antes de escribir este
modulo) -- hasta FASE 50 ninguna fase se habia probado contra un
proveedor real (ver `generation/performance.py`, FASE 56).

Orquesta, en UNA sola llamada, exactamente el flujo que el resto de
`ai_editor` ya construyo fase por fase, sin agregar logica de negocio
nueva -- este modulo es pura COMPOSICION:

    intent/interpret_request()          (POST-GRAPH 2, LLM)
        -> resolver/resolve_change_context()   (POST-GRAPH 3, grafo)
        -> planner/build_change_plan()         (POST-GRAPH 4, grafo)
        -> planner/validate_plan()              (POST-GRAPH 5, filesystem)
        -> generation/generate_with_retry()     (FASE 28+29+30, LLM + repo)
        -> generation/run_sandbox_validation_loop() (FASE 31+32, sandbox)
        -> generation/{code_quality,architecture_compliance,
           dependency_awareness,contract_awareness,test_awareness,
           documentation_awareness}             (FASE 36-43)
        -> generation/reconciliation + impact_recheck (FASE 34-35)
        -> generation/confidence_engine          (FASE 44)
        -> generation/human_review                (FASE 45)
        -> generation/promotion_gate              (FASE 46)
        -> pipeline_states.classify_pipeline_state() (FASE 50, deriva status)

Se detiene (return anticipado) en el primer punto donde la etapa
correspondiente NO produce un resultado utilizable -- nunca sigue
adelante "por las dudas" con datos parciales/invalidos.

**REGLA FINAL DE SEGURIDAD, garantizada estructuralmente**: este archivo
NUNCA importa `ai_editor.generation.promotion` ni `ai_editor.repository.
promote` -- no hay ninguna linea de codigo en todo `ai_editor.agent` que
pueda escribir sobre `WORKSPACE_ROOT` real. El resultado mas "avanzado"
posible es `APPROVAL_REQUIRED` (un sandbox aplicado y validado, con todos
los reportes de FASE 33-46 adjuntos) -- promover esa propuesta requiere
una llamada SEPARADA, humana, a `generation.promotion.review_and_
promote()`, fuera de este modulo.
"""
from ai_editor.agent.policy import AgentPolicy
from ai_editor.agent.schema import AgentRunResult
from ai_editor.generation.confidence_engine import compute_composite_confidence
from ai_editor.generation.architecture_compliance import check_architectural_compliance
from ai_editor.generation.code_quality import run_code_quality_checks
from ai_editor.generation.context import build_generation_context
from ai_editor.generation.contract_awareness import check_contract_coverage
from ai_editor.generation.dependency_awareness import check_dependency_awareness
from ai_editor.generation.documentation_awareness import check_documentation_awareness
from ai_editor.generation.human_review import render_full_review
from ai_editor.generation.impact_recheck import capture_impact_baseline, recheck_impact
from ai_editor.generation.pipeline_states import FAILED, REJECTED, classify_pipeline_state
from ai_editor.generation.promotion_gate import check_promotion_gate
from ai_editor.generation.reconciliation import reconcile_change_scope
from ai_editor.generation.retry import generate_with_retry
from ai_editor.generation.sandbox_loop import run_sandbox_validation_loop
from ai_editor.generation.test_awareness import check_test_awareness
from ai_editor.generation.validation_report import build_generation_validation_report
from ai_editor.intent.parser import interpret_request
from ai_editor.intent.schema import STATUS_RESOLVED as INTENT_RESOLVED
from ai_editor.planner.planner import build_change_plan
from ai_editor.planner.schema import STATUS_PLANNED
from ai_editor.planner.validator import STATUS_APPROVED, validate_plan
from ai_editor.resolver.resolver import resolve_change_context
from ai_editor.resolver.schema import STATUS_RESOLVED as CONTEXT_RESOLVED


def run_autonomous_change_loop(request: str, policy: AgentPolicy | None = None,
                                intent=None) -> AgentRunResult:
    """`request` es texto libre en lenguaje natural, exactamente como lo
    recibe `intent.interpret_request()`. `policy` (FASE 52) por default
    usa `AgentPolicy()` (3 reintentos, provider por env var). `intent`
    permite inyectar un `ChangeIntent` YA resuelto (saltando la primera
    llamada al LLM) -- util quirurgicamente para pruebas deterministas
    del resto del pipeline sin depender de que el LLM de interpretacion
    de intencion produzca siempre el mismo resultado; el flujo normal
    (sin este parametro) siempre llama a `interpret_request()`.

    Limpieza del sandbox: si el resultado queda `APPROVAL_REQUIRED`,
    `result.sandbox_loop_result.sandbox` NO se limpia aca -- sigue vivo a
    proposito, porque `generation.promotion.review_and_promote()`
    (llamado aparte, por un humano) lo necesita para promover. Es
    responsabilidad del CALLER invocar `.cleanup()` una vez que termino
    de usarlo (haya promovido o descartado la propuesta). En cualquier
    otro estado terminal (`FAILED`/`REJECTED`) el sandbox, si llego a
    crearse, ya se limpio aca -- no hay nada que promover."""
    policy = policy or AgentPolicy()

    if intent is None:
        intent = interpret_request(request, provider=policy.provider)
    if intent.status != INTENT_RESOLVED:
        return AgentRunResult(
            request=request, status=FAILED, intent=intent,
            detail=f"ChangeIntent no quedo RESOLVED (esta en {intent.status}) -- "
                    f"ambiguedades: {intent.ambiguities or 'ninguna declarada'}.",
        )

    context = resolve_change_context(intent)
    if context.status != CONTEXT_RESOLVED:
        return AgentRunResult(
            request=request, status=FAILED, intent=intent, context=context,
            detail=f"ChangeContext no quedo RESOLVED (esta en {context.status}) -- "
                    f"entidades sin confirmar contra el grafo: {context.unresolved_entities}.",
        )

    plan = build_change_plan(context)
    plan_validation = validate_plan(plan)
    if plan.status != STATUS_PLANNED or plan_validation.status != STATUS_APPROVED:
        return AgentRunResult(
            request=request, status=FAILED, intent=intent, context=context, plan=plan,
            plan_validation=plan_validation,
            detail=f"ChangePlan bloqueado -- issues: {plan_validation.issues or plan.blocked_reason}.",
        )

    impact_baseline = capture_impact_baseline(context)

    generation_request = build_generation_context(intent, context, plan)
    retry_outcome = generate_with_retry(
        generation_request, plan, context, max_retries=policy.max_retries, provider=policy.provider,
    )
    if not retry_outcome.succeeded:
        return AgentRunResult(
            request=request, status=REJECTED, intent=intent, context=context, plan=plan,
            plan_validation=plan_validation, retry_outcome=retry_outcome,
            detail=f"generate_with_retry() agoto {policy.max_retries} intentos sin una "
                    f"PatchProposal valida -- ver retry_outcome.attempts para el historial completo.",
        )

    proposal = retry_outcome.final_result.proposal
    loop_result = run_sandbox_validation_loop(proposal, plan, context)

    if not loop_result.ready_for_approval:
        loop_result.sandbox.cleanup()
        status = classify_pipeline_state(sandbox_loop_result=loop_result).state
        return AgentRunResult(
            request=request, status=status, intent=intent, context=context, plan=plan,
            plan_validation=plan_validation, retry_outcome=retry_outcome, sandbox_loop_result=loop_result,
            detail="El Sandbox Generation Loop (FASE 32) no quedo listo para revision -- "
                    "no se aplico o fallo la validacion de sintaxis.",
        )

    validation_report = build_generation_validation_report(loop_result, context)
    code_quality_report = run_code_quality_checks(loop_result.sandbox, proposal)
    architecture_report = check_architectural_compliance(proposal)
    dependency_report = check_dependency_awareness(proposal)
    contract_report = check_contract_coverage(proposal, context)
    test_awareness_report = check_test_awareness(proposal)
    documentation_report = check_documentation_awareness(proposal, context=context)
    reconciliation_report = reconcile_change_scope(proposal, loop_result, plan, context)
    impact_recheck_report = recheck_impact(impact_baseline) if impact_baseline is not None else None
    confidence_report = compute_composite_confidence(
        proposal, context=context, validation_report=validation_report,
        architecture_report=architecture_report, contract_report=contract_report,
    )
    promotion_gate_result = check_promotion_gate(
        loop_result, reconciliation_report=reconciliation_report, impact_report=impact_recheck_report,
        architecture_report=architecture_report, contract_report=contract_report,
    )
    human_review_text = render_full_review(
        proposal, validation_report=validation_report, reconciliation_report=reconciliation_report,
        impact_report=impact_recheck_report, confidence_report=confidence_report,
        contract_report=contract_report, architecture_report=architecture_report,
        dependency_report=dependency_report, test_awareness_report=test_awareness_report,
        documentation_report=documentation_report,
    )

    status = classify_pipeline_state(sandbox_loop_result=loop_result).state
    warnings = list(promotion_gate_result.blocking_reasons) + list(promotion_gate_result.warnings)

    return AgentRunResult(
        request=request, status=status,
        detail="Sandbox aplicado y validado, todos los reportes de FASE 33-46 adjuntos -- "
                "listo para revision humana. Promover requiere una llamada aparte a "
                "generation.promotion.review_and_promote() con decision/confirm explicitos.",
        intent=intent, context=context, plan=plan, plan_validation=plan_validation,
        retry_outcome=retry_outcome, sandbox_loop_result=loop_result,
        code_quality_report=code_quality_report, architecture_report=architecture_report,
        dependency_report=dependency_report, contract_report=contract_report,
        test_awareness_report=test_awareness_report, documentation_report=documentation_report,
        reconciliation_report=reconciliation_report, impact_recheck_report=impact_recheck_report,
        confidence_report=confidence_report, promotion_gate_result=promotion_gate_result,
        human_review_text=human_review_text, warnings=warnings,
    )


__all__ = ["run_autonomous_change_loop"]
