# WHATSAPP_CONNECTION_ARCHITECTURE

**Actualizado 2026-09-16 — Misión "Migración Arquitectónica de WhatsApp — QR Web Session
Experimental + Meta Cloud API Futura".** Reemplaza la versión anterior (misión "Refactorización
Arquitectónica del Módulo WhatsApp") con la nomenclatura definitiva: `QRWebSessionAdapter`/
`MetaCloudAPIAdapter` en vez de `QRConnectionAdapter`/`RestConnectionAdapter`. Ver
`AUDITORIA/WHATSAPP_CONNECTION_MIGRATION_BASELINE.md` (FASE 0 de esta misión) para el detalle
completo de qué se renombró y por qué.

## Diagrama real

```
                         SINTEL SUPPORT
                               |
                               v
                     whatsapp.domain.service
                        WhatsAppService
              (customer_resolver, conversation_resolver,
               ai_bridge -- ask_ai/is_ai_mode_active/
               is_ai_rate_limited, ChatCommands)
                               |
                   whatsapp.ports.connection
                      WhatsAppConnectionPort
                               |
                ┌──────────────┴──────────────┐
                v                             v
    QRWebSessionAdapter              MetaCloudAPIAdapter
    (whatsapp/adapters/               (whatsapp/adapters/
     qr_web_session_adapter.py)        meta_cloud_api_adapter.py)
    EXPERIMENTAL / TERCERO                    |
    NO ES API OFICIAL                          v
                |                     MetaWhatsAppClient
                v                     (marketing/integrations/
      BLOQUEADO (sin gateway          meta/, YA EXISTIA)
      real, ver WHATSAPP_QR_                  |
      PROVIDER_EVALUATION.md)                 v
                              graph.facebook.com (Meta Cloud API,
                              REAL, OFICIAL, en produccion)
```

## Capas y responsabilidades reales

| Capa | Módulo | Conoce el mecanismo de conexión |
|---|---|---|
| Dominio | `whatsapp/domain/*.py` | **NUNCA** — verificado con AST real, no solo revisión manual (`whatsapp/tests/test_isolation.py`) |
| Puerto | `whatsapp/ports/connection.py` | Define el contrato, no una implementación |
| Composición | `whatsapp/factory.py` | **ÚNICO** lugar con `if connection_type == ...` |
| Adapters | `whatsapp/adapters/{qr_web_session,meta_cloud_api}_adapter.py` | Cada uno solo conoce su propio proveedor |
| Session Manager (solo QR) | `whatsapp/adapters/session_manager.py` | APPLICATION, específico del adapter QR — el dominio nunca lo conoce |
| Infraestructura real | `marketing/integrations/meta/*`, `notifications/clients/whatsapp.py` | Sin cambios — se envuelve, no se reescribe |

## Contrato canónico (`whatsapp/domain/contracts.py`)

`WhatsAppInboundMessage`/`WhatsAppOutboundMessage` — independientes del proveedor. Un adapter
que no pueda producir un campo lo deja en su default explícito, nunca inventa un valor.

## `ConnectionStatus` vs. `WhatsAppSessionState`

Dos niveles de granularidad reales, deliberadamente separados:

- **`ConnectionStatus`** (`whatsapp/ports/connection.py`) — el contrato genérico del Port:
  `CONNECTED`, `DISCONNECTED`, `ERROR`, `PAIRING_REQUIRED`, `NOT_IMPLEMENTED`,
  **`NOT_CONFIGURED`** (nuevo esta misión — nunca confundido con `ERROR`/`DISCONNECTED`, Regla
  FASE 10/21). Todo adapter lo implementa.
- **`WhatsAppSessionState`** (`whatsapp/adapters/session_manager.py`) — 10 estados granulares
  (`DISABLED`, `NOT_CONFIGURED`, `QR_REQUIRED`, `QR_READY`, `SCANNING`, `AUTHENTICATING`,
  `CONNECTED`, `RECONNECTING`, `DISCONNECTED`, `ERROR`) con una máquina de transiciones válidas
  real (`whatsapp/adapters/session_manager.py::_VALID_TRANSITIONS`). Solo lo usa
  `QRWebSessionAdapter` (expuesto vía `get_session_state()`, no forma parte del Port genérico) —
  Meta Cloud API es stateless por token, no necesita este nivel de detalle.

## Decisión de diseño: Port síncrono, no async

Sin cambios respecto a la versión anterior de este documento — el contexto real de ejecución
(Celery worker síncrono, Django ORM síncrono) no cambió. Ver `ports/connection.py` para el
razonamiento completo.

## Deduplicación

`whatsapp/domain/idempotency.py::WhatsAppIdempotencyGuard` — provider-agnostic, por
`(channel, external_message_id)`. Se invoca **una sola vez**, en el punto de entrada real de
cada adapter (el webhook para Meta Cloud API) — no dentro de `WhatsAppService`.

## Configuración (`WHATSAPP_CONNECTION_TYPE`)

Valores: `QR_WEB_SESSION` | `META_CLOUD_API` (default). La misión pide namespaces separados
`WHATSAPP_QR_*`/`WHATSAPP_META_*` para configuración específica de cada mecanismo — **decisión
real**: las variables de Meta YA EXISTEN en producción con otros nombres
(`META_ACCESS_TOKEN`/`WHATSAPP_PHONE_NUMBER_ID`/`META_APP_SECRET`, compartidas con el resto de
`marketing/integrations/meta/`, no exclusivas de WhatsApp) — renombrarlas sería un cambio real en
`.env.production` sin beneficio funcional (Regla de la misión: "migración incremental sin
breaking change"). Se mantienen tal cual; `WHATSAPP_QR_*` queda reservado para cuando exista un
proveedor QR real que configurar (hoy no hay ninguna variable de ese tipo porque no hay nada que
configurar).

## Qué NO se tocó (deliberado)

- `marketing/integrations/meta/whatsapp.py`, `client.py`, `signatures.py` — transporte oficial real, sin cambios.
- `notifications/models.py::MetaWebhookEvent` — auditoría específica de Meta, sin cambios.
- `notifications/services/commands.py::dispatch_notification` (canal WhatsApp transaccional) — dominio distinto, fuera de alcance.
- `marketing/channels/whatsapp_channel.py` (marketing) — dominio distinto, fuera de alcance.

## Reemplazabilidad demostrada

> **Cambiar de QR_WEB_SESSION a META_CLOUD_API no requiere modificar la lógica de negocio del
> módulo WhatsApp.**

Demostrado con código y pruebas: `whatsapp/tests/test_isolation.py`
(`DomainNeverKnowsConnectionMechanismTests`, análisis AST real del código fuente;
`SwitchConnectionBehaviorTests`, mismo resultado de negocio con 2 adapters distintos inyectados,
en ambos sentidos).
