"""
ADK-06 -- RAG adapter de SINTEL.

Regla dura de la mision (seccion 6 del plan): reusar `RetrievalService`/
pgvector via `ai_knowledge` (ya construido, ver
project_chromadb_to_pgvector_migration en memoria del agente), nunca
reintroducir ChromaDB/FAISS ni un segundo vector store.

Este adapter NO habla con pgvector directo ni con Django -- reutiliza tal
cual `ai_engine/retrievers.py::retrieve_knowledge_for_chat`, la MISMA
funcion real que ya usa `action_graph.py::node_retrieve_knowledge` desde la
migracion de ChromaDB->pgvector (FASE 3, mision anterior). Cero logica de
retrieval nueva aqui.

## Por que esto NO es una Tool ADK normal (a diferencia de ADK-02/04/05)

En el sistema real, retrieval de conocimiento NO es una decision del LLM --
es una rama determinista del grafo: `node_route_after_context` (action_graph.py
linea 734) envia el turno a `retrieve_knowledge` SOLO si
`state["intent"] == "knowledge"` (clasificado por regex, no por el LLM).
Mismo principio ya confirmado por el usuario en ADK-04 ("ADK ORQUESTA.
SINTEL EJECUTA Y CONTROLA"): el Root Workflow decide SI se hace retrieval
(via el mismo `resolve_turn_agent()`/router determinista de ADK-04), y le
inyecta el resultado al agente de dominio -- el LLM nunca "llama" a esto
como una tool ni decide por su cuenta si buscar o no.

## Gobernanza real que este adapter DEBE replicar (Fase 17, hallazgo real)

`node_retrieve_knowledge` (action_graph.py) inyecta un marcador EXPLICITO
("NINGUNO -- no se encontro informacion verificada sobre este tema.")
cuando no hay chunks -- el comentario real documenta el incidente que lo
motivo: sin este marcador, el LLM alucino una respuesta (horario de
atencion) rellenando el hueco con un chunk irrelevante. Omitir este
marcador en la migracion reintroduciria ese bug ya corregido.
"""
import logging
from typing import Any

logger = logging.getLogger("sintel_rag_adapter")

SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY = "sintel_knowledge_context"

# HARDENING F6/C4: categorias de F5 (input_guard) que ponen un chunk en cuarentena.
_QUARANTINE_CATEGORIES = {"override_instructions", "fake_system_message", "delimiter_forgery"}

# Diagnosticos por defecto cuando el turno NO es intent=="knowledge" -- nunca
# se llama a fetch_and_assemble_knowledge en ese caso (mismo criterio de
# siempre: retrieval solo corre si el router determinista lo decide).
EMPTY_KNOWLEDGE_DIAGNOSTICS: dict = {
    "metadata_filters": None,
    "retrieval_candidates": None,
    "retrieval_latency_ms": None,
    "best_similarity": None,
    "selected_sources": [],
}

_NO_KNOWLEDGE_MARKER = "NINGUNO -- no se encontro informacion verificada sobre este tema."

# Mision RAG Enterprise FASE 6 (2026-09-16, ver AUDITORIA/RAG_SUPPORT_BASELINE.md):
# retrieval confidence / answerability check. Antes de esto, la unica senal era
# "hay chunks" vs "no hay chunks" -- un chunk semanticamente lejano pero devuelto
# igual (top-k siempre rellena k resultados si existen, sin piso de calidad) se
# trataba identico a uno realmente relevante. El LLM no debe responder con
# confianza cuando la evidencia recuperada es debil -- mismo espiritu que el
# marcador de Fase 17 de abajo, extendido con una senal real de similitud.
_LOW_CONFIDENCE_MARKER = (
    "EVIDENCIA INSUFICIENTE -- se encontro informacion relacionada pero con baja "
    "similitud a la pregunta. No la uses para afirmar datos concretos (precios, "
    "politicas, horarios, plazos). Indica que no tienes informacion verificada "
    "suficiente sobre eso y ofrece escalar con un agente humano si el cliente insiste."
)

# Umbral de similitud minima para considerar la evidencia suficiente.
# similarity = 1 - cosine_distance (convencion pgvector: 0=identico, 2=opuesto).
# Valor de partida conservador, DOCUMENTADO COMO NO CALIBRADO: ai_knowledge esta
# vacio en este momento (hallazgo F-1 del baseline) -- no hay corpus real contra
# el cual medir un umbral optimo. Recalibrar con evaluacion real (Fase 10 de la
# mision) en cuanto exista contenido real ingerido.
MIN_ANSWERABLE_SIMILARITY = 0.35


def _similarity(distance: float) -> float:
    """cosine_distance real de pgvector -> similitud (1=identico, mas alto=mejor)."""
    return 1.0 - distance


async def fetch_and_assemble_knowledge(message: str, apps: list[str] | None = None) -> tuple[str, dict]:
    """Nucleo real de la construccion de contexto -- devuelve tambien
    diagnosticos de observabilidad (Mision RAG-POST2, FASE 5, 2026-09-16):
    `metadata_filters` (apps resueltos, mismo criterio de fallback que
    `retrievers.retrieve_knowledge_for_chat` -- replicado aqui, NO se cambia
    la firma de esa funcion porque tambien la usa `ai_engine/action_graph.py`
    del runtime OLD), `retrieval_candidates` (cuantos chunks devolvio Django
    antes de truncar a MAX_KNOWLEDGE_CHUNKS), `retrieval_latency_ms`
    (tiempo real de la llamada HTTP interna), `best_similarity` y
    `selected_sources` (titulos de las fuentes que realmente entraron al
    contexto -- [] si el turno fue no_knowledge/low_confidence).

    `build_knowledge_context()` (abajo) sigue siendo un wrapper delgado que
    devuelve SOLO el texto -- contrato sin cambios para no romper
    `test_rag_confidence_and_assembly.py` ni ningun otro caller existente.

    Reutiliza `retrievers.retrieve_knowledge_for_chat` real (import
    diferido, mismo criterio que `sintel_adapter.py`: el modulo de
    ai_engine solo debe existir en sys.path cuando se usa este adapter).

    Mision RAG Enterprise (2026-09-16), sobre la base de Fase 17 original:
    1. Retrieval confidence / answerability: si ni el mejor candidato supera
       MIN_ANSWERABLE_SIMILARITY, se trata igual que "sin evidencia" (marcador
       explicito) en vez de dejar que el LLM improvise sobre un chunk lejano.
    2. Context assembly estructurado (Fase 5): antes se enviaba solo
       `d["content"]` crudo -- title/source/app_name/updated_at que Django ya
       devuelve se pedian y se descartaban (hallazgo F-5 del baseline). Ahora
       cada fuente lleva un encabezado con esa metadata real, para que el LLM
       pueda valorar autoridad/vigencia de la evidencia, no solo su contenido.

    Mismo truncado a `MAX_KNOWLEDGE_CHUNKS` chunks de 800 chars y mismo
    presupuesto total `MAX_CONTEXT_CHARS` que la version original."""
    import time

    from routing import MAX_CONTEXT_CHARS, MAX_KNOWLEDGE_CHUNKS
    from retrievers import detect_apps_from_text, retrieve_knowledge_for_chat

    resolved_apps = apps if apps else detect_apps_from_text(message)

    started = time.monotonic()
    docs_all: list[dict[str, Any]] = await retrieve_knowledge_for_chat(message, apps=apps)
    retrieval_latency_ms = round((time.monotonic() - started) * 1000)
    docs = docs_all[:MAX_KNOWLEDGE_CHUNKS]
    # HARDENING F6/C4: cuarentena de chunks con banderas de inyeccion (defensa en profundidad para contenido que llegue
    # sin pasar por el pipeline de ingesta). Monitor por defecto; con AI_RAG_QUARANTINE_FLAGGED=true se excluyen.
    import config as ai_config
    import input_guard

    if ai_config.AI_INPUT_GUARD_ENABLED:
        kept = []
        for d in docs:
            cats = sorted(set(input_guard.detect_injection(d.get("content", ""))) & _QUARANTINE_CATEGORIES)
            if cats:
                logger.warning("security_event=rag_chunk_quarantined enforced=%s title=%r categories=%s",
                               ai_config.AI_RAG_QUARANTINE_FLAGGED, d.get("title"), cats)
                if ai_config.AI_RAG_QUARANTINE_FLAGGED:
                    continue
            kept.append(d)
        docs = kept

    diagnostics: dict[str, Any] = {
        "metadata_filters": resolved_apps,
        "retrieval_candidates": len(docs_all),
        "retrieval_latency_ms": retrieval_latency_ms,
        "best_similarity": None,
        "selected_sources": [],
    }

    if not docs:
        return _NO_KNOWLEDGE_MARKER, diagnostics

    # default=2.0 (maxima distancia posible -> similarity=-1.0, "insuficiente")
    # si algun caller no incluye "distance" -- tratar dato ausente como
    # evidencia NO confiable, nunca como el mejor caso posible (bug real
    # encontrado por el propio test de esta mision: 0.0 por defecto daba
    # similarity=1.0, lo opuesto de lo pretendido).
    best_similarity = max(_similarity(d.get("distance", 2.0)) for d in docs)
    diagnostics["best_similarity"] = round(best_similarity, 4)
    if best_similarity < MIN_ANSWERABLE_SIMILARITY:
        return _LOW_CONFIDENCE_MARKER, diagnostics

    blocks = []
    selected_sources = []
    for i, d in enumerate(docs, start=1):
        domain = d.get("app_name") or "general"
        updated = (d.get("updated_at") or "")[:10]
        header = f"[Fuente {i}] {d['title']} (dominio: {domain}, actualizado: {updated})"
        blocks.append(f"{header}\n{d['content'][:800]}")
        selected_sources.append(d["title"])
    diagnostics["selected_sources"] = selected_sources
    return "\n---\n".join(blocks)[:MAX_CONTEXT_CHARS], diagnostics


async def build_knowledge_context(message: str, apps: list[str] | None = None) -> str:
    """Wrapper delgado sobre `fetch_and_assemble_knowledge` -- contrato sin
    cambios (str) para no romper callers/tests existentes. Usar
    `fetch_and_assemble_knowledge` directamente cuando se necesiten los
    diagnosticos de observabilidad (ver `sintel_root_workflow.py`)."""
    text, _diagnostics = await fetch_and_assemble_knowledge(message, apps)
    return text
