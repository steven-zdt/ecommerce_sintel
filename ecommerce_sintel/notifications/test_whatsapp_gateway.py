"""
notifications/test_whatsapp_gateway.py

Fase 24 de PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md -- cobertura real
de lo que se construyo en las Fases 6-8 y solo se habia verificado manualmente
(curl + docker exec + Celery real, ver AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md).
Archivo separado de `notifications/tests.py` (912 lineas) por tamano, mismo
patron real (`TransactionTestCase`, `APIClient`, `@patch`) que ya usa ese
archivo para el webhook de Meta -- ver `WhatsAppInboundWebhookDedupeTestCase`/
`WhatsAppInboundHandoffGateTestCase` ahi, que esta suite espeja para el canal
Baileys.
"""
import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from notifications.tasks import process_whatsapp_gateway_inbound_task

User = get_user_model()

_TOKEN = "test-gateway-token"


def _message_event(provider_message_id: str, *, sender_phone: str = "573001234567", text: str = "hola") -> dict:
    return {
        "event": "whatsapp.message.received",
        "event_id": str(uuid.uuid4()),
        "occurred_at": "2026-09-22T20:00:00Z",
        "provider": "baileys",
        "message": {
            "provider_message_id": provider_message_id,
            "remote_jid": f"{sender_phone}@s.whatsapp.net",
            "sender_phone": sender_phone,
            "text": text,
            "timestamp": "2026-09-22T20:00:00Z",
        },
    }


@override_settings(WHATSAPP_GATEWAY_TOKEN=_TOKEN)
class WhatsAppGatewayEventViewAuthTestCase(TransactionTestCase):
    """Fail-closed real (Fase 6/7): sin token o con token invalido, 401 --
    nunca se llega a procesar nada."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("whatsapp-gateway-events")

    def _post(self, payload: dict, *, token: str | None = _TOKEN):
        headers = {}
        if token is not None:
            headers["HTTP_X_GATEWAY_TOKEN"] = token
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json", **headers)

    def test_sin_token_401(self):
        response = self._post(_message_event("msg-1"), token=None)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_invalido_401(self):
        response = self._post(_message_event("msg-1"), token="wrong")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_evento_desconocido_400(self):
        response = self._post({"event": "whatsapp.bogus", "event_id": "x"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(WHATSAPP_GATEWAY_TOKEN="")
    def test_sin_WHATSAPP_GATEWAY_TOKEN_configurado_rechaza_incluso_con_token_vacio(self):
        # Fail-closed real: token vacio en settings == nunca aceptar nada,
        # ni siquiera un header vacio que "coincida" por accidente.
        response = self.client.post(
            self.url, data=json.dumps(_message_event("msg-1")), content_type="application/json",
            HTTP_X_GATEWAY_TOKEN="",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


@override_settings(WHATSAPP_GATEWAY_TOKEN=_TOKEN, WHATSAPP_CONNECTION_TYPE="QR_WEB_SESSION")
class WhatsAppGatewayEventViewDedupeTestCase(TransactionTestCase):
    """Mismo mecanismo real que WhatsAppInboundWebhookDedupeTestCase (Meta),
    canal 'baileys' -- ver whatsapp/domain/idempotency.py."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("whatsapp-gateway-events")

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json", HTTP_X_GATEWAY_TOKEN=_TOKEN,
        )

    @patch("notifications.tasks.process_whatsapp_gateway_inbound_task.delay")
    def test_mismo_provider_message_id_se_procesa_una_sola_vez(self, mock_delay):
        event = _message_event(f"dup-{uuid.uuid4()}")
        r1 = self._post(event)
        r2 = self._post(event)
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.json()["status"], "duplicate")
        self.assertEqual(mock_delay.call_count, 1)

    @patch("notifications.tasks.process_whatsapp_gateway_inbound_task.delay")
    def test_provider_message_ids_distintos_se_procesan_ambos(self, mock_delay):
        self._post(_message_event(f"a-{uuid.uuid4()}"))
        self._post(_message_event(f"b-{uuid.uuid4()}"))
        self.assertEqual(mock_delay.call_count, 2)


class WhatsAppGatewayEventViewConnectionTypeGuardTestCase(TransactionTestCase):
    """Fase 8: NUNCA encolar el procesamiento si el mecanismo activo no es
    QR_WEB_SESSION -- responder por el adapter equivocado (Meta) a un
    mensaje que llego por Baileys seria un bug real de negocio, no cosmetico."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse("whatsapp-gateway-events")

    def _post(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json", HTTP_X_GATEWAY_TOKEN=_TOKEN,
        )

    @override_settings(WHATSAPP_GATEWAY_TOKEN=_TOKEN, WHATSAPP_CONNECTION_TYPE="META_CLOUD_API")
    @patch("notifications.tasks.process_whatsapp_gateway_inbound_task.delay")
    def test_connection_type_meta_no_encola_nada(self, mock_delay):
        response = self._post(_message_event(f"guard-{uuid.uuid4()}"))
        self.assertEqual(response.json(), {"status": "received_not_processed", "reason": "connection_type_mismatch"})
        mock_delay.assert_not_called()

    @override_settings(WHATSAPP_GATEWAY_TOKEN=_TOKEN, WHATSAPP_CONNECTION_TYPE="QR_WEB_SESSION")
    @patch("notifications.tasks.process_whatsapp_gateway_inbound_task.delay")
    def test_connection_type_qr_web_session_si_encola(self, mock_delay):
        response = self._post(_message_event(f"guard-{uuid.uuid4()}"))
        self.assertEqual(response.json()["status"], "received_processing")
        mock_delay.assert_called_once()


class ProcessWhatsAppGatewayInboundTaskTestCase(TransactionTestCase):
    """Fase 24: mismo gate de IA (ai_paused/human handoff) que ya prueba
    WhatsAppInboundHandoffGateTestCase para el canal Meta -- aqui para el
    canal Baileys, mismo WhatsAppService compartido por ambos (Fase 9/19)."""

    def setUp(self):
        from accounts.models import UserProfile
        from support.services.commands import ChatCommands

        self.user = User.objects.create_user(email="wa.gateway.handoff@test.sintel", password="x")
        UserProfile.objects.create(user=self.user, phone_number="3001112233")
        self.room = ChatCommands.get_or_create_room(self.user)

    @patch("support.services.ai_bridge.ask_ai")
    def test_ai_paused_bloquea_auto_respuesta_pero_persiste_mensaje(self, mock_ask_ai):
        from support.models import ChatMessage, ChatRoom

        self.room.ai_paused = True
        self.room.save(update_fields=["ai_paused"])

        process_whatsapp_gateway_inbound_task(
            remote_jid="573001112233@s.whatsapp.net",
            sender_phone="573001112233",
            text="sigo esperando ayuda",
            provider_message_id=f"task-{uuid.uuid4()}",
        )

        mock_ask_ai.assert_not_called()
        room = ChatRoom.objects.get(user=self.user)
        messages = list(ChatMessage.objects.filter(room=room))
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].message, "sigo esperando ayuda")

    @override_settings(WHATSAPP_CONNECTION_TYPE="QR_WEB_SESSION")
    @patch("support.services.ai_bridge.ask_ai")
    def test_sala_normal_llama_a_ask_ai_y_el_envio_falla_limpio_sin_gateway(self, mock_ask_ai):
        """Control positivo (Fase 8): sin ai_paused, la IA SI se consulta.
        El intento de respuesta por WhatsApp falla limpio (QRWebSessionAdapter
        stub, sin gateway configurado en el entorno de tests -- mismo
        principio que whatsapp/tests/test_failure_isolation.py::
        QRGatewayUnavailableTests) -- el mensaje del cliente ya quedo
        persistido de todas formas, no se pierde."""
        from support.models import ChatMessage, ChatRoom

        mock_ask_ai.return_value = {"response": "Con gusto, dame un momento.", "metrics": {}}

        result = process_whatsapp_gateway_inbound_task(
            remote_jid="573001112233@s.whatsapp.net",
            sender_phone="573001112233",
            text="hola, necesito ayuda",
            provider_message_id=f"task-{uuid.uuid4()}",
        )

        mock_ask_ai.assert_called_once()
        room = ChatRoom.objects.get(user=self.user)
        self.assertTrue(ChatMessage.objects.filter(room=room, message__icontains="necesito ayuda").exists())
        self.assertIsNone(result)  # la tarea solo loguea, no propaga el dict de WhatsAppService (ver notifications/tasks.py)

    @patch("support.services.ai_bridge.ask_ai")
    def test_numero_sin_usuario_no_crea_sala_ni_llama_a_la_ia(self, mock_ask_ai):
        process_whatsapp_gateway_inbound_task(
            remote_jid="573009998877@s.whatsapp.net",
            sender_phone="573009998877",
            text="mensaje de un numero desconocido",
            provider_message_id=f"task-{uuid.uuid4()}",
        )
        mock_ask_ai.assert_not_called()
