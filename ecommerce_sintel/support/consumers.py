import asyncio
import json
from urllib.parse import parse_qs
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class SupportChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.user = user

        if user.is_staff and user.is_superuser:
            self.group_name = 'support_admins'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            self.room = await self._get_or_create_room()
            self.group_name = f'chat_{str(user.uuid)}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
            await self._attach_context_from_query_string()
            history = await self._get_room_history()
            contexts = await self._get_room_contexts()
            await self.send(text_data=json.dumps({
                'type': 'history',
                'room_uuid': str(self.room.uuid),
                'messages': history,
                'contexts': contexts,
            }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, TypeError):
            return

        text = str(data.get('message', '')).strip()
        if not text:
            return

        user = self.user

        if user.is_staff and user.is_superuser:
            room_uuid = data.get('room_uuid', '')
            if not room_uuid:
                return
            result = await self._get_room_and_client_uuid(room_uuid)
            if result is None:
                return
            room, client_uuid = result
            msg = await self._save_message(room, user, text)
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
            await self.send(text_data=json.dumps(payload))
        else:
            room = self.room
            msg = await self._save_message(room, user, text)
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
            await self.send(text_data=json.dumps(payload))

            # Fase 7 AI Core: si la sala esta en modo AI, el Action Graph
            # responde. En tarea aparte para no bloquear el socket (el LLM
            # puede tardar); si el motor no responde, el chat sigue normal
            # (un humano vera el mensaje en el panel igual que siempre).
            if await self._ai_mode_active(room):
                asyncio.create_task(self._ai_reply(room, text))

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

    # ── Fase 7 AI Core: modo AI del chat ─────────────────────────────────────

    @database_sync_to_async
    def _ai_mode_active(self, room):
        from support.services.ai_bridge import is_ai_mode_active
        room.refresh_from_db(fields=['status', 'ai_paused', 'assigned_admin'])
        return is_ai_mode_active(room)

    @database_sync_to_async
    def _ask_ai(self, room, text):
        from support.services.ai_bridge import ask_ai
        return ask_ai(self.user, text, conversation_id=f'room-{room.uuid}')

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

    async def _ai_reply(self, room, text):
        try:
            ai_response = await self._ask_ai(room, text)
            if not ai_response or not (ai_response.get('response') or '').strip():
                return
            msg, bot_email = await self._save_ai_message_and_maybe_pause(room, ai_response)
            payload = {
                'type': 'chat_message',
                'message': ai_response['response'],
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
            import logging
            logging.getLogger(__name__).exception('[support] error en respuesta AI')

    @database_sync_to_async
    def _get_or_create_room(self):
        from support.services.commands import ChatCommands
        return ChatCommands.get_or_create_room(self.user)

    @database_sync_to_async
    def _get_room_history(self):
        from django.conf import settings as dj_settings
        from support.services.selectors import ChatSelector
        msgs = ChatSelector.get_room_history(self.room)
        return [
            {
                'message': m.message,
                'sender_email': m.sender.email,
                # El bot IA se muestra del lado del agente en el widget
                'is_admin': bool(
                    (m.sender.is_staff and m.sender.is_superuser)
                    or m.sender.email == dj_settings.AI_BOT_EMAIL
                ),
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
        from support.services.selectors import ChatSelector
        contexts = ChatSelector.get_contexts_for_room(self.room)
        result = []
        for c in contexts:
            if c.context_type == c.CONTEXT_ORDER and c.order:
                result.append({'context_type': c.context_type, 'uuid': str(c.order.uuid), 'label': f'Pedido #{c.order.id}'})
            elif c.context_type == c.CONTEXT_RENTAL and c.rental_request:
                result.append({'context_type': c.context_type, 'uuid': str(c.rental_request.uuid), 'label': f'Alquiler #{c.rental_request.id}'})
        return result
