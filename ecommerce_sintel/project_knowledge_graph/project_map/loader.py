"""
Carga PROJECT_MAP.json con cache. Extraido de ai_engine/project_map.py
(Fase 4, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_GRAPH, 2026-08-08).
"""
import json
import logging
from functools import lru_cache

from project_knowledge_graph.config import PROJECT_MAP_PATH

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_map() -> dict:
    if not PROJECT_MAP_PATH.exists():
        logger.warning("[project_map] PROJECT_MAP.json no encontrado en %s", PROJECT_MAP_PATH)
        return {}
    try:
        data = json.loads(PROJECT_MAP_PATH.read_text(encoding="utf-8"))
        logger.info("[project_map] Cargado PROJECT_MAP.json (%d apps, %d endpoints)",
                    len(data.get("apps", {})), len(data.get("endpoints", [])))
        return data
    except Exception as exc:
        logger.error("[project_map] Fallo al cargar: %s", exc)
        return {}


def get_map(force_reload: bool = False) -> dict:
    if force_reload:
        _load_map.cache_clear()
    return _load_map()
