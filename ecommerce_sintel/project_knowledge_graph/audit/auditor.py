"""
Pipeline explicito de auditoria completa (Fase 8, PLAN_MAESTRO_DE_SEPARACION_
PROJECT_KNOWLEDGE_GRAPH, 2026-08-08). Reemplaza a ai_engine/auditor.py::
ProjectAuditor.run().

[Diferencia deliberada con el original] El auditor.py viejo escondia 8 pasos
distintos (PROJECT_MAP, Knowledge Graph, Dependency Graph, Memory, AI
Manifests, Graph Validator, Graph Visualizer, hash tracker) dentro de un solo
metodo run() de 120 lineas, cada paso con su propio try/except silencioso --
PROJECT_KNOWLEDGE_GRAPH_INVENTORY.md (seccion 2) lo marco como "cadena oculta"
justamente por eso: no habia forma de correr o razonar sobre un paso sin leer
el metodo completo. Aca cada paso es una llamada explicita a una funcion
publica de otro submodulo, en orden, sin heredar estado de instancia entre
pasos (ProjectMapBuilder/KnowledgeGraphBuilder ya no comparten un `self`).

Memory (APP_MEMORY/*.json) y AI Manifests (AI_MANIFESTS/*.json) NO estan aca
a proposito: son artefactos de contexto para el LLM de ai_engine, no analisis
estructural del proyecto -- fuera del alcance de este modulo (Regla 1 del
plan). Si ai_engine necesita encadenarlos despues de un audit_full(), lo hace
desde su propio codigo (Fase 12-14, compatibility layer), no aca.

Uso: python -m project_knowledge_graph.audit.auditor
"""
import json
import logging

from project_knowledge_graph.audit.validator import run_all_validations
from project_knowledge_graph.audit.visualizer import build_html
from project_knowledge_graph.config import GRAPH_VIEW_PATH, VALIDATION_REPORT_PATH
from project_knowledge_graph.dependency_graph.builder import save_dependency_graph
from project_knowledge_graph.incremental.hashing import initialize_hash_tracker
from project_knowledge_graph.knowledge_graph.builder import build_and_save_knowledge_graph
from project_knowledge_graph.project_map.builder import build_project_map
from project_knowledge_graph.snapshots.manager import record_snapshot

logger = logging.getLogger(__name__)


def audit_full(verbose: bool = True) -> dict:
    """Corrida completa: PROJECT_MAP -> Knowledge Graph -> Dependency Graph ->
    validaciones -> visualizacion HTML -> hash tracker -> snapshot. Cada paso
    es defensivo (un fallo en un paso no debe tumbar los anteriores, que ya
    quedaron escritos en disco) salvo PROJECT_MAP, que es la base de todo lo
    demas y debe propagar el error si falla."""
    if verbose:
        print("=== project_knowledge_graph: auditoria completa ===\n")

    pmap = build_project_map(verbose=verbose)

    kg = None
    if verbose:
        print("\nConstruyendo Knowledge Graph...")
    try:
        kg = build_and_save_knowledge_graph()
        if verbose:
            print(f"  Nodos: {len(kg.nodes)}  Aristas: {len(kg.edges)}")
    except Exception:
        logger.exception("[audit_full] Knowledge Graph fallo")

    dg = {}
    if verbose:
        print("Construyendo Dependency Graph...")
    try:
        dg = save_dependency_graph()
        if verbose:
            print(f"  model_dependents: {len(dg.get('model_dependents', {}))}"
                  f"  endpoint_consumers: {len(dg.get('endpoint_consumers', {}))}")
    except Exception:
        logger.exception("[audit_full] Dependency Graph fallo")

    validation = None
    if verbose:
        print("Corriendo validaciones del grafo...")
    try:
        validation = run_all_validations()
        VALIDATION_REPORT_PATH.write_text(
            json.dumps(validation, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        if verbose:
            print(f"  {validation['summary']}")
    except Exception:
        logger.exception("[audit_full] Graph Validator fallo")

    if verbose:
        print("Construyendo visualizacion HTML estatica...")
    try:
        GRAPH_VIEW_PATH.write_text(build_html(), encoding="utf-8")
        if verbose:
            print(f"  {GRAPH_VIEW_PATH.name}: {GRAPH_VIEW_PATH.stat().st_size / 1024:.1f} KB")
    except Exception:
        logger.exception("[audit_full] Graph Visualizer fallo")

    if verbose:
        print("Inicializando hash tracker incremental...")
    hash_count = 0
    try:
        hash_db = initialize_hash_tracker()
        hash_count = len(hash_db)
        if verbose:
            print(f"  {hash_count} archivos rastreados")
    except Exception:
        logger.exception("[audit_full] Hash tracker fallo")

    snapshot = None
    if kg is not None:
        try:
            snapshot = record_snapshot(pmap, kg.to_dict()["stats"], dg, validation, kind="full")
        except Exception:
            logger.exception("[audit_full] Snapshot fallo")

    if verbose:
        print("\nAuditoria completa terminada.")

    return {
        "project_map": pmap,
        "knowledge_graph_stats": kg.to_dict()["stats"] if kg is not None else None,
        "dependency_graph_keys": list(dg.keys()),
        "validation_summary": validation["summary"] if validation else None,
        "hash_tracker_files": hash_count,
        "snapshot": snapshot,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    audit_full()
