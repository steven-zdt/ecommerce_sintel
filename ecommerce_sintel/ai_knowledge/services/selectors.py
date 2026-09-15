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
import re

from django.db.models import QuerySet
from pgvector.django import CosineDistance

from .embedding_service import EmbeddingProviderUnavailable, EmbeddingService
from ..models import AIKnowledgeChunk, AIKnowledgeDocument

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
        """
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
        elif not ranked:
            return []

        ordered = sorted(ranked.values(), key=lambda r: r['distance'])[:k]
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
