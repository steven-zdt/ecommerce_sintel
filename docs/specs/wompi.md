---
app_name: wompi
layer: integration
doc_type: spec
critical_rules:
  - sha256_signature_mandatory
  - WOMPI_EVENTS_SECRET
  - idempotent_webhook
  - on_commit_notify
  - decimal_money
  - tokenized_card_soft_delete
associated_models:
  - Transaction
  - CodTransaction
  - NequiTransaction
  - TokenizedCard
cross_app_dependencies:
  - orders
  - renting
  - notifications
permissions_required:
  - AllowAny (webhook — firma verifica autenticidad)
  - IsAuthenticatedActiveUser (initialize, cards)
---

# App: wompi

## Validacion de Firma de Webhook (OBLIGATORIA)

Toda vista que reciba eventos de Wompi DEBE verificar la firma SHA256 ANTES de cualquier mutacion.

```python
import hashlib
import hmac
from django.conf import settings

def _verify_wompi_event_signature(payload: dict) -> bool:
    events_secret: str = getattr(settings, "WOMPI_EVENTS_SECRET", "")
    if not events_secret:
        return True  # solo en desarrollo

    sig_obj    = payload.get("signature", {})
    checksum   = sig_obj.get("checksum", "")
    properties = sig_obj.get("properties", [])
    timestamp  = payload.get("timestamp", "")
    data       = payload.get("data", {})

    concatenated = ""
    for prop in properties:
        value = data
        for key in prop.split("."):
            value = value.get(key, "") if isinstance(value, dict) else ""
        concatenated += str(value)

    concatenated += str(timestamp) + events_secret
    computed = hashlib.sha256(concatenated.encode("utf-8")).hexdigest()
    return hmac.compare_digest(computed, checksum)
```

### Uso en la vista de webhook:

```python
@action(detail=False, methods=["post"])
def webhook(self, request):
    if not _verify_wompi_event_signature(request.data):
        return Response({"error": "Firma invalida"}, status=400)
    # Solo aqui se procesa el evento
    WompiCommands.process_event(request.data)
    return Response({"status": "ok"})
```

## Variable de Entorno Requerida

```bash
WOMPI_EVENTS_SECRET=<secreto-de-eventos-wompi>
# Nunca WOMPI_EVENTS_KEY — el nombre correcto es WOMPI_EVENTS_SECRET
```

## TokenizedCard — Tarjetas Guardadas del Cliente

Modelo en `wompi/models.py` (migration 0005). Sub-modulo en `wompi/cards/`.

```python
class TokenizedCard(SintelBaseModel):
    user            = models.ForeignKey(AUTH_USER_MODEL, related_name='tokenized_cards')
    token_id        = models.CharField(max_length=255, unique=True)  # token Wompi.js
    masked_number   = models.CharField(max_length=20)   # ej: XXXXXXXXXXXX1234
    brand           = models.CharField(max_length=30)   # VISA, MASTERCARD, AMEX, DINERS
    exp_month       = models.CharField(max_length=2)
    exp_year        = models.CharField(max_length=4)
    cardholder_name = models.CharField(max_length=255, blank=True)
    is_default      = models.BooleanField(default=False, db_index=True)
    # SintelBaseModel: uuid, is_active, is_deleted, created_at, updated_at
```

### Endpoints de tarjetas (`/api/v1/wompi/cards/`)

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `/api/v1/wompi/cards/` | Lista tarjetas activas del usuario |
| POST | `/api/v1/wompi/cards/` | Guarda nueva tarjeta tokenizada |
| DELETE | `/api/v1/wompi/cards/{uuid}/` | Soft-delete |
| POST | `/api/v1/wompi/cards/{uuid}/set-default/` | Marca como predeterminada |

**Permiso:** `IsAuthenticatedActiveUser` en todos.

### Reglas de TokenizedCard

```python
# CORRECTO — soft-delete obligatorio
card.is_active  = False
card.is_deleted = True
card.save()

# INCORRECTO — nunca fisico
card.delete()
```

Al eliminar la tarjeta `is_default=True`, promover automaticamente la siguiente tarjeta activa:
```python
next_card = TokenizedCard.objects.filter(
    user=card.user, is_active=True, is_deleted=False
).exclude(pk=card.pk).order_by('-created_at').first()
if next_card:
    next_card.is_default = True
    next_card.save(update_fields=['is_default'])
```

## NequiTransaction: FK Dual (Order / RentalRequest)

`NequiTransaction` soporta tanto ordenes de productos como solicitudes de renta:

```python
class NequiTransaction(SintelBaseModel):
    order          = models.ForeignKey(Order, null=True, blank=True, ...)
    rental_request = models.ForeignKey(RentalRequest, null=True, blank=True, ...)
    # Solo uno de los dos puede estar presente (mutuamente excluyente)

    def check_and_update_status(self):
        # Bifurcar segun cual FK esta poblada
        if self.order_id:
            # flujo de orden de producto
        elif self.rental_request_id:
            # flujo de solicitud de renta
```

## Metodos de Pago Soportados

| Metodo | Flujo |
|---|---|
| Wompi (widget) | `initialize` -> widget.js -> webhook `TRANSACTION.UPDATED` |
| Nequi Push | `process-payment` con `phone_number` -> polling `nequi-status` |
| COD | `process-payment` -> aprobacion inmediata -> `on_commit` notificacion |

## Idempotencia del Webhook

El webhook puede recibir el mismo evento multiples veces. Doble capa de proteccion:

```python
# En WompiCommands.process_webhook_notification
previous_status = wompi_tx.status
if previous_status == "APPROVED" and new_status == "APPROVED":
    logger.info("Wompi webhook duplicado ignorado | reference=%s", reference)
    return  # capa 1: ignorar a nivel de Transaction

wompi_tx.status   = new_status
wompi_tx.wompi_id = wompi_id
wompi_tx.save(update_fields=["status", "wompi_id", "updated_at"])

if new_status == "APPROVED":
    PaymentCommands.confirm_payment(wompi_tx)
```

```python
# En payment/shared/commands.py — capa 2: idempotencia en confirm_order_payment
@transaction.atomic
def confirm_order_payment(order: Order, reference: str) -> None:
    order = Order.objects.select_for_update().get(pk=order.pk)
    if order.status == 'paid':
        return  # ya procesado — no re-descontar inventario

    order.status = 'paid'
    order.save(update_fields=['status', 'updated_at'])
    # ... deduccion inventario y notificacion
```

**Nunca llamar directamente a `Order.objects.update(status='paid')` ni a funciones de inventario fuera de `confirm_order_payment`.**
