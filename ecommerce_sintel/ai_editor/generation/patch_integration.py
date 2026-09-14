"""
`apply_proposal_to_sandbox()` -- FASE 31 "Patch Engine Integration"
(plan "AI Change Proposal Engine", 2026-08-11).

Flujo del prompt maestro, literal:
    LLM -> PatchProposal -> PatchProposalValidator -> Patch Engine -> Sandbox

Esta es la primera pieza de `generation/` que TERMINA escribiendo algo --
pero solo dentro de un `Sandbox` YA CREADO por el caller (`ai_editor.
repository.create_sandbox(plan)`, POST-GRAPH 7), nunca sobre
`WORKSPACE_ROOT`. Ni crea ni destruye el sandbox -- mismo criterio de
"quien crea el sandbox es el caller, esto solo lo usa" que ya siguen
`validation.engine.run_validation(sandbox, plan)` y `approval.gate.
build_change_summary()`.

Regla del prompt maestro aplicada literal: "El Patch Engine NO debe
confiar ciegamente en el LLM. Debe volver a validar: path/hash/scope/
symbol/operation." -- cumplido en DOS capas independientes, no una:
  1. `proposal_validator.validate_proposal_against_repo()` (FASE 29) se
     vuelve a correr aca mismo, SIEMPRE, sin importar si el caller ya la
     corrio antes -- defensa en profundidad, nunca confiar en que un
     caller externo valido correctamente.
  2. Cada operacion individual pasa por `patch.engine.apply_operation()`
     (POST-GRAPH 6), que vuelve a comparar el `old_fingerprint` de la
     operacion contra el contenido REAL del sandbox en el momento exacto
     de escribir -- si algo cambio la sandbox entre la validacion y la
     escritura (ej. una operacion anterior de la MISMA propuesta), se
     rechaza (`FINGERPRINT_MISMATCH`).

     **Importante, bug real encontrado y corregido durante la
     verificacion de esta fase**: `old_fingerprint` se deriva de
     `compute_fingerprint(operation.old_content)` -- el `old_content` que
     `validate_proposal_against_repo()` (FASE 29) YA confirmo identico al
     repo real -- NUNCA releyendo el sandbox en el momento de la
     conversion. Un primer intento de esta funcion recalculaba el
     fingerprint leyendo el sandbox EN EL MOMENTO DE CONVERTIR cada
     operacion -- eso lo hace coincidir consigo mismo trivialmente
     (siempre "iba a matchear lo que sea que hubiera ahi"), anulando por
     completo la deteccion de drift entre operaciones de una misma
     propuesta. Detectado con un test real de 2 operaciones sobre el
     mismo rango: la primera cambia el contenido, la segunda deberia
     fallar por fingerprint desactualizado -- con el bug, aplicaba las
     dos igual.

Esta fase NUNCA llama a `repository.promote_to_workspace()` -- el flujo
del prompt maestro se detiene explicitamente en "Sandbox", promover a
un checkout real sigue siendo una decision posterior (VALIDATION ->
GRAPH RECONCILIATION -> IMPACT RECHECK -> HUMAN APPROVAL -> PROMOTE, ya
construidas en POST-GRAPH 8/11/12, reusables tal cual sobre el sandbox
que esta funcion deja listo).
"""
from ai_editor.generation.models import PatchApplicationResult
from ai_editor.generation.proposal_validator import find_matching_step, validate_proposal_against_repo
from ai_editor.generation.validators import has_blocking_issues
from ai_editor.patch.engine import apply_operation
from ai_editor.patch.fingerprint import compute_fingerprint
from ai_editor.patch.schema import OPERATION_ADD, STATUS_APPLIED
from ai_editor.patch.schema import PatchOperation as EnginePatchOperation


def _convert_to_engine_operation(operation, step: dict) -> EnginePatchOperation:
    """Convierte un `generation.models.PatchOperation` (sin lineas, con
    `old_content`) en un `patch.schema.PatchOperation` real (con lineas +
    `old_fingerprint`) -- el `step` emparejado (`find_matching_step`,
    FASE 29) es la unica fuente de lineas reales, la propuesta del LLM
    nunca las declara directamente (FASE 25 lo dejo asi a proposito, ver
    `models.py`).

    `old_fingerprint = compute_fingerprint(operation.old_content)` --
    NUNCA se relee el sandbox aca (ver docstring del modulo, "bug real
    encontrado y corregido"): el valor correcto es el fingerprint del
    `old_content` que la propuesta declaro y que `validate_proposal_
    against_repo()` YA verifico identico al repo real -- asi
    `apply_operation()` puede detectar de verdad si el sandbox cambio
    entre la validacion y el momento de escribir.

    ADD es un caso especial: no hay un rango previo que reemplazar, asi
    que se inserta INMEDIATAMENTE DESPUES del rango del step
    (`line_end + 1` -- recordar la semantica real de `apply_operation`:
    un ADD con `line_start=N` inserta ANTES de la linea N, entonces para
    insertar DESPUES de `line_end` hay que pedir `line_end + 1`, leccion
    real de POST-GRAPH 21). `old_fingerprint=None` para ADD -- no hay
    contenido previo que verificar en esa posicion exacta."""
    if operation.operation == OPERATION_ADD:
        insert_line = (step.get("line_end") or step.get("line_start") or 0) + 1
        return EnginePatchOperation(
            file=operation.file, operation=operation.operation,
            line_start=insert_line, line_end=insert_line,
            old_fingerprint=None, new_content=operation.new_content, reason=operation.reason,
        )

    return EnginePatchOperation(
        file=operation.file, operation=operation.operation,
        line_start=step["line_start"], line_end=step["line_end"],
        old_fingerprint=compute_fingerprint(operation.old_content),
        new_content=operation.new_content, reason=operation.reason,
    )


def apply_proposal_to_sandbox(sandbox, proposal, plan, context=None) -> PatchApplicationResult:
    """`sandbox` es un `ai_editor.repository.sandbox.Sandbox` YA CREADO
    (`create_sandbox(plan)`) por el caller. `proposal`/`plan`/`context`
    son los mismos objetos que `validate_proposal_against_repo()` (FASE
    29) ya espera.

    Aplica las operaciones EN ORDEN, se detiene en la primera que no
    quede `APPLIED` (fail-fast) -- una propuesta con multiples
    operaciones sobre el mismo archivo que empieza a divergir a mitad de
    camino no debe seguir aplicando el resto a ciegas."""
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)

    pre_issues = validate_proposal_against_repo(proposal, plan_dict, context)
    if has_blocking_issues(pre_issues):
        return PatchApplicationResult(
            proposal_id=proposal.proposal_id, applied=False, apply_results=[],
            pre_validation_issues=pre_issues,
        )

    apply_results = []
    for operation in proposal.operations:
        step = find_matching_step(operation, plan_dict)
        engine_op = _convert_to_engine_operation(operation, step)
        result = apply_operation(sandbox.root, engine_op)
        apply_results.append(result)
        if result.status != STATUS_APPLIED:
            break

    all_applied = bool(apply_results) and all(r.status == STATUS_APPLIED for r in apply_results)
    return PatchApplicationResult(
        proposal_id=proposal.proposal_id, applied=all_applied, apply_results=apply_results,
        pre_validation_issues=pre_issues,
    )


__all__ = ["apply_proposal_to_sandbox"]
