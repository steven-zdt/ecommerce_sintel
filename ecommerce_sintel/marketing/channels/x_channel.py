"""
X (Twitter) Channel Adapter
Uses Twitter API v2 to post tweets to the company's account.
Requires OAuth 2.0 Bearer Token with tweet.write scope (App-Only or User Context).
"""
import requests
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class XChannelAdapter(AbstractChannelAdapter):
    channel_name = "x"

    POST_URL = "https://api.twitter.com/2/tweets"

    def send(self, message: CampaignMessage) -> dict:
        # [2026-07-12] Fachada de solo lectura sobre settings, ver
        # organization.services.selectors.OrganizationSelector.get_integration_settings()
        # y MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
        from organization.services.selectors import OrganizationSelector
        token = OrganizationSelector.get_integration_settings()['x_bearer_token']
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Combine subject + body, trim to 280 chars
        text = f"{message.subject}\n\n{message.body}"[:280]
        payload = {"text": text}

        try:
            response = requests.post(self.POST_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return {"success": True, "channel": self.channel_name, "response": response.json()}
        except requests.RequestException as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
