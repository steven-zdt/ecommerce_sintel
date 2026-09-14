"""
ai_editor.planner -- POST-GRAPH 4 "Change Plan" + POST-GRAPH 5 "Change
Plan Validator" (rediseno "AI Editor Runtime", 2026-08-11). IMPLEMENTADO
(deja de ser scaffold en esta fase).

`build_change_plan()` convierte un `ChangeContext` (POST-GRAPH 3) en una
secuencia de `PlanStep` concretos (file/symbol/lineas/operation/reason/
dependencies/risk/validation) -- sin generar ni aplicar ningun cambio
real todavia (`patch/` sigue sin implementar, ver ese modulo). Solo
lectura y transformacion de datos ya resueltos, cero llamadas nuevas al
grafo.

`validate_plan()` (POST-GRAPH 5) es la primera pieza de `ai_editor` que
lee el filesystem real (via `ai_editor.workspace`, nunca escribe) -- para
detectar drift entre el grafo (una foto del ultimo `cli audit`) y el
estado actual del disco antes de permitir cualquier patch.
"""
from ai_editor.planner.planner import build_change_plan
from ai_editor.planner.schema import STATUS_BLOCKED, STATUS_PLANNED, ChangePlan, PlanStep
from ai_editor.planner.validator import (
    STATUS_APPROVED,
    PlanValidationResult,
    validate_plan,
)

__all__ = [
    "build_change_plan",
    "ChangePlan",
    "PlanStep",
    "STATUS_PLANNED",
    "STATUS_BLOCKED",
    "validate_plan",
    "PlanValidationResult",
    "STATUS_APPROVED",
]
