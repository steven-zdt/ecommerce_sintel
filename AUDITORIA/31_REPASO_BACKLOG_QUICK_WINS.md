# 31 — Repaso de backlog: quick-wins de las 16 fases

> Tras cerrar las 16 fases del plan (docs [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-
> [30](30_AUDITORIA_PRUEBAS_E2E.md)), quedaban 16 hallazgos de severidad menor documentados como
> pendientes en 5 fases distintas. Este repaso cierra los 4 quick-wins de bajo riesgo y sin
> arquitectura nueva; el resto queda documentado en sus fases originales para una sesión futura.

## 1. `celery_beat` sin ningún HEALTHCHECK (B4 de Fase 4, doc 18)

A diferencia de `celery_worker` (que sí tiene `celery -A ecommerce inspect ping`), `celery_beat`
nunca tuvo `HEALTHCHECK` en `docker-compose.prod.yml` — nada distinguía "no había nada que
notificar" de "el scheduler murió". Esto se volvió más relevante en esta misma sesión: **2
`PeriodicTask` reales** (`notify-unattended-escalated-tickets` de la Fase 1,
`notify-stale-operation-tickets` de la Fase 14) dependen de que este proceso siga vivo.

**Resuelto:** `docker-compose.prod.yml` —
`test: ["CMD-SHELL", "grep -a -l celery /proc/[0-9]*/cmdline >/dev/null 2>&1 || exit 1"]`.
`celery beat` no responde a `inspect ping` (eso es solo para workers). La imagen de runtime no
trae `pgrep` ni `ps` (verificado en vivo, ambos ausentes) — se lee `/proc` directo con
`grep`/`cat`, presentes en cualquier imagen POSIX mínima. Check parcial (no confirma que siga
encolando), pero es una mejora real sobre cero monitoreo. Verificado manualmente dentro del
contenedor real de producción antes de dar el fix por cerrado.

## 2. Índices de BD faltantes (parte de B3/hallazgos de Fase 9, doc 24)

- `NotificationLog`: `dispatch_notification_once()` filtra por `template_slug` +
  `payload_context__dedupe_key` en cada corrida de los 4 scanners proactivos, sin ningún índice
  — scan no indexado sobre una tabla que solo crece (11+ apps escriben ahí). Agregado
  `models.Index(fields=['template_slug'])` + `GinIndex(fields=['payload_context'])`.
- `ChatRoom`: `notify_unattended_escalated_tickets` filtra por `status`, `ai_paused`,
  `updated_at`, `is_deleted` juntos en cada corrida horaria — `ai_paused` no tenía ningún índice,
  y sin uno compuesto Postgres solo podía combinar los demás vía bitmap AND. Agregado
  `models.Index(fields=['status', 'ai_paused', 'updated_at', 'is_deleted'])`.

## 3. Sin heartbeat de aplicación en el WS de soporte (A2 de Fase 4, doc 18)

Confirmado por ausencia real de código: una conexión zombie (TCP vivo pero muerta de un lado,
común detrás de proxies) podía quedar mostrando "en línea" indefinidamente sin que nadie lo
notara.

**Resuelto:** ping/pong de aplicación en ambos consumidores del widget/dashboard
(`SupportChatWidget.vue`, `SupportDashboardView.vue`) — ping cada 25s, si no llega `pong` en 10s
se fuerza el cierre del socket y el reconnect existente (backoff + jitter, ya resuelto en A1)
toma el relevo. `support/consumers.py::receive()` responde `{"type": "pong"}` a un ping sin
consumir el rate-limit de flood ni pasar por el resto de la lógica de mensajes.

## Verificación

- 4 tests nuevos: 3 para el bridge WhatsApp de la Fase 16 (no relacionados con este repaso, ya
  contados en ese documento) + 1 nuevo para el heartbeat (`test_ping_responde_pong_sin_afectar_
  flood_limit`, confirma que muchos más pings que el límite de flood no lo consumen, y que un
  mensaje de chat normal sigue aceptándose después).
- `support/tests.py` + `notifications/tests.py`: **57/57**.
- `manage.py check`: limpio.
- Build de frontend (`npx vite build`) exitoso.
- Migraciones aplicadas limpio en dev: `notifications.0007_...`, `support.0009_...`.

## Pendiente (documentado en sus fases originales, no tocado en este repaso)

Por decisión explícita del usuario (alcance "solo quick-wins seguros"), quedan sin implementar:
- **B2 de Fase 4 (P1, hoy latente)**: `ask_ai()` bloquea el thread pool compartido de
  `sync_to_async`/`database_sync_to_async` — inofensivo hoy porque `AI_SUPPORT_CHAT_ENABLED=False`
  en producción, pero es el bloqueador real antes de activar IA ampliamente. Requiere repensar
  cómo se invoca al AI Engine desde el consumer — mayor alcance/riesgo que el resto de este
  repaso.
- **B1, C1, A4, B5, B6 de Fase 4**: múltiples réplicas de Daphne, orden de respuestas de IA,
  paginación de historial, `OriginValidator`, tuning de nginx — todos de menor severidad o riesgo
  ya evaluado como bajo.
- **Fase 9 (doc 24)**: mensaje proactivo de IA ignora `UserNotificationPreference` del usuario.
- **Fase 10 (doc 25)**: sin historial de cambios (`changed_by`) para `EmailSettings`/`ContactInfo`.
- **Fase 13 (doc 27)**: `CampaignLog` sin FK a usuario (bloquea mostrar campañas en Customer360);
  sin supresión de campañas para clientes con `ChatRoom` abierto.
- **Fase 14 (doc 28)**: referencia a clase inexistente `OperationTicketSelector` en
  comentarios/docs.

## Roadmap — estado final

| Fase | Estado |
|------|--------|
| 1-16 | Todas hechas — ver documentos 15-30 |
| Repaso de backlog | **Este documento — 4 quick-wins cerrados, resto documentado por fase de origen** |
