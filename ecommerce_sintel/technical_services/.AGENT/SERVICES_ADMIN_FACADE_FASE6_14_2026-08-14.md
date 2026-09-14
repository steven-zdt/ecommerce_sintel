# FASE 6-14 -- Frontend de la Fachada Administrativa Unificada

Plan "Fachada Administrativa Unificada -- Technical Services" (2026-08-14).
Construye `/panel/servicios/solicitudes`, la primera vista admin de
Technical Services que muestra "solicitud entrante" antes de que se
convierta en operacion -- no existia equivalente hasta ahora (ver baseline,
seccion 5: "Solicitudes" era terreno genuinamente nuevo).

## Archivos nuevos

- `frontend/src/store/technicalServicesAdmin/requests.js` -- Pinia store,
  mismo patron que `rentingAdmin/requests.js`. Solo estado UI, pega a
  `dashboard/technical-services/requests/` (BFF admin-only).
- `frontend/src/modules/technical_services/ServiceRequestsPanel.vue` --
  listado + filtros (estado operacion / prioridad / tecnico / busqueda),
  paginacion manual (mismo patron `next`/`previous` que
  `RentingRequestList.vue`).
- `frontend/src/modules/technical_services/ServiceRequestActionsPanel.vue`
  -- fila expandible (no modal, mismo patron que
  `RentalRequestActionsPanel.vue`) con 6 secciones (Cliente/Servicio/Pago/
  Solicitud/Operacion/Orden) + Timeline fusionado
  (`StatusTimeline.vue mode="events"`) + acciones contextuales gateadas
  por el estado real de `ServiceOperation`.

## Reuso deliberado (cero infraestructura nueva donde ya existia una)

- **Badges de estado**: `OperationStatusBadge.vue` (ya existente, usado
  por `ServiceOperationBoard.vue`) para `operation.status`;
  `enums.cssClass()`/`enums.label()` sobre `service-order-statuses` y
  `service-priorities` (enums backend YA registrados en
  `core/api/views.py` -- no se creo ninguno nuevo).
- **Candidatos de tecnico**: `GET service-operations/{uuid}/available-technicians/`
  (endpoint YA existente de `ServiceOperationViewSet`) -- cero selector de
  tecnicos nuevo, cumpliendo FASE 10 al pie de la letra.
- **[Ver operacion]**: enlaza a `/panel/servicios/operaciones?search=<order_uuid>`.
  Encontrado y corregido en la verificacion: `ServiceOperationBoard.vue` no
  leia `route.query.search` -- el link navegaba pero no pre-filtraba. Fix
  de 3 lineas (`useRoute()` + seed de `filters.search`), no se creo un
  detalle nuevo (regla FASE 12).
- **[Ver orden]**: enlaza a la ruta `order-detail` YA existente
  (`/panel/ordenes/:uuid`, `OrderDetailView.vue`) -- cero vista nueva
  (regla FASE 19).

## Filtros -- opciones hardcodeadas, labels desde backend

`RentingRequestList.vue` (la referencia UX explicita del plan) tampoco
deriva las opciones de su `<select>` de filtro del catalogo de enums --
solo usa `useEnums()` para el badge de render. Mismo criterio aqui: las
*claves* de los filtros espejan `ServiceOperation.STATUS_CHOICES`/
`OrderServiceDetail.PRIORITY_CHOICES` (codigo real, no inventadas), pero
el *texto* mostrado sale de `enums.label()` -- nunca hardcodeado.

## Navegacion (FASE 13)

`adminServices.routes.js`: `{ path: 'servicios/solicitudes', name: 'service-requests', component: ServiceRequestsPanel }`.
`Sidebar.vue`: entrada "Solicitudes" agregada al grupo `servicios`
(mismo grupo donde vive "Servicios"/"Categorias"/"Niveles"), no al grupo
`operaciones` -- mismo criterio de ubicacion que usa Renting (su
"Solicitudes" vive en el grupo `renting`, no en `operaciones`).

## Verificado en navegador real (no solo lectura de codigo)

Contra una solicitud real preexistente (orden `3d37f47b...`,
"Instalacion de camara de seguridad"):
1. Listado carga las 71 solicitudes, filtros muestran labels reales
   (`Pendiente de planeacion`, `Planeada`, etc., resueltos via `useEnums()`).
2. Fila expandida muestra las 6 secciones + timeline fusionado
   (evento `order` "Solicitud: Pendiente" + evento `operation`
   "OPERATION_CREATED", ambos con actor y fecha) + acciones contextuales
   correctas para `READY_FOR_PLANNING` (`Planificar`/`Reprogramar`/`Cancelar`,
   sin `Asignar`/`Notificar` -- coincide con la FSM real).
3. **Cadena completa ejecutada en vivo**: `Planificar` (fecha 2026-09-15
   09:00) -&gt; fila pasa a "Planeada" -&gt; `Asignar tecnico` (candidatos
   cargados del endpoint reusado, 9 tecnicos reales) -&gt; "Tecnico
   asignado" con "Tomas Tecnico" -&gt; `Notificar cliente` -&gt; "Cliente
   notificado". Cada paso persistio y el listado se refresco solo.
4. `[Ver operacion]` -&gt; `/panel/servicios/operaciones?search=...` filtra
   correctamente a la unica operacion (tras el fix de `route.query.search`).
5. `[Ver orden]` -&gt; `/panel/ordenes/{uuid}` muestra el mismo timeline
   (`OPERATION_CREATED`/`PLANNED`/`TECHNICIAN_ASSIGNED`/`CUSTOMER_NOTIFIED`)
   -- confirmacion cruzada e independiente de que la fachada escribio
   contra el `ServiceOperation` real, no un estado paralelo.
6. `/panel/renta/solicitudes` (Renting) probado sin cambios -- 69
   solicitudes, filtros y tabla identicos a como estaban (FASE 28).

No se revirtio el estado de prueba (la orden `3d37f47b` quedo en
`CUSTOMER_NOTIFIED` con tecnico asignado) -- es un registro de datos de
desarrollo ya usado en pruebas manuales previas de esta misma sesion, no
un efecto secundario destructivo.

## Pendiente del plan original (no cubierto en este incremento)

- FASE 18 (KPIs en `/panel/servicios`) -- no implementado.
- FASE 26 (test automatizado de frontend) -- este repo no tiene runner de
  tests Vue establecido; se sustituyo por verificacion manual en
  navegador real contra datos reales (mismo criterio usado en toda la
  sesion para cambios de frontend).
- FASE 29 (actualizar `ARQUITECTURA_COMPLETA_SERVICES.md`/
  `IMPLEMENTATION_SUMMARY.md`) -- pendiente.
- FASE 30 (checklist de certificacion de 19 puntos) -- pendiente de
  compilar formalmente, aunque la mayoria de los puntos ya quedaron
  demostrados en la verificacion de arriba.
