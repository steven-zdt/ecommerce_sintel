"""
Puente Django -> AI Engine para los canales de la Fase 7 (AI Core).

Regla dura: sintel_ai NUNCA se expone a Internet -- el widget web (via
SupportChatConsumer) y WhatsApp (via webhook de notifications) llegan al
Action Graph a traves de estas funciones. Django es el emisor legitimo de
JWT (SimpleJWT), asi que aqui se acuna un access token efimero del usuario
real para autenticar la llamada -- nunca se persiste.
"""
import logging
import re
import time

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

AI_CHAT_TIMEOUT_SECONDS = 300  # LLM local puede tardar mas de un minuto

# C1 (auditoria enterprise, 2026-07-31): el unico throttle de IA existente (D-03,
# ScopedRateThrottle en AiOpenSupportTicketView) protege un endpoint interno secundario --
# SupportChatConsumer.receive() es el punto de entrada real que dispara ask_ai() por cada
# mensaje de cliente y no tenia ningun limite. Ventana fija por sala (no por usuario: una
# sala es la unidad de conversacion real, y evita que alguien la esquive abriendo salas
# nuevas -- get_or_create_room() reusa la sala OPEN existente).
AI_CHAT_RATE_LIMIT = 20
AI_CHAT_RATE_WINDOW_SECONDS = 600  # 10 min


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


def is_ai_rate_limited(room) -> bool:
    """True si la sala ya alcanzo AI_CHAT_RATE_LIMIT turnos de IA en la ventana actual.

    cache.add es atomico (evita una race condition get+set entre dos mensajes casi
    simultaneos) -- solo el primer caller de la ventana la crea, el resto solo incrementa.
    """
    key = f'support_ai_rate:{room.uuid}'
    cache.add(key, 0, timeout=AI_CHAT_RATE_WINDOW_SECONDS)
    count = cache.incr(key)
    if count > AI_CHAT_RATE_LIMIT:
        logger.warning('[ai_bridge] Rate limit de IA alcanzado para room=%s (%d turnos)', room.uuid, count)
        return True
    return False


_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]')


def _bound_response_text(text: str) -> str:
    """HARDENING F8/C2 (2026-09-24): segunda capa en la frontera de persistencia/entrega. Quita caracteres de control y acota el largo
    (WhatsApp admite ~4096) aunque el ADK cambie o se reemplace. El analisis de secretos/infraestructura/enlaces vive en el ADK (output_guard)."""
    text = _CONTROL_CHARS_RE.sub('', text or '')
    limit = getattr(settings, 'AI_OUTPUT_MAX_CHARS', 3800)
    if len(text) > limit:
        cut = text[:limit]
        boundary = max(cut.rfind('. '), cut.rfind(NL))
        text = (cut[: boundary + 1] if boundary >= int(limit * 0.75) else cut).rstrip() + '...'
    return text


NL = chr(10)


def _process_chat_response(resp, conversation_id: str, latency_ms: int) -> dict | None:
    """Logica de logging/parseo compartida entre ask_ai() y ask_ai_async() -- ambas
    reciben un objeto response ya resuelto (requests.Response o httpx.Response,
    misma interfaz .status_code/.text/.json() para lo que se usa aqui)."""
    if resp.status_code != 200:
        logger.warning(
            '[AI_BRIDGE] response status=%d conversation_id=%s latency_ms=%d body=%s',
            resp.status_code, conversation_id, latency_ms, resp.text[:200],
        )
        return None
    data = resp.json()
    if isinstance(data.get('response'), str):
        data['response'] = _bound_response_text(data['response'])
    metrics = data.get('metrics') or {}
    logger.info(
        '[AI_BRIDGE] response ok conversation_id=%s latency_ms=%d tokens=%s tools=%d agent=%s',
        conversation_id, latency_ms,
        metrics.get('tokens', metrics.get('total_tokens', '?')),
        len(data.get('tool_calls') or []), data.get('agent'),
    )
    return data


def build_ai_headers(token: str) -> dict:
    """Headers hacia el ADK: JWT del usuario + (F2) secreto de servicio si esta configurado."""
    headers = {'Authorization': f'Bearer {token}'}
    service_token = getattr(settings, 'AI_SERVICE_TOKEN', '')
    if service_token:
        headers['X-AI-Service-Token'] = service_token
    return headers


def ask_ai(user, message: str, conversation_id: str) -> dict | None:
    """
    Llama POST /chat del Action Graph en nombre del usuario real.
    Devuelve el dict de respuesta o None si el motor no esta disponible
    (el canal decide como degradar -- nunca rompe el chat).

    Variante SINCRONA -- usada por WhatsApp (notifications/tasks.py, tarea de Celery,
    sin event loop que proteger). El widget web usa ask_ai_async() en su lugar, ver
    docstring de esa funcion para el porque. El logging de REQUEST/RESPONSE/LATENCY/
    TOKENS/ERROR vive en _process_chat_response (FASE 4, auditoria 2026-08-07) -- una
    sola traza compartida entre ambas variantes, sin duplicar la instrumentacion.
    """
    from rest_framework_simplejwt.tokens import AccessToken

    token = str(AccessToken.for_user(user))
    start = time.monotonic()
    logger.info('[AI_BRIDGE] request conversation_id=%s user=%s', conversation_id, user.email)
    try:
        resp = requests.post(
            f"{settings.AI_ENGINE_URL}/chat",
            json={'message': message, 'conversation_id': conversation_id, 'channel': 'whatsapp'},  # ask_ai sync = WhatsApp
            headers=build_ai_headers(token),
            timeout=AI_CHAT_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            '[AI_BRIDGE] AI Engine inalcanzable conversation_id=%s latency_ms=%d error=%s: %s',
            conversation_id, latency_ms, type(exc).__name__, exc,
        )
        return None
    latency_ms = int((time.monotonic() - start) * 1000)
    return _process_chat_response(resp, conversation_id, latency_ms)


async def ask_ai_async(user, message: str, conversation_id: str) -> dict | None:
    """
    Variante ASYNC de ask_ai(), para SupportChatConsumer (Django Channels).

    Hallazgo de auditoria (AI_PROVIDER_RUNTIME_AUDIT.md seccion 7, 2026-08-13, cerrado
    2026-08-17): ask_ai() es un requests.post() sincrono con timeout de hasta
    AI_CHAT_TIMEOUT_SECONDS (300s). El consumer lo invocaba envuelto en
    @database_sync_to_async, que reusa el thread pool COMPARTIDO de asgiref para TODO
    el trabajo sync-to-async del proceso Daphne/Channels -- un turno de IA lento podia
    agotar ese pool y bloquear operaciones de DB de otras conexiones WS concurrentes
    (el B2 que el prompt maestro de esta auditoria senala como bloqueador antes de
    activar la IA ampliamente). httpx.AsyncClient hace la espera de red nativa del
    event loop, sin ocupar ningun thread del pool compartido mientras el AI Engine
    procesa el turno.
    """
    import httpx
    from rest_framework_simplejwt.tokens import AccessToken

    token = str(AccessToken.for_user(user))
    start = time.monotonic()
    logger.info('[AI_BRIDGE] request conversation_id=%s user=%s', conversation_id, user.email)
    try:
        async with httpx.AsyncClient(timeout=AI_CHAT_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                f"{settings.AI_ENGINE_URL}/chat",
                json={'message': message, 'conversation_id': conversation_id, 'channel': 'web'},
                headers=build_ai_headers(token),
            )
    except httpx.HTTPError as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            '[AI_BRIDGE] AI Engine inalcanzable conversation_id=%s latency_ms=%d error=%s: %s',
            conversation_id, latency_ms, type(exc).__name__, exc,
        )
        return None
    latency_ms = int((time.monotonic() - start) * 1000)
    return _process_chat_response(resp, conversation_id, latency_ms)


def ai_response_opened_ticket(ai_response: dict) -> bool:
    """True si en el turno se ejecuto abrir_ticket_soporte con exito (handoff)."""
    for item in ai_response.get('tool_results') or []:
        if not isinstance(item, dict) or item.get('capability') != 'abrir_ticket_soporte':
            continue
        result = item.get('result', {})
        if isinstance(result, dict) and not result.get('error'):
            return True
    return False
