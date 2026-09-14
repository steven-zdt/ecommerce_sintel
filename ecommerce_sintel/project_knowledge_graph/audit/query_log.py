"""
Query/audit log -- Fase 18 "Observability" (Site Knowledge Graph,
2026-08-10). El plan pide poder responder "que se consulto, que nodo, y
contra que version del grafo" -- este modulo agrega ESE registro (append-
only, JSONL) sin tocar ninguna de las funciones de consulta ya construidas
en Fases 5-13: `graph_sdk/__init__.py` envuelve cada una con
`log_query()`, la logica real de cada consulta no cambia.

**Regla explicita seguida aca (pedida por el propio plan, "no guardar
secretos/tokens")**: se registran los ARGUMENTOS de la consulta (nombres
de entidad/texto libre que el propio usuario/agente ya escribio para
pedir la consulta -- no hay ningun input de este modulo que provenga de
credenciales) y un RESUMEN del resultado (found/counts/ids/names), nunca
el `meta` completo de un nodo. Los nodos `EnvVar` de este grafo (Fase 9)
ya solo guardan NOMBRES de variables de entorno, nunca valores reales (el
`.env.production.example` fuente es una plantilla) -- pero igual se aplica
la misma poda de `meta` a TODOS los tipos de nodo, no solo a `EnvVar`, para
no depender de esa garantia especifica si algun enricher futuro cambia.

El logging es best-effort: si escribir al log falla (disco lleno, permisos),
la consulta original NO debe fallar por eso -- `log_query()` nunca
propaga una excepcion.
"""
import datetime
import json
import logging

from project_knowledge_graph.config import QUERY_AUDIT_LOG_PATH

logger = logging.getLogger(__name__)

MAX_ARG_LEN = 200


def _sanitize_args(args: tuple, kwargs: dict) -> dict:
    """Trunca strings largos (defensivo, evita que un texto libre enorme
    infle el log) y convierte cualquier cosa no-primitiva a `repr()` corto
    en vez de serializarla tal cual -- los argumentos reales de graph_sdk
    son siempre strings de busqueda, pero esto no asume esa garantia."""
    def _clip(v):
        if isinstance(v, str):
            return v if len(v) <= MAX_ARG_LEN else v[:MAX_ARG_LEN] + "...(truncado)"
        if isinstance(v, (int, float, bool)) or v is None:
            return v
        return repr(v)[:MAX_ARG_LEN]

    return {
        "args": [_clip(a) for a in args],
        "kwargs": {k: _clip(v) for k, v in kwargs.items()},
    }


def _summarize_result(result) -> dict:
    """NUNCA persiste el `meta` de un nodo ni el payload completo -- solo
    los campos que ya son seguros de por si (found/counts/ids/names, los
    mismos que ya se muestran en un `print()` de CLI)."""
    if not isinstance(result, dict):
        return {"type": type(result).__name__}

    summary: dict = {}
    if "found" in result:
        summary["found"] = result["found"]
    for key in ("id", "name", "type", "risk", "total_affected", "relevant_nodes"):
        if key in result:
            summary[key] = result[key]
    for key, value in result.items():
        if isinstance(value, list):
            summary[f"{key}_count"] = len(value)
    return summary


def log_query(operation: str, args: tuple, kwargs: dict, result, duration_ms: float,
              graph_snapshot: str | None) -> None:
    """Agrega una linea JSONL. Best-effort -- nunca lanza."""
    try:
        record = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "operation": operation,
            "graph_snapshot": graph_snapshot,
            "duration_ms": round(duration_ms, 2),
            **_sanitize_args(args, kwargs),
            "result": _summarize_result(result),
        }
        with QUERY_AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        logger.warning("No se pudo escribir QUERY_AUDIT_LOG_PATH (best-effort, no fatal)", exc_info=True)


def read_recent_queries(limit: int = 50) -> list[dict]:
    """Lee las ultimas `limit` entradas del log, mas reciente al final
    (mismo orden que el archivo). Lineas corruptas individuales se
    saltean (best-effort en lectura tambien) en vez de romper toda la
    lectura por una linea mala."""
    if not QUERY_AUDIT_LOG_PATH.exists():
        return []
    lines = QUERY_AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()
    records = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def latest_graph_snapshot() -> str | None:
    """Timestamp del snapshot mas reciente (Fase 10, `snapshots/manager.py`)
    -- referencia de contra que build del grafo se corrio la consulta. `None`
    si nunca se corrio un `cli audit` que genere snapshots (caso real en un
    checkout recien clonado)."""
    from project_knowledge_graph.snapshots.manager import latest_snapshot

    snap = latest_snapshot()
    return snap["timestamp"] if snap else None
