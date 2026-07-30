"""
API REST del motor cognitivo Sintel AI Engine.
Expone endpoints para generacion de codigo validado y validacion directa.

Arranque:
    uvicorn main:app --host 0.0.0.0 --port 8100 --reload
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import httpx

from auth import get_validated_token, decode_django_jwt
from action_graph import run_action_chat

from embeddings_factory import get_embeddings
from vectorstore_factory import get_vectorstore
from llm_factory import get_llm
from loaders import load_all_documents
from splitters import split_all
from guardrails import SintelArchitectureGuard, ValidationReport
from graph import run_code_generation
from retrievers import detect_task_type
from project_map import build_impact_report, build_impact_context
from dependency_graph import get_dependency_graph, what_breaks_if_i_change, build_impact_analysis_text
from memory_builder import get_global_memory, get_app_memory
from planner import build_plan
from specialized_retrieval import retrieve_with_routing, get_registry
from ai_manifest import build_all_manifests, get_manifest
from incremental_updater import update_changed_apps, detect_changed_apps
from gateway import ai_router
from config import DOCS_SPECS_PATH, CODEBASE_PATH, LLM_PROVIDER, LLM_MODEL, EMBEDDING_MODEL, OLLAMA_BASE_URL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

_STATE: dict = {}


async def _ensure_ollama_models() -> None:
    """Pre-carga los modelos LLM y embedding en Ollama para evitar timeout en primera petición."""
    models = list({LLM_MODEL, EMBEDDING_MODEL})
    async with httpx.AsyncClient(timeout=300) as client:
        for model in models:
            try:
                logger.info("[startup] Pre-cargando modelo Ollama '%s'...", model)
                resp = await client.post(
                    f"{OLLAMA_BASE_URL}/api/pull",
                    json={"name": model, "stream": False},
                )
                resp.raise_for_status()
                logger.info("[startup] Modelo '%s' listo.", model)
            except Exception as exc:
                logger.warning("[startup] No se pudo pre-cargar '%s': %s", model, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] Inicializando motor cognitivo...")
    try:
        if LLM_PROVIDER == "ollama":
            await _ensure_ollama_models()
        embeddings       = get_embeddings()
        vectorstore      = get_vectorstore(embeddings)
        llm              = get_llm()
        raw_docs         = load_all_documents(DOCS_SPECS_PATH, CODEBASE_PATH)
        all_chunks       = split_all(raw_docs)
        _STATE["vectorstore"] = vectorstore
        _STATE["all_docs"]    = all_chunks
        _STATE["llm"]         = llm
        logger.info("[startup] Motor listo. Chunks en memoria: %d", len(all_chunks))

        # Pre-build specialized indices (Phase 5/6)
        try:
            registry = get_registry()
            logger.info("[startup] Specialized indices ready: %s", registry.stats())
        except Exception as exc:
            logger.warning("[startup] Specialized indices not ready: %s", exc)

        # Pre-build AI manifests (Phase 12)
        try:
            manifests = build_all_manifests()
            logger.info("[startup] AI manifests built: %d apps", len(manifests))
        except Exception as exc:
            logger.warning("[startup] AI manifests error: %s", exc)
    except Exception as exc:
        logger.error("[startup] Error critico durante init: %s", exc)
        raise
    yield
    logger.info("[shutdown] Motor cognitivo detenido.")


app = FastAPI(
    title="Sintel AI Engine",
    version="1.0.0",
    description="Motor cognitivo LangChain + LangGraph para Sintel E-Commerce REST v5",
    lifespan=lifespan,
)

# AI Gateway (Fase 1 AI Core): rutas /api/v1/ai/* con JWT de Django obligatorio.
# Los endpoints historicos de generacion de codigo de abajo no cambian.
app.include_router(ai_router)


# ─── Schemas de request/response ─────────────────────────────────────────────

class GenerateRequest(BaseModel):
    task: str
    apps: list[str] | None = None
    task_type: str | None = None   # "frontend" | "backend" | None (auto-detect)


class GenerateResponse(BaseModel):
    final_code: str
    escalated: bool
    escalation_reason: str
    iterations: int
    apps_detected: list[str]
    task_type: str
    validation_report: dict
    impact_context: str
    plan_steps: list
    plan_warnings: list


class PlanRequest(BaseModel):
    task: str
    apps: list[str] | None = None


class PlanResponse(BaseModel):
    intent: list[str]
    task_type: str
    apps: list[str]
    plan_steps: list[str]
    warnings: list[str]
    enriched_context: str
    affected_models: list
    affected_endpoints: list
    affected_frontend: list


class MemoryRequest(BaseModel):
    app: str | None = None


class BreakageRequest(BaseModel):
    entity: str   # e.g. "shop.Product", "ProductSerializer"


class RefreshRequest(BaseModel):
    apps: list[str] | None = None
    frontend: bool = False
    force_full: bool = False


class SearchRequest(BaseModel):
    query: str
    index: str | None = None  # optional: force a specific index name


class ImpactRequest(BaseModel):
    task: str
    apps: list[str] | None = None


class ImpactResponse(BaseModel):
    apps: list[str]
    models: list[dict]
    serializers: list[dict]
    viewsets: list[dict]
    endpoints: list[dict]
    frontend_files: list[dict]
    stores: list[dict]
    services: list[dict]
    impact_summary: str


class ValidateRequest(BaseModel):
    code: str
    app_context: str = ""


class ValidateResponse(BaseModel):
    passed: bool
    violations: list[dict]
    warnings: list[dict]


# ─── Endpoints ───────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None
    # Fase 4: resolucion explicita de una confirmacion pendiente (tambien se
    # acepta un mensaje "si"/"no" simple en el mismo hilo).
    confirm: bool | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    intent: str
    agent: str | None = None
    tool_calls: list
    tool_results: list
    needs_confirmation: bool = False
    confirmation: dict | None = None
    response: str
    # Fase 8 AI Core: telemetria del turno (ver ai_engine/observability.py::TurnMetrics),
    # antes solo se emitia a un log JSON y se descartaba.
    metrics: dict | None = None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, token: str = Depends(get_validated_token)):
    """
    Action Graph (Fase 3 AI Core): el LLM decide que capability de LECTURA
    usar y responde con datos reales del usuario autenticado. No reemplaza
    /generate -- es el grafo paralelo de acciones de negocio.
    """
    if not _STATE.get("llm"):
        raise HTTPException(503, "Motor no inicializado. Esperar al lifespan startup.")
    payload = decode_django_jwt(token)
    result = await run_action_chat(
        message=req.message,
        conversation_id=req.conversation_id,
        token=token,
        user_id=payload["user_id"],
        llm=_STATE["llm"],
        vectorstore=_STATE.get("vectorstore"),
        all_docs=_STATE.get("all_docs", []),
        confirm=req.confirm,
    )
    return ChatResponse(**result)


@app.get("/health")
async def health():
    chunks_count = len(_STATE.get("all_docs", []))
    return {
        "status": "ok",
        "chunks_indexed": chunks_count,
        "vectorstore": "chromadb",
    }


@app.post("/generate", response_model=GenerateResponse)
async def generate_code(req: GenerateRequest):
    if not _STATE.get("vectorstore"):
        raise HTTPException(503, "Motor no inicializado. Esperar al lifespan startup.")

    resolved_type = req.task_type or detect_task_type(req.task)
    result = run_code_generation(
        task=req.task,
        vectorstore=_STATE["vectorstore"],
        all_docs=_STATE["all_docs"],
        llm=_STATE["llm"],
        apps=req.apps,
        task_type=resolved_type,
    )
    result["task_type"] = resolved_type
    result.setdefault("impact_context", "")
    result.setdefault("plan_steps", [])
    result.setdefault("plan_warnings", [])
    return GenerateResponse(**result)


@app.post("/validate", response_model=ValidateResponse)
async def validate_code(req: ValidateRequest):
    report: ValidationReport = SintelArchitectureGuard.validate(req.code, req.app_context)
    return ValidateResponse(
        passed=report.passed,
        violations=[v.model_dump() for v in report.violations],
        warnings=[w.model_dump() for w in report.warnings],
    )


@app.post("/impact", response_model=ImpactResponse)
async def analyze_impact(req: ImpactRequest):
    """
    Analiza que componentes del proyecto (modelos, viewsets, endpoints, frontend)
    se ven afectados por una tarea dada. No genera codigo — solo devuelve el mapa.
    Util para que el AI copilot frontend muestre al usuario el impacto ANTES de generar.
    """
    report = build_impact_report(req.task, extra_apps=req.apps)
    summary = build_impact_context(req.task, extra_apps=req.apps)
    return ImpactResponse(
        apps=report["apps"],
        models=report["models"],
        serializers=report["serializers"],
        viewsets=report["viewsets"],
        endpoints=report["endpoints"],
        frontend_files=report["frontend_files"],
        stores=report["stores"],
        services=report["services"],
        impact_summary=summary,
    )


@app.post("/plan", response_model=PlanResponse)
async def plan_code(req: PlanRequest):
    """
    Ejecuta el pipeline de 17 pasos de razonamiento y devuelve el plan.
    NO genera codigo — devuelve el plan para revision antes de generar.
    """
    plan = build_plan(req.task, apps_hint=req.apps)
    return PlanResponse(
        intent=plan.intent,
        task_type=plan.task_type,
        apps=plan.apps,
        plan_steps=plan.plan_steps,
        warnings=plan.warnings,
        enriched_context=plan.enriched_context,
        affected_models=plan.affected_models,
        affected_endpoints=plan.affected_endpoints,
        affected_frontend=plan.affected_frontend,
    )


@app.post("/breakage")
async def analyze_breakage(req: BreakageRequest):
    """
    Responde: que se rompe si cambio la entidad X?
    Ej: POST /breakage {"entity": "shop.Product"}
    """
    blast = what_breaks_if_i_change(req.entity)
    text = build_impact_analysis_text(req.entity)
    return {"entity": req.entity, "blast_radius": blast, "summary": text}


@app.get("/memory")
async def get_memory(app: str | None = None):
    """
    Devuelve la memoria del proyecto.
    GET /memory          -> global memory
    GET /memory?app=shop -> per-app memory
    """
    if app:
        return get_app_memory(app)
    return get_global_memory()


@app.get("/graph/node/{entity_name}")
async def graph_node(entity_name: str, depth: int = 2):
    """
    Devuelve el vecindario del knowledge graph para una entidad.
    GET /graph/node/Product?depth=2
    """
    try:
        from knowledge_graph import find_node_context
        return find_node_context(entity_name, depth=depth)
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/graph/impact/{entity_name}")
async def graph_impact(entity_name: str):
    """
    Devuelve la cadena de impacto transitivo si se modifica entity_name.
    GET /graph/impact/Product
    """
    try:
        from knowledge_graph import impact_chain
        return {"entity": entity_name, "impact_chain": impact_chain(entity_name)}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.post("/search")
async def specialized_search(req: SearchRequest):
    """
    Busca en los indices especializados (Phase 5/6).
    Ruta automaticamente al mejor indice segun el tipo de query.
    GET /search {"query": "como funciona ProductSerializer"}
    """
    indices = [req.index] if req.index else None
    result = retrieve_with_routing(req.query)
    return result


@app.get("/indices")
async def list_indices():
    """Lista todos los indices especializados y su tamano (numero de documentos)."""
    try:
        registry = get_registry()
        return {"indices": registry.stats()}
    except Exception as exc:
        raise HTTPException(500, str(exc))


@app.get("/manifest/{app_name}")
async def app_manifest(app_name: str):
    """
    Devuelve el AI_MANIFEST completo de una app.
    GET /manifest/shop
    """
    manifest = get_manifest(app_name)
    if manifest.get("error"):
        raise HTTPException(404, manifest["error"])
    return manifest


@app.post("/refresh")
async def refresh_knowledge_base(req: RefreshRequest):
    """
    Actualiza incrementalmente la base de conocimiento (Phase 11).
    Detecta cambios automaticamente o acepta lista de apps cambiadas.

    [EXTENDIDO 2026-07-30, AUDITORIA/14_GRAPHIFY_KNOWLEDGE_GRAPH.md §16 "Graphify
    Orchestrator"] `run_code_generation()` (graph.py) solo PROPONE codigo -- nunca lo
    escribe a disco, eso requiere aprobacion humana (mismo patron de "confirmacion humana
    para escrituras" que ya usa el resto del AI Core). Este endpoint, ya llamado
    manualmente despues de aplicar un cambio, es por lo tanto el unico punto real donde
    "cerrar el ciclo" tiene sentido -- no dentro del grafo de generacion, que corre ANTES
    de que el archivo exista en disco. Ahora, ademas del refresco incremental que ya hacia
    (KG/DependencyGraph/Memory -- Fases 10 y 12), corre gobernanza (`graph_validator.py`,
    Fase 13 -- no existia antes de esa auditoria) y marca la documentacion de Nivel 2 de
    las apps tocadas que conviene revisar (Fase 11 -- nunca la edita sola, solo la señala),
    en la misma llamada.
    """
    result = update_changed_apps(
        app_names=req.apps,
        frontend=req.frontend,
        force_full=req.force_full,
    )

    changed_apps = result.get("changed_apps", [])
    if changed_apps:
        try:
            from graph_validator import run_all_validations
            result["governance"] = run_all_validations()["summary"]
        except Exception as exc:
            logger.error("[refresh] Gobernanza fallo: %s", exc)
            result["governance"] = {"error": str(exc)}

        try:
            from documentation_graph import build_documentation_index
            result["docs_to_review"] = [
                d["path"] for d in build_documentation_index()
                if d["app"] in changed_apps and d["scope"] == "nivel2"
            ]
        except Exception as exc:
            logger.error("[refresh] Listado de docs a revisar fallo: %s", exc)
            result["docs_to_review"] = []

    return result


@app.get("/refresh/detect")
async def detect_changes():
    """Detecta que apps han cambiado desde el ultimo refresh."""
    changed_apps, frontend = detect_changed_apps()
    return {"changed_apps": changed_apps, "frontend_changed": frontend}


@app.post("/ingest")
async def trigger_ingestion():
    """Recarga y re-indexa todos los documentos (invocacion manual)."""
    if not _STATE.get("vectorstore"):
        raise HTTPException(503, "Motor no inicializado.")
    try:
        raw_docs   = load_all_documents(DOCS_SPECS_PATH, CODEBASE_PATH)
        all_chunks = split_all(raw_docs)
        vs         = _STATE["vectorstore"]
        batch_size = 50
        for i in range(0, len(all_chunks), batch_size):
            vs.add_documents(all_chunks[i : i + batch_size])
        _STATE["all_docs"] = all_chunks
        return {"status": "ok", "chunks_ingested": len(all_chunks)}
    except Exception as exc:
        logger.error("[ingest] Error durante re-ingesta: %s", exc)
        raise HTTPException(500, str(exc))
