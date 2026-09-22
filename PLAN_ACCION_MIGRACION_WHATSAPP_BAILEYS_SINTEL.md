# PLAN DE ACCIÓN — MIGRACIÓN WHATSAPP WEB SESSION → BAILEYS
## Sintel E-Commerce REST / Support Center

**Fecha:** 2026-09-22  
**Objetivo:** reemplazar exclusivamente la conexión `QR Web Session (experimental)` de `/panel/soporte/whatsapp` por una integración basada en **Baileys**, manteniendo el dominio de soporte, conversaciones, IA y frontend actuales.

---

# 0. DECISIÓN ARQUITECTÓNICA

La implementación objetivo será:

```text
                         WhatsApp
                            ↕
                     WhatsApp Web
                            ↕
                    @whiskeysockets/baileys
                            ↕
                  WhatsApp Gateway
                   (Node.js/TypeScript)
                            ↕
                 API interna autenticada
                            ↕
                    Django / Support
                            ↕
             Support Services / Notifications
                            ↕
                 ChatRoom / mensajes
                            ↕
                      PostgreSQL
                            ↕
                 Google ADK Support Agent
```

### Decisiones obligatorias

1. **Baileys será un gateway independiente de Django.**
2. Django seguirá siendo la fuente de verdad del dominio comercial y de soporte.
3. El gateway NO tendrá modelos de negocio propios.
4. El gateway NO accederá directamente a PostgreSQL de Django.
5. El gateway NO ejecutará lógica de IA.
6. El gateway NO decidirá permisos de usuarios.
7. El gateway NO será responsable de crear clientes o `ChatRoom`.
8. El gateway solo manejará:
   - conexión WhatsApp;
   - autenticación/sesión;
   - QR;
   - pairing;
   - recepción;
   - envío;
   - reconexión;
   - estado de conexión;
   - logout;
   - eventos de transporte.
9. Django seguirá resolviendo:
   - identidad del cliente;
   - `ChatRoom`;
   - persistencia de mensajes;
   - idempotencia;
   - estado humano/IA;
   - `ai_paused`;
   - `is_ai_mode_active`;
   - permisos;
   - notificaciones;
   - integración con Google ADK.
10. No introducir OpenClaw, n8n ni una segunda base de datos para esta migración.
11. No mezclar Baileys con `ai_engine_adk`.
12. Mantener una interfaz de proveedor para que posteriormente pueda sustituirse Baileys por otro transporte sin modificar Support.

---

# 1. CONTEXTO REAL DEL PROYECTO

La documentación actual confirma que el proyecto es una SPA Vue 3 + Django/DRF + Channels + PostgreSQL + Redis + Celery, con servicios de IA separados. El panel administrativo usa `/panel/*` y el soporte administrativo se centraliza en `SupportAdminOrchestrator` y la app `support`.

El resumen actual también confirma que:

- el soporte web utiliza WebSocket;
- WhatsApp comparte el puente channel-agnostic de soporte;
- la IA de soporte actualmente corre en `ai_engine_adk`;
- Google ADK es el runtime real del agente de soporte;
- WhatsApp debe respetar `ChatRoom.ai_paused` / `is_ai_mode_active`;
- existe una brecha histórica de namespace entre conversaciones web y WhatsApp que no debe reproducirse en la nueva implementación;
- la arquitectura actual ya contempla servicios Docker independientes.

**Regla:** antes de modificar código, la IA editora debe leer los documentos `.AGENT` específicos de `support`, `notifications`, `dashboard`, `organization`, `ai_engine_adk` y frontend, además de la documentación del proveedor WhatsApp actual.

---

# 2. INVESTIGACIÓN OFICIAL OBLIGATORIA

Antes de escribir código, fijar la versión concreta de Baileys y registrar la evidencia.

Fuentes primarias recomendadas:

- WhiskeySockets/Baileys:
  https://github.com/WhiskeySockets/Baileys
- Documentación oficial del proyecto:
  https://github.com/WhiskeySockets/docs
- Quickstart:
  https://github.com/WhiskeySockets/docs/blob/main/quickstart.mdx
- Gestión de sesiones:
  https://github.com/WhiskeySockets/docs/blob/main/authentication/session-management.mdx
- Troubleshooting:
  https://github.com/WhiskeySockets/docs/blob/main/advanced/troubleshooting.mdx
- Condiciones de servicio de WhatsApp:
  https://www.whatsapp.com/legal/terms-of-service

### Hallazgos que deben incorporarse

Baileys es una biblioteca no oficial y no está afiliada a WhatsApp. La documentación del proyecto recomienda utilizarla responsablemente y conforme a las condiciones de WhatsApp.

La documentación actual indica:

- Node.js 20+ para el quickstart actual;
- `makeWASocket`;
- `connection.update` para QR y estado;
- `creds.update` para persistir credenciales;
- `messages.upsert` para mensajes entrantes;
- manejo explícito de reconexión;
- `DisconnectReason.loggedOut` debe tratarse como una desconexión que requiere nueva vinculación;
- `printQRInTerminal` está deprecated; el QR debe ser entregado al frontend;
- `useMultiFileAuthState` sirve como guía y desarrollo, pero la propia documentación actual desaconseja usarlo como estrategia de persistencia de producción.

**Consecuencia:** NO implementar producción usando `useMultiFileAuthState` como almacenamiento definitivo sin evaluar un auth-state store persistente.

---

# 3. FASE 0 — AUDITORÍA PREVIA SIN ESCRITURA

## Objetivo

Conocer exactamente qué existe actualmente en:

```text
/panel/soporte/whatsapp
```

y reemplazar únicamente la implementación experimental.

## La IA editora debe localizar

### Frontend

Buscar:

```text
QR Web Session
WhatsApp
whatsapp
qr
session
web session
connection
```

y determinar:

- componente Vue;
- store Pinia;
- composable;
- servicios Axios;
- endpoints usados;
- WebSocket utilizado;
- estados;
- modales;
- permisos;
- botones;
- textos;
- rutas;
- polling;
- manejo de errores.

### Backend

Buscar:

```text
whatsapp
qr
session
web_session
baileys
meta
webhook
process_whatsapp_inbound_task
```

Determinar:

- modelos;
- Commands;
- Selectors;
- ViewSets;
- URLs;
- Tasks;
- clientes;
- serializers;
- permisos;
- configuración;
- variables `.env`;
- Docker;
- healthchecks.

### Proveedor actual

Identificar exactamente:

```text
QR Web Session (experimental)
```

y documentar:

- archivos;
- endpoints;
- flujo;
- almacenamiento;
- lifecycle;
- puntos de integración;
- código muerto;
- dependencias.

### Regla

No borrar código durante esta fase.

Crear:

```text
docs/audits/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md
```

con:

```text
CURRENT_PROVIDER
FRONTEND_FILES
BACKEND_FILES
API_ENDPOINTS
MODELS
SERVICES
TASKS
DOCKER
ENV
TESTS
RISKS
DEPRECATED_CODE
MIGRATION_BOUNDARY
```

---

# 4. FASE 1 — DEFINIR EL CONTRATO DEL GATEWAY

Crear un contrato interno estable.

El gateway debe exponer como mínimo:

```text
GET  /health
GET  /status

POST /session/start
POST /session/logout
POST /session/reconnect

GET  /session/qr

POST /messages/send
```

Si el proyecto requiere eventos push, preferir:

```text
WebSocket o webhook interno Gateway → Django
```

y no polling continuo desde Django.

## Contrato recomendado

### GET /health

```json
{
  "status": "ok",
  "service": "whatsapp_gateway",
  "provider": "baileys"
}
```

### GET /status

```json
{
  "provider": "baileys",
  "status": "CONNECTED",
  "phone": "***********",
  "jid": "********@s.whatsapp.net",
  "has_session": true,
  "qr_available": false,
  "last_connected_at": "...",
  "last_disconnect_at": null
}
```

Nunca devolver:

- credenciales;
- Signal keys;
- auth state;
- tokens;
- secretos;
- contenido sensible de la sesión.

---

# 5. FASE 2 — MODELO DE ESTADOS

Definir un estado único:

```text
DISCONNECTED
STARTING
QR_REQUIRED
PAIRING
CONNECTED
RECONNECTING
LOGGED_OUT
ERROR
```

No utilizar strings diferentes en cada capa.

Crear constantes tipadas en gateway y equivalentes en Django/frontend.

### Transiciones

```text
DISCONNECTED
    ↓
STARTING
    ↓
QR_REQUIRED
    ↓
PAIRING
    ↓
CONNECTED
```

Desconexión temporal:

```text
CONNECTED
    ↓
RECONNECTING
    ↓
CONNECTED
```

Logout:

```text
CONNECTED
    ↓
LOGGED_OUT
    ↓
QR_REQUIRED
```

Error no recuperable:

```text
ANY
 ↓
ERROR
```

---

# 6. FASE 3 — GATEWAY BAILEYS

## Tecnología

Crear servicio:

```text
whatsapp_gateway/
```

preferiblemente:

```text
Node.js
TypeScript
Baileys
Fastify o Express
Pino
```

No introducir NestJS salvo que exista una razón real.

## Dependencia

Usar el paquete oficial/mantenido:

```text
@whiskeysockets/baileys
```

Fijar versión exacta.

No usar:

```text
@adiwajshing/baileys
```

ni forks desconocidos.

## Requisitos

Node.js 20+.

Configurar:

```text
WA_GATEWAY_PORT
WA_GATEWAY_INTERNAL_TOKEN
WA_SESSION_STORAGE
WA_LOG_LEVEL
WA_RECONNECT_ENABLED
WA_RECONNECT_MAX_ATTEMPTS
WA_RECONNECT_BASE_DELAY
```

---

# 7. FASE 4 — AUTH STATE DE PRODUCCIÓN

Esta es una de las decisiones más importantes.

## NO hacer

```text
useMultiFileAuthState(...)
```

como solución final de producción sin más.

La documentación actual de Baileys señala que es una utilidad de referencia y no recomienda usarla como solución de session management de producción.

## Arquitectura objetivo

Implementar un `AuthenticationStateStore` propio:

```text
AuthStateStore
├── getCreds()
├── saveCreds()
├── getKeys()
├── setKeys()
├── removeKeys()
├── clear()
└── exists()
```

El store debe ser persistente y compatible con reinicio de Docker.

### Opción preferida

Persistencia en PostgreSQL si se puede aislar correctamente la estructura criptográfica.

Alternativamente:

```text
Docker named volume
```

solo si se garantiza:

- persistencia;
- backup;
- permisos;
- aislamiento;
- single-writer;
- recuperación.

### Regla

Nunca guardar auth state:

```text
src/
frontend/
git/
logs/
```

Nunca exponerlo por HTTP.

Nunca incluirlo en imágenes Docker.

Nunca imprimirlo en logs.

---

# 8. FASE 5 — QR

La UI existente debe conservar la experiencia:

```text
Conectar WhatsApp
       ↓
Generar QR
       ↓
Mostrar QR
       ↓
Usuario escanea
       ↓
CONNECTED
```

Pero ahora el QR debe venir del gateway.

Baileys emite el QR desde:

```text
connection.update
```

El gateway debe:

1. recibir QR;
2. guardar temporalmente el QR vigente;
3. generar una representación adecuada para frontend;
4. emitir evento a Django;
5. Django distribuirlo al frontend;
6. eliminarlo cuando:
   - expire;
   - sea reemplazado;
   - la sesión conecte;
   - el usuario cancele.

## Importante

No persistir QR indefinidamente en PostgreSQL.

---

# 9. FASE 6 — EVENT BUS GATEWAY → DJANGO

No permitir que Django dependa de detalles internos de Baileys.

Crear eventos normalizados:

```text
whatsapp.connection.status
whatsapp.connection.qr
whatsapp.connection.logged_out
whatsapp.message.received
whatsapp.message.sent
whatsapp.message.failed
```

Ejemplo:

```json
{
  "event": "whatsapp.message.received",
  "event_id": "uuid",
  "occurred_at": "...",
  "provider": "baileys",
  "account": "default",
  "message": {
    "provider_message_id": "...",
    "remote_jid": "...",
    "sender_phone": "+57...",
    "text": "...",
    "timestamp": "..."
  }
}
```

---

# 10. FASE 7 — AUTENTICACIÓN GATEWAY ↔ DJANGO

Nunca dejar:

```text
Django → http://gateway:port
```

sin autenticación.

Implementar:

```text
X-Gateway-Token
```

o preferiblemente un mecanismo equivalente con secreto interno rotado.

Validar:

- token;
- origen;
- timestamp;
- event_id;
- idempotencia.

No exponer el gateway directamente a Internet.

Arquitectura:

```text
Internet
   X
   |
Nginx
   |
Django
   |
private Docker network
   |
WhatsApp Gateway
```

---

# 11. FASE 8 — RECEPCIÓN DE MENSAJES

Baileys:

```text
messages.upsert
```

↓

Gateway normaliza

↓

Django endpoint interno

↓

`notifications` / `support` service

↓

resolver cliente

↓

resolver ChatRoom

↓

crear mensaje

↓

evaluar IA

↓

Google ADK si corresponde

## Regla crítica

La recepción no debe ejecutar directamente:

```text
LLM
```

desde el gateway.

---

# 12. FASE 9 — IDENTIDAD DEL CLIENTE

No crear una nueva identidad paralela.

Resolver:

```text
WhatsApp JID
      ↓
phone number
      ↓
User
      ↓
UserProfile
```

Usar los resolvers existentes.

No crear:

```text
WhatsAppUser
```

si no es estrictamente necesario.

Si se requiere persistir la relación, crear una entidad de integración:

```text
WhatsAppIdentity
```

con:

```text
user
phone
jid
provider
verified_at
last_seen_at
is_active
```

No duplicar información de `User`.

---

# 13. FASE 10 — CHATROOM / CONVERSACIÓN

La documentación actual identifica una deuda:

```text
wa-{user_id}
vs
room-{uuid}
```

La nueva implementación debe resolverla.

## Regla

WhatsApp y Web deben converger en el mismo concepto de conversación.

Idealmente:

```text
Customer
   |
ChatRoom
   |
   +-- Web
   |
   +-- WhatsApp
```

El canal debe ser metadata:

```text
channel = WEB
channel = WHATSAPP
```

pero no una segunda conversación paralela para el mismo contexto cuando el dominio determine que es la misma interacción.

Si por razones de negocio se mantienen salas distintas por canal, debe existir un identificador de conversación externo y una relación explícita, no namespaces improvisados.

---

# 14. FASE 11 — IDEMPOTENCIA

Cada mensaje de Baileys debe tener:

```text
provider
provider_message_id
```

con constraint única.

Regla:

```text
mismo provider_message_id
        ↓
NO duplicar mensaje
```

Debe existir protección:

```text
DB unique constraint
+
service-level check
```

Nunca confiar únicamente en:

```text
if exists()
```

por condiciones de carrera.

---

# 15. FASE 12 — ENVÍO DE MENSAJES

Flujo:

```text
Support / ADK / Notification
        ↓
Django Command
        ↓
WhatsAppGatewayClient
        ↓
POST /messages/send
        ↓
Baileys
        ↓
WhatsApp
```

El gateway debe devolver:

```json
{
  "accepted": true,
  "provider_message_id": "...",
  "status": "SENT"
}
```

No declarar "entregado" solo porque Baileys aceptó la operación.

Diferenciar:

```text
QUEUED
SENT
DELIVERED
READ
FAILED
```

solo si la fuente de eventos realmente permite determinarlo.

---

# 16. FASE 13 — COLAS Y CONCURRENCIA

No ejecutar envíos masivos desde el request HTTP.

Usar Celery/Django para operaciones que requieran:

```text
retry
backoff
queue
audit
```

El gateway debe serializar las operaciones que Baileys requiera por socket.

Nunca crear múltiples sockets concurrentes para la misma sesión.

Implementar:

```text
one active socket per WhatsApp account
```

---

# 17. FASE 14 — RECONEXIÓN

Baileys no debe asumirse como auto-reconnect mágico.

Implementar explícitamente:

```text
connection.update
```

y distinguir:

```text
loggedOut
temporary network error
connection replaced
timeout
server error
unknown error
```

### Regla

Si:

```text
DisconnectReason.loggedOut
```

no hacer loop infinito.

Cambiar a:

```text
LOGGED_OUT
```

y solicitar nueva vinculación.

Para errores recuperables:

```text
RECONNECTING
```

con:

```text
exponential backoff
jitter
max attempts
```

---

# 18. FASE 15 — LOGOUT

Desde:

```text
/panel/soporte/whatsapp
```

botón:

```text
Desconectar
```

debe:

1. confirmar acción;
2. solicitar logout al gateway;
3. Baileys ejecutar logout;
4. eliminar/inutilizar auth state;
5. cerrar socket;
6. informar Django;
7. limpiar estado QR;
8. frontend mostrar `DISCONNECTED/QR_REQUIRED`.

Nunca eliminar datos de conversación por hacer logout.

---

# 19. FASE 16 — FRONTEND

Modificar exclusivamente el proveedor de conexión.

La ruta debe continuar siendo:

```text
/panel/soporte/whatsapp
```

Conservar el diseño actual cuando sea posible.

Estados visuales:

```text
● Conectado
● Conectando
● Requiere QR
● Reconectando
● Desconectado
● Sesión cerrada
● Error
```

Acciones:

```text
Conectar
Reconectar
Desconectar
Mostrar QR
Copiar pairing code (solo si se decide soportarlo)
```

No mostrar:

- credenciales;
- auth state;
- errores internos;
- stack traces;
- tokens.

---

# 20. FASE 17 — WEBSOCKET DEL PANEL

El frontend no debe consultar el gateway directamente.

Preferido:

```text
Vue
 ↓
Django Channels
 ↓
Gateway
```

Eventos:

```text
whatsapp.status
whatsapp.qr
whatsapp.error
```

Esto mantiene la seguridad y el aislamiento del gateway.

El heartbeat WebSocket existente de soporte debe mantenerse.

---

# 21. FASE 18 — INTEGRACIÓN CON NOTIFICATIONS

Reutilizar:

```text
notifications
```

y sus Commands existentes.

No crear un segundo sistema de notificaciones dentro del gateway.

El gateway es transporte.

Django es dominio.

---

# 22. FASE 19 — INTEGRACIÓN CON GOOGLE ADK

Mantener la separación actual:

```text
WhatsApp
 ↓
Django Support
 ↓
ai_engine_adk
 ↓
Google ADK
```

No:

```text
WhatsApp
 ↓
Baileys
 ↓
LLM
```

El gateway no debe conocer:

```text
AgentProfile
RAG
Tools
ADK
LLM
prompt
```

El comportamiento actual de:

```text
ai_paused
is_ai_mode_active
human handoff
```

debe permanecer en Django/Support.

---

# 23. FASE 20 — SEGURIDAD

Auditar específicamente:

### Secretos

```text
WA_GATEWAY_INTERNAL_TOKEN
session encryption keys
database credentials
JWT
API keys
```

Nunca:

```text
console.log(credentials)
```

### Auth state

Debe estar:

```text
fuera del repo
fuera de la imagen
fuera del frontend
fuera de logs
```

### Red

Gateway:

```text
private network only
```

### Rate limiting

Aplicar al endpoint interno de envío.

### Abuse prevention

No implementar:

```text
bulk spam
automatic unsolicited messaging
```

y documentar que el uso debe respetar las condiciones aplicables de WhatsApp.

---

# 24. FASE 21 — DOCKER

Agregar:

```text
whatsapp_gateway
```

al stack.

Ejemplo conceptual:

```yaml
whatsapp_gateway:
  build:
    context: ./whatsapp_gateway
  restart: unless-stopped
  env_file:
    - .env
  networks:
    - sintel-network
  volumes:
    - whatsapp_auth:/app/data/auth
```

No exponer puerto públicamente si no es necesario.

Healthcheck:

```text
GET /health
```

Debe comprobar:

```text
process alive
```

y opcionalmente:

```text
socket state
```

No marcar el contenedor como unhealthy solo porque WhatsApp esté desconectado temporalmente.

---

# 25. FASE 22 — CONFIGURACIÓN

Agregar variables:

```text
WHATSAPP_GATEWAY_URL=http://whatsapp_gateway:...
WHATSAPP_GATEWAY_TOKEN=...
WHATSAPP_GATEWAY_ENABLED=true
WHATSAPP_PROVIDER=baileys
WHATSAPP_SESSION_ID=default
WHATSAPP_RECONNECT_ENABLED=true
```

No duplicar configuración entre:

```text
Django
frontend
gateway
```

El frontend nunca debe conocer secretos.

---

# 26. FASE 23 — TESTS DEL GATEWAY

Crear mínimo:

```text
tests/
├── test_health
├── test_session
├── test_qr
├── test_connection
├── test_reconnect
├── test_logout
├── test_receive
├── test_send
├── test_idempotency
├── test_auth
└── test_security
```

Cubrir:

- QR generado;
- QR reemplazado;
- QR limpiado;
- conexión;
- desconexión;
- reconnect;
- logout;
- mensaje recibido;
- mensaje enviado;
- duplicate message;
- invalid token;
- malformed payload.

---

# 27. FASE 24 — TESTS DJANGO

Cubrir:

```text
WhatsAppGatewayClient
WhatsAppCommands
WhatsAppSelectors
webhook/event receiver
message idempotency
ChatRoom resolution
customer resolution
notification integration
AI handoff
```

Especialmente:

```text
ai_paused=True
```

debe impedir respuesta automática de IA.

---

# 28. FASE 25 — E2E REAL

No declarar terminado con mocks solamente.

Prueba real:

### Caso A — Primera conexión

```text
Docker start
↓
panel
↓
Conectar
↓
QR
↓
scan desde teléfono
↓
CONNECTED
```

### Caso B — Persistencia

```text
CONNECTED
↓
docker restart whatsapp_gateway
↓
socket reconnect
↓
CONNECTED
```

sin escanear QR nuevamente.

### Caso C — Mensaje entrante

```text
teléfono
↓
WhatsApp
↓
Baileys
↓
gateway
↓
Django
↓
ChatRoom
↓
Support
```

### Caso D — Respuesta

```text
Support/ADK
↓
Django
↓
gateway
↓
WhatsApp
↓
teléfono
```

### Caso E — Logout

```text
panel
↓
Desconectar
↓
WhatsApp session invalidated
↓
QR_REQUIRED
```

### Caso F — Reconexión

Simular caída temporal.

Debe volver sin intervención humana.

---

# 29. FASE 26 — REGRESIÓN

Ejecutar antes y después:

```text
support/tests.py
notifications/tests.py
```

y las suites relacionadas.

También:

```text
ai_engine_adk/tests/
```

No aceptar regresiones en:

```text
web support
AI support
notifications
customer identity
ChatRoom
WebSocket
admin auth
```

---

# 30. FASE 27 — REMOCIÓN DE QR WEB SESSION EXPERIMENTAL

Solo después de que Baileys tenga:

```text
QR PASS
SESSION PASS
SEND PASS
RECEIVE PASS
RECONNECT PASS
LOGOUT PASS
E2E PASS
```

eliminar el proveedor experimental.

Eliminar:

- código;
- endpoints;
- componentes;
- stores;
- dependencias;
- variables `.env`;
- Docker;
- documentación;
- tests obsoletos.

No eliminar modelos de soporte que todavía tengan valor de dominio.

---

# 31. FASE 28 — MIGRACIÓN SIN REGRESIÓN

Orden:

```text
1. Implementar gateway
2. Implementar contrato
3. Implementar integración Django
4. Implementar frontend
5. Ejecutar tests
6. Conectar número real en desarrollo
7. E2E
8. Ejecutar regresión
9. Activar Baileys
10. Verificar producción/staging
11. Retirar Web Session experimental
```

No hacer un "big bang" destructivo.

Usar feature flag:

```text
WHATSAPP_PROVIDER=baileys
```

y permitir rollback temporal:

```text
WHATSAPP_PROVIDER=legacy
```

hasta cerrar la migración.

---

# 32. FASE 29 — OBSERVABILIDAD

Registrar métricas:

```text
whatsapp_connection_status
whatsapp_connection_duration
whatsapp_reconnect_total
whatsapp_qr_generated_total
whatsapp_messages_received_total
whatsapp_messages_sent_total
whatsapp_messages_failed_total
whatsapp_duplicate_messages_total
whatsapp_send_latency
```

Logs estructurados:

```json
{
  "service": "whatsapp_gateway",
  "event": "connection_status",
  "status": "CONNECTED",
  "session": "default",
  "timestamp": "..."
}
```

Nunca registrar:

```text
auth state
Signal keys
tokens
QR completo
contenido sensible innecesario
```

---

# 33. FASE 30 — DOCUMENTACIÓN

Actualizar:

```text
support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md
notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md
dashboard/.AGENT/docs/ARQUITECTURA_COMPLETA_DASHBOARD.md
frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md
```

Crear:

```text
whatsapp_gateway/README.md
docs/architecture/WHATSAPP_BAILEYS_ARCHITECTURE.md
docs/audits/WHATSAPP_BAILEYS_PRE_MIGRATION_AUDIT.md
docs/audits/WHATSAPP_BAILEYS_IMPLEMENTATION_REPORT.md
```

Agregar al final de cada documento afectado:

```markdown
## Cambios Recientes

### 2026-09-22 — Migración WhatsApp Web Session → Baileys
- Qué cambió
- Por qué
- Archivos afectados
- Contratos API
- Docker
- Seguridad
- Tests
```

---

# 34. FASE 31 — REGLAS PARA LA IA EDITORA

La IA editora debe trabajar en LOOP.

## LOOP

```text
AUDIT
↓
PLAN
↓
IMPLEMENT
↓
TEST
↓
VERIFY
↓
FIX
↓
TEST AGAIN
↓
DOCUMENT
↓
AUDIT AGAIN
```

No avanzar a la siguiente fase si la anterior tiene:

```text
FAIL
BLOCKED
UNKNOWN
NOT VERIFIED
```

## Prohibido

No:

- reescribir Support completo;
- reescribir Notifications;
- reescribir Google ADK;
- crear una segunda arquitectura de conversaciones;
- crear una segunda BD;
- acceder al ORM desde Node;
- meter Baileys dentro de Django;
- guardar sesiones en frontend;
- exponer gateway públicamente;
- imprimir secretos;
- eliminar Web Session antes de E2E;
- inventar endpoints;
- inventar modelos;
- duplicar `User`;
- duplicar `ChatRoom`;
- duplicar IA.

---

# 35. FASE 32 — CRITERIOS DE ACEPTACIÓN

## Arquitectura

```text
ARCHITECTURE = PASS
GATEWAY = PASS
DJANGO_BOUNDARY = PASS
SECURITY = PASS
```

## WhatsApp

```text
BAILEYS = PASS
QR = PASS
SESSION = PASS
RECONNECT = PASS
LOGOUT = PASS
```

## Mensajería

```text
RECEIVE = PASS
SEND = PASS
IDEMPOTENCY = PASS
CUSTOMER = PASS
CONVERSATION = PASS
```

## IA

```text
AI_HANDOFF = PASS
AI_PAUSED = PASS
HUMAN_HANDOFF = PASS
```

## Infraestructura

```text
DOCKER = PASS
HEALTHCHECK = PASS
PERSISTENCE = PASS
BACKUP = PASS
```

## Calidad

```text
UNIT_TESTS = PASS
INTEGRATION_TESTS = PASS
E2E = PASS
REGRESSION = PASS
DOCUMENTATION = PASS
```

---

# 36. DEFINICIÓN DE TERMINADO

Solo declarar:

```text
WHATSAPP BAILEYS MIGRATION COMPLETED
```

cuando:

```text
AUDIT = PASS
ARCHITECTURE = PASS
GATEWAY = PASS
BAILEYS = PASS
QR = PASS
SESSION = PASS
SEND = PASS
RECEIVE = PASS
CUSTOMER = PASS
CONVERSATION = PASS
IDEMPOTENCY = PASS
RECONNECT = PASS
LOGOUT = PASS
SECURITY = PASS
DOCKER = PASS
TESTS = PASS
E2E = PASS
REGRESSION = PASS
DOCUMENTATION = PASS
LEGACY_REMOVED = PASS
```

---

# 37. REPORTE FINAL OBLIGATORIO

Crear:

```text
docs/audits/WHATSAPP_BAILEYS_IMPLEMENTATION_REPORT.md
```

Contenido mínimo:

```markdown
# WhatsApp Baileys Implementation Report

## Estado
COMPLETED / BLOCKED

## Versiones
Baileys:
Node:
TypeScript:
Django:
PostgreSQL:

## Arquitectura
Gateway:
Django:
Frontend:
Docker:

## Sesión
QR:
Persistence:
Reconnect:
Logout:

## Mensajería
Receive:
Send:
Idempotency:

## Integración
Customer:
ChatRoom:
Notifications:
Google ADK:

## Tests
Gateway:
Django:
Integration:
E2E:
Regression:

## Evidencia
- comandos
- resultados
- timestamps
- QR
- conexión
- recepción
- envío
- restart
- reconnect
- logout

## Riesgos conocidos
...

## Rollback
...
```

---

# 38. ROLLBACK

Debe ser posible volver temporalmente a la implementación anterior mientras Baileys se valida.

Rollback:

```text
WHATSAPP_PROVIDER=legacy
```

Solo si la implementación anterior todavía existe y se mantiene durante la ventana de migración.

Una vez cerrado el proyecto:

```text
legacy provider = removed
```

y el rollback se realizará mediante la versión anterior del deployment, no manteniendo indefinidamente código muerto.

---

# 39. RIESGOS ESPECÍFICOS

## Riesgo 1 — Cambios de WhatsApp Web

Baileys depende de mecanismos no oficiales de WhatsApp Web.

Mitigación:

```text
version pinning
E2E
rollback
monitoring
re-link procedure
```

## Riesgo 2 — Sesión

No asumir persistencia indefinida.

Mitigación:

```text
persistent auth state
backup
reconnect
re-pair flow
```

## Riesgo 3 — Auth state

El auth state contiene material criptográfico sensible.

Mitigación:

```text
private storage
encryption/permissions
no logs
no git
no frontend
```

## Riesgo 4 — Duplicados

Mitigación:

```text
provider_message_id UNIQUE
```

## Riesgo 5 — Dos conversaciones

Mitigación:

```text
canonical ChatRoom resolution
channel metadata
external conversation identity
```

## Riesgo 6 — IA responde después de handoff humano

Mitigación:

```text
ai_paused
is_ai_mode_active
tests de regresión
```

---

# 40. RESULTADO FINAL OBJETIVO

La arquitectura final debe quedar:

```text
                           ┌────────────────────┐
                           │      WhatsApp      │
                           └─────────┬──────────┘
                                     │
                              WhatsApp Web
                                     │
                           ┌─────────▼──────────┐
                           │      Baileys       │
                           │ Node + TypeScript  │
                           └─────────┬──────────┘
                                     │
                           WhatsApp Gateway
                                     │
                         Internal authenticated API
                                     │
                           ┌─────────▼──────────┐
                           │       Django       │
                           │ Support/Notify     │
                           └─────────┬──────────┘
                                     │
                           ChatRoom / Messages
                                     │
                         ┌───────────▼───────────┐
                         │      PostgreSQL       │
                         └───────────────────────┘
                                     │
                              Google ADK
                                     │
                         Support Agent / RAG / Tools
```

## Principio final

```text
BAILEYS = TRANSPORT
DJANGO = DOMAIN
POSTGRESQL = SOURCE OF TRUTH
CHANNELS = REAL-TIME ADMIN
GOOGLE ADK = INTELLIGENCE
VUE = PRESENTATION
```

No invertir estas responsabilidades.

---

# 41. REFERENCIAS OFICIALES

- Baileys / WhiskeySockets:
  https://github.com/WhiskeySockets/Baileys
- WhiskeySockets Docs:
  https://github.com/WhiskeySockets/docs
- Quickstart:
  https://github.com/WhiskeySockets/docs/blob/main/quickstart.mdx
- Session Management:
  https://github.com/WhiskeySockets/docs/blob/main/authentication/session-management.mdx
- Troubleshooting:
  https://github.com/WhiskeySockets/docs/blob/main/advanced/troubleshooting.mdx
- WhatsApp Terms of Service:
  https://www.whatsapp.com/legal/terms-of-service

---

# 42. NOTA DE CUMPLIMIENTO

Baileys es una biblioteca no oficial. La implementación debe utilizarse de acuerdo con las condiciones aplicables de WhatsApp. No diseñar esta integración para spam, mensajería masiva no solicitada, evasión de controles, recopilación no autorizada de datos o usos contrarios a las condiciones del servicio.

La conexión debe considerarse una capa técnica reemplazable y no una garantía de compatibilidad permanente con WhatsApp Web.
