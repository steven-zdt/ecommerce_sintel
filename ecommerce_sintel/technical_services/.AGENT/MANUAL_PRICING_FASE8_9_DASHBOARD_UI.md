# FASE 8-9 -- Dashboard BFF + UI de Fuente de Precio

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Primera fase con UI real --
un admin puede finalmente cambiar `pricing_source` desde `/panel/servicios`.

## FASE 8 -- Dashboard BFF

`POST /api/v1/dashboard/service-variants/{uuid}/set-pricing/` (nueva accion en
`AdminServiceVariantViewSet`, `dashboard/api/views.py`) -- unica via HTTP real
para cambiar `pricing_source`:

```
Vue -> POST .../set-pricing/ -> SetVariantPricingInputSerializer
    -> ServiceAdminOrchestrator.set_variant_pricing()
    -> ServicePricingCommands.set_manual_pricing()  [FASE 7]
```

`ValidationError` del modelo (combinacion invalida) se atrapa explicitamente y
se traduce a 400 -- confirmado que un `ValueError`/`ValidationError` sin
manejar NO se filtra como 500 al cliente.

`ServiceVariantSerializer` (output) gano `pricing_source`, `manual_unit_price`,
`manual_project_price`, `is_manual_pricing` -- **`read_only_fields`** a
proposito: el PATCH generico de variante (`ServiceVariantInputSerializer`,
usado por `updateVariant()` para SKU/complejidad/etc.) no puede tocar estos
campos, solo la accion dedicada. Verificado con test real: un PATCH intentando
`pricing_source: MANUAL_GENERAL` se ignora silenciosamente, la variante sigue
`AUTOMATIC`.

## FASE 9 -- UI

`frontend/src/modules/technical_services/service-form/PricingSourceCard.vue`
(nuevo) -- montado en `CostosTab.vue` arriba de `CostCalculationPanel.vue`
(existente, sin tocar): 4 radios (Automatico/Proyecto/General/Horas), campo
dinamico segun el modo, motivo opcional, boton "Guardar precio" (deshabilitado
si no hay cambios pendientes).

**Decision explicita:** no se construye una vista previa calculada en el
cliente -- violaria "frontend no calcula reglas comerciales" (FASE 13 del
plan). Al guardar, `CostosTab.vue` fuerza un `:key` nuevo en
`CostCalculationPanel`, que vuelve a pedir `GET quotation/` real al backend --
el mismo componente ya existente sirve para AUTOMATIC y MANUAL_* sin
modificarse, gracias a que FASE 3/4 ya alinearon el contrato de salida.

`serviceUuid` se propaga `ServiceForm.vue -> CostosTab.vue -> PricingSourceCard`
(prop nueva en `CostosTab.vue`, antes no la tenia -- inconsistencia real con
`VariantsTab.vue`/`ImagesTab.vue`, que si la reciben, corregida de paso).

`VariantsTab.vue` gana un badge "Manual por hora/general/proyecto" en la lista
de variantes cuando `v.is_manual_pricing` (FASE 29 del plan, indicador rapido
sin entrar al tab de Costos).

## Verificacion real (navegador, no solo unit tests)

Corrido contra el dev stack real (`docker restart ecommerce_sintel_frontend`
fue necesario -- el bind-mount de Windows no dispara HMR de Vite de forma
confiable, hallazgo operativo, no un bug de codigo):

1. Login admin real, `/panel/servicios` -> Editar "Servicio Fijo Prueba" (2
   variantes) -> tab Costos.
2. `PricingSourceCard` renderiza correctamente: radios, badge "Automatico",
   `CostCalculationPanel` muestra el desglose FIXED real ($150.000 base, IVA
   19% = $28.500, total $178.500).
3. Cambio a MANUAL_HOURLY + tarifa $85.000 + Guardar -> toast "Precio
   actualizado" -> badge cambia a "Manual" -> `CostCalculationPanel` se
   refresca solo y muestra **el calculo manual real del backend**:
   `85000.00 x 1.00 = $85.000`, IVA `$16.150`, total `$101.150`.
4. Verificado en Postgres directamente: `pricing_source=MANUAL_HOURLY`,
   `manual_unit_price=85000.00`, `ServicePriceHistory` con
   `pricing_source_old=AUTOMATIC`, `pricing_source_new=MANUAL_HOURLY`,
   `changed_by` = el admin real que hizo el cambio.
5. Revertido a AUTOMATIC desde la misma UI -- confirma la transicion inversa
   tambien funciona, `CostCalculationPanel` vuelve a mostrar el calculo FIXED
   original sin residuos del estado manual.

**Bug real atrapado durante esta verificacion (harness de prueba, no producto):**
el primer intento de escribir en el input via JS selecciono el campo
equivocado (un `querySelector` ambiguo en mi propio script de verificacion, no
en el componente) -- el backend correctamente rechazo el guardado
(`ValidationError` -> 400 -> toast de error), confirmando que la validacion de
FASE 1/7 funciona tambien contra un payload real malformado desde el
navegador, no solo en tests unitarios.

## Tests

Backend: suite completo de `technical_services` **172/172 PASS** (168
preexistentes + 4 nuevos de FASE 8, incluye el test de `read_only_fields`).
Frontend: verificado manualmente en navegador real (arriba) -- sin suite de
tests de componentes Vue en este proyecto (no hay Vitest/Cypress configurado,
confirmado en la auditoria FASE 0 original de la sesion).

## Estado real del catalogo

El motor manual ahora es alcanzable end-to-end desde el panel real. El resto
del catalogo sigue 100% `AUTOMATIC` (solo la variante de prueba se toco, y se
revirtio). Pendiente: FASE 16-19 (indicador/edicion desde
`/panel/servicios/operaciones`, snapshot vs. confirmado, override
administrativo con motivo obligatorio), FASE 21 (paquetes), FASE 24-27
(historial visible en UI, tests de regresion cruzados con Wompi/checkout/
paquetes/agenda), FASE 31 (documentacion consolidada en
`ARQUITECTURA_COMPLETA_SERVICES.md`).
