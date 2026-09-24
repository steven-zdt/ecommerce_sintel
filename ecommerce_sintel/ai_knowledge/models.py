"""
ai_knowledge/models.py

Plan "FASE 1 -- pgvector" (mision de simplificacion arquitectonica, 2026-09-14,
ver AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md). Reemplazo de ChromaDB como
vector store del RAG del Support Agent -- construido desde cero (no existia
ninguna pieza de esto en el repo antes de esta fase, confirmado en FASE 0).

Separacion arquitectonica (misma regla que ai_provider/models.py):
  AI ENGINE = cerebro del chatbot (NUNCA importa estos modelos ni Postgres
              directo, lee/escribe esta info solo via HTTP interno)
  AI KNOWLEDGE (esta app) = contenido indexado + vector store + retrieval
  AI PROVIDER = que proveedor/modelo de embeddings usar (reusado tal cual via
                AIChannelConfig.CHANNEL_EMBEDDINGS -- ver ai_provider/models.py)

Espejo deliberado del contrato que ya cumplia ChromaDB (metadata.language /
metadata.visibility, ver ai_engine/retrievers.py::retrieve_knowledge_for_chat)
para que la migracion de FASE 3 (cambiar consumidores) sea un cambio de
transporte, no de contrato.
"""
from django.conf import settings
from django.db import models
from pgvector.django import HnswIndex, VectorField

from ecommerce.base_models import SintelBaseModel

# Dimension fija de la columna vector -- pgvector no soporta dimension variable
# por fila. Debe coincidir con el modelo de embeddings activo
# (AIChannelConfig.CHANNEL_EMBEDDINGS). 1024 = bge-m3 (default historico de
# ai_engine/config.py::EMBEDDING_MODEL). Cambiar de modelo de embeddings a uno
# con otra dimension exige: migracion (AlterField) + re-embeber TODOS los
# chunks existentes -- nunca mezclar vectores de dos modelos en la misma
# columna (regla explicita de la mision, seccion 5: "no mezclar embeddings
# incompatibles dentro de la misma coleccion logica").
EMBEDDING_DIMENSIONS = getattr(settings, 'AI_KNOWLEDGE_EMBEDDING_DIMENSIONS', 1024)


class AIKnowledgeDocument(SintelBaseModel):
    """
    Un documento fuente completo (antes de chunkear) -- equivalente al
    `Document` de langchain que loaders.py arma hoy para Chroma, pero
    persistido y editable desde DB en vez de re-escanear el filesystem en
    cada arranque.
    """
    LANGUAGE_MARKDOWN = 'markdown'
    LANGUAGE_CHOICES = [
        (LANGUAGE_MARKDOWN, 'Markdown'),
    ]

    VISIBILITY_PUBLIC = 'public'
    VISIBILITY_INTERNAL = 'internal'
    VISIBILITY_CHOICES = [
        (VISIBILITY_PUBLIC, 'Publico (puede llegar a un cliente via /chat)'),
        (VISIBILITY_INTERNAL, 'Interno (documentacion de ingenieria, nunca al chat de clientes)'),
    ]

    title = models.CharField(max_length=255)
    # app_name vacio = documento global (ej. politicas generales), no atado a
    # un modulo especifico -- mismo campo que ya usaba Chroma metadata.app_name.
    app_name = models.CharField(max_length=100, blank=True, default='', db_index=True)
    source = models.CharField(
        max_length=500, blank=True, default='',
        help_text='Origen del contenido (ruta de archivo, URL, o "manual" si se escribio en el panel).',
    )
    language = models.CharField(max_length=30, choices=LANGUAGE_CHOICES, default=LANGUAGE_MARKDOWN)
    # Governance real (Knowledge Governance, ver retrievers.py comentario historico):
    # DEFAULT INTERNAL a proposito -- un documento nunca es visible para /chat
    # hasta que alguien lo marque explicitamente como public. Preferir "no
    # tengo esa informacion" a filtrar contenido interno por defecto.
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default=VISIBILITY_INTERNAL, db_index=True)
    content = models.TextField()
    is_active = models.BooleanField(default=True, db_index=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True,
    )

    # HARDENING F6/C1 (2026-09-24, plan sec. 10.1) -- metadata de gobierno. Todas con default/null: la migracion es aditiva
    # y los documentos EXISTENTES quedan `approved` (no cambia su comportamiento actual).
    AUTHORITY_OFFICIAL = 'official'
    AUTHORITY_INTERNAL = 'internal'
    AUTHORITY_THIRD_PARTY = 'third_party'
    AUTHORITY_CHOICES = [
        (AUTHORITY_OFFICIAL, 'Oficial (politica/contenido aprobado por la empresa)'),
        (AUTHORITY_INTERNAL, 'Interno'),
        (AUTHORITY_THIRD_PARTY, 'Tercero (menor autoridad)'),
    ]
    REVIEW_DRAFT = 'draft'
    REVIEW_NEEDS_REVIEW = 'needs_review'
    REVIEW_APPROVED = 'approved'
    REVIEW_CHOICES = [
        (REVIEW_DRAFT, 'Borrador'),
        (REVIEW_NEEDS_REVIEW, 'Requiere revision (el analisis de ingesta encontro banderas)'),
        (REVIEW_APPROVED, 'Aprobado'),
    ]
    document_version = models.PositiveIntegerField(default=1)
    content_hash = models.CharField(max_length=64, blank=True, default='', db_index=True)
    effective_from = models.DateTimeField(null=True, blank=True, help_text='Vigencia: no se recupera antes de esta fecha.')
    effective_until = models.DateTimeField(null=True, blank=True, help_text='Vigencia: no se recupera despues de esta fecha.')
    authority = models.CharField(max_length=20, choices=AUTHORITY_CHOICES, default=AUTHORITY_INTERNAL)
    review_status = models.CharField(max_length=20, choices=REVIEW_CHOICES, default=REVIEW_APPROVED, db_index=True)
    injection_flags = models.JSONField(default=list, blank=True,
                                       help_text='Categorias de inyeccion halladas al ingerir (sin el texto).')

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['app_name', 'visibility', 'is_active']),
        ]

    def __str__(self):
        return self.title


class AIKnowledgeChunk(SintelBaseModel):
    """
    Un fragmento embebido de AIKnowledgeDocument -- unidad real de busqueda
    vectorial. `embedding` es NULL hasta que EmbeddingCommands la procese
    (permite crear/editar el documento sin depender de que el proveedor de
    embeddings este disponible en ese momento).
    """
    document = models.ForeignKey(AIKnowledgeDocument, related_name='chunks', on_delete=models.CASCADE)
    chunk_index = models.PositiveIntegerField()
    content = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    # Registrado en cada fila (no solo a nivel de app) para poder detectar en
    # una query real si hay chunks embebidos con un modelo distinto al activo
    # -- ver AIKnowledgeChunkSelector.count_stale_embeddings().
    embedding_model = models.CharField(max_length=200, blank=True, default='')
    embedded_at = models.DateTimeField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, blank=True, default='')  # HARDENING F6/C1

    class Meta:
        ordering = ['document_id', 'chunk_index']
        constraints = [
            models.UniqueConstraint(fields=['document', 'chunk_index'], name='unique_chunk_index_per_document'),
        ]
        indexes = [
            # HNSW sobre vector_cosine_ops -- misma metrica de distancia que
            # ChromaDB usaba por default para este proyecto (ver
            # ai_engine/retrievers.py, search_type="mmr" sobre similitud
            # coseno). No crea el indice sobre filas con embedding NULL.
            HnswIndex(
                name='aik_chunk_embed_hnsw',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ]

    def __str__(self):
        return f'{self.document.title} #{self.chunk_index}'


class AIKnowledgeDocumentVersion(SintelBaseModel):
    """
    HARDENING F6/C1 (2026-09-24): historial de versiones de un documento (plan sec. 10.3 "versionar", sec. 21.2 rollback).
    Antes, `upsert_document` sobrescribia el contenido y borraba los chunks previos sin conservar nada. Cada cambio de
    contenido guarda aqui la version ANTERIOR.
    """
    document = models.ForeignKey(AIKnowledgeDocument, related_name='versions', on_delete=models.CASCADE)
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    content = models.TextField()
    content_hash = models.CharField(max_length=64, blank=True, default='')
    authority = models.CharField(max_length=20, blank=True, default='')
    review_status = models.CharField(max_length=20, blank=True, default='')
    saved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name='+', on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ['document_id', '-version']
        constraints = [
            models.UniqueConstraint(fields=['document', 'version'], name='unique_version_per_document'),
        ]

    def __str__(self):
        return f'{self.document.title} v{self.version}'
