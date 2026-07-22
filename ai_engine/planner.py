"""
planner.py - Sintel Code Planner (Phase 13)

Implements the 17-step reasoning pipeline that runs BEFORE code generation.
Consults all available intelligence: project map, knowledge graph,
dependency graph, app memory, global memory.

Steps:
  1  Analyze intent
  2  Detect apps
  3  Consult manifests (app memory)
  4  Consult global memory (rules, patterns)
  5  Consult knowledge graph
  6  Consult project map (models, viewsets, endpoints)
  7  Consult documentation (from PROJECT_MAP file references)
  8  Consult frontend (who consumes these endpoints)
  9  Consult tests (what must be updated)
  10 Detect impact (what breaks if X changes)
  11 Generate plan (ordered list of changes)
  12 Validate plan (cross-reference consistency)
  13 Determine task_type (backend / frontend / both)
  14 Build enriched context for LLM
  15 [LLM generates code]
  16 [Guardrails validate]
  17 [Memory/index update post-generation — future]
"""
import json
import logging
import re
from pathlib import Path

from project_map import (
    find_affected_apps, build_impact_context,
    get_models_for_apps, get_viewsets_for_apps,
    get_endpoints_for_apps, get_frontend_consumers,
    get_stores_for_apps, get_serializers_for_apps,
)
from dependency_graph import (
    get_dependency_graph, what_breaks_if_i_change,
    build_impact_analysis_text,
)
from memory_builder import get_memory_context, get_app_memory
try:
    from specialized_retrieval import retrieve_specialized, route_to_indices
    _SPECIALIZED_AVAILABLE = True
except Exception:
    _SPECIALIZED_AVAILABLE = False

try:
    from ai_manifest import manifest_summary
    _MANIFEST_AVAILABLE = True
except Exception:
    _MANIFEST_AVAILABLE = False

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent classifiers
# ---------------------------------------------------------------------------

INTENT_PATTERNS = {
    "create":   re.compile(r"\b(crea|crear|add|agrega|agregar|implement|implementa|nuevo|nueva|new)\b", re.I),
    "update":   re.compile(r"\b(actualiz|update|modific|cambiar|edit|extend|extend)\b", re.I),
    "delete":   re.compile(r"\b(elimin|remov|borr|delet|quitar)\b", re.I),
    "fix":      re.compile(r"\b(fix|corrig|arregl|repair|bug|error|broken)\b", re.I),
    "refactor": re.compile(r"\b(refactor|refactori|reorganiz|limpi|clean)\b", re.I),
    "query":    re.compile(r"\b(lista|list|muestra|show|get|obtén|busca|search|query)\b", re.I),
    "migrate":  re.compile(r"\b(migr|schema|alter|add.+field|remov.+field)\b", re.I),
    "test":     re.compile(r"\b(test|prueba|unittest|pytest|coverage)\b", re.I),
    "document": re.compile(r"\b(document|docstring|readme|comment)\b", re.I),
}

FRONTEND_SIGNALS = re.compile(
    r"\b(vue|component|componente|composable|vista|view|pinia|store|"
    r"template|v-model|v-for|v-if|frontend|vite|bootstrap|bi-|"
    r"ref\(|reactive\(|onmounted|defineprops|defineemits|slot|"
    r"productlist|productform|rentinglist|servicelist|homeview|"
    r"landingview|customerprofile|shopcat|heroSection|modulegrid)\b",
    re.I
)

BACKEND_SIGNALS = re.compile(
    r"\b(django|viewset|serializer|command|selector|model|celery|"
    r"consumer|drf|rest_framework|transaction\.atomic|queryset|"
    r"migration|signal|permission_classes|basecommand|"
    r"management command|task\.delay)\b",
    re.I
)


def detect_intent(task: str) -> list[str]:
    intents = []
    for name, pat in INTENT_PATTERNS.items():
        if pat.search(task):
            intents.append(name)
    return intents or ["unknown"]


def detect_task_type(task: str) -> str:
    fe_score = len(FRONTEND_SIGNALS.findall(task))
    be_score = len(BACKEND_SIGNALS.findall(task))
    if fe_score > be_score:
        return "frontend"
    if be_score > 0:
        return "backend"
    return "backend"


# ---------------------------------------------------------------------------
# Core planner
# ---------------------------------------------------------------------------

class CodePlan:
    """Structured plan produced by the 17-step pipeline."""

    def __init__(self):
        self.intent: list[str]       = []
        self.task_type: str          = "backend"
        self.apps: list[str]         = []
        self.affected_models: list   = []
        self.affected_viewsets: list = []
        self.affected_serializers: list = []
        self.affected_endpoints: list  = []
        self.affected_frontend: list   = []
        self.affected_stores: list     = []
        self.blast_radius: dict        = {}
        self.plan_steps: list[str]     = []
        self.enriched_context: str     = ""
        self.warnings: list[str]       = []

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "task_type": self.task_type,
            "apps": self.apps,
            "affected_models": self.affected_models,
            "affected_viewsets": self.affected_viewsets,
            "affected_serializers": self.affected_serializers,
            "affected_endpoints": self.affected_endpoints,
            "affected_frontend": self.affected_frontend,
            "affected_stores": self.affected_stores,
            "blast_radius": self.blast_radius,
            "plan_steps": self.plan_steps,
            "enriched_context": self.enriched_context,
            "warnings": self.warnings,
        }


def build_plan(task: str, apps_hint: list[str] | None = None) -> CodePlan:
    """
    Execute the 17-step reasoning pipeline.
    Returns a CodePlan with full context and ordered change steps.
    """
    plan = CodePlan()

    # --- STEP 1: Analyze intent -------------------------------------------
    plan.intent    = detect_intent(task)
    plan.task_type = detect_task_type(task)
    logger.info("[planner] Step1 intent=%s type=%s", plan.intent, plan.task_type)

    # --- STEP 2: Detect apps ---------------------------------------------
    detected = find_affected_apps(task)
    plan.apps = list(dict.fromkeys((apps_hint or []) + detected))[:6]
    logger.info("[planner] Step2 apps=%s", plan.apps)

    # --- STEP 3 & 4: Consult app + global memory -------------------------
    memory_ctx = get_memory_context(plan.apps)

    # --- STEP 5: Consult knowledge graph (neighborhood of first entity) ---
    kg_ctx = _get_kg_context(task, plan.apps)

    # --- STEP 6: Consult project map -------------------------------------
    plan.affected_models      = get_models_for_apps(plan.apps)[:12]
    plan.affected_viewsets    = get_viewsets_for_apps(plan.apps)[:8]
    plan.affected_serializers = get_serializers_for_apps(plan.apps)[:8]
    plan.affected_endpoints   = get_endpoints_for_apps(plan.apps)[:10]

    # --- STEP 7: Documentation (already in system prompts / context) ------

    # --- STEP 8 & STEP 9: Frontend + tests -------------------------------
    plan.affected_frontend = get_frontend_consumers(plan.apps)[:8]
    plan.affected_stores   = get_stores_for_apps(plan.apps)[:5]
    dg = get_dependency_graph()
    test_files = []
    for app in plan.apps:
        test_files.extend(dg.get("tests", {}).get(app, []))

    # --- STEP 10: Impact analysis ----------------------------------------
    for app in plan.apps:
        for model_entry in plan.affected_models:
            key = f"{model_entry['app']}.{model_entry['model']}"
            blast = what_breaks_if_i_change(key)
            if blast:
                plan.blast_radius[key] = blast

    # --- STEP 11: Generate plan ------------------------------------------
    plan.plan_steps = _generate_plan_steps(plan, task, test_files)

    # --- STEP 12: Validate plan (consistency checks) ---------------------
    plan.warnings = _validate_plan(plan)

    # --- STEP 14: Build enriched context for LLM -------------------------
    plan.enriched_context = _build_enriched_context(
        task, plan, memory_ctx, kg_ctx
    )

    logger.info("[planner] Plan ready: %d steps, %d warnings, context %d chars",
                len(plan.plan_steps), len(plan.warnings), len(plan.enriched_context))
    return plan


def _get_kg_context(task: str, apps: list[str]) -> str:
    """Try to get KG neighborhood for the main entity mentioned in the task."""
    try:
        from knowledge_graph import get_knowledge_graph, find_node_context
        kg = get_knowledge_graph()
        # Find entity names from task (capitalized words)
        candidates = re.findall(r"\b[A-Z][a-zA-Z]{3,}\b", task)
        for c in candidates:
            matches = kg.find_by_name(c)
            if matches:
                ctx = find_node_context(c, depth=2)
                node = ctx.get("node", {})
                neighbors = ctx.get("neighborhood", {}).get("nodes", [])[:6]
                lines = [f"KG [{node.get('type')}] {node.get('name')} ({node.get('app')})"]
                for n in neighbors:
                    lines.append(f"  - {n.get('type')}: {n.get('name')}")
                return "\n".join(lines)
    except Exception as exc:
        logger.debug("[planner] KG context error: %s", exc)
    return ""


def _generate_plan_steps(plan: CodePlan, task: str, test_files: list[str]) -> list[str]:
    """Generate ordered list of steps the LLM should follow."""
    steps = []
    intent = plan.intent

    if "create" in intent or "update" in intent:
        # Backend
        for model_entry in plan.affected_models[:3]:
            steps.append(f"[Backend] Model {model_entry['model']} in {model_entry['file']}")
        for s in plan.affected_serializers[:3]:
            steps.append(f"[Backend] Serializer {s['serializer']} in {s['file']}")
        for vs in plan.affected_viewsets[:3]:
            steps.append(f"[Backend] ViewSet {vs['viewset']} in {vs['file']}")
        for ep in plan.affected_endpoints[:3]:
            steps.append(f"[Backend] Endpoint {ep['endpoint']} ({'/'.join(ep.get('http_methods', []))})")
        # Migration
        if "create" in intent and plan.affected_models:
            steps.append("[Backend] Generate migration (makemigrations)")
        # Frontend
        for fe in plan.affected_frontend[:3]:
            steps.append(f"[Frontend] {fe['file']} consumes {fe['api_calls'][0]['url'] if fe.get('api_calls') else '?'}")
        for st in plan.affected_stores[:2]:
            steps.append(f"[Frontend] Store {st['store']}")
        # Tests
        if test_files:
            steps.append(f"[Tests] Update: {', '.join(test_files[:2])}")

    elif "delete" in intent or "fix" in intent:
        steps.append("[Analysis] Verify blast radius before modifying")
        for key, blast in list(plan.blast_radius.items())[:2]:
            steps.append(f"[Impact] Changing {key} affects: {list(blast.keys())}")

    elif "query" in intent:
        steps.append("[Backend] Selector method (read-only)")
        if plan.affected_endpoints:
            steps.append(f"[Backend] Endpoint: {plan.affected_endpoints[0]['endpoint']}")

    if not steps:
        steps = ["[Plan] Implementar cambios según contexto de arquitectura"]

    return steps


def _validate_plan(plan: CodePlan) -> list[str]:
    warnings = []
    # Warn if modifying payment without checking confirm_order_payment
    if "payment" in plan.apps and "orders" not in plan.apps:
        warnings.append("Payment changes may affect orders — consider adding 'orders' to scope")
    # Warn if modifying models without mentioning migration
    if plan.affected_models and "migrate" not in plan.intent and "create" not in plan.intent:
        pass  # Only warn for model structural changes
    # Warn if frontend-only but also backend entities detected
    if plan.task_type == "frontend" and plan.affected_viewsets:
        warnings.append("Frontend task but backend ViewSets detected — verify endpoint compatibility")
    return warnings


def _build_enriched_context(
    task: str, plan: CodePlan, memory_ctx: str, kg_ctx: str
) -> str:
    """Build the full enriched context string to inject into the LLM."""
    sections = []

    # Impact summary (PROJECT_MAP)
    impact_ctx = build_impact_context(task, extra_apps=plan.apps)
    if impact_ctx:
        sections.append(impact_ctx)

    # Memory context (global rules + per-app constraints)
    if memory_ctx:
        sections.append(memory_ctx)

    # App manifests (most complete per-app knowledge)
    if _MANIFEST_AVAILABLE:
        manifest_sections = []
        for app in plan.apps[:3]:
            ms = manifest_summary(app)
            if ms:
                manifest_sections.append(ms)
        if manifest_sections:
            sections.append("\n".join(manifest_sections))

    # Specialized retrieval (Phase 5/6) — query specialized indices
    if _SPECIALIZED_AVAILABLE:
        try:
            spec_docs = retrieve_specialized(task)
            if spec_docs:
                spec_txt = "\n---\n".join(d.page_content[:200] for d in spec_docs[:5])
                sections.append(f"=== INDICES ESPECIALIZADOS ===\n{spec_txt}\n=== FIN INDICES ===")
        except Exception:
            pass

    # KG context
    if kg_ctx:
        sections.append(f"=== KNOWLEDGE GRAPH CONTEXT ===\n{kg_ctx}\n=== FIN KG ===")

    # Plan steps
    if plan.plan_steps:
        steps_text = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(plan.plan_steps))
        sections.append(f"=== PLAN DE CAMBIOS ===\n{steps_text}\n=== FIN PLAN ===")

    # Warnings
    if plan.warnings:
        sections.append("=== ADVERTENCIAS ===\n" +
                        "\n".join(f"  - {w}" for w in plan.warnings) +
                        "\n=== FIN ADVERTENCIAS ===")

    return "\n\n".join(sections)
