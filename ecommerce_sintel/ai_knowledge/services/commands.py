"""
ai_knowledge/services/commands.py

Ingesta: crear/actualizar un AIKnowledgeDocument, chunkearlo y embeberlo.
Chunking deliberadamente simple (split por parrafos con solape) para FASE 1 --
loaders.py/splitters.py de ai_engine usan langchain_text_splitters con logica
mas rica (por tipo de archivo); portar esa logica es FASE 2/3 si hace falta,
no se duplica aqui sin evidencia de que el splitter simple no alcanza.
"""
import logging

from django.db import transaction
from django.utils import timezone

from .embedding_service import EmbeddingProviderUnavailable, EmbeddingService
from ..models import AIKnowledgeChunk, AIKnowledgeDocument

logger = logging.getLogger(__name__)

_CHUNK_SIZE_CHARS = 1200
_CHUNK_OVERLAP_CHARS = 150


def _split_into_chunks(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    chunks: list[str] = []
    current = ''
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > _CHUNK_SIZE_CHARS:
            chunks.append(current)
            current = current[-_CHUNK_OVERLAP_CHARS:] + '\n\n' + para
        else:
            current = f'{current}\n\n{para}' if current else para
    if current:
        chunks.append(current)
    return chunks or ([text] if text.strip() else [])


class AIKnowledgeDocumentCommands:
    @staticmethod
    @transaction.atomic
    def upsert_document(*, uuid=None, title: str, content: str, app_name: str = '',
                         source: str = '', visibility: str = AIKnowledgeDocument.VISIBILITY_INTERNAL,
                         user=None) -> AIKnowledgeDocument:
        """Crea o actualiza un documento y re-chunkea su contenido. Los
        embeddings de los chunks NO se calculan aqui (puede no haber
        proveedor disponible en el momento de guardar) -- ver
        embed_pending_chunks(), pensado para correr aparte (management
        command / tarea Celery futura, no atado al request de guardado)."""
        if uuid:
            document = AIKnowledgeDocument.objects.select_for_update().get(uuid=uuid, is_deleted=False)
            document.title = title
            document.content = content
            document.app_name = app_name
            document.source = source
            document.visibility = visibility
            document.updated_by = user
            document.save()
            document.chunks.all().delete()
        else:
            document = AIKnowledgeDocument.objects.create(
                title=title, content=content, app_name=app_name,
                source=source, visibility=visibility, updated_by=user,
            )

        for index, chunk_text in enumerate(_split_into_chunks(content)):
            AIKnowledgeChunk.objects.create(document=document, chunk_index=index, content=chunk_text)

        return document

    @staticmethod
    def deactivate(uuid, user=None) -> None:
        AIKnowledgeDocument.objects.filter(uuid=uuid, is_deleted=False).update(is_active=False, updated_by=user)


class AIKnowledgeEmbeddingCommands:
    @staticmethod
    def embed_pending_chunks(limit: int = 500) -> dict:
        """Calcula el embedding de cada chunk con `embedding IS NULL` (creado
        despues del ultimo run, o nunca procesado). No re-embebe chunks que
        ya tienen vector -- para eso ver reembed_stale_chunks(). Se detiene en
        el primer fallo del proveedor (en vez de reintentar chunk por chunk
        contra un proveedor caido) y reporta cuantos quedaron pendientes."""
        pending = AIKnowledgeChunk.objects.filter(is_deleted=False, embedding__isnull=True)[:limit]
        embedded = 0
        for chunk in pending:
            try:
                vector, model_id = EmbeddingService.embed_text(chunk.content)
            except EmbeddingProviderUnavailable as exc:
                logger.warning('[ai_knowledge] embed_pending_chunks detenido en chunk uuid=%s: %s', chunk.uuid, exc)
                break
            chunk.embedding = vector
            chunk.embedding_model = model_id
            chunk.embedded_at = timezone.now()
            chunk.save(update_fields=['embedding', 'embedding_model', 'embedded_at', 'updated_at'])
            embedded += 1
        remaining = AIKnowledgeChunk.objects.filter(is_deleted=False, embedding__isnull=True).count()
        return {'embedded': embedded, 'remaining': remaining}

    @staticmethod
    def reembed_stale_chunks(current_model_id: str, limit: int = 500) -> dict:
        """Re-embebe chunks cuyo embedding_model != el modelo activo hoy --
        uso explicito tras cambiar el proveedor/modelo de embeddings desde
        /panel/soporte (regla de la mision: nunca mezclar vectores de
        modelos distintos en la misma coleccion logica)."""
        stale = (
            AIKnowledgeChunk.objects.filter(is_deleted=False, embedding__isnull=False)
            .exclude(embedding_model=current_model_id)[:limit]
        )
        updated = 0
        for chunk in stale:
            try:
                vector, model_id = EmbeddingService.embed_text(chunk.content)
            except EmbeddingProviderUnavailable as exc:
                logger.warning('[ai_knowledge] reembed_stale_chunks detenido en chunk uuid=%s: %s', chunk.uuid, exc)
                break
            chunk.embedding = vector
            chunk.embedding_model = model_id
            chunk.embedded_at = timezone.now()
            chunk.save(update_fields=['embedding', 'embedding_model', 'embedded_at', 'updated_at'])
            updated += 1
        return {'updated': updated}
