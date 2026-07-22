"""
Instagram Channel Adapter
Uses Meta Graph API to publish a photo/video post on Instagram Business Account.
Two-step process: 1) Create container, 2) Publish.
"""
import requests
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class InstagramChannelAdapter(AbstractChannelAdapter):
    channel_name = "instagram"

    BASE_URL = "https://graph.facebook.com/v19.0"

    def send(self, message: CampaignMessage) -> dict:
        # [2026-07-12] Fachada de solo lectura sobre settings, ver
        # organization.services.selectors.OrganizationSelector.get_integration_settings()
        # y MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
        from organization.services.selectors import OrganizationSelector
        integrations = OrganizationSelector.get_integration_settings()
        account_id = integrations['instagram_business_account_id']
        token = integrations['meta_access_token']

        # Step 1: Create media container
        container_url = f"{self.BASE_URL}/{account_id}/media"
        caption = f"{message.subject}\n\n{message.body}"

        container_payload = {
            "caption": caption[:2200],  # Instagram caption limit
            "access_token": token,
        }
        if message.media_url:
            container_payload["image_url"] = message.media_url
        else:
            # Instagram requires an image for most post types
            return {"success": False, "channel": self.channel_name, "response": "Instagram requires a media_url for posts."}

        try:
            container_response = requests.post(container_url, data=container_payload, timeout=10)
            container_response.raise_for_status()
            creation_id = container_response.json().get("id")

            # Step 2: Publish the container
            publish_url = f"{self.BASE_URL}/{account_id}/media_publish"
            publish_response = requests.post(publish_url, data={"creation_id": creation_id, "access_token": token}, timeout=10)
            publish_response.raise_for_status()
            return {"success": True, "channel": self.channel_name, "response": publish_response.json()}
        except requests.RequestException as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
