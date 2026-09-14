from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from support.models import ChatRoom, ChatMessage, ChatRoomContext

# Fase 11 (AUDITORIA/23_AUDITORIA_SEGURIDAD.md, 2026-08-01): antes SupportChatConsumer.receive()
# no tenia NINGUN limite de frecuencia ni de tamano por mensaje -- distinto del rate-limit de
# turnos de IA (ai_bridge.is_ai_rate_limited, Fase 1 C1), que solo protege las respuestas del
# LLM. Un cliente podia inundar la BD (un ChatMessage por frame WS, sin tope) y a TODOS los
# admins conectados (cada mensaje hace group_send a 'support_admins') con mensajes ilimitados en
# frecuencia y tamano. MAX_MESSAGE_LENGTH coincide con el limite ya establecido del lado de
# ai_engine (ChatRequest.message, Fase 2 G1) por consistencia, no por casualidad.
MAX_MESSAGE_LENGTH = 4000
MESSAGE_FLOOD_LIMIT = 30
MESSAGE_FLOOD_WINDOW_SECONDS = 60


class ChatCommands:

    @staticmethod
    def is_message_flood_limited(user) -> bool:
        """Ventana fija por usuario (no por sala/conexion -- un usuario puede tener varias
        conexiones, ver C2 de AUDITORIA/18) sobre la frecuencia CRUDA de mensajes WS, sin
        importar si disparan IA o no. cache.add es atomico, mismo patron que
        ai_bridge.is_ai_rate_limited."""
        key = f'support_msg_flood:{user.id}'
        cache.add(key, 0, timeout=MESSAGE_FLOOD_WINDOW_SECONDS)
        count = cache.incr(key)
        return count > MESSAGE_FLOOD_LIMIT

    @staticmethod
    @transaction.atomic
    def get_or_create_room(user) -> ChatRoom:
        room = ChatRoom.objects.filter(
            user=user, status=ChatRoom.STATUS_OPEN, is_deleted=False
        ).first()
        if room:
            return room
        return ChatRoom.objects.create(user=user)

    @staticmethod
    @transaction.atomic
    def save_message(room: ChatRoom, sender, text: str, ai_metrics: dict | None = None) -> ChatMessage:
        msg = ChatMessage.objects.create(room=room, sender=sender, message=text, ai_metrics=ai_metrics)
        ChatRoom.objects.filter(pk=room.pk).update(updated_at=msg.created_at)
        return msg

    @staticmethod
    @transaction.atomic
    def close_room(room: ChatRoom) -> ChatRoom:
        room.status = ChatRoom.STATUS_CLOSED
        room.save(update_fields=['status', 'updated_at'])

        # CSAT: avisa al widget del cliente en tiempo real para que ofrezca
        # calificar la conversacion -- mismo patron de
        # notifications/tasks.py::ai_proactive_room_message_task
        # (async_to_sync + group_send plano, imports diferidos).
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(f'chat_{str(room.user.uuid)}', {
                'type': 'room.closed',
                'room_uuid': str(room.uuid),
            })
        return room

    @staticmethod
    @transaction.atomic
    def rate_conversation(room: ChatRoom, user, rating: int, comment: str = '') -> ChatRoom:
        """
        CSAT: el cliente califica una conversacion ya cerrada (1-5 + comentario
        opcional). Mismo patron de validacion (ownership + estado terminal)
        que renting.EquipmentReviewCommands.create_review().
        """
        if room.user_id != user.id:
            raise ValueError('No podes calificar una conversacion que no es tuya.')
        if room.status != ChatRoom.STATUS_CLOSED:
            raise ValueError('Solo podes calificar una conversacion cerrada.')
        if room.csat_rating is not None:
            raise ValueError('Esta conversacion ya fue calificada.')

        room.csat_rating = rating
        room.csat_comment = comment
        room.csat_rated_at = timezone.now()
        room.save(update_fields=['csat_rating', 'csat_comment', 'csat_rated_at', 'updated_at'])
        return room

    @staticmethod
    @transaction.atomic
    def assign_admin(room: ChatRoom, admin) -> ChatRoom:
        room.assigned_admin = admin
        room.save(update_fields=['assigned_admin', 'updated_at'])
        return room

    @staticmethod
    @transaction.atomic
    def mark_messages_read(room: ChatRoom, reader) -> None:
        ChatMessage.objects.filter(
            room=room, is_read=False
        ).exclude(sender=reader).update(is_read=True)

    @staticmethod
    @transaction.atomic
    def attach_context(room: ChatRoom, context_type: str, order=None, rental_request=None, added_by=None) -> ChatRoomContext | None:
        """
        Vincula la sala a un pedido o alquiler (Customer Experience Hub). Idempotente: si
        ya existe el mismo vinculo para esta sala, no crea uno duplicado.
        """
        if context_type == ChatRoomContext.CONTEXT_ORDER:
            if order is None:
                return None
            existing = ChatRoomContext.objects.filter(room=room, context_type=context_type, order=order).first()
            if existing:
                return existing
            return ChatRoomContext.objects.create(room=room, context_type=context_type, order=order, added_by=added_by)
        elif context_type == ChatRoomContext.CONTEXT_RENTAL:
            if rental_request is None:
                return None
            existing = ChatRoomContext.objects.filter(room=room, context_type=context_type, rental_request=rental_request).first()
            if existing:
                return existing
            return ChatRoomContext.objects.create(room=room, context_type=context_type, rental_request=rental_request, added_by=added_by)
        return None
