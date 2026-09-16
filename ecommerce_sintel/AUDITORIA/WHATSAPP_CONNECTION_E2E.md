# WHATSAPP_CONNECTION_E2E

**Misión "Migración Arquitectónica de WhatsApp", FASE 26-28, 2026-09-16.**

## E2E Meta Cloud API — REAL, ejecutable hoy

El flujo completo (FASE 13 de la misión) está verificado real en sesiones anteriores de este
mismo proyecto (no simulado para esta misión — reusa evidencia real ya confirmada):

```
Cliente real por WhatsApp -> Meta -> webhook -> process_whatsapp_inbound_task
   -> WhatsAppService.process_inbound_message() -> CustomerResolver -> ChatRoom
   -> ai_bridge.ask_ai() -> ai_engine_adk -> Google ADK -> RAG (si intent=="knowledge")
   -> respuesta generada -> WhatsAppService envía -> MetaCloudAPIAdapter.send_message()
   -> MetaWhatsAppClient -> graph.facebook.com -> entregado al cliente real
```

Verificado con turnos reales contra producción (`sync-verify-1`, sesión de sync a producción de
esta serie de misiones) — respuesta real generada por ADK, entregada, `ChatMessage` persistido
con `ai_metrics` reales.

## E2E QR Web Session — NO ejecutable (bloqueado, documentado explícitamente)

**No se ejecuta** — `AUDITORIA/WHATSAPP_QR_PROVIDER_EVALUATION.md` (FASE 8) concluyó BLOQUEADO
antes de llegar a esta fase. Los 16 pasos que pide la misión (FASE 26) requieren un gateway real
conectado, que no existe. Documentado aquí en vez de simulado:

| Paso pedido | Estado real |
|---|---|
| 1-5. Abrir panel, seleccionar QR, generar QR, escanear, CONNECTED | No ejecutable — `generate_pairing_qr()` lanza `WhatsAppQRNotImplementedError` explícito |
| 6-16. Enviar/recibir/procesar/responder por WhatsApp real vía QR | No ejecutable, mismo motivo |

**Lo que SÍ se verificó** (evidencia sustituta real, no simulación del E2E completo): el mismo
`WhatsAppService` que procesaría estos pasos con Meta Cloud API los procesa idénticos con un
adapter QR de prueba (`FakeConnectionAdapter`, `whatsapp/tests/test_isolation.py`) — prueba de
que la arquitectura está lista para el día que exista un gateway real, sin fingir que ese día ya
llegó.

## E2E Failover — REAL, ejecutado

`whatsapp/tests/test_failure_isolation.py`:
- Meta Cloud API caída durante el envío → mensaje del cliente + respuesta de IA ya persistidos,
  falla contenida como `"send_failed"`, Support Core sigue operativo (`ChatCommands.save_message`
  verificado funcionando sobre la misma sala después del fallo).
- Gateway QR sin implementar → mismo comportamiento, mismo contenimiento del fallo.

## Session Persistence (FASE 28) — N/A por ahora

Solo aplica a un mecanismo con sesión real (QR). Con `QRWebSessionAdapter` en `NOT_CONFIGURED`
permanente, no hay sesión que persistir — documentado como pendiente de la misma decisión de
negocio que bloquea el resto de FASE 26.

## Checkpoint FASE 26-28 — Estado

**PASS con las salvedades explícitas de arriba.** Ningún resultado se fabricó — el E2E de Meta
Cloud API es real y ya estaba verificado; el E2E de QR se documenta como no ejecutable, con la
evidencia sustituta real (contract/isolation tests) que sí se pudo producir sin un gateway.
