# Domain Source of Truth Matrix (FASE R19)

Auditoria cross-domain 2026-08-14. Declaracion formal de autoridad por dominio,
basada en evidencia de codigo.

## ORDERS

- **`Order`** — Owner: `orders`. Solicitud comercial raiz.
- **`OrderServiceDetail`** — Owner: `orders` (el modelo vive en `technical_services`
  por razones historicas, pero su ciclo de vida comercial -- creacion, snapshot de
  precio/direccion -- lo gobierna `orders` via `ServiceCommands.request_service()`).
  Su campo `.technician` es **LEGACY/COMPATIBILITY**, nunca autoridad — ver Services.

## SERVICES (technical_services)

- **`ServiceOperation.technician`** — **SOURCE OF TRUTH** para "que tecnico esta
  asignado a un servicio". Unico escritor real: `ServiceOperationCommands`
  (`technical_services/services/operations.py`). Consolidado en FASE 0-9 de la
  migracion de esta sesion (2026-08-14) — Django Admin nativo bloqueado, endpoints
  legacy de Orders delegan en vez de decidir.
- **Excepcion parcial no resuelta por esa migracion**: `TechnicianProfile.is_available`
  (bandera compartida con `accounts`) tiene un SEGUNDO escritor independiente fuera
  de Services — ver "Hallazgo Critico" en `CROSS_DOMAIN_ASSIGNMENT_AUDIT_FINAL.md`.

## RENTING

- **`RentalOperation.assigned_dispatcher`** — **SOURCE OF TRUTH** para "que
  despachador esta asignado a una renta". Unico escritor: `RentalOperationCommands.
  assign_dispatcher()` (`renting/services/operations.py`). Confirmado sin
  referencias a `OrderServiceDetail`/`ServiceOperation`/`technical_services` en
  todo el directorio `renting/` (0 hits, 2 agentes independientes).
- **`RentalOperation.assigned_vehicle`** — **SOURCE OF TRUTH** para "que vehiculo
  esta asignado". Campo de texto libre (no hay modelo `Vehicle`), poblado por el
  mismo comando, con default desde `DispatcherProfile.vehicle_plate`.
- **Gap independiente (no es cruce de dominio, es un bug propio de Renting)**:
  `assign_dispatcher()` nunca marca `DispatcherProfile.is_available=False` tras
  asignar — a diferencia de `orders.Shipment` y de `operations.OperationCommands`,
  que si lo hacen. No es parte del alcance de esta auditoria arreglarlo (no viola
  ninguna regla de las 26 prohibiciones del prompt), pero queda documentado.

## OPERATIONS

- **`DispatcherProfile`** — Owner exclusivo: `operations`. Recurso compartido,
  consumido (solo lectura de sus campos + escritura de `is_available`) por
  `renting` (parcial, ver gap arriba), `orders` (Shipment) y `operations` mismo
  (via `OperationCommands`).
- **`OperationTicket`/`OperationAssignment`/`TrackingEvent`/`OperationDocument`/
  `OperationReview`** — Owner exclusivo: `operations`. Sistema de cumplimiento
  logistico generico, creado automaticamente para toda orden/renta pagada. **NO
  es un simple proveedor de recursos pasivo** — tiene su propio FSM
  (`OperationTicket.status`) y sus propios comandos de asignacion
  (`OperationCommands.assign_resource()`/`auto_assign()`), reachable desde
  `/panel/operaciones` (`OperationDetail.vue`), que operan en paralelo — sin
  coordinacion — a los sistemas de `technical_services` y `renting`.
- **FSM compartida (`operations/services/fsm.py::transition_operation`)** —
  infraestructura neutral reutilizada por `ServiceOperationCommands.transition()`
  y `RentalOperationCommands.transition()`. No tiene logica de dominio propia, no
  es una fuente de verdad, es un helper.

## Regla formal (actualizada tras esta auditoria)

> `ServiceOperation.technician` y `RentalOperation.assigned_dispatcher`/
> `assigned_vehicle` son las unicas fuentes de verdad para "quien esta asignado"
> a un servicio tecnico o a una renta, respectivamente. `OrderServiceDetail.technician`
> es snapshot/legacy en Orders. **Sin embargo, las banderas de disponibilidad que
> alimentan esas decisiones (`TechnicianProfile.is_available`,
> `DispatcherProfile.is_available`) NO tienen esa misma garantia de autoridad
> unica hoy** — `operations.OperationCommands` las escribe de forma independiente
> a traves de `/panel/operaciones`, sin que `ServiceOperation`/`RentalOperation`
> se enteren. Esta declaracion de "single source of truth" para Services/Renting
> es correcta a nivel de *asignacion* (el campo `.technician`/`.assigned_dispatcher`
> en si), pero incompleta a nivel de *disponibilidad* (la bandera boolean que
> determina si alguien puede ser candidato). Ver hallazgo critico para el detalle
> completo y opciones de resolucion.
