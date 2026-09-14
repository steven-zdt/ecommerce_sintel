# Operations Resource Map (FASE R8)

Auditoria cross-domain 2026-08-14. `operations/` NO es un simple proveedor pasivo
de recursos compartidos (como asumia el prompt de auditoria en su seccion 2) --
tiene su propio dominio operativo activo, con FSM y comandos de asignacion
propios, que coexiste con los de `technical_services` y `renting` sin
coordinacion. Ver `CROSS_DOMAIN_ASSIGNMENT_AUDIT_FINAL.md` para el analisis
completo del hallazgo critico derivado de esto.

## Modelos owned por `operations/`

| Modelo | Proposito |
|---|---|
| `DispatcherProfile` | Recurso: despachador/transportador (driver, logistics, field_ops). `vehicle_plate`/`vehicle_type` como strings (no hay modelo `Vehicle`). `is_available`/`is_active` booleanos. |
| `OperationTicket` | Ticket generico de cumplimiento logistico: uno por `orders.Order`/`renting.RentalRequest` pagado (creado automaticamente, sin excepcion, al confirmar pago). FK opcional a `technical_services.ServiceOperation`/`renting.RentalOperation` ("satelite"), poblado solo por un backfill manual, sin sincronizacion continua. |
| `OperationAssignment` | Asignacion generica de un `User` a un `OperationTicket` en un rol (TECHNICIAN/DISPATCHER/TRANSPORTER/CONTRACTOR). |
| `TrackingEvent` | Timeline del ticket (creado, docs aprobados, asignado, programado, en camino...). |
| `OperationDocument` | Documentos requeridos por ticket, con flujo aprobar/rechazar. |
| `OperationReview` | Calificacion del cliente post-completado. |

## DispatcherProfile — campos exactos

```python
user            = OneToOneField(AUTH_USER_MODEL, related_name='dispatcher_profile')
dispatcher_type = CharField(choices=[DRIVER, LOGISTICS, FIELD_OPS])
vehicle_plate   = CharField(max_length=20, blank=True)
vehicle_type    = CharField(max_length=50, blank=True)
coverage_cities = JSONField(default=list)
is_available    = BooleanField(default=True, db_index=True)
is_active       = BooleanField(default=True, db_index=True)
```

No existe modelo `Vehicle` en ningun app del backend -- confirmado por busqueda
global `class Vehicle`. "Vehiculo" es siempre texto libre
(`DispatcherProfile.vehicle_plate`/`vehicle_type`, `RentalOperation.assigned_vehicle`).

## FSM compartida: `operations/services/fsm.py::transition_operation()`

Utilidad generica reutilizable (row-lock + validacion de adyacencia +
`update_fields` dinamico) -- **no tiene conocimiento de dominio**, no crea
eventos/notificaciones/side-effects. Cada dominio (`technical_services.
ServiceOperationCommands.transition()`, `renting.RentalOperationCommands.
transition()`) la llama primero y despues hace su propio trabajo de dominio en
su propio `@transaction.atomic`. Clasificacion: **infraestructura compartida
legitima**, no un leak de un dominio a otro.

## Consumidores de `operations.models` (por app)

| App | Que usa | R/W | Por que |
|---|---|---|---|
| `renting/services/operations.py` | `DispatcherProfile` (objeto pasado, no importado directo) | R+W (parcial, ver abajo) | `assign_dispatcher()` lee `is_active`/`is_available`/`vehicle_plate` como precondicion+default; escribe `RentalOperation.assigned_dispatcher`/`assigned_vehicle`. **No** marca `DispatcherProfile.is_available=False` -- gap independiente, ver hallazgo. |
| `renting/api/operation_serializers.py` | `DispatcherProfile` | R | Dropdown de seleccion de despachador. |
| `renting/services/commands.py` | `operations.services.commands.OperationCommands.ensure_ticket_for_rental()` | W (indirecto) | Crea el `OperationTicket` al confirmar pago de renta. |
| `technical_services/services/operations.py` | `operations.services.fsm.transition_operation` | -- | FSM compartida (ver arriba). |
| `orders/services/fulfillment/assignment.py` | `DispatcherProfile` | R+W | `assign_dispatcher()` (envios/Shipment) reutiliza el mismo pool -- SI marca `is_available=False`. |
| `payment/shared/commands.py`, `payment/cod/services/commands.py` | `OperationCommands.ensure_tickets_for_order()`/`ensure_ticket_for_rental()` | W | Crea `OperationTicket` en TODA confirmacion de pago, sin excepcion ni gate por tipo de orden. |
| `dashboard/api/urls.py` | `operations.api.views.AdminOperationViewSet`/`AdminDispatcherViewSet` | R+W (proxied) | Monta directamente las vistas de `operations` bajo el router de dashboard -- no reimplementa logica. |
| `support/services/customer360.py` | `DispatcherProfile` | R | Cuenta `dispatchers_active` para el panel Customer 360. |

## Escritores reales de `DispatcherProfile.is_available` (confirmado por codigo)

| Escritor | Ruta | Estado |
|---|---|---|
| `orders/services/fulfillment/assignment.py::assign_dispatcher()` | Shipment (envios de Orders) | Escribe `is_available=False` |
| `operations/services/commands.py::OperationCommands.assign_resource()` (rol DISPATCHER/TRANSPORTER) | `/panel/operaciones/{uuid}/assign/` | Escribe `is_available=False` |
| `renting/services/operations.py::RentalOperationCommands.assign_dispatcher()` | `/panel/renta` (RentalOperationBoard.vue) | **NO escribe `is_available`** -- lee la bandera como precondicion pero nunca la actualiza tras asignar |

## Escritores reales de `TechnicianProfile.is_available` (confirmado por codigo)

| Escritor | Ruta | Estado |
|---|---|---|
| `technical_services/services/operations.py::ServiceOperationCommands._set_technician_availability()` (agregado FASE 2-4 de la migracion de esta sesion) | `/panel/servicios`, `ServiceOperationBoard.vue`, `orders/service-orders/.../assign-technician` (delegado) | Unico writer *dentro del dominio Services* -- consolidado esta sesion |
| `operations/services/commands.py::OperationCommands.assign_resource()` (rol TECHNICIAN) | `/panel/operaciones/{uuid}/assign\|auto-assign/` | Escribe `is_available=False` **de forma completamente independiente**, sin tocar `ServiceOperation.technician`, sin evento, sin notificacion |

Ver `CROSS_DOMAIN_ASSIGNMENT_AUDIT_FINAL.md` seccion "Hallazgo Critico" para el
analisis de impacto de esta tabla.
