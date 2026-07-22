# ARQUITECTURA COMPLETA — APP notifications

Ultima actualizacion: 2026-07-09 (Nucleo real del Centro de Comunicaciones, Fase 1)

## Fase 1 -- Nucleo real del "Centro de Comunicaciones" (2026-07-09)

Brief de 29 fases evaluado; auditoria (3 agentes Explore) confirmo que el patron central
(`dispatch_notification`) ya es solido -- 11 apps, ~30 call-sites, sin bypass de WS/WhatsApp.
2 bypasses de email conocidos y aceptados (`quotes/tasks.py` adjunta PDF, `users/services/
commands.py` codigo OTP) -- documentados, no migrados. El "Campaign Engine" del brief (Fase 8)
ya existe maduro en `marketing.MarketingCampaign` -- no se duplico.

Se implemento:
- **Fix real de auditoria**: `NotificationLog` gano `template_slug` (poblado SIEMPRE, incluso si
  `template` es `None` por un slug roto/inactivo). Antes, `dispatch_notification()` solo hacia
  `logger.warning(...)` sin dejar NINGUN rastro en BD -- ahora crea un `NotificationLog(
  status=FAILED)`. Migracion de backfill (`0003_backfill_template_slug.py`) poblo los 393 logs
  historicos que ya tenian `template` pero no el nuevo campo.
- **Bug real encontrado y corregido durante la verificacion**: `NotificationLogSerializer.
  template_slug` usaba `source='template.slug'` -- rompia con `AttributeError` (500) al listar
  logs que incluyeran una de las nuevas filas con `template=None`. Corregido usando el campo
  del modelo directamente.
- **Integracion con Security Center**: `SecurityEvent.NOTIFICATION_CHANNEL_FAILED` (CRITICAL) se
  emite desde `send_whatsapp_notification_task` cuando el error es de configuracion/auth
  permanente (`WhatsAppAuthError`/`WhatsAppConfigError`, ya distinguido de errores transitorios).
- **Comando `python manage.py audit_notifications`**: escanea bypasses reales (`send_mail`,
  `EmailMessage`, `channel_layer.group_send`, `WhatsAppClient`) fuera de `notifications`/
  `marketing`, con un allowlist explicito de 4 excepciones documentadas (los 2 bypasses de
  email conocidos + `ecommerce/ws_notify.py` que es el primitivo de bajo nivel que el propio
  patron ya envuelve + `support/consumers.py` que entrega el contenido del chat en tiempo real,
  no un aviso sobre otro evento). Tambien reporta plantillas inactivas y slugs rotos recientes.
- **Frontend cliente**: `/mi-cuenta/notificaciones` conecta la UI real a
  `UserNotificationPreferenceViewSet`, que YA EXISTIA sin ninguna vista.
- **Frontend admin**: el bell del navbar (`Navbar.vue`) mostraba "Sin novedades" hardcodeado sin
  backend -- ahora usa `store/notifications.js` (Pinia) contra `GET notifications/logs/`, mismo
  modelo de datos que el cliente (log personal, no un feed de negocio aparte).

**Explicitamente fuera de esta entrega**: Campaign Engine nuevo, Automation Engine, Scheduler de
recordatorios/cumpleanos/vencimientos, Queue Manager con prioridades/dead-letter, 6 canales
nuevos (SMS/Firebase/APNs/Telegram/Teams/Slack/Webhooks), dashboard ejecutivo `/panel/
notificaciones` con metricas/SLA, `TemplateEditor`/`CampaignBuilder`/`QueueMonitor` y el resto de
componentes Vue, migracion de los 2 bypasses de email existentes.

## Responsabilidad

Sistema centralizado de notificaciones multicanal (WebSocket, Email, WhatsApp).
Es el punto de entrada unico para TODA notificacion del sistema. Las demas apps
no envian notificaciones directamente — siempre delegan a `dispatch_notification`.

---

## Estructura de Directorios

```
notifications/
├── models.py              # NotificationTemplate, NotificationLog
├── api/
│   └── views.py           # (solo admin — listar logs, reintentar)
├── services/
│   ├── commands.py        # NotificationCommands.dispatch_notification()
│   └── selectors.py       # NotificationSelector
├── clients/
│   ├── email_client.py    # Django send_mail wrapper
│   └── whatsapp_client.py # Meta Cloud API HTTP client
└── tasks.py               # Celery: send_ws_task, send_email_task, send_whatsapp_task
```

---

## Modelos

### NotificationTemplate

```python
class NotificationTemplate(SintelBaseModel):
    slug                   = SlugField(max_length=100, unique=True)
    name                   = CharField(max_length=255)
    # Email
    subject                = CharField(max_length=255, blank=True)
    email_body             = TextField(blank=True)   # Django template: {{ order_uuid }}
    # WhatsApp (Meta Cloud API)
    whatsapp_template_name = CharField(max_length=255, blank=True)
    # WebSocket
    ws_event_type          = CharField(max_length=100, blank=True)
    is_active              = BooleanField(default=True)
```

- `slug`: contrato entre el caller y este sistema. Nunca cambiar sin migrar todos los callers.
- Canal deshabilitado = campo vacio para ese canal.

### NotificationLog

```python
class NotificationLog(SintelBaseModel):
    STATUS_PENDING = 'pending'
    STATUS_SENT    = 'sent'
    STATUS_FAILED  = 'failed'

    user            = ForeignKey(User)
    template        = ForeignKey(NotificationTemplate)
    channel         = CharField()   # EMAIL | WEB_SOCKET | WHATSAPP
    status          = CharField(default='pending')
    payload_context = JSONField(default=dict)
    error_message   = TextField(blank=True)
    sent_at         = DateTimeField(null=True)
```

---

## Patron de Uso (Obligatorio)

```python
from notifications.services.commands import NotificationCommands

# SIEMPRE dentro de transaction.on_commit
_user = order.user
_ctx  = {
    'order_uuid': str(order.uuid),
    'status':     'paid',
    'total':      str(order.total_amount),
    'user_name':  _user.get_short_name(),
}
transaction.on_commit(
    lambda: NotificationCommands.dispatch_notification(
        user=_user,
        template_slug='order_paid',
        context=_ctx,
        ws_group=f'user_{_user.uuid}',
        phone=getattr(getattr(_user, 'profile', None), 'phone', None),
    )
)
```

### Parametros de dispatch_notification

| Parametro | Tipo | Descripcion |
|---|---|---|
| `user` | User | Destinatario |
| `template_slug` | str | Slug del NotificationTemplate en BD |
| `context` | dict | Variables para el template (email body, ws payload) |
| `ws_group` | str | Grupo de canal WebSocket |
| `phone` | str o None | Numero para WhatsApp (opcional) |

---

## Canales y Tareas Celery

| Canal | Cola Celery | Tarea | Reintentos |
|---|---|---|---|
| WebSocket | `notifications` | `send_ws_notification_task` | 3x |
| Email | `notifications` | `send_email_notification_task` | 3x |
| WhatsApp | `notifications` | `send_whatsapp_notification_task` | 3x transitorios / 0x auth error |

### WhatsAppAuthError — Sin reintento

```python
# En tasks.py
except WhatsAppAuthError:
    log.status = 'failed'
    log.save()
    logger.critical('WhatsApp auth fallida — Revisa META_ACCESS_TOKEN')
    # NO self.retry() — error permanente de credencial
```

---

## Plantillas en BD (9 slugs)

| slug | Evento | Caller |
|---|---|---|
| `order_created` | Nueva orden creada | `orders/services/commands.py` |
| `order_paid` | Pago online confirmado | `payment/shared/commands.py` |
| `order_cod_confirmed` | Orden COD confirmada | `payment/cod/services/commands.py` |
| `order_shipped` | Pedido despachado | pendiente |
| `rental_payment_confirmed` | Alquiler confirmado (pago online aprobado), incluye `ticket_number` | `renting/services/commands.py::confirm_payment` |
| `rental_cod_confirmed` | Alquiler confirmado (COD aprobado por admin), incluye `ticket_number` | `renting/services/commands.py::approve_manual_validation` |
| `service_request_created` | Solicitud de servicio tecnico | `technical_services` |
| `service_assigned` | Tecnico asignado | `technical_services` |
| `support_new_message` | Mensaje de soporte | `support` |

**Regla:** Si agregas un nuevo evento de negocio, PRIMERO crear el `NotificationTemplate`
en BD (con seeddata o fixture) y LUEGO llamar `dispatch_notification` con su slug.
Nunca usar un slug que no tenga plantilla activa en BD.

---

## Variables de Entorno Requeridas

| Variable | Uso |
|---|---|
| `META_ACCESS_TOKEN` | Bearer token para WhatsApp Cloud API |
| `META_PHONE_NUMBER_ID` | ID del numero de telefono en Meta |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP |

---

## Anti-Patrones Prohibidos

```python
# INCORRECTO — notificar directamente sin on_commit
NotificationCommands.dispatch_notification(...)  # puede ejecutarse antes del commit DB

# INCORRECTO — usar ws_notify directamente en lugar de dispatch_notification
from ecommerce.ws_notify import ws_notify
ws_notify(...)  # no registra NotificationLog, no envia email/whatsapp

# INCORRECTO — slug inventado
dispatch_notification(template_slug='order_finished')  # si no existe en BD: silencia el error
```

---

## Cambios Recientes

### 2026-06-27 — Template order_cod_confirmed documentado
- Agregado a la tabla de plantillas con `ws_group='admin'` (notifica al panel, no al cliente).
- Caller: `payment/cod/services/commands.py CodCommands.confirm_order`.
- Contexto: `{order_uuid, user_email, total, user_name}`.
