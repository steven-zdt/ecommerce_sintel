# WHATSAPP_CLOUD_API

**Misión "Migración Arquitectónica de WhatsApp", 2026-09-16.**

## Clasificación explícita

```
Meta Cloud API = OFFICIAL PLATFORM
```

Integración oficial de WhatsApp Business Platform, propiedad de Meta, con credenciales
aprobadas y en uso real en producción.

## Estado real (2026-09-16)

**Activo, configurado, funcionando en producción** — verificado end-to-end en sesiones
anteriores de esta misma serie de misiones (turno real de chat, respuesta real entregada,
webhook real recibiendo mensajes de clientes reales).

## Arquitectura real

- `whatsapp/adapters/meta_cloud_api_adapter.py::MetaCloudAPIAdapter` — envuelve
  `notifications.clients.whatsapp.WhatsAppClient` → `MetaWhatsAppClient` →
  `MetaGraphClient` → `graph.facebook.com`. Transporte real sin cambios, solo expuesto detrás
  del `WhatsAppConnectionPort`.
- Capacidades reales declaradas: `send_text=True`, `receive_text=True`, `webhook=True`,
  `session_persistence=True` (el "estado" es el token de acceso, no expira por reinicio),
  `delivery_status=True` (vía `MetaWebhookEvent`). `send_media`/`receive_media` = `False` —
  `MetaWhatsAppClient` no implementa envío de multimedia hoy, declarado honesto, no fingido.

## `NOT_CONFIGURED` vs `DISCONNECTED` vs `CONNECTED` (verificado, no solo declarado)

| Estado | Condición real |
|---|---|
| `NOT_CONFIGURED` | Falta `META_ACCESS_TOKEN` o `WHATSAPP_PHONE_NUMBER_ID` en `settings` |
| `DISCONNECTED` | Configurado, pero `connect()` no se ha llamado en este proceso (el mecanismo es stateless por token — esto es más una formalidad de interfaz que un estado operativo real, ver docstring del adapter) |
| `CONNECTED` | Configurado y `connect()` se ejecutó con éxito |

## Configuración real (nombres existentes, no renombrados — ver `WHATSAPP_CONNECTION_ARCHITECTURE.md`)

`META_ACCESS_TOKEN`, `META_APP_SECRET`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN`
— compartidas con el resto de `marketing/integrations/meta/` (Facebook/Instagram/Ads), no
exclusivas de WhatsApp. `WHATSAPP_META_*` (nomenclatura que pide la misión) no se introdujo
porque duplicaría variables ya reales y en uso — decisión documentada en
`WHATSAPP_CONNECTION_ARCHITECTURE.md`.

## Ruta real de activación (ya activa, no hipotética)

```
WHATSAPP_CONNECTION_TYPE=META_CLOUD_API   <- default real, sin cambios de infraestructura
```

## Límites reales conocidos (heredados, no introducidos por esta misión)

- Solo texto libre dentro de la ventana de servicio de 24h abierta por el cliente, o plantillas
  aprobadas fuera de esa ventana (`send_template`) — regla real de Meta, no una limitación de
  este código.
- Sin envío/recepción de multimedia todavía.
