"""
whatsapp/tests/test_gateway_client.py

Fase 24 del plan de migracion Baileys. Cobertura de
whatsapp/clients/gateway_client.py::WhatsAppGatewayClient -- incluye un test
de regresion explicito para el bug real encontrado probando contra el
gateway vivo en la Fase 7-8 (ver AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md):
Content-Type: application/json enviado en POSTs sin body, que Fastify
rechazaba con 400 FST_ERR_CTP_EMPTY_JSON_BODY.
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from whatsapp.clients.gateway_client import WhatsAppGatewayClient, WhatsAppGatewayError


@override_settings(WHATSAPP_GATEWAY_URL="http://gateway.test:3001", WHATSAPP_GATEWAY_TOKEN="secret-token")
class WhatsAppGatewayClientTestCase(SimpleTestCase):
    def setUp(self):
        self.client = WhatsAppGatewayClient()

    @patch("whatsapp.clients.gateway_client.requests.request")
    def test_get_con_body_nunca_manda_content_type_json_en_post_sin_body(self, mock_request):
        """Test de regresion real -- ver docstring del modulo. session_start()
        no manda body; el Content-Type NO debe estar presente (Fastify lo
        rechaza si esta y el body esta vacio)."""
        mock_request.return_value = MagicMock(ok=True, json=lambda: {"status": "STARTING"})
        self.client.session_start()
        _, kwargs = mock_request.call_args
        self.assertNotIn("Content-Type", kwargs["headers"])
        self.assertIsNone(kwargs["json"])

    @patch("whatsapp.clients.gateway_client.requests.request")
    def test_send_message_con_body_si_manda_content_type_json(self, mock_request):
        mock_request.return_value = MagicMock(ok=True, json=lambda: {"accepted": True, "status": "SENT", "provider_message_id": "x"})
        self.client.send_message(recipient="573000000000", text="hola")
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")
        self.assertEqual(kwargs["json"], {"recipient": "573000000000", "text": "hola"})

    @patch("whatsapp.clients.gateway_client.requests.request")
    def test_token_siempre_presente_en_headers(self, mock_request):
        mock_request.return_value = MagicMock(ok=True, json=lambda: {"status": "ok"})
        self.client.status()
        _, kwargs = mock_request.call_args
        self.assertEqual(kwargs["headers"]["X-Gateway-Token"], "secret-token")

    @patch("whatsapp.clients.gateway_client.requests.request")
    def test_http_no_2xx_lanza_WhatsAppGatewayError(self, mock_request):
        mock_request.return_value = MagicMock(ok=False, status_code=500, text="boom")
        with self.assertRaises(WhatsAppGatewayError):
            self.client.status()

    @patch("whatsapp.clients.gateway_client.requests.request")
    def test_excepcion_de_red_se_traduce_a_WhatsAppGatewayError(self, mock_request):
        import requests as requests_module
        mock_request.side_effect = requests_module.ConnectionError("boom")
        with self.assertRaises(WhatsAppGatewayError):
            self.client.status()

    @patch("whatsapp.clients.gateway_client.requests.request")
    def test_health_nunca_lanza_devuelve_false_en_fallo(self, mock_request):
        import requests as requests_module
        mock_request.side_effect = requests_module.Timeout("timeout")
        self.assertFalse(self.client.health())
