# WHATSAPP_CONNECTION_ARCHITECTURE

**Misión "Refactorización Arquitectónica del Módulo WhatsApp", 2026-09-16.** Diseño real
implementado — ver `AUDITORIA/WHATSAPP_CONNECTION_BASELINE.md` (FASE 0) para el hallazgo crítico
que motivó las decisiones de esta arquitectura (QR no existe hoy, REST sí).

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
     RestConnectionAdapter            QRConnectionAdapter
     (whatsapp/adapters/               (whatsapp/adapters/
      rest_adapter.py)                  qr_adapter.py)
                |                             |
                v                             v
      MetaWhatsAppClient                NOT_IMPLEMENTED
      (marketing/integrations/          (sin gateway real,
       meta/, YA EXISTIA)                estructuralmente listo)
                |
                v
        graph.facebook.com (Meta Cloud API, REAL, en produccion)
```

## Capas y responsabilidades reales

| Capa | Módulo | Conoce el mecanismo de conexión |
|---|---|---|
| Dominio | `whatsapp/domain/*.py` | **NUNCA** — verificado con AST real, no solo revisión manual (`whatsapp/tests/test_isolation.py`) |
| Puerto | `whatsapp/ports/connection.py` | Define el contrato, no una implementación |
| Composición | `whatsapp/factory.py` | **ÚNICO** lugar con `if connection_type == ...` |
| Adapters | `whatsapp/adapters/{rest,qr}_adapter.py` | Cada uno solo conoce su propio proveedor |
| Infraestructura real | `marketing/integrations/meta/*`, `notifications/clients/whatsapp.py` | Sin cambios — se envuelve, no se reescribe |

## Contrato canónico (`whatsapp/domain/contracts.py`)

`WhatsAppInboundMessage`/`WhatsAppOutboundMessage` — independientes del proveedor. Un adapter
que no pueda producir un campo lo deja en su default explícito, nunca inventa un valor.

## Decisión de diseño: Port síncrono, no async

El prompt maestro de la misión no exige async/sync. El contexto real de ejecución de este
dominio en SINTEL es 100% síncrono (Celery worker `notifications`, Django ORM síncrono,
`MetaWhatsAppClient` usa `requests`). Hacer el contrato async habría significado envolver código
síncrono real con `sync_to_async` sin ningún beneficio — complejidad sin evidencia de necesidad
(Regla 1 de la misión). Documentado explícitamente en `ports/connection.py`.

## Deduplicación (FASE 14)

`whatsapp/domain/idempotency.py::WhatsAppIdempotencyGuard` — provider-agnostic, por
`(channel, external_message_id)`. Se invoca **una sola vez**, en el punto de entrada real de
cada adapter (el webhook para REST) — no dentro de `WhatsAppService`, para no romper la
idempotencia real (ver docstring de `process_inbound_message`).

## Qué NO se tocó (deliberado)

- `marketing/integrations/meta/whatsapp.py`, `client.py`, `signatures.py` — transporte REST real, sin cambios.
- `notifications/models.py::MetaWebhookEvent` — auditoría REST-específica, sin cambios.
- `notifications/services/commands.py::dispatch_notification` (canal WhatsApp transaccional) — dominio distinto, fuera de alcance.
- `marketing/channels/whatsapp_channel.py` (marketing) — dominio distinto, fuera de alcance.

## Reemplazabilidad demostrada

> **Cambiar de QR a REST no requiere modificar la lógica de negocio del módulo WhatsApp.**

Demostrado con código y pruebas: `whatsapp/tests/test_isolation.py`
(`DomainNeverKnowsConnectionMechanismTests`, análisis AST real del código fuente;
`SwitchConnectionBehaviorTests`, mismo resultado de negocio con 2 adapters distintos inyectados,
en ambos sentidos QR→REST y REST→QR).
