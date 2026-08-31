from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import MetaConfigError
from marketing.integrations.meta.marketing import MetaMarketingClient

_SETTINGS = {
    "meta_access_token": "tok",
    "meta_graph_api_version": "v20.0",
    "meta_ad_account_id": "123456",
}


def _ok(body):
    r = MagicMock()
    r.status_code = 200
    r.content = b"{}"
    r.json.return_value = body
    return r


class MetaMarketingClientTests(SimpleTestCase):

    def _client(self, settings_override=None):
        graph = MetaGraphClient(integration_settings=settings_override or _SETTINGS)
        return MetaMarketingClient(graph=graph)

    def test_act_prefixes_the_account_id(self):
        self.assertEqual(self._client()._act(), "act_123456")

    def test_act_does_not_double_prefix(self):
        c = self._client({"meta_access_token": "t", "meta_ad_account_id": "act_999"})
        self.assertEqual(c._act(), "act_999")

    def test_missing_ad_account_raises_config_error(self):
        c = self._client({"meta_access_token": "t", "meta_ad_account_id": ""})
        with self.assertRaises(MetaConfigError):
            c.list_campaigns()

    @patch("marketing.integrations.meta.client.requests.request")
    def test_list_campaigns_hits_account_edge_with_fields(self, mock_req):
        mock_req.return_value = _ok({"data": [{"id": "c1", "name": "BF"}], "paging": {"cursors": {}}})
        campaigns = self._client().list_campaigns(limit=10, effective_status=["ACTIVE"])
        self.assertEqual(campaigns, [{"id": "c1", "name": "BF"}])
        _method, url = mock_req.call_args[0]
        self.assertEqual(url, "https://graph.facebook.com/v20.0/act_123456/campaigns")
        params = mock_req.call_args[1]["params"]
        self.assertIn("name", params["fields"])
        self.assertEqual(params["limit"], 10)
        self.assertEqual(params["effective_status"], '["ACTIVE"]')

    @patch("marketing.integrations.meta.client.requests.request")
    def test_get_insights_uses_time_range_over_date_preset(self, mock_req):
        mock_req.return_value = _ok({"data": [], "paging": {"cursors": {}}})
        list(self._client().get_insights("c1", level="campaign",
                                         time_range={"since": "2026-08-01", "until": "2026-08-15"}))
        params = mock_req.call_args[1]["params"]
        self.assertEqual(params["time_range"], '{"since": "2026-08-01", "until": "2026-08-15"}')
        self.assertNotIn("date_preset", params)

    @patch("marketing.integrations.meta.client.requests.request")
    def test_account_summary_returns_first_row(self, mock_req):
        mock_req.return_value = _ok({"data": [{"spend": "42.5", "impressions": "1000"}]})
        summary = self._client().get_account_summary()
        self.assertEqual(summary["spend"], "42.5")
        _method, url = mock_req.call_args[0]
        self.assertEqual(url, "https://graph.facebook.com/v20.0/act_123456/insights")
