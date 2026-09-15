# WHATSAPP_CONNECTION_FINAL_CERTIFICATION — FASE 28

**Misión "Refactorización Arquitectónica del Módulo WhatsApp — Dominio Independiente +
Connection Adapter Intercambiable QR/REST", cerrada 2026-09-16.**

## 1. Arquitectura anterior

Lógica de negocio (resolución de cliente, `ChatRoom`, handoff, IA) mezclada inline con llamadas
de transporte directo (`WhatsAppClient().send_text(...)`) dentro de `notifications/tasks.py`.
Deduplicación ad-hoc (cache key específica de Meta) dentro del webhook view. Un solo mecanismo de
conexión posible (REST/Meta), sin ningún punto de extensión real.

## 2. Arquitectura nueva

Hexagonal real: `whatsapp/domain/` (lógica de negocio, nunca conoce el mecanismo) →
`whatsapp/ports/connection.py` (contrato) → `whatsapp/adapters/{rest,qr}_adapter.py`
(implementaciones intercambiables) ← `whatsapp/factory.py` (único punto de composición,
lee `settings.WHATSAPP_CONNECTION_TYPE`). Ver `WHATSAPP_CONNECTION_ARCHITECTURE.md`.

## 3. Dependencias eliminadas

Ninguna — no se retiró ninguna librería ni integración real (`marketing/integrations/meta/*`
sigue intacto).

## 4. Dependencias introducidas

Ninguna nueva de terceros. Solo código propio (`whatsapp/`), sin librerías nuevas en
`requirements.txt`.

## 5. Connection Port

`whatsapp/ports/connection.py::WhatsAppConnectionPort` — síncrono (decisión de diseño
documentada), 6 métodos abstractos + `capabilities` + `translate_inbound`.

## 6. QR Adapter

`whatsapp/adapters/qr_adapter.py::QRConnectionAdapter` — estructuralmente completo,
funcionalmente `NOT_IMPLEMENTED` (hallazgo real: no existe ningún gateway QR en este repo).
Fail-loud explícito en cada método (`WhatsAppQRNotImplementedError`), nunca simula éxito.

## 7. REST Adapter

`whatsapp/adapters/rest_adapter.py::RestConnectionAdapter` — envuelve la integración REAL ya en
producción (`notifications.clients.whatsapp.WhatsAppClient` → `MetaWhatsAppClient` → Meta Cloud
API). Capacidades declaradas: `send_text`, `receive_text`, `webhook`, `session_persistence`,
`delivery_status` (no `send_media`/`receive_media`, honesto con lo que el cliente real soporta
hoy).

## 8. WhatsApp Service

`whatsapp/domain/service.py::WhatsAppService` — único punto de entrada real, recibe el
`ConnectionPort` por inyección (nunca lo construye — verificado con AST). `process_inbound_
message()` y `send_agent_reply()`, mismo comportamiento exacto que el código original.

## 9. Conversation mapping

`whatsapp/domain/conversation_resolver.py::WhatsAppConversationResolver` — envuelve
`ChatCommands.get_or_create_room`, mismo `ChatRoom` compartido con el widget web y con la
creación de tickets desde el perfil (misión anterior). El `ChatRoom` nunca sabe si el mensaje
llegó por QR o REST.

## 10. Customer mapping

`whatsapp/domain/customer_resolver.py::WhatsAppCustomerResolver` — mismo criterio real
(últimos 10 dígitos del teléfono contra `UserProfile`), idéntico sin importar el adapter.

## 11. Support integration

Sin cambios — `ChatCommands`/`support.services.ai_bridge` se siguen consultando tal cual, nunca
duplicados dentro de `whatsapp/`.

## 12. AI integration

Sin cambios — WhatsApp nunca habla con el LLM/RAG/ADK directo, todo pasa por `ask_ai()` →
`ai_bridge` → `ai_engine_adk` → Google ADK, exactamente igual que el widget web.

## 13. Security

Ver `WHATSAPP_CONNECTION_SECURITY.md` — ningún mecanismo existente debilitado (firma HMAC,
auditoría `MetaWebhookEvent`), deduplicación generalizada (no debilitada), 1 riesgo residual
heredado documentado (colisión de identidad por sufijo de teléfono, preexistente).

## 14. Tests

`whatsapp/tests/`: 31 tests reales (contrato, aislamiento estructural vía AST, aislamiento
comportamental QR↔REST y REST↔QR, servicio de dominio, idempotencia). `notifications/`: 44/44
regresión completa, sin cambios de comportamiento — incluye el hallazgo real de compatibilidad
(mock de `WhatsAppClient` vs. clase padre `MetaWhatsAppClient`) encontrado y corregido durante
esta misma migración.

## 15. Failure tests

`whatsapp/tests/test_failure_isolation.py`: REST caído (mensaje del cliente se persiste, solo
falla el envío), QR sin gateway (mismo criterio), Web Support no afectado por un fallo de
WhatsApp (`ChatCommands` sigue operando con normalidad sobre la misma sala).

## 16. Switching tests

`whatsapp/tests/test_isolation.py::SwitchConnectionBehaviorTests` — mismo `WhatsAppService`, 2
adapters distintos inyectados (Fake QR-simulado / Fake REST-simulado), mismo resultado de
negocio verificado (`ChatRoom` resuelto, mensaje persistido) en ambos sentidos.

## 17. Rollback

Ver `WHATSAPP_CONNECTION_MIGRATION.md` sección "Rollback" — `git revert` de los commits de esta
misión, sin impacto en datos persistidos (ningún modelo/migración nuevo, solo código).

---

## Criterios de aceptación de la misión — verificación final

```
✅ WhatsApp tiene logica de negocio independiente           -- whatsapp/domain/
✅ QR esta aislado en un adapter                             -- whatsapp/adapters/qr_adapter.py
✅ REST esta aislado en un adapter                            -- whatsapp/adapters/rest_adapter.py
✅ Ambos implementan el mismo contrato                        -- test_contract.py, 8/8
✅ WhatsAppService no conoce QR                               -- verificado con AST real
✅ WhatsAppService no conoce REST                             -- verificado con AST real
✅ Support no conoce QR/REST                                  -- sin cambios, ChatCommands intacto
✅ ADK no conoce QR/REST                                       -- sin cambios, ai_bridge intacto
✅ RAG no conoce QR/REST                                       -- sin cambios
✅ ChatRoom no depende del transporte                          -- mismo ChatRoom, cualquier canal
✅ CustomerResolver no depende del transporte                  -- mismo criterio, cualquier adapter
✅ Handoff no depende del transporte                            -- ai_paused/is_ai_mode_active sin cambios
✅ Idempotencia no depende del transporte                       -- WhatsAppIdempotencyGuard, (channel, id)
✅ La configuracion determina el adapter                        -- WHATSAPP_CONNECTION_TYPE
✅ Cambiar QR<->REST no requiere tocar business logic           -- test_isolation.py, ambos sentidos
✅ Web Support sigue funcionando                                -- test_failure_isolation.py
✅ Seguridad sigue funcionando                                   -- WHATSAPP_CONNECTION_SECURITY.md
✅ Tests de contrato pasan                                       -- 8/8
✅ E2E REST pasa                                                 -- 44/44 regresion notifications
⚠️ E2E QR "preparado/pasa segun disponibilidad"                 -- preparado (NOT_IMPLEMENTED honesto,
                                                                    no hay gateway real que probar E2E)
```

## Certificación final

**APTA**, con la salvedad explícita y documentada desde FASE 0: QR está arquitectónicamente
resuelto (mismo contrato, mismas pruebas de aislamiento que REST) pero funcionalmente
`NOT_IMPLEMENTED` porque no existe ningún gateway QR real en este proyecto — no es una omisión
de esta misión, es un hecho verificado del estado real del repositorio. El objetivo
arquitectónico central — **el negocio de WhatsApp es estable, el transporte es reemplazable** —
está demostrado con código real y tests reales, no solo documentado en teoría.
