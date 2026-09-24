# MARKETING_CAMPAIGN_MODEL

Fuente de verdad: `marketing/models.py`. Detalle historico por fase en `MARKETING_GAPS.md`.

## Entidades
- `MarketingCampaign`: title (headline), content (body), subheadline, description, cta_label, cta_url,
  terms, valid_from/valid_until (vigencia de la oferta), channels (JSON, subconjunto de
  `CHANNEL_REGISTRY`), target_audience (JSON), scheduled_at/sent_at/is_completed (envio).
- `CampaignItem`: FK a campana + content_type + object_uuid + quantity (patron CatalogRelation, sin
  GenericForeignKey). Soporta Producto, Servicio (`technical_services.technicalservice`) y Renting
  (`renting.equipmentvariant`). 0 items = campana "desde cero". "2 camaras" = 1 item con quantity=2.
- `CampaignBenefit`: FREE_SHIPPING, FREE_INSTALLATION, DISCOUNT_PERCENT, DISCOUNT_FIXED (+label, value).
- `CampaignMedia`: ver `MARKETING_MEDIA.md`.
- `CampaignLog`: tracking por canal/destinatario (idempotente, unique campaign+channel+recipient).

## Estado (derivado, sin columna)
`get_status()` en el serializer: DRAFT / SCHEDULED / RUNNING / COMPLETED segun `is_completed`, `logs` y
`scheduled_at`.

## API (`/api/v1/marketing/campaigns/`, todo `IsAdminUser`)
CRUD estandar; `items` y `benefits` son listas anidadas con reemplazo completo al enviarse (si se
omiten, no se tocan). Lectura de items incluye `preview` resuelto en vivo desde el catalogo real.
Acciones: `media/`, `media/reorder/`, `media/<uuid>/`, `media/<uuid>/toggle/`, `send/`, `preview/`.

## No implementado (gaps conscientes)
Activar/desactivar manual (no hay `is_active`), Pausar/Cancelar (sin cancelacion de tasks Celery en el
proyecto), soft-delete (DELETE es fisico), programacion automatica por `scheduled_at` desde UI,
botones IA (sin claves LLM reales en dev).
