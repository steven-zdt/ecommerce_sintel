"""
`generate_with_retry()` -- FASE 30 "Generation Retry Engine" (plan "AI
Change Proposal Engine", 2026-08-11).

Regla del prompt maestro aplicada literal: "Si el patch falla: Generation
-> Validation -> FAIL, no regenerar infinitamente. Maximo: 3 intentos,
configurable. CADA RETRY DEBE EXPLICAR: error, causa, restriccion
añadida, correccion solicitada."

Orquesta lo que ya existe, sin duplicar logica:
    generator.generate_patch_proposal()        (FASE 28)
    proposal_validator.validate_proposal_against_repo()  (FASE 29)
    prompts.build_prompt(..., previous_attempts=...)      (FASE 27, extendido)

Un intento se considera FALLIDO si:
  - `generate_patch_proposal()` devuelve `REJECTED` (JSON invalido/forma
    invalida, FASE 28), o
  - devuelve `PROPOSED` pero `validate_proposal_against_repo()` encuentra
    al menos un `GenerationIssue` de severidad ERROR (FASE 29).
`ERROR` (fallo de red del LLM, no del contenido) NO consume la logica de
correccion de prompt -- reintentar la MISMA llamada tiene sentido (puede
ser transitorio), agregar una nota de "correccion" no aportaria nada
util al LLM sobre un fallo que nunca vio.

Este modulo SIGUE sin aplicar nada -- ninguna funcion de aca llama a
`patch`/`repository` (misma regla que `generator.py`/
`proposal_validator.py`).
"""
from ai_editor.generation.generator import generate_patch_proposal
from ai_editor.generation.models import (
    STATUS_ERROR,
    STATUS_PROPOSED,
    GenerationIssue,
    RetryAttempt,
    RetryOutcome,
)
from ai_editor.generation.proposal_validator import validate_proposal_against_repo
from ai_editor.generation.validators import has_blocking_issues

# "Maximo: 3 intentos, configurable" -- literal del prompt maestro.
DEFAULT_MAX_RETRIES = 3


def _build_correction_note(attempt: int, issues: list[GenerationIssue]) -> str:
    """Un unico string legible, para que `prompts.build_prompt()` pueda
    inyectarlo tal cual en `PREVIOUS_ATTEMPTS_FEEDBACK` -- describe error +
    causa (via `issue.message`, ya es descriptivo) + que campo esta
    involucrado, que es la "restriccion" implicita a respetar la proxima
    vez (ej. si `field='operations[0].file'`, la correccion es "revisa
    ese campo especifico")."""
    if not issues:
        return f"Intento {attempt}: fallo sin detalle especifico de issues (ver GenerationResult.issues)."
    bullets = "\n".join(
        f"  - [{i.code}] {i.message}" + (f" (campo: {i.field})" if i.field else "")
        for i in issues if i.severity == "ERROR"
    )
    return f"Intento {attempt} fallo. Corregi EXPLICITAMENTE lo siguiente en este intento:\n{bullets}"


def generate_with_retry(request, plan, context=None, max_retries: int = DEFAULT_MAX_RETRIES,
                         change_id: str | None = None, provider: str | None = None) -> RetryOutcome:
    """`request`/`plan`/`context` son los mismos objetos que
    `generate_patch_proposal()`/`validate_proposal_against_repo()` ya
    esperan. Devuelve un `RetryOutcome` con el HISTORIAL completo de
    intentos -- nunca solo el ultimo, para que quede trazable por que
    fallaron los anteriores (FASE 48 "Generation Audit" podra reusar
    esto tal cual)."""
    attempts: list[RetryAttempt] = []
    previous_notes: list[str] = []

    for attempt_num in range(1, max_retries + 1):
        result = generate_patch_proposal(
            request, change_id=change_id, provider=provider,
            previous_attempts=previous_notes or None,
        )

        if result.status == STATUS_ERROR:
            # Fallo de red, no de contenido -- reintentar la llamada tal
            # cual (sin nota de correccion nueva) sigue teniendo sentido.
            attempts.append(RetryAttempt(attempt=attempt_num, status=result.status, issues=result.issues))
            if attempt_num == max_retries:
                return RetryOutcome(attempts=attempts, final_result=result, succeeded=False)
            continue

        if result.status != STATUS_PROPOSED:
            note = _build_correction_note(attempt_num, result.issues)
            attempts.append(RetryAttempt(
                attempt=attempt_num, status=result.status, issues=result.issues, correction_note=note,
            ))
            if attempt_num == max_retries:
                return RetryOutcome(attempts=attempts, final_result=result, succeeded=False)
            previous_notes.append(note)
            continue

        proposal_issues = validate_proposal_against_repo(result.proposal, plan, context)
        if not has_blocking_issues(proposal_issues):
            attempts.append(RetryAttempt(attempt=attempt_num, status=result.status, issues=proposal_issues))
            return RetryOutcome(attempts=attempts, final_result=result, succeeded=True)

        note = _build_correction_note(attempt_num, proposal_issues)
        attempts.append(RetryAttempt(
            attempt=attempt_num, status=result.status, issues=proposal_issues, correction_note=note,
        ))
        if attempt_num == max_retries:
            return RetryOutcome(attempts=attempts, final_result=result, succeeded=False)
        previous_notes.append(note)

    # Inalcanzable con max_retries >= 1 (el loop siempre retorna en la
    # ultima iteracion) -- guardia explicita en vez de dejarlo implicito.
    raise RuntimeError("generate_with_retry: max_retries debe ser >= 1")


__all__ = ["generate_with_retry", "DEFAULT_MAX_RETRIES"]
