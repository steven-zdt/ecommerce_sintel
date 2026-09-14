# FASE 30 -- Certificacion final: Fachada Administrativa Unificada

Plan "Fachada Administrativa Unificada -- Technical Services" (2026-08-14).
Checklist de los 19 puntos del prompt maestro, cada uno con su evidencia
real (test automatizado o verificacion en navegador de esta misma sesion,
no una afirmacion sin respaldo).

| # | Punto | Estado | Evidencia |
|---|---|---|---|
| 1 | Customer crea solicitud | PASS | Flujo `ServiceRequestWizard.vue`/`ServiceCommands.request_service()` sin ningun cambio de codigo -- verificado indirectamente: la solicitud de prueba usada en toda la certificacion (`3d37f47b...`) fue creada por ese mismo camino antes de este plan |
| 2 | Orders sigue siendo dueño | PASS | `dashboard/tests.py::test_no_approve_action_and_no_parallel_service_request_model` + matriz de ownership (`SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md`): ninguna accion de la fachada escribe `Order` directo |
| 3 | `OrderServiceDetail` existe | PASS | Confirmado en baseline (`technical_services/models.py:325-378`), expuesto sin cambios en el DTO (`commercial`/`customer.address`) |
| 4 | `ServiceOperation` existe | PASS | FSM completa auditada (`SERVICES_ADMIN_FACADE_BASELINE.md` §1), usada como fuente de verdad de todas las acciones de la fachada |
| 5 | Admin entra a `/panel/servicios` | PASS | Ruta y sidebar sin cambios estructurales -- "Solicitudes" se agrego al mismo grupo, sin romper `servicios`/`s-categorias`/`s-niveles` |
| 6 | Admin ve solicitud | PASS | Verificado en navegador: listado de 71 solicitudes reales con columnas completas |
| 7 | Admin abre detalle | PASS | Verificado: fila expandible, `ServiceRequestActionsPanel.vue` |
| 8 | Admin ve cliente | PASS | Verificado: seccion "Cliente" (nombre/email/direccion) |
| 9 | Admin ve servicio | PASS | Verificado: seccion "Servicio" (nombre/categoria/variante/precio) |
| 10 | Admin ve pago | PASS | Verificado: seccion "Pago" (metodo/estado orden/total) |
| 11 | Admin ve operacion | PASS | Verificado: seccion "Operacion" (estado via `OperationStatusBadge`/tecnico/programada) |
| 12 | Admin asigna tecnico | PASS | Verificado en vivo: "Tomas Tecnico" asignado, candidatos cargados del endpoint real `available-technicians`, persistido en BD (fila paso a "Tecnico asignado") |
| 13 | Admin programa | PASS | Verificado en vivo: `Planificar` con fecha 2026-09-15 09:00 -- fila paso a "Planeada" |
| 14 | Admin notifica | PASS | Verificado en vivo: `Notificar cliente` -- fila paso a "Cliente notificado" (`ServiceOperation.CUSTOMER_NOTIFIED`) |
| 15 | Admin abre operacion | PASS | Verificado: `[Ver operacion]` -> `/panel/servicios/operaciones?search=<uuid>` -- filtra correctamente a la unica operacion (gap de `route.query.search` encontrado y corregido en la misma verificacion) |
| 16 | Admin puede abrir orden | PASS | Verificado: `[Ver orden]` -> `/panel/ordenes/{uuid}` -- muestra el mismo timeline (`OPERATION_CREATED`/`PLANNED`/`TECHNICIAN_ASSIGNED`/`CUSTOMER_NOTIFIED`), confirmacion cruzada independiente de que la fachada escribio contra el `ServiceOperation` real |
| 17 | Customer sigue funcionando | PASS | Cero archivos de `views/customer/services/` o `ServiceRequestWizard.vue`/`ServiceCheckoutModal` tocados en todo el plan |
| 18 | Renting sigue funcionando | PASS | Verificado en navegador tras completar el plan: `/panel/renta/solicitudes` -- 69 solicitudes, filtros y tabla identicos |
| 19 | No existe `ServiceRequest` duplicado | PASS | `dashboard/tests.py::test_no_approve_action_and_no_parallel_service_request_model`: `hasattr(technical_services.models, 'ServiceRequest')` == `False` (asercion ejecutable, no solo documental) |

**19/19 PASS.**

## Resumen de verificacion tecnica (no parte del checklist de 19, contexto adicional)

- Backend: 5 tests nuevos + regresion completa `dashboard` **57/57 PASS**.
- Performance: 7 queries para 20 filas serializadas completas (incluye
  timeline fusionado) -- verificado con `CaptureQueriesContext` contra las
  71 solicitudes reales existentes, no datos sinteticos.
- Seguridad: `ADMIN_PERMISSIONS` en el ViewSet + test explicito de 403
  para usuario no-admin.
- Ownership: matriz vinculante (`SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md`)
  -- la fachada nunca hace `Model.objects.update()`/`.save()` directo,
  toda escritura es una delegacion de una linea a un comando ya existente.

## Hallazgos reportados durante el plan (no bugs introducidos, deuda preexistente)

1. **H1** (baseline): dos sistemas de asignacion de tecnico coexisten sin
   sincronizar (`ServiceOperation.technician` vs.
   `OrderServiceDetail.technician`). Resuelto para la fachada (trata al
   primero como fuente de verdad), pero los dos paneles admin preexistentes
   (`ServiceOperationBoard.vue`/`TechnicianAssignmentBoard.vue`) siguen
   pudiendo divergir entre si -- fuera del alcance de este plan corregirlo
   de raiz.
2. **H2** (baseline): no existe gate de aprobacion para servicios (a
   diferencia de Renting) -- decision de diseno documentada, no un bug.
3. `ServiceSelector.get_by_uuid()` (modulo de catalogo publico, distinto
   de esta fachada) no filtra `is_active` -- reportado en la auditoria
   FASE 7 del rediseno de `ServiceForm.vue`, la misma sesion, antes de
   este plan. No corregido por requerir separar el selector publico del
   admin (cambio de mayor alcance).
