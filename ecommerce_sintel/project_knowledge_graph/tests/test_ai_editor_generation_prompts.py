"""
Unit tests para ai_editor/generation/prompts.py -- FASE 27
"Architecture-Aware Prompt Engine" (plan "AI Change Proposal Engine",
2026-08-11).
"""
import json

from ai_editor.generation.context import build_generation_context
from ai_editor.generation.models import ChangeGenerationRequest
from ai_editor.generation.prompts import (
    TYPE_API,
    TYPE_BACKEND,
    TYPE_CROSS_STACK,
    TYPE_DOCUMENTATION,
    TYPE_FRONTEND,
    TYPE_UNKNOWN,
    _classify_change_type,
    build_prompt,
)
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context


def _request_for(entities, scope, domain="renting", intent_name="modify_availability"):
    intent = ChangeIntent(
        id="test-prompts", request="cambio de prueba", domain=domain, intent=intent_name,
        entities=entities, scope=scope, confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    return build_generation_context(intent, context, plan)


def test_classify_change_type_api_for_real_django_api_target():
    request = _request_for(["EquipmentViewSet.check_availability"], ["backend"])
    assert _classify_change_type(request.to_dict()) == TYPE_API


def test_classify_change_type_cross_stack_when_scope_has_backend_and_frontend():
    request = _request_for(["EquipmentViewSet.check_availability"], ["backend", "frontend"])
    assert _classify_change_type(request.to_dict()) == TYPE_CROSS_STACK


def test_classify_change_type_unknown_for_empty_request():
    empty = ChangeGenerationRequest(
        change_intent={"scope": []}, change_plan={"steps": []},
        graph_context={}, source_context={}, test_context={}, architecture_context={},
    )
    assert _classify_change_type(empty) == TYPE_UNKNOWN


def test_build_prompt_returns_deterministic_system_and_user_sections():
    request = _request_for(["EquipmentViewSet.check_availability"], ["backend"])
    system1, user1 = build_prompt(request)
    system2, user2 = build_prompt(request)
    assert system1 == system2
    assert user1 == user2
    assert "JSON" in system1


def test_build_prompt_includes_all_required_sections():
    request = _request_for(["EquipmentViewSet.check_availability"], ["backend"])
    _, user = build_prompt(request)
    for section in (
        "CHANGE_REQUEST", "CHANGE_PLAN", "TARGET_FILES_AND_SYMBOLS", "CURRENT_SOURCE",
        "CONTRACTS_AND_DEPENDENCIES", "TESTS", "ARCHITECTURAL_RULES", "EXPECTED_RESULT_SCHEMA",
    ):
        assert f"## {section}" in user


def test_build_prompt_current_source_section_is_valid_embedded_json_with_real_code():
    request = _request_for(["EquipmentViewSet.check_availability"], ["backend"])
    _, user = build_prompt(request)
    section_text = user.split("## CURRENT_SOURCE\n")[1].split("\n\n## ")[0]
    parsed = json.loads(section_text)
    assert any(v and "def check_availability" in v for v in parsed.values())


def test_classify_change_type_backend_for_target_outside_api_path():
    request = _request_for(["HomeCardGroupSelector.get_by_name"], ["backend"], domain="core")
    assert _classify_change_type(request.to_dict()) == TYPE_BACKEND


def test_build_prompt_backend_guidance_mentions_service_layer_rule():
    request = _request_for(["HomeCardGroupSelector.get_by_name"], ["backend"], domain="core")
    system, _ = build_prompt(request)
    assert "Commands" in system or "Selectors" in system
