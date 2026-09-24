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
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.api.permissions import IsAuthenticatedActiveUser

from ..services.commands import CustomerMemoryCommands, MemoryRejected
from ..services.selectors import CustomerMemorySelector


MAX_LIMIT = 10


class CustomerMemoryRetrieveView(APIView):
    """
    GET /api/v1/internal/ai/memory/retrieve/?limit=5
    -> {"memories": [{"category","content","created_at"}, ...]}
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        # HARDENING F7/C5: `limit` validado (antes int() sin tope => 500 con un valor no numerico y lecturas enormes).
        raw = request.query_params.get('limit')
        try:
            limit = int(raw) if raw not in (None, '') else 5
        except (TypeError, ValueError):
            return Response({'detail': 'limit debe ser un entero.'}, status=status.HTTP_400_BAD_REQUEST)
        if not 1 <= limit <= MAX_LIMIT:
            return Response({'detail': f'limit debe estar entre 1 y {MAX_LIMIT}.'}, status=status.HTTP_400_BAD_REQUEST)
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
                source_conversation_id=str(request.data.get('source_conversation_id', '') or ''),
                channel=str(request.data.get('channel', '') or ''),
            )
        except MemoryRejected as exc:
            return Response({'stored': False, 'reason': str(exc), 'code': exc.code})
        return Response({'stored': True, 'uuid': str(record.uuid)}, status=201)


class CustomerMemoryOwnerListView(APIView):
    """
    HARDENING F7/C4-Q5 (2026-09-24) -- Habeas Data: el PROPIO cliente ve y borra lo que el asistente recuerda de el.
    GET    /api/v1/customer-memory/          -> {"memories": [{"uuid","category","content","channel","created_at","expires_at"}]}
    DELETE /api/v1/customer-memory/          -> 200 {"deleted": n}  (olvida TODO, borrado fisico)
    Solo opera sobre `request.user`; jamas acepta un identificador de otro cliente.
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def get(self, request):
        return Response({'memories': CustomerMemorySelector.list_for_owner(request.user)})

    def delete(self, request):
        return Response({'deleted': CustomerMemoryCommands.forget_all(request.user)})


class CustomerMemoryOwnerDetailView(APIView):
    """DELETE /api/v1/customer-memory/<uuid>/ -- olvida UN recuerdo propio (404 si no existe o es de otro cliente)."""
    permission_classes = [IsAuthenticatedActiveUser]

    def delete(self, request, record_uuid):
        if not CustomerMemoryCommands.forget_record(request.user, record_uuid):
            return Response({'detail': 'No encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
