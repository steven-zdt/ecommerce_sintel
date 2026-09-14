"""
`generate_patch_proposal()` -- FASE 28 "Structured LLM Output" (plan
"AI Change Proposal Engine", 2026-08-11), primer punto de entrada real
del AI Change Proposal Engine.

Flujo (sin aplicar nada todavia -- "SIN aplicar todavia el patch" es
literal del prompt maestro para esta primera ejecucion):

    ChangeGenerationRequest (FASE 25/26)
        -> prompts.build_prompt()          (FASE 27)
        -> ai_editor.llm.complete()         (POST-GRAPH 2, ya existente)
        -> validators.extract_json()        (FASE 28)
        -> validators.validate_raw_schema() (FASE 28)
        -> PatchProposal real (FASE 25) o REJECTED

Nunca llama a `ai_editor.patch.engine.apply_operation()` ni a nada de
`ai_editor.repository` -- ese cableado es FASE 31 "Patch Engine
Integration", una fase futura explicitamente posterior en el prompt
maestro.
"""
from ai_editor import llm
from ai_editor.generation.context import build_generation_context
from ai_editor.generation.models import (
    STATUS_ERROR,
    STATUS_PROPOSED,
    STATUS_REJECTED,
    ChangeGenerationRequest,
    GenerationConfidence,
    GenerationIssue,
    GenerationResult,
    PatchOperation,
    PatchProposal,
    SEVERITY_ERROR,
)
from ai_editor.generation.prompts import build_prompt
from ai_editor.generation.validators import extract_json, has_blocking_issues, validate_raw_schema
from ai_editor.llm.providers import LLMRequestError


def _build_proposal_from_raw(raw: dict, change_id: str) -> PatchProposal:
    """Precondicion: `raw` ya paso `validate_raw_schema()` sin issues de
    severidad ERROR -- esta funcion no vuelve a validar tipos."""
    operations = [
        PatchOperation(
            file=op["file"], symbol=op.get("symbol"), operation=op["operation"],
            old_content=op.get("old_content"), new_content=op.get("new_content"),
            old_hash=op.get("old_hash"), expected_hash=op.get("expected_hash"),
            reason=op["reason"],
        )
        for op in raw["operations"]
    ]
    return PatchProposal(
        proposal_id=raw["proposal_id"],
        change_id=change_id,
        operations=operations,
        reasoning_summary=raw["reasoning_summary"],
        confidence=GenerationConfidence.from_score(float(raw["confidence"])),
        risks=list(raw.get("risks") or []),
        assumptions=list(raw.get("assumptions") or []),
        validation_requirements=list(raw.get("validation_requirements") or []),
        tests_to_update=list(raw.get("tests_to_update") or []),
        tests_to_add=list(raw.get("tests_to_add") or []),
        tests_to_remove=list(raw.get("tests_to_remove") or []),
        documentation_to_update=list(raw.get("documentation_to_update") or []),
    )


def generate_patch_proposal(request: ChangeGenerationRequest, change_id: str | None = None,
                             provider: str | None = None,
                             previous_attempts: list[str] | None = None) -> GenerationResult:
    """`request` ya viene ensamblado por `context.build_generation_context()`.
    `change_id` identifica el `ChangeIntent`/`ChangeContext` de origen para
    trazabilidad (default: se toma de `request.change_intent['id']` si
    existe). `provider` permite forzar un LLM especifico (ver
    `ai_editor.llm.complete`), por default usa el configurado por env var.
    `previous_attempts` (FASE 30 "Generation Retry Engine", NUEVO): notas
    de correccion de intentos previos fallidos -- se reenvia tal cual a
    `prompts.build_prompt()`, esta funcion no le agrega logica propia de
    reintento (eso vive en `retry.py`, que es quien la llama de nuevo)."""
    request_dict = request.to_dict() if hasattr(request, "to_dict") else dict(request)
    resolved_change_id = change_id or (request_dict.get("change_intent") or {}).get("id") or "unknown"

    system, user = build_prompt(request_dict, previous_attempts=previous_attempts)

    try:
        response = llm.complete(user, system=system, provider=provider)
    except LLMRequestError as exc:
        return GenerationResult(
            status=STATUS_ERROR, proposal=None,
            issues=[GenerationIssue(code="LLM_REQUEST_FAILED", message=str(exc), severity=SEVERITY_ERROR)],
        )

    raw = extract_json(response.text)
    if raw is None:
        return GenerationResult(
            status=STATUS_REJECTED, proposal=None,
            issues=[GenerationIssue(
                code="INVALID_JSON",
                message="La respuesta del LLM no es JSON valido (o no es un objeto) -- rechazada sin "
                        "intentar repararla, por regla explicita del prompt maestro.",
                severity=SEVERITY_ERROR,
            )],
            raw_llm_text=response.text, provider=response.provider, model=response.model,
        )

    issues = validate_raw_schema(raw)
    if has_blocking_issues(issues):
        return GenerationResult(
            status=STATUS_REJECTED, proposal=None, issues=issues, raw_llm_text=response.text,
            provider=response.provider, model=response.model,
        )

    proposal = _build_proposal_from_raw(raw, resolved_change_id)
    return GenerationResult(
        status=STATUS_PROPOSED, proposal=proposal, issues=issues, raw_llm_text=response.text,
        provider=response.provider, model=response.model,
    )


__all__ = ["generate_patch_proposal", "build_generation_context"]
