from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from support.models import ChatRoom, ChatMessage, ChatRoomContext, SupportTicket

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


class SupportTicketCommands:

    @staticmethod
    @transaction.atomic
    def create_ticket(room: ChatRoom, subject: str = '', summary: str = '',
                       category: str = '', contact_phone: str = '', contact_email: str = '') -> SupportTicket:
        """
        Idempotente por sala: una ChatRoom nunca tiene mas de un SupportTicket
        (OneToOne). Si ya existe (ej. el cliente vuelve a escribir y el AI
        vuelve a invocar la Tool sobre la misma sala ya escalada), actualiza
        subject/summary/category solo si venian vacios -- nunca pisa lo que
        un humano ya haya editado despues.
        """
        existing = SupportTicket.objects.filter(chat_room=room).first()
        if existing:
            update_fields = []
            if subject and not existing.subject:
                existing.subject = subject
                update_fields.append('subject')
            if summary and not existing.summary:
                existing.summary = summary
                update_fields.append('summary')
            if category and not existing.category:
                existing.category = category
                update_fields.append('category')
            if update_fields:
                update_fields.append('updated_at')
                existing.save(update_fields=update_fields)
            return existing

        ticket = SupportTicket.objects.create(
            chat_room=room, subject=subject, summary=summary, category=category,
            contact_phone=contact_phone, contact_email=contact_email,
        )
        ticket.ticket_number = f'SUP-{ticket.pk:06d}'
        ticket.save(update_fields=['ticket_number', 'updated_at'])
        return ticket

    @staticmethod
    @transaction.atomic
    def assign_ticket(ticket: SupportTicket, admin) -> SupportTicket:
        ticket.assigned_admin = admin
        if ticket.status == SupportTicket.STATUS_NEW:
            ticket.status = SupportTicket.STATUS_OPEN
        ticket.save(update_fields=['assigned_admin', 'status', 'updated_at'])
        return ticket

    @staticmethod
    @transaction.atomic
    def change_status(ticket: SupportTicket, status: str) -> SupportTicket:
        if status not in dict(SupportTicket.STATUS_CHOICES):
            raise ValueError(f'Estado invalido: {status}')
        ticket.status = status
        update_fields = ['status', 'updated_at']
        if status == SupportTicket.STATUS_RESOLVED and ticket.resolved_at is None:
            ticket.resolved_at = timezone.now()
            update_fields.append('resolved_at')
        if status == SupportTicket.STATUS_CLOSED and ticket.closed_at is None:
            ticket.closed_at = timezone.now()
            update_fields.append('closed_at')
        ticket.save(update_fields=update_fields)
        return ticket

    @staticmethod
    @transaction.atomic
    def set_priority(ticket: SupportTicket, priority: str) -> SupportTicket:
        if priority not in dict(SupportTicket.PRIORITY_CHOICES):
            raise ValueError(f'Prioridad invalida: {priority}')
        ticket.priority = priority
        ticket.save(update_fields=['priority', 'updated_at'])
        return ticket
