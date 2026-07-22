from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from support.models import ChatRoom
from support.services.commands import ChatCommands
from support.api.serializers import RateConversationInputSerializer


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
        room = ChatRoom.objects.filter(uuid=room_uuid, is_deleted=False).first()
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
