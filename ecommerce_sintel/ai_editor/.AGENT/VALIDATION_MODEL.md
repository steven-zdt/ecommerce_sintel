# Modelo de validacion (`ai_editor/validation/`)

El prompt maestro pide 5 niveles de validacion. Estado real, honesto:

| Nivel | Que pide | Estado | Funcion |
|---|---|---|---|
| 1. Sintaxis | Python/Vue/JS compilan | **REAL** | `check_syntax()` |
| 2. Tests | Correr los tests relevantes | **PARCIAL** -- identifica, no ejecuta | `build_test_validation_report()` |
| 3. Contratos | Endpoint/Serializer/schemas siguen consistentes | NOT_IMPLEMENTED | -- |
| 4. Grafo | Reconstruir y comparar antes/despues | NOT_IMPLEMENTED | `reconcile_graph()` |
| 5. Impacto | Recalcular `calculate_change_impact()` | NOT_IMPLEMENTED | -- |

## Por que 3-5 no estan implementados

El sandbox (POST-GRAPH 7) es una copia PARCIAL de archivos -- no tiene
`settings.py`, otras apps Django, migraciones, ni acceso a
Postgres/Redis/Docker. Correr tests reales o reconstruir
`project_knowledge_graph` ahi es estructuralmente imposible con el diseno
actual. Requeriria un sandbox de tipo distinto (copia completa del repo o
git worktree real) mas acceso a Docker -- decision de arquitectura mayor.
**El usuario eligio explicitamente (2026-08-11) mantener el sandbox
parcial** y avanzar el resto del pipeline en vez de construir esa
infraestructura.

## Nivel 1 -- Sintaxis (`syntax.py`)

```python
check_syntax(sandbox_root: Path, relative_path: str) -> tuple[bool, str]
```

- `.py`: `ast.parse()` real (stdlib, sin dependencias).
- `.js`/`.ts`: `node --check <archivo>` (shell-out seguro, `--check`
  SOLO parsea, nunca ejecuta).
- `.vue`: extrae el bloque `<script>` con una regex PROPIA (no importa
  nada de `project_knowledge_graph.scanner`) y lo valida con `node
  --check`. El `<template>` no se valida a este nivel (no hay parser
  real de Vue SFC disponible).
- Otras extensiones: se omiten (`True`, no es un fallo).

`run_validation(sandbox, plan)` agrega el resultado de Nivel 1 sobre
todos los archivos del plan.

## Nivel 2 -- Test Impact (`tests.py`) -- parcial pero real

```python
build_test_validation_report(context) -> dict
```

Clasifica `direct_tests` -> `required`, `indirect_tests` -> `recommended`
(dato YA real del grafo, Fase 7 del Site Knowledge Graph). `tests_run`
SIEMPRE `False` -- nunca se ejecutan, mismo motivo de infraestructura.
`optional` queda vacia (no hay una tercera categoria con evidencia real
detras).

## Graph Reconciliation (`reconciliation.py`) -- 2 motivos, no 1

```python
reconcile_graph(plan) -> ReconciliationResult  # siempre NOT_IMPLEMENTED
```

1. Mismo limite del sandbox parcial.
2. **Motivo adicional**: reconciliar existe para detectar impacto NO
   previsto que introdujo un patch generado autonomamente -- pero
   `ai_editor.patch` no genera contenido real (cada `PatchOperation` la
   construye un humano o un test). No hay todavia un escenario real de
   "sorpresa" que reconciliar.

## Verificado real

Sobre el sandbox real de Renting: 8/8 archivos pasan Nivel 1 limpio
(incluye 6 archivos JS/Vue reales via `node --check`). Inyectando
sintaxis Python realmente rota via `apply_operation()`, `run_validation()`
la detecta correctamente con el numero de linea real.
