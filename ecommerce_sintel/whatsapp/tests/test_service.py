"""
whatsapp/tests/test_service.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp" (2026-09-16).
Cubre WhatsAppService/resolvers/idempotency con el mismo comportamiento
real que tenia notifications/tasks.py::process_whatsapp_inbound_task antes
de la extraccion -- estos tests son la regresion de que la migracion no
cambio nada observable.
"""
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from support.models import ChatRoom
from whatsapp.adapters.rest_adapter import RestConnectionAdapter
from whatsapp.domain.contracts import MessageType, WhatsAppInboundMessage
from whatsapp.domain.conversation_resolver import WhatsAppConversationResolver
from whatsapp.domain.customer_resolver import WhatsAppCustomerResolver
from whatsapp.domain.idempotency import WhatsAppIdempotencyGuard
from whatsapp.domain.service import WhatsAppService

User = get_user_model()


def _message(text="hola", phone="573001112233", message_id="svc-1"):
    return WhatsAppInboundMessage(
        channel="rest", external_message_id=message_id,
        external_conversation_id=phone, sender_phone=phone,
        message_type=MessageType.TEXT, text=text,
    )


class WhatsAppCustomerResolverTests(TestCase):
    def test_resuelve_por_ultimos_10_digitos_del_telefono(self):
        user = User.objects.create_user(email="resolver-1@example.com", password="x")
        UserProfile.objects.create(user=user, phone_number="3001112233")
        resolved = WhatsAppCustomerResolver.resolve_user("573001112233")
        self.assertEqual(resolved, user)

    def test_numero_sin_usuario_devuelve_none(self):
        self.assertIsNone(WhatsAppCustomerResolver.resolve_user("573000000099"))

    def test_usuario_inactivo_no_se_resuelve(self):
        user = User.objects.create_user(email="resolver-2@example.com", password="x", is_active=False)
        UserProfile.objects.create(user=user, phone_number="3004445566")
        self.assertIsNone(WhatsAppCustomerResolver.resolve_user("573004445566"))


class WhatsAppConversationResolverTests(TestCase):
    def test_reusa_la_misma_sala_abierta(self):
        user = User.objects.create_user(email="conv-1@example.com", password="x")
        room1 = WhatsAppConversationResolver.resolve_room(user)
        room2 = WhatsAppConversationResolver.resolve_room(user)
        self.assertEqual(room1.pk, room2.pk)


class WhatsAppIdempotencyGuardTests(TestCase):
    """IDs unicos por test (uuid4) a proposito -- el guard usa Django cache
    (Redis real en dev), que NO se revierte entre tests como la BD (la
    transaccion de TestCase no alcanza al backend de cache). Una clave fija
    tipo "idem-1" colisiona entre corridas reales de la suite -- hallazgo
    real encontrado corriendo esto (no un detalle teorico)."""

    def test_primera_vez_no_es_duplicado_segunda_si(self):
        message_id = f"idem-{uuid.uuid4()}"
        self.assertFalse(WhatsAppIdempotencyGuard.is_duplicate("rest", message_id))
        self.assertTrue(WhatsAppIdempotencyGuard.is_duplicate("rest", message_id))

    def test_mismo_message_id_en_canales_distintos_no_colisiona(self):
        """Regla FASE 14 de la mision: el mecanismo es (channel,
        external_message_id) -- un futuro gateway QR que reuse IDs no
        debe pisar la deduplicacion de REST."""
        shared_id = f"shared-{uuid.uuid4()}"
        self.assertFalse(WhatsAppIdempotencyGuard.is_duplicate("rest", shared_id))
        self.assertFalse(WhatsAppIdempotencyGuard.is_duplicate("qr", shared_id))

    def test_sin_external_message_id_nunca_es_duplicado(self):
        self.assertFalse(WhatsAppIdempotencyGuard.is_duplicate("rest", ""))
        self.assertFalse(WhatsAppIdempotencyGuard.is_duplicate("rest", ""))


class WhatsAppServiceInboundTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="service-1@example.com", password="x")
        UserProfile.objects.create(user=self.user, phone_number="3001112233")
        self.adapter = RestConnectionAdapter()
        self.service = WhatsAppService(self.adapter)

    def test_numero_desconocido_no_llama_a_la_ia_ni_crea_sala(self):
        message = _message(phone="573009998888", message_id="svc-unknown")
        with patch("support.services.ai_bridge.ask_ai") as mock_ask:
            result = self.service.process_inbound_message(message)
        self.assertEqual(result["status"], "no_user")
        mock_ask.assert_not_called()
        self.assertFalse(ChatRoom.objects.filter(user__email="service-1@example.com").exists())

    def test_ai_paused_no_llama_a_la_ia_pero_persiste_el_mensaje_del_cliente(self):
        room = WhatsAppConversationResolver.resolve_room(self.user)
        room.ai_paused = True
        room.save(update_fields=["ai_paused"])

        message = _message(message_id="svc-paused")
        with patch("support.services.ai_bridge.ask_ai") as mock_ask:
            result = self.service.process_inbound_message(message)

        self.assertEqual(result["status"], "handoff_active")
        mock_ask.assert_not_called()
        from support.models import ChatMessage
        self.assertTrue(ChatMessage.objects.filter(room=room, message="hola").exists())

    def test_respuesta_vacia_de_la_ia_no_intenta_enviar(self):
        message = _message(message_id="svc-empty")
        with patch("support.services.ai_bridge.ask_ai", return_value={"response": "", "metrics": {}}), \
             patch.object(self.adapter, "send_message") as mock_send:
            result = self.service.process_inbound_message(message)
        self.assertEqual(result["status"], "ai_empty_response")
        mock_send.assert_not_called()

    def test_flujo_completo_real_envia_por_el_adapter_inyectado(self):
        message = _message(message_id="svc-full")
        with patch("support.services.ai_bridge.ask_ai", return_value={"response": "aqui tienes la info", "metrics": {"agent": "SupportAgent"}}), \
             patch.object(self.adapter, "send_message", return_value="wamid.real123") as mock_send:
            result = self.service.process_inbound_message(message)
        self.assertEqual(result["status"], "sent")
        self.assertEqual(result["external_message_id"], "wamid.real123")
        mock_send.assert_called_once()
        sent_outbound = mock_send.call_args[0][0]
        self.assertEqual(sent_outbound.text, "aqui tienes la info")
        self.assertEqual(sent_outbound.recipient, "573001112233")

    def test_persist_inbound_false_no_duplica_el_mensaje_del_cliente(self):
        """Equivalente real al guard `self.request.retries == 0` que
        notifications/tasks.py aplicaba -- en un reintento, el mensaje del
        cliente ya se guardo en el primer intento, no debe duplicarse."""
        room = WhatsAppConversationResolver.resolve_room(self.user)
        from support.services.commands import ChatCommands
        ChatCommands.save_message(room, self.user, "hola")

        message = _message(message_id="svc-retry")
        with patch("support.services.ai_bridge.ask_ai", return_value={"response": "respuesta", "metrics": {}}), \
             patch.object(self.adapter, "send_message", return_value="wamid.retry"):
            self.service.process_inbound_message(message, persist_inbound=False)

        from support.models import ChatMessage
        self.assertEqual(ChatMessage.objects.filter(room=room, message="hola", sender=self.user).count(), 1)


class WhatsAppServiceAgentReplyTests(TestCase):
    def test_sin_telefono_no_intenta_enviar(self):
        user = User.objects.create_user(email="agent-reply-1@example.com", password="x")
        adapter = RestConnectionAdapter()
        service = WhatsAppService(adapter)
        with patch.object(adapter, "send_message") as mock_send:
            result = service.send_agent_reply(user=user, text="respuesta del agente")
        self.assertEqual(result["status"], "no_phone")
        mock_send.assert_not_called()

    def test_con_telefono_envia_con_prefijo_de_pais_real(self):
        user = User.objects.create_user(email="agent-reply-2@example.com", password="x")
        UserProfile.objects.create(user=user, phone_number="3007778899")
        adapter = RestConnectionAdapter()
        service = WhatsAppService(adapter)
        with patch.object(adapter, "send_message", return_value="wamid.agent") as mock_send:
            result = service.send_agent_reply(user=user, text="respuesta del agente")
        self.assertEqual(result["status"], "sent")
        sent_outbound = mock_send.call_args[0][0]
        self.assertEqual(sent_outbound.recipient, "573007778899")
