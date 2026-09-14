"""
ai_knowledge/services/selectors.py

RetrievalService -- unico camino de lectura del vector store (regla "Retrieval
unico" de la mision de simplificacion arquitectonica, seccion 13). Reemplaza
ChromaDB + el ensemble BM25/MMR que armaba ai_engine/retrievers.py -- pgvector
con indice HNSW (distancia coseno) hace la busqueda semantica; sin BM25 todavia
(fuera de alcance de FASE 1, ver nota en retrieve()).
"""
from django.db.models import QuerySet
from pgvector.django import CosineDistance

from .embedding_service import EmbeddingProviderUnavailable, EmbeddingService
from ..models import AIKnowledgeChunk, AIKnowledgeDocument


class AIKnowledgeDocumentSelector:
    @staticmethod
    def list_documents(app_name: str | None = None, visibility: str | None = None, include_inactive: bool = False) -> QuerySet:
        qs = AIKnowledgeDocument.objects.filter(is_deleted=False)
        if not include_inactive:
            qs = qs.filter(is_active=True)
        if app_name:
            qs = qs.filter(app_name=app_name)
        if visibility:
            qs = qs.filter(visibility=visibility)
        return qs

    @staticmethod
    def get(uuid) -> AIKnowledgeDocument:
        return AIKnowledgeDocument.objects.get(uuid=uuid, is_deleted=False)


class AIKnowledgeChunkSelector:
    @staticmethod
    def count_stale_embeddings(current_model_id: str) -> int:
        """Chunks embebidos con un modelo distinto al activo hoy -- deben
        re-embeberse antes de poder confiar en resultados de retrieval
        consistentes (mezclar vectores de dos modelos en la misma busqueda
        HNSW no lanza un error, pero las distancias no son comparables entre
        si -- regla de la mision, seccion 5)."""
        return (
            AIKnowledgeChunk.objects.filter(is_deleted=False, embedding__isnull=False)
            .exclude(embedding_model=current_model_id)
            .count()
        )

    @staticmethod
    def count_pending_embeddings() -> int:
        return AIKnowledgeChunk.objects.filter(is_deleted=False, embedding__isnull=True).count()


class RetrievalService:
    @staticmethod
    def retrieve_public_knowledge(query: str, app_names: list[str] | None = None, k: int = 8) -> list[dict]:
        """
        Retrieval para /chat (Support Agent) -- SOLO documentos
        visibility=public (mismo contrato que tenia
        ai_engine/retrievers.py::retrieve_knowledge_for_chat sobre ChromaDB:
        nunca devuelve contenido interno de ingenieria a un cliente).
        Consumido via ai_knowledge/api/views.py::AiKnowledgeRetrieveView
        (FASE 3: ai_engine ya no habla con Postgres directo, llama a ese
        endpoint interno).

        `app_names`: filtro OR -- documentos de cualquiera de esos app_name.
        None/[] = sin filtro (busca en todo el corpus publico).

        Retorna [] (nunca lanza) si no hay modelo de embeddings configurado o
        el proveedor esta caido -- mismo criterio de degradacion con gracia
        que ya usaba el vectorstore=None de ai_engine (preferir "sin
        conocimiento" a romper /chat).

        NOTA (fuera de alcance FASE 1/3): busqueda puramente semantica (HNSW +
        coseno), sin el hibrido BM25+MMR que tenia
        build_ensemble_retriever/retrieve_knowledge_for_chat en ChromaDB.
        Evaluar en una fase futura si hace falta reintroducir keyword-search
        (ej. via pg_trgm o el `SearchVector` nativo de Postgres) -- no se
        asume que no hace falta solo porque Chroma ya se retiro.
        """
        try:
            query_vector, _model_id = EmbeddingService.embed_text(query)
        except EmbeddingProviderUnavailable:
            return []

        qs = (
            AIKnowledgeChunk.objects.filter(
                is_deleted=False,
                embedding__isnull=False,
                document__is_deleted=False,
                document__is_active=True,
                document__visibility=AIKnowledgeDocument.VISIBILITY_PUBLIC,
            )
            .select_related('document')
        )
        if app_names:
            qs = qs.filter(document__app_name__in=app_names)

        # cosine_distance: 0 = identico, 2 = opuesto -- ordenar ascendente
        # es "mas parecido primero", igual semantica que la similitud coseno
        # que Chroma exponia como score.
        results = qs.order_by(CosineDistance('embedding', query_vector))[:k]

        return [
            {
                'content': chunk.content,
                'source': chunk.document.source,
                'app_name': chunk.document.app_name,
                'title': chunk.document.title,
                'updated_at': chunk.document.updated_at.isoformat(),
            }
            for chunk in results
        ]
