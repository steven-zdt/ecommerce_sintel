import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SmsApiError(Exception):
    pass


class SmsConfigError(SmsApiError):
    """Falta SMS_BRIDGE_URL. Error permanente, no tiene sentido reintentar."""
    pass


class SmsBridgeUnreachableError(SmsApiError):
    """El puente en el host Windows no respondio (modem apagado/desconectado/servicio caido)."""
    pass


class SmsClient:
    """
    Adaptador para el modem GSM SIM5360 (SIM Movistar Colombia) conectado por
    USB al host Windows. Django corre en un contenedor Linux (Docker Desktop
    con backend WSL2) que no puede abrir un puerto COM de Windows
    directamente -- por eso este cliente no habla serie, habla HTTP contra
    sms_bridge/bridge.py, un proceso liviano que SI corre en el host y es
    el unico dueno del puerto serie (protocolo AT completo alli).

    Variables de entorno requeridas (settings/base.py bajo Marketing Channels):
      SMS_BRIDGE_URL   -- ej. http://host.docker.internal:8765
      SMS_BRIDGE_TOKEN -- token compartido con el puente (header X-Bridge-Token)
    """

    def __init__(self):
        self.base_url = getattr(settings, 'SMS_BRIDGE_URL', '').rstrip('/')
        self.token = getattr(settings, 'SMS_BRIDGE_TOKEN', '')

    def send(self, to: str, message: str):
        """
        Envia un SMS de texto plano. Retorna la referencia de mensaje que
        asigna la red (o None si el puente no la reporto).
        Lanza SmsConfigError / SmsBridgeUnreachableError / SmsApiError.
        """
        if not self.base_url:
            raise SmsConfigError('SMS_BRIDGE_URL no configurado.')

        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['X-Bridge-Token'] = self.token

        try:
            resp = requests.post(
                f'{self.base_url}/sms/send',
                json={'to': to, 'message': message},
                headers=headers,
                timeout=25,  # el envio real por AT (ATA+CMGS) puede tardar varios segundos
            )
        except requests.RequestException as exc:
            logger.error('SMS bridge inalcanzable | to=%s error=%s', to, exc)
            raise SmsBridgeUnreachableError(f'No se pudo contactar el puente SMS: {exc}') from exc

        if not resp.ok:
            logger.error('SMS bridge error | to=%s status=%s body=%s', to, resp.status_code, resp.text[:500])
            raise SmsApiError(f'Puente SMS respondio {resp.status_code}: {resp.text[:200]}')

        data = resp.json()
        if not data.get('ok'):
            raise SmsApiError(data.get('error') or 'Error desconocido del puente SMS.')

        logger.info('SMS enviado | to=%s ref=%s', to, data.get('message_ref'))
        return data.get('message_ref')
