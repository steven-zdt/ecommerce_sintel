"""
`validate_proposal_against_repo()` -- FASE 29 "Patch Proposal Validator"
(plan "AI Change Proposal Engine", 2026-08-11).

Distincion real con `validators.py` (FASE 28): ese modulo valida FORMA
(la salida cruda del LLM tiene los campos/tipos correctos) SIN tocar el
repo -- este modulo valida la `PatchProposal` YA CONSTRUIDA (`generation.
models.PatchProposal`) CONTRA el estado real del repo/plan. Es la unica
pieza de `generation/` que lee el filesystem real (nunca escribe, mismo
criterio que `ai_editor.planner.validator` -- POST-GRAPH 5).

Regla del prompt maestro aplicada literal: "SI FALLA -> PatchProposal ->
REJECT -> GenerationIssue. No aplicar." -- `validate_proposal_against_
repo()` nunca lanza, siempre devuelve una lista de `GenerationIssue`
(vacia = sin problemas); el llamador decide REJECT si hay alguna de
severidad ERROR (`validators.has_blocking_issues()`, reusado tal cual).

Reusa deliberadamente logica YA construida en vez de reimplementarla:
`ai_editor.patch.fingerprint` (mismo hash que usa el Patch Engine real,
POST-GRAPH 6) y `ai_editor.repository.sandbox._SENSITIVE_PATTERNS`
(misma lista que protege el sandbox, POST-GRAPH 18) -- si esas listas/
funciones cambian, esta validacion queda automaticamente sincronizada,
sin una copia paralela que pueda divergir.
"""
from ai_editor.generation.models import GENERATION_OPERATIONS, GenerationIssue, SEVERITY_ERROR, SEVERITY_WARNING
from ai_editor.patch.fingerprint import compute_fingerprint, read_lines_fingerprint
from ai_editor.patch.schema import MAX_PATCH_CONTENT_BYTES, OPERATION_ADD, OPERATION_DELETE
from ai_editor.repository.sandbox import _SENSITIVE_PATTERNS
from ai_editor.workspace import resolve_repo_file

# Defensa en profundidad, mismo criterio que POST-GRAPH 18
# (`MAX_SANDBOX_FILES`/`MAX_PATCH_CONTENT_BYTES`): un default provisional
# conservador, no un numero descubierto empiricamente -- ninguna
# propuesta real vista hasta ahora (contexto minimo, un target principal)
# se acerca a este limite. Ajustable si un caso de uso real lo justifica.
MAX_OPERATIONS_PER_PROPOSAL = 20

# Umbral heuristico para "posible eliminacion de codigo no relacionado":
# si new_content queda por debajo de este porcentaje del tamano de
# old_content en una operacion MODIFY/REPLACE, se advierte (WARNING, no
# ERROR -- una reduccion grande puede ser exactamente lo que el cambio
# pide, esto solo pide revision humana extra).
SHRINK_WARNING_RATIO = 0.5


def find_matching_step(operation, plan_dict: dict) -> dict | None:
    """Empareja una `PatchOperation` propuesta con el `PlanStep` real que
    la origino -- por archivo y, si la propuesta declaro un simbolo,
    tambien por simbolo. Sin este emparejamiento no hay contra que
    verificar `old_content`/lineas/hash, asi que devuelve `None` si no
    hay match (el llamador lo trata como "fuera del ChangePlan"). Publica
    (no `_privada`) desde FASE 31 "Patch Engine Integration" -- reusada
    tal cual por `generation.patch_integration` para resolver el mismo
    rango de lineas que esta funcion ya usa para validar."""
    for step in plan_dict.get("steps") or []:
        if step.get("file") != operation.file:
            continue
        if operation.symbol and step.get("symbol") and step["symbol"] != operation.symbol:
            continue
        return step
    return None


def _check_scope_and_operation(operation, step: dict | None) -> list[GenerationIssue]:
    """FASE 38 "Cross-Stack Generation" (2026-08-11) relajo esta regla,
    con confirmacion EXPLICITA del usuario dado que toca un guardrail de
    seguridad ya cerrado (FASE 29). Antes: SOLO el step `MODIFY` (target
    principal) podia recibir una escritura -- una propuesta jamas podia
    tocar mas de un archivo real. Ahora, ACOTADO (no "cualquier
    archivo"): tambien se permite escribir sobre steps `REVIEW` que el
    grafo YA vinculo como contrato/consumidor-frontend/dependencia-
    backend REAL del target (`planner.py` los arma exactamente desde
    esos 3 buckets) y sobre steps `RUN` (tests reales identificados por
    el grafo, coincide con el ejemplo de cross-stack del prompt maestro:
    "Model -> Serializer -> Endpoint -> API Client -> Store -> Component
    -> Tests"). Los `REVIEW` de DOCUMENTACION (archivo `.md`) siguen
    BLOQUEADOS -- FASE 43 "Documentation-Aware Generation" exige
    explicitamente que la documentacion quede como PROPUESTA, nunca
    aplicada automaticamente ("no debe modificarse automaticamente...
    si eso aumenta el riesgo"). Un archivo que ni siquiera aparece en el
    plan sigue bloqueado siempre (`FILE_OUTSIDE_PLAN`, sin cambios)."""
    issues: list[GenerationIssue] = []
    if step is None:
        issues.append(GenerationIssue(
            code="FILE_OUTSIDE_PLAN",
            message=f"'{operation.file}' no aparece en el ChangePlan -- una propuesta no puede "
                    "tocar archivos que el plan no declaro.",
            severity=SEVERITY_ERROR, field="operations.file",
        ))
        return issues

    step_operation = step["operation"]
    is_documentation = (step.get("file") or "").lower().endswith(".md")

    if step_operation == "MODIFY":
        return issues
    if step_operation == "REVIEW" and not is_documentation:
        return issues
    if step_operation == "RUN":
        return issues

    issues.append(GenerationIssue(
        code="OPERATION_NOT_ALLOWED_FOR_STEP",
        message=f"'{operation.file}' esta en el plan como step '{step_operation}' (step "
                f"{step['step']}) -- este tipo de step no puede recibir una escritura real "
                + (
                    "(documentacion: FASE 43 exige que quede como propuesta, nunca aplicada "
                    "automaticamente)." if is_documentation else
                    "."
                ),
        severity=SEVERITY_ERROR, field="operations.operation",
    ))
    return issues


def _check_file_and_content(operation, step: dict) -> list[GenerationIssue]:
    issues: list[GenerationIssue] = []

    real_path = resolve_repo_file(operation.file)
    if real_path is None:
        issues.append(GenerationIssue(
            code="FILE_NOT_FOUND",
            message=f"'{operation.file}' no existe en disco real -- no se puede validar contra "
                    "un archivo inexistente.",
            severity=SEVERITY_ERROR, field="operations.file",
        ))
        return issues

    if operation.operation != OPERATION_DELETE and not (operation.new_content or "").strip():
        issues.append(GenerationIssue(
            code="EMPTY_NEW_CONTENT",
            message=f"'{operation.file}': new_content esta vacio para operation="
                    f"'{operation.operation}'.",
            severity=SEVERITY_ERROR, field="operations.new_content",
        ))

    if operation.operation == OPERATION_ADD:
        return issues  # ADD no tiene old_content/lineas previas que verificar

    line_start, line_end = step.get("line_start"), step.get("line_end")
    if line_start is None or line_end is None:
        issues.append(GenerationIssue(
            code="MISSING_LINE_RANGE",
            message=f"'{operation.file}': el step del plan no tiene rango de lineas -- no se "
                    f"puede verificar old_content/hash para operation='{operation.operation}'.",
            severity=SEVERITY_ERROR, field="operations.file",
        ))
        return issues

    real_fingerprint = read_lines_fingerprint(real_path, line_start, line_end)
    if real_fingerprint is None:
        issues.append(GenerationIssue(
            code="INVALID_LINE_RANGE",
            message=f"'{operation.file}': el rango {line_start}-{line_end} del plan ya no es "
                    "valido contra el archivo real -- el grafo puede estar desactualizado.",
            severity=SEVERITY_ERROR, field="operations.file",
        ))
        return issues

    if operation.old_content is not None:
        proposed_fingerprint = compute_fingerprint(operation.old_content)
        if proposed_fingerprint != real_fingerprint:
            issues.append(GenerationIssue(
                code="OLD_CONTENT_MISMATCH",
                message=f"'{operation.file}': old_content de la propuesta no coincide con el "
                        f"contenido real de las lineas {line_start}-{line_end} -- el archivo "
                        "cambio, o el LLM genero old_content de forma incorrecta.",
                severity=SEVERITY_ERROR, field="operations.old_content",
            ))
    else:
        issues.append(GenerationIssue(
            code="MISSING_OLD_CONTENT",
            message=f"'{operation.file}': operation='{operation.operation}' deberia declarar "
                    "old_content para poder verificarlo contra el archivo real.",
            severity=SEVERITY_ERROR, field="operations.old_content",
        ))

    if operation.expected_hash and operation.expected_hash != real_fingerprint:
        issues.append(GenerationIssue(
            code="HASH_MISMATCH",
            message=f"'{operation.file}': expected_hash declarado por la propuesta no coincide "
                    "con el fingerprint real del rango.",
            severity=SEVERITY_ERROR, field="operations.expected_hash",
        ))

    return issues


def _check_content_size_and_shrink(operation) -> list[GenerationIssue]:
    issues: list[GenerationIssue] = []
    if operation.new_content and len(operation.new_content.encode("utf-8")) > MAX_PATCH_CONTENT_BYTES:
        issues.append(GenerationIssue(
            code="CONTENT_TOO_LARGE",
            message=f"'{operation.file}': new_content excede {MAX_PATCH_CONTENT_BYTES} bytes.",
            severity=SEVERITY_ERROR, field="operations.new_content",
        ))

    if operation.old_content and operation.new_content:
        old_len = len(operation.old_content)
        new_len = len(operation.new_content)
        if old_len > 0 and new_len < old_len * SHRINK_WARNING_RATIO:
            issues.append(GenerationIssue(
                code="POSSIBLE_UNRELATED_DELETION",
                message=f"'{operation.file}': new_content es {new_len}/{old_len} caracteres del "
                        "original -- posible eliminacion de codigo no relacionado, revisar a mano.",
                severity=SEVERITY_WARNING, field="operations.new_content",
            ))
    return issues


def _check_sensitive_file(operation) -> list[GenerationIssue]:
    if any(pattern in operation.file.lower() for pattern in _SENSITIVE_PATTERNS):
        return [GenerationIssue(
            code="SENSITIVE_FILE",
            message=f"'{operation.file}' matchea un patron sensible ({_SENSITIVE_PATTERNS}) -- "
                    "nunca se acepta una propuesta que toque un archivo asi.",
            severity=SEVERITY_ERROR, field="operations.file",
        )]
    return []


def _check_undeclared_contract(operation, step: dict | None, context_dict: dict) -> list[GenerationIssue]:
    """¿La propuesta toca un contrato (Endpoint/Serializer)? Antes de
    FASE 38 esto era un ERROR bloqueante ("undeclarado" = el plan solo
    lo listaba REVIEW, nunca escribible). Desde FASE 38, escribir sobre
    un contrato REVIEW real (no-documentacion) YA esta permitido por
    `_check_scope_and_operation()` -- ya no es "silencioso" (el step
    existe en el plan, el grafo lo vinculo). Se degrada a WARNING:
    cumple FASE 41 "Contract-Aware Generation" ("no permitir que el LLM
    cambie SILENCIOSAMENTE un contrato" -- un WARNING visible en el
    reporte no es silencioso, solo ya no bloquea un cambio cross-stack
    legitimo)."""
    if step is not None and step.get("operation") == "MODIFY":
        return []  # es el target principal, es exactamente lo que se pidio cambiar
    resolution = (context_dict or {}).get("resolution") or {}
    contract_files = {c.get("file") for c in (resolution.get("contracts") or []) if c.get("file")}
    if operation.file in contract_files:
        return [GenerationIssue(
            code="UNDECLARED_CONTRACT_CHANGE",
            message=f"'{operation.file}' es un contrato (Endpoint/Serializer) -- confirmar que "
                    "el cambio es intencional y que los consumidores (frontend/tests) tambien "
                    "se actualizan si corresponde.",
            severity=SEVERITY_WARNING, field="operations.file",
        )]
    return []


def validate_proposal_against_repo(proposal, plan, context=None) -> list[GenerationIssue]:
    """Punto de entrada de FASE 29. `proposal` es una `generation.models.
    PatchProposal`, `plan` un `ai_editor.planner.ChangePlan` (o su dict),
    `context` un `ai_editor.resolver.ChangeContext` opcional (habilita el
    chequeo de contratos no declarados; sin el, esa verificacion
    simplemente se omite en vez de fallar)."""
    plan_dict = plan.to_dict() if hasattr(plan, "to_dict") else dict(plan)
    context_dict = (context.to_dict() if hasattr(context, "to_dict") else dict(context)) if context else {}

    issues: list[GenerationIssue] = []

    if len(proposal.operations) > MAX_OPERATIONS_PER_PROPOSAL:
        issues.append(GenerationIssue(
            code="TOO_MANY_OPERATIONS",
            message=f"La propuesta tiene {len(proposal.operations)} operaciones, el limite es "
                    f"{MAX_OPERATIONS_PER_PROPOSAL}.",
            severity=SEVERITY_ERROR, field="operations",
        ))

    for operation in proposal.operations:
        if operation.operation not in GENERATION_OPERATIONS:
            issues.append(GenerationIssue(
                code="INVALID_OPERATION_VALUE",
                message=f"'{operation.file}': operation='{operation.operation}' invalida.",
                severity=SEVERITY_ERROR, field="operations.operation",
            ))
            continue

        issues.extend(_check_sensitive_file(operation))
        step = find_matching_step(operation, plan_dict)
        issues.extend(_check_scope_and_operation(operation, step))
        if step is not None:
            issues.extend(_check_file_and_content(operation, step))
            issues.extend(_check_undeclared_contract(operation, step, context_dict))
        issues.extend(_check_content_size_and_shrink(operation))

    return issues


__all__ = ["validate_proposal_against_repo", "find_matching_step", "MAX_OPERATIONS_PER_PROPOSAL"]
