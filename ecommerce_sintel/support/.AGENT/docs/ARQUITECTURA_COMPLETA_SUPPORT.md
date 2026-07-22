# ARQUITECTURA COMPLETA — APP support

Ultima actualizacion: 2026-07-20

> **[ACTUALIZADO 2026-07-20]** Este documento describia support como un chat WebSocket
> "guardar mensaje + broadcast" sin ninguna integracion de IA. Eso quedo desactualizado desde
> 2026-07-16: existe un puente real con el AI Engine (`support/services/ai_bridge.py`),
> Human Handoff (`ChatRoom.ai_paused`) y, desde esta sesion, telemetria por turno
> (`ChatMessage.ai_metrics`). Ver seccion "Integracion con AI Engine" mas abajo.

> **[CORREGIDO 2026-07-03]** La version anterior de este documento (2026-06-27) describia una
> REST API propia (`ChatRoomViewSet`, `/api/v1/support/rooms/...`) y un WebSocket por sala
> (`ws/support/<room_uuid>/`) que **no existen en el codigo**. Verificado exhaustivamente:
> `support/api/` solo contiene `serializers.py` (sin `views.py` ni `urls.py`), y `support` **no
> esta `include()`do en `ecommerce/urls.py`** — no existe ninguna ruta `/api/v1/support/`.
> Reescrito para reflejar el flujo real: 100% WebSocket para el cliente, gestion admin via el
> BFF de `dashboard`.

## Responsabilidad

Chat de soporte en tiempo real entre clientes y administradores.
Usa Django Channels (WebSocket) con autenticacion JWT via query param.
No expone una REST API propia — la unica interfaz de cliente es el WebSocket; la gestion admin
vive en el BFF de `dashboard` (`AdminSupportChatViewSet`).

---

## Estructura de Directorios (real)

```
support/
├── models.py              # ChatRoom (+ai_paused), ChatMessage (+ai_metrics), ChatRoomContext
├── consumers.py           # SupportChatConsumer (WebSocket, unico consumer; invoca ai_bridge)
├── channels_auth.py       # JWTAuthMiddleware / JWTAuthMiddlewareStack para Channels
├── routing.py             # support_websocket_patterns — UNA sola ruta fija
├── services/
│   ├── commands.py        # ChatCommands
│   ├── selectors.py       # ChatSelector
│   ├── ai_bridge.py       # Puente Django -> AI Engine (POST /chat), Human Handoff
│   └── customer360.py     # Timeline unificado (Customer Experience Hub)
├── api/
│   ├── serializers.py     # ChatRoomSerializer, ChatRoomListSerializer (consumidos por dashboard)
│   └── internal_ai.py     # AiOpenSupportTicketView — endpoint interno para el AI Engine
│                           # NO existe api/views.py ni api/urls.py publicos
├── admin.py
├── migrations/
└── apps.py
```

---

## Modelos (verificados contra `support/models.py`)

### ChatRoom

```python
class ChatRoom(SintelBaseModel):
    STATUS_OPEN   = 'OPEN'
    STATUS_CLOSED = 'CLOSED'

    user           = ForeignKey(AUTH_USER_MODEL, related_name='support_rooms')
    status         = CharField(choices=STATUS_CHOICES, default=STATUS_OPEN)
    assigned_admin = ForeignKey(AUTH_USER_MODEL, null=True, blank=True,
                                related_name='assigned_support_rooms')
    ai_paused      = BooleanField(default=False)  # True = IA escalo a un humano (Human Handoff)

    class Meta:
        ordering = ['-updated_at']
```

- Un usuario puede tener multiples salas historicas, pero solo una `OPEN` a la vez
  (`ChatCommands.get_or_create_room()` reutiliza la abierta si existe).
- `assigned_admin`: se asigna cuando un admin abre la sala (`assign_admin`), no automaticamente.
- `status=CLOSED`: sala cerrada. El consumer no valida el estado al recibir mensajes del cliente
  (solo el admin valida `status=STATUS_OPEN` al enviar, ver `_get_room_and_client_uuid`).

### ChatMessage

```python
class ChatMessage(SintelBaseModel):
    room       = ForeignKey(ChatRoom, related_name='messages')
    sender     = ForeignKey(AUTH_USER_MODEL, related_name='support_messages')
    message    = TextField()          # <- el campo se llama 'message', NO 'content'
    is_read    = BooleanField(default=False)
    ai_metrics = JSONField(null=True, blank=True)  # telemetria del turno IA, null si es humano

    class Meta:
        ordering = ['created_at']
```

---

## WebSocket (el unico canal de interaccion del cliente)

### Ruta real — UNA sola, fija, no por sala

```
ws://host/ws/support/chat/
```

Registrada en `support/routing.py`:
```python
support_websocket_patterns = [
    path('ws/support/chat/', SupportChatConsumer.as_asgi()),
]
```
Incluida en `ecommerce/routing.py` junto a `operations`.

### Consumer: `SupportChatConsumer` (`support/consumers.py`)

**`connect()`** bifurca segun el usuario:

- **Admin** (`user.is_staff and user.is_superuser`): se une al grupo global `support_admins`.
  No recibe historial automaticamente al conectar — la gestion de salas/historial la hace via
  el BFF REST de `dashboard` (ver seccion siguiente), el WebSocket admin solo recibe mensajes
  entrantes en tiempo real.
- **Cliente regular**: `ChatCommands.get_or_create_room(user)` obtiene/crea su sala `OPEN`, se
  une al grupo `chat_{user.uuid}`, y recibe inmediatamente un evento `{"type": "history",
  "room_uuid": ..., "messages": [...]}` con el historial completo de la sala.

**`receive()`** — mensaje entrante `{"message": "texto"}`:

- Si el sender es admin: requiere `room_uuid` en el payload (a que sala responde), guarda el
  mensaje, y lo reenvia al grupo `chat_{client_uuid}` del cliente especifico.
- Si el sender es cliente: guarda el mensaje en su sala activa y lo reenvia al grupo global
  `support_admins` (todos los admins conectados lo reciben).

**Evento saliente (ambos casos):**
```json
{
  "type": "chat_message",
  "message": "texto",
  "sender_email": "...",
  "is_admin": true,
  "room_uuid": "...",
  "created_at": "..."
}
```

### Autenticacion — `JWTAuthMiddleware` (`support/channels_auth.py`)

Token JWT pasado como **query param** (no header, WebSocket no soporta headers custom desde el
navegador facilmente): `ws://host/ws/support/chat/?token=<jwt>`.

```python
class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        # parsea ?token=<jwt> de la query string
        # valida con rest_framework_simplejwt.tokens.AccessToken
        # scope['user'] = User real o AnonymousUser si falla
```

`connect()` cierra la conexion con `code=4001` si `scope['user']` no esta autenticado.

**Anti-patron (ya documentado antes, sigue vigente):** nunca importar
`rest_framework_simplejwt` al nivel de modulo en `channels_auth.py`/`consumers.py` — causa
`ImportError` en el arranque de Channels porque Django no esta listo. Siempre import diferido
dentro de la funcion/metodo.

---

## Gestion administrativa — vive en `dashboard`, NO en `support`

No existe `/api/v1/support/...`. La gestion de salas para el panel admin (`/panel/soporte`) se
hace via `AdminSupportChatViewSet` en `dashboard/api/views.py`, que delega a
`SupportAdminOrchestrator` (`dashboard/services/admin_orchestrators.py`), que a su vez llama a
`ChatCommands`/`ChatSelector` de esta app.

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/v1/dashboard/support/chats/` | GET | Lista salas activas (`ChatSelector.get_active_rooms()`) |
| `/api/v1/dashboard/support/chats/<uuid>/` | GET | Detalle + marca mensajes como leidos (`mark_read`) |
| `/api/v1/dashboard/support/chats/<uuid>/close/` | POST | Cierra la sala (`ChatCommands.close_room`) |
| `/api/v1/dashboard/support/chats/<uuid>/assign/` | POST | Asigna la sala al admin que hace la request (`ChatCommands.assign_admin`) |

Todos requieren `IsAuthenticated + IsAdminUser` (permisos estandar de `dashboard`).

### Services (`support/services/`)

```python
class ChatCommands:
    get_or_create_room(user) -> ChatRoom       # reutiliza la OPEN existente si hay
    save_message(room, sender, text) -> ChatMessage
    close_room(room) -> ChatRoom               # status = CLOSED
    assign_admin(room, admin) -> ChatRoom
    mark_messages_read(room, reader) -> None   # marca no leidos de OTROS senders

class ChatSelector:
    get_active_rooms()          # status=OPEN, is_deleted=False, con user/assigned_admin/messages
    get_room_by_uuid(uuid)
    get_room_history(room)      # mensajes ordenados por created_at ascendente
```

### Panel admin (`/panel/soporte`)

Vista dos columnas (`SupportDashboardView.vue`, en `frontend/src/modules/support/`):
- Columna izquierda: lista de salas abiertas (via REST `dashboard/support/chats/`).
- Columna derecha: historial + input — el envio/recepcion en vivo pasa por el WebSocket
  `ws/support/chat/`, no por REST.

### UI cliente

Widget flotante global (no una ruta dedicada en el router) que abre la conexion WebSocket
directamente al montarse para el usuario autenticado.

---

## Integracion con AI Engine (Fases 7-8 AI Core)

El AI Engine (`ai_engine/`, microservicio FastAPI separado, `settings.AI_ENGINE_URL`) actua
como primer nivel de respuesta cuando la sala esta en "modo AI". `support` es solo el canal —
la decision y ejecucion vive en el AI Engine (Action Graph, Agent Profiles, Tools).

### `support/services/ai_bridge.py`

```python
ask_ai(user, message, conversation_id) -> dict | None
    # POST {AI_ENGINE_URL}/chat con JWT efimero del usuario real (AccessToken.for_user)
    # timeout 300s; None si el motor no responde o status != 200 (degrada, no excepciona)
    # Respuesta incluye: response, tool_calls, tool_results, agent, intent, metrics (Fase 8)

is_ai_mode_active(room) -> bool
    # True solo si settings.AI_SUPPORT_CHAT_ENABLED, room.status == OPEN,
    # not room.ai_paused, y room.assigned_admin is None

get_ai_bot_user()          # usuario bot inactivo/sin password que firma los mensajes IA
ai_response_opened_ticket(ai_response)  # True si el turno ejecuto la Tool "abrir_ticket_soporte"
```

### Flujo en `SupportChatConsumer.receive()`

Tras guardar y reenviar el mensaje del cliente a `support_admins`, si `is_ai_mode_active(room)`
es `True` se lanza `asyncio.create_task(self._ai_reply(room, text))` (no bloquea el socket).
`_ai_reply` llama `ask_ai()`, guarda la respuesta del bot con
`ChatCommands.save_message(room, bot, ..., ai_metrics=ai_response.get('metrics'))`, y hace
`group_send` tanto al cliente (`chat_{user.uuid}`) como a `support_admins` (supervision humana
en vivo) — el bot se muestra del lado "agente" en el widget.

### Human Handoff (`ChatRoom.ai_paused`)

Si el turno ejecuta la Tool `abrir_ticket_soporte`, `AiOpenSupportTicketView`
(`support/api/internal_ai.py`, endpoint interno consumido por el AI Engine, no publico) vuelca
la transcripcion previa, guarda el mensaje que dispara el escalamiento, marca
`room.ai_paused = True` y notifica a `support_admins` por Channels. Con `ai_paused=True`,
`is_ai_mode_active()` devuelve `False` y el consumer deja de invocar al AI Engine en esa sala
hasta que un admin la reabra (flujo manual, no hay endpoint de "reanudar IA" hoy).

### Telemetria por turno — `ChatMessage.ai_metrics` (Fase 8, 2026-07-20)

`ai_engine/observability.py::TurnMetrics` calcula por turno: `agent`, `intent`, `llm_calls`,
`llm_tokens_in/out`, `tool_calls`, `tool_errors`, `tools` (lista `{tool, ms, ok}`),
`fallback_used`, `handoff`, `needs_confirmation`, `write_executed`, `duration_ms`. Antes solo
se emitia a un logger (`logging.getLogger("observability")`) y se descartaba; ahora
`run_action_chat` lo incluye en la respuesta de `POST /chat` (campo `metrics`) y
`_save_ai_message_and_maybe_pause` lo persiste en `ChatMessage.ai_metrics` (JSONField
nullable — `None` para mensajes humanos). Expuesto solo en `ChatMessageSerializer`, consumido
por `AdminSupportChatViewSet` (dashboard) y renderizado como badges en
`SupportDashboardView.vue`. **No se toco `chat_message()` (el broadcast WS)** — sigue
reenviando solo `message/sender_email/is_admin/room_uuid/created_at`, asi que la telemetria
nunca viaja por el canal en vivo (ni al cliente ni al admin); solo se ve al abrir/reabrir la
sala por REST. No existe un "confidence score" calculado por el motor.

---

## Notificaciones

`support/services/commands.py` **no llama a `NotificationCommands.dispatch_notification()`
directamente en el codigo actual** (no se encontro esa llamada en `ChatCommands`). Si se agrega
notificacion push/email por mensaje nuevo, debe hacerse siguiendo el patron centralizado de la
app `notifications` (`NotificationCommands.dispatch_notification()` dentro de
`transaction.on_commit(...)`), no un `ws_notify` ad-hoc.

---

## Anti-Patrones Prohibidos

```python
# INCORRECTO — autenticar en consumer sin import diferido
from rest_framework_simplejwt.authentication import JWTAuthentication  # al nivel modulo
# Causa ImportError en arranque de Channels porque Django no esta listo

# CORRECTO — import dentro del metodo (ver channels_auth.py, consumers.py)
```

```python
# INCORRECTO — asumir que existe una REST API en /api/v1/support/
# No existe. Toda interaccion de cliente es WebSocket; la gestion admin vive en
# /api/v1/dashboard/support/chats/
```

---

## Cambios Recientes

### 2026-07-20 — Documentada integracion AI Engine (ya existia, Fases 7) + Fase 8 telemetria
- Se agrego la seccion "Integracion con AI Engine" — el documento no mencionaba `ai_bridge.py`,
  `ChatRoom.ai_paused` (Human Handoff, en produccion desde 2026-07-16) ni `api/internal_ai.py`.
- Nuevo campo `ChatMessage.ai_metrics` (JSONField nullable, migracion `0006`): persiste la
  telemetria por turno que el AI Engine ya calculaba (`observability.py::TurnMetrics`) pero
  antes se descartaba tras loguearla. Expuesto en el Dashboard admin, nunca por WebSocket.

### 2026-07-03 — Correccion completa contra codigo real
- Se elimino la documentacion de una REST API (`ChatRoomViewSet`, `/api/v1/support/rooms/...`)
  y un WebSocket por sala (`ws/support/<room_uuid>/`) que nunca existieron en el codigo.
- Documentada la ruta WebSocket real, unica y fija: `ws/support/chat/`.
- Documentado que la gestion admin vive en `dashboard/api/views.py::AdminSupportChatViewSet`
  bajo `/api/v1/dashboard/support/chats/`, no en esta app.
- Corregido el nombre del campo `ChatMessage.message` (el doc anterior decia `content`).

### 2026-06-27 — Documento inicial creado (contenido incorrecto, reemplazado 2026-07-03)
- Primera version del documento de arquitectura — describia una arquitectura aspiracional que
  nunca se implemento tal cual.
