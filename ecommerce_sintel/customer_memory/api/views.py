"""
customer_memory/api/views.py

Mision RAG-POST2 (FASE 9, 2026-09-16). Endpoints internos que ai_engine_adk
consulta/escribe -- misma naturaleza que ai_knowledge/api/views.py (llamada
de infraestructura del motor, frontera de seguridad real es de red +
autenticacion JWT real del cliente, nginx bloquea /internal/* hacia afuera).

A diferencia de ai_knowledge/api/views.py::AiKnowledgeRetrieveView
(AllowAny -- conocimiento PUBLICO, igual para cualquiera), estos endpoints
son POR CLIENTE -- requieren `request.user` real (el JWT del cliente que
ai_engine_adk reenvia, mismo patron que cualquier Tool de escritura real,
ej. AiCreateRentalRequestView), nunca AllowAny.

Ruteado bajo /api/v1/internal/ai/memory/ (ecommerce/internal_ai_urls.py).
"""
from rest_framework.response import Response
from rest_framework.views import APIView

from users.api.permissions import IsAuthenticatedActiveUser

from ..services.commands import CustomerMemoryCommands, MemoryRejected
from ..services.selectors import CustomerMemorySelector


class CustomerMemoryRetrieveView(APIView):
    """
    GET /api/v1/internal/ai/memory/retrieve/?limit=5
    -> {"memories": [{"category","content","created_at"}, ...]}
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        limit = int(request.query_params.get('limit') or 5)
        memories = CustomerMemorySelector.list_active_for_customer(request.user, limit=limit)
        return Response({'memories': memories})


class CustomerMemoryStoreView(APIView):
    """
    POST /api/v1/internal/ai/memory/store/
    body: {"category": "...", "content": "...", "source_conversation_id": "..." (opcional)}
    -> 201 {"stored": true, "uuid": "..."} | 200 {"stored": false, "reason": "..."}

    Nunca 500 por una propuesta de memoria invalida -- MemoryRejected es un
    resultado esperado (el extractor de ai_engine_adk puede equivocarse),
    no un error del sistema.
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def post(self, request):
        try:
            record = CustomerMemoryCommands.store_record(
                user=request.user,
                category=request.data.get('category', ''),
                content=request.data.get('content', ''),
                source_conversation_id=request.data.get('source_conversation_id', ''),
            )
        except MemoryRejected as exc:
            return Response({'stored': False, 'reason': str(exc)})
        return Response({'stored': True, 'uuid': str(record.uuid)}, status=201)
