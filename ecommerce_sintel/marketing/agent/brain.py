"""
Marketing Intelligence Agent — Brain
Orchestrates context gathering → LLM reasoning → campaign dispatch.
"""
import json
import logging
from django.utils import timezone

from marketing.agent.llm_router import LLMRouter
from marketing.agent.prompts import MARKETING_AGENT_SYSTEM_PROMPT, ANALYSIS_PROMPT_TEMPLATE
from marketing.services.selectors import MarketingSelector
from marketing.services.commands import CampaignCommands
from marketing.models import MarketingCampaign, AgentRun

logger = logging.getLogger(__name__)


def _sanitize_llm_text(value):
    """
    Los LLMs ocasionalmente duplican el signo de porcentaje ("20%%" en vez de
    "20%") al generar copy promocional -- probablemente sobregeneralizan el
    escape de %-formatting visto en datos de entrenamiento (hallazgo real,
    auditoria QA 2026-07-19: aparecio en una campana y una oferta generadas
    por este agente). Nunca se debe confiar en output crudo de LLM para
    contenido publicado sin sanear.
    """
    return value.replace('%%', '%') if value else value


class MarketingAgent:
    """
    The autonomous brain of the marketing module.
    Reads business context, reasons with an LLM, and dispatches campaigns.
    """

    def run(self, triggered_by: str = "manual") -> AgentRun:
        """
        Execute one analysis cycle.
        triggered_by: 'manual' | 'scheduled'
        Returns an AgentRun record logging the result.
        """
        run = AgentRun.objects.create(
            triggered_by=triggered_by,
            status="running",
        )
        try:
            # 1. Gather context from all business apps
            dashboard = MarketingSelector.get_consolidated_dashboard()

            user_prompt = ANALYSIS_PROMPT_TEMPLATE.format(
                current_time=timezone.now().strftime("%Y-%m-%d %H:%M (%A)"),
                shop_summary=json.dumps(dashboard.get("shop", {}), indent=2, default=str),
                renting_summary=json.dumps(dashboard.get("renting", {}), indent=2, default=str),
                services_summary=json.dumps(dashboard.get("technical_services", {}), indent=2, default=str),
                platform_overview=json.dumps(dashboard.get("platform_overview", {}), indent=2, default=str),
            )

            # 2. Reason with the configured LLM
            raw_response = LLMRouter.complete(
                system_prompt=MARKETING_AGENT_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
            logger.info(f"[MarketingAgent] LLM Response: {raw_response}")

            # 3. Parse LLM decision
            decision = json.loads(raw_response)
            run.llm_decision = decision
            run.llm_provider = self._get_provider()

            if not decision.get("should_dispatch", False):
                run.status = "completed_no_action"
                run.notes = decision.get("rationale", "No action needed.")
                run.save()
                return run

            # 4. Create and dispatch campaign
            campaign = MarketingCampaign.objects.create(
                title=_sanitize_llm_text(decision["campaign_title"]),
                content=_sanitize_llm_text(decision["content"]),
                channels=decision.get("channels", []),
                scheduled_at=timezone.now(),
                target_audience={"description": decision.get("target_audience", "")},
            )

            # Dispatch to all registered channels (no specific recipient needed for social/broadcast)
            CampaignCommands.dispatch(
                campaign=campaign,
                recipient="broadcast",  # Broadcast channels don't need individual recipients
            )

            run.status = "completed_dispatched"
            run.campaign = campaign
            run.notes = decision.get("rationale", "")
            run.save()

            logger.info(f"[MarketingAgent] Campaign dispatched: {campaign.title} → {campaign.channels}")
            return run

        except Exception as e:
            logger.error(f"[MarketingAgent] Error: {e}", exc_info=True)
            run.status = "failed"
            run.notes = str(e)
            run.save()
            return run

    def _get_provider(self) -> str:
        from django.conf import settings
        return getattr(settings, 'MARKETING_AGENT_PROVIDER', 'openai')
