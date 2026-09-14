"""
ai_knowledge/api/views.py

Endpoint interno que AI Engine consulta para RAG (reemplazo de ChromaDB, ver
AUDITORIA/ARCHITECTURE_SIMPLIFICATION_AUDIT.md). Misma naturaleza que
ai_provider/api/internal_ai.py::AiProviderConfigView -- llamada de
INFRAESTRUCTURA del motor (no actua en nombre de un usuario final), la
frontera de seguridad real es de red (Docker interno + nginx bloquea
/api/v1/internal/* en produccion), no permisos de Django. Ver ese modulo
para el razonamiento completo.

Ruteado bajo /api/v1/internal/ai/ (ecommerce/internal_ai_urls.py).
"""
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_knowledge.services.selectors import RetrievalService


class AiKnowledgeRetrieveView(APIView):
    """
    POST /api/v1/internal/ai/knowledge/retrieve/
    body: {"query": "...", "app_names": ["renting"] (opcional), "k": 8 (opcional)}
    -> {"chunks": [{"content", "source", "app_name", "title", "updated_at"}, ...]}

    Siempre 200 con chunks=[] si no hay conocimiento publico relevante o el
    proveedor de embeddings no esta disponible -- nunca un error que rompa
    /chat (mismo criterio de degradacion con gracia que ya tenia
    ai_engine/retrievers.py::retrieve_knowledge_for_chat con vectorstore=None).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        query = (request.data.get('query') or '').strip()
        if not query:
            return Response({'chunks': []})
        app_names = request.data.get('app_names') or None
        k = int(request.data.get('k') or 8)
        chunks = RetrievalService.retrieve_public_knowledge(query, app_names=app_names, k=k)
        return Response({'chunks': chunks})
