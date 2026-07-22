---
app_name: notifications
layer: service_layer
doc_type: spec
critical_rules:
  - on_commit_dispatch
  - WhatsAppAuthError_no_retry
  - dispatch_notification_pattern
associated_models:
  - NotificationTemplate
  - NotificationLog
cross_app_dependencies:
  - users
  - orders
  - renting
  - technical_services
  - support
permissions_required: []
---

# App: notifications

## Dispatch Central: NotificationCommands.dispatch_notification

Es el punto de entrada UNICO para todas las notificaciones del sistema.

```python
# CORRECTO — siempre dentro de transaction.on_commit
transaction.on_commit(
    lambda: NotificationCommands.dispatch_notification(
        user=user_obj,
        template_slug='order_created',    # slug del NotificationTemplate en BD
        context={'order_uuid': str(order.uuid), 'total': str(order.total_amount)},
        ws_group=f'user_{user_obj.uuid}', # grupo WebSocket
        phone=user_obj.phone,             # para WhatsApp (opcional)
    )
)

# INCORRECTO — llamar directamente sin on_commit
NotificationCommands.dispatch_notification(...)  # puede ejecutarse antes del commit
```

## Canales Disponibles

| Canal | Tarea Celery | Cola | Retry |
|---|---|---|---|
| WebSocket | `send_ws_notification_task` | `notifications` | Hasta 3x |
| Email | `send_email_notification_task` | `notifications` | Hasta 3x |
| WhatsApp | `send_whatsapp_notification_task` | `notifications` | 3x para errores transitorios; 0x para auth errors |

## Manejo de Errores WhatsApp

```python
# WhatsAppAuthError: error de credencial permanente — NO reintentar
class WhatsAppAuthError(WhatsAppApiError):
    """Token invalido o expirado (401/403). No tiene sentido reintentar."""
    pass

# En tasks.py:
except WhatsAppAuthError as exc:
    log.status = NotificationLog.STATUS_FAILED
    log.save(update_fields=['status', 'error_message'])
    logger.critical('WhatsApp auth fallida — Revisa META_ACCESS_TOKEN en .env')
    # NO llamar self.retry() — error permanente

except WhatsAppApiError as exc:
    log.status = NotificationLog.STATUS_FAILED
    log.save(update_fields=['status', 'error_message'])
    raise self.retry(exc=exc)   # error transitorio — reintentar
```

## NotificationTemplate (9 plantillas en BD)

| slug | Evento | Caller |
|---|---|---|
| `order_created` | Nueva orden de compra creada | `orders/services/commands.py` `create_from_cart` |
| `order_paid` | Pago online confirmado (Wompi / Nequi) | `payment/shared/commands.py` `confirm_order_payment` |
| `order_cod_confirmed` | Orden COD confirmada | `payment/cod/services/commands.py` `CodCommands.confirm_order` |
| `order_shipped` | Pedido despachado | pendiente de implementar |
| `rental_order_created` | Nueva solicitud de renta | `renting` |
| `rental_confirmed` | Renta confirmada | `renting` |
| `service_request_created` | Nueva solicitud de servicio tecnico | `technical_services` |
| `service_assigned` | Tecnico asignado al servicio | `technical_services` |
| `support_new_message` | Nuevo mensaje en chat de soporte | `support` |

### Contexto de order_cod_confirmed

```python
{
    'order_uuid': str(order.uuid),
    'user_email': user.email,
    'total':      str(order.total_amount),
    'user_name':  user.get_short_name(),
}
```
`ws_group='admin'` — se notifica al panel admin, no al cliente.

## NotificationLog: Auditoria

Cada intento de notificacion crea un `NotificationLog`:

```python
class NotificationLog(SintelBaseModel):
    STATUS_PENDING = 'pending'
    STATUS_SENT    = 'sent'
    STATUS_FAILED  = 'failed'

    user            = models.ForeignKey(User, ...)
    template        = models.ForeignKey(NotificationTemplate, ...)
    channel         = models.CharField()   # WS | EMAIL | WHATSAPP
    status          = models.CharField(choices=STATUS_CHOICES, default='pending')
    payload_context = models.JSONField(default=dict)
    error_message   = models.TextField(blank=True)
    sent_at         = models.DateTimeField(null=True)
```
