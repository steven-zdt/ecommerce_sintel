# EMAIL_GAPS — Hallazgos reales (FASE 0-1)

Ordenados por severidad. Cada uno con evidencia real (archivo:linea o consulta verificada en
runtime dev). Ninguno se corrigio en esta fase — FASE 0-1 es descubrimiento puro, la correccion es
FASE 3+ del plan.

---

## GAP #1 — CRITICO: 5 templates referenciados en codigo real NO EXISTEN en BD

**Evidencia:** verificado en `ecommerce_sintel_django` (dev) via shell: de 35 slugs reales
referenciados en codigo, 5 no tienen fila en `NotificationTemplate`, y NINGUNA migracion en todo
el repo los siembra (`grep -rn "order_created\|order_paid\|rental_cod_review_pending" **/migrations/*.py`
→ 0 resultados):

| Slug | Caller real | Evento de negocio afectado |
|---|---|---|
| `order_created` | `orders/services/commands.py:169` | Cliente NUNCA recibe email de confirmacion al crear una orden |
| `order_paid` | `payment/shared/commands.py:97` | Cliente NUNCA recibe email al confirmarse el pago online |
| `rental_cod_review_pending` | `renting/services/commands.py:570` | Admin no recibe aviso de renta COD pendiente de revision |
| `rental_payment_conflict_customer` | `renting/services/commands.py:664` | Cliente no recibe aviso de conflicto de pago |
| `rental_payment_conflict_admin` | `renting/services/commands.py:672` | Admin no recibe aviso de conflicto de pago |

Confirmado con historial real de `NotificationLog` (dev): `order_created` fallo 22 veces (ultima
2026-07-23), `order_paid` 9 veces (ultima 2026-07-29), `rental_cod_review_pending` 4 veces (ultima
2026-07-21) — es decir, **este gap lleva existiendo desde al menos julio 2026 sin corregirse**,
silenciosamente (cada intento SI queda registrado como `NotificationLog(status=FAILED)`, pero
nadie lo vio porque nada alerta sobre logs FAILED).

`order_created` y `order_paid` son, con alta probabilidad, los eventos transaccionales de email
mas importantes del sistema (confirmacion de compra) — si este mismo estado existe en produccion
(no verificado aun, requiere FASE 2), es el hallazgo de mayor impacto de negocio de toda esta
auditoria.

**Severidad: CRITICA.**

**[CERRADO 2026-09-23]** Confirmado que las 5 filas tambien faltaban en produccion real (0 logs en
90 dias para las 5, mas 2/5/3 `NotificationLog.status=FAILED` historicos para
`order_created`/`order_paid`/`rental_cod_review_pending` respectivamente, coincidiendo exactamente
con las 6 unicas ordenes reales creadas en produccion, 2026-07-29 a 31). Corregido: migraciones
`orders/0018_seed_order_lifecycle_templates.py` y `renting/0038_seed_cod_and_payment_conflict_
templates.py` (contenido real, no placeholder), verificadas en dev (render sin variables rotas,
111 tests OK) y desplegadas a produccion via `./deploy/deploy.sh` — confirmado en el contenedor
real: las 5 plantillas existen y estan `is_active=True`. Pendiente: prueba real de buzon
controlado (FASE 7).

**[CERRADO 2026-09-23, FASE 6]** Guarda de regresion automatica agregada:
`notifications/tests.py::RealBusinessEmailTemplatesTestCase` (4 tests) confirma que las 5
plantillas existen/activas, renderizan sin variables rotas con el contexto real de sus callers, y
que `dispatch_notification()` las despacha correctamente — siembra su propia BD de test leyendo el
`TEMPLATES` real de `orders/migrations/0018...`/`renting/migrations/0038...` (las migraciones de
datos de este proyecto NO se aplican al armar la BD de test, confirmado en vivo), asi que este test
queda automaticamente sincronizado si el contenido de las migraciones cambia. Si alguna de las 5
plantillas se borra o desactiva por error en el futuro, el test suite falla antes de llegar a
produccion.

**Hallazgo nuevo durante el cierre (documentado, NO corregido, ver FASE 4)**:
`rental_payment_conflict_customer` y `rental_payment_conflict_admin`
(`renting/services/commands.py:662,670`) se disparan ambos con
`dispatch_notification(user=rental_request.user, ...)` — el MISMO usuario cliente en las dos
llamadas, solo `ws_group` difiere (`'user_{uuid}'` vs `'admin_notifications'`). El canal Email
resuelve el destinatario exclusivamente del parametro `user` (`notifications/tasks.py:107,136`),
nunca de `ws_group` — asi que el email de la plantilla "admin" tambien llega hoy a la bandeja del
CLIENTE, no de un admin real. El WebSocket si distingue destinatario (por grupo), el Email no.
**Severidad: MEDIA** (no es un fallo de entrega, es un enrutamiento de destinatario probablemente
no intencional — requiere decision de negocio sobre si `rental_payment_conflict_admin` deberia
enviarse a un email de staff real, fuera del alcance minimo de "el email no existe").

---

## GAP #2 — ALTO: `audit_notifications` (herramienta existente) tiene falsos positivos

**Evidencia:** `notifications/management/commands/audit_notifications.py:96-111`
(`_report_invalid_slugs`) usa `NotificationLog.objects.filter(template__isnull=True).exclude(
template_slug='')` sin excluir los marcadores de dedupe (`channel='', status=SENT`) que
`dispatch_notification_once()` crea a proposito. Resultado: reporta 5 slugs que en realidad
funcionan bien (`ticket_soporte_sin_seguimiento`, `cotizacion_sin_respuesta`, `cliente_recurrente_
cross_sell`, `renting_por_vencer`, `pago_rechazado_seguimiento`) mezclados con los 4 genuinamente
rotos del GAP #1, sin forma de distinguirlos desde la salida del comando.

**Impacto real de este gap**: cualquiera que corra `audit_notifications` (incluido este mismo
proceso de auditoria, al principio) puede descartar el reporte completo como "ruido" y no notar
que 4 de los 9 slugs listados son un problema real (GAP #1). Es una herramienta de observabilidad
que actualmente reduce la confianza en si misma.

**Severidad: ALTA** (no rompe el envio de email, pero rompe la capacidad de detectarlo).
**Fix sugerido (no aplicado)**: agregar `.filter(status=NotificationLog.STATUS_FAILED)` a la
consulta, o excluir explicitamente `channel=''`.

---

## GAP #3 — MEDIO: OTP de `users` envia SMTP sincrono dentro del request HTTP

**Evidencia:** `users/services/commands.py:238` (`VerificationCommands._send_otp_email`) llama
`send_mail()` directo, sin `.delay()`, dentro de un `try/except Exception` que solo hace
`logger.warning()`. Esto ocurre en el flujo sincrono de registro/reset de password — el hilo HTTP
que atiende la peticion del cliente **espera el round-trip SMTP completo** (conexion, TLS/SSL
handshake, auth, envio) antes de responder. Si `mail.sintel.net.co` esta lento o caido, el
endpoint de registro/reset se degrada o cuelga con el, sin timeout explicito visible en el codigo
revisado.

Ademas: sin `NotificationLog`, el unico rastro de un fallo es una linea de `logger.warning()` —
no hay forma de saber desde el panel admin cuantos OTP fallaron ni a quien.

**Severidad: MEDIA** (el bypass esta documentado y aceptado por diseno — dato sensible, un solo
uso — pero el problema de bloqueo sincrono y falta de trazabilidad es real y no estaba
documentado antes de esta auditoria).

---

## GAP #4 — MEDIO: `quotes` (envio con PDF) no crea `NotificationLog`

**Evidencia:** `quotes/tasks.py::send_quotation_email_task` (Celery real, con retry) nunca crea un
`NotificationLog`. Funciona (confirmado: task bien configurada, se dispara desde
`QuotationViewSet.send()` fuera del bloque `atomic()`, sin bug de on_commit), pero un admin que
revise `/panel/.../notificaciones` (o el modelo `NotificationLog` via Django admin) NUNCA vera
estos envios, exitosos o fallidos — son invisibles para cualquier auditoria basada en
`NotificationLog`, incluida esta misma.

**Severidad: MEDIA.**

---

## GAP #5 — BAJO: `organization.EmailSettings` posiblemente desalineado (requiere verificar en prod)

**Evidencia:** en DESARROLLO, `EmailSettings.default_from_email = 'sintel.technology@gmail.com'`
(diverge de `contacto@sintel.net.co` en `.env.production`) y `EmailSettings.frontend_base_url =
'http://localhost:5173'`. Como 3 mecanismos reales de envio (`notifications/tasks.py`,
`marketing/channels/email_channel.py`, `users/services/commands.py`) leen esta tabla PRIMERO y
solo caen al `.env` si esta vacia, **esta fila gana siempre que tenga contenido** — el
`DEFAULT_FROM_EMAIL` de `.env.production` podria estar siendo ignorado silenciosamente en
produccion tambien, y cualquier template que renderice `frontend_base_url` en un link podria estar
generando URLs `localhost:5173` reales en emails a clientes.

**[CERRADO 2026-09-23, FASE 2]** Verificado en produccion real (`sintel_prod_django`, solo
lectura): `EmailSettings.default_from_email = 'contacto@sintel.net.co'` (coincide con
`.env.production`, CORRECTO) y `frontend_base_url = 'https://www.sintel.net.co'` (dominio publico
real, CORRECTO). **Produccion NO tiene este problema** — la divergencia es exclusiva del entorno
de desarrollo (fila de `EmailSettings` nunca actualizada ahi desde el seed inicial, sin impacto en
clientes reales). Tambien confirmado en produccion via `settings.EMAIL_HOST/PORT/USE_SSL/
DEFAULT_FROM_EMAIL/EMAIL_HOST_USER` resueltos correctamente (`mail.sintel.net.co:465`, SSL,
`contacto@sintel.net.co`), password configurado (no expuesto).

**Severidad: reclasificada a BAJA — solo afecta a desarrollo.** Accion recomendada (no ejecutada,
fuera de alcance de auditoria): actualizar la fila de `EmailSettings` en dev desde el panel admin
para que coincida con produccion, evita falsos positivos en pruebas locales.

---

## GAP #6 — INFORMATIVO: `kyc_submitted_for_review` tiene `email_body` vacio

**Evidencia:** verificado en BD (dev) — el template existe, `is_active=True`, pero `email_body=''`.
El canal Email para este evento especifico esta efectivamente deshabilitado (WS/WhatsApp si
podrian estar configurados, no verificado). Podria ser intencional (evento interno/admin, no de
cliente) — no se investigo el motivo de negocio en esta fase.

**Severidad: INFORMATIVA**, listar para que un humano confirme intencion.

---

## GAP #7 — INFORMATIVO: 3er canal de Email no contado como "bypass" por la documentacion previa

`marketing/channels/email_channel.py::EmailChannelAdapter` (Campaign Engine) es un canal real,
disenado a proposito, que envia Email fuera de `dispatch_notification`. La documentacion de
`notifications` solo contaba 2 bypasses. No es un bug — es un hallazgo de completitud del
inventario (ver EMAIL_BASELINE.md §5). Se recomienda que `notifications/.AGENT/docs/
ARQUITECTURA_COMPLETA_NOTIFICATIONS.md` lo mencione explicitamente junto a los otros 2, para que
la proxima auditoria no tenga que re-descubrirlo.

---

## GAP #8 — MEDIO (solo DEV, produccion no afectada): credenciales SMTP de desarrollo invalidas

**Evidencia:** descubierto en vivo durante FASE 8 (UI Smoke, checkout real via `POST
/api/v1/orders/orders/create_from_cart/` contra `ecommerce_sintel_django`, 2026-09-23). El canal
Email de `order_created`, `operation_created`, `shop_order_received` y `order_cod_confirmed` fallo
con `(535, b'5.7.8 Username and Password not accepted...')` -- la contrasena de aplicacion de Gmail
en `.env` (`EMAIL_HOST_USER=sintel.technology@gmail.com`) fue rechazada por el servidor SMTP real.
El canal WebSocket de los mismos 4 eventos funciono correctamente (`NotificationLog.status=SENT`),
confirmando que el codigo/template/dispatch estan bien -- es exclusivamente un problema de
credenciales expiradas/revocadas del lado de Gmail.

**Impacto real**: bloquea cualquier verificacion manual de email en desarrollo desde ahora
(incluida la que un desarrollador quiera hacer a futuro). **NO afecta produccion** -- confirmado
independientemente en FASE 7: produccion usa un SMTP distinto (`mail.sintel.net.co:465`, dominio
propio) y los 3 envios reales de esa fase salieron sin error.

**Severidad: MEDIA, alcance DEV unicamente.** Accion recomendada (fuera de alcance de esta
auditoria, requiere que el usuario genere una nueva contrasena de aplicacion de Gmail): rotar
`EMAIL_HOST_PASSWORD` en `.env`.

**Beneficio colateral real**: esta falla, al ocurrir de forma natural durante la prueba de FASE 8,
satisface tambien el requisito de FASE 9 ("simular SMTP unavailable... verificar que no hay perdida
silenciosa") -- confirmado: `NotificationLog.status=FAILED` con el error real de SMTP en los 4
casos, ninguna excepcion sin capturar, ningun crash del negocio (la orden se creo exitosamente
pese a los 4 fallos de Email).

---

## GAP #9 — INFORMATIVO: `operation_created` no estaba en la matriz de senders

**Evidencia:** `operations/services/commands.py:93,152` dispara `operation_created`
(`operations/migrations/0002_seed_notification_templates.py`, template real y activo) -- confirmado
en vivo durante FASE 8, no capturado por el escaneo grep de FASE 0-1 (probablemente por estar
bundleado bajo el conteo generico de `operations` en la matriz original). Agregado a
`EMAIL_SEND_MATRIX.md`.

---

## FASE 4 — Decision sobre los 3 bypasses/canales (2026-09-23)

Criterio del plan (secciones 16, 52-53): no eliminar sin entender el proposito, no reemplazo
global ciego, no cambiar logica de negocio salvo lo estrictamente necesario para que el email
previsto se envie. Las 3 decisiones:

**1. `users/services/commands.py::_send_otp_email` (GAP #3) → A) MANTENER como excepcion
documentada.** Motivo real de su existencia sigue vigente: OTP es un dato sensible de un solo uso,
no encaja como `NotificationTemplate` reutilizable. El problema real (bloqueo sincrono del hilo
HTTP, sin `NotificationLog`) es genuino pero **no esta roto hoy** — es una mejora de
resiliencia/observabilidad, no un fix de un email que no sale. Convertirlo a Celery async
cambiaria el contrato de UX del flujo de registro/reset (el usuario ya no tendria garantia de que
el email fue *intentado* antes de que el endpoint responda) — decision de producto, no de esta
auditoria. Recomendacion: dejarlo como esta, revisar en una mision aparte si se decide invertir en
resiliencia de este flujo especifico.

**2. `quotes/tasks.py::send_quotation_email_task` (GAP #4) → A) MANTENER como excepcion
documentada.** Motivo real solido y verificado: adjunta un PDF generado dinamicamente,
`NotificationTemplate.email_body` no soporta adjuntos — no es un atajo, es una limitacion real del
sistema central. Ya usa Celery real con retry (`max_retries=3, autoretry_for`). El unico gap real
(sin `NotificationLog`, invisible para auditoria/panel admin) es una mejora de observabilidad de
bajo riesgo (agregar la creacion del log no cambia el comportamiento de envio) — candidata natural
para una mision futura pequena y aislada, no para esta auditoria (que es de solo lectura salvo el
fix minimo ya aplicado en GAP #1).

**3. `marketing/channels/email_channel.py::EmailChannelAdapter` (GAP #7) → A) MANTENER, sin
cambios de codigo; SI actualizar documentacion.** Es un subsistema disenado a proposito (Campaign
Engine, 8 canales, campanas masivas — dominio de negocio distinto a notificaciones transaccionales
1:1). Ya usa Celery real con retry (`marketing.tasks.send_via_channel_task`, `max_retries=3`).
Unica accion recomendada: actualizar `notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_
NOTIFICATIONS.md` para que mencione este 3er canal junto a los 2 bypasses conocidos — evita que la
proxima auditoria tenga que re-descubrirlo desde cero (no aplicado en esta pasada, solo lectura de
`docs/notifications/`, no de `.AGENT/docs/` por alcance de la tarea delegada).

**Conclusion FASE 4: ninguno de los 3 requiere migracion al servicio central ni correccion de
codigo en esta mision.** Los 2 gaps de observabilidad reales (OTP sin log/async, quotes sin log)
quedan documentados para una mejora futura aislada, no forman parte de "el email no sale" (que ya
esta resuelto en GAP #1).
