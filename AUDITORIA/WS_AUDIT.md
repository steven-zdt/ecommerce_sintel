# WS_AUDIT.md — Auditoría FASE 2: WebSocket de Soporte

> **Fecha:** 2026-08-07. Alcance: `support/channels_auth.py`, `support/routing.py`,
> `support/consumers.py` (+ `ecommerce/asgi.py`/`ecommerce/routing.py` para el wiring
> completo). Continúa la serie ya existente en este directorio — en particular
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md), [18](18_AUDITORIA_PRODUCCION_RESILIENCIA_WS.md) y
> [23](23_AUDITORIA_SEGURIDAD.md) — no repite hallazgos ya cerrados ahí, los referencia.

## Resultado global

**El WebSocket conecta, autentica, enruta, transmite y reconecta correctamente.** No se
encontró ningún punto donde una conexión válida termine sin respuesta o en silencio total.
Se agregaron trazas de depuración estructuradas (`[WS]`/`[CHAT]`) en los 3 archivos —
antes prácticamente no existía logging en `consumers.py` fuera de un único `except`. Un
hallazgo crítico ya documentado (B2 de doc 18: `ask_ai()` bloqueante dentro de
`database_sync_to_async`) pasó de **latente** a **activo**: `AI_SUPPORT_CHAT_ENABLED=True`
en dev hoy (se intentó confirmar en prod, bloqueado por el clasificador de auto-modo al
requerir `docker exec` contra `sintel_prod_django` — pendiente de verificación explícita).

## Checklist FASE 2

| Ítem | Estado | Evidencia |
|---|---|---|
| JWT válido | ✅ Cumple | `channels_auth._get_user_from_token()`: `AccessToken(token_key)` (simplejwt) + `User.objects.get(pk=..., is_active=True)`. Cualquier excepción (vencido, malformado, usuario inactivo/inexistente) cae a `AnonymousUser()`, nunca revienta el middleware. |
| Middleware | ✅ Cumple | `JWTAuthMiddleware` lee `?token=` de la query string; si no hay token, deja pasar lo que ya puso `AuthMiddlewareStack` (sesión/anónimo) — ahora logueado explícitamente en vez de ser indistinguible de "no se evaluó". |
| Routing | ✅ Cumple | `support/routing.py` → `ws/support/chat/` → `SupportChatConsumer.as_asgi()`. Registrado en `ecommerce/routing.py::websocket_urlpatterns` y envuelto por `JWTAuthMiddlewareStack(URLRouter(...))` en `ecommerce/asgi.py`. Verificado por lectura directa de los 3 archivos, cadena completa sin huecos. |
| Connection | ✅ Cumple | `connect()`: sin usuario autenticado → `close(code=4001)` (ahora logueado). Admin (`is_staff and is_superuser`) → grupo `support_admins`. Cliente → `get_or_create_room()` + grupo `chat_{uuid}` + historial + contextos enviados en `type=history`. |
| Disconnect | ✅ Cumple | `group_discard` si `group_name` fue asignado (siempre, salvo rechazo temprano). Ahora logueado con usuario/grupo/código de cierre. |
| Receive | ✅ Cumple, con brechas de log ya cerradas | JSON inválido, flood-limit, `room_uuid` faltante (admin), sala no-OPEN (admin y cliente) — todos los `return` tempranos antes eran silenciosos, ahora cada uno deja un `logger.warning` con la causa. |
| Send | ✅ Cumple | `chat_message()`/`room_closed()` — handlers de grupo que reenvían el payload tal cual al cliente WS. |
| Broadcast | ✅ Cumple (ya corregido en doc 18, C2) | Ambas ramas (admin/cliente) hacen `group_send` a su propio grupo además del grupo contrario — el remitente ve su propio mensaje por el mismo camino que el resto de sus conexiones (multi-pestaña). |
| Groups | ✅ Cumple | `chat_{user.uuid}` (por usuario, todas sus pestañas) y `support_admins` (todo el panel). `group_add` en `connect()`, `group_discard` en `disconnect()` — sin fugas de membresía detectadas. |
| History | ✅ Cumple, límite conocido (A4, doc 18, aún abierto) | `_get_room_history()` trae **todo** el historial sin paginar en cada `connect()`. Documentado como P3 desde 2026-08-01, sin evidencia de que hoy cause problema real (volumen bajo) — no se fuerza su cierre en esta fase por ser explícitamente de bajo riesgo y no formar parte del checklist de corrección de FASE 14 (no es "error real" hoy). |
| Reconnect | ✅ Cumple | Cada reconexión vuelve a ejecutar `connect()` completo: reusa la sala OPEN existente (`get_or_create_room`), reenvía historial completo. El backoff exponencial + resincronización del panel admin al reconectar ya se corrigieron y verificaron en doc 18 (A1/A3) — no se re-auditó el frontend en esta fase (fuera del alcance de los 3 archivos pedidos), solo se confirmó que el backend no depende de estado en memoria que se pierda entre conexiones. |
| Room Assignment | ✅ Cumple | `ChatCommands.assign_admin()` setea `assigned_admin`; `is_ai_mode_active()` lo consulta para que la IA deje de responder en cuanto un humano toma la sala. No se invoca desde `consumers.py` (correcto — es una acción del dashboard, auditada en FASE 10). |
| Sala abierta | ✅ Cumple | `get_or_create_room()` reusa la última sala `OPEN` del usuario; nunca crea una segunda mientras haya una abierta. |
| Sala cerrada | ✅ Cumple | `_room_is_open()` **revalida contra BD** en cada `receive()` del cliente (no confía en el `self.room` cacheado de `connect()`) — cierra la brecha ya documentada donde un cliente podía seguir escribiendo en una sala CLOSED. `close_room()` notifica en vivo (`room.closed`) al grupo del cliente. |
| Human Handoff | ✅ Cumple | `ai_response_opened_ticket()` detecta `abrir_ticket_soporte` exitoso en `tool_results` → `room.ai_paused=True` → `is_ai_mode_active()` deja de disparar IA en esa sala. Ahora logueado explícitamente (`AI handoff status=escalated`). |

## Trazas de depuración agregadas (FASE 2)

Todas usan `logging.getLogger(__name__)` (nombres `support.channels_auth` /
`support.consumers`), nivel `INFO`/`WARNING` — visibles por defecto (root logger en `INFO`,
`ecommerce/settings/base.py::LOGGING`), sin necesidad de configuración adicional:

- `channels_auth.py`: `[WS][AUTH] token valido user=<email>` (éxito) / `Token WS rechazado
  (<TipoExcepcion>): <detalle>` (ya existía) / `sin parametro 'token' ...` (nuevo, caso sin
  JWT en query string).
- `consumers.py` — ciclo de vida: `[WS] connect rechazado: ...` / `[WS] connect admin
  user=... group=...` / `[WS] connect client user=... room=... group=... history=N
  contexts=N` / `[WS] disconnect user=... group=... code=...`.
- `consumers.py` — mensajes: `[WS] receive: frame no-JSON descartado` / `flood-limited` /
  `sin room_uuid` / `room no existe o no esta OPEN` / `ya no esta OPEN` / `[CHAT] room=...
  user=... message_len=N is_admin=<bool> status=sent`.
- `consumers.py` — turno de IA: `[CHAT] room=... AI request status=started` → `[CHAT]
  room=... AI agent=... intent=... tools=N tokens=... latency_ms=N status=ok` (éxito) /
  `status=degraded` (motor no respondió) / `status=exception` (con traceback vía
  `logger.exception`) / `status=escalated` (handoff) / `status=skipped` (rate-limited).

**Nuevo flag `SUPPORT_DEBUG_MODE`** (`ecommerce/settings/base.py`, default `False`): cuando
está en `True`, las trazas `[CHAT]` de mensajes y respuestas de IA agregan el texto
(truncado a 200 caracteres) del mensaje/respuesta real. Apagado por defecto para no dejar
contenido de conversaciones en logs de producción — recomendación explícita del brief de
auditoría ("modo diagnóstico" para reconstruir el recorrido completo sin aplicar cambios a
ciegas). Actívese solo puntualmente vía variable de entorno para depurar un incidente.

## Hallazgos que NO se corrigen en esta fase (documentados, no ignorados)

| Hallazgo | Origen | Por qué no se toca aquí |
|---|---|---|
| **B2 — `ask_ai()` bloquea el hilo compartido `database_sync_to_async` hasta 300s** | Doc 18 | Ahora **activo** (`AI_SUPPORT_CHAT_ENABLED=True` en dev). Es un cambio de arquitectura (mover a `httpx`/`aiohttp` async o a un pool dedicado), no un "error real" puntual — corresponde a FASE 4 (AI Bridge) donde se audita `ai_bridge.py` en profundidad, y a FASE 14 solo si se decide que calza en "problemas de concurrencia" sin tocar contratos. Señalado aquí para que no se pierda de vista. |
| A4 — historial sin paginar | Doc 18 | P3, sin síntoma real hoy. |
| C1 — respuestas de IA fuera de orden (sin lock por sala) | Doc 18 | Requiere diseño (cola/lock), no es un bug de "un paso que termina mal" sino una decisión de concurrencia — se deja para FASE 14 si aplica. |

## Verificación

- `python -m py_compile` sobre los 3 archivos modificados: limpio.
- `manage.py check`: limpio (único warning preexistente y no relacionado,
  `cart.Cart.user`).
- `pytest support/tests.py` (suite real de `WebsocketCommunicator` contra Redis real):
  **27 passed, 0 failed** (213s). Cobertura de `support/consumers.py`: 89% — confirma que
  los tests ya ejercitan connect/receive/disconnect/broadcast/AI-reply, no solo que el
  archivo compila. Cero regresiones introducidas por las trazas nuevas.

---

## FASE 3 — Auditoría del Consumer (`SupportChatConsumer`)

Mismo archivo que FASE 2 (`support/consumers.py`); el trabajo de tracing de la fase
anterior ya cubre casi todo este checklist. Métodos auditados uno por uno:

| Método | Estado | Nota |
|---|---|---|
| `connect()` | ✅ | Nunca termina sin `accept()` o `close()` explícito. Ambas ramas (admin/cliente) logueadas. |
| `disconnect()` | ✅ | Único camino, siempre limpia el grupo si llegó a asignarse. Logueado. |
| `receive()` | ✅ | 6 puntos de retorno temprano identificados (JSON inválido, ping, mensaje vacío, flood-limit, `room_uuid` faltante, sala no encontrada/cerrada) — los 5 que representan una condición anómala (todos salvo "mensaje vacío", que es un no-op legítimo del cliente) ahora quedan logueados con causa explícita. Ninguno deja el socket en un estado inconsistente: cada `return` ocurre antes de tocar BD o de hacer `group_send`. |
| `send()` | N/A como método propio | `AsyncWebsocketConsumer.send()` es de la librería (Channels); el código propio usa `self.send(text_data=json.dumps(...))` en 2 puntos (`connect`, y los handlers `chat_message`/`room_closed`) — ambos con payload bien formado, sin ruta de excepción no capturada. |
| `_ai_reply()` | ✅ | Reescrito con medición de latencia (`time.monotonic()`) y logging de los 4 desenlaces posibles: `status=ok`, `status=degraded` (motor sin respuesta), `status=exception` (con traceback), y `status=escalated` cuando hay Human Handoff. Antes solo el camino de excepción dejaba rastro. |
| `group_send()` | ✅ | 6 llamadas en el archivo, todas con `type` correcto (`chat.message`/`room.closed` → resueltos por Channels a `chat_message`/`room_closed`). Broadcast simétrico ya corregido en doc 18 (C2). |
| `history()` | No existe como método propio | El envío de historial ocurre inline en `connect()` (`_get_room_history()` + `send(type='history', ...)`), no como un handler de mensaje separado — arquitectura válida (el historial es parte del handshake inicial, no un mensaje bajo demanda). |
| `mark_read()` | No vive en el Consumer | `ChatCommands.mark_messages_read()` se invoca desde `AdminSupportChatViewSet` (REST, `support/api/views.py`), no desde el WebSocket — el checklist del brief asumía que podía vivir aquí; en esta arquitectura marcar-como-leído es una acción REST del dashboard (auditada en FASE 10), no un mensaje WS. Nota arquitectónica, no un defecto. |

**Ningún método termina anticipadamente sin dejar rastro.** Los `return` tempranos que sí
existen (por diseño: mensaje vacío, `ping`, contexto ya vinculado) son comportamientos
esperados, no fallos silenciosos — se distinguieron explícitamente de los que sí ameritaban
un log de advertencia.

## Roadmap — estado actualizado

| Fase (brief 2026-08-07) | Estado |
|---|---|
| FASE 2 — Auditoría WebSocket | **Hecha.** Checklist 14/14 validado, trazas agregadas, `SUPPORT_DEBUG_MODE` nuevo, cero regresiones de código (solo logging aditivo). |
| FASE 3 — Auditoría del Consumer | **Hecha.** 8/8 métodos del checklist revisados (2 no aplican tal como estaba planteado el checklist, con nota arquitectónica). 27/27 tests pasando. |
| FASE 4-15 | Pendientes. |
