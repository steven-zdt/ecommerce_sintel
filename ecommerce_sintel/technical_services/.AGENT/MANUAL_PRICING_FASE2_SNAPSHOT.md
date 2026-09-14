# FASE 2 -- Snapshot Comercial Ampliado

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Ver `SERVICE_MANUAL_PRICING_
BASELINE.md` (FASE 0, hallazgo real: el snapshot anterior solo capturaba
`labor_cost`) y `MANUAL_PRICING_FASE1_CONTRACT.md` (FASE 1).

## Cambio

`OrderServiceDetail` gana 6 campos nuevos -- migracion
`0034_orderservicedetail_duration_snapshot_and_more.py`:

```python
pricing_source_snapshot  = CharField(null=True, blank=True)   # AUTOMATIC/MANUAL_*
pricing_mode_snapshot    = CharField(null=True, blank=True)   # HOURLY/DAILY/FIXED (solo AUTOMATIC)
unit_price_snapshot      = DecimalField(null=True, blank=True)
project_price_snapshot   = DecimalField(null=True, blank=True)
duration_snapshot        = DecimalField(null=True, blank=True)
quotation_snapshot       = JSONField(null=True, blank=True)   # dict completo de get_variant_quotation()
```

`applied_rate_type`/`applied_rate_amount` (preexistentes) **no se tocan** --
siguen consumidos por `OrderServiceDetailSerializer` sin cambios, cero riesgo de
romper un consumidor existente.

## Por que 6 campos y no solo los 5 que enumero el plan

El plan pidio explicitamente `pricing_source_snapshot`, `pricing_mode_snapshot`,
`unit_price_snapshot`, `project_price_snapshot`, `duration_snapshot` -- los 5
existen tal cual. Se agrego un sexto, `quotation_snapshot` (JSONField), porque el
propio ejemplo del plan (`{"pricing_source", "unit_price", "duration", "subtotal",
"iva", "total"}`) incluye `subtotal`/`iva`/`total`, que no caben en los 5 campos
escalares sin inventar 3 columnas mas. En vez de seguir agregando columnas,
`quotation_snapshot` guarda el dict COMPLETO que devuelve `get_variant_quotation()`
(incluye `material_cost`, `discount_amount`, `iva_amount`, `total_price`,
`breakdown` con el desglose de reglas de costo aplicadas) -- mismo patron ya
usado por `contact_person` en este mismo modelo. Los 5 campos escalares siguen
sirviendo para queries/filtros rapidos sin parsear JSON (ej. un admin filtrando
"todas las ordenes MANUAL_HOURLY del mes"); `quotation_snapshot` es el registro
historico completo para auditoria/disputas.

## Decision explicita: el motor sigue siendo 100% AUTOMATIC

`ServiceCommands.request_service()` puebla estos campos con lo que HOY puede
calcular -- `ServiceQuotationResolver`/`ManualPricingCalculator` (FASE 3/4) no
existen todavia, asi que:

```python
pricing_source_snapshot = variant.pricing_source        # ya correcto (viene de FASE 1)
pricing_mode_snapshot   = quotation.get('pricing_strategy') if not variant.is_manual_pricing else None
unit_price_snapshot     = quotation.get('labor_cost')   # PROVISIONAL -- ver nota abajo
project_price_snapshot  = None                           # siempre None hasta FASE 4
duration_snapshot       = quotation.get('breakdown', {}).get('hours')
quotation_snapshot       = quotation (Decimals top-level -> str, resto ya es JSON-safe)
```

**Nota real, no oculta:** si una variante ya tiene `pricing_source=MANUAL_PROJECT`
(posible desde FASE 1, aunque ningun endpoint lo expone todavia) y alguien la
compra HOY, `unit_price_snapshot` se llenaria con `labor_cost` (calculo AUTOMATIC,
incorrecto para ese modo) porque `get_variant_quotation()` todavia ignora
`pricing_source` por completo. Esto se corrige en FASE 4
(`ServiceQuotationResolver`) sin tocar este bloque de nuevo -- `quotation` traera
los valores correctos una vez el resolver este cableado. No es un bug de FASE 2,
es el orden de fases explicito del plan (FASE 3/4 vienen despues).

## Tests

`OrderServiceDetailCommercialSnapshotTestCase` (nueva) -- 2 tests:
1. Snapshot poblado correctamente en una orden AUTOMATIC real (`pricing_source_
   snapshot=AUTOMATIC`, `pricing_mode_snapshot=HOURLY`, `duration_snapshot`
   coincide con `estimated_hours`, `quotation_snapshot` contiene `total_price` y
   `breakdown`).
2. El snapshot sobrevive a un cambio posterior de `ServiceConfiguration` (mismo
   principio ya probado para `applied_rate_amount` -- una orden ya creada no debe
   cambiar de precio si el SMLV cambia despues).

Suite completo de `technical_services`: **146/146 PASS** (144 preexistentes +
2 nuevos), 0 regresiones.

## Siguiente fase

FASE 3 -- `ManualPricingCalculator` (`technical_services/services/manual_pricing.py`,
archivo nuevo, no mezclar con `LaborCostCalculator`).
