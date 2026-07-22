"""
incremental_updater.py - Incremental Knowledge Base Updater (Phase 11)

Detects which files changed (by file hash), re-audits only the affected apps,
and updates selectively:
  - PROJECT_MAP.json  (only changed apps)
  - KNOWLEDGE_GRAPH.json
  - DEPENDENCY_GRAPH.json
  - APP_MEMORY/{app}.json
  - GLOBAL_MEMORY.json  (only if critical files changed)

Supports both git-diff based detection and hash-based detection.
Run as: python ai_engine/incremental_updater.py
Or call update_changed_apps(['shop', 'orders']) for targeted updates.
"""
import hashlib
import json
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

AI_ENGINE_DIR = Path(__file__).resolve().parent
BASE_DIR      = AI_ENGINE_DIR.parent / "ecommerce_sintel"
MAP_PATH      = AI_ENGINE_DIR / "PROJECT_MAP.json"
HASH_DB_PATH  = AI_ENGINE_DIR / ".file_hashes.json"

DJANGO_APPS = [
    "accounts", "cart", "core", "dashboard", "ecommerce",
    "inventory", "kyc", "marketing", "notifications", "operations", "organization", "orders",
    "payment", "quotes", "renting", "security", "shipping", "shop", "support",
    "technical_services", "users",
]


# ---------------------------------------------------------------------------
# File hash tracking
# ---------------------------------------------------------------------------

def _hash_file(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def _load_hash_db() -> dict[str, str]:
    if HASH_DB_PATH.exists():
        return json.loads(HASH_DB_PATH.read_text(encoding="utf-8"))
    return {}


def _save_hash_db(db: dict[str, str]):
    HASH_DB_PATH.write_text(json.dumps(db, indent=2), encoding="utf-8")


def _collect_app_files(app_name: str) -> list[Path]:
    app_dir = BASE_DIR / app_name
    if not app_dir.exists():
        return []
    return [p for p in app_dir.rglob("*.py") if "__pycache__" not in str(p)]


def _collect_frontend_files() -> list[Path]:
    fe_dir = BASE_DIR / "frontend" / "src"
    if not fe_dir.exists():
        return []
    result = []
    for ext in ("*.vue", "*.js", "*.ts"):
        result.extend(fe_dir.rglob(ext))
    return [p for p in result if "node_modules" not in str(p) and "dist" not in str(p)]


def detect_changed_apps() -> tuple[list[str], bool]:
    """
    Returns (changed_app_names, frontend_changed).
    Uses git diff if available, falls back to file-hash comparison.
    """
    # Try git diff first
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True, text=True, cwd=str(BASE_DIR.parent), timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            return _parse_git_diff(result.stdout.strip().splitlines())
    except Exception:
        pass

    # Fallback: hash-based detection
    return _detect_via_hashes()


def _parse_git_diff(changed_files: list[str]) -> tuple[list[str], bool]:
    apps = set()
    frontend_changed = False
    for f in changed_files:
        parts = Path(f).parts
        if not parts:
            continue
        # ecommerce_sintel/{app}/... structure
        if len(parts) >= 2 and parts[0] == "ecommerce_sintel":
            if parts[1] in DJANGO_APPS:
                apps.add(parts[1])
            elif parts[1] == "frontend":
                frontend_changed = True
    return list(apps), frontend_changed


def _detect_via_hashes() -> tuple[list[str], bool]:
    hash_db = _load_hash_db()
    new_db: dict[str, str] = {}
    changed_apps: set[str] = set()
    frontend_changed = False

    for app_name in DJANGO_APPS:
        for path in _collect_app_files(app_name):
            key = str(path)
            new_hash = _hash_file(path)
            new_db[key] = new_hash
            if hash_db.get(key) != new_hash:
                changed_apps.add(app_name)

    for path in _collect_frontend_files():
        key = str(path)
        new_hash = _hash_file(path)
        new_db[key] = new_hash
        if hash_db.get(key) != new_hash:
            frontend_changed = True

    _save_hash_db(new_db)
    return list(changed_apps), frontend_changed


# ---------------------------------------------------------------------------
# Selective update
# ---------------------------------------------------------------------------

def update_changed_apps(
    app_names: list[str] | None = None,
    frontend: bool = False,
    force_full: bool = False,
) -> dict:
    """
    Updates only the apps that changed.
    Returns a summary of what was updated.
    """
    if force_full:
        logger.info("[incremental] Force full rebuild")
        return _full_rebuild()

    if app_names is None:
        app_names, frontend = detect_changed_apps()

    if not app_names and not frontend:
        logger.info("[incremental] No changes detected")
        return {"changed_apps": [], "frontend": False, "updated": []}

    logger.info("[incremental] Changed apps=%s frontend=%s", app_names, frontend)
    updated: list[str] = []

    # 1. Re-audit changed apps in PROJECT_MAP
    if app_names or frontend:
        updated.extend(_update_project_map(app_names, frontend))

    # 2. Rebuild KG, DG, Memory from updated PROJECT_MAP
    updated.extend(_rebuild_derived_artifacts())

    return {
        "changed_apps": app_names,
        "frontend": frontend,
        "updated": updated,
    }


def _update_project_map(app_names: list[str], frontend: bool) -> list[str]:
    if not MAP_PATH.exists():
        logger.warning("[incremental] PROJECT_MAP.json missing — running full audit")
        _full_rebuild()
        return ["PROJECT_MAP.json (full rebuild)"]

    pmap = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    updated = []

    if app_names:
        # Import auditor to re-audit only changed apps
        import sys
        sys.path.insert(0, str(AI_ENGINE_DIR))
        from auditor import ProjectAuditor, DJANGO_APPS as ALL_APPS

        auditor = ProjectAuditor()
        for app_name in app_names:
            if app_name not in ALL_APPS:
                continue
            logger.info("[incremental] Re-auditing app: %s", app_name)
            app_data = auditor.audit_app(app_name)
            if app_data:
                pmap["apps"][app_name] = app_data
                updated.append(f"apps.{app_name}")

        # Rebuild cross-refs and endpoints for updated apps
        auditor.project_map = pmap
        auditor.build_cross_refs()
        auditor.build_endpoints_list()
        pmap = auditor.project_map

    if frontend:
        logger.info("[incremental] Re-auditing frontend")
        from auditor import ProjectAuditor
        auditor = ProjectAuditor()
        fe_data = auditor.audit_frontend()
        pmap["frontend"] = fe_data
        updated.append("frontend")

        # Rebuild cross-refs since frontend changed
        auditor.project_map = pmap
        auditor.build_cross_refs()
        pmap = auditor.project_map

    import datetime
    pmap["meta"]["last_incremental_update"] = datetime.datetime.now(datetime.UTC).isoformat()
    pmap["meta"]["last_changed_apps"] = app_names

    MAP_PATH.write_text(json.dumps(pmap, indent=2, ensure_ascii=False), encoding="utf-8")
    updated.append("PROJECT_MAP.json")
    logger.info("[incremental] PROJECT_MAP.json updated")
    return updated


def _rebuild_derived_artifacts() -> list[str]:
    updated = []

    # Invalidate cached modules
    import sys
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("knowledge_graph", "dependency_graph", "memory_builder",
                        "project_map", "specialized_retrieval"):
            del sys.modules[mod_name]

    # KG
    try:
        from knowledge_graph import build_and_save_knowledge_graph, KG_PATH
        kg = build_and_save_knowledge_graph()
        logger.info("[incremental] KG rebuilt: %d nodes %d edges", len(kg.nodes), len(kg.edges))
        updated.append("KNOWLEDGE_GRAPH.json")
    except Exception as exc:
        logger.error("[incremental] KG rebuild failed: %s", exc)

    # DG
    try:
        from dependency_graph import save_dependency_graph
        save_dependency_graph()
        updated.append("DEPENDENCY_GRAPH.json")
    except Exception as exc:
        logger.error("[incremental] DG rebuild failed: %s", exc)

    # Memory
    try:
        from memory_builder import build_all_memories
        mems = build_all_memories()
        updated.append(f"APP_MEMORY ({len(mems)} files)")
    except Exception as exc:
        logger.error("[incremental] Memory rebuild failed: %s", exc)

    # Specialized indices (in-memory, rebuilt on next request)
    try:
        from specialized_retrieval import get_registry
        get_registry(force_rebuild=True)
        updated.append("SpecializedIndices (in-memory)")
    except Exception as exc:
        logger.debug("[incremental] Specialized indices will rebuild on next request: %s", exc)

    return updated


def _full_rebuild() -> dict:
    """Full rebuild — equivalent to running auditor.py."""
    import sys
    sys.path.insert(0, str(AI_ENGINE_DIR))
    from auditor import ProjectAuditor
    auditor = ProjectAuditor()
    auditor.run()
    return {
        "changed_apps": DJANGO_APPS,
        "frontend": True,
        "updated": ["PROJECT_MAP.json", "KNOWLEDGE_GRAPH.json",
                    "DEPENDENCY_GRAPH.json", "APP_MEMORY/*", "GLOBAL_MEMORY.json"],
    }


# ---------------------------------------------------------------------------
# AI Engine integration: refresh current state post-generation
# ---------------------------------------------------------------------------

def refresh_after_change(changed_apps: list[str], frontend_changed: bool = False) -> dict:
    """
    Called after code generation to keep knowledge base in sync.
    Phase 14: auto-learning hook.
    """
    logger.info("[incremental] Auto-refresh after change: apps=%s fe=%s",
                changed_apps, frontend_changed)
    return update_changed_apps(changed_apps, frontend_changed)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = update_changed_apps()
    print("Incremental update result:")
    print(f"  Changed apps: {result['changed_apps']}")
    print(f"  Frontend changed: {result['frontend']}")
    print(f"  Updated: {result['updated']}")
