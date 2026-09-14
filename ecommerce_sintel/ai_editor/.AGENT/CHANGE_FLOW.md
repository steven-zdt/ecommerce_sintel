# Change Flow -- el ciclo completo de `ai_editor`

12 pasos, cada uno con su funcion real y su estado -- ver
`AUTONOMOUS_CHANGE_LOOP.md` para el diagrama completo con detalle de por
que NO se orquesta automaticamente. Este documento es la referencia
rapida de que llamar y en que orden.

```python
from ai_editor.intent import interpret_request
from ai_editor.resolver import resolve_change_context
from ai_editor.planner import build_change_plan, validate_plan
from ai_editor.repository import create_sandbox, promote_to_workspace, rollback_promotion
from ai_editor.patch import apply_operation
from ai_editor.validation import run_validation, build_test_validation_report
from ai_editor.approval import build_change_summary, record_decision
from ai_editor.audit import audit_pipeline_run

# 1-2. INTENT -- interpreta la solicitud humana, confirma el dominio contra el grafo real
intent = interpret_request("Permitir alquiler por horas en Renting")
if intent.status == "NEEDS_CLARIFICATION":
    ...  # pedir aclaracion al usuario, NO adivinar

# 3. RESOLVE -- resuelve cada entidad EXACTA contra el grafo
context = resolve_change_context(intent)

# 4-5. PLAN + VALIDATE PLAN -- pasos concretos + verificacion contra el disco real
plan = build_change_plan(context)
plan_validation = validate_plan(plan)
if plan_validation.status != "APPROVED":
    ...  # BLOCKED, no seguir

# 6. SANDBOX -- copia aislada, el checkout real nunca se toca aca
with create_sandbox(plan) as sandbox:

    # 7. PATCH -- aplica un new_content YA DECIDIDO (no lo genera este sistema)
    result = apply_operation(sandbox.root, patch_operation)

    # 8-9. VALIDATE (Nivel 1) + TEST IMPACT -- sintaxis real; tests identificados, no ejecutados
    validation_report = run_validation(sandbox, plan)
    test_report = build_test_validation_report(context)

    # 10. HUMAN GATE -- punto de parada obligatorio
    summary = build_change_summary(context, plan, validation_report, test_report)
    print(summary.render_text())
    approval = record_decision("APPROVE")  # SOLO tras revision humana real

    # 11. COMMIT -- requiere aprobacion + confirm=True + sin drift + validacion OK; workspace_root EXPLICITO
    promote_result = promote_to_workspace(sandbox, approval, workspace_root, confirm=True,
                                            validation_report=validation_report)

    # (si algo sale mal despues de promover)
    # rollback_promotion(workspace_root, promote_result)

# 12. AUDIT -- registra la corrida completa, nunca secretos
audit_pipeline_run(intent, context, plan, validation_report, test_report, approval, promote_result)
```

## Puntos de parada reales (no solo documentados -- verificados por codigo)

- `intent.status == "NEEDS_CLARIFICATION"` -- si el dominio no se
  confirma o hay ambiguedad, no hay `ChangeContext` util que resolver.
- `plan_validation.status == "BLOCKED"` -- archivos/lineas no coinciden
  con el disco real, o quedan entidades sin confirmar.
- `promote_to_workspace()` exige `ApprovalRecord.decision == APPROVE`
  (rechaza sin el) Y `confirm=True` explicito (rechaza sin el) Y ausencia
  de drift de fingerprint (rechaza si el archivo real cambio desde el
  sandbox) Y, si se pasa `validation_report`, que la sintaxis haya
  pasado -- 4 chequeos independientes, cualquiera bloquea.

## Que NO esta en este flujo (a proposito)

No hay ningun paso que genere `new_content` automaticamente -- ese valor
lo decide un humano o un test antes de llamar `apply_operation()`. Ver
`PATCH_ENGINE.md`.
