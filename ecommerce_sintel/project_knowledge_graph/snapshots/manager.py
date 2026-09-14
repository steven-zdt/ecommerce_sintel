"""
Snapshot Manager -- historial ligero de cada full rebuild (Fase 10, PLAN_
MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).

No existia en el ai_engine original: auditor.py sobreescribia PROJECT_MAP.json/
KNOWLEDGE_GRAPH.json/DEPENDENCY_GRAPH.json en cada corrida sin dejar rastro de
corridas anteriores -- no habia forma de responder "cuando crecio el grafo",
"cuando fue el ultimo full rebuild" o "que conteos tenia el proyecto la semana
pasada" sin buscar en el historial de git de esos JSON.

Guarda SOLO metadata liviana (conteos, timestamp, resumen de validacion) en
SNAPSHOT_META.json -- nunca una copia del grafo completo, eso ya vive
versionado en PROJECT_MAP.json/KNOWLEDGE_GRAPH.json/DEPENDENCY_GRAPH.json.
"""
import datetime
import json

from project_knowledge_graph.config import SNAPSHOT_META_PATH

MAX_SNAPSHOTS = 50


def _load_snapshots() -> list[dict]:
    if not SNAPSHOT_META_PATH.exists():
        return []
    try:
        return json.loads(SNAPSHOT_META_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save_snapshots(snapshots: list[dict]) -> None:
    SNAPSHOT_META_PATH.write_text(
        json.dumps(snapshots[-MAX_SNAPSHOTS:], indent=2, ensure_ascii=False), encoding="utf-8"
    )


def record_snapshot(pmap: dict, kg_stats: dict, dg: dict, validation: dict | None = None,
                     kind: str = "full") -> dict:
    """Agrega una entrada de snapshot y persiste. `kind` es 'full' (rebuild
    completo) o 'incremental' (update_changed_apps)."""
    snapshot = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kind": kind,
        "apps_audited": len(pmap.get("apps", {})),
        "endpoints": len(pmap.get("endpoints", [])),
        "frontend_files": sum(len(v) for v in pmap.get("frontend", {}).values()),
        "kg_nodes": kg_stats.get("total_nodes", 0),
        "kg_edges": kg_stats.get("total_edges", 0),
        "kg_node_types": kg_stats.get("node_types", {}),
        "dg_change_impact_entries": len(dg.get("change_impact", {})),
        "validation_summary": validation.get("summary") if validation else None,
    }
    snapshots = _load_snapshots()
    snapshots.append(snapshot)
    _save_snapshots(snapshots)
    return snapshot


def list_snapshots() -> list[dict]:
    return _load_snapshots()


def latest_snapshot() -> dict | None:
    snapshots = _load_snapshots()
    return snapshots[-1] if snapshots else None
