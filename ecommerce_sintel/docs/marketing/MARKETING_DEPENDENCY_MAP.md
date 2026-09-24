# MARKETING_DEPENDENCY_MAP — Fase 0

Mapa real de dependencias de `marketing/` (verificado por lectura de codigo, no por documentacion
previa).

## Apps que `marketing` consume

| App | Como | Archivo real |
|---|---|---|
| `shop` | `ShopSummaryProvider.get_summary()` (patron pull, sin importar modelos de `shop` directo en la logica del agente/dashboard) -- **excepcion real:** `marketing/models.py` SI importa `shop.models.ProductVariant` directo para los FK de `FlashOffer`/`PersonalOffer` (no de `MarketingCampaign`, que no tiene FK a catalogo, ver `MARKETING_BASELINE.md`) | `marketing/services/selectors.py`, `marketing/models.py:4` |
| `technical_services` | `ServicesSummaryProvider.get_summary()` + FK directo `ServiceVariant` en `FlashOffer`/`PersonalOffer` | `marketing/models.py:5` |
| `renting` | `RentingSummaryProvider.get_summary()` + FK directo `EquipmentVariant` en `FlashOffer`/`PersonalOffer` | `marketing/models.py:6` |
| `notifications` | **No usado por `MarketingCampaign`/`CampaignLog`** -- el tracking de envio de campanas es 100% propio (`CampaignLog`, `is_sent`/`error_message`), no pasa por `NotificationLog`. Confirmado en la auditoria de Email de esta misma sesion (`docs/notifications/EMAIL_GAPS.md` GAP #7): el Campaign Engine (`marketing/channels/email_channel.py`) envia Email fuera de `dispatch_notification`, por diseno. |
| `organization` | `EmailSettings` (remitente real para el canal `email` de campanas) -- mismo mecanismo auditado en la mision de Email, confirmado correcto en produccion. |
| `users` | `IsAdminUser` (permisos), `PersonalOffer.user` FK. |
| `core` | **No existe un "core/media" reusable** -- se busco explicitamente (el plan lo menciona como posible dependencia para Fase 11), no hay tal app/modulo. Lo mas cercano son los modelos `<X>Image`/`<X>Video` por dominio (ver abajo). |

## Patron real de Media a reutilizar (si se construye `CampaignMedia`, Fase 11+)

No existe un sistema de media generico/compartido en el proyecto -- cada dominio reimplementa su propio
modelo de imagen/video con el mismo shape. Ejemplos reales:

- `shop.ProductImage` (`shop/models.py:122`): `product` FK, `variant` FK opcional, `image = ImageField`,
  `alt_text`, tipo (`PRINCIPAL`/`GALERIA`/`DETALLE`/`EJEMPLO`).
- `shop.ProductVideo` (`shop/models.py:383`): `product` FK, `title`, `source_type`
  (`YOUTUBE`/`VIMEO`/`MP4` -- YouTube/Vimeo usan `video_url`, MP4 usa `video_file` subido).
- `renting.EquipmentImage` (`renting/models/equipment.py:64`): mismo patron, con mas tipos
  (`INSTALACION`/`VISTA_360`/`PLANO`).
- `technical_services.ServiceVideo` (`technical_services/models.py:530`): mismo patron que
  `ProductVideo`.

**Recomendacion para una futura Fase 11:** replicar este mismo patron (`CampaignMedia` con
`type`/`source_type`, `file`/`url` segun tipo, `sort_order`, `is_active`) en vez de inventar uno nuevo --
consistente con la regla del plan "no duplicar el sistema de media del resto del proyecto" (que en
realidad significa "seguir el mismo patron ya replicado 3 veces", no que exista un sistema central
unico).

## Canales reales (`marketing/channels/`, Fase 15 del plan)

8 adapters registrados en `channels/registry.py`, cada uno hereda `AbstractChannelAdapter`
(`channels/base.py`):

```
email            -> email_channel.py            (via organization.EmailSettings + SMTP central)
whatsapp         -> whatsapp_channel.py          (Meta Cloud API, ver whatsapp/ para el dominio real de conexion)
facebook         -> facebook_channel.py          (Meta Graph API)
instagram        -> instagram_channel.py         (Meta Graph API)
youtube          -> youtube_channel.py
tiktok           -> tiktok_channel.py
x                -> x_channel.py
google_business  -> google_business_channel.py
```

No hay SMS como canal real de campanas (distinto de `sms_bridge/`, que es un mecanismo aparte para
OTP/notificaciones puntuales via modem GSM, ver `AUDITORIA`/`.AGENT` de `notifications`) -- ver GAP #2
en `MARKETING_GAPS.md` (el frontend SI muestra un checkbox de SMS que no corresponde a ningun canal
real).

## Difusion real (Celery)

`marketing/tasks.py::send_via_channel_task` -- Celery real, `max_retries=3`, ya verificado como
funcional en la auditoria de Email de esta sesion. `marketing/agent/brain.py::MarketingAgent.run()` +
`agent/llm_router.py` (OpenAI/Anthropic/Gemini) para la generacion asistida (`AgentRun`).

## Frontend

```
/panel/marketing (Sidebar.vue:180)
  -> (FALTABA route, corregido Fase 1) frontend/src/apps/admin/routes/adminMarketing.routes.js
  -> frontend/src/modules/marketing/MarketingView.vue (tabs: Campanias / Ofertas Flash / Agente)
       -> CampaignForm.vue (crear/editar, VeeValidate via useFormValidation.js::campaignValidationSchema)
       -> AgentRunDetail.vue (solo lectura, prop `run`)
  -> frontend/src/store/marketingAdmin.js (Pinia)
       -> frontend/src/services/marketing/marketingService.js
            -> useApi().{get,post,patch,delete}('marketing/...')  -- API real, IsAdminUser server-side
```

Nota: a diferencia de la regla general de `frontend/CLAUDE.md` ("ESCRITURA -> `dashboard/...`, requiere
JWT admin"), `marketing/campaigns/` NO esta bajo el prefijo `dashboard/` -- el `ViewSet` mismo declara
`IsAdminUser`, asi que el patron sigue siendo seguro, solo con una convencion de URL distinta al resto
del panel. No se encontro ningun problema real derivado de esto en esta pasada.
