"""
Instagram Channel Adapter -- publica una foto en un Instagram Business Account.
Proceso de 2 pasos de la Graph API: 1) crear contenedor de media, 2) publicarlo.

Usa MetaGraphClient (marketing/integrations/meta/) -- FASE 4 del plan de
integracion Meta Business.
"""
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage
from marketing.integrations.meta.client import MetaGraphClient
from marketing.integrations.meta.exceptions import MetaApiError


class InstagramChannelAdapter(AbstractChannelAdapter):
    channel_name = "instagram"

    def send(self, message: CampaignMessage) -> dict:
        from organization.services.selectors import OrganizationSelector
        account_id = OrganizationSelector.get_integration_settings().get("instagram_business_account_id", "")
        if not account_id:
            return {"success": False, "channel": self.channel_name, "response": "INSTAGRAM_BUSINESS_ACCOUNT_ID no configurado."}
        if not message.media_url:
            return {"success": False, "channel": self.channel_name, "response": "Instagram requiere media_url para publicar."}

        caption = f"{message.subject}\n\n{message.body}"
        client = MetaGraphClient()

        try:
            container = client.post(f"/{account_id}/media", data={
                "caption": caption[:2200],  # limite de caption de Instagram
                "image_url": message.media_url,
            })
            creation_id = container.get("id")
            if not creation_id:
                return {"success": False, "channel": self.channel_name, "response": "Meta no devolvio creation_id."}
            published = client.post(f"/{account_id}/media_publish", data={"creation_id": creation_id})
            return {"success": True, "channel": self.channel_name, "response": published}
        except MetaApiError as exc:
            return {"success": False, "channel": self.channel_name, "response": str(exc)}
