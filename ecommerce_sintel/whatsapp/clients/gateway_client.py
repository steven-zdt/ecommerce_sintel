"""
whatsapp/clients/gateway_client.py

Fase 7/8 del plan de migracion Baileys (AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md).
Cliente HTTP sincrono Django -> whatsapp_gateway/ (direccion opuesta al Event
Bus de notifications/api/whatsapp_gateway_webhook.py). Envuelve el contrato
exacto de la Fase 1 del plan (whatsapp_gateway/src/server.ts): health/status/
session-start/session-logout/session-reconnect/session-qr/messages-send.

Mismo patron que MetaWhatsAppClient (marketing/integrations/meta/client.py)
-- `requests` sincrono con timeout corto, sin reintento propio (el dominio
ya maneja fallos de `send_message` con try/except generico, ver
whatsapp/domain/service.py). Solo `whatsapp/adapters/qr_web_session_adapter.py`
debe importar esto -- ningun otro modulo del dominio.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger("whatsapp.gateway_client")

_TIMEOUT_SECONDS = 5


class WhatsAppGatewayError(Exception):
    """Fallo operacional real (red, timeout, HTTP no-2xx) hablando con un
    gateway configurado -- distinto de "no hay gateway configurado"
    (ese caso sigue siendo WhatsAppQRNotImplementedError en el adapter,
    ver qr_web_session_adapter.py)."""


class WhatsAppGatewayClient:
    def __init__(self):
        self._base_url = settings.WHATSAPP_GATEWAY_URL.rstrip("/")
        self._base_headers = {"X-Gateway-Token": settings.WHATSAPP_GATEWAY_TOKEN}

    def _request(self, method: str, path: str, *, json=None) -> dict:
        url = f"{self._base_url}{path}"
        # Content-Type: application/json SOLO si hay body real -- Fastify
        # (whatsapp_gateway/) rechaza con 400 FST_ERR_CTP_EMPTY_JSON_BODY un
        # POST con ese header y body vacio (session/start|logout|reconnect
        # no llevan body). Bug real encontrado probando contra el gateway
        # vivo, no una suposicion -- ver AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md.
        headers = dict(self._base_headers)
        if json is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = requests.request(
                method, url, headers=headers, json=json, timeout=_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            raise WhatsAppGatewayError(f"{method} {path} fallo: {exc}") from exc
        if not response.ok:
            raise WhatsAppGatewayError(f"{method} {path} devolvio HTTP {response.status_code}: {response.text[:200]}")
        try:
            return response.json()
        except ValueError as exc:
            raise WhatsAppGatewayError(f"{method} {path} devolvio un body no-JSON") from exc

    def health(self) -> bool:
        try:
            data = self._request("GET", "/health")
        except WhatsAppGatewayError:
            return False
        return data.get("status") == "ok"

    def status(self) -> dict:
        return self._request("GET", "/status")

    def qr(self) -> dict:
        return self._request("GET", "/session/qr")

    def session_start(self) -> dict:
        return self._request("POST", "/session/start")

    def session_logout(self) -> dict:
        return self._request("POST", "/session/logout")

    def session_reconnect(self) -> dict:
        return self._request("POST", "/session/reconnect")

    def send_message(self, *, recipient: str, text: str) -> dict:
        return self._request("POST", "/messages/send", json={"recipient": recipient, "text": text})
