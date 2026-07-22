"""
Facebook Channel Adapter
Uses Meta Graph API to post on a Facebook Page.
"""
import requests
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class FacebookChannelAdapter(AbstractChannelAdapter):
    channel_name = "facebook"

    BASE_URL = "https://graph.facebook.com/v19.0"

    def send(self, message: CampaignMessage) -> dict:
        # [2026-07-12] Fachada de solo lectura sobre settings, ver
        # organization.services.selectors.OrganizationSelector.get_integration_settings()
        # y MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
        from organization.services.selectors import OrganizationSelector
        integrations = OrganizationSelector.get_integration_settings()
        page_id = integrations['facebook_page_id']
        token = integrations['meta_access_token']
        url = f"{self.BASE_URL}/{page_id}/feed"

        payload = {
            "message": f"{message.subject}\n\n{message.body}",
            "access_token": token,
        }
        if message.media_url:
            payload["link"] = message.media_url

        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            return {"success": True, "channel": self.channel_name, "response": response.json()}
        except requests.RequestException as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
