"""
Marketing Campaign Commands
Orchestrates campaign dispatch across selected channels.
Uses Celery for async execution to keep the API response fast.
"""
import logging

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from marketing.models import MarketingCampaign, CampaignLog
from marketing.channels.registry import get_adapter
from marketing.channels.base import CampaignMessage

logger = logging.getLogger(__name__)

# Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): el canal whatsapp de marketing usa
# el MISMO phone_number_id/token de Meta que notifications (envio transaccional de soporte,
# OTPs) -- ver organization.services.selectors.OrganizationSelector.get_integration_settings()
# vs notifications/clients/whatsapp.py. Sin limite propio, una rafaga de campanas de marketing
# podia consumir la cuota de mensajeria de esa cuenta y degradar/bloquear mensajes
# transaccionales de soporte que comparten el mismo numero. Mismo patron atomico
# cache.add()/cache.incr() ya usado en notifications/services/commands.py::_channel_rate_limited
# y en support/services/commands.py::is_message_flood_limited.
_WHATSAPP_MARKETING_RATE_LIMIT_KEY = 'marketing_whatsapp_throttle'
_WHATSAPP_MARKETING_RATE_LIMIT_MAX = 20
_WHATSAPP_MARKETING_RATE_LIMIT_WINDOW_SECONDS = 3600


def _marketing_whatsapp_rate_limited() -> bool:
    cache.add(_WHATSAPP_MARKETING_RATE_LIMIT_KEY, 0, timeout=_WHATSAPP_MARKETING_RATE_LIMIT_WINDOW_SECONDS)
    count = cache.incr(_WHATSAPP_MARKETING_RATE_LIMIT_KEY)
    return count > _WHATSAPP_MARKETING_RATE_LIMIT_MAX


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
            if channel == 'whatsapp' and _marketing_whatsapp_rate_limited():
                logger.warning(
                    "[MarketingCommands] whatsapp omitido por rate-limit (comparte cuota Meta "
                    "con soporte transaccional) -- campaign=%s", campaign.uuid,
                )
                continue

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
