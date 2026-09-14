"""
Marketing Tasks
Celery tasks for agent execution and per-channel campaign dispatch.
"""
from celery import shared_task


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    name="marketing.run_agent",
    queue="marketing",
)
def run_marketing_agent_task(self, triggered_by: str = "scheduled"):
    """
    Triggers a full MarketingAgent analysis cycle.
    Can be triggered manually via API or scheduled via Celery Beat.
    """
    from marketing.agent.brain import MarketingAgent
    agent = MarketingAgent()
    run = agent.run(triggered_by=triggered_by)
    return {"status": run.status, "run_uuid": str(run.uuid)}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    max_retries=3,
    default_retry_delay=60,
    name="marketing.send_via_channel",
    queue="marketing",
)
def send_via_channel_task(self, campaign_id: str, channel: str, recipient: str,
                          media_url: str = None, log_id: str = None):
    """
    Sends a single campaign message through one channel adapter.
    Called by MarketingCommands.dispatch() — one task per channel per recipient.
    Idempotency is enforced via CampaignLog.is_sent in MarketingCommands.send_now().

    Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): importaba `CampaignCommands`,
    una clase que nunca existio en marketing.services.commands (siempre fue
    `MarketingCommands`) -- cualquier CampaignLog que llegara a encolarse fallaria aqui con
    ImportError, presente desde el commit inicial.
    """
    from marketing.services.commands import MarketingCommands
    MarketingCommands.send_now(log_id=log_id)
