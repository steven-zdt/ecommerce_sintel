"""
whatsapp/domain/service.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 7
(2026-09-16). UNICO punto de entrada de la logica de negocio real de
WhatsApp -- extraida tal cual (mismo comportamiento, mismo orden de
chequeos) de notifications/tasks.py::process_whatsapp_inbound_task /
send_whatsapp_agent_reply_task, que ahora delegan aqui (ver ese archivo).

Regla dura de la mision (seccion 1): CERO condicionales de infraestructura
aqui dentro -- este archivo NUNCA importa QRConnectionAdapter ni
RestConnectionAdapter, ni sabe cual esta activo. Recibe un
`WhatsAppConnectionPort` ya resuelto por `whatsapp/factory.py` (capa de
composicion).

WhatsApp nunca habla con el LLM/RAG/ADK directo (Regla FASE 16/17 de la
mision) -- todo pasa por support.services.ai_bridge, exactamente igual
que el widget web.
"""
import logging

from whatsapp.domain.contracts import WhatsAppOutboundMessage
from whatsapp.domain.conversation_resolver import WhatsAppConversationResolver
from whatsapp.domain.customer_resolver import WhatsAppCustomerResolver
from whatsapp.ports.connection import WhatsAppConnectionPort

logger = logging.getLogger("whatsapp.service")


class WhatsAppService:
    """Recibe el adapter por inyeccion -- NUNCA lo construye (Regla FASE 7
    de la mision: "Nunca debe hacer QRConnectionAdapter()/RestConnectionAdapter()
    internamente"). Ver whatsapp/factory.py para donde se decide cual."""

    def __init__(self, connection: WhatsAppConnectionPort):
        self._connection = connection

    def process_inbound_message(self, message, *, persist_inbound: bool = True) -> dict:
        """Devuelve un dict de resultado observable (para logging/metrics
        del caller, ver notifications/tasks.py) -- nunca lanza salvo que
        `ask_ai()` (Support Core) lo haga, deliberado: ese caso lo debe
        manejar el caller real (reintento de Celery), el dominio no conoce
        Celery.

        Deduplicacion (FASE 14 de la mision): NO se verifica aqui adentro
        -- vive en `whatsapp.domain.idempotency.WhatsAppIdempotencyGuard`,
        invocada UNA sola vez por el punto de entrada real de cada adapter
        (el webhook para REST, ver notifications/api/whatsapp_webhook.py)
        ANTES de siquiera encolar el procesamiento. Verificarlo de nuevo
        aqui rompería la idempotencia real (la primera invocacion legitima
        ya habria marcado la clave como vista). El mecanismo SI es
        provider-agnostic y vive en el dominio (Regla FASE 14) -- lo que
        cambia es DONDE se invoca, no donde vive el codigo."""
        user = WhatsAppCustomerResolver.resolve_user(message.sender_phone)
        if user is None:
            logger.warning(
                "[whatsapp.service] numero sin usuario asociado: ...%s", message.sender_phone[-4:],
            )
            return {"status": "no_user"}

        room = WhatsAppConversationResolver.resolve_room(user)

        from support.services.commands import ChatCommands

        if persist_inbound:
            # Fase 9 original (AUDITORIA/24_AUDITORIA_NOTIFICATIONS_SUPPORT.md):
            # solo en el primer intento real -- si ask_ai() falla mas abajo
            # y el caller reintenta, el mensaje del cliente no debe
            # duplicarse por cada reintento.
            ChatCommands.save_message(room, user, message.text)
            self._broadcast(room, user, message.text, user.email, is_admin=False)

        room.refresh_from_db(fields=["status", "ai_paused", "assigned_admin"])

        from support.services.ai_bridge import ask_ai, get_ai_bot_user, is_ai_mode_active, is_ai_rate_limited

        if not is_ai_mode_active(room):
            logger.info(
                "[whatsapp.service] IA inactiva para room=%s (handoff activo) -- sin auto-respuesta", room.uuid,
            )
            return {"status": "handoff_active", "room_uuid": str(room.uuid)}
        if is_ai_rate_limited(room):
            logger.warning(
                "[whatsapp.service] rate limit de IA alcanzado para room=%s -- sin auto-respuesta", room.uuid,
            )
            return {"status": "ai_rate_limited", "room_uuid": str(room.uuid)}

        # Deliberadamente SIN try/except -- un fallo de ask_ai() (Support
        # Core / ai_engine_adk) debe propagarse al caller real, que decide
        # si reintentar (Celery) o no (ver notifications/tasks.py).
        ai_response = ask_ai(user, message.text, conversation_id=f"wa-{user.id}")

        reply = (ai_response or {}).get("response") or ""
        if not reply.strip():
            logger.warning("[whatsapp.service] AI sin respuesta para user=%s", user.email)
            return {"status": "ai_empty_response", "room_uuid": str(room.uuid)}

        bot = get_ai_bot_user()
        msg = ChatCommands.save_message(room, bot, reply, ai_metrics=(ai_response or {}).get("metrics"))
        self._broadcast(room, user, reply, bot.email, is_admin=True, created_at=msg.created_at)

        outbound = WhatsAppOutboundMessage(
            external_conversation_id=message.external_conversation_id,
            recipient=message.sender_phone,
            text=reply,
        )
        try:
            external_id = self._connection.send_message(outbound)
        except Exception as exc:
            logger.error("[whatsapp.service] no se pudo responder por WhatsApp: %s", exc)
            return {"status": "send_failed", "room_uuid": str(room.uuid), "error": str(exc)}
        return {"status": "sent", "room_uuid": str(room.uuid), "external_message_id": external_id}

    def send_agent_reply(self, *, user, text: str) -> dict:
        """Reenvia por WhatsApp la respuesta de un agente HUMANO escrita
        desde /panel/soporte -- mismo bridge real que antes vivia en
        send_whatsapp_agent_reply_task. `_resolve_phone` se reusa tal cual
        de notifications/services/commands.py (compartida con el canal de
        notificaciones transaccionales, ver AUDITORIA/
        WHATSAPP_CONNECTION_BASELINE.md -- no se duplica)."""
        from notifications.services.commands import _resolve_phone

        phone = _resolve_phone(user)
        if not phone:
            return {"status": "no_phone"}

        outbound = WhatsAppOutboundMessage(
            external_conversation_id=phone,
            recipient=f"57{phone}",  # mismo prefijo de pais real que el codigo original
            text=text,
        )
        try:
            external_id = self._connection.send_message(outbound)
        except Exception as exc:
            logger.error("[whatsapp.service] no se pudo reenviar por WhatsApp a %s: %s", user.email, exc)
            return {"status": "send_failed", "error": str(exc)}
        return {"status": "sent", "external_message_id": external_id}

    @staticmethod
    def _broadcast(room, user, text: str, sender_email: str, *, is_admin: bool, created_at=None) -> None:
        """group_send plano (mismo formato que SupportChatConsumer.chat_message)
        -- extraido tal cual de notifications/tasks.py::_broadcast_chat_message,
        mismo comportamiento exacto."""
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        from django.utils import timezone

        layer = get_channel_layer()
        if layer is None:
            return
        payload = {
            "type": "chat.message",
            "message": text,
            "sender_email": sender_email,
            "is_admin": is_admin,
            "room_uuid": str(room.uuid),
            "created_at": (created_at or timezone.now()).isoformat(),
        }
        async_to_sync(layer.group_send)(f"chat_{str(user.uuid)}", payload)
        async_to_sync(layer.group_send)("support_admins", payload)
