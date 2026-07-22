"""
Google Business Profile Channel Adapter
Uses Google Business Profile API (My Business API) to create local posts.
Requires OAuth2 with scope: https://www.googleapis.com/auth/business.manage
"""
import requests
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class GoogleBusinessChannelAdapter(AbstractChannelAdapter):
    channel_name = "google_business"

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    API_BASE = "https://mybusiness.googleapis.com/v4"

    def _get_access_token(self) -> str:
        # [2026-07-12] Fachada de solo lectura sobre settings, ver
        # organization.services.selectors.OrganizationSelector.get_integration_settings()
        # y MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
        from organization.services.selectors import OrganizationSelector
        integrations = OrganizationSelector.get_integration_settings()
        response = requests.post(self.TOKEN_URL, data={
            "client_id": integrations['google_business_client_id'],
            "client_secret": integrations['google_business_client_secret'],
            "refresh_token": integrations['google_business_refresh_token'],
            "grant_type": "refresh_token",
        }, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]

    def send(self, message: CampaignMessage) -> dict:
        from organization.services.selectors import OrganizationSelector
        location_name = OrganizationSelector.get_integration_settings()['google_business_location_name']
        # Format: accounts/{account_id}/locations/{location_id}
        url = f"{self.API_BASE}/{location_name}/localPosts"

        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "languageCode": "es",
                "summary": f"{message.subject}\n\n{message.body}"[:1500],
                "topicType": "STANDARD",
            }
            if message.media_url:
                payload["media"] = [{"mediaFormat": "PHOTO", "sourceUrl": message.media_url}]

            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return {"success": True, "channel": self.channel_name, "response": response.json()}
        except requests.RequestException as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
