# FASE 6-7 -- Historial dedicado + ServicePricingCommands

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Ver FASE 1-4 previas.

## FASE 6 -- `ServicePriceHistory` ampliado

Migracion `0035_servicepricehistory_pricing_source_new_and_more.py` -- 7 campos
nuevos: `pricing_source_old/new`, `unit_price_old/new`, `project_price_old/new`,
`reason`. `old_price`/`new_price` (preexistentes) quedan intactos -- siguen
siendo poblados exclusivamente por `ServiceVariantCommands.update_variant()`
cuando `fixed_price` cambia. Las dos parejas de campos nunca se mezclan en la
misma fila: una entrada de `ServicePriceHistory` es de un tipo o del otro,
segun que la disparo.

## FASE 7 -- `ServicePricingCommands.set_manual_pricing()`

`technical_services/services/commands.py` -- clase nueva, un unico metodo
maneja las 4 transiciones posibles (no hay un comando separado para "volver a
automatico" -- pasar `pricing_source=AUTOMATIC` con `unit_price=None,
project_price=None` ya lo hace):

```python
ServicePricingCommands.set_manual_pricing(
    variant, pricing_source, unit_price=None, project_price=None,
    changed_by=None, reason='',
)
```

- Valida la combinacion via `variant.clean()` **antes** de guardar -- si es
  invalida, `ValidationError` se propaga y la variante NUNCA queda con datos a
  medio guardar (verificado con test: `save()` nunca se ejecuta si `clean()`
  lanza).
- Solo crea entrada de `ServicePriceHistory` si algo realmente cambio
  (`pricing_source`/`unit_price`/`project_price` distintos de los previos) --
  llamar dos veces con los mismos valores no genera historial duplicado.
- `ServiceVariantCommands.update_variant()` (generico, sin allowlist, sin
  tocar) ahora tambien valida -- pero SOLO si `data` toca alguno de los 3
  campos de pricing (`pricing_source`, `manual_unit_price`,
  `manual_project_price`). Actualizar `complexity_factor`/`sku`/etc. sigue
  exactamente igual que antes, sin ningun `clean()` de por medio -- cero riesgo
  de que una validacion nueva rompa un caller existente que nunca toca estos 3
  campos. `update_variant()` NO genera el historial dedicado (eso es
  exclusivo de `set_manual_pricing()`, que es la via preferida segun el propio
  plan).

## Tests

`ServicePricingCommandsTestCase` (6 tests): transicion AUTOMATIC -> MANUAL_HOURLY
con historial completo (`pricing_source_old/new`, `unit_price_old/new`,
`changed_by`, `reason`); transicion de vuelta a AUTOMATIC; rechazo de una
combinacion invalida (MANUAL_PROJECT sin `project_price`) SIN guardar nada ni
generar historial; sin historial cuando no hay cambio real; `update_variant()`
valida cuando toca pricing, no valida (ni genera overhead) cuando no.
Suite completo de `technical_services`: **168/168 PASS** (162 preexistentes +
6 nuevos), 0 regresiones.

## Estado real del catalogo

Sigue sin haber ningun caller HTTP/admin que llegue a
`ServicePricingCommands.set_manual_pricing()` -- ni el ViewSet
(`AdminServiceVariantViewSet`), ni el serializer (`ServiceVariantInputSerializer`)
lo exponen todavia. Solo alcanzable via Django shell/tests. FASE 8 (Dashboard
BFF)/FASE 9 (UI) son las que lo conectan a `/panel/servicios`.
