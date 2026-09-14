"""
CLI de project_knowledge_graph (Fase 11, PLAN_MAESTRO_DE_SEPARACION_PROJECT_
KNOWLEDGE_GRAPH, 2026-08-08). Punto de entrada unico para todas las
operaciones que antes requerian saber que script de ai_engine correr
(auditor.py, graph_validator.py, graph_visualizer.py, incremental_updater.py
cada uno con su propio `if __name__ == "__main__"` y su propia forma de
invocarse).

Uso:
  python -m project_knowledge_graph.cli audit
  python -m project_knowledge_graph.cli incremental [--full]
  python -m project_knowledge_graph.cli validate
  python -m project_knowledge_graph.cli viz
  python -m project_knowledge_graph.cli node <nombre> [--depth N]
  python -m project_knowledge_graph.cli impact <entidad>
  python -m project_knowledge_graph.cli app-summary <app>
  python -m project_knowledge_graph.cli snapshots [--limit N]
  python -m project_knowledge_graph.cli data-flow <Model|Model.campo>
  python -m project_knowledge_graph.cli execution <simbolo>
  python -m project_knowledge_graph.cli tests-for <Symbol|Endpoint|Model>
  python -m project_knowledge_graph.cli docs-for <query de texto libre>
  python -m project_knowledge_graph.cli config-for <query>
  python -m project_knowledge_graph.cli change-impact <target>
  python -m project_knowledge_graph.cli resolve-change <request>
  python -m project_knowledge_graph.cli context-packet <request>
  python -m project_knowledge_graph.cli changed-symbols
  python -m project_knowledge_graph.cli validation-report
  python -m project_knowledge_graph.cli query-log [--limit N]
"""
import argparse
import json
import sys


def _cmd_audit(args) -> int:
    from project_knowledge_graph.audit.auditor import audit_full

    audit_full(verbose=not args.quiet)
    return 0


def _cmd_incremental(args) -> int:
    from project_knowledge_graph.incremental.updater import update_changed_apps

    result = update_changed_apps(force_full=args.full)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_validate(args) -> int:
    from project_knowledge_graph.audit.validator import run_all_validations
    from project_knowledge_graph.config import VALIDATION_REPORT_PATH

    result = run_all_validations()
    VALIDATION_REPORT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
    print(f"\nReporte completo: {VALIDATION_REPORT_PATH}")
    return 0


def _cmd_viz(args) -> int:
    from project_knowledge_graph.audit.visualizer import build_html
    from project_knowledge_graph.config import GRAPH_VIEW_PATH

    GRAPH_VIEW_PATH.write_text(build_html(), encoding="utf-8")
    print(f"Escrito: {GRAPH_VIEW_PATH} ({GRAPH_VIEW_PATH.stat().st_size / 1024:.1f} KB)")
    return 0


def _cmd_node(args) -> int:
    from project_knowledge_graph.knowledge_graph.query import find_node_context

    result = find_node_context(args.name, depth=args.depth)
    if not result.get("found"):
        print(f"No se encontro ningun nodo que coincida con '{args.name}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_impact(args) -> int:
    from project_knowledge_graph.dependency_graph.impact import build_impact_analysis_text

    text = build_impact_analysis_text(args.entity)
    print(text or f"Sin impacto conocido para '{args.entity}' (no encontrado o sin dependientes).")
    return 0


def _cmd_app_summary(args) -> int:
    from project_knowledge_graph.dependency_graph.query import get_app_summary

    print(json.dumps(get_app_summary(args.app), indent=2, ensure_ascii=False))
    return 0


def _cmd_data_flow(args) -> int:
    """Fase 5 'Data Flow Graph' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import trace_data_flow

    result = trace_data_flow(args.target)
    if not result.get("found"):
        print(f"No se encontro ningun Model que coincida con '{args.target}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_execution(args) -> int:
    """Fase 6 'Execution Graph' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import trace_execution

    result = trace_execution(args.start)
    if not result.get("found"):
        print(f"No se encontro ningun Symbol que coincida con '{args.start}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_tests_for(args) -> int:
    """Fase 7 'Test Graph' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import find_tests_for_change

    result = find_tests_for_change(args.target)
    if not result.get("found"):
        print(f"No se encontro ningun Symbol/Endpoint/Model que coincida con '{args.target}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_docs_for(args) -> int:
    """Fase 8 'Documentation Graph' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import find_docs_for_change

    result = find_docs_for_change(args.query)
    if not result.get("found"):
        print(f"Sin documentos que coincidan con '{args.query}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_config_for(args) -> int:
    """Fase 9 'Configuration/Infrastructure Graph' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import find_configuration_for

    result = find_configuration_for(args.query)
    if not result.get("found"):
        print(f"Sin configuracion que coincida con '{args.query}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_change_impact(args) -> int:
    """Fase 10 'Change Graph' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import calculate_change_impact

    result = calculate_change_impact(args.target)
    if not result.get("found"):
        print(f"No se encontro ninguna entidad que coincida con '{args.target}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_resolve_change(args) -> int:
    """Fase 11 'Change Resolver' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import resolve_change

    result = resolve_change(args.request)
    if not result.get("found"):
        print(f"No se encontro ninguna entidad que coincida con '{args.request}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_context_packet(args) -> int:
    """Fase 12 'Graph Context Packet' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.knowledge_graph.query import build_graph_context_packet

    result = build_graph_context_packet(args.request)
    if not result.get("found"):
        print(f"No se encontro ninguna entidad que coincida con '{args.request}'")
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def _cmd_changed_symbols(args) -> int:
    """Fase 15 'Incremental Semantic Graph' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.incremental.diff import detect_changed_symbols

    symbols = detect_changed_symbols()
    print(json.dumps(symbols, indent=2, ensure_ascii=False))
    if not symbols:
        print("(sin cambios detectados via git diff, o git no disponible)")
    return 0


def _cmd_validation_report(args) -> int:
    """Fase 16 'Change Validation' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.audit.change_validation import build_change_validation_report

    report = build_change_validation_report()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["risk"] != "HIGH" else 1


def _cmd_query_log(args) -> int:
    """Fase 18 'Observability' (Site Knowledge Graph, 2026-08-10)."""
    from project_knowledge_graph.audit.query_log import read_recent_queries

    records = read_recent_queries(args.limit)
    print(json.dumps(records, indent=2, ensure_ascii=False))
    if not records:
        print("(sin consultas registradas via graph_sdk todavia)")
    return 0


def _cmd_snapshots(args) -> int:
    from project_knowledge_graph.snapshots.manager import list_snapshots

    snapshots = list_snapshots()[-args.limit:]
    print(json.dumps(snapshots, indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="project-graph",
        description="Analisis estructural del proyecto Sintel E-Commerce (independiente de ai_engine).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_audit = sub.add_parser("audit", help="Auditoria completa: PROJECT_MAP + KG + DG + validaciones + viz + hash tracker")
    p_audit.add_argument("--quiet", action="store_true", help="No imprimir progreso paso a paso")
    p_audit.set_defaults(func=_cmd_audit)

    p_incr = sub.add_parser("incremental", help="Actualiza solo las apps/frontend que cambiaron (git diff o hash)")
    p_incr.add_argument("--full", action="store_true", help="Forzar rebuild completo en vez de deteccion incremental")
    p_incr.set_defaults(func=_cmd_incremental)

    p_val = sub.add_parser("validate", help="Corre las 6 validaciones sobre el Knowledge Graph ya generado")
    p_val.set_defaults(func=_cmd_validate)

    p_viz = sub.add_parser("viz", help="Genera GRAPH_VIEW.html a partir del Knowledge Graph ya generado")
    p_viz.set_defaults(func=_cmd_viz)

    p_node = sub.add_parser("node", help="Vecindario de un nodo del Knowledge Graph por nombre")
    p_node.add_argument("name")
    p_node.add_argument("--depth", type=int, default=2)
    p_node.set_defaults(func=_cmd_node)

    p_impact = sub.add_parser("impact", help="Analisis de impacto legible: que se rompe si cambia esta entidad")
    p_impact.add_argument("entity")
    p_impact.set_defaults(func=_cmd_impact)

    p_app = sub.add_parser("app-summary", help="Modelos/viewsets/endpoints/tests de una app")
    p_app.add_argument("app")
    p_app.set_defaults(func=_cmd_app_summary)

    p_snap = sub.add_parser("snapshots", help="Historial de corridas (conteos, no el grafo completo)")
    p_snap.add_argument("--limit", type=int, default=10)
    p_snap.set_defaults(func=_cmd_snapshots)

    p_flow = sub.add_parser("data-flow", help="Traza database->serializer->API->frontend->component para un Model o Model.campo")
    p_flow.add_argument("target", help="Nombre de Model, ej. 'Product' o 'Product.image'")
    p_flow.set_defaults(func=_cmd_data_flow)

    p_exec = sub.add_parser("execution", help="Traza ExecutionPath: FUNCTION->API->VIEW->SERVICE->DATABASE->EVENT->TASK desde un Symbol")
    p_exec.add_argument("start", help="Nombre de Symbol de partida, ej. 'dispatch_notification'")
    p_exec.set_defaults(func=_cmd_execution)

    p_tests = sub.add_parser("tests-for", help="Que tests ejecutar si cambia este Symbol/Endpoint/Model")
    p_tests.add_argument("target", help="Nombre de Symbol, Endpoint o Model")
    p_tests.set_defaults(func=_cmd_tests_for)

    p_docs = sub.add_parser("docs-for", help="Que documentacion es relevante para un cambio (texto libre o nombre exacto)")
    p_docs.add_argument("query", help="Texto libre, ej. 'renting availability', o nombre exacto de Symbol/Endpoint/Model/File/App")
    p_docs.set_defaults(func=_cmd_docs_for)

    p_config = sub.add_parser("config-for", help="Donde esta configurada una funcionalidad: env/docker/nginx/settings")
    p_config.add_argument("query", help="Texto libre, ej. 'AI_SUPPORT_CHAT' o 'sintel_ai'")
    p_config.set_defaults(func=_cmd_config_for)

    p_change = sub.add_parser("change-impact", help="Impacto categorizado (directo/indirecto/frontend/backend/contract/test/doc/config) de cambiar una entidad")
    p_change.add_argument("target", help="Nombre exacto o aproximado de la entidad a cambiar")
    p_change.set_defaults(func=_cmd_change_impact)

    p_resolve = sub.add_parser("resolve-change", help="Envelope completo de Change Resolver: target/files/symbols/contracts/tests/docs/config/risk/orden")
    p_resolve.add_argument("request", help="Nombre real de una entidad (Symbol/Model/Endpoint/...) -- sin parsing de lenguaje natural")
    p_resolve.set_defaults(func=_cmd_resolve_change)

    p_packet = sub.add_parser("context-packet", help="Subgrafo relevante comprimido (para consumo LLM) de un cambio")
    p_packet.add_argument("request", help="Nombre real de una entidad")
    p_packet.set_defaults(func=_cmd_context_packet)

    p_changed = sub.add_parser("changed-symbols", help="Symbol nodes reales tocados por el git diff actual (-U0 HEAD)")
    p_changed.set_defaults(func=_cmd_changed_symbols)

    p_valreport = sub.add_parser("validation-report", help="Change Validation Report: impacto + tests requeridos + consistencia del grafo/contratos, sobre el git diff actual")
    p_valreport.set_defaults(func=_cmd_validation_report)

    p_qlog = sub.add_parser("query-log", help="Historial de consultas reales via graph_sdk (Fase 18 Observability)")
    p_qlog.add_argument("--limit", type=int, default=50)
    p_qlog.set_defaults(func=_cmd_query_log)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
