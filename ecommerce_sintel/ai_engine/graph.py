import logging
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_chroma import Chroma
from langchain_core.documents import Document

from guardrails import SintelArchitectureGuard
from guardrails_frontend import SintelFrontendGuard
from chains import build_editor_chain, build_feedback_prompt
from chains_frontend import build_frontend_chain, build_frontend_feedback_prompt
from retrievers import detect_apps_from_text, detect_task_type
from planner import build_plan
from config import VALIDATION_MAX_RETRIES

logger = logging.getLogger(__name__)


class SintelCodeState(TypedDict):
    task: str
    task_type: str          # "backend" | "frontend"
    apps: list[str]
    impact_context: str     # enriched context from 17-step planner
    plan_steps: list        # ordered change steps from planner
    plan_warnings: list     # plan consistency warnings
    retrieved_context: str
    generated_code: str
    validation_report: dict
    iteration: int
    final_code: str
    escalated: bool
    escalation_reason: str


# ─── Nodos ───────────────────────────────────────────────────────────────────

def node_analyze_impact(state: SintelCodeState) -> SintelCodeState:
    """
    Nodo de planificacion: ejecuta el pipeline de 17 pasos antes de la generacion.
    Consulta PROJECT_MAP, Knowledge Graph, Dependency Graph, App Memory y Global Memory.
    Construye un plan de cambios y contexto enriquecido para el LLM.
    """
    task = state.get("task", "")
    existing_apps = state.get("apps", [])

    plan = build_plan(task, apps_hint=existing_apps)

    state["apps"]          = plan.apps
    state["task_type"]     = state.get("task_type") or plan.task_type
    state["impact_context"]= plan.enriched_context
    state["plan_steps"]    = plan.plan_steps
    state["plan_warnings"] = plan.warnings

    logger.info("[graph] plan_code: apps=%s steps=%d type=%s",
                plan.apps, len(plan.plan_steps), plan.task_type)
    return state


def node_generate_code(state: SintelCodeState, editor_chain, frontend_chain) -> SintelCodeState:
    task = state.get("task", "")
    task_type = state.get("task_type", "backend")
    impact_context = state.get("impact_context", "")
    logger.info("[graph] Generando %s — iteracion %d", task_type, state.get("iteration", 0) + 1)
    chain = frontend_chain if task_type == "frontend" else editor_chain
    try:
        # Inject impact context into the task so the chain sees it
        enriched_task = task
        if impact_context and "IMPACTO EN EL PROYECTO" not in task:
            enriched_task = f"{task}\n\n{impact_context}"
        code = chain.invoke({"task": enriched_task, "apps": state.get("apps", [])})
        state["generated_code"] = code
    except Exception as exc:
        logger.error("[graph] Error generando codigo: %s", exc)
        state["generated_code"] = ""
        state["escalated"] = True
        state["escalation_reason"] = f"LLM error durante generacion: {exc}"
    return state


def node_validate_code(state: SintelCodeState) -> SintelCodeState:
    code = state.get("generated_code", "")
    app_ctx = state.get("apps", [""])[0] if state.get("apps") else ""
    task_type = state.get("task_type", "backend")

    if task_type == "frontend":
        report = SintelFrontendGuard.validate(code, app_ctx)
    else:
        report = SintelArchitectureGuard.validate(code, app_ctx)

    state["validation_report"] = {
        "passed": report.passed,
        "violations": [v.model_dump() for v in report.violations],
        "warnings": [w.model_dump() for w in report.warnings],
    }
    state["iteration"] = state.get("iteration", 0) + 1

    if report.passed:
        state["final_code"] = code
        logger.info("[graph] Validacion PASS (iter %d)", state["iteration"])
    else:
        violation_ids = [v.rule_id for v in report.violations]
        logger.warning("[graph] Validacion FAIL iter=%d violations=%s", state["iteration"], violation_ids)

        if task_type == "frontend":
            feedback = build_frontend_feedback_prompt(
                state["task"],
                [v.model_dump() for v in report.violations],
                state["iteration"],
            )
        else:
            feedback = build_feedback_prompt(
                state["task"],
                [v.model_dump() for v in report.violations],
                state["iteration"],
            )
        state["task"] = feedback

    return state


def node_emit_result(state: SintelCodeState) -> SintelCodeState:
    logger.info("[graph] Emitiendo resultado final PASS")
    return state


def node_escalate(state: SintelCodeState) -> SintelCodeState:
    report = state.get("validation_report", {})
    violations = report.get("violations", [])
    reason = "; ".join(f"[{v['rule_id']}] {v['description'][:80]}" for v in violations)
    state["escalated"] = True
    state["escalation_reason"] = (
        f"Superado limite de reintentos ({VALIDATION_MAX_RETRIES}). "
        f"Violaciones persistentes: {reason}"
    )
    logger.error("[graph] ESCALADO: %s", state["escalation_reason"])
    return state


def route_after_validation(state: SintelCodeState) -> str:
    report = state.get("validation_report", {})
    if report.get("passed", False):
        return "emit_result"
    if state.get("iteration", 0) < VALIDATION_MAX_RETRIES:
        return "generate_code"
    return "escalate"


# ─── Builder del grafo ───────────────────────────────────────────────────────

def build_sintel_graph(vectorstore: Chroma, all_docs: list[Document], llm):
    editor_chain   = build_editor_chain(vectorstore, all_docs, llm)
    fe_chain       = build_frontend_chain(vectorstore, all_docs, llm)

    def _gen_node(state):
        return node_generate_code(state, editor_chain, fe_chain)

    g = StateGraph(SintelCodeState)
    g.add_node("analyze_impact", node_analyze_impact)
    g.add_node("generate_code",  _gen_node)
    g.add_node("validate_code",  node_validate_code)
    g.add_node("emit_result",    node_emit_result)
    g.add_node("escalate",       node_escalate)

    g.set_entry_point("analyze_impact")
    g.add_edge("analyze_impact", "generate_code")
    g.add_edge("generate_code",  "validate_code")
    g.add_conditional_edges(
        "validate_code",
        route_after_validation,
        {
            "emit_result":   "emit_result",
            "generate_code": "generate_code",
            "escalate":      "escalate",
        },
    )
    g.add_edge("emit_result", END)
    g.add_edge("escalate",    END)

    return g.compile()


def run_code_generation(
    task: str,
    vectorstore: Chroma,
    all_docs: list[Document],
    llm,
    apps: list[str] | None = None,
    task_type: str | None = None,
) -> dict:
    graph = build_sintel_graph(vectorstore, all_docs, llm)

    resolved_type = task_type or detect_task_type(task)

    initial_state: SintelCodeState = {
        "task": task,
        "task_type": resolved_type,
        "apps": apps or detect_apps_from_text(task),
        "impact_context": "",
        "plan_steps": [],
        "plan_warnings": [],
        "retrieved_context": "",
        "generated_code": "",
        "validation_report": {},
        "iteration": 0,
        "final_code": "",
        "escalated": False,
        "escalation_reason": "",
    }

    final_state = graph.invoke(initial_state)
    return {
        "final_code":         final_state.get("final_code", ""),
        "escalated":          final_state.get("escalated", False),
        "escalation_reason":  final_state.get("escalation_reason", ""),
        "iterations":         final_state.get("iteration", 0),
        "validation_report":  final_state.get("validation_report", {}),
        "apps_detected":      final_state.get("apps", []),
        "impact_context":     final_state.get("impact_context", ""),
        "plan_steps":         final_state.get("plan_steps", []),
        "plan_warnings":      final_state.get("plan_warnings", []),
    }
