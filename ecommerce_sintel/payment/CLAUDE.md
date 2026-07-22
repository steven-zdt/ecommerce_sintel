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
| `tasks.py` | `reconcile_pending_wompi_transactions` (Celery beat, sembrada via migration 0008, ver `.AGENT/docs` seccion 5.1) |

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
- **Firma HMAC-SHA256 del webhook: YA IMPLEMENTADA** en `_verify_wompi_event_signature()` (`online/api/views.py`). Si `WOMPI_EVENTS_SECRET` no está seteado, permite el paso con warning — asegurar que esté configurado antes de producción.

## Flujo de estados de Transaction

```
PENDING → (Wompi procesa, via webhook o via _sync_wompi_status()) → APPROVED | DECLINED | VOIDED | ERROR
Si APPROVED → PaymentCommands.confirm_payment() → confirm_order_payment() → Order.status = 'paid'
Si la Transaction tiene rental_request → RentalRequestCommands.confirm_payment() en vez de confirm_order_payment()
```

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
