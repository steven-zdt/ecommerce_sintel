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
| `online/api/views.py` | WompiPaymentViewSet: initialize(), webhook(), transaction_status(), confirmation() |
| `online/services/commands.py` | WompiCommands, PaymentCommands |
| `cod/services/commands.py` | CodCommands |
| `nequi/client.py`, `nequi/services/commands.py` | NequiApiClient, NequiCommands |
| `cards/views.py` | TokenizedCardViewSet (list, create, destroy, set_default) |

## Patrones obligatorios en esta app

- `amount_in_cents = int(Decimal(...) * 100)` — usar `Decimal` + `int()`, nunca `float`
- `webhook()` endpoint debe ser **AllowAny** (Wompi no envía credenciales)
- `confirm_payment()` usa `@transaction.atomic`: valida stock → actualiza orden → deduce inventario → WebSocket on_commit
- **Safety check de stock:** `_has_sufficient_stock()` debe usar `InventorySelector.get_current_stock()` de verdad — nunca dejarla como stub que retorne `True`
- Si stock insuficiente en confirmación: marcar `Transaction.status = 'ERROR'` + raise ValueError → rollback
- **Webhook idempotente:** Si llega duplicado (status ya era APPROVED), se ignora sin reprocesar
- **Firma HMAC-SHA256 del webhook: YA IMPLEMENTADA** en `_verify_wompi_event_signature()` (`online/api/views.py`)

## Flujo de estados de Transaction

```
PENDING → (Wompi procesa, via webhook o via _sync_wompi_status()) → APPROVED | DECLINED | VOIDED | ERROR
Si APPROVED → PaymentCommands.confirm_payment() → confirm_order_payment() → Order.status = 'paid'
```

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
