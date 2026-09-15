# WHATSAPP_CONNECTION_BASELINE — FASE 0

**Misión "Refactorización Arquitectónica del Módulo WhatsApp — Dominio Independiente + Connection
Adapter Intercambiable QR/REST", 2026-09-16.** Auditoría real del código (no de documentación
previa) antes de escribir una sola línea de la nueva arquitectura.

---

## HALLAZGO CRÍTICO — la premisa de la misión está invertida respecto a la realidad

La misión asume: **"hoy usamos QR, mañana cambiaremos a REST"** — el `RESULTADO FINAL` pide
`WHATSAPP_CONNECTION_TYPE=QR` como el valor de **hoy**.

**Confirmado contra código real, no asumido**: no existe absolutamente ningún mecanismo QR en
este repositorio — ninguna librería de pairing (Baileys/whatsapp-web.js/similar), ninguna
automatización de navegador, ningún endpoint de generación de QR. Búsqueda exhaustiva
(`grep -rli "qr\|baileys\|whatsapp-web\|pairing"`) no encontró ni un solo resultado real.

**Lo que SÍ existe, real y funcionando en producción hoy, es REST** — la API oficial de Meta
Cloud API (`marketing/integrations/meta/`), completamente integrada: webhook con verificación de
firma HMAC, cliente HTTP real (`MetaGraphClient`/`MetaWhatsAppClient`), auditoría de eventos
(`MetaWebhookEvent`), y el flujo conversacional completo (recepción → IA → respuesta) verificado
en producción real desde la migración a ADK (2026-09-14, ver memoria de sesión
`project_two_docker_stacks_staging_vs_real_production`).

**Decisión de esta misión, documentada aquí, no oculta**: se construyen AMBOS adapters cumpliendo
el mismo contrato hexagonal que pide la misión, pero:
- `RestConnectionAdapter` envuelve la integración REAL ya existente (Meta Cloud API) — es el
  adapter que funciona hoy.
- `QRConnectionAdapter` se construye estructuralmente completo (mismo contrato, mismas
  capacidades declaradas) pero **funcionalmente `NOT_IMPLEMENTED`** — sin librería de pairing
  elegida ni gateway real integrado. Mismo tratamiento que la misión ya anticipa para el caso
  "la API real todavía no está disponible" (sección 9 del prompt maestro), aplicado al mecanismo
  que en este repo real es el que falta, no REST.
- **`WHATSAPP_CONNECTION_TYPE` por defecto será `REST`**, no `QR` — reflejar la realidad del
  sistema, no la premisa del prompt. Si en el futuro se integra un gateway QR real, activarlo es
  cambiar la configuración, exactamente como pide la misión — la arquitectura queda preparada
  para ambos sentidos.

Esto no es una desviación del objetivo arquitectónico (que es 100% real y correcto: dominio
independiente del mecanismo de conexión) — es una corrección de un hecho puntual sobre cuál
mecanismo existe hoy.

---

## Matriz de componentes reales

| Componente | Responsabilidad actual | Ubicación real | Clasificación | Debe permanecer | Debe moverse |
|---|---|---|---|---|---|
| **WhatsApp Business Logic** | Resolución de cliente por teléfono, get-or-create de `ChatRoom`, guardado de mensajes, verificación `ai_paused`/`is_ai_mode_active`/`is_ai_rate_limited`, llamada a `ask_ai()`, decisión de qué responder | Inline dentro de `notifications/tasks.py::process_whatsapp_inbound_task` y `send_whatsapp_agent_reply_task` | **DOMAIN + APPLICATION**, mezclado hoy con llamadas de transporte inline | La lógica | Extraer a `whatsapp/domain/service.py::WhatsAppService` |
| **QR** | — | No existe | — | N/A | Construir `whatsapp/adapters/qr_adapter.py`, `NOT_IMPLEMENTED` explícito |
| **REST (Meta Cloud API)** | Envío real (`send_text`/`send_template`), HTTP a `graph.facebook.com` | `marketing/integrations/meta/whatsapp.py::MetaWhatsAppClient`, `marketing/integrations/meta/client.py::MetaGraphClient` | **INFRASTRUCTURE** | Sí, tal cual — no se reescribe el transporte real | Se ENVUELVE en `whatsapp/adapters/rest_adapter.py`, no se duplica |
| **Verificación de firma webhook** | HMAC-SHA256 fail-closed | `marketing/integrations/meta/signatures.py::verify_meta_webhook_signature` | **INFRASTRUCTURE**, compartida con Page/Instagram (no exclusiva de WhatsApp) | Sí, tal cual | No se mueve — es infra de Meta en general, no del dominio WhatsApp |
| **Recepción webhook + parseo de payload Meta** | Extrae `wa_id`/`text`/`message_id`/`phone_number_id`/`waba_id` del payload específico de Meta | `notifications/api/whatsapp_webhook.py::WhatsAppInboundWebhookView` | **TRANSPORT** | El endpoint HTTP en sí (Meta solo puede llamar a una URL fija) | El PARSEO a un contrato canónico se mueve a `rest_adapter.py` |
| **Auditoría de eventos crudos** (`MetaWebhookEvent`) | Persiste cada evento (incl. rechazados), retención 30/180 días | `notifications/models.py` | **INFRASTRUCTURE**, específica de Meta (campos `waba_id`/`phone_number_id`) | Sí, tal cual — es forense de la entrega REST, no del dominio | No se generaliza a un modelo provider-agnostic (Regla: no reescritura innecesaria) |
| **Deduplicación** | `cache.add()` por `message_id`, TTL 24h | Inline en el webhook view | **TRANSPORT hoy, debe ser DOMAIN** | El fast-path de descarte temprano (evita encolar 2 veces) | La deduplicación AUTORITATIVA se mueve a `WhatsAppService`, genérica por `(channel, external_message_id)` — el webhook la reusa, no la duplica |
| **Resolución de cliente por teléfono** | `UserProfile.objects.filter(phone_number__endswith=...)` | Inline en `process_whatsapp_inbound_task` | **DOMAIN (customer resolution)** | La lógica | `whatsapp/domain/customer_resolver.py` |
| **Resolución de conversación / ChatRoom** | `ChatCommands.get_or_create_room(user)` | Inline en `process_whatsapp_inbound_task`, `send_whatsapp_agent_reply_task` | **DOMAIN (conversation mapping)**, ya correctamente reusa `support.ChatCommands` | Sí, reusar `ChatCommands` (Service Layer real de `support`, no se reimplementa) | Se envuelve en `whatsapp/domain/conversation_resolver.py`, mismo llamado interno |
| **Broadcast a WebSocket** (`_broadcast_chat_message`) | Avisa en vivo al widget/panel admin | `notifications/tasks.py` | **APPLICATION**, correcto tal cual | Sí | Se mueve junto con el resto del dominio a `WhatsAppService`, sin cambiar su lógica |
| **Human Handoff** (`ai_paused`/`is_ai_mode_active`/`is_ai_rate_limited`) | Decide si la IA responde o no | `support/services/ai_bridge.py`, ya reusado correctamente por `notifications/tasks.py` | **Support Core**, correcto — NO se duplica en WhatsApp | Sí, sin cambios | No se mueve — WhatsApp solo lo CONSULTA, igual que hoy |
| **IA / RAG / ADK** | `ask_ai()` → `ai_bridge` → `ai_engine_adk` → Google ADK | `support/services/ai_bridge.py` | **Support Core**, correcto — WhatsApp nunca habla con el LLM directo | Sí, sin cambios | No se mueve |
| **Envío saliente** (respuesta de IA, respuesta de agente humano) | `WhatsAppClient().send_text(...)` | 2 call sites en `notifications/tasks.py` | **TRANSPORT**, correctamente ya NO decide contenido, solo transporta | El wrapping en `MetaWhatsAppClient` | La DECISIÓN de enviar se mueve a `WhatsAppService.send_message()`, que invoca `ConnectionPort.send_message()` |
| **Notificaciones transaccionales por WhatsApp** (`dispatch_notification`, plantillas de pedido/confirmación) | Envío proactivo, plantillas aprobadas, NO conversacional | `notifications/services/commands.py::dispatch_notification` | **RELACIONADO, FUERA DE ALCANCE** | Sin cambios — no es el dominio conversacional de soporte que pide la misión | No se toca |
| **Canal de marketing WhatsApp** (`AbstractChannelAdapter`) | Envío de campañas de marketing vía WhatsApp | `marketing/channels/whatsapp_channel.py` | **RELACIONADO, FUERA DE ALCANCE** | Sin cambios — dominio de marketing, ya sigue su propio patrón de Channel Adapter (`marketing/CLAUDE.md`) | No se toca |

## Puntos de entrada reales (todos los lugares donde hoy se menciona WhatsApp, clasificados)

| Archivo | Clasificación |
|---|---|
| `notifications/tasks.py` (`process_whatsapp_inbound_task`, `send_whatsapp_agent_reply_task`, `_broadcast_chat_message`, `_mark_meta_webhook_event`) | DOMAIN+APPLICATION (a extraer) + llamadas TRANSPORT inline |
| `notifications/api/whatsapp_webhook.py` | TRANSPORT (HTTP entrypoint real, no se puede mover) |
| `notifications/clients/whatsapp.py` | INFRASTRUCTURE — shim de compatibilidad hacia `MetaWhatsAppClient`, se mantiene |
| `notifications/models.py::MetaWebhookEvent` | INFRASTRUCTURE (auditoría REST-específica) |
| `notifications/services/commands.py::_resolve_phone` | DOMAIN (reusable por el customer resolver) |
| `marketing/integrations/meta/whatsapp.py`, `client.py`, `signatures.py` | INFRASTRUCTURE (transporte REST real) |
| `support/consumers.py::_dispatch_whatsapp_agent_reply` | APPLICATION (dispara la tarea Celery de respuesta saliente) |
| `support/services/ai_bridge.py` | Support Core, sin cambios |
| `ecommerce/settings/base.py` (`WHATSAPP_WEBHOOK_VERIFY_TOKEN`, `META_ACCESS_TOKEN`, `META_APP_SECRET`, `WHATSAPP_PHONE_NUMBER_ID`, etc.) | CONFIGURATION — específica de REST, se mantiene, se agrega `WHATSAPP_CONNECTION_TYPE` nuevo |
| `dashboard/api/views.py` (plantillas de notificación) | No relacionado con el mecanismo de conexión — fuera de alcance |
| `marketing/channels/whatsapp_channel.py` | Dominio de marketing, fuera de alcance (ver arriba) |

## Checkpoint FASE 0 — Estado

**PASS, con el hallazgo crítico documentado arriba.** Los puntos de acoplamiento reales están
identificados: la lógica de negocio real vive mezclada con 2 llamadas de transporte directo
(`WhatsAppClient().send_text(...)`) dentro de `notifications/tasks.py`, y el parseo del payload
de Meta vive inline en el webhook view. Ambos son extraíbles sin tocar la integración REST real
que ya funciona — no se reescribe `MetaWhatsAppClient`/`MetaGraphClient`/`MetaWebhookEvent`, se
envuelven.
