"""
`audit_pipeline_run()` -- POST-GRAPH 13 "Change Audit" (rediseno "AI
Editor Runtime", 2026-08-11), extendido en FASE 48 "Generation Audit"
(plan "AI Change Proposal Engine", 2026-08-11).

Compone un registro COMPLETO de una corrida del pipeline (intent ->
resolver -> planner -> validation -> approval -> [promote]) a partir de
los objetos ya reales de cada fase -- cero logica nueva de negocio, solo
extraccion de los campos relevantes y sanitizacion (via
`ai_editor.audit.log`) antes de persistir.

**FASE 48** agrega `proposal`/`generation_result` (opcionales) para
registrar lo que el prompt maestro pide especificamente de la capa de
generacion: `proposal_id`, `model`/`model version` (campo nuevo en
`GenerationResult`, ver `generation/models.py`), archivos/simbolos que
la propuesta declara tocar, confianza. **Nunca se registra**: API keys,
tokens, contenido crudo de `new_content`/`old_content` (podria contener
codigo propietario o, en teoria, algo sensible pegado por error) -- solo
metadatos. `log_change_operation()` sanitiza igual cualquier clave que
matchee un patron sensible, defensa en profundidad ya existente
reusada tal cual."""
from ai_editor.audit.log import log_change_operation


def audit_pipeline_run(intent, context, plan=None, validation_report=None,
                        test_report=None, approval=None, promote_result=None,
                        patch_results=None, rollback_result=None,
                        proposal=None, generation_result=None) -> None:
    """Todos los argumentos salvo `intent`/`context` son opcionales --
    una corrida puede auditarse en cualquier punto del pipeline, no hace
    falta haber llegado hasta el final. `intent`/`context` aceptan tanto
    el objeto real (`ChangeIntent`/`ChangeContext`) como su `.to_dict()`.
    `patch_results` (POST-GRAPH 17): lista de `ApplyResult` de
    `ai_editor.patch.apply_operation()`, para poder derivar
    `patch_failures` en `metrics.py`. `rollback_result` (POST-GRAPH 17):
    el `RollbackResult` si esta corrida tuvo un rollback, para derivar
    `rollback_count`. `proposal`/`generation_result` (FASE 48): la
    `PatchProposal`/`GenerationResult` de `generation/`, si esta corrida
    paso por el AI Change Proposal Engine."""
    intent_dict = intent.to_dict() if hasattr(intent, "to_dict") else dict(intent)
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)

    fields = {
        "request": intent_dict.get("request"),
        "intent_id": intent_dict.get("id"),
        "domain": intent_dict.get("domain"),
        "intent_status": intent_dict.get("status"),
        "context_status": context_dict.get("status"),
        "primary_target": (context_dict.get("primary_target") or {}).get("name"),
        "unresolved_entities": context_dict.get("unresolved_entities"),
    }

    if plan is not None:
        plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
        steps = plan_dict.get("steps", [])
        fields["plan_status"] = plan_dict.get("status")
        fields["files"] = sorted({s["file"] for s in steps if s.get("file")})
        fields["symbols"] = sorted({s["symbol"] for s in steps if s.get("symbol")})

    if validation_report is not None:
        vr = validation_report.to_dict() if hasattr(validation_report, "to_dict") else dict(validation_report)
        fields["validation_status"] = "PASS" if vr.get("level_1_passed") else "FAIL"

    if test_report is not None:
        fields["tests_required"] = test_report.get("required")
        fields["tests_run"] = test_report.get("tests_run")

    if approval is not None:
        approval_dict = approval.to_dict() if hasattr(approval, "to_dict") else dict(approval)
        fields["approval_decision"] = approval_dict.get("decision")

    if promote_result is not None:
        pr = promote_result.to_dict() if hasattr(promote_result, "to_dict") else dict(promote_result)
        fields["promote_status"] = pr.get("status")
        fields["files_promoted"] = pr.get("files_promoted")

    if patch_results is not None:
        statuses = [
            (r.to_dict() if hasattr(r, "to_dict") else dict(r)).get("status")
            for r in patch_results
        ]
        fields["patch_statuses"] = statuses
        fields["patch_failures"] = sum(1 for s in statuses if s != "APPLIED")

    if rollback_result is not None:
        rr = rollback_result.to_dict() if hasattr(rollback_result, "to_dict") else dict(rollback_result)
        fields["rollback_status"] = rr.get("status")

    if generation_result is not None:
        gr = generation_result.to_dict() if hasattr(generation_result, "to_dict") else dict(generation_result)
        fields["generation_status"] = gr.get("status")
        fields["generation_provider"] = gr.get("provider")
        fields["generation_model"] = gr.get("model")
        fields["generation_attempt"] = gr.get("attempt")
        # Nunca el texto crudo del LLM -- puede ser largo y no aporta a
        # una auditoria de METADATOS (proposal_id/archivos/confianza ya
        # se registran aparte, via `proposal` abajo).

    if proposal is not None:
        pd = proposal.to_dict() if hasattr(proposal, "to_dict") else dict(proposal)
        fields["proposal_id"] = pd.get("proposal_id")
        fields["proposal_confidence"] = (pd.get("confidence") or {}).get("score")
        fields["proposal_files"] = sorted({op["file"] for op in pd.get("operations") or []})
        fields["proposal_operations_count"] = len(pd.get("operations") or [])
        # Nunca old_content/new_content -- solo metadatos (archivo/
        # cantidad), nunca el CONTENIDO propuesto.

    log_change_operation(**fields)
