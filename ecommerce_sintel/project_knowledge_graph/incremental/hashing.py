"""
Tracking de hashes de archivo para deteccion incremental de cambios.
Extraido de ai_engine/incremental_updater.py (Fase 7, PLAN_MAESTRO_DE_
SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).

[Regla 1 del plan] A diferencia del original, estas funciones son publicas
(sin guion bajo) a proposito: auditor.py (via incremental_updater.py) alcanzaba
las funciones PRIVADAS de este modulo para inicializar el hash tracker en cada
corrida completa -- el acoplamiento "oculto" que el inventario fisico
(PROJECT_KNOWLEDGE_GRAPH_INVENTORY.md, seccion 2) marco para resolver aca.
"""
import hashlib
import json
from pathlib import Path

from project_knowledge_graph.config import BASE_DIR, DJANGO_APPS, HASH_DB_PATH


def hash_file(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def load_hash_db() -> dict[str, str]:
    if HASH_DB_PATH.exists():
        return json.loads(HASH_DB_PATH.read_text(encoding="utf-8"))
    return {}


def save_hash_db(db: dict[str, str]) -> None:
    HASH_DB_PATH.write_text(json.dumps(db, indent=2), encoding="utf-8")


def collect_app_files(app_name: str) -> list[Path]:
    app_dir = BASE_DIR / app_name
    if not app_dir.exists():
        return []
    return [p for p in app_dir.rglob("*.py") if "__pycache__" not in str(p)]


def collect_frontend_files() -> list[Path]:
    fe_dir = BASE_DIR / "frontend" / "src"
    if not fe_dir.exists():
        return []
    result = []
    for ext in ("*.vue", "*.js", "*.ts"):
        result.extend(fe_dir.rglob(ext))
    return [p for p in result if "node_modules" not in str(p) and "dist" not in str(p)]


def initialize_hash_tracker() -> dict[str, str]:
    """Recalcula el hash de todos los archivos rastreados (apps Django +
    frontend) y persiste el baseline completo. Usado por una corrida completa
    (full rebuild) para dejar el tracker incremental listo para la proxima
    corrida selectiva."""
    db: dict[str, str] = {}
    for app_name in DJANGO_APPS:
        for path in collect_app_files(app_name):
            db[str(path)] = hash_file(path)
    for path in collect_frontend_files():
        db[str(path)] = hash_file(path)
    save_hash_db(db)
    return db
