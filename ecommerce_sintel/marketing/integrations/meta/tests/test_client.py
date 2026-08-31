from unittest.mock import MagicMock, patch

import requests
from django.test import SimpleTestCase

from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import (
    MetaApiError,
    MetaApiTransientError,
    MetaAuthError,
    MetaConfigError,
    MetaRateLimitError,
)

_SETTINGS = {
    "meta_access_token": "tok-123",
    "meta_graph_api_version": "v20.0",
    "whatsapp_phone_number_id": "PN1",
}


def _resp(status_code, *, json_body=None, text="", content=b"x"):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    r.content = content
    if json_body is None:
        r.json.side_effect = ValueError("not json")
    else:
        r.json.return_value = json_body
    return r


class MetaGraphClientRequestTests(SimpleTestCase):

    def setUp(self):
        self.client = MetaGraphClient(integration_settings=_SETTINGS)

    @patch("marketing.integrations.meta.client.requests.request")
    def test_success_returns_parsed_json(self, mock_req):
        mock_req.return_value = _resp(200, json_body={"data": [1, 2]})
        self.assertEqual(self.client.get("/me/accounts"), {"data": [1, 2]})
        method, url = mock_req.call_args[0]
        self.assertEqual(method, "GET")
        self.assertEqual(url, "https://graph.facebook.com/v20.0/me/accounts")
        self.assertEqual(
            mock_req.call_args[1]["headers"]["Authorization"], "Bearer tok-123"
        )

    @patch("marketing.integrations.meta.client.requests.request")
    def test_empty_2xx_body_returns_empty_dict(self, mock_req):
        mock_req.return_value = _resp(204, content=b"")
        self.assertEqual(self.client.delete("/123"), {})

    @patch("marketing.integrations.meta.client.requests.request")
    def test_non_json_2xx_raises_api_error(self, mock_req):
        mock_req.return_value = _resp(200, json_body=None, content=b"<html>")
        with self.assertRaises(MetaApiError):
            self.client.get("/x")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_business_4xx_raises_plain_api_error(self, mock_req):
        mock_req.return_value = _resp(400, json_body={"error": {"message": "bad", "code": 100}})
        with self.assertRaises(MetaApiError) as ctx:
            self.client.get("/x")
        self.assertNotIsInstance(ctx.exception, MetaAuthError)
        self.assertNotIsInstance(ctx.exception, MetaRateLimitError)

    @patch("marketing.integrations.meta.client.requests.request")
    def test_401_raises_auth_error(self, mock_req):
        mock_req.return_value = _resp(401, json_body={"error": {"message": "tok", "code": 190}})
        with self.assertRaises(MetaAuthError):
            self.client.get("/x")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_403_raises_auth_error(self, mock_req):
        mock_req.return_value = _resp(403, json_body={"error": {}})
        with self.assertRaises(MetaAuthError):
            self.client.get("/x")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_http_429_raises_rate_limit_error(self, mock_req):
        mock_req.return_value = _resp(429, json_body={"error": {"message": "slow down"}})
        with self.assertRaises(MetaRateLimitError):
            self.client.get("/x")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_graph_rate_limit_code_raises_rate_limit_error(self, mock_req):
        mock_req.return_value = _resp(400, json_body={"error": {"code": 4, "message": "limit"}})
        with self.assertRaises(MetaRateLimitError):
            self.client.get("/x")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_5xx_raises_transient_error(self, mock_req):
        mock_req.return_value = _resp(500, json_body={"error": {}})
        with self.assertRaises(MetaApiTransientError):
            self.client.get("/x")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_network_error_raises_transient_error(self, mock_req):
        mock_req.side_effect = requests.ConnectionError("boom")
        with self.assertRaises(MetaApiTransientError):
            self.client.get("/x")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_missing_token_raises_config_error_without_hitting_network(self, mock_req):
        client = MetaGraphClient(integration_settings={"meta_access_token": ""})
        with self.assertRaises(MetaConfigError):
            client.get("/x")
        mock_req.assert_not_called()


class MetaGraphClientPaginateTests(SimpleTestCase):

    def setUp(self):
        self.client = MetaGraphClient(integration_settings=_SETTINGS)

    @patch("marketing.integrations.meta.client.requests.request")
    def test_paginate_follows_after_cursor_then_stops(self, mock_req):
        mock_req.side_effect = [
            _resp(200, json_body={
                "data": [{"id": "a"}, {"id": "b"}],
                "paging": {"cursors": {"after": "CUR1"}, "next": "https://x/next"},
            }),
            _resp(200, json_body={"data": [{"id": "c"}], "paging": {"cursors": {}}}),
        ]
        items = list(self.client.paginate("/act_1/campaigns"))
        self.assertEqual([i["id"] for i in items], ["a", "b", "c"])
        self.assertEqual(mock_req.call_count, 2)
        self.assertEqual(mock_req.call_args_list[1][1]["params"]["after"], "CUR1")

    @patch("marketing.integrations.meta.client.requests.request")
    def test_paginate_respects_max_pages(self, mock_req):
        mock_req.return_value = _resp(200, json_body={
            "data": [{"id": "x"}],
            "paging": {"cursors": {"after": "SAME"}, "next": "https://x/next"},
        })
        items = list(self.client.paginate("/edge", max_pages=3))
        self.assertEqual(len(items), 3)
        self.assertEqual(mock_req.call_count, 3)
