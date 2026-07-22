"""
Marketing Campaign Commands
Orchestrates campaign dispatch across selected channels.
Uses Celery for async execution to keep the API response fast.
"""
from django.db import transaction
from django.utils import timezone
from marketing.models import MarketingCampaign, CampaignLog
from marketing.channels.registry import get_adapter
from marketing.channels.base import CampaignMessage


class MarketingCommands:

    @staticmethod
    @transaction.atomic
    def dispatch(campaign: MarketingCampaign, recipient: str, media_url: str = None):
        """
        Enqueues async tasks for each selected channel in the campaign.
        Called from the API view; returns immediately (202 pattern).
        """
        from marketing.tasks import send_via_channel_task

        for channel in campaign.channels:
            log, created = CampaignLog.objects.get_or_create(
                campaign=campaign,
                channel=channel,
                recipient=recipient,
            )
            if log.is_sent:
                continue  # Idempotency: skip already-sent logs

            send_via_channel_task.delay(
                campaign_id=str(campaign.uuid),
                channel=channel,
                recipient=recipient,
                media_url=media_url,
                log_id=str(log.uuid),
            )

    @staticmethod
    @transaction.atomic
    def send_now(log_id: str):
        """
        Executes a single CampaignLog send. Called by Celery worker.
        """
        log = CampaignLog.objects.select_related('campaign').get(uuid=log_id)
        if log.is_sent:
            return

        campaign = log.campaign
        message = CampaignMessage(
            recipient=log.recipient,
            subject=campaign.title,
            body=campaign.content,
        )

        adapter = get_adapter(log.channel)
        result = adapter.send(message)

        log.is_sent = result["success"]
        log.sent_at = timezone.now() if result["success"] else None
        log.error_message = result["response"] if not result["success"] else ""
        log.save()
