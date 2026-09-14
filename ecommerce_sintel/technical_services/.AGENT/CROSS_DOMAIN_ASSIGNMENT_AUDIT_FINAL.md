# Cross-Domain Assignment Audit — Reporte Final

Fecha: 2026-08-14. Branch `fix/audit-p0-remediation`, commit base `5a9f642`.
Auditoria de solo-lectura (FASE R0-R14) sobre mecanismos de asignacion de
tecnico, despachador y vehiculo en Services/Renting/Orders/Operations/Dashboard/
Frontend. Ver documentos complementarios: `CROSS_DOMAIN_ASSIGNMENT_AUDIT_BASELINE.md`,
`OPERATIONS_RESOURCE_MAP.md`, `CROSS_DOMAIN_ASSIGNMENT_MATRIX.md`,
`DOMAIN_SOURCE_OF_TRUTH.md`, `TECHNICIAN_ASSIGNMENT_RECONCILIATION_REPORT.md`.

## Resumen ejecutivo

**La pregunta que el prompt de auditoria hacia explicitamente (¿Renting depende
indebidamente de `OrderServiceDetail.technician`?) tiene respuesta NEGATIVA,
confirmada con evidencia exhaustiva: 0 referencias.** Ese eje de riesgo, tal como
estaba planteado, no existe.

**Pero la auditoria encontro un hallazgo real y critico que ninguno de los 2
prompts de esta sesion anticipaba**: existe un tercer sistema de asignacion
(`operations.OperationCommands`, detras de `/panel/operaciones`) que escribe de
forma independiente y sin coordinacion las mismas banderas de disponibilidad
(`TechnicianProfile.is_available`, `DispatcherProfile.is_available`) que
`technical_services` y `renting` usan como precondicion para sus propias
asignaciones. Es codigo vivo, alcanzable desde un panel admin real, no
infraestructura muerta. Ver seccion "Hallazgo Critico" abajo.

## 1. Arquitectura encontrada

```
                     ORDERS
                       |
                commercial owner (Order, OrderServiceDetail)
                       |
              +--------+--------+
              |                 |
              v                 v
          SERVICES           RENTING
              |                 |
              v                 v
       ServiceOperation    RentalOperation
       .technician         .assigned_dispatcher
                            .assigned_vehicle
              |                 |
              v                 v
       TechnicianProfile   DispatcherProfile
       .is_available       .is_available
              ^                 ^
              |                 |
              +--------+--------+
                       |
              operations.OperationCommands
              (assign_resource / auto_assign,
               via OperationTicket -- tercer
               sistema, no coordinado)
```

Confirmado: no hay flecha directa `RentalOperation -> ServiceOperation` ni
`RentalOperation -> OrderServiceDetail.technician` en ninguna direccion. El
cruce real esta mas abajo en el diagrama, a nivel de las banderas de
disponibilidad compartidas, no a nivel de los campos de asignacion en si.

## 2. Ownership (confirmado)

| Dominio | Owner de |
|---|---|
| Orders | `Order`, `OrderServiceDetail` (comercial/snapshot) |
| Services | `ServiceOperation` (incluye `.technician`) |
| Renting | `RentalOperation` (incluye `.assigned_dispatcher`/`.assigned_vehicle`) |
| Operations | `DispatcherProfile`, `OperationTicket`, `OperationAssignment`, `TrackingEvent`, `OperationDocument`, `OperationReview` |

Ver `DOMAIN_SOURCE_OF_TRUTH.md` para el detalle completo por campo.

## 3. Writers (matriz completa)

Ver `CROSS_DOMAIN_ASSIGNMENT_MATRIX.md`. Resumen de escrituras a los 2 campos de
asignacion "reales":

- `ServiceOperation.technician`: **1 escritor** — `ServiceOperationCommands`
  (`technical_services/services/operations.py`). Consolidado esta sesion.
- `RentalOperation.assigned_dispatcher`/`.assigned_vehicle`: **1 escritor** —
  `RentalOperationCommands.assign_dispatcher()` (`renting/services/operations.py`).

Escrituras a las 2 banderas de disponibilidad compartidas (el hallazgo real):

- `TechnicianProfile.is_available`: **2 escritores** —
  `ServiceOperationCommands._set_technician_availability()` (Services, esta
  sesion) y `OperationCommands.assign_resource()` (Operations, preexistente,
  desconocido hasta esta auditoria).
- `DispatcherProfile.is_available`: **2 escritores activos** (de 3 consumidores
  potenciales) — `OperationCommands.assign_resource()` (Operations) y
  `orders/services/fulfillment/assignment.py::assign_dispatcher()` (Shipment).
  Renting **lee** la bandera pero nunca la escribe (gap propio, no cruce de
  dominio).

## 4. Readers

- `dashboard/services/admin_orchestrators.py::ServiceAdminRequestSelector` lee
  intencionalmente AMBOS `ServiceOperation.technician` (fuente real) y
  `OrderServiceDetail.technician` (legacy) para calcular un flag `diverges` —
  disenado correctamente desde el principio (Fachada Administrativa Unificada,
  fase anterior de esta sesion), no es un hallazgo nuevo.
- `orders/api/service_orders.py` y `technical_services/api/serializers.py`
  (`OrderServiceDetailSerializer`, `ServiceAssignmentQueueSerializer`): migrados
  esta sesion (FASE 9) para priorizar `ServiceOperation.technician`.
- Ningun lector encontrado en `renting/`/`operations/` para
  `OrderServiceDetail.technician` (0 hits).

## 5. Referencias legacy

- `OrderServiceDetail.technician` — unico caso legacy formal, ya resuelto
  (ver migracion previa de esta sesion, `TECHNICIAN_ASSIGNMENT_MIGRATION_
  FASE0_2026-08-14.md`).
- `RentalOperation.assigned_vehicle` como string libre (no FK a un modelo
  `Vehicle`, que no existe) — no es "legacy", es una decision de diseno
  deliberada y consistente en todo el codebase (`DispatcherProfile.vehicle_plate`
  tambien es string).

## 6. Conflictos reales (datos)

Ver `TECHNICIAN_ASSIGNMENT_RECONCILIATION_REPORT.md` (corrido contra la base de
datos real, no la de tests): **0 conflictos** entre `ServiceOperation.technician`
y `OrderServiceDetail.technician`. Esta auditoria no corrio una reconciliacion
equivalente para `TechnicianProfile.is_available`/`DispatcherProfile.is_available`
divergentes de `OperationAssignment` -- queda como trabajo pendiente si se decide
actuar sobre el hallazgo critico (ver Riesgos).

## 7. Hallazgos por dominio

### Renting (R5-R7, R12)
**Limpio.** `RentalOperation.assigned_dispatcher`/`.assigned_vehicle` es el unico
escritor real de asignacion logistica de Renting. `assign_dispatcher()`
(`renting/services/operations.py:88-133`) valida FSM (`status == SCHEDULED`),
valida `dispatcher.is_active`/`is_available`, pero **no valida conflicto real de
horario** contra otras asignaciones (solo el booleano) -- mismo nivel de
madurez que el sistema legacy de Services tenia antes de esta sesion (que si fue
mejorado a chequeo real de agenda via `ProfessionalAvailability`). No es un
hallazgo de esta auditoria arreglarlo (fuera del alcance R0-R14, y no viola
ninguna de las 26 prohibiciones), pero es una brecha de calidad conocida.
0 referencias a `OrderServiceDetail`/`ServiceOperation`/`technical_services` en
todo el directorio -- confirmado por 2 busquedas independientes.

### Services (R4)
Ya resuelto por la migracion previa de esta sesion (FASE 0-9): `ServiceOperation.
technician` es la unica autoridad de asignacion, `OrderServiceDetail.technician`
es snapshot puro. 0 conflictos reales en datos. Unico gap remanente: la bandera
compartida `TechnicianProfile.is_available` tiene un segundo escritor fuera de
Services (ver Hallazgo Critico).

### Orders (R9)
Sigue siendo owner comercial puro. `OrderServiceDetail.technician` no acepta
escrituras independientes desde ningun sistema (Django Admin bloqueado, endpoints
legacy delegan). `orders.Shipment` (dominio de envios, distinto del de
tecnicos/despachadores de Services/Renting) SI escribe `DispatcherProfile.
is_available` para su propio flujo de asignacion de conductor de entrega --
correcto y esperado (reutiliza el mismo pool de recursos, es un consumidor
legitimo mas, no un cruce indebido).

### Operations (R8, hallazgo critico)
Ver seccion dedicada abajo.

### Frontend (R13)
Limpio a nivel de UI: ningun modulo de Renting llama nada con "technician" en el
nombre/endpoint, ningun modulo de Services llama nada con "dispatcher"/"vehicle".
Cada dominio tiene su propio conjunto de llamadas API bien delimitado. El unico
punto de contacto cross-domain en el frontend es el dropdown de seleccion de
despachador en `RentalOperationBoard.vue`, que carga `dashboard/dispatchers/`
(read-only, pool compartido legitimo) -- no un problema.

## 8. Hallazgo Critico: tercer escritor no coordinado de disponibilidad

**Sistema encontrado**: `operations.OperationCommands.assign_resource()`/
`.auto_assign()` (`operations/services/commands.py:169-293`), expuesto en
`POST /api/v1/dashboard/operations/{pk}/assign/` y `.../auto-assign/`, con UI
real y clickeable en `/panel/operaciones/{uuid}` (`OperationDetail.vue`, botones
"Asignar"/"Auto-asignar").

**Por que es real, no teorico**:
- `OperationTicket` se crea automaticamente para **toda** orden/renta pagada
  (`payment/shared/commands.py`, `payment/cod/services/commands.py`,
  `renting/services/commands.py` -- sin excepcion, sin gate por tipo).
- Un admin puede abrir `/panel/operaciones/{uuid}` para CUALQUIERA de esos
  tickets y asignar un tecnico o despachador real desde ahi.
- Para rol TECHNICIAN: escribe `accounts.TechnicianProfile.is_available = False`
  y crea un `OperationAssignment` -- **sin tocar `ServiceOperation.technician`,
  sin crear `ServiceOperationEvent`, sin notificacion, sin `ProfessionalAvailability`**.
  El tecnico queda invisible para `/panel/servicios` como "ocupado" pero sin
  ninguna `ServiceOperation` que lo explique.
- Para rol DISPATCHER/TRANSPORTER: escribe `operations.DispatcherProfile.
  is_available = False` -- el mismo campo que Renting **lee** como precondicion
  en `assign_dispatcher()` pero nunca escribe. Resultado: un despachador
  asignado via `/panel/operaciones` desaparece silenciosamente del pool
  disponible de Renting, sin que `RentalOperation` se entere de por que.
- `OperationTicket.status` es una FSM independiente de `ServiceOperation.status`/
  `RentalOperation.status`, sin ningun mecanismo de sincronizacion (confirmado:
  ni signal, ni post_save, ni llamada cruzada) -- el propio codigo del proyecto
  ya documenta un caso real de divergencia observada
  (`get_effective_status()`, comentario: "ticket real con status=CANCELLED cuyo
  ServiceOperation vinculado sigue en READY_FOR_PLANNING, nunca se sincronizo").

**Por que la migracion de esta sesion no lo detecto**: la auditoria FASE 0 de
esa migracion (documentada en `TECHNICIAN_ASSIGNMENT_MIGRATION_FASE0_2026-08-14.md`)
busco escrituras directas al patron `.technician =` -- `OperationCommands.
assign_resource()` nunca hace eso; escribe `technician.is_available = False`
y crea una fila en `OperationAssignment`. El patron de busqueda de esa auditoria
no podia detectar este escritor por diseno, no por descuido.

**Clasificacion**: `CRITICAL DUPLICATE WRITER` sobre las banderas de
disponibilidad (no sobre los campos de asignacion `.technician`/
`.assigned_dispatcher` en si, que siguen teniendo un unico escritor cada uno).

## 9. Cambios necesarios (recomendacion, NO ejecutados en esta auditoria)

Por regla del prompt (R31: "si existe doble writer: ejecutar R15 en adelante" —
pero R15-R17 del prompt solo cubren la solucion para Services/Orders/Renting tal
como el prompt las definio, no para este hallazgo nuevo de Operations), **no se
ejecuta remediacion automatica** porque:
1. `/panel/operaciones` es una funcionalidad admin real y en uso -- desactivarla
   o cambiar su comportamiento sin confirmacion podria romper un flujo que algun
   admin depende hoy.
2. Hay mas de una estrategia de resolucion valida con tradeoffs distintos (ver
   opciones abajo), es una decision de producto/arquitectura, no solo tecnica.
3. El prompt mismo lista "UNEXPECTED OWNER" como condicion de STOP explicita —
   `operations.OperationCommands` es exactamente un tercer owner no anticipado.

**Opciones de resolucion (para decidir, no implementadas)**:

- **A. Hacer `OperationCommands.assign_resource()` de solo-lectura/deshabilitarlo
  para roles TECHNICIAN/DISPATCHER** -- el ticket seguiria existiendo y
  trackeando timeline/documentos/reviews, pero la asignacion real solo se haria
  desde `/panel/servicios` o `/panel/renta`. Preserva la garantia de escritor
  unico sin tocar Services/Renting. Requiere decidir que pasa con
  `/panel/operaciones` (¿se convierte en panel de solo-vista? ¿se le agrega un
  link a "ir a asignar en el panel correcto"?).
- **B. Hacer que `OperationCommands.assign_resource()` delegue en
  `ServiceOperationCommands`/`RentalOperationCommands` en vez de escribir la
  bandera el mismo** -- mismo patron ya usado para resolver el hallazgo H1 de
  Services esta sesion (FASE 4). Mantiene `/panel/operaciones` funcional pero
  redirige la decision real al dominio correcto.
- **C. Sincronizar `OperationTicket`/`OperationAssignment` con `ServiceOperation`/
  `RentalOperation` via signals** -- expresamente desaconsejado por la regla 8
  del prompt ("Sincronizar campos mediante signals sin autoridad clara") salvo
  que se defina una autoridad clara primero (lo cual apunta de vuelta a A o B).

**Decision del usuario (2026-08-14, via `AskUserQuestion`): Opcion B.** Implementada:

- `operations/services/commands.py::OperationCommands.assign_resource()` ya NO
  escribe `TechnicianProfile.is_available`/`DispatcherProfile.is_available`
  directamente para tickets SERVICE/RENTAL -- delega en
  `ServiceOperationCommands.assign_technician()`/
  `RentalOperationCommands.assign_dispatcher()` (via
  `ensure_for_order()`/`ensure_for_request()` para resolver la operacion real).
  Para SHOP_DELIVERY (dominio de `orders.Shipment`, fuera del alcance de esta
  auditoria) se conserva el comportamiento previo sin cambios.
- `renting/services/operations.py::RentalOperationCommands.assign_dispatcher()`/
  `.schedule()` relajados con el mismo patron ya validado para Services (FASE 2
  de la migracion de autoridad de tecnico, misma sesion): permite pre-asignar
  transportista antes de programar, completando la asignacion real cuando
  `schedule()` se ejecuta. De paso se cerro el gap documentado en la seccion 7
  ("Renting nunca marca `DispatcherProfile.is_available=False`") -- ahora lo
  hace, via `_set_dispatcher_availability()` (mismo patron que
  `ServiceOperationCommands._set_technician_availability()`).
- `frontend/src/modules/renting/RentalOperationBoard.vue`: gating del bloque de
  asignacion de transportista extendido a `READY_FOR_SCHEDULING`/
  `TRANSPORT_ASSIGNED` (antes solo `SCHEDULED`), consistente con la nueva
  capacidad del backend.
- Tests nuevos: `operations.tests.OperationPipelineTests.
  test_assign_resource_service_ticket_delegates_to_service_operation`/
  `test_assign_resource_rental_ticket_delegates_to_rental_operation` (verifican
  que `assign_resource()` efectivamente mueve `ServiceOperation.technician`/
  `RentalOperation.assigned_dispatcher`, no solo la bandera) +
  `renting.tests.RentalOperationLifecycleTestCase.
  test_can_pre_assign_dispatcher_before_scheduling`/
  `test_cannot_assign_dispatcher_invalid_operation_status`.
- Regresion verificada: `renting` + `operations`, 131 tests, 9 fallas
  preexistentes sin relacion (bugs de datos en `renting/tests_presenters.py`,
  confirmado via `git status` sin cambios en esos archivos ni en
  `renting/models/` -- reportado por separado, no es parte de este hallazgo).
  Los 21 tests que ejercitan directamente el codigo tocado por esta
  remediacion (`RentalOperationLifecycleTestCase`, `OperationPipelineTests`,
  `DispatcherProfileCrossDomainFixTests`, `NotifyStaleOperationTicketsTests`)
  pasan sin excepcion.

**No implementado (fuera del alcance de la decision tomada)**: el mismo patron
de duplicacion para tickets SHOP_DELIVERY (`orders.Shipment.assigned_dispatcher`
vs `OperationAssignment` vs `DispatcherProfile.is_available`) -- mencionado en
la seccion "Hallazgos por dominio > Orders" como un consumidor legitimo
adicional del mismo pool de recursos, pero no fue parte de la pregunta
formulada al usuario ni de su decision. Queda documentado como alcance futuro
si se decide auditar ese tercer eje.

## 10. Cambios NO necesarios

- Renting: ningun cambio -- confirmado limpio de cruce con `OrderServiceDetail`.
- Services/Orders: ningun cambio adicional -- la migracion previa de esta sesion
  ya cerro ese eje completamente (0 conflictos reales en datos).
- No se requiere ninguna entidad nueva (`ServiceRequest`, `RentalAssignment`,
  `OrderAssignment`, `TransportAssignment`) -- todas las entidades necesarias ya
  existen.

## 11. Riesgos

| Riesgo | Severidad | Estado |
|---|---|---|
| Tecnico marcado `is_available=False` via `/panel/operaciones` sin `ServiceOperation` visible que lo explique -- posible bloqueo fantasma de un tecnico en `/panel/servicios` | Alto | Sin mitigar, requiere decision (ver seccion 9) |
| Despachador marcado `is_available=False` via `/panel/operaciones`, invisible para `/panel/renta` | Alto | Sin mitigar, requiere decision |
| `OperationTicket.status` puede divergir permanentemente de `ServiceOperation`/`RentalOperation` (ya observado en datos reales segun comentario propio del codigo) | Medio | Conocido, sin mitigar |
| Renting nunca marca `DispatcherProfile.is_available=False` al asignar -- posible doble-reserva de un despachador entre 2 rentas simultaneas | Medio | Gap propio de Renting, fuera del alcance de esta auditoria pero documentado |
| Cruce `OrderServiceDetail.technician` <-> Renting | Ninguno | Descartado con evidencia (0 hits) |

## 12. Tests

No se agregaron tests nuevos en esta auditoria (fase de solo-descubrimiento). Los
existentes que siguen siendo validos como red de seguridad para Services/Orders:
`technical_services.tests`, `technical_services.tests_operations` (203 tests,
incluye los 2 agregados en la migracion previa de esta sesion). No existe
cobertura de test hoy para el hallazgo critico (`OperationCommands.
assign_resource()` vs `ServiceOperation`/`RentalOperation`) -- se recomienda
agregarla junto con la resolucion que se decida en la seccion 9.

## 13. Resultado final

**Conclusion formal para R14** (confirmar/refutar dos sistemas de escritura):

- Para el eje que el prompt anticipaba explicitamente (`ServiceOperation.technician`
  vs `OrderServiceDetail.technician`, y cualquier cruce equivalente hacia
  Renting): **refutado** -- ya resuelto, un unico escritor real por campo de
  asignacion, 0 cruce con Renting.
- Para el eje que la auditoria encontro (banderas de disponibilidad compartidas
  `TechnicianProfile.is_available`/`DispatcherProfile.is_available`, con
  `operations.OperationCommands` como tercer escritor no coordinado):
  **confirmado, CRITICAL DUPLICATE WRITER** -- resuelto (Opcion B, seccion 9)
  para tickets SERVICE/RENTAL. `OperationCommands.assign_resource()` ya no
  decide nada por su cuenta para esos 2 tipos; delega en
  `ServiceOperationCommands`/`RentalOperationCommands`, los unicos escritores
  reales de cada dominio. SHOP_DELIVERY queda fuera del alcance de la decision
  tomada (ver nota al final de la seccion 9).

El sistema demuestra hoy:
1. ✅ Un unico writer para Services technician (`.technician`).
2. ✅ Un unico writer para Renting dispatcher/vehicle (`.assigned_dispatcher`/
   `.assigned_vehicle`).
3. ❌ **NO** un unico writer para la disponibilidad de tecnicos
   (`TechnicianProfile.is_available`) -- 2 escritores confirmados.
4. ❌ **NO** un unico writer para la disponibilidad de despachadores
   (`DispatcherProfile.is_available`) -- 2 escritores confirmados (mas un
   tercer consumidor, Renting, que nunca escribe).
5. ✅ Orders sigue siendo owner comercial.
6. ✅ Services sigue siendo owner tecnico.
7. ✅ Renting sigue siendo owner logistico.
8. ⚠️ Operations es owner de recursos compartidos, pero TAMBIEN tiene su propio
   sistema de asignacion activo que no estaba documentado como tal antes de esta
   auditoria -- no es solo un proveedor pasivo de recursos.
9. ❌ Existe sincronizacion circular / divergencia sin resolver entre
   `OperationTicket.status` y los FSM de dominio (confirmada por evidencia en el
   propio codigo).
10. ❌ Existen escrituras cruzadas indebidas -- las 2 banderas de disponibilidad.
11. ✅ Panel Services funciona como fachada (sin cambios de ownership).
12. ✅ Panel Renting sigue funcionando independientemente.
