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

from django.core.exceptions import ValidationError

from . import ingestion
from .embedding_service import EmbeddingProviderUnavailable, EmbeddingService
from ..models import AIKnowledgeChunk, AIKnowledgeDocument, AIKnowledgeDocumentVersion

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
                         user=None, authority: str = AIKnowledgeDocument.AUTHORITY_INTERNAL,
                         effective_from=None, effective_until=None) -> AIKnowledgeDocument:
        """Crea o actualiza un documento pasando por el pipeline de ingesta (HARDENING F6/C2, plan sec. 10.3):
        validar fuente -> sanear -> clasificar -> hash/dedupe -> versionar -> indexar (chunks). Los embeddings NO se
        calculan aqui (puede no haber proveedor en el momento de guardar) -- ver embed_pending_chunks().

        - Fuente invalida => ValidationError (nada se guarda).
        - Banderas de inyeccion bloqueantes => review_status=needs_review y visibility forzada a INTERNAL (no publicable
          hasta `approve_document` + `publish_document`).
        - Mismo contenido (hash) => solo se actualizan metadatos; no se re-chunkea ni se cambia de version (dedupe).
        - Cambio de contenido => la version anterior se guarda en AIKnowledgeDocumentVersion y `document_version` sube."""
        source = ingestion.validate_source(source)
        clean = ingestion.sanitize_content(content)
        digest = ingestion.content_hash(clean)
        verdict = ingestion.classify(clean)
        blocked = bool(verdict['blocking'])
        if blocked:
            logger.warning('[ai_knowledge] ingesta con banderas bloqueantes %s title=%r -> needs_review', verdict['blocking'], title)
            visibility = AIKnowledgeDocument.VISIBILITY_INTERNAL
        review_status = AIKnowledgeDocument.REVIEW_NEEDS_REVIEW if blocked else AIKnowledgeDocument.REVIEW_APPROVED

        if uuid:
            document = AIKnowledgeDocument.objects.select_for_update().get(uuid=uuid, is_deleted=False)
            changed = document.content_hash != digest or document.content != clean
            if changed:
                AIKnowledgeDocumentVersion.objects.get_or_create(
                    document=document, version=document.document_version,
                    defaults=dict(title=document.title, content=document.content, content_hash=document.content_hash,
                                  authority=document.authority, review_status=document.review_status, saved_by=user),
                )
                document.document_version += 1
            document.title = title
            document.content = clean
            document.content_hash = digest
            document.app_name = app_name
            document.source = source
            document.visibility = visibility
            document.authority = authority
            document.effective_from = effective_from
            document.effective_until = effective_until
            document.review_status = review_status
            document.injection_flags = verdict['flags']
            document.updated_by = user
            document.save()
            if not changed:
                return document  # dedupe: mismo contenido -> no se re-chunkea
            document.chunks.all().delete()
        else:
            document = AIKnowledgeDocument.objects.create(
                title=title, content=clean, app_name=app_name, source=source, visibility=visibility,
                updated_by=user, authority=authority, effective_from=effective_from, effective_until=effective_until,
                content_hash=digest, review_status=review_status, injection_flags=verdict['flags'], document_version=1,
            )

        for index, chunk_text in enumerate(_split_into_chunks(clean)):
            AIKnowledgeChunk.objects.create(
                document=document, chunk_index=index, content=chunk_text, content_hash=ingestion.content_hash(chunk_text),
            )
        return document

    @staticmethod
    @transaction.atomic
    def approve_document(uuid, reviewer=None) -> AIKnowledgeDocument:
        """Accion HUMANA explicita: una persona revisa un documento `needs_review` y lo aprueba. NO lo publica (sigue INTERNAL)."""
        document = AIKnowledgeDocument.objects.select_for_update().get(uuid=uuid, is_deleted=False)
        document.review_status = AIKnowledgeDocument.REVIEW_APPROVED
        document.updated_by = reviewer
        document.save(update_fields=['review_status', 'updated_by', 'updated_at'])
        logger.info('[ai_knowledge] documento %s aprobado por revision humana (flags=%s)', document.uuid, document.injection_flags)
        return document

    @staticmethod
    @transaction.atomic
    def publish_document(uuid, user=None) -> AIKnowledgeDocument:
        """Publicacion EXPLICITA (visibility=public). Exige review_status=approved y sin banderas bloqueantes sin revisar."""
        document = AIKnowledgeDocument.objects.select_for_update().get(uuid=uuid, is_deleted=False)
        if document.review_status != AIKnowledgeDocument.REVIEW_APPROVED:
            raise ValidationError('El documento requiere revision aprobada antes de publicarse.')
        if not document.is_active:
            raise ValidationError('El documento esta inactivo.')
        document.visibility = AIKnowledgeDocument.VISIBILITY_PUBLIC
        document.updated_by = user
        document.save(update_fields=['visibility', 'updated_by', 'updated_at'])
        return document

    @staticmethod
    @transaction.atomic
    def rollback_to_version(uuid, version: int, user=None) -> AIKnowledgeDocument:
        """Restaura una version anterior (crea una version nueva con ese contenido; nunca borra el historial)."""
        document = AIKnowledgeDocument.objects.get(uuid=uuid, is_deleted=False)
        old = AIKnowledgeDocumentVersion.objects.get(document=document, version=version)
        return AIKnowledgeDocumentCommands.upsert_document(
            uuid=uuid, title=old.title, content=old.content, app_name=document.app_name, source=document.source,
            visibility=AIKnowledgeDocument.VISIBILITY_INTERNAL, user=user, authority=document.authority,
            effective_from=document.effective_from, effective_until=document.effective_until,
        )

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
