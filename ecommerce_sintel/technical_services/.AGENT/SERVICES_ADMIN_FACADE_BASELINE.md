# FASE 0 -- Baseline: Fachada Administrativa Unificada (Technical Services)

Auditoria pura (cero cambios de codigo) previa al plan de 30 fases "Fachada
Administrativa Unificada — Technical Services" (2026-08-14). Verificado
contra codigo real via 3 agentes de exploracion en paralelo + investigacion
directa del patron Orchestrator ya establecido en `dashboard/`.

## 0. Resumen ejecutivo -- 2 hallazgos que el prompt maestro no anticipaba

**H1. Dos sistemas de asignacion de tecnico paralelos y desincronizados.**
Existen HOY dos caminos completos e independientes para "asignar un
tecnico a una solicitud de servicio", cada uno con su propio panel admin
ya montado en `/panel/servicios`:

| | Sistema nuevo (FSM) | Sistema legacy |
|---|---|---|
| Owner | `technical_services.ServiceOperation` | `orders.OrderServiceDetail` |
| Comando | `ServiceOperationCommands.assign_technician` (`technical_services/services/operations.py:156`) | `ServiceAssignmentCommands.assign_technician` (`technical_services/services/commands.py:722+`) |
| Escribe | `ServiceOperation.technician`/`.availability_slot` + reserva real en `accounts.ProfessionalAvailability` | `OrderServiceDetail.technician` + togglea `TechnicianProfile.is_available` (sin tocar `ProfessionalAvailability`) |
| Panel admin | `ServiceOperationBoard.vue` (`/panel/servicios/operaciones`) | `TechnicianAssignmentBoard.vue` (`/panel/servicios/asignacion-tecnicos`) |
| Endpoint | `/api/v1/service-operations/{uuid}/assign-technician/` | `/api/v1/orders/service-orders/{uuid}/assign-technician/` |

Asignar por un board **no actualiza ni libera** el estado del otro sistema
-- pueden divergir en produccion hoy mismo. El prompt maestro (FASE 10)
asume "reutilizar infraestructura existente" como si fuera una sola pieza;
en realidad hay que decidir explicitamente cual es la fuente de verdad
para la fachada. Ver seccion 5 para la decision tomada.

**H2. No existe hoy un "paso de aprobacion" para solicitudes de servicio
tecnico**, a diferencia de Renting. En Renting, una `RentalRequest` nace en
`pending_validation` y requiere accion admin explicita (`aprobar`/`rechazar`,
`RentalRequestCommands`) antes de continuar. En Technical Services,
`ServiceCommands.request_service()` (`technical_services/services/commands.py:230-238`)
crea la `ServiceOperation` **automaticamente**, en el mismo momento de la
solicitud, en estado `READY_FOR_PLANNING` -- comentario explicito en el
codigo: "toda solicitud... entra de inmediato a Operaciones... sin esperar
a que el pago se confirme". No hay ningun estado equivalente a
`pending_validation` ni accion `aprobar`/`rechazar` en el backend de
servicios hoy. El diseno conceptual del prompt maestro (FASE 9/15,
"Solicitud recibida: [Aprobar][Rechazar]") no tiene backing real -- ver
seccion 7 para como se resuelve esto sin inventar un gate que no existe.

Ninguno de los dos hallazgos rompe una condicion de PARE del prompt
maestro (no rompe ownership, no crea modelo duplicado, no rompe orders/
ServiceOperation/customer/renting) -- son huecos de diseno que el prompt
asumia resueltos y no lo estan. Se documentan aqui para que FASE 1 (matriz
de responsabilidades) parta de la arquitectura real, no de la asumida.

## 1. Ownership -- confirmado en codigo

- **NO existe** ningun modelo/clase `ServiceRequest` en todo el backend
  (grep exhaustivo con limite de palabra, 0 resultados). El camino real es
  `Order -&gt; OrderServiceDetail -&gt; ServiceBooking -&gt; ServiceVariant -&gt;
  TechnicalService`, con el estado operativo terminal en `ServiceOperation`
  -- exactamente como documenta `technical_services/CLAUDE.md`.
- `orders.Order` es dueno de la solicitud comercial: `status` (CharField
  libre, NO es una FSM formal -- sin `TRANSITIONS` dict ni validacion de
  transicion a nivel modelo; mezcla valores de logistica de envios en
  MAYUSCULAS con valores de servicios en minusculas -- inconsistencia real,
  no cosmetica), `payment_method`, `total_amount`.
- `technical_services.OrderServiceDetail` (vive en `technical_services/models.py:325-378`
  pese a su nombre "Order...") es 1:1 con `Order`, guarda el snapshot
  comercial congelado (`applied_rate_type`/`applied_rate_amount`), tecnico
  asignado (sistema legacy), prioridad, y referencia desacoplada a
  `ProfessionalAvailability` via `booked_slot_id` (sin FK real).
- `technical_services.ServiceOperation` (`models.py:541-633`) es 1:1 con
  `Order` (**no** con `OrderServiceDetail`), dominio tecnico separado por
  diseno (comentario explicito en el modelo: "OrderServiceDetail sigue
  siendo solo el snapshot de la orden, nunca el centro operativo"). FSM
  real de 11 estados: `READY_FOR_PLANNING -&gt; PLANNED -&gt;
  TECHNICIAN_ASSIGNED -&gt; CUSTOMER_NOTIFIED -&gt; READY_TO_VISIT -&gt;
  ON_THE_WAY -&gt; ARRIVED -&gt; IN_PROGRESS -&gt; COMPLETED -&gt; CLOSED`, mas
  `CANCELLED` (terminal desde casi cualquier punto no cerrado).

## 2. Flujo real end-to-end (verificado, no asumido)

```
Customer -> ServiceRequestWizard.vue -> POST orders/service-orders/
  -> ServiceOrderViewSet.create() -> ServiceCommands.request_service()
     [transaction.atomic]
     1. valida is_active/is_purchasable/disponibilidad
     2. crea Order (status=PENDING_PAYMENT) + OrderItem
     3. si hay paquete: snapshot ServiceRequestPackage/AdditionalCost
     4. crea OrderServiceDetail (snapshot comercial)
     5. crea OrderServiceTimeline inicial (status='pending')
     6. notifica admin (service_request_created, ws admin_notifications)
     7. ServiceOperationCommands.ensure_for_order(order)
        -> crea ServiceOperation en READY_FOR_PLANNING (AUTOMATICO, no
           gateado por aprobacion admin)
        -> crea ServiceOperationEvent OPERATION_CREATED
        -> notifica cliente (service_operation_created)

[pago confirmado] -> ServiceCommands.confirm_slot_on_payment()
   -> confirma ServiceBooking, ensure_for_order() de nuevo (idempotente)
   -> intenta try_auto_assign_via_engine() si sigue sin tecnico

[admin, sistema NUEVO] ServiceOperationCommands:
   plan() -> PLANNED
   assign_technician() / try_auto_assign_via_engine() -> TECHNICIAN_ASSIGNED
   notify_client() -> CUSTOMER_NOTIFIED
   transition(READY_TO_VISIT/ON_THE_WAY/ARRIVED/IN_PROGRESS/COMPLETED)
   close() -> CLOSED
   (cancel()/report_incident()/resolve_incident() en cualquier punto valido)

[admin, sistema LEGACY, EN PARALELO] ServiceOrderViewSet + ServiceAssignmentCommands:
   assign-technician/auto-assign/unassign-technician/change-priority
   -> escriben directo OrderServiceDetail.technician (sin tocar ServiceOperation)
```

Dos timelines independientes conviven sobre la misma orden:
- `OrderServiceTimeline` (orders/service_detail, estados
  `pending/assigned/in_progress/completed/cancelled`) -- escrito por
  `ServiceTimelineCommands.add_timeline_event()` y por el sistema legacy de
  asignacion.
- `ServiceOperationEvent` (`technical_services`, `event_type` libre,
  append-only, 14 puntos de creacion en `ServiceOperationCommands`).
- **Unico punto de sincronizacion**: `ServiceOperationCommands.transition()`
  cuando `target_status == COMPLETED` tambien escribe en
  `OrderServiceTimeline`. El resto de transiciones de `ServiceOperation`
  (plan/assign/notify/ready-to-visit/on-the-way/arrived/cancel/incidentes/close)
  **NO** tocan `OrderServiceTimeline`. Una fachada con timeline unificado
  debe fusionar ambas fuentes, no asumir espejo.

## 3. Endpoints ya existentes (para no duplicar en FASE 5)

| Endpoint | Donde | Admin-only | Que hace |
|---|---|---|---|
| `GET/POST orders/service-orders/` | `orders/api/service_orders.py` | Mixto (filtra por `is_staff` dentro de `get_queryset`) | CRUD de solicitudes, ya con `select_related`/`prefetch_related` sin N+1 |
| `GET orders/service-orders/assignment-queue/` | idem | No explicito (heredado `IsAuthenticated`) | Listado admin-style YA optimizado (`ServiceAssignmentQueueSerializer`), sistema LEGACY |
| `POST orders/service-orders/{uuid}/assign-technician/` etc. | idem | Si (`IsAdminUser` en la lista de acciones) | Sistema LEGACY completo: assign/auto-assign/unassign/change-priority |
| `GET/POST service-operations/` + 15 `@action` | `technical_services/api/operation_views.py` | Si (`IsAdminUser` a nivel de clase, sin excepcion) | Sistema NUEVO completo: dashboard/plan/assign/auto-assign/unassign/reschedule/cancel/notify-client/ready-to-visit/start/arrive/start-service/complete/close/report-incident/resolve-incident |
| `GET services/technician-availability/calendar/` | `technical_services/api/availability_views.py` | Si | `build_calendar_feed()`, agrega WorkingSchedule+WorkingException+ServiceOperation en 3 queries bulk |
| `OrderAdminOrchestrator.list_orders()` | `dashboard/services/admin_orchestrators.py:1071` | Si | Generico, SIN filtro `service_detail__isnull=False` ni prefetch de tecnico -- no serviria tal cual, produciria N+1 |

**No existe** hoy ningun endpoint en `dashboard/api/` especifico para
listar solicitudes de servicio -- es terreno genuinamente nuevo para
FASE 5, pero debe decidir explicitamente sobre cual de los dos sistemas de
asignacion (tabla H1) operar, no puede ignorar la divergencia.

## 4. Frontend -- que existe hoy bajo `/panel/servicios`

Confirmado en `frontend/src/apps/admin/router.js:221-227` +
`Sidebar.vue:134-196`:

| Tab/ruta | Componente | Estado |
|---|---|---|
| Servicios (catalogo) | `ServiceList.vue` + `ServiceForm.vue` (15 tabs internos, ver auditoria FASE 0-7 previa de esta sesion) | Existe, maduro |
| Categorias | `ServiceCategoryList.vue` | Existe |
| Niveles | `ServiceLevelList.vue` | Existe |
| Operaciones | `ServiceOperationBoard.vue` (`servicios/operaciones`) | Existe -- sin store Pinia (useApi directo), sin paginacion, sistema NUEVO |
| Asignacion tecnicos | `TechnicianAssignmentBoard.vue` (`servicios/asignacion-tecnicos`) | Existe -- sin store Pinia, con paginacion, sistema LEGACY |
| Agenda | `TechnicianCalendarBoard.vue` (`servicios/agenda`) | Existe -- sin store Pinia |
| Horarios | `TechnicianScheduleAdmin.vue` (`servicios/horarios`) | Existe -- sin store Pinia |
| **Solicitudes** | **No existe.** Sin componente, sin store (`technicalServicesAdmin/` no tiene `requests.js`, a diferencia de `rentingAdmin/requests.js`) | **Genuinamente nuevo (FASE 6-9)** |
| **Resumen (KPIs)** | **No existe** | **Genuinamente nuevo (FASE 18)** |
| **FAQ (tab independiente)** | Existe solo embebido dentro de `ServiceForm.vue` (`ServiceFAQManager.vue`), no como tab propio de `/panel/servicios` | Requiere reubicacion, no creacion |

## 5. Patron de referencia UX -- Renting `/panel/renta/solicitudes`

`RentingRequestList.vue` + `RentalRequestActionsPanel.vue` (fila expandible,
NO modal/offcanvas separado) + store `rentingAdmin/requests.js`.

- Filtros: `status` (8 opciones **hardcodeadas** en el `&lt;select&gt;`, ni
  siquiera Renting usa `useEnums()` para poblar el filtro), `payment_method`,
  `refund_required`. Sin filtro de fecha ni de tecnico (Renting no tiene
  tecnico).
- Paginacion manual inline (`next`/`previous` del payload), sin componente
  compartido -- **no existe un `Pagination.vue` generico en el panel admin
  para reutilizar tal cual**.
- Empty-state y loading: inline (`&lt;tr v-if&gt;`), sin componente compartido.
- Acciones contextuales: computeds que espejan 1:1 las transiciones validas
  del backend (`RentalRequestCommands`), gateadas por `status` -- patron
  correcto a replicar, pero el `status` de referencia en Renting SI es un
  approval-gated FSM (`pending_validation` inicial); Technical Services no
  tiene ese gate (ver H2).
- `useEnums()` (`frontend/src/composables/useEnums.ts`) SI se usa, pero
  solo para el badge/label de render (`enums.cssClass()`/`enums.label()`),
  no para poblar el filtro. No existe entrada `service-request-statuses`
  en el catalogo fallback -- habria que agregarla si se define un estado
  de "solicitud" propio para servicios.
- `StatusTimeline.vue` (`components/shared/`) es el componente de timeline
  unificado del proyecto (modo `steps`/`events`) -- Renting-solicitudes NO
  lo usa hoy (usa texto plano de estado actual sin historial visual), pero
  es el candidato correcto para el timeline fusionado de la seccion 2.
- `BaseOperationBoard.vue` es el unico componente genuinamente compartido
  entre boards (4 usos: Rental/Service/Shop Operation Boards + generico) --
  cascaron de header+metricas, cada dominio aporta su tabla propia.
- `ServiceOperationBoard.vue` (ya existente en Technical Services) **NO**
  sigue el patron de Renting -- no usa `useEnums()`, define `STATUSES`
  hardcodeado y usa `OperationStatusBadge.vue` en vez de `enums.cssClass()`.
  Si "Solicitudes" replica el patron de Renting (recomendado), diverge del
  patron ya usado por su tab hermana "Operaciones" -- inconsistencia a
  asumir conscientemente, no a "corregir" en este plan (fuera de alcance).

## 6. Notificaciones (ya centralizadas, para FASE 17)

Todo pasa por `NotificationCommands.dispatch_notification()`
(`notifications/services/commands.py:45-148`), siempre en
`transaction.on_commit`. Templates ya sembrados:
`service_request_created` (admin, migracion `0030_seed_service_request_status_templates.py`),
`service_status_updated` (admin), `service_payment_confirmed` (cliente),
`service_operation_created`/`service_operation_assigned`/`service_operation_cancelled`/`service_visit_scheduled`
(dominio ServiceOperation). FASE 17 no necesita crear nada nuevo, solo
invocar estos mismos comandos desde el Orchestrator de fachada.

## 7. Decision de diseno para FASE 1 (resolviendo H1 y H2)

Dado que el prompt maestro autoriza continuar sin pausa salvo condiciones
de PARE explicitas, y ninguno de los 2 hallazgos las dispara, se adoptan
estas resoluciones para que FASE 1 en adelante tenga una base consistente:

- **H1 (doble sistema de asignacion)**: la fachada trata **`ServiceOperation`
  (sistema NUEVO) como fuente de verdad para "tecnico asignado"** -- es el
  que tiene FSM completa, reserva real en `ProfessionalAvailability`, y es
  el que ya usan Agenda/Horarios. El campo legacy
  `OrderServiceDetail.technician` se muestra en el detalle unificado como
  dato de solo lectura ("Tecnico legacy", si difiere del de
  `ServiceOperation`, se marca visualmente como posible inconsistencia) pero
  las ACCIONES de asignacion desde la fachada nueva **solo** escriben via
  `ServiceOperationCommands` -- nunca via `ServiceAssignmentCommands`. Esto
  cumple la regla del prompt ("no crear nuevo selector de tecnicos, usar
  infraestructura existente") escogiendo cual infraestructura existente es
  la correcta, en vez de perpetuar la divergencia.
- **H2 (sin gate de aprobacion)**: la fachada **no inventa** un estado
  `pending_validation` que no existe en el backend (violaria la regla de
  no duplicar/inventar FSM). El primer estado visible de una solicitud en
  la fachada es `READY_FOR_PLANNING` (ya creado automaticamente). Las
  acciones "Aprobar"/"Rechazar" del prompt maestro (FASE 9) se reinterpretan
  como: no existe rechazo formal de una `ServiceOperation` ya creada mas
  alla de `cancel()` (que si existe) -- la fachada muestra directamente las
  acciones reales disponibles segun el estado real (`plan`, `assign`,
  `schedule`, `cancel`...), sin fingir un boton "Aprobar" que no dispara
  nada real en el backend.

## 8. No auditado en profundidad en este incremento

- `ServiceAttachment` (adjuntos de la solicitud) -- mencionado en
  `ServiceOrderViewSet.upload_attachment` pero no explorado a fondo, no es
  bloqueante para FASE 1-5.
- Permisos exactos fila-por-fila de cada `@action` del sistema legacy
  (`orders/api/service_orders.py`) mas alla de la lista ya documentada en
  seccion 3 -- suficiente para decidir el diseno de FASE 1, se revisaria
  con detalle en FASE 23 (seguridad).
- `AdminMetricsOrchestrator._get_marketplace_metrics()` como posible fuente
  reutilizable para FASE 18 (KPIs) -- ya da agregados de servicios
  (`service_status_counts`, etc.) via Subquery/OuterRef sobre el timeline
  append-only; candidato fuerte para no reinventar el calculo de KPIs,
  evaluar en FASE 18.
