"""
Unit/integration tests para ai_editor/generation/context.py -- FASE 26
"Source Context Builder" (plan "AI Change Proposal Engine", 2026-08-11).

Usa el mismo target real que el resto de la suite de `ai_editor`
(`EquipmentViewSet.check_availability`, renting) -- no un fixture
sintetico -- para verificar contra datos reales del grafo/repo que el
contexto ensamblado es minimo (no el archivo completo) y trazable.
"""
from ai_editor.generation.context import (
    build_architecture_context,
    build_generation_context,
    build_source_context,
    _extract_global_rules,
    _read_symbol_source,
)
from ai_editor.intent.schema import ChangeIntent
from ai_editor.planner import build_change_plan
from ai_editor.resolver import resolve_change_context
from ai_editor.workspace import WORKSPACE_ROOT, resolve_repo_file

TARGET_ENTITY = "EquipmentViewSet.check_availability"


def _real_context_and_plan(scope=("backend",)):
    intent = ChangeIntent(
        id="test-context-builder", request="Permitir alquiler por horas.",
        domain="renting", intent="modify_availability", entities=[TARGET_ENTITY],
        scope=list(scope), confidence=0.9, ambiguities=[], status="RESOLVED",
    )
    context = resolve_change_context(intent)
    plan = build_change_plan(context)
    return intent, context, plan


def test_read_symbol_source_reads_only_the_requested_range_plus_margin_not_the_whole_file():
    """El archivo real (`ai_editor/workspace.py`) es corto pero de todas
    formas confirma la regla: el contenido devuelto es acotado, con un
    margen chico, no el archivo entero linea por linea sin limite."""
    result = _read_symbol_source("ai_editor/workspace.py", 47, 52)
    assert result is not None
    assert result["context_lines"] != result["requested_lines"]
    start, end = (int(x) for x in result["context_lines"].split("-"))
    assert end - start < 60  # rango + margen, no el archivo completo


def test_read_symbol_source_returns_none_for_file_that_does_not_exist():
    assert _read_symbol_source("this/does/not/exist.py", 1, 5) is None


def test_read_symbol_source_handles_node_without_line_range():
    result = _read_symbol_source("ai_editor/workspace.py", None, None)
    assert result["source"] is None
    assert result["requested_lines"] is None


def test_build_source_context_reads_source_for_modify_and_non_doc_review_run_steps():
    """FASE 38 "Cross-Stack Generation" (2026-08-11, relajado con
    confirmacion explicita del usuario) extendio esto mas alla de solo
    MODIFY -- ahora tambien lee REVIEW (no documentacion) y RUN, los
    mismos steps que `proposal_validator` ahora acepta como escribibles.
    Documentacion (`.md`) sigue excluida."""
    _, _, plan = _real_context_and_plan()
    result = build_source_context(plan)
    plan_dict = plan.to_dict()
    writable_steps = {
        s["step"] for s in plan_dict["steps"]
        if s.get("file") and (
            s["operation"] == "MODIFY"
            or (s["operation"] in ("REVIEW", "RUN") and not s["file"].endswith(".md"))
        )
    }
    assert set(result["targets"].keys()) == writable_steps
    doc_steps = {s["step"] for s in plan_dict["steps"] if (s.get("file") or "").endswith(".md")}
    assert not doc_steps & set(result["targets"].keys())
    # "Nunca el archivo completo" se prueba mejor por-archivo (algunos
    # simbolos reales, ej. un composable grande, pueden legitimamente
    # abarcar la mayor parte de un archivo chico) -- lo real y verificable
    # es que el rango leido nunca excede MARGIN_BEFORE/AFTER alrededor del
    # rango DECLARADO del propio simbolo (cubierto en detalle por
    # test_read_symbol_source_reads_only_the_requested_range_plus_margin_
    # not_the_whole_file). Aca solo se confirma que ningun target lee mas
    # lineas de las que el archivo real tiene.
    for target in result["targets"].values():
        if target["source"] is None:
            continue
        real_path = resolve_repo_file(target["file"])
        total_lines_in_file = len(real_path.read_text(encoding="utf-8", errors="replace").splitlines())
        assert len(target["source"].splitlines()) <= total_lines_in_file


def test_build_architecture_context_resolves_real_app_doc_via_claude_md():
    """Defecto que este builder evita: los nombres de doc de arquitectura
    NO son uniformes entre apps (ver CLAUDE.md real) -- se resuelve via la
    tabla de ruteo real, no una convencion de nombre adivinada."""
    _, context, _ = _real_context_and_plan()
    result = build_architecture_context(context)
    assert result["app"] == "renting"
    assert result["architecture_doc_path"] == "renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md"
    assert result["architecture_doc_excerpt"]
    assert (WORKSPACE_ROOT / result["architecture_doc_path"]).exists()


def test_build_architecture_context_resolves_app_rows_with_an_annotation_in_claude_md():
    """FASE 61.8 (plan "AI Model Qualification") -- gap real encontrado: la fila de
    `organization` en CLAUDE.md real trae una anotacion entre celdas
    (`*(nueva, en construccion)*`) que la regex original no toleraba, dejando
    `architecture_doc_path`/`architecture_doc_excerpt` en `None` para esa app (y `seo`,
    mismo patron) sin que nada lo señalara -- corregido tolerando texto sin `|` entre
    el cierre de la primera celda y el separador."""
    from ai_editor.intent.schema import ChangeIntent
    from ai_editor.resolver import resolve_change_context

    intent = ChangeIntent(
        id="x", request="x", domain="organization", intent="x",
        entities=["SocialLink"], scope=["backend"], confidence=1.0, ambiguities=[],
        status="RESOLVED",
    )
    context = resolve_change_context(intent)
    result = build_architecture_context(context)

    assert result["app"] == "organization"
    assert result["architecture_doc_path"] == "organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md"
    assert result["architecture_doc_excerpt"]
    assert (WORKSPACE_ROOT / result["architecture_doc_path"]).exists()


def test_extract_global_rules_reads_five_real_rules_from_memory_md():
    rules = _extract_global_rules()
    assert len(rules) == 5
    assert any("Service Layer" in r for r in rules)
    assert any("Soft-Delete" in r for r in rules)


def test_build_generation_context_assembles_all_six_fields_with_real_data():
    intent, context, plan = _real_context_and_plan(scope=("backend", "frontend"))
    request = build_generation_context(intent, context, plan)
    d = request.to_dict()

    assert d["change_intent"]["id"] == "test-context-builder"
    assert d["change_plan"]["status"] == "PLANNED"
    assert d["graph_context"]["found"] is True
    assert d["source_context"]["targets"]
    assert "required_count" in d["test_context"]
    assert d["architecture_context"]["app"] == "renting"


def test_build_generation_context_never_ships_the_full_knowledge_graph():
    """Regla del prompt maestro (seccion 5): nunca 9.575/20.335 nodos/aristas
    como contexto -- `graph_context` debe ser el packet COMPACTADO
    (decenas de nodos), no el grafo completo."""
    intent, context, plan = _real_context_and_plan()
    request = build_generation_context(intent, context, plan)
    graph_context = request.to_dict()["graph_context"]
    assert graph_context["stats"]["relevant_nodes"] < graph_context["stats"]["total_graph_nodes"]
    assert graph_context["stats"]["relevant_nodes"] < 200
