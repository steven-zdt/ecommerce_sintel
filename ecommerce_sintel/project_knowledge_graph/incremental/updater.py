"""
Orquestacion de update selectivo: reauditar solo lo que cambio y reconstruir
los artefactos derivados. Extraido de ai_engine/incremental_updater.py::
update_changed_apps/_update_project_map/_rebuild_derived_artifacts/_full_rebuild
/refresh_after_change (Fase 8, PLAN_MAESTRO_DE_SEPARACION_PROJECT_KNOWLEDGE_
GRAPH, 2026-08-08).

[Diferencia deliberada con el original] La version vieja hacia
`from auditor import ProjectAuditor` y despues alcanzaba atributos/metodos de
UNA instancia (`auditor.project_map = pmap; auditor.build_cross_refs()`) --
acoplamiento que solo funcionaba porque ambos modulos vivian en el mismo
namespace plano y auditor.py exponia su estado interno sin querer. Aca
ProjectMapBuilder ya es una clase publica de otro submodulo (project_map/
builder.py) con la misma forma (build_cross_refs()/build_endpoints_list()
leen y escriben self.project_map), asi que la reasignacion sigue siendo
necesaria pero deja de ser un acceso "no documentado" a un modulo hermano --
es la API publica normal de ProjectMapBuilder.

Memory (APP_MEMORY/*.json) y specialized_retrieval NO se reconstruyen aca --
son responsabilidad de ai_engine, no de este modulo (Regla 1 del plan). El
ai_engine que llame a esto puede encadenarlos despues si los necesita.
"""
import datetime
import json
import logging

from project_knowledge_graph.config import DJANGO_APPS, PROJECT_MAP_PATH
from project_knowledge_graph.dependency_graph.builder import save_dependency_graph
from project_knowledge_graph.incremental.diff import detect_changed_apps
from project_knowledge_graph.knowledge_graph.builder import build_and_save_knowledge_graph
from project_knowledge_graph.project_map.builder import ProjectMapBuilder, build_project_map
from project_knowledge_graph.snapshots.manager import record_snapshot

logger = logging.getLogger(__name__)


def update_changed_apps(
    app_names: list[str] | None = None,
    frontend: bool = False,
    force_full: bool = False,
) -> dict:
    """Actualiza solo las apps que cambiaron. Devuelve un resumen de lo
    actualizado."""
    if force_full:
        logger.info("[incremental] Full rebuild forzado")
        return _full_rebuild()

    if app_names is None:
        app_names, frontend = detect_changed_apps()

    if not app_names and not frontend:
        logger.info("[incremental] Sin cambios detectados")
        return {"changed_apps": [], "frontend": False, "updated": []}

    logger.info("[incremental] Apps cambiadas=%s frontend=%s", app_names, frontend)
    updated: list[str] = []

    if app_names or frontend:
        updated.extend(_update_project_map(app_names, frontend))

    updated.extend(_rebuild_derived_artifacts())

    return {"changed_apps": app_names, "frontend": frontend, "updated": updated}


def _update_project_map(app_names: list[str], frontend: bool) -> list[str]:
    if not PROJECT_MAP_PATH.exists():
        logger.warning("[incremental] PROJECT_MAP.json no existe -- corriendo audit completo")
        _full_rebuild()
        return ["PROJECT_MAP.json (full rebuild)"]

    pmap = json.loads(PROJECT_MAP_PATH.read_text(encoding="utf-8"))
    updated = []
    builder = ProjectMapBuilder()
    builder.project_map = pmap

    if app_names:
        from project_knowledge_graph.scanner.project_scanner import scan_app

        for app_name in app_names:
            if app_name not in DJANGO_APPS:
                continue
            logger.info("[incremental] Re-auditando app: %s", app_name)
            app_data = scan_app(app_name, DJANGO_APPS)
            if app_data:
                pmap["apps"][app_name] = app_data
                updated.append(f"apps.{app_name}")

        builder.build_cross_refs()
        builder.build_endpoints_list()

    if frontend:
        from project_knowledge_graph.scanner.project_scanner import scan_frontend

        logger.info("[incremental] Re-auditando frontend")
        pmap["frontend"] = scan_frontend()
        updated.append("frontend")
        builder.build_cross_refs()

    pmap["meta"]["last_incremental_update"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    pmap["meta"]["last_changed_apps"] = app_names

    PROJECT_MAP_PATH.write_text(json.dumps(pmap, indent=2, ensure_ascii=False), encoding="utf-8")
    updated.append("PROJECT_MAP.json")
    logger.info("[incremental] PROJECT_MAP.json actualizado")
    return updated


def _rebuild_derived_artifacts() -> list[str]:
    updated = []

    try:
        kg = build_and_save_knowledge_graph()
        logger.info("[incremental] KG reconstruido: %d nodos %d aristas", len(kg.nodes), len(kg.edges))
        updated.append("KNOWLEDGE_GRAPH.json")
    except Exception:
        logger.exception("[incremental] KG rebuild fallo")

    try:
        save_dependency_graph()
        updated.append("DEPENDENCY_GRAPH.json")
    except Exception:
        logger.exception("[incremental] DG rebuild fallo")

    return updated


def _full_rebuild() -> dict:
    """Full rebuild -- equivalente a project_knowledge_graph.audit.audit_full()."""
    from project_knowledge_graph.audit.auditor import audit_full

    audit_full(verbose=False)
    return {
        "changed_apps": DJANGO_APPS,
        "frontend": True,
        "updated": ["PROJECT_MAP.json", "KNOWLEDGE_GRAPH.json", "DEPENDENCY_GRAPH.json",
                    "GRAPH_VALIDATION_REPORT.json", "GRAPH_VIEW.html", ".file_hashes.json"],
    }


def refresh_after_change(changed_apps: list[str], frontend_changed: bool = False) -> dict:
    """Punto de integracion para ai_engine: llamar despues de generar/editar
    codigo para mantener el knowledge base sincronizado."""
    logger.info("[incremental] Auto-refresh tras cambio: apps=%s fe=%s", changed_apps, frontend_changed)
    return update_changed_apps(changed_apps, frontend_changed)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    result = update_changed_apps()
    print("Resultado de update incremental:")
    print(f"  Apps cambiadas: {result['changed_apps']}")
    print(f"  Frontend cambiado: {result['frontend']}")
    print(f"  Actualizado: {result['updated']}")
