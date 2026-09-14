"""
Deteccion incremental de cambios (hashing + git diff) y actualizacion
selectiva de los artefactos derivados (PROJECT_MAP/KNOWLEDGE_GRAPH/
DEPENDENCY_GRAPH). Extraido de ai_engine/incremental_updater.py (Fase 7-8,
PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).
"""
from project_knowledge_graph.incremental.diff import detect_changed_apps
from project_knowledge_graph.incremental.hashing import (
    collect_app_files,
    collect_frontend_files,
    hash_file,
    initialize_hash_tracker,
    load_hash_db,
    save_hash_db,
)
from project_knowledge_graph.incremental.updater import refresh_after_change, update_changed_apps

__all__ = [
    "detect_changed_apps", "collect_app_files", "collect_frontend_files",
    "hash_file", "initialize_hash_tracker", "load_hash_db", "save_hash_db",
    "refresh_after_change", "update_changed_apps",
]
