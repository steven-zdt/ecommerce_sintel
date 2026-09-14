"""
API REST del motor cognitivo Sintel AI Engine (chatbot de soporte + RAG).

FASE 4a (mision de simplificacion arquitectonica, 2026-09-14): se retiro el
pipeline de generacion/validacion de codigo (`/generate`, `/validate`,
`/plan`, `/impact`, `/breakage`, `/graph/node`, `/graph/impact` y los
modulos graph.py/chains.py/chains_frontend.py/guardrails.py/
guardrails_frontend.py/planner.py) -- confirmado sin ningun consumidor
externo (grep global) y superseded por `ai_editor/` + `project_knowledge_graph/`,
ya construidos y certificados (FASE61).

FASE 4b (misma mision): se retiro ChromaDB por completo (`/ingest`,
vectorstore_factory.py, embeddings_factory.py, bootstrap.py, loaders.py,
splitters.py) -- el RAG del chat (`/chat`) ya no vive en este proceso desde
FASE 3, consulta el endpoint interno de Django `ai_knowledge`
(PostgreSQL+pgvector) via retrievers.py::retrieve_knowledge_for_chat. Este
motor ya no mantiene ningun estado de conocimiento propio en memoria.

FASE 5 (misma mision, 2026-09-14): se retiraron `/memory`, `/search`,
`/indices`, `/manifest/{app}`, `/refresh`, `/refresh/detect` y los modulos
que los sostenian (memory_builder.py, specialized_retrieval.py,
ai_manifest.py, incremental_updater.py) junto con los artefactos JSON que
leian/escribian (PROJECT_MAP.json, DEPENDENCY_GRAPH.json,
KNOWLEDGE_GRAPH.json, GLOBAL_MEMORY.json, AI_MANIFESTS/, APP_MEMORY/,
MASTER_MANIFEST.json) -- eran indices/memoria/manifiestos construidos
exclusivamente para alimentar el pipeline de generacion de codigo retirado
en FASE 4a; sin ese pipeline, no tenian ningun consumidor (confirmado con
grep global de todo el repo, incluyendo scripts y docs operativos).

ADK-12 (mision "ADK-SINTEL", 2026-09-14): se retiro tambien `/chat` (y
`ChatRequest`/`ChatResponse`) de este proceso -- el chat de soporte real corre
enteramente en `ai_engine_adk/` desde el cutover (ADK-11, ver
AUDITORIA/ADK_CUTOVER_PLAN.md), con el fix del leak de razonamiento de
Qwen3.5 ya aplicado alli. `action_graph.py`/`llm_factory.py` dejaron de tener
un consumidor real en este proceso: `llm_factory.py` se elimino (ningun otro
modulo lo importaba); `action_graph.py` se mantiene SOLO como referencia
probada de la Policy Layer (`node_evaluate_policy`, ver
`tests/test_policy_layer.py`/`test_security_adversarial.py`/
`test_tool_policy_matrix.py`) mientras su gate `IsAdminUser` no se termine de
portar a `ai_engine_adk` (el rate limiter ya se porto, ver
AUDITORIA/ADK_CUTOVER_PLAN.md seccion 4nonies) -- no se importa desde
`main.py`.

Este proceso ahora expone unicamente `/health` y las rutas del AI Gateway
(`/api/v1/ai/*`, `gateway/`). Ver AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md
y AUDITORIA/ADK_CUTOVER_PLAN.md para el detalle completo.

Arranque:
    uvicorn main:app --host 0.0.0.0 --port 8100 --reload
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from gateway import ai_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[startup] AI Gateway listo (sin motor de chat en este proceso, ver docstring).")
    yield
    logger.info("[shutdown] AI Gateway detenido.")


app = FastAPI(
    title="Sintel AI Engine",
    version="1.0.0",
    description="AI Gateway (Meta Ads MCP) para Sintel E-Commerce REST v5 -- el chat de soporte corre en ai_engine_adk",
    lifespan=lifespan,
)

# AI Gateway (Fase 1 AI Core): rutas /api/v1/ai/* con JWT de Django obligatorio.
app.include_router(ai_router)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """
    Fase 10 (auditoria de puesta en produccion, 2026-08-17): antes devolvia
    "status": "ok" fijo -- no distinguia liveness (el proceso esta vivo) de
    readiness real de sus dependencias.

    ADK-12 (2026-09-14): ya no reporta `llm_ready` -- este proceso ya no
    mantiene ningun LLM propio desde que `/chat` se retiro (vive en
    `ai_engine_adk/`, con su propio healthcheck). Liveness simple del
    proceso/Gateway.
    """
    return {"status": "ok"}
