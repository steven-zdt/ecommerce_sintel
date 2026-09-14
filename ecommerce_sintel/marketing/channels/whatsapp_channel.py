"""
WhatsApp Channel Adapter (campanas de marketing).

Usa MetaWhatsAppClient (marketing/integrations/meta/) -- FASE 4 del plan de
integracion Meta Business. Distinto del envio transaccional
(notifications/clients/whatsapp.py, que tambien es ahora un shim sobre el mismo
cliente): este canal manda una plantilla de marketing pre-aprobada.
"""
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage
from marketing.integrations.meta.exceptions import MetaApiError
from marketing.integrations.meta.whatsapp import MetaWhatsAppClient


class WhatsAppChannelAdapter(AbstractChannelAdapter):
    channel_name = "whatsapp"

    # Debe existir aprobada en Meta Business Manager.
    TEMPLATE_NAME = "marketing_campaign"
    TEMPLATE_LANG = "es"

    def send(self, message: CampaignMessage) -> dict:
        try:
            message_id = MetaWhatsAppClient().send_template(
                to=message.recipient,
                template_name=self.TEMPLATE_NAME,
                variables={"1": message.body[:1024]},
                lang=self.TEMPLATE_LANG,
            )
            return {"success": True, "channel": self.channel_name, "response": {"message_id": message_id}}
        except MetaApiError as exc:
            return {"success": False, "channel": self.channel_name, "response": str(exc)}
