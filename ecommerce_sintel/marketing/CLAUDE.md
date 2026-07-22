# App: marketing — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/marketing/.AGENT/docs/ARQUITECTURA_COMPLETA_MARKETING.md
```

## Responsabilidad de esta app

Motor de marketing multicanal con IA. Campañas, ofertas flash, ofertas personales,
agente LLM autónomo y dashboard de estadísticas de negocio consolidado.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | MarketingCampaign, FlashOffer, PersonalOffer, CampaignLog, AgentRun, SalesAnalysis |
| `api/views.py` | MarketingCampaignViewSet, FlashOfferViewSet, AgentRunViewSet, DashboardViewSet |
| `services/commands.py` | MarketingCommands: dispatch(), send_now() |
| `services/selectors.py` | MarketingSelector: get_consolidated_dashboard(), get_user_marketing_profile() |
| `channels/registry.py` | CHANNEL_REGISTRY — 8 canales: email, whatsapp, facebook, instagram, youtube, tiktok, x, google_business |
| `channels/base.py` | AbstractChannelAdapter — interfaz de envío |
| `agent/brain.py` | MarketingAgent.run() — orquesta contexto → LLM → dispatch |
| `agent/llm_router.py` | LLMRouter.complete() — soporta OpenAI, Anthropic, Gemini |
| `tasks.py` | run_marketing_agent_task, send_via_channel_task (Celery) |

## Patrones obligatorios en esta app

- **Pull-based:** Nunca importar modelos de shop/renting/services directamente.
  Usar `ShopSummaryProvider.get_summary()`, `RentingSummaryProvider.get_summary()`, `ServicesSummaryProvider.get_summary()`
- **Idempotencia:** CampaignLog tiene `unique_together=(campaign, channel, recipient)` — verificar antes de despachar
- **Channel Adapter:** Nuevo canal → crear clase en `channels/` heredando `AbstractChannelAdapter` y registrar en `CHANNEL_REGISTRY`
- **LLM:** Toda decisión del agente se loggea en `AgentRun.llm_decision` (JSONField)
- **Celery tasks:** `max_retries=3`, `default_retry_delay=60` para envíos por canal

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
