# FASE 16-19 -- Precio Comercial de Orden en /panel/servicios/operaciones

**Fecha:** 2026-08-13. Plan "Manual Pricing Engine". Distinto de FASE 0-9
(precio de CATALOGO, antes de la venta) -- esta fase es sobre el precio de una
**orden ya creada**, visible/editable desde el panel operativo.

## Decision de alcance confirmada con el usuario ANTES de escribir codigo

Pregunta explicita: ¿el override de precio debe tambien actualizar
`Order.total_amount` (lo que Wompi ya cobro o va a cobrar)? Respuesta: **no** --
el override queda como registro auditado, `Order.total_amount`/`OrderItem.price`
nunca se tocan. Un ajuste de cobro real (nota de credito, reembolso parcial) es
un proceso de negocio aparte, deliberadamente fuera de este plan -- evita tocar
el dominio de Payment/Wompi sin una decision de negocio explicita sobre
reembolsos parciales, pagos ya confirmados, etc.

## FASE 18 -- Estados de precio

`OrderServiceDetail.price_status` (nuevo, mig. 0036): `ESTIMATED` (default, al
crear la orden), `CONFIRMED` (admin reviso y confirma que el total actual es
correcto), `OVERRIDDEN` (admin cambio el total mostrado), `LOCKED` (terminal --
ningun comando de este dominio permite mas cambios). `confirmed_total`
(DecimalField, informativo -- el total que el admin confirmo/ajusto, **nunca**
reemplaza `Order.total_amount`).

## FASE 19 -- Override administrativo

`OrderPriceAdjustment` (modelo nuevo, append-only) -- `order_service_detail`,
`old_total`, `new_total`, `reason` (obligatorio a nivel de Command, no de
modelo -- ver docstring), `changed_by`. `old_total` es el `confirmed_total`
previo si ya existia, o `Order.total_amount` la primera vez -- una cadena de
overrides encadena correctamente (verificado con test:
`test_second_override_uses_previous_confirmed_total_as_old_total`).

`technical_services/services/commands.py::OrderPricingCommands`:
- `confirm_price(detail, changed_by)` -- `ESTIMATED/OVERRIDDEN -> CONFIRMED`,
  `confirmed_total = order.total_amount`. Lanza `ValueError` si `LOCKED`.
- `override_price(detail, new_total, reason, changed_by)` -- exige `reason` no
  vacio y `new_total >= 0`, crea el `OrderPriceAdjustment`, actualiza
  `confirmed_total`/`price_status=OVERRIDDEN`. Lanza `ValueError` si `LOCKED`.
- `lock_price(detail)` -- terminal, bloquea futuros cambios.

## API

`POST /api/v1/service-operations/{uuid}/confirm-price/` y `.../override-price/`
(`ServiceOperationViewSet`, mismo patron que el resto del FSM de operaciones --
`ValueError`/`ValidationError` -> 400, nunca 500). Body de `override-price/`:
`{"new_total": "220000.00", "reason": "..."}` (`reason` obligatorio tambien en
el serializer, doble capa igual que `discount_pct`).

`ServiceOperationOrderSummarySerializer.get_quotation()` (ya existia, exponia
`applied_rate_type`/`applied_rate_amount`) se amplio con
`pricing_source_snapshot`, `pricing_mode_snapshot`, `unit_price_snapshot`,
`project_price_snapshot` (FASE 2), `price_status`, `price_status_display`,
`confirmed_total` -- el bloque "PRECIO COMERCIAL" que pide FASE 16 ya viaja en
el payload existente de `GET /service-operations/{uuid}/`, sin endpoint nuevo
de lectura.

## Tests

`technical_services/tests_order_pricing.py` (nuevo, 13 tests) -- incluye
`test_override_price_never_touches_order_total_amount`, la prueba mas
importante del archivo, que confirma la decision de alcance a nivel de
codigo, no solo de conversacion. Suite completo de `technical_services`:
**187/187 PASS** (174 preexistentes + 13 nuevos), 0 regresiones.

## Actualizacion 2026-08-13 (mismo dia) -- UI en /panel/servicios/operaciones

Se construyo el bloque "PRECIO COMERCIAL" (`OperationPricingPanel.vue`, nuevo,
`frontend/src/components/customer/services/`), montado en
`ServiceOperationBoard.vue` justo despues de `OperationSummary`. Sigue el
mismo patron de comunicacion que el resto del panel (`TechnicianSelector`,
`ScheduleModal`): el hijo emite `confirm`/`override`, el padre ejecuta la
llamada real via su helper `execute()` (mismo toast/reload que
`cancelOperation`/`reportIncident`).

Muestra: fuente de pricing (`pricing_source_snapshot` traducido a label),
tarifa/precio-proyecto si aplica, total de la orden, total confirmado/ajustado
(si existe), badge de estado (`price_status_display`). Botones "Confirmar
precio" / "Editar precio" (oculto si `LOCKED`); "Editar precio" abre un form
inline con nuevo total + motivo obligatorio (boton Guardar deshabilitado
hasta que ambos campos sean validos), llamando a `override-price/`.

Verificado end-to-end en navegador real (no solo unit tests): login admin,
`Gestionar` sobre una operacion real -> "Confirmar precio" -> toast +
badge CONFIRMADO -> "Editar precio" (nuevo total $250.000, motivo real) ->
"Guardar" -> toast + badge "Modificado por administrador" ("OVERRIDDEN").
Confirmado tambien contra Postgres directamente:
`Order.total_amount` siguio en `214200.00` (sin tocar), `confirmed_total`
paso a `250000.00`, se creo el `OrderPriceAdjustment` con
`old_total=214200.00`/`new_total=250000.00`/`reason`/`changed_by` correctos.

Bug real encontrado y corregido durante esta verificacion: `emit` se
declaraba dos veces en `OperationPricingPanel.vue` (`const props = ...` +
`defineEmits` arriba, y otro `const emit = defineEmits(...)` mas abajo antes
de `submitOverride`), lo que rompia la compilacion de Vite
(`Identifier 'emit' has already been declared`) -- Vite lo reportaba como
`Failed to fetch dynamically imported module` en el navegador. Corregido
dejando una sola declaracion (`const emit = defineEmits(...)` junto a
`defineProps`, reusada en `submitOverride`).

## Explicitamente NO hecho en esta fase (fuera del alcance decidido)

- FASE 17 (asignacion manual de costo POR HORAS en la operacion, con
  recalculo antes de confirmar) -- el mecanismo generico (`override_price`
  con cualquier `new_total`) ya lo cubre funcionalmente sin UI dedicada de
  "tarifa x horas" en el panel operativo.
- Ningun flujo automatico llama `confirm_price()`/`lock_price()` todavia (ej.
  al pagar, al cerrar la operacion) -- son comandos disponibles, no
  disparados por ningun trigger del sistema en este incremento.
