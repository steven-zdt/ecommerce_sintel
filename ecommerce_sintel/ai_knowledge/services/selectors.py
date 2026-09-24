"""
ai_knowledge/services/selectors.py

RetrievalService -- unico camino de lectura del vector store (regla "Retrieval
unico" de la mision de simplificacion arquitectonica, seccion 13). Reemplaza
ChromaDB + el ensemble BM25/MMR que armaba ai_engine/retrievers.py -- pgvector
con indice HNSW (distancia coseno) hace la busqueda semantica.

Mision RAG Enterprise (2026-09-16, FASE 3, ver AUDITORIA/RAG_SUPPORT_BASELINE.md
hallazgo F-3): hybrid retrieval -- capa exacta/lexica (coincidencia textual de
tokens tipo codigo/SKU/UUID/termino tecnico) + capa vectorial (igual que antes).
La busqueda semantica sola puede no priorizar un match textual exacto (gap ya
senalado en el propio codigo antes de esta fase). No se implemento BM25/pg_trgm
completo (evaluado, descartado por ahora -- ver docstring de retrieve_public_
knowledge): un match exacto de token tecnico cubre el caso real que la mision
senala (SKUs, codigos, UUIDs, nombres exactos) sin agregar una dependencia
nueva (pg_trgm) ni el costo de mantener un SearchVectorField indexado sin
contenido real todavia que lo justifique (hallazgo F-1 del baseline).
"""
import logging
import re

from django.db.models import Q, QuerySet
from django.utils import timezone
from pgvector.django import CosineDistance

from .embedding_service import EmbeddingProviderUnavailable, EmbeddingService
from ..models import AIKnowledgeChunk, AIKnowledgeDocument

logger = logging.getLogger(__name__)

# Mision RAG Enterprise (2026-09-16, FASE 4): reranking -- no depender solo
# del score de retrieval crudo (distance). Se combina similitud (semantica o
# exacta, ya resuelta en la capa de hybrid retrieval) con un boost leve por
# vigencia del documento. Pesos deliberadamente conservadores (similitud
# domina, recency es desempate/boost menor) -- sin corpus real todavia
# (hallazgo F-1 del baseline) no hay forma de calibrar estos pesos con
# datos reales; quedan documentados como punto de partida, no como
# resultado medido. Reranking simple, sin servicio externo (Regla 2 de la
# mision: no crear Agentic RAG/reranker externo sin evidencia de que el
# retrieval monolitico actual es insuficiente).
_RERANK_WEIGHT_SIMILARITY = 0.85
_RERANK_WEIGHT_RECENCY = 0.15
_RECENCY_HALF_LIFE_DAYS = 365  # un documento de ~1 ano de antiguedad pesa la mitad que uno recien actualizado


def _rerank_score(distance: float, updated_at) -> float:
    similarity = 1.0 - distance
    days_old = max((timezone.now() - updated_at).days, 0)
    recency = 1.0 / (1.0 + days_old / _RECENCY_HALF_LIFE_DAYS)
    return _RERANK_WEIGHT_SIMILARITY * similarity + _RERANK_WEIGHT_RECENCY * recency

# Token candidato a coincidencia EXACTA: alfanumerico de 4+ caracteres. Se
# exige ademas un digito O un separador (- _) para no capturar palabras
# comunes en espanol ("hola", "precio", "tienda" tambien tienen >=4 letras) --
# el objetivo es SKUs/codigos/UUIDs/referencias tecnicas, no vocabulario
# general (eso ya lo cubre la capa vectorial).
_EXACT_TOKEN_PATTERN = re.compile(r'\b[A-Za-z0-9][A-Za-z0-9_-]{3,}\b')
_MAX_EXACT_TOKENS_PER_QUERY = 5


def _extract_exact_candidates(query: str) -> list[str]:
    seen: list[str] = []
    for token in _EXACT_TOKEN_PATTERN.findall(query):
        has_digit = any(c.isdigit() for c in token)
        has_separator = '-' in token or '_' in token
        if (has_digit or has_separator) and token not in seen:
            seen.append(token)
        if len(seen) >= _MAX_EXACT_TOKENS_PER_QUERY:
            break
    return seen


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


def _warn_embedding_mismatch(chunk_model: str, query_model: str) -> None:
    """Aviso (una vez cada 10 min) cuando un chunk recuperado se embebio con un modelo distinto al de la consulta."""
    from django.core.cache import cache

    if cache.add('ai_knowledge:embedding_mismatch_warned', 1, timeout=600):
        logger.warning('ai_operation_event=embedding_model_mismatch chunk_model=%s query_model=%s -- re-embeber con '
                       'reembed_stale_chunks()', chunk_model, query_model)


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

        Hybrid retrieval (FASE 3, 2026-09-16): combina dos capas antes de
        rankear:
          1. Exacta/lexica: tokens tipo codigo/SKU/UUID/termino tecnico
             detectados en `query` (ver `_extract_exact_candidates`),
             buscados via `content__icontains`. Un match exacto es evidencia
             fuerte -- se trata como distance=0.0 (mejor score posible),
             tiene prioridad sobre cualquier resultado puramente vectorial.
          2. Vectorial: igual que antes (HNSW + coseno), rellena el resto
             hasta `k` con lo que la capa exacta no encontro.
        Degradacion con gracia MEJORADA respecto a la version anterior: si el
        proveedor de embeddings esta caido pero SI hay matches exactos
        (ej. un cliente pregunta por un SKU literal mientras el proveedor de
        embeddings esta abajo), ahora se devuelven esos matches en vez de []
        -- antes cualquier fallo del proveedor vaciaba el resultado por
        completo sin importar si habia evidencia textual exacta disponible.
        Si NO hay proveedor Y NO hay matches exactos, sigue devolviendo []
        (nunca lanza), mismo criterio de siempre.

        Reranking (FASE 4, 2026-09-16): el orden final NO es solo `distance`
        cruda -- se combina con vigencia (`_rerank_score`, ver arriba). El
        campo `distance` en la respuesta sigue siendo la senal cruda
        original (para confidence/answerability en sintel_rag_adapter.py);
        el orden de la lista es el que decide `_rerank_score`.
        """
        now = timezone.now()
        qs = (
            AIKnowledgeChunk.objects.filter(
                is_deleted=False,
                embedding__isnull=False,
                document__is_deleted=False,
                document__is_active=True,
                document__visibility=AIKnowledgeDocument.VISIBILITY_PUBLIC,
                # HARDENING F6/C3: solo contenido APROBADO y VIGENTE, filtrado ANTES de rankear (plan sec. 10.2).
                document__review_status=AIKnowledgeDocument.REVIEW_APPROVED,
            )
            .filter(Q(document__effective_from__isnull=True) | Q(document__effective_from__lte=now))
            .filter(Q(document__effective_until__isnull=True) | Q(document__effective_until__gte=now))
            .select_related('document')
        )
        if app_names:
            qs = qs.filter(document__app_name__in=app_names)

        ranked: dict[int, dict] = {}
        for token in _extract_exact_candidates(query):
            for chunk in qs.filter(content__icontains=token)[:k]:
                ranked.setdefault(chunk.id, {'chunk': chunk, 'distance': 0.0})

        try:
            query_vector, _model_id = EmbeddingService.embed_text(query)
        except EmbeddingProviderUnavailable:
            query_vector = None

        if query_vector is not None:
            # cosine_distance: 0 = identico, 2 = opuesto -- ordenar ascendente
            # es "mas parecido primero", igual semantica que la similitud
            # coseno que Chroma exponia como score.
            for chunk in qs.annotate(distance=CosineDistance('embedding', query_vector)).order_by('distance')[:k]:
                if chunk.id in ranked:
                    continue  # ya esta por match exacto -- prioridad mas alta, no se pisa
                ranked[chunk.id] = {'chunk': chunk, 'distance': float(chunk.distance)}
                # HARDENING F6/C6: nunca mezclar vectores de dos modelos en la misma columna (ver models.EMBEDDING_DIMENSIONS).
                if chunk.embedding_model and _model_id and chunk.embedding_model != _model_id:
                    _warn_embedding_mismatch(chunk.embedding_model, _model_id)
        elif not ranked:
            return []

        ordered = sorted(
            ranked.values(),
            key=lambda r: _rerank_score(r['distance'], r['chunk'].document.updated_at),
            reverse=True,  # score mas alto primero (a diferencia de distance, donde menor es mejor)
        )[:k]
        return [
            {
                'content': r['chunk'].content,
                'source': r['chunk'].document.source,
                'app_name': r['chunk'].document.app_name,
                'title': r['chunk'].document.title,
                'updated_at': r['chunk'].document.updated_at.isoformat(),
                'distance': r['distance'],
            }
            for r in ordered
        ]
