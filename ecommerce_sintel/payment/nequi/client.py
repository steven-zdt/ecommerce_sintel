import logging
import uuid as uuid_lib
from datetime import datetime
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_OAUTH_URL   = 'https://oauth.nequi.com/oauth2/token'
_PAYMENT_URL = 'https://api.nequi.com/payments/v2/-services-paymentservice-unregisteredpayment'
_STATUS_URL  = 'https://api.nequi.com/payments/v2/-services-paymentservice-getstatuspayment'

_SANDBOX_OAUTH   = 'https://oauth.sandbox.nequi.com/oauth2/token'
_SANDBOX_PAYMENT = 'https://sandbox-api.nequi.com/payments/v2/-services-paymentservice-unregisteredpayment'
_SANDBOX_STATUS  = 'https://sandbox-api.nequi.com/payments/v2/-services-paymentservice-getstatuspayment'


class NequiApiError(Exception):
    pass


class NequiApiClient:
    def __init__(self):
        self._is_sandbox = getattr(settings, 'NEQUI_ENVIRONMENT', 'sandbox') != 'production'
        self._client_id  = settings.NEQUI_CLIENT_ID
        self._secret     = settings.NEQUI_CLIENT_SECRET
        self._api_key    = settings.NEQUI_API_KEY

        if self._is_sandbox:
            self._oauth_url   = _SANDBOX_OAUTH
            self._payment_url = _SANDBOX_PAYMENT
            self._status_url  = _SANDBOX_STATUS
        else:
            self._oauth_url   = _OAUTH_URL
            self._payment_url = _PAYMENT_URL
            self._status_url  = _STATUS_URL

    def get_access_token(self) -> str:
        resp = requests.post(
            self._oauth_url,
            data={
                'grant_type':    'client_credentials',
                'client_id':     self._client_id,
                'client_secret': self._secret,
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.error("Nequi OAuth error | status=%s body=%s", resp.status_code, resp.text)
            raise NequiApiError(f"No se pudo obtener token Nequi: {resp.status_code}")
        return resp.json()['access_token']

    def request_push_payment(self, phone: str, amount: Decimal, reference: str) -> str:
        """
        Envia solicitud de pago push al usuario en Nequi.
        Retorna el messageId para consultas de estado posteriores.
        """
        token      = self.get_access_token()
        message_id = str(uuid_lib.uuid4()).replace('-', '')[:20]
        amount_int = int(amount)

        payload = {
            "RequestMessage": {
                "RequestHeader": {
                    "Channel":     "PNP03",
                    "RequestDate": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                    "MessageID":   message_id,
                    "ClientID":    self._client_id,
                    "Destination": {
                        "ServiceName":      "PaymentService",
                        "ServiceOperation": "unregisteredPayment",
                        "ServiceRegion":    "C001",
                        "ServiceVersion":   "1.2.0",
                    },
                },
                "RequestBody": {
                    "any": {
                        "unregisteredPaymentRQ": {
                            "phoneNumberTo": phone,
                            "value":         amount_int,
                        }
                    }
                },
            }
        }

        resp = requests.post(
            self._payment_url,
            json=payload,
            headers={
                'Authorization': f'Bearer {token}',
                'x-api-key':     self._api_key,
                'Content-Type':  'application/json',
            },
            timeout=20,
        )
        logger.info("Nequi push sent | reference=%s status=%s", reference, resp.status_code)

        if resp.status_code not in (200, 201):
            raise NequiApiError(f"Error al enviar push Nequi: {resp.status_code}")

        data = resp.json()
        try:
            response_code = data["ResponseMessage"]["ResponseHeader"]["ResponseCode"]
            if response_code not in ("00", "200"):
                raise NequiApiError(f"Nequi rechazo el push: code={response_code}")
        except (KeyError, TypeError):
            pass

        return message_id

    def get_payment_status(self, message_id: str) -> str:
        """
        Consulta el estado de un pago push Nequi.
        Retorna uno de: 'PENDING', 'APPROVED', 'REJECTED', 'ERROR'.
        """
        token = self.get_access_token()

        resp = requests.get(
            self._status_url,
            params={'messageId': message_id},
            headers={
                'Authorization': f'Bearer {token}',
                'x-api-key':     self._api_key,
            },
            timeout=15,
        )
        logger.info("Nequi status check | message_id=%s status=%s", message_id, resp.status_code)

        if resp.status_code != 200:
            return 'ERROR'

        data = resp.json()
        try:
            status_code = (
                data["ResponseMessage"]["ResponseBody"]["any"]
                ["getStatusPaymentRS"]["status"]["statusCode"]
            )
        except (KeyError, TypeError):
            return 'ERROR'

        mapping = {'00': 'PENDING', '20': 'APPROVED', '09': 'REJECTED', '96': 'ERROR'}
        return mapping.get(str(status_code), 'ERROR')
