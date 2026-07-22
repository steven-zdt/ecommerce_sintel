"""
Email Channel Adapter
Uses Django's email backend (compatible with SendGrid via django-anymail).
"""
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from marketing.channels.base import AbstractChannelAdapter, CampaignMessage


class EmailChannelAdapter(AbstractChannelAdapter):
    channel_name = "email"

    def send(self, message: CampaignMessage) -> dict:
        try:
            # [2026-07-12] Lee de organization.EmailSettings (SSoT), settings.DEFAULT_FROM_EMAIL
            # como fallback -- ver MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md.
            from organization.services.selectors import OrganizationSelector
            email_settings = OrganizationSelector.get_email_settings()
            from_email = (email_settings.default_from_email if email_settings else '') or settings.DEFAULT_FROM_EMAIL

            email = EmailMultiAlternatives(
                subject=message.subject,
                body=message.body,
                from_email=from_email,
                to=[message.recipient],
            )
            email.send(fail_silently=False)
            return {"success": True, "channel": self.channel_name, "response": "Sent via Django Email Backend"}
        except Exception as e:
            return {"success": False, "channel": self.channel_name, "response": str(e)}
