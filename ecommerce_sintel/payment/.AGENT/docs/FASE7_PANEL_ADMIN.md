# Fase 7 — Panel administrativo de pagos con acciones reales (completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** plan original del usuario, Fase 7 (dentro del bloque "Fases 6 a 10").

## Contexto (hallazgo de la Fase 0)

`PaymentTransactionsAdminView.vue` + `AdminPaymentViewSet` eran **100% de solo lectura** — solo listaban transacciones Wompi/Nequi/COD con filtro por estado. Sin ningún botón de acción, sin forma de que un admin resolviera manualmente una transacción atascada, sin visibilidad del historial de auditoría (`TransactionEvent`, Fase 4) desde la UI, y el flag de la Fase 5 (`PaymentFeatureFlags`) solo era togglable desde `/admin/` de Django, no desde el panel Vue que el equipo realmente usa día a día.

## Qué se hizo

### Backend

- **`PaymentAdminSelector`** (`payment/services/selectors.py`): `get_wompi_transaction(uuid)`, `list_transaction_events(uuid)`.
- **`PaymentAdminOrchestrator`** (`dashboard/services/admin_orchestrators.py`): `resync_wompi_transaction`, `list_transaction_events`, `get_feature_flags`, `set_card_api_flow_enabled` — siguiendo el patrón ya establecido en el mismo archivo (`NotificationAdminOrchestrator.update_template`) de delegar la mutación real a la capa de dominio (aquí: `PaymentFeatureFlags.set_card_api_flow_enabled`, un método nuevo del modelo) en vez de mutar directamente desde el orquestador.
- **`AdminPaymentViewSet`** (`dashboard/api/views.py`), 3 acciones nuevas:
  - `POST .../{uuid}/resync/` — dispara `_sync_wompi_status` bajo demanda (mismo camino que usa `/payment/result` y la tarea periódica de la Fase 6). Responde **409** con un mensaje claro si la transacción no tiene `wompi_id` (nada que consultar) en vez de fallar en silencio.
  - `GET .../{uuid}/events/` — historial `TransactionEvent` de una transacción, más reciente primero. 404 real si la transacción no existe (antes retornaba lista vacía sin distinguir "no existe" de "existe sin eventos" — corregido en el propio orquestador).
  - `GET`/`PATCH .../feature-flags/` — consulta/actualiza `PaymentFeatureFlags.card_api_flow_enabled` desde el panel, sin salir a `/admin/` de Django.
- **`TransactionSerializer`** ganó `correlation_id`; nuevo **`TransactionEventSerializer`**.

### Frontend (`PaymentTransactionsAdminView.vue`)

- Switch "Flujo de pago con tarjeta via API" arriba de las pestañas.
- Pestaña Wompi: columna **Acciones** nueva — botón **Reconciliar** (solo visible si `PENDING` + `wompi_id` conocido) y botón **Historial** (expande una fila con la tabla de `TransactionEvent`). Nequi y COD sin cambios — la Fase 0 ya documentó que esas pasarelas no tienen el mismo problema de reconciliación (Nequi tiene su propio polling; COD no pasa por gateway externo).

## Bug real encontrado y corregido durante la implementación

`request.data.get('card_api_flow_enabled')` seguido de `bool(...)` — **`bool('False')` es `True` en Python**. El formato por defecto del cliente de test de DRF (y de formularios HTML reales) es `multipart/form-data`, donde un booleano llega como el string literal `'False'`, no como un booleano JSON. El PATCH para *desactivar* el flag lo dejaba *activado*. Corregido interpretando explícitamente strings (`'false'/'0'/'no'/''` → `False`) antes de aplicar `bool()` al resto de los casos. **Lo encontró el test, no inspección manual.**

## Verificación realizada

8 tests nuevos (`payment/tests.py::PaymentAdminPanelTestCase`): resync exitoso actualiza la transacción; resync sin `wompi_id` responde 409 sin llamar a Wompi; resync de transacción inexistente responde 404; historial ordenado correctamente (más reciente primero); historial de transacción inexistente responde 404; GET/PATCH del flag (incluye el caso que reveló el bug del párrafo anterior); PATCH sin el campo responde 400; un usuario no-admin recibe 403 en las 3 acciones nuevas.

- `docker exec ecommerce_sintel_django python manage.py test payment.tests.PaymentAdminPanelTestCase` → **8/8 OK** (tras el fix del bug de parseo booleano).
- `docker exec ecommerce_sintel_django python manage.py test payment` (suite completa) → **63/63 OK**.
- `docker exec ecommerce_sintel_django python manage.py test dashboard` → **50/50 OK** (sin regresiones en el resto del panel admin).
- **Verificación real en el navegador** (Playwright, tráfico real contra el backend de desarrollo, sin mocks — nada de esto toca la API de Wompi): switch de flag con `PATCH` real confirmado y restaurado a su estado original al terminar; columna Acciones visible solo en Wompi; botón Reconciliar presente únicamente en la fila `PENDING`+`wompi_id` (verificado creando un dato de prueba desechable, **sin hacer clic en el botón** — ver nota de seguridad abajo); botón Historial funcional con `GET` real, mostrando "Sin eventos registrados" para una transacción nueva; pestañas Nequi/COD sin cambios. Cero errores de consola/red en todo el recorrido.

**Nota de seguridad operativa:** el botón "Reconciliar" del panel Vue, al igual que el resto de este proyecto de migración, **nunca se ejercitó contra la API real de Wompi** durante la verificación — dispara una llamada saliente real del backend (usa `WOMPI_PRIVATE_KEY`), y este proyecto mantiene la política de no hacer esas llamadas sin autorización explícita del usuario. Se verificó su presencia/ausencia correcta en el DOM sin interactuar con él.

## Qué NO se hizo (fuera de alcance de esta fase)

- No se agregó ninguna acción de "reintentar pago" o "forzar aprobación" — sería modificar el estado de una transacción sin que Wompi lo confirme, sale del alcance de "reconciliar" hacia "falsificar", sin pedirse explícitamente.
- No se agregó un dashboard de métricas (tasas de aprobación, tiempos) — eso no estaba en el hallazgo de la Fase 0 como parte de "panel administrativo", y el plan original lo separa en su propio punto implícito de "alertas operativas" (Fase 8).

## Siguiente paso

Me detengo aquí. Quedan del plan original: **Fase 8** (alertas operativas), **Fase 9** (pruebas E2E/carga), **Fase 10** (documentación final de `ARQUITECTURA_COMPLETA_PAYMENT.md`/`IMPLEMENTATION_SUMMARY.md`). ¿Cómo quieres continuar?
