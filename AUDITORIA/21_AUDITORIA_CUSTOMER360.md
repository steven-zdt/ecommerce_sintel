# 21 — Auditoría Enterprise: Customer 360 completo (Fase 7)

> **Fase 7 completada y cerrada 2026-08-01** — continúa el plan iniciado en
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[20](20_AUDITORIA_OMNICANALIDAD.md). El brief pedía que
> cada conversación conociera automáticamente: cliente, órdenes, cotizaciones, alquileres,
> servicios, tickets, facturas, pagos, historial, marketing, preferencias, interacciones, eventos.
> Fase 5 ya había encontrado (M1) que `addresses`/`notifications` se calculaban pero nunca se
> mostraban. Esta fase revisó el resto de la lista contra `Customer360Selector.build()` real.

## Hallazgo — cotizaciones ausentes por completo (resuelto el mismo día)

`Customer360Selector.build()` incluía `orders`/`rentals` pero **no `quotations`**, pese a que
`quotes.services.selectors.QuotationSelector.list_for_user(user)` ya existe con exactamente el
mismo patrón (`filter(user=user, is_deleted=False)`, mismo estilo de queryset). Un agente viendo
el Customer 360 de un cliente no tenía forma de saber si tenía cotizaciones activas — dato
directamente relevante para atender un chat de soporte.

**Resuelto:** agregado `quotations` al selector (reusando `QuotationSelector.list_for_user`, sin
inventar una query nueva), evento `_quotation_events()` al timeline unificado, y — a diferencia
de M1 (Fase 5), donde el campo se calculaba y nunca se mostraba — esta vez se creó el componente
`QuotationContextCard.vue` (mismo patrón que `OrderContextCard`/`RentalContextCard`) y se conectó
en `Customer360Panel.vue` con su propia sección "Cotizaciones recientes", para no repetir el
mismo error.

**Verificado end-to-end con datos reales, no solo en tests:** cotización real creada para un
cliente de dev con sala abierta → panel del dashboard admin mostró la sección "Cotizaciones
recientes" con badge de estado y total en pesos, y el timeline las intercaló correctamente por
fecha junto con pedidos/KYC — sin errores de consola. 1 test nuevo (`Customer360Selector`
directo, sin cobertura previa) + 22/22 de la suite de `support` pasando. Desplegado a producción.

## Ítems del brief NO implementados — pendientes de diseño, no de olvido

Verificados y confirmados ausentes, con razón concreta de por qué no se implementaron hoy:

- **Servicios (`technical_services`)**: no existe un selector `list_for_user` limpio para
  reservas de servicio (`ServiceBooking`) equivalente al de orders/rentals/quotes — el único
  método existente en `ServiceSelector` es de catálogo admin, no de reservas de un cliente.
  Requiere diseño (¿qué modelo exacto representa "el servicio que pidió este cliente"?) antes de
  poder replicar el mismo patrón con confianza.
- **Facturas/Pagos (`payment`)**: no existe un selector `list_for_user` de transacciones de pago;
  hoy `orders` ya expone `payment_method` (string) pero no los intentos/transacciones Wompi reales.
  Ambiguo qué contaría como "factura" en este sistema — necesita una decisión de producto, no una
  query directa.
- **Marketing (preferencias/interacciones/eventos)**: sin selector equivalente ni claridad de qué
  dato específico de `marketing` sería relevante mostrar en un panel de soporte. Más vago que los
  anteriores — no se fuerza un hallazgo especulativo sin evidencia concreta de qué se necesita.

Ninguno de estos bloquea nada — el patrón para replicarlos (cuando haya un `list_for_user` o
equivalente claro) es exactamente el que ya se usó hoy para `quotations`.

## Resumen ejecutivo

De la lista completa del brief, `orders`/`rentals`/`addresses`/`notifications`/`conversations` ya
estaban cubiertos (Fases 1 y 5), y `quotations` fue el único gap real y accionable — cerrado hoy
siguiendo el mismo patrón ya establecido, con componente de UI nuevo para no repetir el error de
M1 (campo calculado y nunca mostrado). `technical_services`, `payment` y `marketing` quedan fuera
por falta de un selector `list_for_user` reusable y, en el caso de payment/marketing, por
ambigüedad real de qué dato específico debería exponerse — mejor dejarlos pendientes de una
decisión concreta que forzar un hallazgo especulativo.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1 — Auditoría global de `support` | Hecha, 11/11 cerrados |
| 2 — Sincronización con AI Engine | Hecha, 7/8 cerrados |
| 3 — Sincronización documental cross-módulo | Hecha, 4/4 cerrados |
| 4 — Producción y resiliencia WS | Hecha, 3/12 cerrados |
| 5 — Communication Center y canales | Hecha, M2 cerrado |
| 6 — Omnicanalidad | Hecha, confirma Fase 5 |
| 7 — Customer 360 completo | **Hecha (este documento) — cotizaciones agregadas y verificadas en vivo** |
| 8-16 | Pendientes |
