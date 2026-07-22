# Fase 6 — Reconciliación automática mejorada (completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** plan original del usuario, Fase 6 (dentro del bloque "Fases 6 a 10"). Se ejecutó como fase propia porque es la única de ese bloque que tiene entregable técnico claro y aislado; el resto (panel admin, alertas, pruebas E2E, docs finales) queda para las siguientes fases.

## Contexto (hallazgo de la Fase 0, sin resolver hasta ahora)

`reconcile_pending_wompi_transactions` solo alcanza transacciones que **ya tienen `wompi_id`** — Wompi no ofrece un endpoint de búsqueda por `reference`, así que una transacción que nunca recibió webhook **y** cuyo usuario nunca volvió a `/payment/result` quedaba `PENDING` para siempre, sin ningún rastro visible, sin ninguna forma de que un admin la encontrara. Además, cuando la reconciliación SÍ intentaba consultar Wompi y fallaba (timeout, 5xx), el único rastro era una línea de log de texto — invisible una vez rotan los logs.

## Qué se hizo

### 1. Fallos de sincronización ahora dejan `TransactionEvent`

`_sync_wompi_status()` (`payment/online/api/views.py`) — las dos ramas de error que antes solo hacían `logger.warning(...)` ahora **también** escriben un `TransactionEvent(source=API_SYNC, processed=False, error_detail=...)`:
- Wompi responde algo distinto a 200.
- Cualquier excepción (timeout, error de red, JSON inválido).

Esto usa la infraestructura de la Fase 4 (`TransactionEvent`, `correlation_id`) — un intento de reconciliación fallido ahora queda en el historial de auditoría de la transacción, no solo en un log de texto que rota.

### 2. Transacciones abandonadas (sin `wompi_id`) ahora quedan marcadas, no invisibles

`reconcile_pending_wompi_transactions()` (`payment/tasks.py`) ahora hace una **segunda pasada** en cada corrida (cada 5 minutos, sin cambiar el intervalo): busca `Transaction` `PENDING`, sin `wompi_id`, con más de **30 minutos** de antigüedad (umbral nuevo, deliberadamente generoso para no marcar transacciones que un usuario normal completaría en minutos), y que **no tengan ya** un evento de este tipo — y les crea un `TransactionEvent(processed=False, error_detail="Transaccion abandonada: ...")`.

Puntos de diseño deliberados (siguiendo el ADR §7):
- **`Transaction.status` nunca se toca** — sigue siendo `PENDING`, fiel al último estado real conocido de Wompi. No se inventa un estado nuevo tipo `ABANDONED`/`EXPIRED` (misma lección ya aprendida en 2026-07-07: Wompi no tiene esos estados).
- **No se re-marca en cada corrida** — una vez que una transacción tiene su evento de "abandonada", las corridas siguientes la excluyen (`exclude(events__source=..., events__error_detail__icontains=...)`), evitando que la tabla de eventos crezca sin límite para la misma transacción estancada.
- **Efecto reducido para el flujo nuevo:** desde la Fase 2, cualquier transacción creada vía el flujo backend-directo (tarjeta, `card_token`/`payment_source_id`) obtiene su `wompi_id` **de inmediato** (creación síncrona) — este problema estructuralmente ya casi no le aplica a ese camino. El hueco real que esta fase cierra es principalmente para el camino PSE/Widget (que sigue sin cambios de flujo, por diseño), donde `wompi_id` solo llega por webhook o por una visita a `/payment/result`.

## Verificación realizada

5 tests nuevos (`payment/tests.py::WompiReconciliationObservabilityTestCase`): fallo no-200 de Wompi escribe evento; excepción de red escribe evento; transacción abandonada (45 min, sin `wompi_id`) se marca correctamente sin cambiar su `status`; una segunda corrida del task **no** duplica el evento para la misma transacción; una transacción reciente sin `wompi_id` (el caso normal de "todavía en curso") **no** se marca.

- `docker exec ecommerce_sintel_django python manage.py test payment.tests.WompiReconciliationObservabilityTestCase` → **5/5 OK**.
- `docker exec ecommerce_sintel_django python manage.py test payment` (suite completa) → **55/55 OK** (50 anteriores + 5 nuevos).

## Qué NO se hizo (a propósito, fuera de alcance de esta fase específica)

- **No se agregó notificación al cliente** para transacciones abandonadas — no sabemos con certeza si el pago se completó o no del lado de Wompi (esa es justo la razón por la que están "abandonadas"), así que notificar "tu pago falló, intenta de nuevo" podría inducir un doble cobro si el cliente sí pagó. Sin evidencia suficiente para actuar automáticamente aquí.
- **No se construyó ninguna UI de admin** para ver estas transacciones marcadas — eso es explícitamente la Fase 7 del plan original ("panel administrativo de pagos"), que hoy sigue siendo de solo lectura (hallazgo de la Fase 0). El `TransactionEvent` ya queda accesible por Django Admin (`TransactionEventAdmin`, agregado en la Fase 5) mientras tanto.

## Siguiente paso

Me detengo aquí. Quedan del plan original: **Fase 7** (panel administrativo de pagos con acciones reales), **Fase 8** (alertas operativas), **Fase 9** (pruebas E2E/carga), **Fase 10** (documentación final de `ARQUITECTURA_COMPLETA_PAYMENT.md`/`IMPLEMENTATION_SUMMARY.md`). ¿Cómo quieres continuar?
