"""
`compute_metrics()` -- POST-GRAPH 17 "AI Editor Observability" (rediseno
"AI Editor Runtime", 2026-08-11).

Deriva metricas agregadas a partir de los registros YA REALES que
`audit_pipeline_run()` (POST-GRAPH 13) escribio -- 0 logica nueva de
tracking, esto es puramente agregacion sobre datos que ya existen.

**Metricas del prompt maestro que SI son derivables hoy** (documentadas
explicitamente, no las demas -- ver mas abajo cuales NO):
`changes_requested`/`changes_planned`/`changes_approved`/
`changes_rejected`/`changes_promoted`/`patch_failures`/
`validation_failures`/`rollback_count`.

**Metricas que el prompt maestro pide y NO se incluyen aca, honesto, no
fabricadas:**
- `graph_mismatches`/`unexpected_impacts`: dependen de Graph
  Reconciliation (POST-GRAPH 9), que es `NOT_IMPLEMENTED` -- no hay datos
  reales de los que derivar esto, agregar el campo con un valor
  hardcodeado a 0 seria mentir por omision (parece "0 problemas
  detectados" cuando en realidad es "nunca se detecto nada porque nunca
  se busco").
- `graph_resolution_time`/`planning_time`/`patch_time`/`validation_time`:
  `audit_pipeline_run()` no instrumenta timers por etapa -- agregarlos
  requeriria modificar cada fase del pipeline para medir su propia
  duracion, no solo este modulo de metricas. Fuera de alcance de esta
  pasada, documentado como gap real, no resuelto en silencio.
"""
from ai_editor.audit.log import read_recent_operations


def compute_metrics(records: list[dict] | None = None) -> dict:
    """`records` permite pasar una lista ya cargada (util para tests o
    para analizar un subconjunto) -- por default lee TODO el log
    disponible via `read_recent_operations()`."""
    if records is None:
        records = read_recent_operations(limit=100000)

    changes_requested = len(records)
    changes_planned = sum(1 for r in records if r.get("plan_status") == "PLANNED")
    changes_approved = sum(1 for r in records if r.get("approval_decision") == "APPROVE")
    changes_rejected = sum(1 for r in records if r.get("approval_decision") == "REJECT")
    changes_promoted = sum(1 for r in records if r.get("promote_status") == "PROMOTED")
    validation_failures = sum(1 for r in records if r.get("validation_status") == "FAIL")
    patch_failures = sum(r.get("patch_failures") or 0 for r in records)
    rollback_count = sum(1 for r in records if r.get("rollback_status") == "ROLLED_BACK")

    return {
        "changes_requested": changes_requested,
        "changes_planned": changes_planned,
        "changes_approved": changes_approved,
        "changes_rejected": changes_rejected,
        "changes_promoted": changes_promoted,
        "validation_failures": validation_failures,
        "patch_failures": patch_failures,
        "rollback_count": rollback_count,
        "graph_mismatches": None,  # NOT_IMPLEMENTED -- ver docstring del modulo
        "unexpected_impacts": None,  # NOT_IMPLEMENTED -- ver docstring del modulo
        "timing": None,  # NOT_IMPLEMENTED -- sin timers por etapa instrumentados
    }
