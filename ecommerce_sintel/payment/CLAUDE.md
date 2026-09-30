# App: payment — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md
```

## Responsabilidad de esta app

Integración con la pasarela de pagos Wompi Colombia, más los métodos COD y Nequi Push.
Inicialización de transacciones, recepción de webhooks y confirmación de pagos
(actualización de orden + deducción de inventario + notificación WebSocket).
Montada en `INSTALLED_APPS` como `'payment'` y expuesta en `/api/v1/payment/`.

## Archivos clave

| Archivo | Proposito |
|---------|-----------|
| `models.py` | Transaction, CodTransaction, NequiTransaction, **TokenizedCard** |
| `shared/commands.py` | `confirm_order_payment()`, `_deduct_inventory_for_order()` — SSoT post-pago |
| `online/api/views.py` | WompiPaymentViewSet: initialize(), webhook(), transaction_status(), confirmation(); `_sync_wompi_status()` fallback de reconciliacion |
| `online/services/commands.py` | WompiCommands (`handle_status_change()` — unica fuente de verdad de APPROVED/DECLINED/VOIDED/FAILED, usada por el webhook Y por `_sync_wompi_status`), PaymentCommands |
| `cod/services/commands.py` | CodCommands |
| `nequi/client.py`, `nequi/services/commands.py` | NequiApiClient, NequiCommands |
| `cards/views.py` | TokenizedCardViewSet (list, create, destroy, set_default) |
| `cards/urls.py` | Router para /api/v1/payment/cards/ |
| `tasks.py` | `reconcile_pending_wompi_transactions`, `notify_declined_payments_followup` (Celery beat, sembradas via migration; ver `.AGENT/docs` seccion 5.1) |

## TokenizedCard — tarjetas guardadas del cliente

Modelo en `payment/models.py` (migration 0005). Sub-modulo en `payment/cards/`.

```
GET    /api/v1/payment/cards/              — lista tarjetas del usuario
POST   /api/v1/payment/cards/             — guardar nueva tarjeta
DELETE /api/v1/payment/cards/{uuid}/      — soft-delete
POST   /api/v1/payment/cards/{uuid}/set-default/  — marcar predeterminada
```

Permiso: `IsAuthenticatedActiveUser`. Soft-delete obligatorio (nunca `.delete()` fisico).

## Patrones obligatorios en esta app

- `amount_in_cents = int(Decimal(...) * 100)` — usar `Decimal` + `int()`, nunca `float`
- `webhook()` endpoint debe ser **AllowAny** (Wompi no envía credenciales)
- `confirm_payment()` usa `@transaction.atomic`: valida stock → actualiza orden → deduce inventario → WebSocket on_commit
- **Safety check de stock:** `_has_sufficient_stock()` en `payment/shared/commands.py` y en `payment/online/services/commands.py` deben usar `InventorySelector.get_current_stock()` de verdad — **nunca** dejarlas como stub que retorne `True`/`None`, aunque sea "temporalmente" durante un refactor. Ya ocurrió una vez (ver historial en el doc de arquitectura) y dejó todos los pagos sin descuento de stock.
- Si stock insuficiente en confirmación: marcar `Transaction.status = 'ERROR'` + raise ValueError → rollback
- **Webhook idempotente:** Si llega duplicado (status ya era APPROVED), se ignora sin reprocesar
- **Firma HMAC-SHA256 del webhook: YA IMPLEMENTADA** en `_verify_wompi_event_signature()` (`online/api/views.py`). **Fail-closed** (F-01, auditoria 2026-07-24): si `WOMPI_EVENTS_SECRET` no está seteado, el webhook RECHAZA el evento (`return False`) y registra un `SecurityEvent` CRITICAL — antes retornaba `True` (fail-open), lo que permitia falsificar un "pago aprobado". `settings/production.py` ademas exige el secreto para arrancar.
- **Toda tarea Celery nueva en `tasks.py` queda cubierta por `CELERY_TASK_DEFAULT_QUEUE='default'`** (`ecommerce/settings/base.py`) — no requiere tocar nada extra. Pero si algun dia se le asigna una cola PROPIA (via `CELERY_TASK_ROUTES['payment.*']` o `queue=` explicito en el decorador), esa cola nueva debe agregarse tambien al flag `-Q` de `celery_worker` en `docker-compose.prod.yml`, o la tarea queda encolada sin worker que la procese — exactamente lo que le paso a `reconcile_pending_wompi_transactions` hasta el 2026-07-27 (ver detalle en `ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md`, seccion 16).

## Flujo de estados de Transaction

```
PENDING → (Wompi procesa, via webhook o via _sync_wompi_status()) → APPROVED | DECLINED | VOIDED | ERROR
Si APPROVED → PaymentCommands.confirm_payment() → confirm_order_payment() → Order.status = 'paid'
Si la Transaction tiene rental_request → RentalRequestCommands.confirm_payment() en vez de confirm_order_payment()
```

`confirm_order_payment()` tambien la invoca `technical_services.ServiceCommands.request_service()` **sin pasar por Wompi** cuando el total de una orden de servicio es 0 (visita diagnostica sin costo, `reference='FREE-SERVICE'`, desde 2026-09-30). No existe `Transaction` en ese caso: cualquier codigo que asuma que toda orden `paid` tiene una `Transaction` asociada debe tolerar su ausencia.

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
