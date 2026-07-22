import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        # Default group for all management users
        await self.channel_layer.group_add("sintel_notifications", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("sintel_notifications", self.channel_name)

    async def receive(self, text_data):
        # Placeholder for receiving messages from client
        pass

    async def send_notification(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
