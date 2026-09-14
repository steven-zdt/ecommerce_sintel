# 18 — Auditoría Enterprise: producción y resiliencia del WS de soporte (Fase 4)

> **Fase 4 completada 2026-08-01** — diagnóstico de solo lectura, cero cambios de código.
> Continúa el plan iniciado en [15](15_AUDITORIA_SUPPORT_OMNICANAL.md) (Fase 1),
> [16](16_AUDITORIA_AI_ENGINE_SYNC.md) (Fase 2) y [17](17_AUDITORIA_SYNC_DOCUMENTAL_CROSSMODULO.md)
> (Fase 3), todas cerradas el mismo día. No repite el bug de JWT ya corregido hoy ni los headers
> WS de nginx ya verificados correctos. Verificado en vivo contra `sintel_prod_django`/
> `sintel_prod_celery_*` (solo lectura — sin reiniciar ni modificar nada).

## A. Reconexión y resiliencia del cliente

- **A1 (P2).** Reintento de reconexión fijo cada 3s, sin backoff exponencial ni jitter
  (`SupportChatWidget.vue`/`SupportDashboardView.vue`). Un deploy o reinicio de varios minutos
  produce thundering herd de reconexiones sincronizadas justo cuando el servidor recién levanta,
  cada una además disparando `refreshAccessToken()`.
- **A2 (P2).** Sin heartbeat/ping-pong de aplicación — confirmado por ausencia real de código, no
  supuesto. Una conexión zombie (TCP vivo pero silenciosamente muerta de un lado, común detrás de
  proxies) puede quedar mostrando "en línea" indefinidamente sin que nadie lo note. Se conecta con
  B3 (pérdida silenciosa de mensajes bajo capacity/expiry de Redis).
- **A3 (P2).** El panel admin **no resincroniza su historial al reconectar** — a diferencia del
  widget cliente (que sí reemplaza el array completo de mensajes en cada `history`, sin riesgo de
  pérdida/duplicación). Si un admin se desconecta brevemente (WiFi, laptop en suspensión),
  cualquier mensaje llegado durante el corte no aparece hasta que reselecciona la sala o recarga.
- **A4 (P3).** Historial de sala sin límite ni paginación — se reenvía completo en cada conexión.
  Inofensivo con el volumen actual; relevante si conversaciones se alargan (IA activa) o al escalar.

## B. Infraestructura (Channels + Daphne + Redis + Celery)

- **B1 (P2).** Un solo proceso Daphne sirve TODO el proyecto (HTTP + WS), sin réplicas, verificado
  en vivo (`/proc/1/cmdline`). 12 vCPUs disponibles sin aprovechar paralelismo de procesos.
- **B2 — el hallazgo más severo de la fase (P1, hoy latente).** `ask_ai()` hace un `requests.post`
  síncrono de hasta 300s dentro de `@database_sync_to_async` (`thread_sensitive=True` por
  defecto). En este proceso ASGI puro (un solo Daphne, sin envoltura WSGI), ese es el MISMO hilo
  compartido que usa todo el `sync_to_async`/`database_sync_to_async` del proceso — incluyendo
  peticiones HTTP normales de Django. Una llamada de IA lenta o colgada puede estancar consultas
  de BD de peticiones completamente ajenas al chat. Verificado en vivo:
  `AI_SUPPORT_CHAT_ENABLED=False` en el `.env.production` real — inofensivo hoy, pero es el
  bloqueador real a resolver antes de activar IA ampliamente (más grave que el simple "falta
  timeout" ya señalado en G2 de Fase 2 — el problema no es solo la duración, es que bloquea el
  hilo compartido de TODA la app).
- **B3 (P3).** `CHANNEL_LAYERS` sin `capacity`/`expiry` propios — defaults de `channels_redis`
  (`capacity=100`, `expiry=60`) nunca evaluados a propósito. Verificado en el código fuente real
  instalado: al superar capacity, el mensaje simplemente NO se encola, solo un log `INFO` de la
  librería — sin excepción, sin señal a nadie. Se conecta con A2.
- **B4 (P3).** `notify_unattended_escalated_tickets` (cron horaria) sin catch-up si el worker está
  caído justo esa hora, sin alerta si deja de correr (nada distingue "no había nada que notificar"
  de "el worker no corrió"), y `celery_beat` — a diferencia de `celery_worker` — **no tiene
  healthcheck** en `docker-compose.prod.yml`. Sin Sentry/Flower/monitoreo alguno en el proyecto.
- **B5 (P4, informativo).** Sin `OriginValidator` en el WS — riesgo evaluado como bajo: la auth es
  100% JWT en query string (no cookie de sesión), el vector clásico que `OriginValidator` mitiga.
- **B6 (P4, informativo).** `worker_connections` de nginx en su default de imagen, nunca ajustado
  a propósito — alto para el volumen actual, vale documentar de cara a la Fase 10.

## C. Race conditions / backpressure

- **C1 (P2, hoy latente).** Respuestas de IA pueden llegar fuera de orden — cada mensaje del
  cliente dispara una `asyncio.create_task(self._ai_reply(...))` independiente, sin cola/lock por
  sala. El rate-limit de Fase 1 (C1, `AI_CHAT_RATE_LIMIT`) protege frecuencia, no orden/concurrencia.
- **C2 — reproducible HOY en producción, sin ninguna dependencia de IA (P2).** Multi-pestaña/
  multi-dispositivo del mismo usuario, o 2 admins viendo la misma sala: los mensajes propios **no
  se propagan en vivo** a las otras conexiones del mismo grupo. La rama cliente de `receive()`
  hace `group_send` solo a `support_admins` y ecoa el mensaje únicamente a la conexión que lo
  envió (`self.send()`), nunca a `chat_{user.uuid}` (el grupo al que están unidas TODAS sus
  pestañas). Mismo patrón en espejo del lado admin. Un cliente con el sitio abierto en
  móvil+desktop, o dos agentes trabajando la misma sala en simultáneo, son escenarios comunes, no
  de borde — probablemente el hallazgo con mayor probabilidad real de ocurrir de todo este informe.

## Resueltos (2026-08-01, mismo día)

**C2** — La rama cliente y la rama admin de `receive()` ahora hacen `group_send` a
`chat_{user.uuid}`/`support_admins` (respectivamente) en vez de `self.send()` unicast. Cada
conexión recibe su propio eco por el mismo camino que las demás conexiones del grupo — sin
duplicar lógica de envío. **Verificado en el navegador real**, no solo en tests: 2 pestañas
autenticadas como el mismo usuario, mensaje enviado desde una, apareció en vivo en la otra sin
recargar. 2 tests nuevos de regresión (multi-pestaña cliente y multi-pestaña admin), ambos
pasando junto con los 19 preexistentes (21/21 total).

**A3** — `SupportDashboardView.vue::connectWs()` ahora resincroniza al reconectar (`ws.onopen`):
refresca la lista de salas y, si hay una sala seleccionada, vuelve a pedir su historial completo
por REST (mismo endpoint que `selectRoom()`, sin riesgo de duplicar — reemplaza el array).

**A1** — Backoff exponencial con techo (3s→30s) + jitter aleatorio (50-100% del valor) en ambos
componentes, reemplazando el `setTimeout` fijo de 3s. Se resetea a 0 en cada conexión exitosa.

Verificado: `manage.py check` limpio, 21/21 tests de `support` pasando, prueba real en navegador
de C2 con dos pestañas simultáneas, cero errores de consola. Desplegado a producción.

Actualizacion 2026-08-04: A2, B3 y B4 ya fueron cerrados en los repasos posteriores
[31](31_REPASO_BACKLOG_QUICK_WINS.md) y [32](32_REPASO_BACKLOG_PARTE2.md). Permanecen pendientes
A4, B1, B2, B5, B6 y C1. La readiness general de produccion y el nuevo riesgo operativo de
backups se documentan en [33](33_AUDITORIA_READINESS_PRODUCCION_2026-08-04.md).

## Resumen ejecutivo

Dos gaps de reconexión de bajo riesgo de regresión (A1: sin backoff/jitter; A2: sin heartbeat,
confirmado ausente). Un bug funcional real y reproducible hoy mismo, sin depender de IA: los
mensajes propios de un usuario/admin no llegan en vivo a sus otras pestañas o a otros admins en
la misma sala (C2) — el hallazgo de mayor probabilidad de ocurrencia real de esta fase. El panel
admin tampoco resincroniza al reconectar (A3), a diferencia del widget cliente que sí lo hace
correctamente. El hallazgo de mayor severidad técnica es de infraestructura y hoy está inerte:
`ask_ai()` bloquea el hilo compartido de TODA la app Django (no solo el chat) por hasta 300s, vía
`database_sync_to_async` con una llamada HTTP síncrona — precondición dura antes de activar IA
ampliamente (B2). Redondean el cuadro: defaults de Redis nunca evaluados que pierden mensajes en
silencio bajo presión (B3), y `celery_beat` sin healthcheck ni alerta si la tarea horaria de
proactividad deja de correr, en un proyecto sin monitoreo externo (B4). Nada de esto bloquea la
operación actual (volumen bajo, IA apagada), pero C2 y A3 valen corrección pronto por ser bugs
funcionales de hoy, y B2 es la precondición dura para las Fases 9-10 del roadmap original.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1 — Auditoría global de `support` | Hecha, 11/11 cerrados |
| 2 — Sincronización con AI Engine | Hecha, 7/8 cerrados (A3 pendiente, latente) |
| 3 — Sincronización documental cross-módulo | Hecha, 4/4 cerrados |
| 4 — Producción y resiliencia WS | **Hecha; C2, A3, A1, A2, B3 y B4 cerrados en esta fase y repasos posteriores. A4, B1, B2, B5, B6 y C1 pendientes.** |
| 5-16 | Pendientes |
