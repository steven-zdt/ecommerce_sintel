"""
API REST del motor cognitivo Sintel AI Engine.
Expone endpoints para generacion de codigo validado y validacion directa.

Arranque:
    uvicorn main:app --host 0.0.0.0 --port 8100 --reload
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field
import httpx

from auth import get_validated_token, decode_django_jwt
from action_graph import run_action_chat

from embeddings_factory import get_embeddings
from vectorstore_factory import get_vectorstore
from llm_factory import get_llm, get_dynamic_llm
from loaders import load_all_documents
from splitters import split_all
from guardrails import SintelArchitectureGuard, ValidationReport
from graph import run_code_generation
from retrievers import detect_task_type
from memory_builder import get_global_memory, get_app_memory
from planner import build_plan
from specialized_retrieval import retrieve_with_routing, get_registry
from ai_manifest import build_all_manifests, get_manifest
from incremental_updater import update_changed_apps, detect_changed_apps
from gateway import ai_router
from config import DOCS_SPECS_PATH, CODEBASE_PATH, LOCAL_MODEL_CHAIN, EMBEDDING_PROVIDER, EMBEDDING_MODEL, OLLAMA_BASE_URL
from llm_factory import parse_local_model_chain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")

_STATE: dict = {}


# ---------------------------------------------------------------------------
# Stubs de project_knowledge_graph (FASE 0, 2026-08-10) -- ai_engine ya no
# importa project_knowledge_graph ("AI Engine no conoce ni importa
# project_knowledge_graph", separacion Site Knowledge Graph / AI Editor
# Runtime). /impact y /breakage devuelven estructura vacia valida en vez de
# fallar; su version real debe reconstruirse en el futuro AI Editor Runtime.
# ---------------------------------------------------------------------------

def build_impact_report(task: str, extra_apps: list[str] | None = None) -> dict:
    return {
        "apps": [], "models": [], "serializers": [], "viewsets": [],
        "endpoints": [], "frontend_files": [], "stores": [], "services": [],
    }


def build_impact_context(task: str, extra_apps: list[str] | None = None) -> str:
    return ""


def what_breaks_if_i_change(entity: str) -> dict:
    return {}


def build_impact_analysis_text(entity: str) -> str:
    return ""


async def _ensure_ollama_models() -> None:
    """
    Pre-carga en Ollama los modelos que se van a necesitar antes de la primera peticion
    real, para evitar el timeout de la primera llamada. Nivel A (auditoria 2026-08-07):
    ya no hay un unico LLM_PROVIDER que revisar -- se recorre LOCAL_MODEL_CHAIN y se
    pre-carga cada entrada 'ollama-nativo' (mas el modelo de embeddings, si tambien usa
    Ollama). Motores openai-compatible/anthropic no necesitan pre-carga: son servicios
    externos al proceso, no procesos que este mismo Ollama tenga que arrancar.
    """
    targets: list[tuple[str, str]] = []
    if EMBEDDING_PROVIDER == "ollama":
        targets.append((OLLAMA_BASE_URL, EMBEDDING_MODEL))
    for entry in parse_local_model_chain(LOCAL_MODEL_CHAIN):
        if entry["kind"] == "ollama-nativo":
            targets.append((entry["base_url"], entry["model"]))

    seen: set[tuple[str, str]] = set()
    async with httpx.AsyncClient(timeout=300) as client:
        for base_url, model in targets:
            key = (base_url, model)
            if key in seen:
                continue
            seen.add(key)
            try:
                logger.info("[startup] Pre-cargando modelo Ollama '%s' @ %s...", model, base_url)
                resp = await client.post(
                    f"{base_url}/api/pull",
                    json={"name": model, "stream": False},
                )
                resp.raise_for_status()
                logger.info("[startup] Modelo '%s' listo.", model)
            except Exception as exc:
                logger.warning("[startup] No se pudo pre-cargar '%s' @ %s: %s", model, base_url, exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] Inicializando motor cognitivo...")
    try:
        await _ensure_ollama_models()  # no-op limpio si LOCAL_MODEL_CHAIN no tiene entradas ollama-nativo
        llm              = get_llm()
        raw_docs         = load_all_documents(DOCS_SPECS_PATH, CODEBASE_PATH)
        all_chunks       = split_all(raw_docs)
        _STATE["all_docs"]    = all_chunks
        _STATE["llm"]         = llm

        # Fallback de produccion (auditoria de puesta en produccion, 2026-08-17):
        # chromadb.HttpClient valida la conexion al construirse -- si ChromaDB no
        # esta disponible, get_vectorstore() lanza y (antes de este fix) tumbaba
        # el arranque ENTERO del proceso, no solo el RAG. /chat ya pasa
        # vectorstore=_STATE.get("vectorstore") (None-safe) y
        # retrieve_knowledge_for_chat ya tolera vectorstore=None -- el unico punto
        # que faltaba blindar era este. Motor sigue arrancando sin RAG si Chroma
        # esta caido; /generate (que si necesita vectorstore) sigue devolviendo
        # 503 explicito como ya hacia (linea ~331), no un crash de proceso.
        try:
            embeddings  = get_embeddings()
            vectorstore = get_vectorstore(embeddings)
            _STATE["vectorstore"] = vectorstore
        except Exception as exc:
            _STATE["vectorstore"] = None
            logger.warning("[startup] ChromaDB no disponible, RAG degradado (motor sigue arrancando): %s", exc)

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
    # G1 (AUDITORIA/16, 2026-08-01): antes sin ningun limite en toda la cadena
    # support(consumers.py) -> ChatRequest -> LLM. Inofensivo hoy con Ollama local (costo
    # marginal ~0), pero un riesgo de costo real y directo si se activa un proveedor de pago
    # (LLM_PROVIDER=openai/anthropic, ya soportado en llm_factory.py) sin este techo.
    message: str = Field(max_length=4000)
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
    try:
        # FASE 4 (plan "CONFIGURACION DINAMICA DE MODELOS LOCALES", 2026-08-13):
        # get_dynamic_llm() consulta ai_provider (Postgres via Django) en vez de usar
        # el LLM fijo de _STATE construido una sola vez al arrancar -- cae sola a
        # LOCAL_MODEL_CHAIN/_STATE['llm'] si no hay config real o Django no responde,
        # asi que el guard de arriba (_STATE['llm'] inicializado) sigue siendo valido
        # como senal de que el proceso arranco bien.
        chat_llm = await get_dynamic_llm()
        result = await run_action_chat(
            message=req.message,
            conversation_id=req.conversation_id,
            token=token,
            user_id=payload["user_id"],
            llm=chat_llm,
            vectorstore=_STATE.get("vectorstore"),
            all_docs=_STATE.get("all_docs", []),
            confirm=req.confirm,
        )
    except Exception:
        # Certificacion del chat (2026-08-07): con un solo motor en
        # LOCAL_MODEL_CHAIN (sin fallback configurado), una caida del motor
        # (ej. httpx.ConnectError si el contenedor se detiene) no tenia
        # ningun catch en este endpoint -- se propagaba como 500 crudo sin
        # cuerpo util. ai_bridge.py (Django) ya trata cualquier status != 200
        # como "motor no disponible" y degrada con gracia del lado del
        # usuario (mensaje + Human Handoff implicito), pero el 500 crudo
        # rompia la traza [AI_BRIDGE] con un cuerpo vacio en vez de un
        # error explicito, y cualquier otro consumidor de /chat (debug
        # manual, futuros clientes) se llevaba una excepcion sin contexto.
        logger.exception("[chat] error no controlado en run_action_chat, conversation_id=%s", req.conversation_id)
        return ChatResponse(
            conversation_id=req.conversation_id or "",
            intent="unknown",
            agent=None,
            tool_calls=[],
            tool_results=[],
            needs_confirmation=False,
            confirmation=None,
            response="En este momento nuestro asistente no esta disponible. Un agente humano revisara tu mensaje pronto.",
            metrics={"engine_unavailable": True},
        )
    return ChatResponse(**result)


@app.get("/health")
async def health():
    """
    Fase 10 (auditoria de puesta en produccion, 2026-08-17): antes devolvia
    "status": "ok" fijo + un conteo de chunks -- no distinguia liveness (el
    proceso esta vivo) de readiness real de sus dependencias. `llm`/`all_docs`
    siempre quedan poblados si el proceso llego a aceptar requests (el lifespan
    los construye fuera del bloque tolerante a fallos); lo unico que puede faltar
    es `vectorstore` (RAG degradado si ChromaDB no estaba disponible al
    arrancar, ver lifespan). Deliberadamente sin hacer una llamada de red nueva
    aqui -- un healthcheck que depende de red puede volverse su propio punto de
    falla bajo latencia/saturacion; reporta el estado ya conocido de `_STATE`.
    """
    vectorstore_ok = _STATE.get("vectorstore") is not None
    llm_ok = _STATE.get("llm") is not None
    return {
        "status": "ok" if llm_ok else "starting",
        "llm_ready": llm_ok,
        "rag_ready": vectorstore_ok,
        "chunks_indexed": len(_STATE.get("all_docs", [])),
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
    [RETIRADO 2026-08-10, FASE 0] ai_engine ya no importa project_knowledge_graph
    -- esta consulta debe hacerse via `python -m project_knowledge_graph.cli node
    <entidad>` o el futuro AI Editor Runtime, no desde este servicio.
    """
    raise HTTPException(501, "Retirado: ai_engine ya no depende de project_knowledge_graph. "
                              "Usar `python -m project_knowledge_graph.cli node <entidad>`.")


@app.get("/graph/impact/{entity_name}")
async def graph_impact(entity_name: str):
    """
    [RETIRADO 2026-08-10, FASE 0] ai_engine ya no importa project_knowledge_graph
    -- esta consulta debe hacerse via `python -m project_knowledge_graph.cli
    impact <entidad>` o el futuro AI Editor Runtime, no desde este servicio.
    """
    raise HTTPException(501, "Retirado: ai_engine ya no depende de project_knowledge_graph. "
                              "Usar `python -m project_knowledge_graph.cli impact <entidad>`.")


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
    Actualiza incrementalmente la memoria del motor (APP_MEMORY/indices
    especializados -- Fases 10 y 12). Detecta cambios automaticamente o acepta
    lista de apps cambiadas.

    [DEGRADADO 2026-08-10, FASE 0 -- desacoplamiento ai_engine <->
    project_knowledge_graph] Este endpoint corria ademas gobernanza
    (`graph_validator.py`) y marcaba documentacion de Nivel 2 a revisar --
    ambas dependian de project_knowledge_graph, que ai_engine ya no debe
    importar. Ese analisis sigue existiendo, pero via
    `python -m project_knowledge_graph.cli validate`, fuera de este servicio.
    """
    result = update_changed_apps(
        app_names=req.apps,
        frontend=req.frontend,
        force_full=req.force_full,
    )
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
