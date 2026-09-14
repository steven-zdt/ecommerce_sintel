# Cross-Domain Assignment Matrix (FASE R10)

Auditoria 2026-08-14. Basada en evidencia de codigo real (3 agentes de
exploracion + verificacion dirigida), no en supuestos.

| Concepto | Orders | Services (technical_services) | Renting | Operations |
|---|---|---|---|---|
| Solicitud comercial | **Owner** (`Order`, `OrderServiceDetail`) | consume (`OrderServiceDetail` es su snapshot) | consume (via `Order` generico) | no |
| Technician (asignacion real) | referencia legacy (`OrderServiceDetail.technician`, snapshot, NO write owner) | **Owner** (`ServiceOperation.technician`, `ServiceOperationCommands`) | no | **escritor paralelo NO coordinado** (`OperationCommands.assign_resource(role=TECHNICIAN)`, ver hallazgo) |
| Dispatcher (asignacion real) | no | no | **Owner** (`RentalOperation.assigned_dispatcher`, `RentalOperationCommands`) | recurso (`DispatcherProfile`) + **escritor paralelo NO coordinado** de su bandera `is_available` |
| Vehicle | no | no | **Owner** (`RentalOperation.assigned_vehicle`, string libre) | recurso (`DispatcherProfile.vehicle_plate/type`, string libre) -- no existe modelo `Vehicle` en ningun app |
| `ServiceOperation` (FSM tecnico) | no | **Owner** | no | FK opcional de solo-lectura desde `OperationTicket.service_operation` (poblada por backfill manual, sin sync continuo) |
| `RentalOperation` (FSM logistico) | no | no | **Owner** | FK opcional de solo-lectura desde `OperationTicket.rental_operation` (misma situacion) |
| `OrderServiceDetail` | **Owner** | snapshot/legacy (lee, no escribe desde ningun sistema nuevo) | sin referencia (confirmado, 0 hits) | sin referencia (confirmado, 0 hits) |
| `OperationTicket` (ticket generico de cumplimiento) | dispara su creacion (via pago) | dispara su creacion (via pago) | dispara su creacion (via pago) | **Owner** -- creado automaticamente para TODA orden/renta pagada, sin excepcion |
| `TechnicianProfile.is_available` (bandera compartida) | no | escritor consolidado (FASE 2-4 de esta sesion) | no | **segundo escritor independiente** (`OperationCommands`, via `/panel/operaciones`) |
| `DispatcherProfile.is_available` (bandera compartida) | escritor (`Shipment`/envios, via `orders/services/fulfillment/assignment.py`) | no | **NO escribe** (gap: lee la bandera pero nunca la actualiza tras asignar) | escritor (`OperationCommands`, via `/panel/operaciones`) |
| `DispatcherProfile` (recurso) | consumidor (pool compartido para Shipment) | no | consumidor (pool compartido para `RentalOperation`) | **Owner** |
| Paneles admin | `/panel/pedidos` (envios/Shipment) | `/panel/servicios`, `/panel/servicios/operaciones`, `/panel/servicios/solicitudes`, `TechnicianAssignmentBoard.vue` (legacy) | `/panel/renta`, `RentalOperationBoard.vue` | `/panel/operaciones` (`OperationDetail.vue`) |
| FSM helper compartido | no usa | usa (`operations.services.fsm.transition_operation`) | usa (mismo helper) | provee el helper (infraestructura neutral, sin logica de dominio) |

## Notas de clasificacion (evidencia, no supuesto)

- **`OrderServiceDetail.technician` -> Renting/Operations**: 0 referencias
  encontradas en ninguna de las 2 apps (busqueda de directorio completo, 2
  agentes independientes). No hay cruce indebido en este eje -- el que la
  migracion de esta sesion (FASE 0-9) SI resolvio dentro de Services/Orders
  sigue intacto y no se filtra a Renting.
- **`ServiceOperation` <-> `RentalOperation`**: ninguna referencia cruzada
  directa entre estos 2 modelos. Cada uno vive exclusivamente en su dominio.
- **El cruce real no anticipado por el prompt de auditoria** esta en las 2
  filas marcadas "escritor paralelo NO coordinado" / "segundo escritor
  independiente": las banderas compartidas `TechnicianProfile.is_available` y
  `DispatcherProfile.is_available` tienen mas de un escritor activo y
  alcanzable desde produccion, a traves de un tercer sistema
  (`operations.OperationCommands`) que ninguno de los 2 prompts de migracion
  de esta sesion conocia. Ver `CROSS_DOMAIN_ASSIGNMENT_AUDIT_FINAL.md`.
