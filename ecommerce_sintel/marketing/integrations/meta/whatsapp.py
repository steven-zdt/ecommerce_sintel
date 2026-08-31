"""
MetaWhatsAppClient -- envio transaccional por WhatsApp Cloud API, construido
sobre MetaGraphClient.

Reemplaza el transporte propio (requests.Session + parseo de errores) que vivia
en notifications/clients/whatsapp.py. El contrato publico (send_template /
send_text, y el message_id que devuelven) se mantiene identico -- ver el shim
de compatibilidad en notifications/clients/whatsapp.py.

Meta solo permite send_text (texto libre) dentro de la ventana de servicio de
24h que abre un mensaje entrante del cliente; fuera de esa ventana hay que usar
una plantilla aprobada (send_template).
"""
import logging

from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import MetaConfigError

logger = logging.getLogger(__name__)

_TEXT_MAX_LEN = 4000
_DEFAULT_TEMPLATE_LANG = "es_CO"


class MetaWhatsAppClient:

    def __init__(self, *, graph: MetaGraphClient | None = None):
        self._graph = graph or MetaGraphClient()
        self._phone_id = self._graph._settings.get("whatsapp_phone_number_id", "") or ""

    def _messages_path(self) -> str:
        if not self._phone_id:
            raise MetaConfigError("WHATSAPP_PHONE_NUMBER_ID no configurado.")
        return f"/{self._phone_id}/messages"

    @staticmethod
    def _first_message_id(data: dict) -> str:
        return (data.get("messages") or [{}])[0].get("id", "")

    def send_template(self, to: str, template_name: str, variables: dict,
                      lang: str = _DEFAULT_TEMPLATE_LANG) -> str:
        """
        Envia una plantilla aprobada por Meta. Los valores de `variables` se
        mapean EN ORDEN como {{1}}, {{2}}, ... en el cuerpo de la plantilla.
        Devuelve el message_id de WhatsApp.
        """
        path = self._messages_path()
        components = []
        if variables:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": str(v)} for v in variables.values()],
            })
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": lang},
                "components": components,
            },
        }
        data = self._graph.post(path, json=payload)
        message_id = self._first_message_id(data)
        logger.info("WhatsApp enviado | to=%s template=%s msg_id=%s", to, template_name, message_id)
        return message_id

    def send_text(self, to: str, body: str) -> str:
        """Envia texto libre (respuestas conversacionales del Action Graph).
        Solo valido dentro de la ventana de 24h abierta por el mensaje entrante
        del cliente -- exactamente el caso del webhook."""
        path = self._messages_path()
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": (body or "")[:_TEXT_MAX_LEN]},
        }
        data = self._graph.post(path, json=payload)
        message_id = self._first_message_id(data)
        logger.info("WhatsApp texto enviado | to=%s msg_id=%s", to, message_id)
        return message_id
