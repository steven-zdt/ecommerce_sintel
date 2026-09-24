import asyncio
import json
import logging
import time
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

logger = logging.getLogger(__name__)


def _debug_preview(text: str) -> str:
    """FASE 2: sufijo con el contenido (truncado) para las trazas [CHAT], solo si
    SUPPORT_DEBUG_MODE=True -- por defecto los logs de produccion no llevan texto de
    conversaciones, solo metadatos (longitud, latencia, status)."""
    if not settings.SUPPORT_DEBUG_MODE or not text:
        return ''
    return ' text=%r' % text[:200]


class SupportChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            # FASE 2 (auditoria WS, 2026-08-07): antes un WSREJECT (code 4001) no dejaba
            # ningun rastro del lado de Django -- el unico log posible era el de
            # channels_auth (token rechazado) o ninguno si directamente faltaba el
            # parametro 'token'. Distingue "conecto sin auth" de "el JWT era invalido"
            # (ya cubierto en channels_auth.py).
            logger.warning('[WS] connect rechazado: sin usuario autenticado en scope')
            await self.close(code=4001)
            return

        self.user = user

        if user.is_staff and user.is_superuser:
            self.group_name = 'support_admins'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            logger.info('[WS] connect admin user=%s group=%s', user.email, self.group_name)
        else:
            self.room = await self._get_or_create_room()
            self.group_name = f'chat_{str(user.uuid)}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            await self._attach_context_from_query_string()
            history = await self._get_room_history()
            contexts = await self._get_room_contexts()
            logger.info(
                '[WS] connect client user=%s room=%s group=%s history=%d contexts=%d',
                user.email, self.room.uuid, self.group_name, len(history), len(contexts),
            )
            await self.send(text_data=json.dumps({
                'type': 'history',
                'room_uuid': str(self.room.uuid),
                'messages': history,
                'contexts': contexts,
            }))

    async def disconnect(self, close_code):
        # FASE 2: hasattr(self, 'group_name') es False solo si connect() rechazo la
        # conexion antes de llegar a group_add (ya logueado arriba) -- de lo contrario
        # siempre hay group_name, tanto para admin como para cliente.
        user_email = getattr(getattr(self, 'user', None), 'email', 'desconocido')
        logger.info(
            '[WS] disconnect user=%s group=%s code=%s',
            user_email, getattr(self, 'group_name', None), close_code,
        )
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            # FASE 3 (auditoria consumer, 2026-08-07): antes un frame no-JSON terminaba el
            # metodo en silencio total -- indistinguible de "no se recibio nada". No se
            # loguea text_data crudo (podria no ser JSON por diseno de terceros/bots, sin
            # valor diagnostico en el 99% de los casos y evita volcar payloads arbitrarios).
            logger.warning('[WS] receive: frame no-JSON descartado (len=%d)', len(text_data or ''))
            return

        # Repaso de backlog (AUDITORIA/18_AUDITORIA_PRODUCCION_RESILIENCIA_WS.md A2, 2026-08-03):
        # antes no habia NINGUN heartbeat de aplicacion -- una conexion zombie (TCP vivo pero
        # muerta de un lado, comun detras de proxies) podia quedar mostrando "en linea"
        # indefinidamente sin que nadie lo notara. No consume el rate-limit de flood ni pasa por
        # el resto de la logica de mensajes -- no es un mensaje de chat.
        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
            return

        from support.services.commands import MAX_MESSAGE_LENGTH
        text = str(data.get('message', '')).strip()[:MAX_MESSAGE_LENGTH]
        if not text:
            return

        # HARDENING F9: un request_id por mensaje del cliente (el WS es una sola peticion HTTP larga; sin esto
        # todos los mensajes compartirian id). Lo leen el filtro de logs y ai_bridge.build_ai_headers.
        from ai_engine_adk import observability_logging as obs
        obs.set_context(request_id=obs.new_request_id('ws'), session_id=None)

        user = self.user

        # Fase 11 (AUDITORIA/23_AUDITORIA_SEGURIDAD.md, 2026-08-01): antes esto no tenia NINGUN
        # limite de frecuencia -- distinto del rate-limit de turnos de IA (Fase 1 C1), que solo
        # protege las respuestas del LLM. Aplica a ambas ramas (cliente Y admin) por igual, antes
        # de cualquier escritura -- un mensaje descartado por flood ni se guarda ni se transmite.
        if await self._message_flood_limited(user):
            logger.warning('[WS] receive: flood-limited user=%s', user.email)
            return

        if user.is_staff and user.is_superuser:
            room_uuid = data.get('room_uuid', '')
            if not room_uuid:
                logger.warning('[WS] receive: admin user=%s sin room_uuid en el frame', user.email)
                return
            result = await self._get_room_and_client_uuid(room_uuid)
            if result is None:
                logger.warning(
                    '[WS] receive: admin user=%s room=%s no existe o no esta OPEN',
                    user.email, room_uuid,
                )
                return
            room, client_uuid = result
            msg = await self._save_message(room, user, text)
            logger.info(
                '[CHAT] room=%s user=%s message_len=%d is_admin=True status=sent%s',
                room.uuid, user.email, len(text), _debug_preview(text),
            )
            payload = {
                'type': 'chat_message',
                'message': text,
                'sender_email': user.email,
                'is_admin': True,
                'room_uuid': str(room.uuid),
                'created_at': msg.created_at.isoformat(),
            }
            await self.channel_layer.group_send(
                f'chat_{client_uuid}',
                {'type': 'chat.message', **payload},
            )
            # C2 (AUDITORIA/18, 2026-08-01): antes era self.send() directo -- solo la conexion
            # que envio el mensaje lo veia. Si el mismo admin tenia el dashboard abierto en 2
            # pestanas/dispositivos, o habia otro admin viendo la misma sala, esas otras
            # conexiones no se enteraban en vivo (solo al reseleccionar la sala). group_send a
            # 'support_admins' hace que el propio remitente reciba su eco por el mismo camino
            # que todos los demas admins conectados -- reproducible en produccion HOY, sin
            # depender de que la IA este activa.
            await self.channel_layer.group_send(
                'support_admins',
                {'type': 'chat.message', **payload},
            )

            # Fase 16 (AUDITORIA/30_AUDITORIA_PRUEBAS_E2E.md, 2026-08-03): antes la respuesta
            # del agente humano SOLO se difundia por WS -- un cliente que hablaba unicamente
            # por WhatsApp (sin el widget web abierto) nunca la recibia. Fire-and-forget: si el
            # usuario no tiene telefono valido o la ventana de 24h de Meta ya cerro, la tarea lo
            # resuelve/loggea sin bloquear ni afectar el WS (que ya entrego el mensaje).
            await self._dispatch_whatsapp_agent_reply(room.user_id, text)
        else:
            room = self.room
            if not await self._room_is_open(room):
                # B2 (auditoria enterprise, 2026-07-31): self.room se capturo una sola
                # vez en connect() y nunca se revalidaba -- a diferencia de la rama
                # admin (_get_room_and_client_uuid ya filtra status=OPEN), el cliente
                # podia seguir escribiendo en una sala ya CLOSED (mensaje sin ruta de
                # reapertura ni respuesta, ni humana ni de IA).
                logger.warning('[WS] receive: cliente user=%s room=%s ya no esta OPEN', user.email, room.uuid)
                return
            msg = await self._save_message(room, user, text)
            logger.info(
                '[CHAT] room=%s user=%s message_len=%d is_admin=False status=sent%s',
                room.uuid, user.email, len(text), _debug_preview(text),
            )
            payload = {
                'type': 'chat_message',
                'message': text,
                'sender_email': user.email,
                'is_admin': False,
                'room_uuid': str(room.uuid),
                'created_at': msg.created_at.isoformat(),
            }
            await self.channel_layer.group_send(
                'support_admins',
                {'type': 'chat.message', **payload},
            )
            # C2 (AUDITORIA/18, 2026-08-01): antes self.send() directo -- si el mismo cliente
            # tenia el chat abierto en 2 pestanas/dispositivos (ambos unidos a chat_{user.uuid}
            # en connect()), la otra pestana no se enteraba en vivo de un mensaje enviado desde
            # esta. group_send al propio grupo del usuario hace que TODAS sus conexiones (incluida
            # esta) reciban el eco por el mismo camino.
            await self.channel_layer.group_send(
                f'chat_{str(user.uuid)}',
                {'type': 'chat.message', **payload},
            )

            # Fase 7 AI Core: si la sala esta en modo AI, el Action Graph
            # responde. En tarea aparte para no bloquear el socket (el LLM
            # puede tardar); si el motor no responde, el chat sigue normal
            # (un humano vera el mensaje en el panel igual que siempre).
            # C1 (auditoria enterprise, 2026-07-31): el throttle de IA (D-03)
            # solo se habia aplicado al endpoint interno secundario
            # (AiOpenSupportTicketView) -- este WS es el punto de entrada real
            # que dispara el costo por mensaje, y no tenia ningun limite.
            ai_active = await self._ai_mode_active(room)
            if ai_active and not await self._ai_rate_limited(room):
                asyncio.create_task(self._ai_reply(room, text))
            elif ai_active:
                # FASE 3/4 (auditoria, 2026-08-07): antes el rate-limit de IA descartaba el
                # turno en silencio total del lado de logs -- is_ai_rate_limited() ya loguea
                # un warning en ai_bridge.py, pero no habia forma de correlacionarlo con la
                # sala/mensaje concreto que lo disparo desde este lado.
                logger.info('[CHAT] room=%s user=%s AI rate-limited status=skipped', room.uuid, user.email)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender_email': event['sender_email'],
            'is_admin': event['is_admin'],
            'room_uuid': event['room_uuid'],
            'created_at': event['created_at'],
        }))

    # CSAT: aviso en tiempo real de que la sala se cerro (ChatCommands.close_room),
    # para que el widget del cliente ofrezca calificar la conversacion.
    async def room_closed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'room_closed',
            'room_uuid': event['room_uuid'],
        }))

    # Fase 17 de PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md -- "el
    # frontend no debe consultar el gateway directamente... Vue -> Django
    # Channels -> Gateway". Reusa el heartbeat/reconexion YA existente de
    # este mismo consumer (grupo 'support_admins', el mismo que ya usa
    # SupportDashboardView.vue) en vez de crear un consumer/ruta WS nueva --
    # "el heartbeat WebSocket existente de soporte debe mantenerse" (regla
    # explicita de esa fase). Broadcast real disparado desde
    # notifications/api/whatsapp_gateway_webhook.py.
    async def whatsapp_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'whatsapp_status',
            'status': event['status'],
            'phone': event.get('phone'),
            'jid': event.get('jid'),
        }))

    async def whatsapp_qr(self, event):
        await self.send(text_data=json.dumps({
            'type': 'whatsapp_qr',
            'qr_image': event.get('qr_image'),
        }))

    # ── Fase 7 AI Core: modo AI del chat ─────────────────────────────────────

    @database_sync_to_async
    def _room_is_open(self, room) -> bool:
        room.refresh_from_db(fields=['status'])
        return room.status == room.STATUS_OPEN

    @database_sync_to_async
    def _message_flood_limited(self, user) -> bool:
        from support.services.commands import ChatCommands
        return ChatCommands.is_message_flood_limited(user)

    @database_sync_to_async
    def _dispatch_whatsapp_agent_reply(self, user_id, text):
        from notifications.tasks import send_whatsapp_agent_reply_task
        send_whatsapp_agent_reply_task.delay(user_id=user_id, text=text)

    @database_sync_to_async
    def _ai_mode_active(self, room):
        from support.services.ai_bridge import is_ai_mode_active
        room.refresh_from_db(fields=['status', 'ai_paused', 'assigned_admin'])
        return is_ai_mode_active(room)

    @database_sync_to_async
    def _ai_rate_limited(self, room) -> bool:
        """Limite por sala sobre los turnos que realmente disparan al LLM (costo real por
        mensaje) -- el mensaje del cliente ya se guardo y se muestra igual; esto solo
        evita que el AI Engine responda mas de AI_CHAT_RATE_LIMIT veces por ventana."""
        from support.services.ai_bridge import is_ai_rate_limited
        return is_ai_rate_limited(room)

    async def _ask_ai(self, room, text):
        # No @database_sync_to_async: ask_ai_async() no toca el ORM (room.uuid ya esta
        # cargado en memoria), y evita ocupar el thread pool compartido de
        # sync_to_async con una llamada de red que puede tardar hasta
        # AI_CHAT_TIMEOUT_SECONDS -- ver docstring de ask_ai_async en ai_bridge.py.
        from support.services.ai_bridge import ask_ai_async
        return await ask_ai_async(self.user, text, conversation_id=f'room-{room.uuid}')

    @database_sync_to_async
    def _save_ai_message_and_maybe_pause(self, room, ai_response):
        from support.services.ai_bridge import ai_response_opened_ticket, get_ai_bot_user
        from support.services.commands import ChatCommands
        bot = get_ai_bot_user()
        msg = ChatCommands.save_message(
            room, bot, ai_response.get('response') or '',
            ai_metrics=ai_response.get('metrics'),
        )
        if ai_response_opened_ticket(ai_response):
            # Human Handoff: el AI escalo -- deja de responder en esta sala.
            room.ai_paused = True
            room.save(update_fields=['ai_paused', 'updated_at'])
        return msg, bot.email

    @database_sync_to_async
    def _save_ai_degraded_marker(self, room):
        from support.services.ai_bridge import get_ai_bot_user
        from support.services.commands import ChatCommands
        bot = get_ai_bot_user()
        msg = ChatCommands.save_message(
            room, bot,
            'En este momento nuestro asistente no está disponible. '
            'Un agente humano revisará tu mensaje pronto.',
            ai_metrics={'engine_unavailable': True},
        )
        return msg, bot.email

    async def _ai_reply(self, room, text):
        # FASE 3/4/12 (auditoria, 2026-08-07): unico punto donde se puede medir de punta a
        # punta REQUEST -> RESPONSE -> LATENCY -> TOOLS -> STATUS de un turno de IA. Antes
        # solo existia logging en la rama de excepcion -- un turno lento o degradado (sin
        # excepcion) no dejaba ningun rastro de tiempo ni de que herramientas se ejecutaron.
        start = time.monotonic()
        logger.info('[CHAT] room=%s AI request status=started', room.uuid)
        try:
            ai_response = await self._ask_ai(room, text)
            latency_ms = int((time.monotonic() - start) * 1000)
            if not ai_response or not (ai_response.get('response') or '').strip():
                # C2 (auditoria enterprise, 2026-07-31): antes esto retornaba en
                # silencio total -- una caida del AI Engine no dejaba ninguna senal,
                # ni para el cliente (chat mudo) ni para las metricas del dashboard
                # (ChatAnalyticsSelector solo agregaba turnos ya persistidos).
                # Persistir un marcador degradado (ai_metrics.engine_unavailable)
                # y avisar, igual que un turno de IA normal.
                msg, bot_email = await self._save_ai_degraded_marker(room)
                response_text = msg.message
                logger.warning(
                    '[CHAT] room=%s AI response=empty latency_ms=%d status=degraded',
                    room.uuid, latency_ms,
                )
            else:
                msg, bot_email = await self._save_ai_message_and_maybe_pause(room, ai_response)
                response_text = ai_response['response']
                metrics = ai_response.get('metrics') or {}
                tool_calls = ai_response.get('tool_calls') or []
                logger.info(
                    '[CHAT] room=%s AI agent=%s intent=%s tools=%d tokens=%s latency_ms=%d status=ok%s',
                    room.uuid, ai_response.get('agent'), ai_response.get('intent'),
                    len(tool_calls), metrics.get('tokens', metrics.get('total_tokens', '?')),
                    latency_ms, _debug_preview(response_text),
                )
                from support.services.ai_bridge import ai_response_opened_ticket
                if ai_response_opened_ticket(ai_response):
                    logger.info('[CHAT] room=%s AI handoff status=escalated', room.uuid)
            payload = {
                'type': 'chat_message',
                'message': response_text,
                'sender_email': bot_email,
                'is_admin': True,   # el widget lo muestra del lado del agente
                'room_uuid': str(room.uuid),
                'created_at': msg.created_at.isoformat(),
            }
            await self.channel_layer.group_send(
                f'chat_{str(self.user.uuid)}',
                {'type': 'chat.message', **payload},
            )
            # Supervision humana: los admins ven la conversacion IA en vivo.
            await self.channel_layer.group_send(
                'support_admins',
                {'type': 'chat.message', **payload},
            )
        except Exception:
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.exception('[CHAT] room=%s AI error latency_ms=%d status=exception', room.uuid, latency_ms)

    @database_sync_to_async
    def _get_or_create_room(self):
        from support.services.commands import ChatCommands
        return ChatCommands.get_or_create_room(self.user)

    @database_sync_to_async
    def _get_room_history(self):
        from support.services.selectors import ChatSelector
        msgs = ChatSelector.get_room_history(self.room)
        return [
            {
                'message': m.message,
                'sender_email': m.sender.email,
                'is_admin': m.is_from_agent,
                'created_at': m.created_at.isoformat(),
            }
            for m in msgs
        ]

    @database_sync_to_async
    def _save_message(self, room, sender, text: str):
        from support.services.commands import ChatCommands
        return ChatCommands.save_message(room, sender, text)

    @database_sync_to_async
    def _get_room_and_client_uuid(self, room_uuid: str):
        from support.models import ChatRoom
        try:
            room = ChatRoom.objects.select_related('user').get(
                uuid=room_uuid,
                status=ChatRoom.STATUS_OPEN,
                is_deleted=False,
            )
            return room, str(room.user.uuid)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def _attach_context_from_query_string(self):
        """
        Fase 3 (Customer Experience Hub): si el widget conecta con
        ?context_type=ORDER&context_uuid=... (botón "¿Necesitas ayuda?" en una orden/alquiler
        propios), vincula la sala automáticamente -- valida que la entidad pertenezca al
        usuario conectado antes de vincular.
        """
        from support.models import ChatRoomContext
        from support.services.commands import ChatCommands

        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        context_type = (params.get('context_type', [''])[0] or '').upper()
        context_uuid = params.get('context_uuid', [''])[0]
        if not context_type or not context_uuid:
            return

        if context_type == ChatRoomContext.CONTEXT_ORDER:
            from orders.models import Order
            order = Order.objects.filter(uuid=context_uuid, user=self.user, is_deleted=False).first()
            if order:
                ChatCommands.attach_context(self.room, ChatRoomContext.CONTEXT_ORDER, order=order, added_by=self.user)
        elif context_type == ChatRoomContext.CONTEXT_RENTAL:
            from renting.models import RentalRequest
            rental = RentalRequest.objects.filter(uuid=context_uuid, user=self.user, is_deleted=False).first()
            if rental:
                ChatCommands.attach_context(self.room, ChatRoomContext.CONTEXT_RENTAL, rental_request=rental, added_by=self.user)

    @database_sync_to_async
    def _get_room_contexts(self):
        # D1 (auditoria enterprise, 2026-07-31): ChatRoomContext.target_uuid/.label son
        # ahora la unica fuente de verdad, reusada por ChatRoomContextSerializer (payload
        # REST equivalente).
        from support.services.selectors import ChatSelector
        contexts = ChatSelector.get_contexts_for_room(self.room)
        return [
            {'context_type': c.context_type, 'uuid': c.target_uuid, 'label': c.label}
            for c in contexts if c.target_uuid
        ]
