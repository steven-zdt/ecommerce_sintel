# FASE 2-5 -- Backend de la Fachada Administrativa Unificada

Plan "Fachada Administrativa Unificada -- Technical Services" (2026-08-14).
Implementa el backend completo de lectura+escritura de
`/panel/servicios &gt; Solicitudes`, siguiendo la matriz de ownership de
`SERVICES_ADMIN_FACADE_MATRIX_2026-08-14.md`.

## FASE 2-4 -- DTO + Selector + Orchestrator

`dashboard/services/admin_orchestrators.py` (antes de `RentingAdminOrchestrator`):

- **`ServiceAdminRequestSelector`**: `base_queryset()` combina `Order` +
  `OrderServiceDetail` + `ServiceOperation` + tecnico (+ perfil) en una
  sola consulta, con `current_status` anotado via Subquery/OuterRef sobre
  `OrderServiceTimeline` (mismo patron ya usado por
  `AdminMetricsOrchestrator._get_marketplace_metrics()` -- no inventado).
  `list_for_admin(status, priority, technician_id, has_technician, search)`
  y `get_by_uuid(uuid)` sobre ese queryset. **Nunca escribe.**
- **`ServiceAdminRequestOrchestrator`**: `list_requests()`/`get_request()`
  delegan al Selector. `plan_request()`/`assign_technician()`/
  `schedule_request()`/`notify_customer()`/`cancel_request()` son
  delegaciones de una linea a `ServiceOperationCommands` (nunca
  `Model.objects.update()`/`.save()` directo -- regla vinculante de la
  matriz). **No existe `approve_request()`**: no hay estado de aprobacion
  en el backend de servicios (hallazgo H2 del baseline) -- inventar un
  "aprobar" sin transicion real detras violaria la regla de no crear FSM
  paralela.

`dashboard/api/serializers.py` -- **`ServiceAdminRequestSummarySerializer`**
(DTO, no persistente): `request_id`/`order_id`/`tracking_number`/
`created_at` + `customer`/`service`/`variant`/`commercial`/`payment`/
`request_status`/`operation`/`technician`/`schedule`/`timeline` (todos
`SerializerMethodField`). `technician` expone ambos sistemas de asignacion
(ver H1): `uuid`/`name` = `ServiceOperation.technician` (fuente de
verdad), `legacy_uuid`/`legacy_name` = `OrderServiceDetail.technician`
(solo lectura), `diverges=True` si difieren. `timeline` fusiona
`OrderServiceTimeline` + `ServiceOperationEvent` (dos bitacoras
independientes, ver baseline) ordenadas por fecha.

**Performance verificado con datos reales** (71 solicitudes existentes en
BD): 20 filas serializadas completas (incluyendo timeline fusionado) en
**7 queries totales** (antes de agregar `select_related('profile')` en
la cadena de usuarios/tecnicos: 87 queries -- `User.get_full_name()`
delega a `ProfileResolver.get_profile()` = `user.profile`, que sin
`select_related` dispara una query por cada referencia a usuario/tecnico/
actor de timeline). Corregido antes de cerrar la fase, no despues.

## FASE 5 -- Endpoint BFF

`dashboard/api/views.py` -- **`AdminServiceRequestViewSet`**
(`viewsets.ViewSet`, `ADMIN_PERMISSIONS`, mismo patron que
`AdminTechnicalServiceViewSet`): `list()` (con `DashboardResultsSetPagination`,
mismo patron que `AdminProductViewSet`) + `retrieve()` +
`@action` `plan`/`assign`/`schedule`/`notify`/`cancel`, todas `POST`
`detail=True`. Reusa los serializers de INPUT ya existentes de
`ServiceOperationViewSet`
(`ServiceOperationPlanSerializer`/`AssignSerializer`/`RescheduleSerializer`/
`CancelSerializer` de `technical_services/api/operation_serializers.py`)
en vez de duplicarlos.

`dashboard/api/urls.py` --
`router.register(r'technical-services/requests', AdminServiceRequestViewSet, basename='admin-service-requests')`
→ `GET/POST /api/v1/dashboard/technical-services/requests/`,
`GET /{uuid}/`, `POST /{uuid}/plan/`, `/assign/`, `/schedule/`, `/notify/`,
`/cancel/`. **No existe `/{uuid}/approve/`** (404 verificado por test, ver
abajo) -- consistente con H2.

## Tests (`dashboard/tests.py::ServiceAdminRequestFacadeTestCase`, 5/5 PASS)

Contra una solicitud real creada por el camino real
(`ServiceCommands.request_service()`, no un fixture inventado):
1. `test_list_includes_the_request` -- el listado admin incluye la orden.
2. `test_detail_combines_order_and_operation` -- el detalle trae
   `service.name` (de `orders`) y `operation.status` (de
   `technical_services`) en un solo payload.
3. `test_plan_assign_schedule_notify_cancel_delegate_to_service_operation`
   -- las 5 acciones reales mueven `ServiceOperation` por su FSM real
   (`READY_FOR_PLANNING → PLANNED → TECHNICIAN_ASSIGNED → ... →
   CUSTOMER_NOTIFIED → CANCELLED`), y **confirma explicitamente que
   `OrderServiceDetail.technician` (legacy) permanece `None`** tras
   asignar desde la fachada -- prueba directa de que H1 se resolvio como
   se documento (`ServiceOperation` es la unica fuente de verdad para
   escritura).
4. `test_no_approve_action_and_no_parallel_service_request_model` --
   `POST .../approve/` → 404, y `hasattr(technical_services.models, 'ServiceRequest')`
   → `False`. Cubre 2 de las reglas de "NO crear" del prompt maestro con
   una asercion ejecutable, no solo documental.
5. `test_non_admin_cannot_access_facade` -- 403 para usuario no-admin.

Regresion completa de `dashboard.tests` corriendo en background al cierre
de esta fase (ver checkpoint).
