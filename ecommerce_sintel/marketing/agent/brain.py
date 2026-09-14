"""
Marketing Intelligence Agent — Brain
Orchestrates context gathering → LLM reasoning → campaign dispatch.
"""
import json
import logging
from django.utils import timezone

# Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): este archivo importaba
# `CampaignCommands` de marketing.services.commands, una clase que nunca existio ahi (el
# nombre real siempre fue `MarketingCommands`) -- ImportError a nivel de modulo, presente desde
# el commit inicial. El agente autonomo de marketing (run_marketing_agent_task, scheduled o
# manual) NUNCA pudo ejecutarse una sola vez sin fallar en el import, antes de llegar a
# cualquier logica real. Descubierto al escribir el primer test que efectivamente importa este
# modulo (marketing/tests.py::MarketingAgentBroadcastChannelFilterTestCase).
from marketing.agent.llm_router import LLMRouter
from marketing.agent.prompts import MARKETING_AGENT_SYSTEM_PROMPT, ANALYSIS_PROMPT_TEMPLATE
from marketing.services.selectors import MarketingSelector
from marketing.services.commands import MarketingCommands
from marketing.channels.registry import BROADCAST_CHANNELS
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
            # Fase 13 (AUDITORIA/27_AUDITORIA_MARKETING.md, 2026-08-03): el agente autonomo
            # solo resuelve un sentinel "broadcast", no una lista real de destinatarios --
            # antes se pasaba ese sentinel TAMBIEN a email/whatsapp (canales que si usan
            # `recipient` como direccion real), rompiendo el envio en silencio siempre que el
            # LLM los elegia. Se filtran aqui a los canales realmente broadcast (pagina/cuenta,
            # sin destinatario individual); email/whatsapp requieren una audiencia real que este
            # flujo de un solo disparo no resuelve -- construir esa resolucion de audiencia es
            # una feature mayor, fuera de alcance de este fix incremental.
            requested_channels = decision.get("channels", [])
            dispatchable_channels = [c for c in requested_channels if c in BROADCAST_CHANNELS]
            skipped_channels = [c for c in requested_channels if c not in BROADCAST_CHANNELS]

            campaign = MarketingCampaign.objects.create(
                title=_sanitize_llm_text(decision["campaign_title"]),
                content=_sanitize_llm_text(decision["content"]),
                channels=dispatchable_channels,
                scheduled_at=timezone.now(),
                target_audience={"description": decision.get("target_audience", "")},
            )

            if skipped_channels:
                logger.warning(
                    f"[MarketingAgent] canales omitidos (requieren destinatario real que este "
                    f"flujo no resuelve): {skipped_channels}"
                )

            if dispatchable_channels:
                # Broadcast channels don't need individual recipients.
                MarketingCommands.dispatch(campaign=campaign, recipient="broadcast")

            run.status = "completed_dispatched" if dispatchable_channels else "completed_no_action"
            run.campaign = campaign
            notes = decision.get("rationale", "")
            if skipped_channels:
                notes = (notes + " " if notes else "") + (
                    f"[Fase 13] Canales omitidos por requerir destinatario real: "
                    f"{', '.join(skipped_channels)}."
                )
            run.notes = notes
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
