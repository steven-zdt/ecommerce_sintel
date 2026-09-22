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
recordatorios/cumpleanos/vencimientos, Queue Manager con prioridades/dead-letter, 5 canales
nuevos (Firebase/APNs/Telegram/Teams/Slack/Webhooks), dashboard ejecutivo `/panel/
notificaciones` con metricas/SLA, `TemplateEditor`/`CampaignBuilder`/`QueueMonitor` y el resto de
componentes Vue, migracion de los 2 bypasses de email existentes.

> **[CORREGIDO 2026-08-05, auditoria transversal]** SMS **ya no esta fuera de alcance** --
> `send_sms_notification_task` + `clients/sms.py::SmsClient` + `CHANNEL_SMS` ya existen y
> funcionan en el codigo (ver tabla de canales arriba), contradiciendo esta afirmacion. No se
> investigo en esta auditoria si el canal esta activo en produccion (requiere config real del
> proveedor de SMS) ni cuando se agrego -- solo se confirma que la infraestructura de codigo ya
> no es "0 canales nuevos ademas de los 3 originales" como decia esta seccion.

## Responsabilidad

Sistema centralizado de notificaciones multicanal (WebSocket, Email, WhatsApp).
Es el punto de entrada unico para TODA notificacion del sistema. Las demas apps
no envian notificaciones directamente — siempre delegan a `dispatch_notification`.

---

## Estructura de Directorios

*(Sincronizado 2026-07-31 contra el arbol real — ver auditoria de WhatsApp de esa fecha, el
arbol anterior tenia nombres de archivo que nunca existieron asi.)*

```
notifications/
├── models.py              # NotificationTemplate, NotificationLog, UserNotificationPreference
├── api/
│   ├── views.py             # (solo admin — listar logs, reintentar)
│   ├── serializers.py
│   └── whatsapp_webhook.py  # WhatsAppInboundWebhookView (GET verify + POST eventos entrantes)
├── services/
│   ├── commands.py        # NotificationCommands.dispatch_notification()/dispatch_notification_once()
│   └── selectors.py       # NotificationSelector
├── clients/
│   ├── whatsapp.py        # WhatsAppClient — Meta Cloud API HTTP client (transaccional, v20.0)
│   └── sms.py             # cliente SMS
└── tasks.py                # Celery: send_ws_notification_task, send_email_notification_task,
                             # send_whatsapp_notification_task, process_whatsapp_inbound_task,
                             # ai_proactive_room_message_task, send_sms_notification_task,
                             # send_whatsapp_agent_reply_task [agregados aqui 2026-08-05,
                             # auditoria transversal -- ya existian en el codigo, no en este arbol]
```

No existe `clients/email_client.py` — el envio de email usa `django.core.mail.send_mail` directo
desde `tasks.py`, sin wrapper propio (a diferencia de WhatsApp/SMS, que si necesitan un cliente HTTP
dedicado porque hablan con una API externa, no con SMTP via la libreria estandar de Django).

**Nota sobre el canal WhatsApp (auditoria 2026-07-31)**: el flujo saliente (`dispatch_notification`
→ `send_whatsapp_notification_task` → `WhatsAppClient.send_template()`) y el flujo entrante
(`whatsapp_webhook.py` → `process_whatsapp_inbound_task` → `support.services.ai_bridge.ask_ai()` →
AI Engine, microservicio FastAPI separado en el repo hermano `ai_engine/`) estan **implementados y
verificados end-to-end en desarrollo**, incluyendo verificacion de firma HMAC fail-closed y
deduplicacion por `message.id` (evita reprocesar reintentos de Meta). Lo que falta es puramente
configuracion/negocio, no codigo: credenciales reales de Meta en `.env.production` (hoy vacias),
registrar el webhook en Meta Business Manager, decidir si el stack de IA (`sintel_ai`/Ollama/
ChromaDB, excluido a proposito de `docker-compose.prod.yml`) se despliega a produccion, y poblar
`whatsapp_template_name` en los `NotificationTemplate` de negocio que hoy lo tienen vacio (solo uno,
`service_status_updated`, lo tiene poblado). Existe tambien un segundo cliente HTTP hacia Meta,
independiente de este (`marketing/channels/whatsapp_channel.py::WhatsAppChannelAdapter`, v20.0
tras la unificacion de version del 2026-07-31, para campañas masivas) — es una decision de diseño
documentada, no un descuido, ver `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`.

**Tercer punto de contacto con WhatsApp, NO relacionado con `dispatch_notification` (2026-07-31)**:
`CommunicationCenter.vue` (portal cliente, ver `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md`
§5.1) es un widget flotante que abre `https://wa.me/<numero>?text=...` **directo desde el navegador
del cliente** — no pasa por `dispatch_notification()`, `WhatsAppClient`, ni por Meta Cloud API en
absoluto. Es un simple deep-link (como un `mailto:` o `tel:`), sin backend involucrado en el envio
del mensaje en si. La unica pieza de backend que este widget toca es
`organization/api/views.py::CommunicationEventViewSet` (telemetria de uso: apertura de panel/clic en
canal), no `notifications`. No confundir los 3 puntos: (1) `dispatch_notification` = mensajes
transaccionales salientes automaticos del sistema via API de Meta, (2) `marketing`
`WhatsAppChannelAdapter` = campañas masivas via API de Meta, (3) `CommunicationCenter` = el cliente
inicia una conversacion manual via deep-link, ningun mensaje sale de nuestros servidores.

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

> **[CORREGIDO 2026-08-05, auditoria transversal]** faltaban 2 tareas que ya existen en
> `tasks.py` y no estaban en esta tabla ni en el arbol de directorios de arriba:
> `send_sms_notification_task` (canal SMS -- ver nota debajo, contradice la seccion "Fuera de
> esta entrega") y `send_whatsapp_agent_reply_task` (Fase 16, bridge de respuesta humana por
> WhatsApp cuando un ticket escala, `AUDITORIA/30_AUDITORIA_PRUEBAS_E2E.md`, 2026-08-03).

| Canal | Cola Celery | Tarea | Reintentos |
|---|---|---|---|
| WebSocket | `notifications` | `send_ws_notification_task` | 3x |
| Email | `notifications` | `send_email_notification_task` | 3x |
| WhatsApp | `notifications` | `send_whatsapp_notification_task` | 3x transitorios / 0x auth error |
| SMS | `notifications` | `send_sms_notification_task` (`CHANNEL_SMS`, `clients/sms.py::SmsClient`) | manejo de `SmsApiError`/`SmsConfigError`/`SmsBridgeUnreachableError`, ver codigo |
| WhatsApp (respuesta de agente humano) | `notifications` | `send_whatsapp_agent_reply_task(user_id, text)` | fallo no bloqueante (ventana de 24h de Meta) |

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

## Plantillas en BD (18 slugs)

> **[CORREGIDO 2026-08-01, Fase 3 de AUDITORIA/17_AUDITORIA_SYNC_DOCUMENTAL_CROSSMODULO.md]**
> Esta tabla documentaba un slug ficticio (`support_new_message`, nunca existio en ninguna
> migracion/seed/caller real) en vez del real que `support` si dispara
> (`ticket_soporte_sin_seguimiento`), y le faltaban los otros 4 slugs sembrados por las
> migraciones `0004`/`0005` (Fase 11 Proactividad + cross-sell). Conteo real (en ese momento): 13.
>
> **[CORREGIDO 2026-08-05, auditoria transversal]** Faltaban los 5 slugs de `kyc`
> (sembrados por `kyc/migrations/0002_seed_notification_templates.py`, disparados desde
> `kyc/services/commands.py`) — `kyc` no estaba listado entre las apps caller pese a que la
> propia introduccion de este documento afirma "11 apps, ~30 call-sites". Conteo real: 18.

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
| `cotizacion_sin_respuesta` | Cotizacion sin respuesta (Fase 11 Proactividad) | `quotes` (Event Bus proactivo) |
| `renting_por_vencer` | Renting por vencer (Fase 11 Proactividad) | `renting` (Event Bus proactivo) |
| `pago_rechazado_seguimiento` | Pago rechazado - seguimiento (Fase 11 Proactividad) | `payment` (Event Bus proactivo) |
| `ticket_soporte_sin_seguimiento` | Ticket de soporte escalado a humano sin actividad hace mas de 2h (Fase 11 Proactividad) | `support/tasks.py::notify_unattended_escalated_tickets` (via `dispatch_notification_once`, cron horaria Celery Beat) |
| `cliente_recurrente_cross_sell` | Cliente recurrente, recomendacion cross-sell | migracion `0005_seed_cross_sell_template.py` |
| `kyc_submitted_for_review` | Verificacion KYC enviada a revision | `kyc/services/commands.py:176` |
| `kyc_approved` | Verificacion KYC aprobada (2 call sites: aprobacion directa y post-validacion) | `kyc/services/commands.py:207,263` |
| `kyc_rejected` | Verificacion KYC rechazada | `kyc/services/commands.py:368` |
| `kyc_info_requested` | KYC: se solicito informacion adicional al usuario | `kyc/services/commands.py:390` |
| `kyc_blocked` | Verificacion KYC bloqueada | `kyc/services/commands.py:426` |

**Regla:** Si agregas un nuevo evento de negocio, PRIMERO crear el `NotificationTemplate`
en BD (con seeddata o fixture) y LUEGO llamar `dispatch_notification` con su slug.
Nunca usar un slug que no tenga plantilla activa en BD.

### `dispatch_notification_once` — variante idempotente para scanners periodicos

A diferencia de `dispatch_notification()` (tabla de parametros arriba), esta variante la usan
tareas Celery Beat que detectan la MISMA condicion en cada corrida (ej. "sala de soporte escalada
sin seguimiento") y no deben renotificar la misma entidad dos veces:

```python
NotificationCommands.dispatch_notification_once(
    user: User, template_slug: str, context: dict, dedupe_key: str,
) -> bool  # True si notifico, False si ya se habia notificado antes bajo esa dedupe_key
```

El marcador de dedupe se crea de forma SINCRONA (un `NotificationLog` con `channel=''`,
`payload_context__dedupe_key=dedupe_key`) antes de llamar a `dispatch_notification()` — no
depende de que un canal async ya haya corrido, evitando una ventana de carrera si dos corridas
del scan se solapan. Unico consumidor real hoy: `support/tasks.py::notify_unattended_escalated_tickets`.

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

### 2026-09-22 — Migración WhatsApp Web Session → Baileys (Fases 1-24): Event Bus + tarea de inbound
- **Qué cambió**: nuevo receptor `notifications/api/whatsapp_gateway_webhook.py::WhatsAppGatewayEventView`
  (`POST /api/v1/notifications/whatsapp-gateway-events/`, auth por `X-Gateway-Token` contra
  `settings.WHATSAPP_GATEWAY_TOKEN`, fail-closed) — recibe los 6 eventos normalizados del gateway
  Baileys (`whatsapp_gateway/`, Node/TypeScript, fuera de este repo Django). Nueva tarea Celery
  `notifications.tasks.process_whatsapp_gateway_inbound_task` (equivalente de
  `process_whatsapp_inbound_task` para este canal, sin el bookkeeping de `MetaWebhookEvent` que no
  aplica aquí).
- **Por qué**: Fase 6/8 del plan (`PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md`) — el gateway
  es transporte puro, Django sigue siendo el único que decide identidad/ChatRoom/IA
  (`whatsapp.domain.service.WhatsAppService`, sin cambios, compartido con el canal Meta).
- **Archivos afectados**: `notifications/api/whatsapp_gateway_webhook.py` (nuevo),
  `notifications/api/urls.py` (+1 ruta), `notifications/tasks.py` (+1 tarea, nada existente tocado),
  `ecommerce/settings/base.py` (+`WHATSAPP_GATEWAY_TOKEN`/`WHATSAPP_GATEWAY_URL`/`WHATSAPP_GATEWAY_ENABLED`).
- **Contratos**: eventos `whatsapp.connection.status/qr/logged_out`, `whatsapp.message.received/sent/failed`
  — ver `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md` seccion "Contrato HTTP" y `whatsapp_gateway/src/types.ts`.
- **Regla dura, verificada con test dedicado**: `message.received` solo se encola si
  `settings.WHATSAPP_CONNECTION_TYPE == 'QR_WEB_SESSION'` -- si no, se audita/deduplica pero NO se
  procesa, para no responder por el adapter equivocado (Meta) a un mensaje que llegó por Baileys.
- **Seguridad**: fail-closed sin `WHATSAPP_GATEWAY_TOKEN`; no se creó ningún modelo nuevo para
  persistir estos eventos (logs estructurados son la auditoría, Fase 31 prohíbe inventar modelos
  sin necesidad real).
- **Tests**: `notifications/test_whatsapp_gateway.py` (nuevo archivo, auth/dedupe/guard de
  `WHATSAPP_CONNECTION_TYPE`/gate de `ai_paused`) + `whatsapp/tests/test_gateway_client.py`
  (incluye regresión del bug real de `Content-Type` en POSTs sin body). Verificado también en vivo
  con Celery real y curl contra el servidor de desarrollo antes de escribir estos tests.
- Ver `AUDITORIA/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md` y `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md`
  para el resto de la migración.

### 2026-08-31 — Fundacion integracion Meta Business (FASE 1-3 + 6)

Ver `Documentacion/Arquitectura_general/META_BUSINESS_INTEGRATION_MASTER_PLAN.md`.

- **`clients/whatsapp.py` es ahora un shim.** El transporte HTTP hacia
  `graph.facebook.com` se movio a `marketing/integrations/meta/` (`MetaGraphClient`
  + `MetaWhatsAppClient`). `WhatsAppClient` es `class WhatsAppClient(MetaWhatsAppClient)`;
  `WhatsAppApiError`/`WhatsAppAuthError`/`WhatsAppConfigError` son alias de
  `MetaApiError`/`MetaAuthError`/`MetaConfigError`. Nombre de clase, modulo y API
  publica (`send_template`/`send_text` -> message_id) intactos. Nueva dependencia:
  `notifications` importa de `marketing.integrations.meta` (aprobado por el usuario).
- **Modelo `MetaWebhookEvent`** (migracion `0008`): auditoria de cada evento del
  webhook de Meta -- una fila por mensaje/estado, incluidos los rechazados por firma
  (`status=REJECTED`, 403) y los reintentos de Meta (`status=DUPLICATE`). Ciclo de
  vida: `RECEIVED -> PROCESSING -> PROCESSED | FAILED | DUPLICATE | REJECTED`.
  `payload_hash` = sha256 del body crudo. Admin de solo lectura.
- **`api/whatsapp_webhook.py`**: la firma se verifica con
  `marketing.integrations.meta.signatures.verify_meta_webhook_signature` (funcion
  pura, misma logica fail-closed); ademas de `messages` ahora tambien persiste los
  callbacks `statuses` (delivered/read/failed). Sigue: challenge, firma, dedupe
  Redis `cache.add`, 200 rapido, `.delay()`. Cero logica de negocio, cero IA.
- **`tasks.py::process_whatsapp_inbound_task(..., event_id=None)`**: helper
  `_mark_meta_webhook_event()` avanza el `MetaWebhookEvent` (`PROCESSED` con
  `error_code` de contexto en salidas benignas -- `no_user_for_number`,
  `handoff_active`, `ai_rate_limited`, `ai_empty_response`; `FAILED` +
  `retry_count++` en fallo de `ask_ai`; `FAILED` en fallo de envio). `event_id`
  es opcional -- las llamadas directas/tests sin el siguen funcionando.
- **`tasks.py::purge_meta_webhook_events_task`** (FASE 6.1, seed
  `0009_seed_purge_meta_webhook_events_task.py`): PeriodicTask diaria (03:30,
  cola `notifications`). `payload` sanitizado a `{}` a los 30 dias; fila borrada
  a los 180. El `payload` de los mensajes entrantes contiene texto del cliente
  -- misma clase de dato que `ChatMessage`.

### 2026-06-27 — Template order_cod_confirmed documentado
- Agregado a la tabla de plantillas con `ws_group='admin'` (notifica al panel, no al cliente).
- Caller: `payment/cod/services/commands.py CodCommands.confirm_order`.
- Contexto: `{order_uuid, user_email, total, user_name}`.
