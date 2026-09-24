# MARKETING_BASELINE — Fase 0 de PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md

**Fecha:** 2026-09-23. **Metodo:** lectura directa de codigo real (`marketing/`, `frontend/src/modules/
marketing/`, `frontend/src/apps/admin/router.js`), mas reproduccion real via API (curl + JWT admin real)
contra `ecommerce_sintel_django` (dev). No se asumio nada del plan ni de `marketing/CLAUDE.md`.

## Estado real vs. lo que el plan asume

| Componente que el plan asume/pide | Estado real |
|---|---|
| `MarketingCampaignViewSet` -- `IsAdminUser`, ModelViewSet completo | **Existe y funciona.** `marketing/api/views.py:16`, CRUD completo via DRF `ModelViewSet` generico (sin logica custom), `POST /api/v1/marketing/campaigns/` verificado con **201 Created** real (2 payloads distintos probados, incluido el formato exacto que produce `<input type="datetime-local">`). |
| `/panel/marketing` no permite crear campanias | **Causa real encontrada: la ruta NUNCA estuvo registrada en el router del frontend.** `Sidebar.vue:180` enlaza a `/panel/marketing` desde siempre, pero `frontend/src/apps/admin/router.js` no tenia ninguna entrada para ese path ni importaba `MarketingView.vue` -- el usuario no podia ni siquiera LLEGAR al formulario, la API nunca estuvo rota. Mismo patron exacto que el bug de `/panel/asistente` resuelto en una mision anterior de esta misma sesion. **Corregido en Fase 1** (ver `MARKETING_GAPS.md` GAP #1). |
| Canales de envio -- "la documentacion no establece cuales son todos" | **8 canales reales, registrados en `marketing/channels/registry.py`:** `email`, `whatsapp`, `facebook`, `instagram`, `youtube`, `tiktok`, `x`, `google_business`. Cada uno con su propio archivo (`email_channel.py`, `whatsapp_channel.py`, etc.) heredando `AbstractChannelAdapter` (`base.py`). Coincide con `MarketingCampaign.CHANNEL_CHOICES` en `models.py` -- **pero ese campo `choices` es cosmetico**, el `JSONField` no lo valida en runtime (confirmado: no hay `validators=` en el modelo ni en el serializer). |
| Campana desde Producto/Servicio/Renting (Fase 3-6 del plan) | **No existe.** `MarketingCampaign` no tiene ningun FK a `ProductVariant`/`ServiceVariant`/`EquipmentVariant` (esos SI existen en `FlashOffer`/`PersonalOffer`, modelos hermanos, pero NO en `MarketingCampaign`). Crear una campana "desde catalogo" hoy es imposible sin cambiar el modelo. |
| Campanas compuestas (Fase 7, "2 camaras + transporte + instalacion gratis") | **No existe.** No hay modelo `CampaignItem`/`CampaignBenefit` ni nada equivalente. `MarketingCampaign.content` es un unico `TextField` libre -- toda la oferta hoy se redacta como texto plano, sin estructura. |
| Contenido estructurado (headline/subheadline/body/CTA/terms, Fase 10) | **No existe.** Campos reales de `MarketingCampaign`: `title`, `content` (texto libre), `channels` (JSON), `scheduled_at`, `sent_at`, `target_audience` (JSON, sin uso real encontrado en esta pasada), `is_completed` (booleano). Nada de CTA, terms, benefit_text por separado. |
| Media imagen/video (Fase 11-14) | **No existe en `MarketingCampaign`.** No hay `CampaignMedia`, ni `image`/`video` field alguno. Si existe un patron real a reutilizar en otras apps del proyecto (`shop.ProductImage`/`ProductVideo`, `renting.EquipmentImage`, `technical_services.ServiceVideo` -- mismo shape: `type`/`source_type`, `file` o `url`, `sort_order`/`position`, `is_active`/`is_primary`), ver `MARKETING_DEPENDENCY_MAP.md`. |
| Estados de campana DRAFT->READY->SCHEDULED->RUNNING->COMPLETED (Fase 17) | **No existe.** Solo hay `is_completed` (booleano) y `sent_at` (null hasta que se envia). No hay maquina de estados, no hay `DRAFT`/`READY`/`RUNNING` como conceptos separados. |
| Contrato de canal (`CampaignChannelLog`: campaign/channel/status/scheduled_at/sent_at/failed_at/external_id/error, Fase 16) | **Ya existe, con otro nombre: `CampaignLog`** (`models.py:118`). Campos reales: `campaign`, `channel`, `recipient`, `is_sent`, `sent_at`, `error_message`. `unique_together=('campaign','channel','recipient')` para idempotencia (documentado en `marketing/CLAUDE.md`). No tiene `status` como enum (solo `is_sent` booleano) ni `scheduled_at`/`failed_at`/`external_id` propios -- mas simple que lo que el plan describe, pero cubre el proposito central (tracking + idempotencia). **No duplicar -- coincide con la instruccion explicita del plan de reusar el contrato existente.** |
| Difusion Campaign -> Channel -> Celery -> Provider (Fase 18-20) | **Ya existe y funciona**, no es un placeholder: `marketing/tasks.py::send_via_channel_task` (Celery, `max_retries=3`, confirmado en la auditoria de Email de esta misma sesion, ver `docs/notifications/EMAIL_GAPS.md` GAP #7). Los 8 adapters de `channels/` implementan el envio real por proveedor. |
| `AgentRun`/IA complementaria (Fase 21) | **Ya existe y es real, no un scaffold.** `marketing/agent/brain.py::MarketingAgent.run()`, `agent/llm_router.py` (soporta OpenAI/Anthropic/Gemini), `AgentRun` persiste cada ejecucion con `llm_decision` (JSON). `AgentRunViewSet` (ReadOnly, `IsAdminUser`) ya expone esto al panel. |
| Permisos (Fase 23) | **Correcto tal cual.** `MarketingCampaignViewSet.permission_classes = [IsAdminUser]`, confirmado -- ningun endpoint de escritura de campanas es accesible sin admin. |
| Tests backend (Fase 24) | `marketing/tests.py`: **58 tests, OK** (corridos en esta auditoria, ver `MARKETING_GAPS.md`). Cobertura real existente antes de tocar nada: incluye `MetaGraphClient` (canales Meta), WhatsApp send, mas los tests generales del modulo -- no se audito exhaustivamente cuales de los 58 cubren especificamente `MarketingCampaign` CRUD (ver gap en `MARKETING_GAPS.md`). |

## Conclusion de la Fase 0

**El "bug" que motivo esta mision (`/panel/marketing` no permite crear campanias") tenia una causa
trivial y ya corregida (Fase 1): una ruta de frontend faltante.** El backend (modelo, API, permisos,
service layer, canales, Celery, IA) estaba sano desde antes -- nada de eso estaba roto.

**Pero el resto del plan (Fases 3-17: catalogo como base, campanas compuestas, beneficios, contenido
estructurado, media) es trabajo genuinamente nuevo de principio a fin**, muy similar en naturaleza al
hallazgo de `ASSISTANT_BASELINE.md` en la mision del Admin AI Assistant: el modulo real hoy es un CRUD
simple de 6 campos (`title`/`content`/`channels`/`scheduled_at`/`sent_at`/`is_completed`) mas
distribucion multicanal real -- no tiene absolutamente nada de integracion con catalogo, composicion,
beneficios estructurados o media. Construir eso implica: nuevos campos/modelos en `MarketingCampaign`
(o modelos satelite `CampaignItem`/`CampaignBenefit`/`CampaignMedia`), nuevas migraciones, nuevos
endpoints (`dashboard/api/` para escritura de estos sub-recursos, si se sigue la convencion documentada
en `frontend/CLAUDE.md`), UI nueva (selector de catalogo, formulario de beneficios, galeria de media,
selector de canales dinamico) -- semanas de trabajo, no una correccion puntual.

**GATE: PASS** para declarar la Fase 0 completa (auditoria honesta, verificada contra codigo real y
contra un intento de creacion real via API, sin inventar componentes).

Ver `MARKETING_GAPS.md` para el detalle de hallazgos con severidad y `MARKETING_DEPENDENCY_MAP.md` para
el mapa de dependencias reales de `marketing/`.
