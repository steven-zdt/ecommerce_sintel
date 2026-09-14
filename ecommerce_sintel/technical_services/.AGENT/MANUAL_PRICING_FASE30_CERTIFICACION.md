# FASE 30 -- Certificacion de los 4 modos de pricing

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Objetivo: probar los 4
modos (`AUTOMATIC`, `MANUAL_PROJECT`, `MANUAL_GENERAL`, `MANUAL_HOURLY`) a
traves del stack real (Panel -> guardar -> cotizacion -> orden -> snapshot),
sin mocks.

## Cobertura por modo

| Modo | Configuracion (panel/comando) | Cotizacion publica | Orden + snapshot |
|---|---|---|---|
| `AUTOMATIC` | Ya certificado, es el comportamiento pre-existente (SMLV/fijo) | OK (suite completa) | OK (suite completa) |
| `MANUAL_HOURLY` | Verificado en navegador real, FASE 8-9 (`$85.000/h` -> `$101.150` total, confirmado en Postgres) | OK (navegador) | OK (navegador) |
| `MANUAL_PROJECT` | **Verificado en este incremento** -- `ServicePricingCommands.set_manual_pricing()` real contra la variante `SVC-servicio-fijo-prueba-MQMN43CB` (`Servicio Fijo Prueba`) | OK -- ver abajo | OK -- ver abajo |
| `MANUAL_GENERAL` | **Verificado en este incremento** -- misma variante, mismo mecanismo | OK -- ver abajo | OK -- ver abajo |

`MANUAL_PROJECT`/`MANUAL_GENERAL` se certificaron contra el stack de comandos
real (`ServicePricingCommands` -> `ServiceSelector.get_variant_quotation()`
-> `ServiceCommands.request_service()`), no via navegador+checkout: un
checkout real dispara Wompi (cobro), y automatizar eso esta fuera de lo que
se debe ejecutar sin que el usuario lo apruebe explicitamente por cada cargo.
La ruta de comandos ejercitada aqui es la MISMA que invoca el checkout real
(`orders`/`payment` no tienen un camino alterno para crear
`OrderServiceDetail` -- todo pasa por `ServiceCommands.request_service()`),
asi que la cobertura es equivalente sin el riesgo de un cargo real.

### MANUAL_PROJECT (project_price=$500.000)

```
ServicePricingCommands.set_manual_pricing(v, MANUAL_PROJECT, project_price=500000)
-> ServiceSelector.get_variant_quotation(v):
   labor_cost=500000.00, iva_amount=95000.00, total_price=595000.00
   breakdown.labor_calculation = "Precio de proyecto (manual)"
-> ServiceCommands.request_service(...):
   order.total_amount = 595000.00
   pricing_source_snapshot=MANUAL_PROJECT, pricing_mode_snapshot=None,
   unit_price_snapshot=None, project_price_snapshot=500000.00,
   duration_snapshot=None
```

### MANUAL_GENERAL (unit_price=$220.000)

```
ServicePricingCommands.set_manual_pricing(v, MANUAL_GENERAL, unit_price=220000)
-> ServiceSelector.get_variant_quotation(v):
   labor_cost=220000.00, iva_amount=41800.00, total_price=261800.00
   breakdown.labor_calculation = "Precio general (manual)"
-> ServiceCommands.request_service(...):
   order.total_amount = 261800.00
   pricing_source_snapshot=MANUAL_GENERAL, pricing_mode_snapshot=None,
   unit_price_snapshot=220000.00, project_price_snapshot=None,
   duration_snapshot=None
```

Ambos confirman FASE 12 (misma forma de contrato de cotizacion que
`AUTOMATIC`: `labor_cost`/`material_cost`/`total_price`/`breakdown` siempre
presentes) y FASE 2 (snapshot correcto segun el modo -- solo se llena
`project_price_snapshot` en `MANUAL_PROJECT`, solo `unit_price_snapshot` en
`MANUAL_GENERAL`/`MANUAL_HOURLY`, ninguno de los dos en `AUTOMATIC`).

## Limpieza

Las 2 ordenes sinteticas creadas para esta certificacion se eliminaron
(`ServiceOperation` primero por `PROTECT`, luego `Order`) y la variante de
prueba (`Servicio Fijo Prueba`, variante default) se devolvio a su estado
original (`AUTOMATIC`/`FIXED`/`$150.000`) via el mismo comando real. Las
entradas de `ServicePriceHistory` generadas por los cambios de
`pricing_source` durante la prueba se dejaron intactas -- son auditoria
legitima, mismo criterio que el resto de la sesion (no se borra historial de
auditoria real, solo datos sinteticos de orden/operacion).

## Pendiente (no certificado en este incremento)

- Checkout real end-to-end con Wompi para `MANUAL_PROJECT`/`MANUAL_GENERAL`
  (requiere aprobacion explicita del usuario por ser un cargo real -- fuera
  de alcance de una verificacion automatica).
- FASE 17 (UI dedicada de tarifa x horas en el panel operativo) y el
  disparo automatico de `confirm_price()`/`lock_price()` -- ver
  `MANUAL_PRICING_FASE16_19_ORDER_PRICE_OVERRIDE.md`, seccion "Explicitamente
  NO hecho en esta fase".
