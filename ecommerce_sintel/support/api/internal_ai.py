"""
Endpoint interno para el AI Engine (Fase 4 AI Core) — OpenSupportTicketTool.

Envuelve ChatCommands.get_or_create_room + save_message + attach_context
(idempotente). No requiere confirmacion (no es destructivo), pero el AI
avisa al usuario que un humano lo atendera. La sala aparece en el panel
/panel/soporte como cualquier chat; la notificacion push al operador en
tiempo real es alcance de la Fase 7 (Human Handoff completo).

Tambien es la resolucion del gap #1 (decision del usuario 2026-07-16):
cambiar fechas de un alquiler NO es self-service -- la RentalTool escala
aqui, adjuntando la solicitud como contexto (CONTEXT_RENTAL).
"""
from rest_framework import status as http_status
from rest_framework.views import APIView
from rest_framework.response import Response

from support.models import ChatRoomContext
from support.services.commands import ChatCommands
from users.api.permissions import IsAuthenticatedActiveUser


def _dump_ai_transcript(room, history) -> None:
    """
    Human Handoff (Componente 7): vuelca la conversacion previa con el AI en
    la sala, firmada por el bot -- el operador humano recibe TODO el contexto,
    nunca se pierde historial.
    """
    if not history:
        return
    from support.services.ai_bridge import get_ai_bot_user
    lines = ['[Transcripcion de la conversacion con el asistente IA]']
    for turn in history[-6:]:
        if not isinstance(turn, dict):
            continue
        if turn.get('user'):
            lines.append(f"Cliente: {str(turn['user'])[:300]}")
        if turn.get('assistant'):
            lines.append(f"Asistente: {str(turn['assistant'])[:300]}")
    ChatCommands.save_message(room, get_ai_bot_user(), '\n'.join(lines))


def _notify_support_admins(room, user, message: str) -> None:
    """Aviso en vivo al grupo support_admins (ya existe en SupportChatConsumer)."""
    from django.utils import timezone
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)('support_admins', {
        'type': 'chat.message',
        'message': f'[Escalado por el asistente IA] {message}',
        'sender_email': user.email,
        'is_admin': False,
        'room_uuid': str(room.uuid),
        'created_at': timezone.now().isoformat(),
    })


class AiOpenSupportTicketView(APIView):
    """
    POST /api/v1/internal/ai/support/ticket/
    Body: {message, order_uuid?, rental_uuid?, history?}

    `history` (Fase 7) es la conversacion previa con el AI -- la inyecta el
    Action Graph (execute_write), nunca el LLM (no esta en el args_schema).
    """
    permission_classes = [IsAuthenticatedActiveUser]

    def post(self, request):
        message = str(request.data.get('message', '')).strip()
        if not message:
            return Response({'error': 'Parametro message requerido.'}, status=http_status.HTTP_400_BAD_REQUEST)

        room = ChatCommands.get_or_create_room(request.user)
        _dump_ai_transcript(room, request.data.get('history'))
        ChatCommands.save_message(room, request.user, message)
        # Human Handoff: la sala pasa a manos humanas -- el modo AI se pausa.
        if not room.ai_paused:
            room.ai_paused = True
            room.save(update_fields=['ai_paused', 'updated_at'])
        _notify_support_admins(room, request.user, message)

        attached = None
        rental_uuid = str(request.data.get('rental_uuid', '')).strip()
        order_uuid = str(request.data.get('order_uuid', '')).strip()
        if rental_uuid:
            from renting.services.selectors import RentalRequestSelector
            rental = RentalRequestSelector.get_by_uuid_for_user(rental_uuid, request.user)
            ChatCommands.attach_context(
                room, ChatRoomContext.CONTEXT_RENTAL, rental_request=rental, added_by=request.user,
            )
            attached = f'alquiler {rental_uuid}'
        elif order_uuid:
            from orders.services.selectors import OrderSelector
            order = OrderSelector.get_by_uuid(order_uuid)
            if order.user_id != request.user.id:
                return Response({'error': 'Orden no encontrada.'}, status=http_status.HTTP_404_NOT_FOUND)
            ChatCommands.attach_context(
                room, ChatRoomContext.CONTEXT_ORDER, order=order, added_by=request.user,
            )
            attached = f'orden {order_uuid}'

        from security.models import SecurityEvent
        from security.services.commands import SecurityCommands
        SecurityCommands.log_event(
            SecurityEvent.AI_ACTION_EXECUTED,
            request=request,
            metadata={'tool': 'OpenSupportTicketTool', 'room_uuid': str(room.uuid),
                      'attached_context': attached},
        )
        return Response({'ticket': {
            'room_uuid': str(room.uuid),
            'status': room.status,
            'attached_context': attached,
            'detail': 'Mensaje registrado. Un agente humano atendera la sala de soporte.',
        }}, status=http_status.HTTP_201_CREATED)
