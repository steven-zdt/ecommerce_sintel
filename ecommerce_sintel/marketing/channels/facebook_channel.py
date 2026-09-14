"""
Facebook Channel Adapter -- publica en el feed de una Pagina de Facebook.

Usa MetaGraphClient (marketing/integrations/meta/) -- FASE 4 del plan de
integracion Meta Business. Ya no arma requests.post a mano.
"""
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage
from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import MetaApiError


class FacebookChannelAdapter(AbstractChannelAdapter):
    channel_name = "facebook"

    def send(self, message: CampaignMessage) -> dict:
        from organization.services.selectors import OrganizationSelector
        page_id = OrganizationSelector.get_integration_settings().get("facebook_page_id", "")
        if not page_id:
            return {"success": False, "channel": self.channel_name, "response": "FACEBOOK_PAGE_ID no configurado."}

        payload = {"message": f"{message.subject}\n\n{message.body}"}
        if message.media_url:
            payload["link"] = message.media_url

        try:
            response = MetaGraphClient().post(f"/{page_id}/feed", data=payload)
            return {"success": True, "channel": self.channel_name, "response": response}
        except MetaApiError as exc:
            return {"success": False, "channel": self.channel_name, "response": str(exc)}
