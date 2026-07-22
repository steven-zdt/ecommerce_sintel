"""
TikTok Channel Adapter
Uses TikTok Content Posting API to publish videos to a Business Account.
Requires an OAuth2 access token with scope: video.upload, video.publish
"""
import requests
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class TikTokChannelAdapter(AbstractChannelAdapter):
    channel_name = "tiktok"

    BASE_URL = "https://open.tiktokapis.com/v2"

    def send(self, message: CampaignMessage) -> dict:
        # [2026-07-12] Fachada de solo lectura sobre settings, ver
        # organization.services.selectors.OrganizationSelector.get_integration_settings()
        # y MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
        from organization.services.selectors import OrganizationSelector
        token = OrganizationSelector.get_integration_settings()['tiktok_access_token']
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

        # TikTok Content Posting API — Direct Post (video required)
        # For text-only campaigns, we use the caption as a video description.
        # Supply a media_url pointing to an MP4 for full video post.
        payload = {
            "post_info": {
                "title": f"{message.subject}\n\n{message.body}"[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": message.media_url or "",
            }
        }

        try:
            response = requests.post(
                f"{self.BASE_URL}/post/publish/video/init/",
                json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            return {"success": True, "channel": self.channel_name, "response": response.json()}
        except requests.RequestException as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
