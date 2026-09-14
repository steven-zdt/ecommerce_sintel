# FASE 4 -- ServiceQuotationResolver

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Esta es la fase donde las
variantes MANUAL_* pasan de "solo tienen los campos" (FASE 1) a "efectivamente
se cotizan distinto" -- primera fase con efecto observable en produccion.

## Cambio

- `technical_services/services/quotation_resolver.py` (nuevo) --
  `ServiceQuotationResolver.resolve(variant, duration, discount_pct)`: si
  `variant.is_manual_pricing` delega en `ManualPricingCalculator.calculate()`
  (FASE 3), si no delega en la logica AUTOMATIC ya existente.
- `ServiceSelector.get_variant_quotation()` (services/selectors.py) --
  **misma firma, mismo nombre** -- ahora es un wrapper de 2 lineas que delega en
  el resolver. El cuerpo real de la logica AUTOMATIC se renombro a
  `ServiceSelector._get_automatic_quotation()` (cero cambios de logica, solo
  movido/renombrado).

Como `get_variant_quotation()` no cambio de firma ni de nombre, **ningun
caller existente se toco**: `ServiceVariantSerializer` (api/serializers.py),
`ServiceCommands.request_service()` (services/commands.py),
`PackagePriceCalculator`/`ServiceRequestPackageCommands` (services/packages.py)
y `TechnicalServiceViewSet.quotation` (api/views.py, el endpoint publico) ya
enrutan automaticamente segun `pricing_source` sin que nadie mas los haya
modificado. Esto confirma el diagrama del propio plan (`get_variant_quotation()
-> ServiceQuotationResolver -> AUTOMATIC | MANUAL`) tal cual.

## Import diferido, no circular

`quotation_resolver.py` y `selectors.py` se importan mutuamente -- ambos
imports estan DENTRO de metodos (no a nivel de modulo) para evitar un ciclo en
tiempo de carga de Django. Verificado con un import real
(`django.setup()` + import de los 3 modulos) antes de correr tests.

## Bug real atrapado por el propio test suite de esta fase

`ServiceCommands.request_service()` (el snapshot de FASE 2) leia
`quotation.get('labor_cost')` como `unit_price_snapshot` para TODOS los modos
manuales. Para `MANUAL_GENERAL` es correcto (`labor_cost == manual_unit_price`,
sin multiplicar por nada), pero para `MANUAL_HOURLY` `labor_cost` es
`unit_price x duration` (el TOTAL, no la tarifa) -- un test end-to-end
(`test_manual_hourly_order_snapshots_unit_price_and_duration`) lo atrapo antes
de llegar a produccion: con tarifa $85.000/h x 6h, `unit_price_snapshot`
quedaba en `$510.000` en vez de `$85.000`. Corregido leyendo
`breakdown['unit_price']` (que `ManualPricingCalculator` ya deja explicito para
exactamente este caso) en vez de `labor_cost` para los 2 modos MANUAL_GENERAL/
MANUAL_HOURLY.

## Tests

- `ServiceQuotationResolverTestCase` (7 tests) -- dispatch directo del resolver
  (unit) + **el endpoint publico real** (`GET /api/v1/services/services/
  quotation/`) sirviendo los 3 modos MANUAL_* y confirmando que AUTOMATIC sigue
  funcionando igual (regresion explicita). Incluye el caso de un variant mal
  configurado (`MANUAL_HOURLY` sin `manual_unit_price`, forzado via `.update()`
  para saltarse la validacion del modelo) -- confirma 400, no 500.
- `OrderServiceDetailManualSnapshotTestCase` (2 tests) -- snapshot real de
  ordenes MANUAL_PROJECT/MANUAL_HOURLY via `request_service()`, incluye el caso
  que atrapo el bug de arriba.

Suite completo de `technical_services`: **162/162 PASS** (154 preexistentes +
8 nuevos), 0 regresiones.

## Estado real del catalogo despues de esta fase

Toda `ServiceVariant` con `pricing_source=AUTOMATIC` (el default, y hoy el
unico valor real en la base de datos -- FASE 1/2/3 no crearon ninguna variante
MANUAL_* en produccion) sigue cotizando exactamente igual que antes de este
plan completo. El motor manual esta **live** pero sin ningun caller real en el
panel todavia -- ningun admin puede poner `pricing_source=MANUAL_*` desde
`/panel/servicios` (eso es FASE 7 Commands + FASE 9 UI). Solo es alcanzable hoy
via Django admin/shell/tests.

## Siguiente fase

FASE 5 ya esta cubierta de facto por las decisiones de FASE 3 (sin reglas de
costo ni materiales sobre precio manual). FASE 6 -- ampliar
`ServicePriceHistory` con `reason`/`pricing_source_old`/`pricing_source_new`.
FASE 7 -- `ServicePricingCommands.set_manual_pricing()` (comando dedicado,
decision ya tomada en FASE 0 baseline).
