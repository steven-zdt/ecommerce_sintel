"""
Integration tests para ai_editor/generation/retry.py -- FASE 30
"Generation Retry Engine" (plan "AI Change Proposal Engine", 2026-08-11).

Regla del prompt maestro verificada aca literal: "Maximo: 3 intentos,
configurable" y "CADA RETRY DEBE EXPLICAR: error, causa, restriccion
añadida, correccion solicitada" -- `ai_editor.llm.complete()` se
mockea con una SECUENCIA de respuestas (`side_effect`), igual patron que
`test_ai_editor_generation_generator.py`, sobre un `ChangeGenerationRequest`/
`ChangePlan` reales.
"""
import json
from unittest.mock import patch

import ai_editor.generation.generator as generator_module
from ai_editor.generation.context import build_generation_context
from ai_editor.generation.retry import DEFAULT_MAX_RETRIES, generate_with_retry
from ai_editor.intent.schema import ChangeIntent
from ai_editor.llm.providers import LLMRequestError, LLMResponse
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import resolve_repo_file


def _real_setup():
    intent = ChangeIntent(
        id="test-retry", request="r", domain="core", intent="x",
        entities=["HomeCardGroupSelector.get_by_name"], scope=["backend"],
        confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    request = build_generation_context(intent, context, plan)
    return request, plan, context


def _exact_old_content(plan):
    step1 = plan.to_dict()["steps"][0]
    real_path = resolve_repo_file(step1["file"])
    lines = real_path.read_text(encoding="utf-8").splitlines(keepends=True)
    return step1, "".join(lines[step1["line_start"] - 1:step1["line_end"]])


def _proposal_json(proposal_id, file, symbol, old_content, new_content):
    return {
        "proposal_id": proposal_id,
        "operations": [{
            "file": file, "symbol": symbol, "operation": "MODIFY",
            "old_content": old_content, "new_content": new_content, "reason": "r",
        }],
        "tests_to_update": [], "risks": [], "assumptions": [],
        "reasoning_summary": "test", "confidence": 0.9,
    }


def _response(payload: dict) -> LLMResponse:
    return LLMResponse(text=json.dumps(payload), provider="fake", model="fake-model", raw={})


def test_first_attempt_success_needs_no_retry():
    request, plan, context = _real_setup()
    step1, exact_old = _exact_old_content(plan)
    good = _proposal_json("p-good", step1["file"], step1["symbol"], exact_old, exact_old)

    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.return_value = _response(good)
        outcome = generate_with_retry(request, plan, context)

    assert outcome.succeeded is True
    assert len(outcome.attempts) == 1
    assert outcome.attempts[0].correction_note is None
    assert outcome.final_result.proposal.proposal_id == "p-good"


def test_fails_twice_then_succeeds_on_third_attempt():
    """El ejemplo literal del prompt maestro: Attempt 1 FAIL, Attempt 2
    FAIL, Attempt 3 PASS."""
    request, plan, context = _real_setup()
    step1, exact_old = _exact_old_content(plan)
    bad = _proposal_json("p-bad", step1["file"], step1["symbol"], "contenido inventado", "x")
    good = _proposal_json("p-good", step1["file"], step1["symbol"], exact_old, exact_old)

    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.side_effect = [_response(bad), _response(bad), _response(good)]
        outcome = generate_with_retry(request, plan, context, max_retries=3)

    assert outcome.succeeded is True
    assert len(outcome.attempts) == 3
    assert outcome.attempts[0].correction_note is not None
    assert "OLD_CONTENT_MISMATCH" in outcome.attempts[0].correction_note
    assert outcome.attempts[1].correction_note is not None
    assert outcome.attempts[2].correction_note is None  # el ultimo exitoso no genera nota
    assert outcome.final_result.proposal.proposal_id == "p-good"


def test_exhausts_max_retries_and_reports_failure():
    request, plan, context = _real_setup()
    step1, _ = _exact_old_content(plan)
    bad = _proposal_json("p-bad", step1["file"], step1["symbol"], "siempre invalido", "x")

    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.return_value = _response(bad)
        outcome = generate_with_retry(request, plan, context, max_retries=3)

    assert outcome.succeeded is False
    assert len(outcome.attempts) == 3
    assert all(a.status == "PROPOSED" for a in outcome.attempts)
    assert all(a.issues for a in outcome.attempts)


def test_second_attempt_prompt_includes_the_first_attempt_correction_note():
    """Verifica que la correccion realmente se REENVIA al LLM -- no solo
    que se calcula, sino que aparece en el `user_prompt` del intento 2."""
    request, plan, context = _real_setup()
    step1, exact_old = _exact_old_content(plan)
    bad = _proposal_json("p-bad", step1["file"], step1["symbol"], "contenido inventado", "x")
    good = _proposal_json("p-good", step1["file"], step1["symbol"], exact_old, exact_old)

    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.side_effect = [_response(bad), _response(good)]
        generate_with_retry(request, plan, context, max_retries=3)

    assert mock_llm.complete.call_count == 2
    first_call_kwargs = mock_llm.complete.call_args_list[0]
    second_call_kwargs = mock_llm.complete.call_args_list[1]
    first_user_prompt = first_call_kwargs.args[0] if first_call_kwargs.args else first_call_kwargs.kwargs["user"]
    second_user_prompt = second_call_kwargs.args[0] if second_call_kwargs.args else second_call_kwargs.kwargs["user"]
    assert "PREVIOUS_ATTEMPTS_FEEDBACK" not in first_user_prompt
    assert "PREVIOUS_ATTEMPTS_FEEDBACK" in second_user_prompt
    assert "OLD_CONTENT_MISMATCH" in second_user_prompt


def test_llm_connection_error_retries_without_correction_note():
    """ERROR (fallo de red) es distinto de REJECTED/PROPOSED-con-issues --
    reintenta la MISMA llamada, sin agregar una nota de correccion (no
    hay nada de contenido que corregir)."""
    request, plan, context = _real_setup()
    step1, exact_old = _exact_old_content(plan)
    good = _proposal_json("p-good", step1["file"], step1["symbol"], exact_old, exact_old)

    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.side_effect = [LLMRequestError("timeout simulado"), _response(good)]
        outcome = generate_with_retry(request, plan, context, max_retries=3)

    assert outcome.succeeded is True
    assert outcome.attempts[0].status == "ERROR"
    assert outcome.attempts[0].correction_note is None


def test_default_max_retries_is_three_matching_master_prompt():
    assert DEFAULT_MAX_RETRIES == 3


def test_never_calls_patch_engine_or_writes_anything():
    import ast

    import ai_editor.generation.retry as mod

    with open(mod.__spec__.origin, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any(m.startswith("ai_editor.patch.engine") for m in imported_modules)
    assert not any(m.startswith("ai_editor.repository") for m in imported_modules)
