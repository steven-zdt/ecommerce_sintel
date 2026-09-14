"""
Refresco incremental de la memoria del motor -- APP_MEMORY (memory_builder)
e indices especializados (specialized_retrieval). [SEPARADO 2026-08-10, FASE
0: desacoplamiento ai_engine <-> project_knowledge_graph]

Hasta esta fase, este archivo delegaba PROJECT_MAP/KNOWLEDGE_GRAPH/
DEPENDENCY_GRAPH a project_knowledge_graph/incremental/. Esa delegacion se
retiro por completo: "AI Engine no conoce ni importa project_knowledge_graph"
es ahora una regla arquitectonica (separacion Site Knowledge Graph / AI Editor
Runtime) -- ai_engine debe poder ejecutarse sin que project_knowledge_graph
exista siquiera en disco.

[LIMITACION CONOCIDA, fuera de alcance de FASE 0] memory_builder.py/
ai_manifest.py/specialized_retrieval.py leen `ai_engine/PROJECT_MAP.json`
directo de disco -- ese archivo ya NO se regenera desde ningun lado (el
`auditor.py` que lo escribia se retiro cuando se extrajo project_knowledge_
graph; la delegacion que lo reemplazaba temporalmente tambien se retira aca).
Es una foto estatica del proyecto en el momento en que se genero por ultima
vez. Reconstruir una fuente de datos propia y realmente fresca para ai_engine
(sin volver a depender de project_knowledge_graph) es una decision de
arquitectura que excede el alcance de FASE 0 -- deliberadamente NO se
resuelve aca con un scanner duplicado sin que el usuario lo pida.
"""
import logging
import subprocess
from pathlib import Path

from config import CODEBASE_PATH

logger = logging.getLogger(__name__)

# Mismo set de apps que ai_manifest.py/memory_builder.py asumen implicitamente
# via PROJECT_MAP.json -- duplicado aca a proposito (independencia real de
# project_knowledge_graph, no solo de su codigo Python) para que detect_
# changed_apps() no necesite ninguna fuente compartida con ese modulo.
DJANGO_APPS = [
    "accounts", "cart", "core", "dashboard", "ecommerce",
    "inventory", "kyc", "marketing", "notifications", "operations",
    "organization", "orders", "payment", "quotes", "renting", "security",
    "shared", "shop", "support", "technical_services", "users",
]


def detect_changed_apps() -> tuple[list[str], bool]:
    """Deteccion best-effort via `git diff` -- solo para el reporte informativo
    de /refresh y /refresh/detect. No gatea nada: build_all_memories()/
    build_all_manifests()/get_registry(force_rebuild=True) siempre reconstruyen
    todo, sin importar que apps aparezcan aca."""
    try:
        base_dir = Path(CODEBASE_PATH)
        repo_root = base_dir.parent if base_dir.name == "ecommerce_sintel" else base_dir
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=10,
        )
        if result.returncode != 0:
            return [], False
        apps: set[str] = set()
        frontend_changed = False
        for line in result.stdout.strip().splitlines():
            parts = Path(line).parts
            if len(parts) >= 2 and parts[0] == "ecommerce_sintel":
                if parts[1] in DJANGO_APPS:
                    apps.add(parts[1])
                elif parts[1] == "frontend":
                    frontend_changed = True
        return list(apps), frontend_changed
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("[incremental_updater] deteccion de cambios no disponible: %s", exc)
        return [], False


def _rebuild_ai_engine_artifacts() -> list[str]:
    """Memory + Manifests + indices especializados -- responsabilidad exclusiva
    de ai_engine. Todos reconstruyen TODAS las apps (no hay reconstruccion
    selectiva por app aca, ver limitacion en el docstring del modulo)."""
    updated = []

    try:
        from memory_builder import build_all_memories
        mems = build_all_memories()
        updated.append(f"APP_MEMORY ({len(mems)} archivos)")
    except Exception:
        logger.exception("[incremental_updater] Memory rebuild fallo")

    try:
        from ai_manifest import build_all_manifests
        mfts = build_all_manifests()
        updated.append(f"AI_MANIFESTS ({len(mfts)} archivos)")
    except Exception:
        logger.exception("[incremental_updater] AI Manifest rebuild fallo")

    try:
        from specialized_retrieval import get_registry
        get_registry(force_rebuild=True)
        updated.append("SpecializedIndices (in-memory)")
    except Exception:
        logger.debug("[incremental_updater] Indices especializados se reconstruyen en el proximo request")

    return updated


def update_changed_apps(
    app_names: list[str] | None = None,
    frontend: bool = False,
    force_full: bool = False,
) -> dict:
    """Reconstruye APP_MEMORY/AI_MANIFESTS/indices especializados. `app_names`/
    `frontend`/`force_full` se aceptan por compatibilidad de firma con el
    endpoint /refresh existente, pero no cambian el resultado -- ver
    limitacion en el docstring del modulo (siempre es una reconstruccion
    completa)."""
    if app_names is None:
        app_names, frontend = detect_changed_apps()

    updated = _rebuild_ai_engine_artifacts()
    return {"changed_apps": app_names, "frontend": frontend, "updated": updated}


def refresh_after_change(changed_apps: list[str], frontend_changed: bool = False) -> dict:
    logger.info("[incremental_updater] Auto-refresh tras cambio: apps=%s fe=%s", changed_apps, frontend_changed)
    return update_changed_apps(changed_apps, frontend_changed)


__all__ = ["detect_changed_apps", "update_changed_apps", "refresh_after_change"]
