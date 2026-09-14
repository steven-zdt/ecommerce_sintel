# FASE 1 -- Matriz de responsabilidades (Fachada Administrativa Unificada)

Regla de diseno vinculante para FASE 2 en adelante. Basada en el baseline
real verificado en `SERVICES_ADMIN_FACADE_BASELINE.md`. Ninguna fase
posterior puede escribir un modelo fuera de su OWNER declarado aqui.

| Entidad | Owner | Lectura (fachada) | Escritura (fachada) | Uso en la fachada |
|---|---|---|---|---|
| `Order` | `orders` | Si, via `ServiceAdminRequestSelector` | **No directo** -- la fachada nunca hace `Order.objects.update()`. Cambios de estado pasan por comandos existentes de `orders`/`technical_services`, nunca inline | Cabecera de la solicitud: tracking, fecha, metodo de pago, total |
| `OrderServiceDetail` | `technical_services` (vive fisicamente ahi, pero es snapshot del dominio `orders`) | Si | **No directo** desde la fachada -- se actualiza solo a traves de `ServiceCommands`/`ServiceAssignmentCommands` ya existentes | Datos comerciales: direccion, contacto, prioridad, snapshot de tarifa, tecnico LEGACY (solo lectura, ver H1) |
| `ServiceOperation` | `technical_services` | Si | **Si, pero solo via `ServiceOperationCommands` existente** (`plan`/`assign_technician`/`reschedule`/`cancel`/`notify_client`/`transition`/`close`/`report_incident`/`resolve_incident`) -- el Orchestrator de fachada (FASE 4) delega, nunca reimplementa la transicion | Estado operativo real, tecnico NUEVO (fuente de verdad, ver H1), fechas programadas, timeline tecnico |
| `ServiceOperationEvent` | `technical_services` | Si (fusionado con `OrderServiceTimeline` para el timeline unificado) | No -- se crea solo como efecto secundario de `ServiceOperationCommands`, nunca insertado manualmente por la fachada | Timeline unificado (seccion "TIMELINE" del detalle, FASE 8) |
| `OrderServiceTimeline` | `orders` (aunque el modelo fisicamente vive en `technical_services/models.py`, semanticamente es del dominio comercial) | Si (fusionado, ver arriba) | No directo -- solo via `ServiceTimelineCommands.add_timeline_event()` existente | Timeline unificado |
| `TechnicalService`/`ServiceVariant` | `technical_services` | Si | No (fuera de alcance de "solicitudes" -- ya tiene su propio CRUD maduro en `ServiceForm.vue`, auditado en sesiones previas) | Nombre del servicio/variante solicitada, precio |
| `ProfessionalAvailability` | `accounts` | Si (para mostrar conflictos/disponibilidad al asignar) | **No directo** -- solo via `ServiceOperationCommands.assign_technician`/`unassign_technician` (que internamente llaman `AvailabilityCommands.confirm_booking`/`release_booking` de `accounts`) | Panel de asignacion de tecnico (FASE 10) |
| `WorkingSchedule`/`WorkingException` | `technical_services` | Si (via `TechnicianAvailabilityEngine`, solo lectura calculada) | No -- la fachada NUNCA escribe disponibilidad directo, siempre via `assign_technician` | Candidatos de tecnico + conflictos en FASE 10 |
| `Technician` (User + `TechnicianProfile`) | `accounts`/`users` | Si | No | Selector de tecnico (reutiliza `available_technicians`/`ServiceOperationSelector.available_technicians`, no crea uno nuevo) |
| `ServiceBooking` | `technical_services` | Si (indirecto, via `OrderServiceDetail`) | No directo | Confirma que la solicitud tiene slot reservado |
| `NotificationTemplate`/dispatch | `notifications` | No (fire-and-forget) | Si, pero **solo invocando `NotificationCommands.dispatch_notification()`** con templates YA sembrados (`service_operation_*`, `service_status_updated`) -- la fachada nunca crea un template nuevo | Efecto secundario de approve/assign/schedule/cancel (FASE 17) |

## Regla de escritura -- una sola linea

**La fachada (`ServiceAdminRequestOrchestrator`, FASE 4) nunca hace
`Model.objects.create()/.update()/.save()` sobre ninguna de las entidades
de arriba.** Cada accion administrativa es una llamada de una linea a un
comando ya existente de `orders`, `technical_services` o `accounts`. Si en
algun punto de FASE 4-9 hiciera falta escribir un campo que ningun comando
existente cubre, eso es una senal de PARE (posible necesidad real de tocar
`orders`/`ServiceOperation`, fuera del alcance "solo fachada" de este plan)
y se reporta en el checkpoint de esa fase en vez de improvisar un `.save()`
directo.

## Resolucion explicita de H1/H2 reflejada en la matriz

- "Tecnico asignado" que la fachada **escribe** = siempre
  `ServiceOperation.technician` (via `ServiceOperationCommands`). El campo
  `OrderServiceDetail.technician` (legacy) se lee pero nunca se escribe
  desde la fachada nueva -- evita agrandar la divergencia de H1 en vez de
  fingir resolverla.
- No hay fila "estado de aprobacion" en la matriz porque no existe ese
  concepto en el backend (H2) -- el "estado de solicitud" visible en la
  fachada es directamente `ServiceOperation.status`, sin capa inventada
  encima.
