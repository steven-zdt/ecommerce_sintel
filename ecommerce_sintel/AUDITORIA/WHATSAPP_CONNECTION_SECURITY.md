# WHATSAPP_CONNECTION_SECURITY

**Actualizado 2026-09-16 — Misión "Migración Arquitectónica de WhatsApp", FASE 29.** Reemplaza la
versión anterior con la nueva nomenclatura y los ítems adicionales que pide explícitamente esta
misión (acceso QR desde panel protegido, unauthorized send, session hijacking, QR session
leakage, credential leakage).

| Ítem | Estado real | Evidencia |
|---|---|---|
| Credential isolation | `META_ACCESS_TOKEN`/`META_APP_SECRET`/`WHATSAPP_PHONE_NUMBER_ID` solo se leen vía `settings.*`, nunca hardcodeados, nunca pasados como parámetro de función logueable | `whatsapp/adapters/meta_cloud_api_adapter.py::_is_configured` — solo `bool(...)`, nunca el valor |
| Secret masking en logs | Ningún log de `whatsapp/` imprime un secreto | `whatsapp/domain/service.py`, `whatsapp/adapters/*.py` — todos los `logger.*` solo incluyen `room.uuid`, últimos 4 dígitos de teléfono, o mensajes de error de proveedor (no credenciales) |
| Webhook authentication | Firma HMAC-SHA256 (`X-Hub-Signature-256`), fail-closed — **sin cambios** | `notifications/api/whatsapp_webhook.py::WhatsAppInboundWebhookView.post` |
| **Acceso QR solo desde panel protegido** | El endpoint `AdminWhatsAppConnectionStatusView` (solo lectura, incluye estado de QR) ya exige `ADMIN_PERMISSIONS` (`IsAuthenticated` + `IsAdminUser`). No existe todavía ningún endpoint de generación/escaneo real de QR (`generate_pairing_qr()` lanza `WhatsAppQRNotImplementedError`) — cuando exista, debe heredar el mismo `ADMIN_PERMISSIONS`, nunca `AllowAny` | `dashboard/api/views.py::AdminWhatsAppConnectionStatusView` |
| QR session protection / QR session leakage / session hijacking | **N/A hoy** — no existe sesión QR real que proteger ni que pueda filtrarse (`QRWebSessionAdapter` es `NOT_IMPLEMENTED`, `WhatsAppSessionManager` nunca sale de `NOT_CONFIGURED`) | `AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` — re-auditar esta fila completa el día que exista un gateway real |
| Meta Cloud API credential protection | Token de acceso vive solo en `settings`/env, nunca en código ni en `WhatsAppInboundMessage.provider_metadata` (ese campo solo guarda `raw_type`) | `meta_cloud_api_adapter.py::translate_inbound` |
| Message spoofing / Sender spoofing | Mitigado por la firma HMAC del webhook (evento rechazado con 403 antes de cualquier lógica de negocio) — **sin cambios** | Mismo mecanismo preexistente |
| Replay | `MetaWebhookEvent` persiste cada evento con `payload_hash`; deduplicación real por `(channel, external_message_id)` vía `WhatsAppIdempotencyGuard`, TTL 24h | `whatsapp/domain/idempotency.py`, test real |
| Duplicate delivery | Mismo mecanismo que Replay | Confirmado en regresión real de `notifications` |
| **Unauthorized send** | `WhatsAppService.send_agent_reply()` solo se invoca desde `send_whatsapp_agent_reply_task`, disparada únicamente por `support/consumers.py::_dispatch_whatsapp_agent_reply` cuando un admin autenticado (`IsAdminUser`, ya verificado por el consumer de WebSocket) responde desde `/panel/soporte` — nunca alcanzable desde un endpoint público | `support/consumers.py`, sin cambios |
| Identity confusion | `WhatsAppCustomerResolver` resuelve por los últimos 10 dígitos del teléfono — **riesgo preexistente, no introducido por esta migración**: 2 clientes con el mismo sufijo podrían colisionar. Documentado, no corregido | `whatsapp/domain/customer_resolver.py` |
| Cross-customer leakage | Cada `ChatRoom` es estrictamente 1:1 con `user` — el único vector real es Identity confusion (arriba) | Sin cambios |

## Test de seguridad real agregado

`whatsapp/tests/test_isolation.py::DomainNeverKnowsConnectionMechanismTests` — análisis AST real
del código fuente (no un grep de texto, que daría falsos positivos contra los propios
docstrings). Confirma que ningún módulo de dominio importa o instancia
`QRWebSessionAdapter`/`MetaCloudAPIAdapter` — control de seguridad real, no solo arquitectónico:
si algún día alguien agrega credenciales específicas de un proveedor dentro del dominio, este
mismo mecanismo puede extenderse para detectarlo.

## Riesgos residuales (heredados, no introducidos)

- Colisión de identidad por sufijo de teléfono de 10 dígitos — riesgo preexistente, no corregido
  (decisión de producto, no bug de esta migración).
- La superficie de seguridad completa de un gateway QR real (protección de la sesión, riesgo de
  secuestro de sesión, filtración del token multi-device) **no está auditada porque no existe
  ningún gateway real** — esta tabla debe re-auditarse por completo el día que
  `AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` se reabra con una decisión de negocio distinta.

## Checkpoint FASE 29 — Estado

**PASS.** Ningún mecanismo de seguridad existente se debilitó. Los ítems específicos de QR se
declaran explícitamente `N/A` (no simulados como "seguros" ni omitidos en silencio) porque no
hay ningún gateway real que auditar.
