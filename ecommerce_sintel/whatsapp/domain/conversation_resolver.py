"""
whatsapp/domain/conversation_resolver.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 12
(2026-09-16). Resuelve `external_conversation_id` (lo que sea que un
adapter use -- el telefono E.164 en REST hoy) a una `ChatRoom` real de
SINTEL. El `ChatRoom` nunca sabe si el mensaje llego por QR o REST --
mismo objeto, mismo Service Layer de `support`, sin importar el adapter.

No reimplementa nada de `support` -- envuelve `ChatCommands` (Service
Layer real ya existente), mismo patron que ya usaba
notifications/tasks.py antes de esta mision.
"""
from support.services.commands import ChatCommands


class WhatsAppConversationResolver:
    @staticmethod
    def resolve_room(user):
        """Mismo ChatRoom compartido con el widget web y con el flujo de
        creacion de tickets desde el perfil (support/api/views.py) --
        WhatsApp no tiene su propia nocion de "sala", reusa la real de
        `support`."""
        return ChatCommands.get_or_create_room(user)
