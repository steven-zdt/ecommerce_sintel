"""
YouTube Channel Adapter
Uses YouTube Data API v3 to upload videos or post community messages.
Requires OAuth2 credentials (refresh token) pre-configured.
"""
import requests
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class YouTubeChannelAdapter(AbstractChannelAdapter):
    channel_name = "youtube"

    TOKEN_URL = "https://oauth2.googleapis.com/token"
    COMMUNITY_POST_URL = "https://www.googleapis.com/youtube/v3/communityPosts"

    def _get_access_token(self) -> str:
        """Exchange refresh token for a short-lived access token."""
        # [2026-07-12] Fachada de solo lectura sobre settings, ver
        # organization.services.selectors.OrganizationSelector.get_integration_settings()
        # y MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
        from organization.services.selectors import OrganizationSelector
        integrations = OrganizationSelector.get_integration_settings()
        response = requests.post(self.TOKEN_URL, data={
            "client_id": integrations['youtube_client_id'],
            "client_secret": integrations['youtube_client_secret'],
            "refresh_token": integrations['youtube_refresh_token'],
            "grant_type": "refresh_token",
        }, timeout=10)
        response.raise_for_status()
        return response.json()["access_token"]

    def send(self, message: CampaignMessage) -> dict:
        try:
            access_token = self._get_access_token()

            # YouTube Community Post (text + optional image)
            payload = {
                "snippet": {
                    "text": f"{message.subject}\n\n{message.body}",
                }
            }
            headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
            response = requests.post(
                f"{self.COMMUNITY_POST_URL}?part=snippet",
                json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            return {"success": True, "channel": self.channel_name, "response": response.json()}
        except requests.RequestException as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
