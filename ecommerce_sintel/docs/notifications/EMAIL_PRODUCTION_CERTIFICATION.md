# EMAIL_PRODUCTION_CERTIFICATION — Sintel E-Commerce/ERP

**Mision:** `PLAN_AUDITORIA_EMAIL_PRODUCCION_SINTEL_LOOP.md` (Fases 0-10, completas).
**Fecha:** 2026-09-23. **Alcance:** exclusivamente Email (WhatsApp/SMS/WebSocket fuera de alcance).
**Documentos de respaldo:** `EMAIL_BASELINE.md`, `EMAIL_SEND_MATRIX.md` (40 filas), `EMAIL_GAPS.md`
(9 hallazgos).

---

## Resultado global

**El servicio de Email de Sintel funciona en produccion real, verificado con evidencia real hasta
el buzon** (no solo `HTTP 200` / `task queued` / `NotificationLog=SENT`, sino entrega SMTP real
CONFIRMADA POR EL USUARIO: los 3 correos de FASE 7 llegaron realmente a `contacto@sintel.net.co`,
incluidos los que referencian `AUDIT-TEST-0001`/`AUDIT-TEST-0002` — confirmacion visual directa,
2026-09-23).

Se encontro y cerro **1 gap critico real** que llevaba desde julio 2026 sin corregir: 5 eventos
transaccionales (incluidos los 2 mas importantes del sistema, confirmacion de pedido y de pago)
fallaban silenciosamente en produccion porque sus plantillas nunca fueron sembradas en base de
datos. Las 6 unicas ordenes reales creadas en produccion hasta la fecha de esta auditoria (29-31
julio 2026) sufrieron este gap. **Corregido, verificado en dev, desplegado a produccion, y
confirmado con un envio SMTP real.**

---

## GATE por fase

| Fase | Resultado |
|---|---|
| 0 — Baseline Forense | PASS (35 senders reales catalogados, 12 modulos + shop sin Email) |
| 1 — Inventario de Senders | PASS (100% de senders conocidos, 2 filas agregadas/corregidas en el cierre) |
| 2 — Configuracion Produccion | **EMAIL CONFIGURED** (SMTP real verificado en vivo: `mail.sintel.net.co:465`, SSL, remitente correcto) |
| 3 — Servicio Central | **PASS** (task registrada, retry real `max_retries=3`, captura de error correcta, `transaction.on_commit()` sin violaciones en los 12 call sites reales) |
| 4 — Bypasses | Resuelto: 3 bypasses/canales evaluados, los 3 mantenidos como excepcion documentada (ninguno esta roto, 2 tienen gaps de observabilidad menores ya documentados) |
| 5 — Module Matrix | Completa, 40 filas, `docs/notifications/EMAIL_SEND_MATRIX.md` |
| 6 — Backend Tests | PASS (59/59 tests de `notifications`, incluidos 4 nuevos que cierran GAP #1 como regresion permanente) |
| 7 — Production Smoke | **PASS, CONFIRMADO** — 3 emails reales enviados por SMTP real desde `sintel_prod_django` a buzon de prueba autorizado, `NotificationLog.status=SENT` los 3, sin error, Y recepcion visual confirmada por el usuario en `contacto@sintel.net.co` (2026-09-23) |
| 8 — UI Smoke | PARTIAL — checkout HTTP real (dev) confirmo 4 eventos disparandose correctamente (WebSocket SENT); Email fallo por credenciales SMTP de DEV invalidas (GAP #8, no afecta produccion) |
| 9 — Failure Tests | PASS — template inexistente y destinatario invalido ambos terminan en `FAILED` con error claro, sin crash del negocio; el fallo SMTP real de Fase 8 sirvio ademas como prueba natural de "SMTP unavailable" |
| 10 — Certificacion | Este documento |

---

## Certificacion por modulo

| Modulo | Resultado | Evidencia |
|---|---|---|
| **orders** | **PASS** | `order_created`: enviado por SMTP real a produccion (FASE 7). `shop_order_received`/`operation_created`: disparo confirmado via checkout real (FASE 8, WebSocket SENT). Los 6 slugs restantes de fulfillment (`shop_preparing_order`, `shop_dispatch_assigned`, `shop_order_shipped`, `shop_delivery_scheduled`, `shop_order_delivered`, `shop_delivery_confirmed`) comparten el mismo template/mecanismo ya certificado (migracion `0014`, sin gaps encontrados) — no probados individualmente uno por uno, riesgo residual bajo. |
| **payment** | **PASS** | `order_paid` (online): enviado por SMTP real a produccion (FASE 7). `order_cod_confirmed`: mecanismo confirmado (FASE 8, WebSocket SENT), Email no probado en produccion pero mismo servicio central ya certificado. |
| **accounts** | PARTIAL | `user_registered` disparado realmente durante el setup de FASE 8 (WebSocket SENT, Email fallo solo por GAP #8 de dev) — mecanismo confirmado. `admin_password_reset`/`admin_email_verification` (accion desde `/panel/usuarios`) no se probaron end-to-end en esta auditoria — templates existen y activos, no hay motivo real para sospechar un problema, pero falta la prueba directa. |
| **users** | PARTIAL (por diseno) | Bypass documentado (GAP #3): OTP funciona pero sincrono, sin `NotificationLog`. No es un fallo de entrega. |
| **renting** | **PASS** (linea de pago) / PARTIAL (COD/conflicto) | `rental_payment_confirmed`: enviado por SMTP real a produccion (FASE 7). `rental_cod_review_pending`/`rental_payment_conflict_customer`/`rental_payment_conflict_admin`: templates corregidos y confirmados activos en produccion (GAP #1), mismo servicio central ya certificado por el template hermano, pero no incluidos en la muestra de 3 de FASE 7 — pendiente de una prueba de buzon dedicada si se quiere cerrar al 100%. Hallazgo de enrutamiento documentado (GAP #1): `rental_payment_conflict_admin` llega hoy al cliente, no a un admin real — requiere decision de negocio, no bloquea la certificacion de "el email sale". Resto de slugs de renting (`rental_order_created`, `rental_payment_failed`, `rental_operation_created`, `rental_dispatch_assigned`, `rental_delivery_scheduled`, `rental_comodato_review_pending`) no probados individualmente — templates existen, sin gaps encontrados. |
| **technical_services** | PARTIAL | 7 slugs, todos con template existente y sin gap encontrado, ninguno probado con envio real individual en esta auditoria — mecanismo central ya certificado (FASE 3/7) da alta confianza, no es prueba directa de este modulo especifico. |
| **support** | PARTIAL | Scanner proactivo (`ticket_soporte_sin_seguimiento`) confirmado ACTIVO en produccion — marcador de dedupe visto corriendo el mismo dia de esta auditoria (evidencia de que Celery Beat lo ejecuta de verdad). Envio de Email no confirmado con buzon real. |
| **operations** | PARTIAL | `operation_created` confirmado disparandose (FASE 8). `operacion_estancada` (scanner) no probado. |
| **kyc** | PARTIAL — 1 gap real menor | `kyc_submitted_for_review` tiene `email_body` vacio (GAP #6, informativo, requiere que un humano confirme si es intencional). Los otros 4 slugs (`kyc_approved`, `kyc_rejected`, `kyc_info_requested`, `kyc_blocked`) existen y sin gap encontrado, no probados individualmente. |
| **marketing** | PARTIAL (por diseno) | Campaign Engine (bypass documentado, GAP #7): sistema real con Celery+retry, sin `NotificationLog` (invisible a auditorias basadas en ese modelo, no es un fallo de entrega). Scanner de cross-sell no probado individualmente. |
| **quotes** | PARTIAL (por diseno) | Bypass documentado (GAP #4): funciona con Celery+retry+PDF adjunto real, sin `NotificationLog`. Scanner `cotizacion_sin_respuesta` confirmado con dedupe marker real en logs (mecanismo activo). |
| **shop** | N/A | No envia Email directamente — confirmado en FASE 0, ningun `dispatch_notification`/`send_mail` real en esta app. |

---

## Gaps abiertos (no bloquean la certificacion, quedan documentados)

Ver `EMAIL_GAPS.md` para el detalle completo con evidencia archivo:linea. Resumen:

| # | Severidad | Resumen | Estado |
|---|---|---|---|
| 1 | ~~CRITICA~~ | 5 templates faltantes (orders/renting) | **CERRADO** — corregido y desplegado a produccion, verificado con SMTP real |
| 1b | MEDIA | `rental_payment_conflict_admin` llega al cliente, no a un admin real | Abierto — requiere decision de negocio |
| 2 | ALTA | `audit_notifications` (comando existente) tiene falsos positivos que ocultan fallos reales | Abierto — fix sugerido no aplicado (fuera del alcance minimo) |
| 3 | MEDIA | OTP de `users` sincrono, sin log/retry | Abierto — aceptado por diseno, mejora futura |
| 4 | MEDIA | `quotes` no crea `NotificationLog` | Abierto — aceptado por diseno, mejora futura |
| 5 | ~~BAJA~~ | `EmailSettings` divergente | **CERRADO** — confirmado que produccion esta correcta, solo dev tenia el problema |
| 6 | INFORMATIVA | `kyc_submitted_for_review.email_body` vacio | Abierto — requiere confirmacion humana de intencion |
| 7 | INFORMATIVA | Campaign Engine no documentado junto a los otros 2 bypasses | **CERRADO** — `notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md` actualizado |
| 8 | MEDIA (solo dev) | Credenciales SMTP de Gmail en `.env` invalidas | Abierto — requiere rotar `EMAIL_HOST_PASSWORD`, accion del usuario |
| 9 | INFORMATIVA | `operation_created` faltaba en la matriz original | **CERRADO** — agregado |

---

## Cambios reales aplicados a produccion en esta mision

1. `orders/migrations/0018_seed_order_lifecycle_templates.py` (nuevo) — siembra `order_created`, `order_paid`.
2. `renting/migrations/0038_seed_cod_and_payment_conflict_templates.py` (nuevo) — siembra `rental_cod_review_pending`, `rental_payment_conflict_customer`, `rental_payment_conflict_admin`.
3. `notifications/tests.py::RealBusinessEmailTemplatesTestCase` (nuevo, 4 tests) — regresion permanente para el gap critico.
4. Desplegado a produccion via `./deploy/deploy.sh` (build `--no-cache` + migracion automatica) — verificado en el contenedor real.

**Ningun cambio de logica de negocio, precios, pedidos, pagos, stock, permisos o workflow** —
consistente con la regla 53 del plan. Ningun bypass fue eliminado ni migrado a la fuerza.

## Accion pendiente del usuario (fuera del alcance de esta auditoria)

- ~~Confirmar recepcion visual de los 3 correos de prueba en `contacto@sintel.net.co` (FASE 7).~~
  **CONFIRMADO 2026-09-23** — el usuario recibio los 3 correos reales, incluidos los que
  referencian `AUDIT-TEST-0001`/`AUDIT-TEST-0002`. FASE 7 queda certificada al 100%, sin
  pendientes.
- Rotar la contrasena de aplicacion de Gmail en `.env` de desarrollo (GAP #8).
- Decidir el destino real de `rental_payment_conflict_admin` (GAP #1b): ¿debe llegar a un email de
  staff real, o el nombre del slug es enganoso y en realidad siempre fue para el cliente?
- Confirmar si `kyc_submitted_for_review` debe tener contenido de Email o es intencional que este
  vacio (GAP #6).
