"""
ai_editor.validation -- POST-GRAPH 8 "Validation Engine" (rediseno "AI
Editor Runtime", 2026-08-11). IMPLEMENTADO PARCIALMENTE.

Solo el NIVEL 1 (sintaxis, `run_validation()`/`check_syntax()`) es real:
Python via `ast.parse()`, JS/TS via `node --check` (shell-out seguro, solo
parsea), Vue extrayendo el bloque `<script>` con una regex propia (no
importa nada de `project_knowledge_graph`, que es "internal"). Los
Niveles 2-5 (tests reales, contratos, grafo antes/despues, impacto)
quedan `NOT_IMPLEMENTED` explicito -- el sandbox actual (copia parcial de
archivos) no provee la infraestructura necesaria, ver `engine.py` para el
detalle completo de por que.

POST-GRAPH 9 "Graph Reconciliation": `reconcile_graph()` -- tambien
`NOT_IMPLEMENTED` explicito, ver `reconciliation.py` (2 motivos reales,
no solo el del sandbox parcial).

POST-GRAPH 10 "Test Impact Execution": `build_test_validation_report()`
-- SI es real: clasifica los tests ya identificados (`direct_tests`/
`indirect_tests`, Fase 7) en `required`/`recommended`, pero NO los
ejecuta (mismo motivo del sandbox parcial).
"""
from ai_editor.validation.engine import LEVELS_2_TO_5_REASON, ValidationReport, run_validation
from ai_editor.validation.reconciliation import (
    RECONCILIATION_NOT_IMPLEMENTED_REASON,
    ReconciliationResult,
    reconcile_graph,
)
from ai_editor.validation.syntax import check_syntax
from ai_editor.validation.tests import build_test_validation_report, classify_tests

__all__ = [
    "run_validation",
    "check_syntax",
    "ValidationReport",
    "LEVELS_2_TO_5_REASON",
    "reconcile_graph",
    "ReconciliationResult",
    "RECONCILIATION_NOT_IMPLEMENTED_REASON",
    "build_test_validation_report",
    "classify_tests",
]
