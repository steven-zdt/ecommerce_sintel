# ARQUITECTURA COMPLETA — APP support

Ultima actualizacion: 2026-07-31

> **[CORREGIDO 2026-07-31, Auditoria Enterprise §15]** Este documento afirmaba (desde la version
> 2026-07-03) que `support` **no tiene REST API propia** — quedo desactualizado desde que se
> agrego el endpoint CSAT (`RateConversationView`, `api/views.py` + `api/urls.py`, ver §"REST
> publica"). Ya estaba detectado y dejado pendiente en
> `Documentacion/Arquitectura_general/IMPLEMENTATION_SUMMARY.md` desde 2026-07-23 sin corregirse.
> Ademas: se documenta `support/tasks.py` (llama a `NotificationCommands` -- la seccion
> "Notificaciones" decia lo contrario), la estructura real de directorios (faltaban
> `api/views.py`, `api/urls.py`, `tasks.py`), los campos CSAT de `ChatRoom` y el modelo
> `ChatRoomContext`, y `ChatAnalyticsSelector`. Tambien se documentan 8 correcciones reales
> aplicadas el mismo dia (bot IA mal atribuido en REST, rate-limit de IA, visibilidad de caidas
> del motor, validacion de estado en sala cerrada, duplicacion WS/REST) — ver "Cambios Recientes".

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
Usa Django Channels (WebSocket) con autenticacion JWT via query param — esa sigue siendo la
**unica** interfaz para enviar/recibir mensajes en vivo. `support` expone una REST API propia
pero minima (CSAT, ver mas abajo); la gestion admin de salas (listar, cerrar, asignar) sigue
viviendo en el BFF de `dashboard` (`AdminSupportChatViewSet`), no aca.

---

## Estructura de Directorios (real)

```
support/
├── models.py              # ChatRoom (+ai_paused, +CSAT), ChatMessage (+ai_metrics), ChatRoomContext
├── consumers.py           # SupportChatConsumer (WebSocket, unico consumer; invoca ai_bridge)
├── channels_auth.py       # JWTAuthMiddleware / JWTAuthMiddlewareStack para Channels
├── routing.py             # support_websocket_patterns — UNA sola ruta fija
├── tasks.py               # notify_unattended_escalated_tickets (Celery Beat, Fase 11 Proactividad)
├── services/
│   ├── commands.py        # ChatCommands
│   ├── selectors.py       # ChatSelector, ChatAnalyticsSelector (Fase 9, KPIs del Dashboard)
│   ├── ai_bridge.py       # Puente Django -> AI Engine (POST /chat), Human Handoff, rate-limit
│   └── customer360.py     # Timeline unificado (Customer Experience Hub)
├── api/
│   ├── serializers.py     # ChatRoomSerializer, ChatRoomListSerializer (consumidos por dashboard)
│   ├── views.py           # RateConversationView — CSAT, unica REST publica del cliente
│   ├── urls.py             # api/v1/support/chats/<uuid>/rate/
│   └── internal_ai.py     # AiOpenSupportTicketView — endpoint interno para el AI Engine
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
    # CSAT (migracion 0008): calificacion del cliente tras cerrar la sala.
    csat_rating    = PositiveSmallIntegerField(null=True, blank=True)  # 1-5
    csat_comment   = TextField(blank=True, default='')
    csat_rated_at  = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']
```

- Un usuario puede tener multiples salas historicas, pero solo una `OPEN` a la vez
  (`ChatCommands.get_or_create_room()` reutiliza la abierta si existe).
- `assigned_admin`: se asigna cuando un admin abre la sala (`assign_admin`), no automaticamente.
- `status=CLOSED`: sala cerrada. **[CORREGIDO 2026-07-31]** Antes el consumer NO validaba el
  estado al recibir mensajes del cliente (solo el admin validaba `status=STATUS_OPEN` al enviar,
  ver `_get_room_and_client_uuid`) — un cliente podia seguir escribiendo en una sala ya cerrada,
  sin ruta de respuesta. Ahora la rama cliente de `receive()` tambien valida
  `status=STATUS_OPEN` (`_room_is_open`) antes de guardar.
- `csat_rating`/`csat_comment`/`csat_rated_at`: se setean una unica vez, solo sobre una sala ya
  `CLOSED`, via `ChatCommands.rate_conversation()` — expuesto por `RateConversationView` (REST).

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

    @property
    def is_from_agent(self) -> bool:
        # True si staff+superuser O el sender es el bot IA (settings.AI_BOT_EMAIL).
        ...
```

**[CORREGIDO 2026-07-31]** `is_from_agent` es la unica fuente de verdad para "¿este mensaje va
del lado agente?" en el widget/dashboard. Antes `ChatMessageSerializer.get_is_admin()` (payload
REST, historial del dashboard) solo chequeaba `is_staff and is_superuser` -- el bot IA nunca
cumple eso (se crea con `is_active=False`), asi que los mensajes de la IA se atribuian al
**cliente** en el panel admin vía REST, mientras que por WebSocket (`consumers.py`) se marcaban
bien como agente. Ambos puntos ahora reusan `is_from_agent`.

### ChatRoomContext

```python
class ChatRoomContext(SintelBaseModel):
    CONTEXT_ORDER = 'ORDER'
    CONTEXT_RENTAL = 'RENTAL'

    room           = ForeignKey(ChatRoom, related_name='contexts')
    context_type   = CharField(choices=CONTEXT_CHOICES)
    order          = ForeignKey('orders.Order', null=True, blank=True, on_delete=CASCADE)
    rental_request = ForeignKey('renting.RentalRequest', null=True, blank=True, on_delete=CASCADE)
    added_by       = ForeignKey(AUTH_USER_MODEL, null=True, blank=True, on_delete=SET_NULL)

    class Meta:
        constraints = [CheckConstraint(...)]  # exactamente un target (order XOR rental_request)

    @property
    def target_uuid(self) -> str | None: ...  # uuid de la entidad referenciada
    @property
    def label(self) -> str: ...               # "Pedido #123" / "Alquiler #45"
```

Vinculo opcional de una sala a una entidad de negocio (Customer Experience Hub, Fase 3) — FKs
reales por tipo, NO GenericForeignKey (ese patron ya genero un bug real en `inventory`). Una sala
puede tener varios contextos (una fila por cada uno). `CASCADE` (no `SET_NULL`) en `order`/
`rental_request`: si la entidad se borra de verdad, la fila de contexto debe desaparecer con
ella, o violaria la constraint de "exactamente un target". **[CORREGIDO 2026-07-31]**
`target_uuid`/`label` son la unica fuente de verdad para "uuid/etiqueta legible" — antes esa
misma rama `ORDER->Pedido #.../RENTAL->Alquiler #...` estaba duplicada, con codigo casi identico
pero independiente, en `consumers.py::_get_room_contexts` (payload WS) y en
`ChatRoomContextSerializer` (payload REST).

### SupportTicket (2026-09-15 -- objeto de trabajo, separado de la conversacion)

```python
class SupportTicket(SintelBaseModel):
    ticket_number  = CharField(unique=True, null=True, blank=True)  # 'SUP-000123', pk-based
    chat_room      = OneToOneField(ChatRoom, related_name='ticket')

    subject        = CharField(max_length=200, blank=True, default='')
    summary        = TextField(blank=True, default='')

    status         = CharField(choices=[NEW,OPEN,IN_PROGRESS,WAITING_CUSTOMER,RESOLVED,CLOSED,CANCELLED], default=NEW)
    priority       = CharField(choices=[LOW,NORMAL,HIGH,URGENT], default=NORMAL)
    category       = CharField(choices=[ACCOUNT,ORDER,PAYMENT,PRODUCT,RENTING,TECHNICAL,DELIVERY,OTHER], blank=True)

    assigned_admin = ForeignKey(AUTH_USER_MODEL, null=True, blank=True, related_name='assigned_support_tickets')
    contact_phone  = CharField(max_length=20, blank=True, default='')  # SNAPSHOT, no FK viva
    contact_email  = EmailField(blank=True, default='')                # SNAPSHOT, no FK viva

    resolved_at    = DateTimeField(null=True, blank=True)
    closed_at      = DateTimeField(null=True, blank=True)
```

**Por que existe:** antes de esto, "abrir un ticket" (`OpenSupportTicketTool`) solo dejaba
`ChatRoom.ai_paused=True` -- no habia ninguna entidad de negocio con asunto, prioridad,
categoria o numero visible para el operador humano; lo que se veia en `/panel/soporte` era una
conversacion, no un objeto de trabajo. `ChatRoom`/`ChatMessage` siguen siendo la SSoT de la
conversacion en si, sin cambios.

- **OneToOne deliberado** (no ForeignKey): hoy solo hay UN flujo real de creacion (Human Handoff
  via `OpenSupportTicketTool`), siempre sobre la sala resuelta por
  `ChatCommands.get_or_create_room()` -- una sala nunca tiene mas de un ticket de trabajo activo.
- **`ticket_number`**: generado a partir del `pk` autoincremental real (`SUP-{pk:06d}`), NO
  aleatorio -- deliberadamente distinto del patron de `operations.OperationTicket`
  (`OP-{año}-{uuid4().hex[:8]}`, ver `operations/services/commands.py::_generate_ticket_number`)
  porque el objetivo aca es que sea memorable/secuencial para el cliente y el operador, no unico
  por azar. `null=True` hasta el primer `save()` posterior al INSERT (Postgres permite varios
  NULL bajo `unique=True` sin chocar).
- **`contact_phone`/`contact_email` son SNAPSHOT**, no `ticket.chat_room.user.profile.
  phone_number` en vivo -- si el cliente cambia su telefono despues, el ticket debe seguir
  mostrando el dato de contacto real que tenia al momento de abrirse. El campo maestro real de
  telefono es `accounts.UserProfile.phone_number` (mismo que ya usa
  `notifications.tasks.process_whatsapp_inbound_task` para resolver el usuario por WhatsApp) --
  `users.User` NO tiene telefono propio. `UserProfile` puede no existir (sin señal `post_save`
  en `User` que lo garantice) -- el snapshot usa `getattr` seguro, nunca rompe la creacion.
- **`SupportTicketCommands.create_ticket()`** (`support/services/commands.py`) es idempotente por
  sala: si el cliente vuelve a escribir sobre una sala ya escalada, reusa el ticket existente y
  solo completa `subject`/`summary`/`category` si venian vacios -- nunca pisa lo que un humano ya
  edito despues.
- **`OpenSupportTicketTool`** (`ai_engine/tools/support_tools.py`) ahora acepta `subject`/
  `summary` opcionales del LLM (ademas de `message`, que sigue siendo obligatorio) -- el backend
  sigue siendo la autoridad que crea el ticket, el LLM nunca toca el ORM.
- **Dashboard/BFF de tickets: NO CONSTRUIDO todavia** (`AdminSupportChatViewSet` sigue exactamente
  igual que antes, sin tocar) -- `SupportTicket` hoy solo es consultable via Django Admin o ORM
  directo. Cola/asignacion/SLA/auditoria de eventos (equivalentes a FASE 6-10 de un plan de mesa
  de ayuda completo) quedan pendientes, requieren decision de producto explicita antes de
  construirse (superficie nueva de API + UI, no solo el modelo).

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

**[BUG REAL DE PRODUCCION, CORREGIDO 2026-07-31]** El WS solo se autentica UNA vez, al conectar.
`ACCESS_TOKEN_LIFETIME` es 15 min, y el interceptor de Axios que refresca el token sola nunca
corre para conexiones WebSocket — cualquier tab abierta mas de 15 min reutilizaba un access token
vencido en cada reintento automatico (cada ~3s, para siempre), mostrando "Desconectado"
permanente en `SupportChatWidget.vue`/`SupportDashboardView.vue`. Causa raiz confirmada en vivo
en produccion via `ExpiredTokenError` (antes `_get_user_from_token` tragaba la excepcion en
silencio -- ahora loguea con `logger.warning`, ver `channels_auth.py`). Fix: ambos widgets
refrescan el access token proactivamente (`useAuth().refreshAccessToken()`) antes de cada intento
de conexion; si el refresh TAMBIEN falla (refresh token vencido, sesion realmente muerta), se
hace `logout()` + aviso al usuario en vez de reintentar en loop infinito con un token muerto.

---

## REST publica del cliente — CSAT (`api/views.py`)

**[CORREGIDO 2026-07-31]** A diferencia de lo que este documento afirmaba, `support` SI expone
una REST publica minima -- solo para calificar una conversacion ya cerrada:

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/api/v1/support/chats/<uuid>/rate/` | POST | CSAT: `{rating: 1-5, comment?}` sobre una sala `CLOSED` propia (`RateConversationView` -> `ChatCommands.rate_conversation`) |

Permiso: `IsAuthenticated` + lookup scoped a `request.user` desde el inicio (una sala ajena da
`404`, igual que una inexistente -- nunca se revela si "existe" antes de chequear ownership).
Toda la DEMAS interaccion de cliente sigue siendo 100% WebSocket.

---

## Gestion administrativa de salas — vive en `dashboard`, NO en `support`

La gestion de salas para el panel admin (`/panel/soporte`, listar/cerrar/asignar) se
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
    get_contexts_for_room(room)

class ChatAnalyticsSelector:    # Fase 9 AI Core (Aprendizaje) -- agrega ChatMessage.ai_metrics
    get_summary(days=30) -> dict
        # total_conversations, avg_csat, total_ai_turns, avg_duration_ms, avg_tokens_in/out,
        # fallback_rate, handoff_rate, engine_unavailable_count/_rate (§C2, 2026-07-31),
        # intent_breakdown, top_tools, frequent_issues -- consumido por SupportDashboardView.vue
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
is_ai_rate_limited(room) -> bool  # [NUEVO 2026-07-31] ver "Rate limit de IA" mas abajo
```

### Flujo en `SupportChatConsumer.receive()`

Tras guardar y reenviar el mensaje del cliente a `support_admins`, si `is_ai_mode_active(room)`
**y no `is_ai_rate_limited(room)`** es `True` se lanza `asyncio.create_task(self._ai_reply(room,
text))` (no bloquea el socket). `_ai_reply` llama `ask_ai()`, guarda la respuesta del bot con
`ChatCommands.save_message(room, bot, ..., ai_metrics=ai_response.get('metrics'))`, y hace
`group_send` tanto al cliente (`chat_{user.uuid}`) como a `support_admins` (supervision humana
en vivo) — el bot se muestra del lado "agente" en el widget.

### Rate limit de IA (`is_ai_rate_limited`, corregido 2026-07-31)

**[GAP CERRADO]** El unico throttle de IA que existia (D-03, auditoria previa) era un
`ScopedRateThrottle` en `AiOpenSupportTicketView` — un endpoint interno SECUNDARIO. El punto de
entrada real que dispara `ask_ai()` (costo de LLM real) por cada mensaje de cliente es este WS,
que no tenia ningun limite. Ahora `is_ai_rate_limited(room)` usa un contador atomico en cache
(`cache.add`/`cache.incr`, ventana fija): **20 turnos de IA por sala cada 10 min**
(`AI_CHAT_RATE_LIMIT`/`AI_CHAT_RATE_WINDOW_SECONDS` en `ai_bridge.py`). Al limite: el mensaje del
cliente se guarda y muestra igual (el humano lo ve), solo se omite la respuesta de la IA para ese
turno.

### Visibilidad de caidas del AI Engine (corregido 2026-07-31)

**[GAP CERRADO]** Antes, si `ask_ai()` devolvia `None` (motor inalcanzable o error), `_ai_reply`
retornaba en silencio total: nada se persistia, el cliente no recibia ningun aviso, y
`ChatAnalyticsSelector` (que solo agrega `ai_metrics` ya persistidos) no tenia forma de detectar
la caida. Ahora se persiste un `ChatMessage` del bot con `ai_metrics={'engine_unavailable':
True}` y un texto de degradacion ("Un agente humano revisara tu mensaje pronto"), enviado igual
que un turno normal por WS. `ChatAnalyticsSelector.get_summary()` cuenta estos marcadores APARTE
de `total_ai_turns` (no ensucian promedios/tasas de turnos reales) y expone
`engine_unavailable_count`/`engine_unavailable_rate` — visible como KPI en
`SupportDashboardView.vue`.

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

## Notificaciones — `support/tasks.py` (Fase 11 AI Core, Proactividad)

**[CORREGIDO 2026-07-31]** `ChatCommands` en si mismo sigue sin llamar a
`NotificationCommands.dispatch_notification()` (el guardado de mensajes no dispara
notificaciones), pero `support/tasks.py::notify_unattended_escalated_tickets` **si** lo hace:

```python
@shared_task
def notify_unattended_escalated_tickets() -> None:
    # Cron horaria (Celery Beat, migracion 0007_seed_notify_stale_tickets_periodic_task).
    # Busca ChatRoom: status=OPEN, ai_paused=True (escalada a humano), sin actividad hace
    # mas de _UNATTENDED_THRESHOLD_HOURS (2h). Por cada una:
    NotificationCommands.dispatch_notification_once(
        user=room.user, template_slug='ticket_soporte_sin_seguimiento',
        context={'room_uuid': str(room.uuid)}, dedupe_key=f'chatroom:{room.uuid}',
    )
    # dispatch_notification_once (variante para scanners periodicos): dedupe SINCRONO via
    # NotificationLog antes de llamar a dispatch_notification() -- cada sala se notifica
    # UNA sola vez, sin importar cuantas veces corra el scan mientras siga sin atenderse.
```

Si se agrega notificacion por mensaje nuevo (no por inactividad), debe seguir el mismo patron
centralizado (`NotificationCommands.dispatch_notification()` dentro de
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
# INCORRECTO — asumir que support tiene una REST API completa de gestion de salas
# ([CORREGIDO 2026-07-31] SI existe una REST publica, pero minima: solo CSAT
# (/api/v1/support/chats/<uuid>/rate/). Listar/cerrar/asignar salas sigue viviendo
# en /api/v1/dashboard/support/chats/, no aca.)
```

```python
# INCORRECTO — reusar una clase con costo real (mensaje al LLM) sin rate-limit
if is_ai_mode_active(room):
    asyncio.create_task(self._ai_reply(room, text))  # sin limite -- ver "Rate limit de IA"

# CORRECTO
if is_ai_mode_active(room) and not is_ai_rate_limited(room):
    asyncio.create_task(self._ai_reply(room, text))
```

---

## Cambios Recientes

### 2026-09-15 — Modelo `SupportTicket` (objeto de trabajo, separado de ChatRoom)
- **Que cambio y por que**: `OpenSupportTicketTool` solo pausaba la IA en `ChatRoom` -- no
  existia ninguna entidad de negocio con asunto/prioridad/categoria/numero para el operador
  humano. Nuevo modelo `SupportTicket` (OneToOne con `ChatRoom`) + `SupportTicketCommands`/
  `SupportTicketSelector` en `support/services/`. Ver seccion "Modelos" arriba para el detalle
  completo (ticket_number, snapshot de contacto, idempotencia).
- **Archivos afectados**: `support/models.py` (+`SupportTicket`), `support/migrations/
  0010_supportticket.py`, `support/services/commands.py` (+`SupportTicketCommands`),
  `support/services/selectors.py` (+`SupportTicketSelector`), `support/admin.py` (+registro),
  `support/api/internal_ai.py::AiOpenSupportTicketView` (crea el ticket, snapshot de contacto,
  `ticket_number`/`subject` en la respuesta -- `room_uuid`/`status`/`attached_context`/`detail`
  se mantienen intactos, retrocompatible), `ai_engine/tools/support_tools.py::
  OpenSupportTicketTool` (+`subject`/`summary` opcionales en `args_schema`).
- **Contrato API**: `POST /api/v1/internal/ai/support/ticket/` ahora acepta `subject`/`summary`
  opcionales en el body y devuelve `ticket.ticket_number`/`ticket.subject` ademas de los campos
  previos (aditivo, nada se quito ni se renombro).
- **Tests**: 7 tests nuevos en `support/tests.py` (creacion con numero/asunto/contacto real via
  el endpoint, usuario sin `UserProfile` no rompe, idempotencia sin pisar subject, generacion de
  numero, transiciones de estado, filtros del selector). Suite completa `support` verificada
  real contra el contenedor dev (pytest no estaba instalado en la imagen -- instalado ad-hoc para
  poder correr la suite de verdad, no asumir): **37/37 passed**. Regresion `ai_engine`(OLD)
  112/16, `ai_engine_adk` smoke real end-to-end (Tool Registry -> http_bridge -> Django ->
  `SupportTicketCommands`) devolvio `SUP-000001` real contra el contenedor dev.
- **Migracion**: `0010_supportticket.py`, aditiva (tabla nueva), aplicada solo en dev, NO en
  produccion todavia.
- **Riesgos**: ninguno estructural -- tabla nueva, no toca `ChatRoom`/`ChatMessage`/
  `ChatRoomContext` ni ninguna vista/consumer existente. `AdminSupportChatViewSet` (dashboard) NO
  se toco -- el ticket hoy solo es visible via Django Admin/ORM, sin UI de mesa de ayuda.
- **Pendiente, requiere decision de producto separada**: dashboard de tickets (cola, asignacion,
  filtros), API BFF dedicada (`/api/v1/dashboard/support/tickets/...`), SLA/notificaciones sobre
  `SupportTicket` (hoy `notify_unattended_escalated_tickets` sigue mirando `ChatRoom.ai_paused`,
  sin tocar), y un `SupportTicketEvent` de auditoria de cambios de estado -- ninguno construido
  en esta sesion, deliberadamente, dado el alcance (nueva superficie de API + UI).

### 2026-07-31 — Auditoria Enterprise (AUDITORIA/15) — doc desincronizada + 8 correcciones reales
- **Documentacion**: corregidos 5 puntos desincronizados con el codigo real (este documento
  afirmaba que no existia REST API propia -- ya detectado y dejado pendiente en
  `IMPLEMENTATION_SUMMARY.md` desde 2026-07-23 sin corregirse hasta ahora; faltaban
  `tasks.py`/`api/views.py`/`api/urls.py` en la estructura; faltaban los campos CSAT de
  `ChatRoom`, el modelo `ChatRoomContext` completo, y `ChatAnalyticsSelector`).
- **Bug de produccion resuelto el mismo dia** (antes de esta auditoria): WS nunca refrescaba el
  JWT antes de conectar -- "Desconectado" permanente tras 15 min. Ver seccion "Autenticacion".
- **Correctitud**: `ChatMessage.is_from_agent` unifica la atribucion agente/cliente (antes el bot
  IA se mostraba como cliente en el historial REST del dashboard, bien por WS -- inconsistencia
  real). Cliente ya no puede seguir escribiendo en una sala `CLOSED` por WS (antes solo el admin
  validaba estado).
- **Seguridad/costo**: rate-limit real sobre el WS que dispara el LLM (antes solo protegido el
  endpoint interno secundario). Caida del AI Engine ahora deja un mensaje real al cliente + KPI
  visible en el dashboard (antes: silencio total, invisible en metricas).
- **DRY**: `ChatRoomContext.target_uuid`/`.label` reemplazan la logica duplicada WS/REST.
- **Tests**: 6 tests nuevos (CSAT REST end-to-end incl. el fix de disclosure D-04 que no tenia
  regresion; Human Handoff interno, sin cobertura previa en todo el repo; cron de tickets sin
  seguimiento; sala cerrada). Suite completa: 19/19 pasando.

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
