from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from marketing.channels.base import CampaignMessage
from marketing.channels.facebook_channel import FacebookChannelAdapter
from marketing.channels.instagram_channel import InstagramChannelAdapter
from marketing.channels.whatsapp_channel import WhatsAppChannelAdapter

_META = dict(
    META_ACCESS_TOKEN="tok",
    META_GRAPH_API_VERSION="v20.0",
    WHATSAPP_PHONE_NUMBER_ID="PN1",
    FACEBOOK_PAGE_ID="PAGE1",
    INSTAGRAM_BUSINESS_ACCOUNT_ID="IG1",
)


def _ok(body):
    r = MagicMock()
    r.status_code = 200
    r.content = b"{}"
    r.json.return_value = body
    return r


@override_settings(**_META)
class ChannelAdaptersUseMetaGraphClientTests(SimpleTestCase):

    def _msg(self, **kw):
        base = dict(recipient="573001234567", subject="Promo", body="Contenido", media_url=None)
        base.update(kw)
        return CampaignMessage(**base)

    @patch("marketing.integrations.meta.client.requests.request")
    def test_whatsapp_channel_sends_marketing_template(self, mock_req):
        mock_req.return_value = _ok({"messages": [{"id": "wamid.C"}]})
        out = WhatsAppChannelAdapter().send(self._msg())
        self.assertTrue(out["success"])
        self.assertEqual(out["response"]["message_id"], "wamid.C")
        payload = mock_req.call_args[1]["json"]
        self.assertEqual(payload["template"]["name"], "marketing_campaign")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_facebook_channel_posts_to_page_feed(self, mock_req):
        mock_req.return_value = _ok({"id": "PAGE1_123"})
        out = FacebookChannelAdapter().send(self._msg(media_url="https://x/img.png"))
        self.assertTrue(out["success"])
        _method, url = mock_req.call_args[0]
        self.assertEqual(url, "https://graph.facebook.com/v20.0/PAGE1/feed")
        self.assertEqual(mock_req.call_args[1]["data"]["link"], "https://x/img.png")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_instagram_channel_two_step_publish(self, mock_req):
        mock_req.side_effect = [_ok({"id": "CONTAINER1"}), _ok({"id": "MEDIA1"})]
        out = InstagramChannelAdapter().send(self._msg(media_url="https://x/img.png"))
        self.assertTrue(out["success"])
        self.assertEqual(mock_req.call_count, 2)
        self.assertEqual(mock_req.call_args_list[1][1]["data"]["creation_id"], "CONTAINER1")

    def test_instagram_without_media_url_fails_gracefully(self):
        out = InstagramChannelAdapter().send(self._msg())
        self.assertFalse(out["success"])

    @override_settings(FACEBOOK_PAGE_ID="")
    def test_facebook_channel_reports_missing_config(self):
        out = FacebookChannelAdapter().send(self._msg())
        self.assertFalse(out["success"])
        self.assertIn("FACEBOOK_PAGE_ID", out["response"])

    @patch("marketing.integrations.meta.client.requests.request")
    def test_whatsapp_channel_wraps_api_error(self, mock_req):
        err = MagicMock()
        err.status_code = 400
        err.text = "{}"
        err.json.return_value = {"error": {"message": "template no aprobada", "code": 132}}
        mock_req.return_value = err
        out = WhatsAppChannelAdapter().send(self._msg())
        self.assertFalse(out["success"])
        self.assertIn("template no aprobada", out["response"])
