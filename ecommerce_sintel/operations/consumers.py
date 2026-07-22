import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class OperationTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket para tracking en tiempo real de un ticket especifico.
    URL: ws/operations/<ticket_uuid>/
    Usa JWTAuthMiddleware (mismo patron que support/consumers.py).
    Solo acepta conexiones del cliente propietario o admins.
    """

    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4001)
            return

        self.ticket_uuid = self.scope['url_route']['kwargs']['ticket_uuid']
        self.group_name  = f'user_{user.uuid}'

        # Verificar que el usuario puede ver este ticket
        from channels.db import database_sync_to_async
        allowed = await database_sync_to_async(_check_ticket_access)(
            self.ticket_uuid, user
        )
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(
            "OperationTrackingConsumer conectado | ticket=%s user=%s",
            self.ticket_uuid, user.pk,
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Solo lectura; el cliente no envia mensajes
        pass

    # Manejador de mensajes de grupo → cliente
    async def operation_tracking_update(self, event):
        await self.send(text_data=json.dumps(event['payload']))

    async def _send_tracking_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'tracking_update',
            'event': event.get('payload', {}),
        }))

    async def operation_created(self, event):
        await self._send_tracking_update(event)

    async def operation_assigned(self, event):
        await self._send_tracking_update(event)

    async def operation_scheduled(self, event):
        await self._send_tracking_update(event)

    async def operation_en_route(self, event):
        await self._send_tracking_update(event)

    async def operation_in_progress(self, event):
        await self._send_tracking_update(event)

    async def operation_completed(self, event):
        await self._send_tracking_update(event)

    async def operation_cancelled(self, event):
        await self._send_tracking_update(event)


def _check_ticket_access(ticket_uuid: str, user) -> bool:
    from operations.models import OperationTicket
    try:
        ticket = OperationTicket.objects.get(uuid=ticket_uuid, is_deleted=False)
        if user.is_staff and user.is_superuser:
            return True
        return ticket.customer_id == user.pk
    except OperationTicket.DoesNotExist:
        return False
