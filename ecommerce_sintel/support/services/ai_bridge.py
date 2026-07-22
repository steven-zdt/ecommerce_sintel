"""
Puente Django -> AI Engine para los canales de la Fase 7 (AI Core).

Regla dura: sintel_ai NUNCA se expone a Internet -- el widget web (via
SupportChatConsumer) y WhatsApp (via webhook de notifications) llegan al
Action Graph a traves de estas funciones. Django es el emisor legitimo de
JWT (SimpleJWT), asi que aqui se acuna un access token efimero del usuario
real para autenticar la llamada -- nunca se persiste.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

AI_CHAT_TIMEOUT_SECONDS = 300  # LLM local puede tardar mas de un minuto


def get_ai_bot_user():
    """
    Usuario que firma los mensajes del asistente (ChatMessage.sender es NOT
    NULL). Inactivo y con password inutilizable: no puede autenticarse ni
    obtener tokens jamas.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    bot, created = User.objects.get_or_create(
        email=settings.AI_BOT_EMAIL,
        defaults={'is_active': False},
    )
    if created:
        bot.set_unusable_password()
        bot.save(update_fields=['password'])
    return bot


def is_ai_mode_active(room) -> bool:
    """El AI atiende la sala solo si nadie la escalo ni la tomo un humano."""
    return (
        settings.AI_SUPPORT_CHAT_ENABLED
        and room.status == room.STATUS_OPEN
        and not room.ai_paused
        and room.assigned_admin_id is None
    )


def ask_ai(user, message: str, conversation_id: str) -> dict | None:
    """
    Llama POST /chat del Action Graph en nombre del usuario real.
    Devuelve el dict de respuesta o None si el motor no esta disponible
    (el canal decide como degradar -- nunca rompe el chat).
    """
    from rest_framework_simplejwt.tokens import AccessToken

    token = str(AccessToken.for_user(user))
    try:
        resp = requests.post(
            f"{settings.AI_ENGINE_URL}/chat",
            json={'message': message, 'conversation_id': conversation_id},
            headers={'Authorization': f'Bearer {token}'},
            timeout=AI_CHAT_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.warning('[ai_bridge] AI Engine inalcanzable: %s', exc)
        return None
    if resp.status_code != 200:
        logger.warning('[ai_bridge] AI Engine respondio %s: %s', resp.status_code, resp.text[:200])
        return None
    return resp.json()


def ai_response_opened_ticket(ai_response: dict) -> bool:
    """True si en el turno se ejecuto abrir_ticket_soporte con exito (handoff)."""
    for item in ai_response.get('tool_results') or []:
        if not isinstance(item, dict) or item.get('capability') != 'abrir_ticket_soporte':
            continue
        result = item.get('result', {})
        if isinstance(result, dict) and not result.get('error'):
            return True
    return False
