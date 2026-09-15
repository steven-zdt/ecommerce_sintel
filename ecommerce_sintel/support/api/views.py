from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from support.models import ChatRoom
from support.services.commands import ChatCommands, SupportTicketCommands
from support.api.serializers import CreateSupportTicketInputSerializer, RateConversationInputSerializer, SupportTicketSerializer


class RateConversationView(APIView):
    """
    POST /api/v1/support/chats/{room_uuid}/rate/
    CSAT: el cliente califica su propia conversacion ya cerrada (1-5 +
    comentario opcional). Primera REST API publica de `support` -- el resto
    de la interaccion del cliente es 100% WebSocket (ver
    support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Califica una conversacion de soporte cerrada (CSAT)",
        request=RateConversationInputSerializer,
        responses={200: dict, 400: dict, 404: dict},
    )
    def post(self, request, room_uuid=None):
        # D-04 (auditoria enterprise): el lookup ahora esta scoped a
        # request.user desde el inicio -- antes cualquier usuario
        # autenticado podia distinguir "existe" (200/400 mas adelante) de
        # "no existe" (404) para un room_uuid ajeno, antes de que
        # rate_conversation() hiciera su propio chequeo de ownership. Ahora
        # una sala ajena da 404 desde aca, igual que una que no existe.
        room = ChatRoom.objects.filter(uuid=room_uuid, user=request.user, is_deleted=False).first()
        if room is None:
            return Response({'detail': 'Sala no encontrada.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = RateConversationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            room = ChatCommands.rate_conversation(room, request.user, **serializer.validated_data)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'csat_rating': room.csat_rating,
            'csat_comment': room.csat_comment,
            'csat_rated_at': room.csat_rated_at,
        })


class CreateSupportTicketView(APIView):
    """
    POST /api/v1/support/tickets/create/
    body: {"subject": "...", "description": "...", "category": "..." (opcional)}
    -> 201 {"ticket": {...}, "room_uuid": "..."}

    Segundo flujo REAL de creacion de SupportTicket (2026-09-16) -- hasta
    ahora el UNICO camino era Human Handoff via el AI Engine
    (AiOpenSupportTicketView, support/api/internal_ai.py). Este es el
    directo: el cliente abre un ticket desde su perfil sin pasar por el
    chat. Misma logica real de fondo (get_or_create_room + save_message +
    pausar IA + notificar admins + SupportTicketCommands.create_ticket),
    reusada, no reimplementada -- solo cambia quien dispara el flujo y la
    fuente del texto (un formulario, no un mensaje de chat).
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Abre un ticket de soporte directamente desde el perfil del cliente",
        request=CreateSupportTicketInputSerializer,
        responses={201: dict, 400: dict},
    )
    def post(self, request):
        serializer = CreateSupportTicketInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        subject = serializer.validated_data['subject']
        description = serializer.validated_data['description']
        category = serializer.validated_data.get('category', '')

        from support.api.internal_ai import _notify_support_admins

        room = ChatCommands.get_or_create_room(request.user)
        ChatCommands.save_message(room, request.user, description)
        # Human Handoff: un ticket abierto a mano por el cliente tambien
        # implica que quiere atencion humana -- mismo criterio real que la
        # rama de IA (ai_paused=True), sin inventar un estado nuevo.
        if not room.ai_paused:
            room.ai_paused = True
            room.save(update_fields=['ai_paused', 'updated_at'])
        _notify_support_admins(room, request.user, description, label='[Ticket abierto por el cliente]')

        # Snapshot deliberado del contacto AL MOMENTO de abrir el ticket
        # (ver docstring de SupportTicket) -- mismo criterio que
        # AiOpenSupportTicketView.
        profile = getattr(request.user, 'profile', None)
        ticket = SupportTicketCommands.create_ticket(
            room, subject=subject, summary=description, category=category,
            contact_phone=getattr(profile, 'phone_number', '') or '',
            contact_email=request.user.email or '',
        )
        return Response(
            {'ticket': SupportTicketSerializer(ticket).data, 'room_uuid': str(room.uuid)},
            status=status.HTTP_201_CREATED,
        )
