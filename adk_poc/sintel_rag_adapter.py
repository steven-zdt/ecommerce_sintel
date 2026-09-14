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
from typing import Any

SINTEL_KNOWLEDGE_CONTEXT_STATE_KEY = "sintel_knowledge_context"

_NO_KNOWLEDGE_MARKER = "NINGUNO -- no se encontro informacion verificada sobre este tema."


async def build_knowledge_context(message: str, apps: list[str] | None = None) -> str:
    """Reutiliza `retrievers.retrieve_knowledge_for_chat` real (import
    diferido, mismo criterio que `sintel_adapter.py`: el modulo de
    ai_engine solo debe existir en sys.path cuando se usa este adapter).
    Replica EXACTAMENTE el recorte/formato/gobernanza real de
    `action_graph.py::node_retrieve_knowledge` -- mismo truncado a
    `MAX_KNOWLEDGE_CHUNKS` chunks de 800 chars, mismo separador, mismo
    marcador de Fase 17 cuando no hay resultados."""
    from action_graph import MAX_CONTEXT_CHARS, MAX_KNOWLEDGE_CHUNKS
    from retrievers import retrieve_knowledge_for_chat

    docs: list[dict[str, Any]] = (await retrieve_knowledge_for_chat(message, apps=apps))[:MAX_KNOWLEDGE_CHUNKS]
    if not docs:
        return _NO_KNOWLEDGE_MARKER
    return "\n---\n".join(d["content"][:800] for d in docs)[:MAX_CONTEXT_CHARS]
