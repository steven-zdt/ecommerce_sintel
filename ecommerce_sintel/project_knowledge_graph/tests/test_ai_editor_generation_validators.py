"""
Unit tests para ai_editor/generation/validators.py -- FASE 28
"Structured LLM Output" (plan "AI Change Proposal Engine", 2026-08-11).

Regla critica que estos tests verifican explicitamente: texto libre
nunca se convierte en un patch -- `extract_json()` debe devolver `None`,
nunca "rescatar" un fragmento con una regex laxa.
"""
from ai_editor.generation.validators import extract_json, has_blocking_issues, validate_raw_schema

VALID_RAW = {
    "proposal_id": "gen-1",
    "operations": [{
        "file": "core/services/commands.py", "symbol": "X.get_by_name", "operation": "MODIFY",
        "old_content": "old", "new_content": "new", "reason": "razon real",
    }],
    "tests_to_update": [], "risks": [], "assumptions": [],
    "reasoning_summary": "resumen", "confidence": 0.8,
}


def test_extract_json_parses_raw_json_object():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_strips_markdown_code_fence():
    text = "```json\n{\"a\": 1}\n```"
    assert extract_json(text) == {"a": 1}


def test_extract_json_returns_none_for_free_text():
    assert extract_json("Claro, aca esta el cambio: modifica la linea 10.") is None


def test_extract_json_returns_none_for_partial_or_broken_json():
    assert extract_json('{"a": 1') is None


def test_extract_json_returns_none_for_json_array_not_object():
    assert extract_json('[1, 2, 3]') is None


def test_extract_json_returns_none_for_none_input():
    assert extract_json(None) is None


def test_validate_raw_schema_accepts_fully_valid_proposal():
    issues = validate_raw_schema(VALID_RAW)
    assert not has_blocking_issues(issues)


def test_validate_raw_schema_flags_missing_required_field():
    raw = {k: v for k, v in VALID_RAW.items() if k != "proposal_id"}
    issues = validate_raw_schema(raw)
    assert has_blocking_issues(issues)
    assert any(i.code == "MISSING_FIELD" and i.field == "proposal_id" for i in issues)


def test_validate_raw_schema_flags_wrong_type():
    raw = {**VALID_RAW, "operations": "not a list"}
    issues = validate_raw_schema(raw)
    assert has_blocking_issues(issues)


def test_validate_raw_schema_flags_confidence_out_of_range():
    raw = {**VALID_RAW, "confidence": 1.5}
    issues = validate_raw_schema(raw)
    assert any(i.code == "INVALID_CONFIDENCE" for i in issues)


def test_validate_raw_schema_flags_invalid_operation_value():
    raw = {**VALID_RAW, "operations": [{**VALID_RAW["operations"][0], "operation": "RENAME"}]}
    issues = validate_raw_schema(raw)
    assert any(i.code == "INVALID_OPERATION_VALUE" for i in issues)


def test_validate_raw_schema_flags_missing_operation_field():
    bad_op = {"operation": "MODIFY", "reason": "r"}  # sin 'file'
    raw = {**VALID_RAW, "operations": [bad_op]}
    issues = validate_raw_schema(raw)
    assert any(i.code == "MISSING_OPERATION_FIELD" and i.field == "operations[0].file" for i in issues)


def test_validate_raw_schema_warns_on_empty_operations_but_does_not_block():
    raw = {**VALID_RAW, "operations": []}
    issues = validate_raw_schema(raw)
    assert not has_blocking_issues(issues)
    assert any(i.code == "EMPTY_OPERATIONS" for i in issues)


def test_validate_raw_schema_warns_add_with_old_content():
    op = {"file": "a.py", "operation": "ADD", "reason": "r", "old_content": "no deberia estar", "new_content": "x"}
    issues = validate_raw_schema({**VALID_RAW, "operations": [op]})
    assert any(i.code == "UNEXPECTED_OLD_CONTENT" for i in issues)
    assert not has_blocking_issues(issues)
