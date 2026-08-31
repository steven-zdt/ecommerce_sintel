from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import MetaConfigError
from marketing.integrations.meta.whatsapp import MetaWhatsAppClient

_SETTINGS = {
    "meta_access_token": "tok-123",
    "meta_graph_api_version": "v20.0",
    "whatsapp_phone_number_id": "PN1",
}


def _ok(body):
    r = MagicMock()
    r.status_code = 200
    r.content = b"{}"
    r.json.return_value = body
    return r


class MetaWhatsAppClientTests(SimpleTestCase):

    def _client(self, settings_override=None):
        graph = MetaGraphClient(integration_settings=settings_override or _SETTINGS)
        return MetaWhatsAppClient(graph=graph)

    @patch("marketing.integrations.meta.client.requests.request")
    def test_send_text_builds_payload_and_returns_message_id(self, mock_req):
        mock_req.return_value = _ok({"messages": [{"id": "wamid.ABC"}]})
        msg_id = self._client().send_text("573001234567", "hola")
        self.assertEqual(msg_id, "wamid.ABC")
        method, url = mock_req.call_args[0]
        self.assertEqual(method, "POST")
        self.assertEqual(url, "https://graph.facebook.com/v20.0/PN1/messages")
        payload = mock_req.call_args[1]["json"]
        self.assertEqual(payload["messaging_product"], "whatsapp")
        self.assertEqual(payload["type"], "text")
        self.assertEqual(payload["text"]["body"], "hola")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_send_text_truncates_to_4000_chars(self, mock_req):
        mock_req.return_value = _ok({"messages": [{"id": "x"}]})
        self._client().send_text("57300", "a" * 5000)
        self.assertEqual(len(mock_req.call_args[1]["json"]["text"]["body"]), 4000)

    @patch("marketing.integrations.meta.client.requests.request")
    def test_send_template_maps_variables_in_order(self, mock_req):
        mock_req.return_value = _ok({"messages": [{"id": "wamid.T"}]})
        msg_id = self._client().send_template(
            "57300", "order_update", {"1": "Pedro", "2": "12345"}
        )
        self.assertEqual(msg_id, "wamid.T")
        tmpl = mock_req.call_args[1]["json"]["template"]
        self.assertEqual(tmpl["name"], "order_update")
        self.assertEqual(tmpl["language"]["code"], "es_CO")
        texts = [p["text"] for p in tmpl["components"][0]["parameters"]]
        self.assertEqual(texts, ["Pedro", "12345"])

    @patch("marketing.integrations.meta.client.requests.request")
    def test_missing_phone_number_id_raises_config_error(self, mock_req):
        client = self._client({"meta_access_token": "tok", "whatsapp_phone_number_id": ""})
        with self.assertRaises(MetaConfigError):
            client.send_text("57300", "hola")
        mock_req.assert_not_called()
