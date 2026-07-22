"""
Fase 12 AI Core -- Validacion funcional del Copilot de Soporte.

Primer test suite de `support`. A diferencia de otros `tests.py` del repo (que
usan `TransactionTestCase` sincrono, ej. `notifications/tests.py`), aqui se
prueba un WebSocket consumer real (`SupportChatConsumer`) con
`channels.testing.WebsocketCommunicator`, que corre en su propio hilo/loop --
requiere funciones async (`pytest-asyncio`, ya instalado sin uso previo en el
repo) y envolver cada acceso al ORM con `channels.db.database_sync_to_async`
(equivalente al motivo por el que `notifications` usa `TransactionTestCase` en
vez de `TestCase`: las escrituras deben ser visibles fuera de la transaccion
atomica de un solo hilo). `CHANNEL_LAYERS` usa Redis real (no hace falta un
`InMemoryChannelLayer` de test): estos tests corren dentro del contenedor
Docker (`docker compose exec django pytest support/tests.py`), donde Redis ya
esta arriba.

`ai_bridge.ask_ai()` (el unico punto de contacto con el AI Engine real) se
mockea siempre a nivel de `support.services.ai_bridge.requests.post` --mismo
patron que `notifications/tests.py::test_whatsapp_client_...` usa para
`requests.Session.post`-- para no depender de Ollama/latencia real. La
ejecucion real de Tools, latencia y disponibilidad se valida aparte con
`ai_engine/e2e_http/e2e_support_ai_chat_test.ps1` contra el stack vivo.
"""
import asyncio
import json
from unittest.mock import patch, MagicMock

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from rest_framework_simplejwt.tokens import AccessToken

from support.channels_auth import JWTAuthMiddlewareStack
from support.routing import support_websocket_patterns
from support.models import ChatRoom, ChatMessage, ChatRoomContext
from orders.models import Order

application = JWTAuthMiddlewareStack(URLRouter(support_websocket_patterns))

MOCK_METRICS = {
    'agent': 'SupportAgent', 'intent': 'unknown', 'llm_calls': 1,
    'llm_tokens_in': 120, 'llm_tokens_out': 30, 'tool_calls': 0,
    'tool_errors': 0, 'tools': [], 'fallback_used': False, 'handoff': None,
    'needs_confirmation': False, 'write_executed': False, 'duration_ms': 5,
}


# ── Helpers (envuelven ORM/creacion de tokens para uso desde tests async) ────

@database_sync_to_async
def _create_user(email, **kwargs):
    return get_user_model().objects.create_user(email=email, password='TestPass123!', **kwargs)


@database_sync_to_async
def _create_order(user, total=100000):
    return Order.objects.create(user=user, total_amount=total)


@database_sync_to_async
def _get_open_room(user):
    return ChatRoom.objects.get(user=user, status=ChatRoom.STATUS_OPEN)


@database_sync_to_async
def _count_open_rooms(user):
    return ChatRoom.objects.filter(user=user, status=ChatRoom.STATUS_OPEN).count()


@database_sync_to_async
def _count_contexts(room):
    return ChatRoomContext.objects.filter(room=room).count()


@database_sync_to_async
def _count_bot_messages():
    return ChatMessage.objects.filter(sender__email=settings.AI_BOT_EMAIL).count()


@database_sync_to_async
def _refresh(instance):
    instance.refresh_from_db()
    return instance


def _mock_response(payload: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    return resp


async def _connect_ws(user, extra_qs: str = ""):
    token = str(AccessToken.for_user(user))
    path = f"/ws/support/chat/?token={token}"
    if extra_qs:
        path += f"&{extra_qs}"
    from channels.testing import WebsocketCommunicator
    communicator = WebsocketCommunicator(application, path)
    connected, _ = await communicator.connect()
    assert connected, f"WebSocket no conecto para {user.email}"
    return communicator


# ── 1. Inicio de conversacion ────────────────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_inicio_conversacion_crea_sala_y_envia_historial():
    user = await _create_user('cliente.inicio@test.sintel')

    comm = await _connect_ws(user)
    history = json.loads(await comm.receive_from(timeout=5))
    assert history['type'] == 'history'
    assert history['messages'] == []
    assert await _count_open_rooms(user) == 1
    await comm.disconnect()

    # Reconectar reutiliza la sala OPEN existente, no crea una segunda.
    comm2 = await _connect_ws(user)
    await comm2.receive_from(timeout=5)
    assert await _count_open_rooms(user) == 1
    await comm2.disconnect()


# ── 2. Recuperacion de contexto del cliente ──────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_recuperacion_contexto_order_propia_y_ajena():
    owner = await _create_user('cliente.contexto@test.sintel')
    other = await _create_user('otro.cliente@test.sintel')
    own_order = await _create_order(owner)
    other_order = await _create_order(other)

    # Contexto propio: se vincula.
    comm = await _connect_ws(owner, f"context_type=ORDER&context_uuid={own_order.uuid}")
    history = json.loads(await comm.receive_from(timeout=5))
    assert len(history['contexts']) == 1
    assert history['contexts'][0]['uuid'] == str(own_order.uuid)
    room = await _get_open_room(owner)
    assert await _count_contexts(room) == 1
    await comm.disconnect()

    # Contexto ajeno (orden de otro usuario): NO se vincula, sigue en 1.
    comm2 = await _connect_ws(owner, f"context_type=ORDER&context_uuid={other_order.uuid}")
    await comm2.receive_from(timeout=5)
    assert await _count_contexts(room) == 1
    await comm2.disconnect()


# ── 3. Respuesta de IA + persistencia de telemetria (Fase 8) ────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('support.services.ai_bridge.requests.post')
async def test_respuesta_ia_persiste_texto_y_metrics(mock_post):
    user = await _create_user('cliente.ia@test.sintel')
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
        'confirmation': None, 'response': 'Hola, en que puedo ayudarte?',
        'metrics': MOCK_METRICS,
    })

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history
        await comm.send_to(text_data=json.dumps({'message': 'hola'}))
        await comm.receive_from(timeout=5)  # eco del propio mensaje
        ai_raw = json.loads(await comm.receive_from(timeout=10))
        assert ai_raw['message'] == 'Hola, en que puedo ayudarte?'
        await comm.disconnect()

    bot_msg = await database_sync_to_async(
        lambda: ChatMessage.objects.get(sender__email=settings.AI_BOT_EMAIL)
    )()
    assert bot_msg.ai_metrics == MOCK_METRICS


# ── 4. Flujo de confirmacion (Tool de escritura) ─────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('support.services.ai_bridge.requests.post')
async def test_flujo_confirmacion_escritura_dos_turnos(mock_post):
    user = await _create_user('cliente.confirma@test.sintel')
    metrics_pending = {**MOCK_METRICS, 'needs_confirmation': True}
    metrics_done = {**MOCK_METRICS, 'needs_confirmation': False, 'write_executed': True}
    mock_post.side_effect = [
        _mock_response({
            'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SalesAgent',
            'tool_calls': [], 'tool_results': [], 'needs_confirmation': True,
            'confirmation': {'question': 'Confirmas crear la cotizacion?'},
            'response': 'Confirmas crear la cotizacion?', 'metrics': metrics_pending,
        }),
        _mock_response({
            'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SalesAgent',
            'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
            'confirmation': None, 'response': 'Listo, cotizacion creada.',
            'metrics': metrics_done,
        }),
    ]

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history

        await comm.send_to(text_data=json.dumps({'message': 'crea una cotizacion'}))
        await comm.receive_from(timeout=5)  # eco
        turn1 = json.loads(await comm.receive_from(timeout=10))
        assert 'Confirmas' in turn1['message']

        await comm.send_to(text_data=json.dumps({'message': 'si'}))
        await comm.receive_from(timeout=5)  # eco
        turn2 = json.loads(await comm.receive_from(timeout=10))
        assert turn2['message'] == 'Listo, cotizacion creada.'
        await comm.disconnect()

    bot_msgs = await database_sync_to_async(
        lambda: list(ChatMessage.objects.filter(sender__email=settings.AI_BOT_EMAIL).order_by('created_at'))
    )()
    assert len(bot_msgs) == 2
    assert bot_msgs[0].ai_metrics['needs_confirmation'] is True
    assert bot_msgs[1].ai_metrics['write_executed'] is True


# ── 5. Escalamiento a humano (Human Handoff) ─────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('support.services.ai_bridge.requests.post')
async def test_human_handoff_pausa_sala_y_detiene_ia(mock_post):
    user = await _create_user('cliente.handoff@test.sintel')
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'response': 'Te transfiero con un agente humano.',
        'tool_results': [{'capability': 'abrir_ticket_soporte', 'result': {'ticket_id': 1}}],
        'needs_confirmation': False, 'confirmation': None,
        'metrics': {**MOCK_METRICS, 'handoff': 'SupportAgent->Human'},
    })

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history
        await comm.send_to(text_data=json.dumps({'message': 'quiero hablar con alguien'}))
        await comm.receive_from(timeout=5)  # eco
        await comm.receive_from(timeout=10)  # respuesta IA (escalando)

        room = await _get_open_room(user)
        room = await _refresh(room)
        assert room.ai_paused is True

        # Segundo mensaje del cliente: la IA ya no debe responder (sala pausada).
        await comm.send_to(text_data=json.dumps({'message': 'hola de nuevo'}))
        await comm.receive_from(timeout=5)  # eco del segundo mensaje humano
        with pytest.raises(asyncio.TimeoutError):
            await comm.receive_from(timeout=2)  # no debe llegar una 2da respuesta IA
        # No se llama a comm.disconnect() aca: tras un timeout esperado en
        # receive_from(), el future interno del comunicator queda cancelado y
        # un disconnect() posterior solo repropaga ese CancelledError (artefacto
        # de limpieza de channels.testing, no un bug de la app).

    assert mock_post.call_count == 1


# ── 6. Persistencia del historial tras reconexion ────────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_persistencia_historial_tras_reconexion():
    # AI_SUPPORT_CHAT_ENABLED puede ser True en el entorno real (.env) -- se
    # fuerza a False aqui porque este test no mockea ai_bridge y no debe
    # disparar una llamada real al AI Engine en segundo plano.
    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        user = await _create_user('cliente.historial@test.sintel')
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=5)  # history vacio
        await comm.send_to(text_data=json.dumps({'message': 'primer mensaje'}))
        await comm.receive_from(timeout=5)  # eco
        await comm.disconnect()

        comm2 = await _connect_ws(user)
        history = json.loads(await comm2.receive_from(timeout=5))
        assert len(history['messages']) == 1
        assert history['messages'][0]['message'] == 'primer mensaje'
        await comm2.disconnect()


# ── 7. Sincronizacion Dashboard admin <-> widget cliente ─────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_sincronizacion_dashboard_admin_y_widget_cliente():
    # Igual que en el test de persistencia: se fuerza AI_SUPPORT_CHAT_ENABLED a
    # False porque este test no mockea ai_bridge y el mensaje del cliente no
    # debe disparar una respuesta real de la IA que se mezcle con la respuesta
    # manual del admin en el mismo grupo.
    with override_settings(AI_SUPPORT_CHAT_ENABLED=False):
        client_user = await _create_user('cliente.sync@test.sintel')
        admin_user = await _create_user('admin.sync@test.sintel', is_staff=True, is_superuser=True)

        client_comm = await _connect_ws(client_user)
        await client_comm.receive_from(timeout=5)  # history
        admin_comm = await _connect_ws(admin_user)

        await client_comm.send_to(text_data=json.dumps({'message': 'hola admin'}))
        await client_comm.receive_from(timeout=5)  # eco propio del cliente

        admin_event = json.loads(await admin_comm.receive_from(timeout=5))
        assert admin_event['type'] == 'chat_message'
        assert admin_event['message'] == 'hola admin'
        room = await _get_open_room(client_user)
        assert admin_event['room_uuid'] == str(room.uuid)

        await admin_comm.send_to(text_data=json.dumps({
            'message': 'hola cliente', 'room_uuid': str(room.uuid),
        }))
        await admin_comm.receive_from(timeout=5)  # eco propio del admin

        client_event = json.loads(await client_comm.receive_from(timeout=5))
        assert client_event['message'] == 'hola cliente'
        assert client_event['is_admin'] is True

        await client_comm.disconnect()
        await admin_comm.disconnect()


# ── 8. Concurrencia -- multiples chats simultaneos ───────────────────────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
@patch('support.services.ai_bridge.requests.post')
async def test_concurrencia_multiples_chats_simultaneos(mock_post):
    # N=5 (no 8/10): en este entorno Docker/Windows el I/O de Postgres bajo
    # carga concurrente es medible (ver TRUNCATE entre tests, varios segundos
    # reales) -- 5 conexiones simultaneas siguen demostrando enrutamiento
    # correcto sin cruces, con menos contencion de thread pool que hacia el
    # test intermitente por timeout (nunca por un cruce real de sala).
    #
    # NOTA (Fase 12, verificado 2026-07-20): en este host este test fallo por
    # TimeoutError en ~1 de cada 5 corridas incluso con timeout=45s, siempre
    # esperando la respuesta IA de alguno de los N -- NUNCA por la aserción de
    # "cruce de sala" (la correctitud de enrutamiento nunca fallo en ~15
    # corridas). Es I/O real del entorno (Docker Desktop/Windows), no un bug
    # de `support`/`ai_engine`: si este test falla, reintentar antes de asumir
    # una regresion real.
    N = 5
    mock_post.return_value = _mock_response({
        'conversation_id': 'x', 'intent': 'unknown', 'agent': 'SupportAgent',
        'tool_calls': [], 'tool_results': [], 'needs_confirmation': False,
        'confirmation': None, 'response': 'Respuesta automatica de prueba.',
        'metrics': MOCK_METRICS,
    })
    users = [await _create_user(f'concurrente{i}@test.sintel') for i in range(N)]

    async def _flow(user):
        # Timeouts generosos (no una SLA de performance): con N conexiones
        # concurrentes, cada una con varias escrituras via
        # database_sync_to_async, el thread pool + I/O de Postgres puede
        # encolar bajo carga -- esto valida correctitud de enrutamiento
        # (sin cruces), no latencia.
        comm = await _connect_ws(user)
        await comm.receive_from(timeout=15)  # history
        await comm.send_to(text_data=json.dumps({'message': 'hola'}))
        await comm.receive_from(timeout=15)  # eco
        ai_event = json.loads(await comm.receive_from(timeout=45))
        room = await _get_open_room(user)
        assert ai_event['room_uuid'] == str(room.uuid), (
            f"cruce de sala detectado para {user.email}: "
            f"esperaba {room.uuid}, llego {ai_event['room_uuid']}"
        )
        await comm.disconnect()
        return room.uuid

    with override_settings(AI_SUPPORT_CHAT_ENABLED=True):
        room_uuids = await asyncio.gather(*[_flow(u) for u in users])

    assert len(set(room_uuids)) == N  # cada sala es unica, sin cruces
    assert await _count_bot_messages() == N


# ── 9. Analytics de conversaciones (Fase 9 AI Core -- Aprendizaje) ──────────
# Sincrono (sin WebSocket): ChatAnalyticsSelector solo lee ChatRoom/ChatMessage
# ya persistidos, no necesita Channels ni pytest-asyncio.

@pytest.mark.django_db
def test_analytics_summary_agrega_datos_reales():
    from support.services.selectors import ChatAnalyticsSelector

    User = get_user_model()
    user = User.objects.create_user(email='cliente.analytics@test.sintel', password='x')
    bot = User.objects.create_user(email='bot.analytics@test.sintel', password='x', is_active=False)

    room1 = ChatRoom.objects.create(user=user)
    room2 = ChatRoom.objects.create(user=User.objects.create_user(email='otro.analytics@test.sintel', password='x'))

    def _msg(room, **metrics_overrides):
        base = {
            'agent': 'SupportAgent', 'intent': 'unknown', 'llm_calls': 1,
            'llm_tokens_in': 0, 'llm_tokens_out': 0, 'tool_calls': 0,
            'tool_errors': 0, 'tools': [], 'fallback_used': False, 'handoff': None,
            'needs_confirmation': False, 'write_executed': False, 'duration_ms': 0,
        }
        base.update(metrics_overrides)
        return ChatMessage.objects.create(room=room, sender=bot, message='respuesta', ai_metrics=base)

    _msg(room1, intent='order_status', duration_ms=1000, llm_tokens_in=100, llm_tokens_out=20,
         tools=[{'tool': 'OrderStatusTool', 'ms': 50, 'ok': True}])
    _msg(room1, intent='order_status', duration_ms=2000, llm_tokens_in=200, llm_tokens_out=40,
         fallback_used=True, tools=[{'tool': 'OrderStatusTool', 'ms': 60, 'ok': True}])
    _msg(room2, intent='quotation_request', duration_ms=3000, llm_tokens_in=300, llm_tokens_out=60,
         handoff='SalesAgent->Human', tools=[{'tool': 'QuoteTemplatesTool', 'ms': 70, 'ok': True}])
    # Mensaje humano (ai_metrics=None) -- no debe contarse como turno de IA.
    ChatMessage.objects.create(room=room1, sender=user, message='hola', ai_metrics=None)

    summary = ChatAnalyticsSelector.get_summary(days=30)

    assert summary['total_conversations'] == 2
    assert summary['total_ai_turns'] == 3
    assert summary['avg_duration_ms'] == 2000.0
    assert summary['avg_tokens_in'] == 200.0
    assert summary['avg_tokens_out'] == 40.0
    assert summary['fallback_rate'] == round(1 / 3, 4)
    assert summary['handoff_rate'] == round(1 / 3, 4)
    assert {'intent': 'order_status', 'count': 2} in summary['intent_breakdown']
    assert {'intent': 'quotation_request', 'count': 1} in summary['intent_breakdown']
    assert {'tool': 'OrderStatusTool', 'count': 2} in summary['top_tools']
    assert {'intent': 'order_status', 'fallback_count': 1} in summary['frequent_issues']


# ── 10. CSAT -- calificar una conversacion cerrada ───────────────────────────
# Sincrono (sin WebSocket): ChatCommands.rate_conversation solo escribe en BD.

@pytest.mark.django_db
def test_rate_conversation_exito_y_validaciones():
    from support.services.commands import ChatCommands

    User = get_user_model()
    owner = User.objects.create_user(email='cliente.csat@test.sintel', password='x')
    other = User.objects.create_user(email='otro.csat@test.sintel', password='x')

    room_open = ChatRoom.objects.create(user=owner)
    with pytest.raises(ValueError, match='cerrada'):
        ChatCommands.rate_conversation(room_open, owner, rating=5)

    room = ChatRoom.objects.create(user=owner, status=ChatRoom.STATUS_CLOSED)

    with pytest.raises(ValueError, match='no es tuya'):
        ChatCommands.rate_conversation(room, other, rating=5)

    rated = ChatCommands.rate_conversation(room, owner, rating=4, comment='Buena atencion')
    assert rated.csat_rating == 4
    assert rated.csat_comment == 'Buena atencion'
    assert rated.csat_rated_at is not None

    with pytest.raises(ValueError, match='ya fue calificada'):
        ChatCommands.rate_conversation(room, owner, rating=1)


# ── 11. CSAT -- aviso en tiempo real de cierre de sala (room_closed) ─────────

@pytest.mark.asyncio
@pytest.mark.django_db(transaction=True)
async def test_room_closed_avisa_al_cliente_por_ws():
    from support.services.commands import ChatCommands

    user = await _create_user('cliente.roomclosed@test.sintel')
    comm = await _connect_ws(user)
    await comm.receive_from(timeout=5)  # history

    room = await _get_open_room(user)
    await database_sync_to_async(ChatCommands.close_room)(room)

    closed_event = json.loads(await comm.receive_from(timeout=5))
    assert closed_event['type'] == 'room_closed'
    assert closed_event['room_uuid'] == str(room.uuid)
    await comm.disconnect()
