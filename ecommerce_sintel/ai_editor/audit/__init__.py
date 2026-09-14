"""
ai_editor.audit -- POST-GRAPH 13 "Change Audit" + POST-GRAPH 17
"Observability" (rediseno "AI Editor Runtime", 2026-08-11). NUEVO
submodulo (mismo criterio que `llm/` y `approval/` -- el prompt lo pide
explicito, no encaja limpio en los 7 originales).

`log_change_operation()`/`read_recent_operations()`: registro append-only
propio, nunca persiste secretos. `audit_pipeline_run()`: compone el
registro completo de una corrida a partir de los objetos reales de cada
fase del pipeline. `compute_metrics()` (POST-GRAPH 17): agrega metricas
sobre los registros ya existentes -- ver `metrics.py` para el detalle de
que metricas del prompt maestro SI son derivables hoy y cuales no.
"""
from ai_editor.audit.log import AUDIT_LOG_PATH, log_change_operation, read_recent_operations
from ai_editor.audit.metrics import compute_metrics
from ai_editor.audit.pipeline_audit import audit_pipeline_run

__all__ = [
    "log_change_operation",
    "read_recent_operations",
    "audit_pipeline_run",
    "compute_metrics",
    "AUDIT_LOG_PATH",
]
