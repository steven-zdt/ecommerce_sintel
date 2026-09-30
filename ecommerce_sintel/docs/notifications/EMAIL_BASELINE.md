# EMAIL_BASELINE — Auditoria Forense de Email (FASE 0-1 de PLAN_AUDITORIA_EMAIL_PRODUCCION_SINTEL_LOOP.md)

**Fecha:** 2026-09-23
**Metodo:** lectura de codigo real + verificacion en runtime contra el contenedor de DESARROLLO
(`ecommerce_sintel_django`, solo lectura) — CERO acceso a `sintel_prod_*` en esta fase, por diseno
del plan (FASE 0-1 es descubrimiento, no pruebas de produccion). Cualquier hallazgo marcado
"pendiente de verificar en prod" requiere una fase posterior con acceso explicito autorizado.

---

## 1. Servicio central — `notifications`

Arquitectura confirmada contra codigo real (coincide con `notifications/.AGENT/docs/
ARQUITECTURA_COMPLETA_NOTIFICATIONS.md`, que ya documentaba esto con precision):

- `NotificationCommands.dispatch_notification(user, template_slug, context, ws_group=None)`
  (`notifications/services/commands.py:74-203`) — resuelve `NotificationTemplate` por
  `slug`+`is_active=True`; si no existe, crea `NotificationLog(status=FAILED, template=None)` y
  retorna sin lanzar excepcion (fallo silencioso a nivel de excepcion Python, pero SI queda
  trazado en BD). Despacha una tarea Celery independiente por canal habilitado
  (`send_email_notification_task`, `send_ws_notification_task`, `send_whatsapp_notification_task`,
  `send_sms_notification_task`).
- `NotificationCommands.dispatch_notification_once(user, template_slug, context, dedupe_key)`
  (`notifications/services/commands.py:206-247`) — variante para scanners periodicos (Celery
  Beat). Crea un `NotificationLog` marcador SINCRONO con `template=None, channel='', status=SENT`
  ANTES de llamar a `dispatch_notification()` real, para deduplicar entre corridas. **Esto es
  intencional, no un bug** — ver hallazgo 5.1 mas abajo (el propio comando `audit_notifications`
  lo mal-clasifica).
- `notifications/tasks.py::send_email_notification_task` — usa `django.core.mail.send_mail()`
  directo (NO existe `notifications/clients/email_client.py`, a diferencia de lo que asume el
  plan en su seccion 1 — la doc de arquitectura de `notifications` ya lo aclara explicitamente:
  "No existe `clients/email_client.py`"). Resuelve `from_email` via `OrganizationSelector.
  get_email_settings().default_from_email`, con fallback a `settings.DEFAULT_FROM_EMAIL` solo si
  esa fila esta vacia (`notifications/tasks.py:125-135`).
- Modelos: `NotificationTemplate` (slug, subject, email_body, whatsapp_template_name, ws_event_type,
  is_active) y `NotificationLog` (user, template FK nullable, template_slug, channel, status,
  payload_context, error_message, sent_at).

## 2. `transaction.on_commit()` — verificado, SIN violaciones encontradas

Se revisaron los 10 archivos reales que llaman a `dispatch_notification`/`dispatch_notification_once`
(ver `EMAIL_SEND_MATRIX.md` para el listado completo por archivo:linea). Todos los call sites reales
estan envueltos en `transaction.on_commit(lambda: ...)`. Dos archivos (`kyc/services/commands.py`,
`operations/services/commands.py`) usan un helper privado `_dispatch()` que en un primer grep
superficial parecia NO estar protegido -- verificado a fondo: **si lo esta**, el `on_commit()`
envuelve la llamada a `_dispatch()` en cada uno de sus 6+6 call sites reales, no a
`dispatch_notification` directamente. Sin gap aqui.

## 3. Configuracion SMTP — verificado, config presente y coherente

`ecommerce/settings/base.py:453-460` define 8 variables via `config(...)` (django-environ), todas
con default razonable salvo `EMAIL_BACKEND` (default `console.EmailBackend` — **si `.env.production`
no la sobreescribe, los emails solo se imprimen en logs y nunca salen realmente**, riesgo real a
verificar explicitamente).

Verificado en `.env.production` (solo nombres/valores no sensibles, contraseña NO volcada aqui):
- Las 8 variables SI estan definidas (no vacias), incluida `EMAIL_HOST_PASSWORD` (confirmado
  no-vacio, valor no expuesto).
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` (real, no console — correcto).
- `EMAIL_HOST=mail.sintel.net.co`, `EMAIL_PORT=465`, `EMAIL_USE_TLS=False`, `EMAIL_USE_SSL=True`
  — combinacion coherente (465 es SSL implicito, no TLS explicito — la config es la correcta para
  ese puerto, no una inconsistencia).
- `DEFAULT_FROM_EMAIL=contacto@sintel.net.co` (dominio propio, coherente).

**No verificado en esta fase**: conectividad SMTP real (handshake TLS/SSL, autenticacion) contra
`mail.sintel.net.co` desde el contenedor de produccion — eso es FASE 2/7 del plan (pruebas), fuera
de alcance de esta fase forense de solo-lectura.

## 4. `organization.EmailSettings` — GAP CRITICO encontrado (ver EMAIL_GAPS.md #1)

Consumida por 3 call sites reales (`notifications/tasks.py:126`, `marketing/channels/
email_channel.py:18`, `users/services/commands.py:233` — los 3 con el MISMO patron: leer
`default_from_email` de esta tabla PRIMERO, `.env`/`settings.DEFAULT_FROM_EMAIL` solo como
fallback si la fila esta vacia). En DESARROLLO, esta fila existe y tiene:
- `default_from_email = 'sintel.technology@gmail.com'` (diverge de `contacto@sintel.net.co`
  configurado en `.env`/`.env.production` — como esta fila NO esta vacia, GANA sobre el `.env`,
  asi que TODO email real (los 3 mecanismos, no solo el central) sale con este remitente, no el
  de `.env.production`).
- `frontend_base_url = 'http://localhost:5173'` (URL de desarrollo).

**No se verifico el valor real de esta misma fila en la base de datos de PRODUCCION** (fuera de
alcance de esta fase, requiere acceso de solo lectura a `sintel_prod_db` en una fase posterior) —
pero dado que es la MISMA tabla replicada por migracion/seed en ambos entornos y nada en el codigo
sugiere que se gestione distinto, existe riesgo real de que produccion tenga el mismo valor de
desarrollo sin nunca haberse actualizado desde el panel admin. **Prioridad maxima para FASE 2**.

## 5. Bypasses reales encontrados (3, no 2)

La documentacion de `notifications` (y el plan, seccion 1) afirman "2 bypasses conocidos". El
escaneo real (`grep -rn "send_mail(\|EmailMessage(\|EmailMultiAlternatives(" --include=*.py`)
encuentra 3 sitios reales fuera de `notifications/tasks.py`:

1. **`users/services/commands.py:238` — `VerificationCommands._send_otp_email()`**. `send_mail()`
   SINCRONO (no Celery, no `.delay()`), dentro de un `try/except Exception` que solo hace
   `logger.warning(...)` — sin `NotificationLog`, sin retry, sin metrica. Motivo: envia un codigo
   OTP de un solo uso (registro/reset de password), dato sensible que no encaja bien en
   `NotificationTemplate` (no es un evento de negocio reutilizable). Se llama directo desde el
   flujo HTTP de registro/reset — **bloquea el hilo de la peticion con el round-trip SMTP real**
   (gap real, ver EMAIL_GAPS.md #3).
2. **`quotes/tasks.py:46` — `send_quotation_email_task()`**. Celery task real, bien configurada
   (`queue='notifications'`, `max_retries=3`, `autoretry_for=(Exception,)`, `acks_late=True`).
   Adjunta un PDF generado dinamicamente (`PDFService.generate_quotation_pdf`) — motivo real y
   valido (`NotificationTemplate.email_body` no soporta adjuntos). Llamador real:
   `quotes/api/views.py:206` (`QuotationViewSet.send()`), fuera del bloque `transaction.atomic()`
   — verificado que NO tiene el bug de "enviar antes del commit" pese a no usar el patron
   `on_commit` explicito (el `.delay()` ya ocurre despues de que el `with transaction.atomic()`
   sale de scope). **NO crea `NotificationLog`** — sin trazabilidad en el panel admin (gap real,
   ver EMAIL_GAPS.md #4).
3. **`marketing/channels/email_channel.py:21` — `EmailChannelAdapter.send()`**. Tercer canal, NO
   contado como "bypass" por la documentacion existente porque es un subsistema paralelo DISENADO
   a proposito: el Campaign Engine de `marketing` (`CHANNEL_REGISTRY`, 8 canales) envia campanas
   masivas, un dominio distinto de las notificaciones transaccionales de `dispatch_notification`
   — mismo criterio arquitectonico que `marketing.channels.whatsapp_channel.WhatsAppChannelAdapter`
   (documentado aparte). Se documenta aqui porque el plan pide "descubrimiento exhaustivo, no
   asumir nada" y el escaneo real lo encuentra — no se recomienda migrarlo.

Los 2 "bypasses conocidos" del plan corresponden a los items 1 y 2 de arriba. El item 3 es un
HALLAZGO NUEVO de esta auditoria (existia y estaba documentado en `marketing/CLAUDE.md`, pero
nunca contado como "bypass de email" en la documentacion de `notifications`).

## 6. Bug real encontrado en la propia herramienta de auditoria existente

`notifications/management/commands/audit_notifications.py::_report_invalid_slugs()`
(linea 96-111) consulta `NotificationLog.objects.filter(template__isnull=True).exclude(
template_slug='')` para reportar "slugs invalidos". Esta consulta **no distingue** fallos reales
(`status=FAILED`, `dispatch_notification` no encontro el template) de marcadores de dedupe
intencionales (`status=SENT, channel=''`, creados a proposito por `dispatch_notification_once()`).
Resultado: el comando reporta como "ROTO" el slug `ticket_soporte_sin_seguimiento` (11
ocurrencias, la mas reciente HOY 2026-09-23 17:00 UTC) pese a que el template existe, esta activo,
y el sistema funciona correctamente — es simplemente el scanner horario de tickets sin seguimiento
dejando su marcador de dedupe. Mismo patron para `cotizacion_sin_respuesta`, `cliente_recurrente_
cross_sell`, `renting_por_vencer`, `pago_rechazado_seguimiento` (los 5 slugs de "Proactividad" de
Fase 11, todos via `dispatch_notification_once`). Ver EMAIL_GAPS.md #2.

## 7. Inventario real de templates — 35 slugs referenciados en codigo, no 18

La tabla de 18 slugs en `notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md`
(actualizada por ultima vez con la auditoria del 2026-08-05) esta desactualizada: el escaneo real
de `template_slug='...'` en callers encuentra **35 slugs distintos** referenciados en codigo real
(sin contar `notifications/tests.py`, que usa slugs ficticios de test). De esos 35:
- **30 existen** como `NotificationTemplate` activo en la BD de desarrollo.
- **5 NO EXISTEN** — ver EMAIL_GAPS.md #1, el hallazgo mas severo de esta auditoria.
- De los 30 que existen, 1 (`kyc_submitted_for_review`) tiene `email_body` vacio — el canal Email
  esta efectivamente deshabilitado para ese evento especifico (podria ser intencional, no
  verificado el motivo de negocio en esta fase).

Ver `EMAIL_SEND_MATRIX.md` para la tabla completa modulo-por-modulo.

## 8. Modulos auditados — con envio real de Email vs sin el

| Modulo | Envia Email | Mecanismo |
|---|---|---|
| accounts | Si | `dispatch_notification` (`user_registered` x2, `admin_password_reset`, `admin_email_verification`) |
| users | Si (bypass) | `send_mail()` sincrono directo (OTP) |
| notifications | Si (central) | `send_email_notification_task` |
| orders | Si | `dispatch_notification` (`order_created` + 7 slugs `shop_*` de fulfillment — todos OK; `order_created` **[CORREGIDO 2026-09-23]**, template no existia, ya creado y desplegado) |
| payment | Si | `dispatch_notification` (`order_paid` **[CORREGIDO 2026-09-23]**, template no existia, ya creado y desplegado; `order_cod_confirmed` — OK) |
| support | Indirecto | `support/tasks.py` llama `dispatch_notification` para `ticket_soporte_sin_seguimiento` via `dispatch_notification_once` (Celery Beat horario) |
| technical_services | Si | `dispatch_notification` (5 slugs, todos existen: `service_operation_created/assigned/cancelled`, `service_visit_scheduled`, `service_incident_reported`, `service_request_created`, `service_payment_confirmed`, `service_status_updated`) |
| renting | Si | `dispatch_notification` (9 call sites — 3 slugs **[CORREGIDOS 2026-09-23]**: `rental_cod_review_pending`, `rental_payment_conflict_admin`/`_customer` no existian, ya creados y desplegados; el resto OK) |
| quotes | Si (bypass) | `send_quotation_email_task` (Celery, adjunta PDF) + `dispatch_notification` (`cotizacion_sin_respuesta`, proactivo) |
| operations | Si | `dispatch_notification` via `_dispatch()` (`operacion_estancada`) |
| organization | No envia, es SSoT | Provee `default_from_email`/`frontend_base_url` consumido por notifications/users/marketing |
| shop | No | Sin ningun sender encontrado en el escaneo real |
| kyc | Si | `dispatch_notification` via `_dispatch()` (5 slugs KYC, todos existen) |
| marketing | Si (canal paralelo, disenado) | `EmailChannelAdapter` (Campaign Engine, campanas masivas) |
| dashboard | **[CORREGIDO FASE 5] No** | `dashboard/api/views.py:3294` solo MENCIONA `dispatch_notification()` en un comentario ("contrato fijo del slug") — verificado con grep dedicado, 0 llamadas reales en todo el archivo. Falso positivo del escaneo inicial, corregido en EMAIL_SEND_MATRIX.md |

**No se encontraron senders de Email en**: `shop`. Confirma la lista del plan, con la salvedad de
que el plan no menciona `dashboard` como caller (si lo es, via un endpoint admin) ni `marketing`
como canal paralelo real.

## 9. Pendiente para fases posteriores (fuera de alcance de FASE 0-1)

- Verificar `organization.EmailSettings` REAL en produccion (gap #1 de EMAIL_GAPS.md).
- Verificar conectividad SMTP real contra `mail.sintel.net.co` desde el contenedor de produccion.
- Auditar URLs de templates (localhost/`/panel/` en templates CUSTOMER) — no se alcanzo a revisar
  el contenido HTML completo de los 30 templates existentes en esta pasada, solo su existencia y
  si `email_body` esta poblado.
- Prueba real end-to-end con buzon controlado (FASE 7 del plan).

---

## FASE 2 — Configuracion produccion (2026-09-23, GATE: EMAIL CONFIGURED)

Verificado en vivo contra `sintel_prod_django` (solo lectura, sin exponer secretos):

```
EMAIL_BACKEND      django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST         mail.sintel.net.co
EMAIL_PORT         465
EMAIL_USE_TLS      False
EMAIL_USE_SSL      True
EMAIL_HOST_USER    contacto@sintel.net.co
DEFAULT_FROM_EMAIL contacto@sintel.net.co
password           configurado (no vacio, valor no expuesto)
```

Coherente (465 = SSL implicito, combinacion correcta), coincide con `.env.production` (§3 arriba,
verificado por la Fase 0-1). `docker-compose.prod.yml` NO tiene overrides de `EMAIL_*` en
`environment:` de `django`/`celery_worker` — la config viaja integra via `env_file:
.env.production`, sin duplicacion ni riesgo de un valor distinto pisando al otro.

`organization.EmailSettings` en produccion (verificado, solo lectura): `default_from_email =
'contacto@sintel.net.co'`, `frontend_base_url = 'https://www.sintel.net.co'` — **ambos correctos,
coinciden con lo esperado**. El gap #5 (divergencia) es exclusivo de desarrollo, cerrado en
EMAIL_GAPS.md.

**GATE FASE 2: `EMAIL CONFIGURED`.** No se probo el handshake SMTP real (conexion/auth contra
`mail.sintel.net.co`) — eso es FASE 7 (envio real controlado), a proposito no ejecutado en esta
pasada de solo-analisis.

## FASE 3 — Servicio central (2026-09-23, GATE: PASS)

Re-verificado independientemente lo que §1-2 de este documento ya habia encontrado, mas lo nuevo:

- **Task Celery registrada y activa**: `celery -A ecommerce inspect registered` contra el worker
  real (dev) confirma `notifications.send_email` registrada. Config real
  (`notifications/tasks.py:84-92`): `bind=True, autoretry_for=(Exception,), max_retries=3,
  default_retry_delay=60, queue='notifications', acks_late=True`.
- **Captura de errores verificada linea por linea** (`notifications/tasks.py:118-149`): el
  `NotificationLog` se crea en `STATUS_PENDING` ANTES de intentar el envio, se actualiza a
  `STATUS_SENT` en exito o a `STATUS_FAILED` + `error_message=str(exc)` en el `except` ANTES de
  `raise self.retry(exc=exc)` — un fallo real de SMTP queda trazado en BD sin excepcion, cumple
  exactamente el criterio de la Seccion 2/42 del plan ("nunca perdida silenciosa").
- **Regla `transaction.on_commit()` (Seccion 8 del plan): re-verificada de forma independiente,
  CONFIRMADO sin violaciones.** Los 2 casos que a primera vista (grep superficial) parecian
  llamadas directas sin `lambda:` resultaron ser las DEFINICIONES del helper `_dispatch()`
  (`kyc/services/commands.py:23`, `operations/services/commands.py:616`), no llamadas reales — sus
  12 call sites reales (6+6, confirmado con grep dedicado) SI estan envueltos en
  `transaction.on_commit(lambda: _dispatch(...))`. El unico caller de `dispatch_notification()`
  SIN `on_commit` es `dispatch_notification_once()` misma (`notifications/services/commands.py:246`,
  la variante para Celery Beat) — correcto por diseno: los scanners periodicos leen estado ya
  commiteado, no hay transaccion abierta que esperar.

**GATE FASE 3: `PASS`.** Servicio central certificado: resolucion de template, recipient,
from_email, Celery real con retry, captura de errores en `NotificationLog`, y regla `on_commit`
respetada en el 100% de los callers reales.
