# CORE v4 — Fase 5 (Refactorización por Dominio): propuesta de diseño para consolidar Operaciones

**Fecha:** 2026-07-12
**Estado:** Propuesta de diseño. **Cero código escrito todavía.** Este documento existe para
acordar el ENFOQUE antes de tocar datos operativos en vivo (pedidos/servicios/rentas en curso
ahora mismo en producción).

---

## Recordatorio del problema (Fase 1)

4 máquinas de estado independientes para el mismo concepto ("ciclo operativo post-pago"), creadas
simultáneamente para el mismo evento, sin FK entre sí:

| Sistema | Dueño hoy | Estados | Campos ricos propios |
|---|---|---|---|
| `OperationTicket` | `operations` | 9 (CREATED→...→COMPLETED/CANCELLED) | `operation_type`, `source_order`/`source_rental_request`, `scheduled_date/time` |
| `ServiceOperation` | `technical_services` | 11 (READY_FOR_PLANNING→...→CLOSED/CANCELLED) | `technician`, `availability_slot`, `arrived_at/started_at/completed_at`, `closure_status`, `has_incident` |
| `RentalOperation` | `renting` | 10 (READY_FOR_SCHEDULING→...→COMPLETED) | `assigned_dispatcher`, `assigned_vehicle`, `delivery_date/pickup_date`, `has_incident` |
| `Shipment` | `orders` | FSM propio (picking/packing/despacho/entrega) | `dispatch_center`, `carrier`, `driver`, `package_*`, `evidence_photos` |

Cada uno tiene su propio timeline (`ServiceOperationEvent`/`RentalOperationEvent`/
`ShipmentTimeline`/`TrackingEvent`) y su propio tablero de frontend
(`ServiceOperationBoard.vue`, `RentalOperationBoard.vue`, fulfillment UI de `orders`,
`OperationBoard.vue`).

---

## 3 opciones de diseño

### Opción A — Consolidación total en `OperationTicket`
Un solo modelo absorbe todos los campos de los 3 satélites (con campos condicionales según
`operation_type`); se eliminan `ServiceOperation`, `RentalOperation`, `Shipment` por completo.

- ✅ Máximo apego al principio "un solo dueño".
- 🔴 **Riesgo muy alto**: migración de datos en vivo de 3 tablas con registros activos AHORA
  MISMO (técnicos en camino, rentas en tránsito, pedidos en preparación) hacia una tabla nueva.
- 🔴 Antipatrón "God model": mezcla campos de 3 dominios distintos (`technician`+
  `assigned_vehicle`+`dispatch_center`) en un solo modelo genérico — contradice el espíritu de
  "cada dominio es dueño único de su proceso" que motiva todo este plan.
- 🔴 Requiere reescribir los 4 tableros de frontend para consumir un modelo/API nuevo.
- **No recomendada.**

### Opción B — `OperationTicket` como capa de despacho; los satélites conservan su FSM rica (recomendada)
`OperationTicket` deja de tener un campo `status` independiente. Se agrega un FK directo desde
el ticket hacia su registro de ejecución específico (`service_operation`, `rental_operation`,
`shipment` — nullable, exactamente uno según `operation_type`, mismo patrón de constraint que ya
usa `source_order`/`source_rental_request`). El "estado visible" del ticket se **deriva** del
estado del satélite vía una propiedad/selector (`OperationTicketSelector.get_display_status()`),
con un mapa de traducción de los 9-11-10 estados especializados a un pequeño set de estados
genéricos para el tablero unificado (`PENDING`/`IN_PROGRESS`/`COMPLETED`/`CANCELLED`, por
ejemplo).

- ✅ Cada dominio conserva su FSM rica y su propia lógica de negocio — respeta "cada dominio es
  dueño único de su proceso".
- ✅ **No se borra ni migra ningún dato existente** — se agrega un FK y se cambia cómo se LEE el
  estado en `OperationTicket`, no se toca `ServiceOperation`/`RentalOperation`/`Shipment`.
- ✅ Los 3 tableros de dominio (`ServiceOperationBoard.vue`, etc.) siguen funcionando sin
  cambios — solo el tablero unificado de Operaciones cambia de dónde lee el "estado".
- ✅ Elimina la duplicación real: a partir de ahora hay una sola fuente de verdad del estado por
  operación (el satélite), `OperationTicket` deja de tener su propio estado que pueda divergir.
- ⚠️ Requiere backfill de los FKs nuevos para los tickets ya existentes (asociar cada
  `OperationTicket` histórico con su `ServiceOperation`/`RentalOperation`/`Shipment`
  correspondiente, vía `source_order`/`source_rental_request` que ya existen) — riesgo bajo,
  es solo lectura + UPDATE de un FK nuevo, no modifica estados.
- ⚠️ El campo `OperationTicket.status` actual no se puede eliminar de golpe (rompería cualquier
  código que lo lea) — se mantiene como columna "legacy" de solo lectura por un tiempo, o se
  convierte en `@property` calculada (ver "compatibilidad temporal mediante adaptadores",
  mencionado explícitamente en las reglas del plan).

### Opción C — Solo trazabilidad cruzada (paso mínimo, no resuelve la duplicación)
Igual que B pero sin tocar `OperationTicket.status` — solo se agregan los FKs de enlace para que
por primera vez se pueda saber qué `ServiceOperation`/`RentalOperation`/`Shipment` corresponde a
cada `OperationTicket`. El campo `status` de cada uno sigue siendo independiente y puede seguir
divergiendo.

- ✅ Esfuerzo y riesgo mínimos.
- 🔴 No resuelve el problema de fondo — solo lo hace visible/trazable.
- Útil como **primer paso técnico de la Opción B**, no como solución final.

---

## Recomendación

**Opción B**, ejecutada en 2 pasos dentro de la misma Fase 5:

1. **Paso 1 (bajo riesgo):** agregar los 3 FKs nuevos a `OperationTicket` + comando de backfill
   que los popule para los tickets existentes usando `source_order`/`source_rental_request` ya
   presentes. Cero cambio de comportamiento observable — solo trazabilidad nueva. Equivale a
   ejecutar la Opción C primero.
2. **Paso 2 (riesgo medio):** convertir `OperationTicket.status` en una propiedad calculada
   (derivada del satélite vía el mapa de traducción de estados) en vez de un campo propio
   editable, y actualizar el selector/API que sirve al tablero de Operaciones para usar el
   estado derivado. **No se toca `ServiceOperation`/`RentalOperation`/`Shipment` en ningún
   momento.**

Esto cumple las 2 reglas explícitas del usuario para esta fase: *"Mantener compatibilidad
temporal mediante adaptadores cuando sea necesario"* (el Paso 1 es exactamente ese adaptador) y
*"Todo dato tendrá un único propietario (SSoT)"* (al final del Paso 2, el estado operativo real
vive solo en el satélite de cada dominio).

---

## Antes de ejecutar el Paso 1, necesito tu confirmación de enfoque

Este es el cambio de mayor riesgo de todo el plan CORE v4 porque toca modelos con registros
activos en producción ahora mismo (técnicos asignados, rentas en tránsito). Aunque el Paso 1 es
de bajo riesgo (solo agrega trazabilidad, no cambia comportamiento), quiero tu autorización
explícita sobre el enfoque completo (B, en 2 pasos) antes de tocar el primer archivo.

---

## Paso 1 — EJECUTADO (2026-07-12)

Aprobado por el usuario ("si opcion b"). Cambios reales:

1. **`operations/models.py`**: 3 campos nuevos en `OperationTicket` —
   `service_operation` (`OneToOneField` a `technical_services.ServiceOperation`),
   `rental_operation` (`OneToOneField` a `renting.RentalOperation`), `shipment`
   (`OneToOneField` a `orders.Shipment`) — los 3 `null=True, blank=True, on_delete=SET_NULL`.
   **Ningún campo existente se modificó ni se eliminó.**
2. **Migración** `operations/migrations/0004_operationticket_rental_operation_and_more.py` —
   solo `AddField` x3, sin tocar datos.
3. **Comando de backfill** `operations/management/commands/backfill_operation_satellite_links.py`
   (con `--dry-run`), idempotente, solo lee `ServiceOperation`/`RentalOperation`/`Shipment` y
   escribe únicamente los 3 campos nuevos.
4. **Ejecutado en el ambiente real** — resultado: **2 de 9 tickets existentes se enlazaron**
   (2 SERVICE). Los 7 restantes (2 SERVICE, 3 RENTAL, 2 SHOP_DELIVERY) quedaron sin enlazar.

### Hallazgo real durante la ejecución — no es un bug, es información nueva y valiosa

**Los 7 tickets sin enlazar NO son datos corruptos ni divergencia real** — investigué cada uno:
todos están en un estado temprano del ciclo (`DOCS_PENDING`/`READY_TO_ASSIGN`), es decir, el
`OperationTicket` se crea **antes** de que exista el registro de ejecución específico
(`ServiceOperation`/`RentalOperation`/`Shipment` se crean más adelante en el flujo, al confirmar
pago/aprobar — ej. `RentalOperationCommands.ensure_for_request()` solo se dispara en
`confirm_payment`/`approve_manual_validation`). Es una **secuencia temporal esperada**, no una
inconsistencia.

**Implicación directa para el Paso 2**: la propiedad calculada de `OperationTicket.status` NO
puede asumir que el satélite siempre existe. Debe tener un *fallback* explícito: si el FK de
enlace es `None` (ticket en etapa temprana, satélite aún no creado), el estado mostrado debe
seguir viniendo del campo `status` propio del ticket (que en ese caso sigue siendo la única
fuente de verdad real, porque el satélite literalmente no existe todavía); solo cuando el FK se
puebla, el estado se deriva del satélite. Este detalle no estaba explícito en el diseño original
del Paso 2 — se agrega aquí antes de ejecutarlo.

**Verificado:** `manage.py check` limpio, comando corrido dos veces (confirmado idempotente:
segunda corrida = 0 enlaces nuevos), `manage.py test operations technical_services renting
orders` sin regresiones.

**Estado: Paso 1 completo.**

---

## Paso 2 — EJECUTADO (2026-07-12), con una corrección técnica importante al diseño original

Aprobado por el usuario ("si"). **Antes de implementar, encontré una razón real para NO hacer
lo que el diseño original decía literalmente** ("convertir `status` en propiedad calculada"):
`OperationTicketSelector` ya usa `.filter(status=...)` — convertir el campo real de BD en una
`@property` de Python habría roto esa query instantáneamente (Django no puede filtrar por un
atributo que no es un campo). Implementación real, más segura:

1. **`OperationTicket.status` NO se tocó** — sigue siendo el campo de BD real, con el mismo
   comportamiento de siempre en cualquier query/filter/admin existente.
2. **`OperationTicket.get_effective_status()`** (método nuevo, aditivo) — deriva el estado del
   satélite específico (`service_operation`/`rental_operation`/`shipment`) vía 3 mapas de
   traducción `_SERVICE_OPERATION_STATUS_MAP`/`_RENTAL_OPERATION_STATUS_MAP`/
   `_SHIPMENT_STATUS_MAP` (best-effort — cada satélite tiene su propia secuencia y
   granularidad, no hay traducción 1:1 perfecta). Si el satélite todavía no existe, cae al
   campo `status` propio.
3. **Regla de seguridad agregada durante la implementación** (no estaba en el diseño
   original): si `status` del ticket ya está en un estado terminal (`CANCELLED`/`COMPLETED`),
   ese valor tiene prioridad sobre lo que diga el satélite — nunca se deriva desde ahí.
4. **`effective_status`** expuesto como campo nuevo (aditivo) en
   `OperationTicketListSerializer`/`OperationTicketDetailSerializer`. El campo `status`
   original sigue en la respuesta sin cambios. El frontend (`OperationBoard.vue`) sigue leyendo
   `status` hasta que se conecte a `effective_status` en la Fase 6 — el tablero actual **no
   cambia visualmente todavía** con este paso.

### Hallazgo real durante la verificación — divergencia confirmada con datos reales

Al probar `get_effective_status()` contra los 9 tickets reales de este ambiente, encontré
**una divergencia real ya existente**: `OP-2026-7C215EE1` tiene `status=CANCELLED` en el
ticket, pero su `ServiceOperation` vinculado sigue en `READY_FOR_PLANNING` — nunca se
sincronizó cuando se canceló. Es exactamente el riesgo de "silent divergence" identificado como
el hallazgo crítico de la Fase 1, ahora con evidencia concreta, no solo teórica. La regla de
prioridad del punto 3 se agregó específicamente en respuesta a este caso real (sin ella,
`get_effective_status()` habría mostrado "listo para asignar" para un trabajo cancelado — peor
que el comportamiento actual).

**Verificado:** `manage.py check` limpio, `get_effective_status()` probado contra los 9 tickets
reales (resultado correcto en todos, incluido el caso de divergencia), `manage.py test
operations` 6/6 OK.

### Estado final de esta fase

**Paso 1 y Paso 2 de la Opción B completos.** El siguiente trabajo relacionado
(conectar el frontend a `effective_status`, y decidir si se ataca la divergencia real
encontrada en `OP-2026-7C215EE1`) queda para cuando se retome Fase 6 (Refactorización del
Frontend) — no se toca el frontend en esta fase por decisión explícita del plan del usuario.
