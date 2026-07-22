import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class WhatsAppApiError(Exception):
    pass


class WhatsAppAuthError(WhatsAppApiError):
    """Token invalido o expirado (401/403). No tiene sentido reintentar."""
    pass


class WhatsAppConfigError(WhatsAppApiError):
    """Falta configuracion de META_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID."""
    pass


class WhatsAppClient:
    """
    Adaptador para Meta Cloud API (WhatsApp Business Platform).

    Variables de entorno requeridas (ya en settings/base.py bajo Marketing Channels):
      META_ACCESS_TOKEN       — token de sistema permanente de Meta Business
      WHATSAPP_PHONE_NUMBER_ID — ID del número registrado en Meta Business Manager
    """
    BASE_URL = 'https://graph.facebook.com/v20.0'

    def __init__(self):
        self.token    = getattr(settings, 'META_ACCESS_TOKEN', '')
        self.phone_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
        self._session = requests.Session()
        self._session.headers.update({
            'Authorization': f'Bearer {self.token}',
            'Content-Type':  'application/json',
        })

    def send_template(self, to: str, template_name: str, variables: dict) -> str:
        """
        Envía un mensaje usando una plantilla aprobada por Meta.
        Los valores del dict `variables` se mapean en orden como
        {{1}}, {{2}}, ... en el cuerpo de la plantilla.
        Retorna el message_id asignado por WhatsApp.
        Lanza WhatsAppApiError si la API responde con un error HTTP.
        """
        if not self.token or not self.phone_id:
            raise WhatsAppConfigError(
                'META_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID no configurados.'
            )

        components = []
        if variables:
            params = [
                {'type': 'text', 'text': str(v)}
                for v in variables.values()
            ]
            components.append({'type': 'body', 'parameters': params})

        payload = {
            'messaging_product': 'whatsapp',
            'to':   to,
            'type': 'template',
            'template': {
                'name':       template_name,
                'language':   {'code': 'es_CO'},
                'components': components,
            },
        }

        url  = f'{self.BASE_URL}/{self.phone_id}/messages'
        resp = self._session.post(url, json=payload, timeout=15)

        if not resp.ok:
            logger.error(
                'WhatsApp API error | to=%s template=%s status=%s body=%s',
                to, template_name, resp.status_code, resp.text[:500],
            )
            if resp.status_code in (401, 403):
                raise WhatsAppAuthError(
                    f'Meta API respondio {resp.status_code}: {resp.text[:200]}'
                )
            raise WhatsAppApiError(
                f'Meta API respondio {resp.status_code}: {resp.text[:200]}'
            )

        data       = resp.json()
        message_id = data.get('messages', [{}])[0].get('id', '')
        logger.info(
            'WhatsApp enviado | to=%s template=%s msg_id=%s',
            to, template_name, message_id,
        )
        return message_id

    def send_text(self, to: str, body: str) -> str:
        """
        Envia un mensaje de texto libre (Fase 7 AI Core -- respuestas
        conversacionales del Action Graph). Meta solo lo permite dentro de la
        ventana de servicio de 24h abierta por un mensaje entrante del
        cliente, exactamente el caso del webhook.
        """
        if not self.token or not self.phone_id:
            raise WhatsAppConfigError(
                'META_ACCESS_TOKEN o WHATSAPP_PHONE_NUMBER_ID no configurados.'
            )
        payload = {
            'messaging_product': 'whatsapp',
            'to':   to,
            'type': 'text',
            'text': {'body': body[:4000]},
        }
        url  = f'{self.BASE_URL}/{self.phone_id}/messages'
        resp = self._session.post(url, json=payload, timeout=15)
        if not resp.ok:
            logger.error('WhatsApp API error | to=%s text status=%s body=%s',
                         to, resp.status_code, resp.text[:500])
            if resp.status_code in (401, 403):
                raise WhatsAppAuthError(f'Meta API respondio {resp.status_code}: {resp.text[:200]}')
            raise WhatsAppApiError(f'Meta API respondio {resp.status_code}: {resp.text[:200]}')
        message_id = resp.json().get('messages', [{}])[0].get('id', '')
        logger.info('WhatsApp texto enviado | to=%s msg_id=%s', to, message_id)
        return message_id
