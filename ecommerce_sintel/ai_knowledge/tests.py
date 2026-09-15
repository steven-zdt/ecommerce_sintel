"""
ai_knowledge/tests.py

FASE 1 (mision de simplificacion arquitectonica, 2026-09-14). Cubre: chunking,
upsert/re-chunk, filtro real de visibilidad (nunca devolver contenido interno
a /chat), degradacion con gracia sin proveedor de embeddings, y el endpoint
interno end-to-end. EmbeddingService se mockea (no depende de un Ollama real
corriendo) -- ver AI_ENGINE_AUDIT_SUPPORT_VS_ENGINEERING.md/AI_SUPPORT_SCOPE.md
para el mismo criterio ya aplicado en ai_engine/tests/test_retrieve_knowledge_for_chat.py.
"""
from unittest.mock import patch

from django.db import transaction
from django.db.utils import DataError
from django.test import TestCase
from rest_framework.test import APIClient

from ai_knowledge.models import AIKnowledgeChunk, AIKnowledgeDocument
from ai_knowledge.services.commands import AIKnowledgeDocumentCommands, AIKnowledgeEmbeddingCommands
from ai_knowledge.services.embedding_service import EmbeddingProviderUnavailable
from ai_knowledge.services.selectors import AIKnowledgeChunkSelector, RetrievalService

_FAKE_DIM = 1024


def _fake_vector(seed: float) -> list[float]:
    """Vector determinista (no aleatorio) para que dos textos "parecidos" en
    el seed queden cerca en distancia coseno -- suficiente para probar
    ranking sin depender de un modelo de embeddings real."""
    return [seed] * _FAKE_DIM


class ChunkingTests(TestCase):
    def test_upsert_document_splits_into_chunks(self):
        content = ('Parrafo uno con contenido real. ' * 20 + '\n\n') * 5
        doc = AIKnowledgeDocumentCommands.upsert_document(title='Doc largo', content=content)
        self.assertGreater(doc.chunks.count(), 1)
        indices = list(doc.chunks.order_by('chunk_index').values_list('chunk_index', flat=True))
        self.assertEqual(indices, list(range(len(indices))))

    def test_upsert_existing_document_replaces_chunks(self):
        doc = AIKnowledgeDocumentCommands.upsert_document(title='Doc', content='version uno')
        first_chunk_uuid = doc.chunks.first().uuid

        updated = AIKnowledgeDocumentCommands.upsert_document(uuid=doc.uuid, title='Doc', content='version dos, distinta')
        self.assertEqual(updated.uuid, doc.uuid)
        self.assertEqual(updated.chunks.count(), 1)
        self.assertNotEqual(updated.chunks.first().uuid, first_chunk_uuid)
        self.assertIn('version dos', updated.chunks.first().content)


class RetrievalVisibilityTests(TestCase):
    """El hallazgo real que motivo SAFE_KNOWLEDGE_VISIBILITY en el ChromaDB
    original (ver retrievers.py, comentario historico: una pregunta sobre
    horario de atencion recupero arquitectura interna) -- pgvector debe
    respetar exactamente la misma regla."""

    def setUp(self):
        self.public_doc = AIKnowledgeDocumentCommands.upsert_document(
            title='FAQ publica', content='Contenido publico para clientes.',
            visibility=AIKnowledgeDocument.VISIBILITY_PUBLIC,
        )
        self.internal_doc = AIKnowledgeDocumentCommands.upsert_document(
            title='Doc interno de arquitectura', content='Contenido interno de ingenieria, jamas para clientes.',
            visibility=AIKnowledgeDocument.VISIBILITY_INTERNAL,
        )
        for doc in (self.public_doc, self.internal_doc):
            chunk = doc.chunks.first()
            chunk.embedding = _fake_vector(1.0)
            chunk.embedding_model = 'fake-model'
            chunk.save()

    @patch('ai_knowledge.services.selectors.EmbeddingService.embed_text')
    def test_retrieval_never_returns_internal_documents(self, mock_embed):
        mock_embed.return_value = (_fake_vector(1.0), 'fake-model')
        results = RetrievalService.retrieve_public_knowledge('cualquier consulta')
        titles = [r['title'] for r in results]
        self.assertIn('FAQ publica', titles)
        self.assertNotIn('Doc interno de arquitectura', titles)

    @patch('ai_knowledge.services.selectors.EmbeddingService.embed_text')
    def test_retrieval_excludes_inactive_documents(self, mock_embed):
        mock_embed.return_value = (_fake_vector(1.0), 'fake-model')
        AIKnowledgeDocumentCommands.deactivate(self.public_doc.uuid)
        results = RetrievalService.retrieve_public_knowledge('cualquier consulta')
        self.assertEqual(results, [])

    @patch('ai_knowledge.services.selectors.EmbeddingService.embed_text')
    def test_retrieval_filters_by_app_name(self, mock_embed):
        mock_embed.return_value = (_fake_vector(1.0), 'fake-model')
        results = RetrievalService.retrieve_public_knowledge('cualquier consulta', app_names=['shop'])
        self.assertEqual(results, [])


class RetrievalDistanceTests(TestCase):
    """Mision RAG Enterprise (2026-09-16, FASE 6): RetrievalService ahora
    anota y devuelve la distancia coseno real de cada chunk -- necesaria
    para retrieval confidence/answerability en sintel_rag_adapter.py. Antes
    de esto, el campo no existia en la respuesta; el orden ya era correcto
    pero no habia forma de saber CUANTO mejor era el primer resultado."""

    def setUp(self):
        self.close_doc = AIKnowledgeDocumentCommands.upsert_document(
            title='Cercano', content='contenido cercano', visibility=AIKnowledgeDocument.VISIBILITY_PUBLIC,
        )
        self.far_doc = AIKnowledgeDocumentCommands.upsert_document(
            title='Lejano', content='contenido lejano', visibility=AIKnowledgeDocument.VISIBILITY_PUBLIC,
        )
        close_chunk = self.close_doc.chunks.first()
        close_chunk.embedding = _fake_vector(1.0)
        close_chunk.embedding_model = 'fake-model'
        close_chunk.save()
        far_chunk = self.far_doc.chunks.first()
        far_chunk.embedding = _fake_vector(-1.0)
        far_chunk.embedding_model = 'fake-model'
        far_chunk.save()

    @patch('ai_knowledge.services.selectors.EmbeddingService.embed_text')
    def test_cada_resultado_incluye_distance_como_float(self, mock_embed):
        mock_embed.return_value = (_fake_vector(1.0), 'fake-model')
        results = RetrievalService.retrieve_public_knowledge('consulta')
        self.assertEqual(len(results), 2)
        for r in results:
            self.assertIn('distance', r)
            self.assertIsInstance(r['distance'], float)

    @patch('ai_knowledge.services.selectors.EmbeddingService.embed_text')
    def test_distance_menor_para_el_resultado_mas_cercano(self, mock_embed):
        # Query identico al vector "cercano" -- su distancia coseno debe ser
        # ~0 (identico), la del "lejano" (vector opuesto) debe ser ~2.
        mock_embed.return_value = (_fake_vector(1.0), 'fake-model')
        results = RetrievalService.retrieve_public_knowledge('consulta')
        by_title = {r['title']: r['distance'] for r in results}
        self.assertLess(by_title['Cercano'], 0.01)
        self.assertGreater(by_title['Lejano'], 1.9)
        # Y el orden real de la lista debe reflejar esto (mas cercano primero).
        self.assertEqual(results[0]['title'], 'Cercano')


class RetrievalDegradationTests(TestCase):
    @patch('ai_knowledge.services.selectors.EmbeddingService.embed_text')
    def test_retrieval_returns_empty_list_without_provider(self, mock_embed):
        """Nunca debe lanzar -- /chat debe poder seguir respondiendo aunque
        el proveedor de embeddings este caido o sin configurar (mismo
        criterio que vectorstore=None en la version anterior sobre ChromaDB)."""
        mock_embed.side_effect = EmbeddingProviderUnavailable('sin proveedor configurado')
        results = RetrievalService.retrieve_public_knowledge('cualquier consulta')
        self.assertEqual(results, [])

    def test_retrieval_with_empty_query_via_endpoint(self):
        client = APIClient()
        resp = client.post('/api/v1/internal/ai/knowledge/retrieve/', {'query': ''}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {'chunks': []})


class EmbeddingCommandsTests(TestCase):
    @patch('ai_knowledge.services.commands.EmbeddingService.embed_text')
    def test_embed_pending_chunks_embeds_and_reports_remaining(self, mock_embed):
        mock_embed.return_value = (_fake_vector(0.5), 'fake-model')
        AIKnowledgeDocumentCommands.upsert_document(title='Doc', content='contenido para embeber')

        result = AIKnowledgeEmbeddingCommands.embed_pending_chunks()

        self.assertEqual(result, {'embedded': 1, 'remaining': 0})
        chunk = AIKnowledgeChunk.objects.get()
        self.assertIsNotNone(chunk.embedding)
        self.assertEqual(chunk.embedding_model, 'fake-model')

    @patch('ai_knowledge.services.commands.EmbeddingService.embed_text')
    def test_embed_pending_chunks_stops_on_provider_failure(self, mock_embed):
        mock_embed.side_effect = EmbeddingProviderUnavailable('proveedor caido')
        AIKnowledgeDocumentCommands.upsert_document(title='Doc', content='contenido')

        result = AIKnowledgeEmbeddingCommands.embed_pending_chunks()

        self.assertEqual(result, {'embedded': 0, 'remaining': 1})

    def test_count_stale_embeddings(self):
        doc = AIKnowledgeDocumentCommands.upsert_document(title='Doc', content='contenido')
        chunk = doc.chunks.first()
        chunk.embedding = _fake_vector(1.0)
        chunk.embedding_model = 'old-model'
        chunk.save()

        self.assertEqual(AIKnowledgeChunkSelector.count_stale_embeddings('new-model'), 1)
        self.assertEqual(AIKnowledgeChunkSelector.count_stale_embeddings('old-model'), 0)


class EmbeddingDimensionMismatchTests(TestCase):
    """Auditoria de hardening (2026-09-14, "PROMPT MAESTRO"): la columna real es
    `vector(EMBEDDING_DIMENSIONS)` (1024, bge-m3, ver models.py) -- un vector de
    otra dimension (ej. un proveedor de embeddings mal configurado, o un
    modelo distinto sin re-embeber toda la coleccion) NUNCA debe guardarse en
    silencio ni mezclarse con vectores de la dimension correcta. Confirma que
    pgvector rechaza esto a nivel de columna (DataError real de Postgres), no
    solo que el codigo de la app lo valide -- la regla de la mision explicita
    ("nunca mezclar embeddings incompatibles dentro de la misma coleccion
    logica") queda garantizada por el schema, no por disciplina."""

    def test_vector_de_dimension_incorrecta_es_rechazado_por_la_columna(self):
        doc = AIKnowledgeDocumentCommands.upsert_document(title='Doc', content='contenido')
        chunk = doc.chunks.first()
        chunk.embedding = [0.1] * 5   # dimension incorrecta a proposito (real=1024)
        with self.assertRaises(DataError):
            with transaction.atomic():
                chunk.save(update_fields=['embedding'])

    def test_vector_de_dimension_correcta_si_se_guarda(self):
        doc = AIKnowledgeDocumentCommands.upsert_document(title='Doc', content='contenido')
        chunk = doc.chunks.first()
        chunk.embedding = _fake_vector(0.5)
        chunk.save(update_fields=['embedding'])
        chunk.refresh_from_db()
        self.assertEqual(len(chunk.embedding), _FAKE_DIM)
