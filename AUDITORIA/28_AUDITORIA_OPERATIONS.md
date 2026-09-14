# 28 — Auditoría Enterprise: Operations (Fase 14)

> **Fase 14 completada y cerrada 2026-08-03** — continúa el plan de
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[27](27_AUDITORIA_MARKETING.md). Tras el `ImportError`
> P0 encontrado en la [Fase 13](27_AUDITORIA_MARKETING.md) (invisible a la lectura estática de
> código), esta fase verificó explícitamente — importando en vivo cada módulo clave de
> `operations/` dentro del contenedor — que no existiera el mismo tipo de bug oculto. **Resultado:
> todos los imports de `operations/` funcionan correctamente**, incluyendo el management command
> `backfill_operation_satellite_links`. `operations/` no tiene `tasks.py` propio hasta este fix —
> sus tareas periódicas previas se registraban vía data-migrations con `PeriodicTask`, igual que
> `payment`/`renting`/`orders`/`support`. Alcance aprobado por el usuario: los 2 P2. El P4
> cosmético (doc/comentarios referencian una clase `OperationTicketSelector` que nunca existió,
> el nombre real es `OperationSelector`) queda documentado sin corregir.

## P2 — Customer 360 no incluía órdenes de operación pese a existir un selector limpio

`support/services/customer360.py` agregaba orders/rentals/quotations/kyc/conversaciones, pero
nunca `OperationTicket` — pese a que `operations/services/selectors.py::OperationSelector.
list_for_user(user)` ya existe con el mismo patrón exacto que `QuotationSelector.list_for_user`
(integrado en la [Fase 7](21_AUDITORIA_CUSTOMER360.md)). El modelo `OperationTicket` ya trae
justo lo que necesitaría un agente atendiendo "¿dónde está mi técnico?": técnico asignado (vía
`assignments`), cita programada (`scheduled_date`/`scheduled_time_start`), y
`get_effective_status()` para el estado real (deriva del satélite `ServiceOperation`/
`RentalOperation`/`Shipment` cuando existe).

**Resuelto:** `support/services/customer360.py` agrega `_operation_events()`/
`_operation_technician()` (mismo patrón que `_quotation_events()` de Fase 7) y una nueva clave
`'operations'` en el dict devuelto, con `ticket_number`, `operation_type`, `status` (vía
`get_effective_status()`), `priority`, `scheduled_date` y `technician` (email del asignado
`ROLE_TECHNICIAN`/`STATUS_ACTIVE`). Se agregó también al timeline unificado.

**Frontend:** `OperationContextCard.vue` (nuevo, mismo patrón que `QuotationContextCard.vue`) y
sección "Ordenes de operación" en `Customer360Panel.vue`, reusando los enums
`operation-statuses`/`operation-types` ya expuestos por `core/api/views.py::enums()` — sin
necesidad de agregar enums nuevos.

## P2 — Ausencia total de monitoreo de estancamiento para OperationTicket

Confirmado por grep de `PeriodicTask` en todo el repo: `orders`, `payment` (x2), `renting` (x2) y
`support` (Fase 9) tienen tareas periódicas seedeadas vía migración para detectar
estancamiento/expiración. `operations/` no tenía ninguna — un ticket podía quedar
indefinidamente en `ASSIGNED`/`SCHEDULED`/`EN_ROUTE` (técnico que nunca se presenta) sin ninguna
alerta automática. A diferencia de la Fase 9 (donde el mecanismo ya existía con una brecha
puntual), aquí era ausencia completa de la funcionalidad equivalente.

**Resuelto:** `operations/tasks.py` (archivo nuevo) con `notify_stale_operation_tickets` —
`OperationTicket` en `ASSIGNED`/`SCHEDULED`/`EN_ROUTE` sin avance (`updated_at`) en 48h (umbral
más largo que las 2h de soporte, por tratarse de operaciones físicas de campo, no un chat) se
notifica al asignado `ACTIVE` del ticket, deduplicado por `NotificationLog` vía
`NotificationCommands.dispatch_notification_once` — mismo patrón exacto que
`support.tasks.notify_unattended_escalated_tickets` (Fase 1). Plantilla nueva
`operacion_estancada` (`operations/migrations/0006_seed_stale_ticket_template.py`) y
`PeriodicTask` diario a las 8am (`0007_seed_notify_stale_tickets_periodic_task.py`), mismo
patrón de migración usado por `support/migrations/0007_...`.

## Pendiente (P4, no corregido en esta fase)

- `operations/models.py:170`, `operations/api/serializers.py:45` y la doc de arquitectura
  referencian una clase `OperationTicketSelector` con un método `.list_all(status=...)` que
  nunca existió — el nombre real es `OperationSelector`, sin método `list_all` (el más parecido
  es `list_for_board`). Cosmético, pero puede inducir a un futuro refactor a "proteger" un
  método que no existe.

## Verificación

- Import real (no solo lectura de código) de `operations.models`, `operations.services.
  {commands,selectors,fsm,config}`, `operations.consumers`, `operations.routing`,
  `operations.admin`, `operations.api.{views,serializers,urls}` y el management command
  `backfill_operation_satellite_links` — **todos limpios**.
- 4 tests nuevos para `notify_stale_operation_tickets` (notifica al asignado tras 48h; no
  notifica dentro del umbral; no duplica notificación en corridas repetidas; no notifica
  tickets ya completados). `operations/tests.py`: **10/10**.
- 1 test nuevo para Customer360 (`test_customer360_incluye_ordenes_de_operacion_del_cliente`,
  aísla por usuario, verifica técnico asignado en el payload).
- `manage.py check`: limpio.
- Build de frontend (`npx vite build`) exitoso con el componente nuevo
  `OperationContextCard.vue`.

## Resumen ejecutivo

La verificación activa de imports (adoptada tras el hallazgo P0 de la Fase 13) confirmó que
`operations/` está sano en ese sentido — el módulo simplemente carecía de dos piezas de
integración con el objetivo real de esta auditoría (que soporte se convierta en un centro de
servicio omnicanal): visibilidad de órdenes de operación en el contexto 360 del cliente, y una
alerta cuando una operación física se estanca. Ambos se cerraron reusando exactamente los
patrones ya validados en fases anteriores (selector existente + helper de eventos del timeline;
`dispatch_notification_once` + `PeriodicTask` vía migración), sin arquitectura nueva.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1-10 | Hechas — ver documentos 15-25 |
| 12 | Hecha — ver [26](26_AUDITORIA_CORE.md) (sin hallazgos) |
| 13 | Hecha — ver [27](27_AUDITORIA_MARKETING.md) (ImportError P0 + P1 + P2) |
| 14 — Operations | **Hecha (este documento) — 2 P2 cerrados, 1 P4 documentado** |
| 15 | Hecha — ver [29](29_AUDITORIA_OBSERVABILIDAD.md) |
| 16 | Fuera de alcance de esta sesión |
