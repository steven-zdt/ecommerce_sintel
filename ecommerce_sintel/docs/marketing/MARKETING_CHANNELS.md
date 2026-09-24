# MARKETING_CHANNELS

Registro real: `marketing/channels/registry.py` (`CHANNEL_REGISTRY`), 8 canales:
email, whatsapp (directos: requieren `recipient`) y facebook, instagram, youtube, tiktok, x,
google_business (broadcast: publican a la cuenta conectada, sentinel `recipient="broadcast"`).
No existe canal SMS (checkbox fantasma retirado del formulario).

## Flujo
UI (`CampaignDispatchPanel.vue`) -> `POST campaigns/<uuid>/send/` -> `MarketingCommands.dispatch()`
-> `CampaignLog` (idempotente) -> Celery `send_via_channel_task` -> `send_now()` -> adapter -> resultado
en `CampaignLog.is_sent/error_message`. Email reutiliza el servicio de notifications; WhatsApp respeta
el rate-limit compartido con soporte. Canales directos sin `recipient` se omiten y se reportan en
`skipped_channels`.

## Preview
`GET campaigns/<uuid>/preview/` usa `MarketingCommands.build_message()`, el mismo metodo del envio real.

## Observabilidad (log estructurado `marketing_event=...`)
campaign_created, campaign_updated, campaign_deleted, campaign_sent, channel_send_started,
channel_send_success, channel_send_failed, media_uploaded, media_removed. Resultado por canal auditado
en `CampaignLog`. Pendientes por no tener mecanismo: campaign_activated/deactivated/scheduled/failed.
