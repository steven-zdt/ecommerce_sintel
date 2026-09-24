import logging

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from support.models import ChatRoom, ChatMessage, ChatRoomContext, SupportTicket

logger = logging.getLogger(__name__)

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
    def pause_ai_for_human_takeover(room: ChatRoom) -> bool:
        """
        HARDENING F18: un agente humano respondio en la sala => la IA deja de contestar automaticamente (hasta reactivacion EXPLICITA con
        resume_ai). UPDATE atomico y condicional (no depende de una instancia `room` posiblemente vieja). True si cambio el estado.
        """
        changed = ChatRoom.objects.filter(pk=room.pk, ai_paused=False).update(ai_paused=True, updated_at=timezone.now())
        if changed:
            room.ai_paused = True
        return bool(changed)

    @staticmethod
    @transaction.atomic
    def resume_ai(room: ChatRoom, admin) -> ChatRoom:
        """
        HARDENING F18: reactivacion EXPLICITA de la IA en una sala (el unico camino: antes nada volvia a poner ai_paused=False). Solo salas
        abiertas; libera tambien la asignacion (is_ai_mode_active exige `assigned_admin is None`). Deja un mensaje visible del asistente.
        """
        if room.status != ChatRoom.STATUS_OPEN:
            raise ValueError('Solo se puede reactivar el asistente en una sala abierta.')
        room.ai_paused = False
        room.assigned_admin = None
        room.save(update_fields=['ai_paused', 'assigned_admin', 'updated_at'])

        from support.services.ai_bridge import get_ai_bot_user
        text = 'El asistente virtual volvio a atender esta conversacion. Si necesitas a una persona, solo dilo.'
        msg = ChatCommands.save_message(room, get_ai_bot_user(), text)
        logger.info('ai_operation_event=ai_resumed room=%s admin=%s', room.uuid, getattr(admin, 'email', '?'))

        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        if layer is not None:
            payload = {'type': 'chat.message', 'message': text, 'sender_email': get_ai_bot_user().email, 'is_admin': True,
                       'room_uuid': str(room.uuid), 'created_at': msg.created_at.isoformat()}
            async_to_sync(layer.group_send)(f'chat_{str(room.user.uuid)}', payload)
            async_to_sync(layer.group_send)('support_admins', payload)
        return room

    @staticmethod
    def alert_admins_ai_degraded(room: ChatRoom, reason: str = 'degraded') -> bool:
        """
        HARDENING F18: el asistente dijo "un agente humano revisara tu mensaje" pero nadie era avisado. Aviso en vivo al grupo support_admins,
        con cooldown por sala (cache.add atomico) para no inundar durante una caida. True si se envio. Nunca rompe el chat.
        """
        from django.conf import settings
        if not getattr(settings, 'AI_DEGRADED_ADMIN_ALERT', True):
            return False
        try:
            cooldown = int(getattr(settings, 'AI_DEGRADED_ALERT_COOLDOWN_SECONDS', 900))
            if not cache.add(f'support_ai_degraded_alert:{room.uuid}', 1, timeout=cooldown):
                return False
            from support.api.internal_ai import _notify_support_admins
            _notify_support_admins(room, room.user, 'El asistente no pudo responder este mensaje; requiere atencion humana.',
                                   label='[Asistente no disponible]')
            logger.warning('ai_operation_event=ai_degraded_admin_alert room=%s reason=%s', room.uuid, reason)
            return True
        except Exception:  # noqa: BLE001 -- un aviso fallido no debe romper el turno
            logger.exception('[SUPPORT] no se pudo avisar a los admins del turno degradado room=%s', getattr(room, 'uuid', '?'))
            return False

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
