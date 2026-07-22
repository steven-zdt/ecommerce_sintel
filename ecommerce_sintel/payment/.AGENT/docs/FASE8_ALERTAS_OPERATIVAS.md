# Fase 8 — Alertas operativas (completa)

**Fecha:** 2026-07-13
**Diseño de referencia:** plan original del usuario, Fase 8 (dentro del bloque "Fases 6 a 10", sin más detalle que "Alertas operativas").

## Decisión de diseño: reusar `SecurityEvent`, no `dispatch_notification`

Se evaluaron dos mecanismos ya existentes en el proyecto para "alertar":

1. **`NotificationCommands.dispatch_notification()`** — el mecanismo centralizado de notificaciones (email/WhatsApp/WebSocket), usado en 11+ apps. Requiere un `user` obligatorio para resolver canales — y aunque `ws_group='admin'` permite enrutar el WebSocket al panel admin, el `user` sigue determinando a quién se le envían **otros** canales (email, WhatsApp) si la plantilla los tiene configurados. Para una alerta de "transacción abandonada", el único `user` disponible es el **cliente** de la transacción, no un admin — usar este mecanismo arriesgaba notificar por error al cliente por email sobre algo que la Fase 6 decidió explícitamente NO comunicarle (no se sabe con certeza si su pago se completó).
2. **`security.SecurityEvent` + `SecurityCommands.log_event()`** — ya usado en 3 puntos de `payment/` (firma de webhook inválida, pago rechazado, tarjeta eliminada), append-only, con severidad, y **ya visible en el panel admin** (`/panel/seguridad`, `SecurityDashboardView.vue`) sin necesidad de construir nada nuevo. No tiene ningún riesgo de notificar a un cliente — es puramente interno.

Se eligió la opción 2. No existe integración con Slack/PagerDuty/SMS en este proyecto (confirmado en la Fase 0 — solo WS/Email/WhatsApp), así que "alertas operativas" se interpreta aquí como *"eventos operativamente significativos quedan auditados y visibles donde el equipo de operaciones ya mira"*, no como un nuevo canal de mensajería.

## Qué se hizo

### 2 tipos de evento nuevos en `SecurityEvent.EVENT_CHOICES`

- **`PAYMENT_TRANSACTION_ABANDONED`** — disparado desde `reconcile_pending_wompi_transactions()` (`payment/tasks.py`, Fase 6) en el mismo punto donde ya se crea el `TransactionEvent` de "abandonada". Metadata: `transaction_uuid`, `correlation_id`, `order`/`rental_request`, `minutes_pending`. Severidad `WARNING`.
- **`PAYMENT_FEATURE_FLAG_CHANGED`** — disparado en **ambos** caminos por los que se puede togglear `PaymentFeatureFlags.card_api_flow_enabled` (el kill-switch de la Fase 5):
  - Panel Vue (`AdminPaymentViewSet.feature_flags()` PATCH, `dashboard/api/views.py`) — tiene `request`, así que se audita también `user`/IP/ruta.
  - Django `/admin/` (`PaymentFeatureFlagsAdmin.save_model()`, `payment/admin.py`) — mismo evento, `source: 'django_admin'` en vez de `'panel_admin'` para distinguir el origen.
  - **En ambos casos, solo se dispara si el valor realmente cambió** — togglear al mismo valor (o guardar el formulario sin tocar el campo) no genera ruido.

Migración `security/migrations/0005_alter_securityevent_event_type.py`.

## Bug evitado (no un bug real, una decisión de diseño consciente)

Se consideró loguear el cambio de flag directamente en `PaymentFeatureFlags.save()` (un solo punto para ambos caminos) pero se descartó: el modelo no tiene acceso a `request`/`user` en ese contexto, y perder esa atribución (quién lo cambió) le habría restado valor real a la auditoría. Se prefirió duplicar la lógica de comparación en los dos call sites (panel Vue y Django admin) a cambio de una auditoría más útil.

## Verificación realizada

19 tests nuevos entre 3 archivos de la suite (`WompiReconciliationObservabilityTestCase`, `PaymentAdminPanelTestCase`, `PaymentFeatureFlagsAdminSaveModelTestCase`): alerta de transacción abandonada con metadata correcta; alerta de flag cambiado desde el panel Vue (con `user`/`source`) y ausencia de alerta cuando el valor no cambia; mismo par de casos para el camino de Django `/admin/`, incluyendo que una creación nueva (`change=False`) no dispara nada (no hay "valor anterior" que comparar).

- `docker exec ecommerce_sintel_django python manage.py test payment` (suite completa) → **69/69 OK**.
- `docker exec ecommerce_sintel_django python manage.py test security` → **4/4 OK** (sin regresión).
- **Verificación real en el navegador**: toggle real del flag desde `/panel/pagos` → el evento `PAYMENT_FEATURE_FLAG_CHANGED` aparece de inmediato en `/panel/seguridad` (severidad, usuario, IP, ruta legibles, sin `undefined`), sin errores de consola. Flag restaurado a su estado original al terminar.

**Hallazgo colateral, no corregido (fuera de alcance):** el filtro por tipo de evento del panel de seguridad (`<select>` en `SecurityDashboardView.vue`) es una lista hardcodeada en el frontend que ya estaba incompleta antes de esta fase (le faltaban varios tipos existentes, no solo los 2 nuevos de hoy). El listado general de eventos SÍ muestra los eventos nuevos sin problema — solo el dropdown de filtro específico no los incluye como opción. No se tocó por no ser parte de esta fase.

## Siguiente paso

Me detengo aquí. Quedan del plan original: **Fase 9** (pruebas E2E/carga), **Fase 10** (documentación final de `ARQUITECTURA_COMPLETA_PAYMENT.md`/`IMPLEMENTATION_SUMMARY.md`). ¿Cómo quieres continuar?
