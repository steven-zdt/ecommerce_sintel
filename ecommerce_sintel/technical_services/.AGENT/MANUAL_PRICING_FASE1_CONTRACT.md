# FASE 1 -- Contrato formal de Pricing Source

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Ver
`SERVICE_MANUAL_PRICING_BASELINE.md` (FASE 0) para el contexto completo.

## Cambio

`ServiceVariant` (`technical_services/models.py`) gana 3 campos nuevos --
migracion `0033_servicevariant_manual_project_price_and_more.py`:

```python
SOURCE_AUTOMATIC = 'AUTOMATIC'
SOURCE_MANUAL_PROJECT = 'MANUAL_PROJECT'
SOURCE_MANUAL_GENERAL = 'MANUAL_GENERAL'
SOURCE_MANUAL_HOURLY = 'MANUAL_HOURLY'

pricing_source = CharField(choices=..., default=SOURCE_AUTOMATIC, db_index=True)
manual_unit_price = DecimalField(null=True, blank=True)     # MANUAL_GENERAL | MANUAL_HOURLY
manual_project_price = DecimalField(null=True, blank=True)  # MANUAL_PROJECT
```

Contrato reducido tal como lo propuso el usuario -- **no** 3 campos redundantes
por modo. `MANUAL_GENERAL` y `MANUAL_HOURLY` comparten `manual_unit_price`; la
diferencia (si `duration` multiplica o no) se resuelve en el motor de calculo
(FASE 3), no en el modelo.

## Reglas de validacion (`ServiceVariant.clean()`)

| pricing_source | manual_unit_price | manual_project_price |
|---|---|---|
| `AUTOMATIC` | debe ser `None` | debe ser `None` |
| `MANUAL_PROJECT` | debe ser `None` | requerido, `> 0` |
| `MANUAL_GENERAL` | requerido, `> 0` | debe ser `None` |
| `MANUAL_HOURLY` | requerido, `> 0` | debe ser `None` |

`ValidationError` si se viola cualquiera de estas combinaciones. Property
`is_manual_pricing` (`True` para los 3 modos MANUAL_*) -- helper que usara FASE 4
(`ServiceQuotationResolver`) para decidir el motor sin repetir el `in (...)` en
cada caller.

**Deliberadamente NO se toca `pricing_strategy`/`fixed_price`/`estimated_hours`**
-- quedan intactos y siguen siendo la fuente de verdad cuando `pricing_source ==
AUTOMATIC` (comportamiento actual, cero cambios). Si un admin cambia una variante
de MANUAL a AUTOMATIC, la configuracion de mano de obra previa sigue ahi, no hay
que reconfigurarla desde cero.

## Explicitamente FUERA de esta fase

- `ManualPricingCalculator` (FASE 3) -- no existe todavia.
- `ServiceQuotationResolver` (FASE 4) -- `get_variant_quotation()` sigue
  ignorando `pricing_source` por completo (todas las variantes, incluso las que
  ahora tienen `pricing_source=MANUAL_*`, se siguen cotizando 100% AUTOMATIC
  hasta FASE 4). Esto es intencional -- FASE 1 es solo el contrato de datos.
- Serializers/Commands/Dashboard/Frontend -- ningun endpoint expone estos campos
  todavia (`ServiceVariantInputSerializer`/`ServiceVariantSerializer` sin tocar).
  Un admin no puede setear `pricing_source` desde el panel hasta FASE 7/9.

## Tests

`ServiceVariantPricingSourceTestCase` (nueva, `technical_services/tests.py`) --
12 tests cubriendo las 4 combinaciones validas + sus violaciones (falta el precio
requerido, precio en cero/negativo, precio del modo incorrecto seteado). Suite
completo de `technical_services`: **144/144 PASS** (132 preexistentes + 12
nuevos), 0 regresiones.

## Siguiente fase

FASE 2 -- ampliar el snapshot comercial de `OrderServiceDetail` (ver hallazgo
real de `SERVICE_MANUAL_PRICING_BASELINE.md` §1: el snapshot actual solo
captura `labor_cost`, no el total completo -- FASE 2 es extension real, no
solo agregar columnas).
