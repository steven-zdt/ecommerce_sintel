# 32 — Repaso de backlog, parte 2

> Continúa [31_REPASO_BACKLOG_QUICK_WINS.md](31_REPASO_BACKLOG_QUICK_WINS.md). Cierra 3 ítems
> más del backlog acumulado y confirma que 2 ítems de la Fase 13 (Marketing) quedaron **moot**
> (ya no aplican) como efecto secundario del propio fix de esa fase.

## Cerrado en este repaso

**Fase 9 (doc 24) — mensaje proactivo de IA ignoraba `UserNotificationPreference`.**
`ai_proactive_room_message_task` creaba/difundía el mensaje incondicionalmente, a diferencia de
los demás canales de `dispatch_notification` (que sí respetan las preferencias del usuario).
Resuelto con el mismo criterio "opt-out" que el resto: sin preferencias registradas se asume
habilitado; con preferencias explícitas, solo se respeta si `WEB_SOCKET` está entre las
habilitadas. Para este canal en particular "enviar" y "crear el mensaje en la sala" son la misma
acción — si está desactivado, no se crea nada (no solo se omite la difusión en vivo). 3 tests
nuevos.

**Fase 14 (doc 28) — P4, referencias a clase inexistente `OperationTicketSelector`.**
`operations/models.py`, `operations/api/serializers.py` y la doc de arquitectura referenciaban
una clase que nunca existió (el nombre real es `OperationSelector`). Corregido en los 3 lugares.

**Fase 4 (doc 18) — B3, `CHANNEL_LAYERS` sin `capacity`/`expiry` declarados a propósito.**
Los defaults de `channels_redis` (`capacity=100`, `expiry=60`) nunca se habían evaluado — al
superar `capacity`, un mensaje simplemente no se encola (solo un log `INFO` de la librería, sin
excepción ni señal a nadie). `support_admins` es el grupo de mayor riesgo real: cada agente
conectado y cada broadcast de chat comparten la misma cola. Declarado explícitamente
`capacity=1000` (margen real ante una ráfaga, muy por debajo del volumen actual) y `expiry=60`
(sin cambio, pero ahora explícito y documentado en vez de un default silencioso).

## Confirmado como moot (ya no aplica, sin acción necesaria)

**Fase 13 (doc 27) — los 2 P3 pendientes.** `CampaignLog` sin FK a usuario (para Customer360) y
sin supresión de campañas para clientes con `ChatRoom` abierto. Verificado: el único caller real
de `MarketingCommands.dispatch()` en todo el repo es `MarketingAgent.run()`, y desde el fix P1
de la propia Fase 13 (que filtró el despacho a solo `BROADCAST_CHANNELS` con el sentinel literal
`"broadcast"`), **no existe ningún código que envíe una campaña a un usuario individual
identificado** — ni por email ni por WhatsApp. Agregar una FK de usuario a `CampaignLog` hoy
sería infraestructura sin ningún escritor real que la poblara; la supresión no tiene nada que
suprimir sin un envío dirigido. Ambos hallazgos quedan documentados como "sin acción" — si en el
futuro se construye una resolución de audiencia real (fuera de alcance de toda esta auditoría),
ahí sí volverían a ser relevantes.

## Sigue pendiente (evaluado, no implementado en este repaso — requiere alcance mayor)

- **B2 de Fase 4 (P1, hoy latente)**: `ask_ai()` bloquea el thread pool compartido de
  `sync_to_async`. Requiere decidir cómo invocar al AI Engine desde el consumer sin ese bloqueo
  (cliente HTTP async dedicado, o un pool de threads separado del default de Django) — decisión
  de arquitectura, no un fix mecánico.
- **A4 de Fase 4**: paginación del historial de sala — feature nueva (backend + frontend).
- **C1 de Fase 4**: orden de respuestas de IA — requiere cola/lock por sala, cambio de
  concurrencia real.
- **B1 de Fase 4**: múltiples réplicas de Daphne — decisión de infraestructura/ops, no de código.
- **B5/B6 de Fase 4**: `OriginValidator` (ya evaluado como riesgo bajo) y tuning de
  `worker_connections` de nginx (requiere datos reales de tráfico) — informativos, no
  accionables sin más contexto.
- **Fase 10 (doc 25)**: historial de cambios (`changed_by`) para `EmailSettings`/`ContactInfo` —
  requiere un modelo de auditoría nuevo, mayor alcance.

## Verificación

- 3 tests nuevos para el respeto de preferencias del mensaje proactivo de IA.
- `notifications/tests.py` + `operations/tests.py`: corrida completa sin regresiones (ver
  resultado en el cierre de este documento tras el deploy).
- `manage.py check`: limpio.

## Roadmap

| Ítem | Estado |
|------|--------|
| Fase 9 — preferencias del mensaje proactivo | **Cerrado en este repaso** |
| Fase 14 — P4 doc/comentarios | **Cerrado en este repaso** |
| Fase 4 — B3 (capacity/expiry) | **Cerrado en este repaso** |
| Fase 13 — CampaignLog FK + supresión | **Moot, confirmado sin acción necesaria** |
| Fase 4 — B2, A4, C1, B1, B5, B6 | Pendiente, requiere decisión de alcance mayor |
| Fase 10 — historial de cambios | Pendiente, requiere modelo nuevo |
