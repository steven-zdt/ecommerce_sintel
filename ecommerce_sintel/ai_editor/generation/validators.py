"""
Validacion de la salida CRUDA del LLM -- FASE 28 "Structured LLM Output"
(plan "AI Change Proposal Engine", 2026-08-11).

Regla critica del prompt maestro, aplicada literal aca: "Si el LLM
devuelve texto libre sin estructura valida -> REJECT. No intentar
convertir silenciosamente una respuesta invalida en patch." --
`extract_json()` nunca "adivina" un JSON a partir de prosa (no hay
regex que intente rescatar fragmentos); si `json.loads` falla, es
`None`, punto. `validate_raw_schema()` es la unica puerta antes de
construir un `PatchProposal` real -- ninguna funcion de este modulo
escribe nada, esto es puro chequeo de forma (la validacion CONTRA el
repo real -- archivo existe, symbol existe, old_content coincide,
scope permitido -- es FASE 29 "Patch Proposal Validator", todavia no
implementada en esta primera ejecucion FASE 24-28).
"""
import json
import re

from ai_editor.generation.models import GENERATION_OPERATIONS, GenerationIssue, SEVERITY_ERROR, SEVERITY_WARNING

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*\n(.*)\n```\s*$", re.DOTALL)

REQUIRED_TOP_LEVEL_KEYS = {
    "proposal_id": str,
    "operations": list,
    "reasoning_summary": str,
    "confidence": (int, float),
}
OPTIONAL_LIST_KEYS = (
    "tests_to_update", "tests_to_add", "tests_to_remove", "documentation_to_update",
    "risks", "assumptions",
)
REQUIRED_OPERATION_KEYS = {"file": str, "operation": str, "reason": str}
OPTIONAL_OPERATION_KEYS = {"symbol": str, "old_content": str, "new_content": str,
                           "old_hash": str, "expected_hash": str}


def extract_json(text: str) -> dict | None:
    """Intenta interpretar `text` como UN objeto JSON. Tolera que el LLM
    haya envuelto la respuesta en un code fence markdown (```json ... ```)
    -- convencion comun de salida de LLM que no cambia el CONTENIDO, solo
    el empaquetado; todo lo demas (prosa antes/despues, JSON parcial,
    multiples objetos) se rechaza devolviendo `None`, nunca se repara."""
    if text is None:
        return None
    candidate = text.strip()
    fence_match = _CODE_FENCE_RE.match(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def validate_raw_schema(raw: dict) -> list[GenerationIssue]:
    """Valida SOLO forma/tipos -- no toca el repo real. Devuelve una lista
    de `GenerationIssue`; cualquier issue de severidad ERROR implica
    rechazo (ver `generator.generate_patch_proposal`)."""
    issues: list[GenerationIssue] = []

    for key, expected_type in REQUIRED_TOP_LEVEL_KEYS.items():
        if key not in raw:
            issues.append(GenerationIssue(
                code="MISSING_FIELD", message=f"Falta el campo obligatorio '{key}'.",
                severity=SEVERITY_ERROR, field=key,
            ))
        elif not isinstance(raw[key], expected_type):
            issues.append(GenerationIssue(
                code="INVALID_TYPE",
                message=f"'{key}' deberia ser {expected_type}, vino {type(raw[key]).__name__}.",
                severity=SEVERITY_ERROR, field=key,
            ))

    if "confidence" in raw and isinstance(raw["confidence"], (int, float)):
        if not 0.0 <= float(raw["confidence"]) <= 1.0:
            issues.append(GenerationIssue(
                code="INVALID_CONFIDENCE", message=f"'confidence' fuera de rango [0,1]: {raw['confidence']}",
                severity=SEVERITY_ERROR, field="confidence",
            ))

    for key in OPTIONAL_LIST_KEYS:
        if key in raw and not isinstance(raw[key], list):
            issues.append(GenerationIssue(
                code="INVALID_TYPE", message=f"'{key}' deberia ser list, vino {type(raw[key]).__name__}.",
                severity=SEVERITY_ERROR, field=key,
            ))

    operations = raw.get("operations")
    if isinstance(operations, list):
        if not operations:
            issues.append(GenerationIssue(
                code="EMPTY_OPERATIONS", message="'operations' esta vacio -- no hay nada que proponer.",
                severity=SEVERITY_WARNING, field="operations",
            ))
        for idx, op in enumerate(operations):
            issues.extend(_validate_operation(op, idx))

    return issues


def _validate_operation(op, idx: int) -> list[GenerationIssue]:
    issues: list[GenerationIssue] = []
    prefix = f"operations[{idx}]"

    if not isinstance(op, dict):
        return [GenerationIssue(
            code="INVALID_OPERATION_TYPE", message=f"{prefix} deberia ser un objeto, vino {type(op).__name__}.",
            severity=SEVERITY_ERROR, field=prefix,
        )]

    for key, expected_type in REQUIRED_OPERATION_KEYS.items():
        if key not in op:
            issues.append(GenerationIssue(
                code="MISSING_OPERATION_FIELD", message=f"{prefix}: falta '{key}'.",
                severity=SEVERITY_ERROR, field=f"{prefix}.{key}",
            ))
        elif not isinstance(op[key], expected_type):
            issues.append(GenerationIssue(
                code="INVALID_OPERATION_FIELD_TYPE",
                message=f"{prefix}.{key} deberia ser {expected_type}, vino {type(op[key]).__name__}.",
                severity=SEVERITY_ERROR, field=f"{prefix}.{key}",
            ))

    if isinstance(op.get("operation"), str) and op["operation"] not in GENERATION_OPERATIONS:
        issues.append(GenerationIssue(
            code="INVALID_OPERATION_VALUE",
            message=f"{prefix}.operation='{op['operation']}' no es una de {sorted(GENERATION_OPERATIONS)}.",
            severity=SEVERITY_ERROR, field=f"{prefix}.operation",
        ))

    for key, expected_type in OPTIONAL_OPERATION_KEYS.items():
        if key in op and op[key] is not None and not isinstance(op[key], expected_type):
            issues.append(GenerationIssue(
                code="INVALID_OPERATION_FIELD_TYPE",
                message=f"{prefix}.{key} deberia ser {expected_type} o null, vino {type(op[key]).__name__}.",
                severity=SEVERITY_ERROR, field=f"{prefix}.{key}",
            ))

    op_type = op.get("operation")
    if op_type == "ADD" and op.get("old_content") not in (None, ""):
        issues.append(GenerationIssue(
            code="UNEXPECTED_OLD_CONTENT",
            message=f"{prefix}: operation=ADD no deberia declarar 'old_content' (no hay nada que reemplazar).",
            severity=SEVERITY_WARNING, field=f"{prefix}.old_content",
        ))
    if op_type == "DELETE" and op.get("new_content") not in (None, ""):
        issues.append(GenerationIssue(
            code="UNEXPECTED_NEW_CONTENT",
            message=f"{prefix}: operation=DELETE no deberia declarar 'new_content'.",
            severity=SEVERITY_WARNING, field=f"{prefix}.new_content",
        ))

    return issues


def has_blocking_issues(issues: list[GenerationIssue]) -> bool:
    return any(issue.severity == SEVERITY_ERROR for issue in issues)
