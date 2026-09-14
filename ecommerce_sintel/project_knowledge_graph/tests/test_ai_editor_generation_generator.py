"""
Integration tests para ai_editor/generation/generator.py -- FASE 28
"Structured LLM Output" (plan "AI Change Proposal Engine", 2026-08-11).

`ai_editor.llm.complete()` se mockea (`unittest.mock.patch`, mismo patron
que `test_ai_editor_llm.py` usa para los proveedores reales) -- estos
tests NO dependen de un LLM real corriendo (Ollama/OpenAI/Anthropic no
estan disponibles en este entorno de test), pero SI usan un
`ChangeGenerationRequest` real, construido contra el grafo/repo real
(mismo target que el resto de la suite de generation/), para que el
prompt/contexto que efectivamente se ensambla sea real de punta a punta
-- solo la respuesta del LLM es sintetica.
"""
import json
from unittest.mock import patch

from ai_editor.generation.context import build_generation_context
from ai_editor.generation.models import STATUS_ERROR, STATUS_PROPOSED, STATUS_REJECTED
from ai_editor.intent.schema import ChangeIntent
from ai_editor.llm.providers import LLMRequestError, LLMResponse
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context

import ai_editor.generation.generator as generator_module
from ai_editor.generation.generator import generate_patch_proposal


def _real_request():
    intent = ChangeIntent(
        id="test-generator", request="Permitir alquiler por horas.",
        domain="core", intent="modify_x", entities=["HomeCardGroupSelector.get_by_name"],
        scope=["backend"], confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    return build_generation_context(intent, context, plan)


def _valid_llm_json(request) -> dict:
    target = next(iter(request.to_dict()["source_context"]["targets"].values()))
    return {
        "proposal_id": "gen-real-1",
        "operations": [{
            "file": target["file"], "symbol": target.get("symbol"), "operation": "MODIFY",
            "old_content": target["source"], "new_content": target["source"], "reason": "sin cambio, test",
        }],
        "tests_to_update": [], "risks": ["ninguno, es un test"], "assumptions": [],
        "reasoning_summary": "test de integracion FASE 28", "confidence": 0.85,
    }


def test_generate_patch_proposal_returns_proposed_for_valid_structured_json():
    request = _real_request()
    fake_json = _valid_llm_json(request)
    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.return_value = LLMResponse(
            text=json.dumps(fake_json), provider="fake", model="fake-model", raw={},
        )
        result = generate_patch_proposal(request)

    assert result.status == STATUS_PROPOSED
    assert result.proposal.proposal_id == "gen-real-1"
    assert result.proposal.confidence.level == "HIGH"
    assert len(result.proposal.operations) == 1
    assert result.issues == []


def test_generate_patch_proposal_strips_markdown_fence_around_json():
    request = _real_request()
    fake_json = _valid_llm_json(request)
    fenced_text = "```json\n" + json.dumps(fake_json) + "\n```"
    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.return_value = LLMResponse(text=fenced_text, provider="fake", model="fake-model", raw={})
        result = generate_patch_proposal(request)
    assert result.status == STATUS_PROPOSED


def test_generate_patch_proposal_rejects_free_text_never_fabricates_a_patch():
    """La regla critica de FASE 28: texto libre -> REJECT, nunca se
    intenta convertir en un patch de todas formas."""
    request = _real_request()
    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.return_value = LLMResponse(
            text="Claro, para lograr eso hay que cambiar la funcion asi: ...",
            provider="fake", model="fake-model", raw={},
        )
        result = generate_patch_proposal(request)

    assert result.status == STATUS_REJECTED
    assert result.proposal is None
    assert result.issues[0].code == "INVALID_JSON"
    assert result.raw_llm_text is not None


def test_generate_patch_proposal_rejects_json_missing_required_fields():
    request = _real_request()
    incomplete = {"operations": []}  # sin proposal_id/reasoning_summary/confidence
    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.return_value = LLMResponse(
            text=json.dumps(incomplete), provider="fake", model="fake-model", raw={},
        )
        result = generate_patch_proposal(request)

    assert result.status == STATUS_REJECTED
    assert result.proposal is None
    assert any(i.code == "MISSING_FIELD" for i in result.issues)


def test_generate_patch_proposal_returns_error_status_on_llm_connection_failure():
    """Distincion real entre REJECTED (el LLM respondio, pero mal) y
    ERROR (el LLM ni siquiera respondio) -- un consumidor futuro (FASE 30
    Retry Engine) necesita poder distinguir "reintentar con mejor prompt"
    de "reintentar la llamada de red"."""
    request = _real_request()
    with patch.object(generator_module, "llm") as mock_llm:
        mock_llm.complete.side_effect = LLMRequestError("conexion rechazada (simulado)")
        result = generate_patch_proposal(request)

    assert result.status == STATUS_ERROR
    assert result.proposal is None
    assert result.issues[0].code == "LLM_REQUEST_FAILED"


def test_generate_patch_proposal_never_calls_patch_engine_or_writes_anything():
    """FASE 24-28 es explicito: 'SIN aplicar todavia el patch'. Confirma
    via AST (no via texto -- el docstring del modulo MENCIONA a proposito
    `ai_editor.patch`/`apply_operation` en prosa explicando que NO se usa
    todavia, un grep de texto plano da un falso positivo con eso) que
    `generator.py` no tiene ningun `import` real de `ai_editor.patch`/
    `ai_editor.repository`."""
    import ast

    import ai_editor.generation.generator as mod

    with open(mod.__spec__.origin, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    assert not any(m.startswith("ai_editor.patch") for m in imported_modules)
    assert not any(m.startswith("ai_editor.repository") for m in imported_modules)
    assert not hasattr(mod, "apply_operation")
    assert not hasattr(mod, "promote_to_workspace")
