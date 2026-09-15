# WHATSAPP_CONNECTION_SECURITY

**Misión "Refactorización Arquitectónica del Módulo WhatsApp", FASE 19, 2026-09-16.**

| Ítem | Estado real | Evidencia |
|---|---|---|
| Credential isolation | `META_ACCESS_TOKEN`/`META_APP_SECRET`/`WHATSAPP_PHONE_NUMBER_ID` solo se leen vía `settings.*`, nunca hardcodeados, nunca pasados como parámetro de función logueable | `whatsapp/adapters/rest_adapter.py::_is_configured` — solo `bool(...)`, nunca el valor |
| Secret masking en logs | Ningún log nuevo de `whatsapp/` imprime un secreto — verificado leyendo cada `logger.*` del paquete nuevo | `whatsapp/domain/service.py`, `whatsapp/adapters/*.py` — todos los `logger.*` solo incluyen `room.uuid`, últimos 4 dígitos de teléfono, o mensajes de error de proveedor (no credenciales) |
| Webhook authentication | Firma HMAC-SHA256 (`X-Hub-Signature-256`), fail-closed — **sin cambios**, no se tocó `marketing/integrations/meta/signatures.py` | `notifications/api/whatsapp_webhook.py::WhatsAppInboundWebhookView.post` |
| QR session protection | **N/A hoy** — no existe sesión QR real que proteger (`QRConnectionAdapter` es `NOT_IMPLEMENTED`) | `AUDITORIA/WHATSAPP_CONNECTION_BASELINE.md` |
| REST credential protection | Token de acceso vive solo en `settings`/env, nunca en código ni en `WhatsAppInboundMessage.provider_metadata` (ese campo solo guarda `raw_type`, ver `rest_adapter.py::translate_inbound`) | Revisión de código real |
| Message spoofing | Mitigado por la firma HMAC del webhook (si la firma es inválida, el evento se rechaza con 403 antes de llegar a cualquier lógica de negocio) — **sin cambios** | Mismo mecanismo preexistente |
| Replay | `MetaWebhookEvent` persiste cada evento con `payload_hash`; deduplicación real por `(channel, external_message_id)` vía `WhatsAppIdempotencyGuard`, TTL 24h | `whatsapp/domain/idempotency.py`, verificado con test real (`whatsapp/tests/test_service.py::WhatsAppIdempotencyGuardTests`) |
| Duplicate delivery | Mismo mecanismo que Replay — Meta reintrega el webhook si no recibe 200 a tiempo, la dedup lo absorbe | Confirmado en la regresión real de `notifications` (log real: "mensaje ... ya procesado, se ignora reintento de Meta") |
| Identity confusion | `WhatsAppCustomerResolver` resuelve por los últimos 10 dígitos del teléfono contra `UserProfile` — **riesgo preexistente, no introducido por esta migración**: 2 clientes con el mismo sufijo de 10 dígitos (números internacionales distintos) podrían colisionar. Documentado, no corregido (fuera de alcance — es una regla de negocio preexistente de `notifications/tasks.py` original, extraída tal cual) | `whatsapp/domain/customer_resolver.py` |
| Cross-customer leakage | Cada `ChatRoom` es estrictamente 1:1 con `user` (`ChatCommands.get_or_create_room`) — un mensaje resuelto a un `user` incorrecto (ver Identity confusion arriba) sería el único vector real, no hay otro camino de mezcla entre clientes | Mismo Service Layer de `support`, sin cambios |

## Test de seguridad real agregado en esta fase

`whatsapp/tests/test_isolation.py::DomainNeverKnowsConnectionMechanismTests` no es solo un test
arquitectónico — es también un control de seguridad real: si en el futuro alguien agrega
credenciales/tokens específicos de un proveedor dentro del dominio (violando la separación), ese
mismo tipo de análisis AST se puede extender para detectarlo. No se implementó un scanner de
secretos dedicado en esta fase — no hay evidencia de que el existente (`_is_configured()`,
verificación booleana) sea insuficiente.

## Riesgos residuales (heredados, no introducidos)

- Colisión de identidad por sufijo de teléfono de 10 dígitos (ver tabla arriba) — riesgo
  preexistente de `notifications/tasks.py` original, ahora en `whatsapp/domain/customer_resolver.py`,
  extraído tal cual, no corregido (cambiar el criterio de resolución es una decisión de producto,
  no un bug de esta migración).
- `QRConnectionAdapter` no tiene superficie de seguridad real que auditar hoy — cuando se integre
  un gateway QR real, esta sección debe re-auditarse (sesión de navegador/pairing token son un
  vector de ataque real que no existe todavía en este repo).

## Checkpoint FASE 19 — Estado

**PASS.** Ningún mecanismo de seguridad existente se debilitó — la firma del webhook, el
mecanismo de auditoría (`MetaWebhookEvent`), y la deduplicación siguen siendo tan fuertes como
antes (esta última, generalizada, no debilitada). Ningún secreto nuevo se introdujo en logs ni en
el contrato canónico.
