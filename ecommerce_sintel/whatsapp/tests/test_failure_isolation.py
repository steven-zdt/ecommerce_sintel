"""
whatsapp/tests/test_failure_isolation.py

Mision "Refactorizacion Arquitectonica del Modulo WhatsApp", FASE 23
(2026-09-16). Prueba que una caida del mecanismo de transporte (REST
-- Meta Cloud API caida/credenciales invalidas; QR -- gateway no
implementado) NUNCA rompe la capa de negocio de WhatsApp, ni Support, ni
la resolucion de cliente/ChatRoom. El fallo debe quedar contenido en el
adapter -- el dominio lo recibe como un resultado observable
("send_failed"), nunca como una excepcion no controlada que tumbe todo
el procesamiento del mensaje entrante.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.models import UserProfile
from support.models import ChatMessage, ChatRoom
from whatsapp.adapters.qr_adapter import QRConnectionAdapter
from whatsapp.adapters.rest_adapter import RestConnectionAdapter
from whatsapp.domain.contracts import MessageType, WhatsAppInboundMessage
from whatsapp.domain.service import WhatsAppService

User = get_user_model()


class RestGatewayDownTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="wa-failure-rest@example.com", password="x")
        UserProfile.objects.create(user=self.user, phone_number="3009876543")

    def test_rest_down_el_mensaje_del_cliente_se_persiste_igual_solo_falla_el_envio(self):
        """Caso real: Meta Cloud API caida/token invalido durante el
        envio de la RESPUESTA -- el mensaje del cliente y la respuesta de
        la IA ya deben estar guardados en el ChatRoom (visibles para un
        agente humano en /panel/soporte) ANTES de que se intente el envio
        por WhatsApp. Un fallo de transporte no debe perder eso."""
        adapter = RestConnectionAdapter()
        service = WhatsAppService(adapter)

        message = WhatsAppInboundMessage(
            channel="rest", external_message_id="fail-1",
            external_conversation_id="573009876543", sender_phone="573009876543",
            message_type=MessageType.TEXT, text="necesito ayuda con mi pedido",
        )

        with patch("support.services.ai_bridge.ask_ai", return_value={"response": "claro, dame el numero de pedido", "metrics": {}}), \
             patch.object(adapter, "send_message", side_effect=RuntimeError("Meta Cloud API caida (simulado)")):
            result = service.process_inbound_message(message)

        self.assertEqual(result["status"], "send_failed")
        room = ChatRoom.objects.get(user=self.user)
        self.assertTrue(ChatMessage.objects.filter(room=room, message__icontains="necesito ayuda con mi pedido").exists())
        self.assertTrue(ChatMessage.objects.filter(room=room, message__icontains="dame el numero de pedido").exists())

    def test_rest_sin_credenciales_configuradas_get_status_reporta_error_no_lanza(self):
        with patch("django.conf.settings.META_ACCESS_TOKEN", ""):
            adapter = RestConnectionAdapter()
            from whatsapp.ports.connection import ConnectionStatus
            self.assertEqual(adapter.get_status(), ConnectionStatus.ERROR)
            self.assertFalse(adapter.health_check())


class QRGatewayUnavailableTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="wa-failure-qr@example.com", password="x")
        UserProfile.objects.create(user=self.user, phone_number="3005551234")

    def test_qr_sin_gateway_el_mensaje_del_cliente_se_persiste_el_envio_falla_contenido(self):
        """Mismo principio, canal QR: process_inbound_message NO debe
        reventar sin control -- WhatsAppService captura CUALQUIER
        excepcion de connection.send_message() (red caida, credenciales
        invalidas, o -- este caso -- un mecanismo sin gateway real) y la
        reporta como "send_failed", nunca deja que se propague sin control
        (mismo criterio, sin importar la CAUSA del fallo de transporte).
        El mensaje del cliente y la respuesta de la IA YA quedaron
        guardados antes de llegar a ese punto."""
        adapter = QRConnectionAdapter()
        service = WhatsAppService(adapter)

        message = WhatsAppInboundMessage(
            channel="qr", external_message_id="fail-2",
            external_conversation_id="573005551234", sender_phone="573005551234",
            message_type=MessageType.TEXT, text="hola por QR",
        )

        with patch("support.services.ai_bridge.ask_ai", return_value={"response": "hola, en que te ayudo", "metrics": {}}):
            result = service.process_inbound_message(message)

        self.assertEqual(result["status"], "send_failed")
        room = ChatRoom.objects.get(user=self.user)
        self.assertTrue(ChatMessage.objects.filter(room=room, message__icontains="hola por QR").exists())
        self.assertTrue(ChatMessage.objects.filter(room=room, message__icontains="en que te ayudo").exists())


class WebSupportUnaffectedByWhatsAppFailureTests(TestCase):
    """FASE 23 de la mision, explicito: "Web Support sigue funcionando"
    cuando WhatsApp falla. Verificado real: ChatCommands (el Service
    Layer que el widget web usa) sigue operando con normalidad sobre el
    MISMO ChatRoom que un intento fallido de WhatsApp toco."""

    def test_chatcommands_sigue_operando_sobre_una_sala_que_tuvo_un_fallo_de_whatsapp(self):
        user = User.objects.create_user(email="wa-failure-web@example.com", password="x")
        UserProfile.objects.create(user=user, phone_number="3002223344")
        adapter = RestConnectionAdapter()
        service = WhatsAppService(adapter)
        message = WhatsAppInboundMessage(
            channel="rest", external_message_id="fail-3",
            external_conversation_id="573002223344", sender_phone="573002223344",
            message_type=MessageType.TEXT, text="mensaje que fallara al responder",
        )
        with patch("support.services.ai_bridge.ask_ai", return_value={"response": "respuesta real", "metrics": {}}), \
             patch.object(adapter, "send_message", side_effect=RuntimeError("caido")):
            service.process_inbound_message(message)

        from support.services.commands import ChatCommands
        room = ChatRoom.objects.get(user=user)
        # Un agente humano (o el propio cliente por el widget web) sigue
        # pudiendo escribir en la sala con total normalidad.
        msg = ChatCommands.save_message(room, user, "mensaje nuevo por el widget web")
        self.assertIsNotNone(msg.pk)
