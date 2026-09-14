# Arquitectura Completa - Modulo Operations

> Ultima actualizacion: 2026-06-27

## Responsabilidad

`operations` orquesta la ejecucion posterior al pago. `orders` y `renting` conservan
la propiedad de sus datos comerciales; este modulo solo mantiene tickets,
asignaciones, documentos y trazabilidad operativa.

## Modelos

- `OperationTicket`: fuente exclusiva `source_order` o `source_rental_request`, tipo,
  estado, prioridad, programacion y snapshot de ubicacion.
  **[2026-07-12, CORE v4 Fase 5 Opcion B Paso 1]** gano 3 `OneToOneField` nullable de
  trazabilidad: `service_operation` (-> `technical_services.ServiceOperation`),
  `rental_operation` (-> `renting.RentalOperation`), `shipment` (-> `orders.Shipment`).
  Poblados via `python manage.py backfill_operation_satellite_links` (idempotente, tiene
  `--dry-run`). **No siempre estan poblados**: el ticket se crea ANTES que el satelite en
  tickets en etapa temprana (`DOCS_PENDING`/`READY_TO_ASSIGN`) -- el satelite recien se crea al
  confirmar pago/aprobar. Ver
  `Documentacion/Arquitectura_general/MIGRACION_CORE_V4_DOMINIOS_FASE5_PROPUESTA_OPERACIONES.md`.
  **[2026-07-12, Paso 2]** `get_effective_status()` implementado (metodo aditivo -- `status`
  real de BD NO se toco, convertirlo en `@property` habria roto
  `OperationSelector`'s `.filter(status=...)`). Estados terminales propios
  (`CANCELLED`/`COMPLETED`) tienen prioridad sobre el satelite -- encontrado con un caso REAL
  de divergencia en este ambiente (`OP-2026-7C215EE1`: ticket `CANCELLED`, `ServiceOperation`
  vinculado seguia en `READY_FOR_PLANNING`). Expuesto como campo aditivo `effective_status` en
  `OperationTicketListSerializer`/`OperationTicketDetailSerializer`; el frontend sigue leyendo
  `status` hasta Fase 6.
- `OperationAssignment`: personal asignado con roles `TECHNICIAN`, `DISPATCHER`,
  `TRANSPORTER` o `CONTRACTOR`.
- `TrackingEvent`: historial visible para el cliente.
- `DispatcherProfile`: disponibilidad, tipo operativo, vehiculo y ciudades de cobertura.
- `OperationDocument` y `OperationReview`: documentos y cierre de experiencia.

Una orden puede producir un ticket por cada tipo de item. La restriccion
`operationticket_unique_order_type` impide duplicados por orden y tipo.

## Integracion de pagos

`payment.shared.confirm_order_payment()` es la SSoT de confirmacion online. Despues
de marcar la orden como pagada y descontar inventario invoca
`OperationCommands.ensure_tickets_for_order(order)`. COD usa el mismo command.
`RentalRequestCommands` usa `ensure_ticket_for_rental()`.

Ambos commands son idempotentes. Una orden mixta puede generar:

- producto -> `SHOP_DELIVERY`
- equipo -> `RENTAL`
- servicio -> `SERVICE`

## Estados

Flujo principal:

`CREATED/DOCS_PENDING -> READY_TO_ASSIGN -> ASSIGNED -> SCHEDULED -> EN_ROUTE -> IN_PROGRESS -> COMPLETED`

`CANCELLED` es terminal. Las transiciones se validan en `services/config.py`.
Asignar bloquea la disponibilidad del recurso; completar o cancelar libera sus
asignaciones y restablece disponibilidad cuando no conserva otras tareas activas.

## APIs

- Cliente: `/api/v1/operations/my/`
- Personal: `/api/v1/operations/tasks/`
- Admin BFF: `/api/v1/dashboard/operations/`
- Personal disponible: `/api/v1/dashboard/operations/{uuid}/available-staff/`
- Despachadores: `/api/v1/dashboard/dispatchers/`
- WebSocket: `/ws/operations/{ticket_uuid}/?token={jwt}`

El cliente solo consulta tickets propios. El personal solo consulta tickets donde
tiene una asignacion y solo puede avanzar a `EN_ROUTE`, `IN_PROGRESS` y `COMPLETED`.
El BFF administrativo requiere `users.api.permissions.IsAdminUser`.

## Frontend

- `/panel/operaciones`: tabla filtrable y paginada.
- `/panel/operaciones/:uuid`: asignacion, programacion, documentos y estados.
- `/mi-cuenta/operaciones`: tracking del cliente.
- `/mis-tareas`: portal mobile-first del personal operativo.

Todas las llamadas usan `useApi()` y las notificaciones usan `useToast()`.

## Migraciones y pruebas

- `0001_initial`: modelos iniciales.
- `0002_seed_notification_templates`: plantillas multicanal.
- `0003_alter_dispatcherprofile_created_at_and_more`: tickets multiples por orden,
  roles operativos e indices heredados de `SintelBaseModel`.
- `operations/tests.py`: ordenes mixtas, idempotencia, disponibilidad y permisos.
