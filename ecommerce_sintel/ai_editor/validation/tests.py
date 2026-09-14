"""
`build_test_validation_report()` -- POST-GRAPH 10 "Test Impact Execution"
(rediseno "AI Editor Runtime", 2026-08-11).

Identificar que tests son relevantes para un cambio YA es dato real
disponible en `context.resolution["tests"]` (`direct_tests`/
`indirect_tests`, Fase 7 del Site Knowledge Graph) -- este modulo solo
CLASIFICA (`required`/`recommended`/`optional`) y arma el TEST VALIDATION
REPORT que pide el prompt maestro. **NO ejecuta los tests**: mismo motivo
que Niveles 2-5 de POST-GRAPH 8 -- requieren Django/Postgres/Redis/Docker
que el sandbox parcial actual (POST-GRAPH 7) no provee. `tests_run` queda
`False` explicito, nunca se fabrica un resultado pass/fail.
"""
REQUIRED = "required"
RECOMMENDED = "recommended"
OPTIONAL = "optional"

TESTS_NOT_RUN_NOTE = (
    "No se ejecutan automaticamente -- requieren Django/Postgres/Redis/Docker que el sandbox "
    "actual (copia parcial de archivos, POST-GRAPH 7) no provee. Ejecutar manualmente: "
    "manage.py test <nombre_del_test>."
)


def classify_tests(context) -> dict:
    """`direct_tests` (cubren el target exacto) -> `required`.
    `indirect_tests` (cubren un dependiente del target) -> `recommended`.
    No existe una tercera categoria con datos reales verificables todavia
    -- `optional` queda vacia a proposito, no se fabrica una heuristica
    sin evidencia real detras."""
    context_dict = context.to_dict() if hasattr(context, "to_dict") else dict(context)
    resolution = context_dict.get("resolution") or {}
    tests = resolution.get("tests") or {}
    return {
        REQUIRED: tests.get("direct_tests") or [],
        RECOMMENDED: tests.get("indirect_tests") or [],
        OPTIONAL: [],
    }


def build_test_validation_report(context) -> dict:
    classified = classify_tests(context)
    return {
        "required": [t["name"] for t in classified[REQUIRED]],
        "recommended": [t["name"] for t in classified[RECOMMENDED]],
        "optional": [t["name"] for t in classified[OPTIONAL]],
        "required_count": len(classified[REQUIRED]),
        "recommended_count": len(classified[RECOMMENDED]),
        "tests_run": False,
        "tests_run_note": TESTS_NOT_RUN_NOTE,
        "passed": None,
        "failed": None,
        "skipped": None,
    }
