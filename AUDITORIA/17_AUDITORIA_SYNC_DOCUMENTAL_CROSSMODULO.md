# 17 — Auditoría Enterprise: sincronización documental cross-módulo (Fase 3)

> **Fase 3 completada y cerrada 2026-08-01** — continúa el plan de 16 fases iniciado en
> [15_AUDITORIA_SUPPORT_OMNICANAL.md](15_AUDITORIA_SUPPORT_OMNICANAL.md) (Fase 1) y
> [16_AUDITORIA_AI_ENGINE_SYNC.md](16_AUDITORIA_AI_ENGINE_SYNC.md) (Fase 2), ambas cerradas
> completas el mismo día. A diferencia de esas dos fases (que corrigieron la documentación PROPIA
> de `support` y `ai_engine`), esta Fase 3 mira la dirección opuesta: cómo describen OTROS
> módulos (`notifications`, `security`, `frontend`, `organization`, `core`, `marketing`,
> `accounts`, `operations`, `IMPLEMENTATION_SUMMARY.md`) su relación con `support`. Todos los
> hallazgos reales son de documentación — ningún bug de código nuevo.

## Hallazgos reales (3, todos resueltos el mismo día)

**N1. `notifications/.AGENT/docs/ARQUITECTURA_COMPLETA_NOTIFICATIONS.md` documentaba un slug de
plantilla ficticio.** (P2, resuelto)
La tabla "Plantillas en BD" listaba `support_new_message` — nunca existió en ninguna migración,
seed, ni caller real. El slug real que `support/tasks.py::notify_unattended_escalated_tickets`
dispara es `ticket_soporte_sin_seguimiento` (migración `0004_seed_proactive_templates.py`), que
no aparecía en absoluto. Faltaban también los otros 3 slugs de la Fase 11 Proactividad
(`cotizacion_sin_respuesta`, `renting_por_vencer`, `pago_rechazado_seguimiento`) y el de
cross-sell (`cliente_recurrente_cross_sell`, migración `0005`) — conteo real 13, no 9. Tampoco se
documentaba `dispatch_notification_once()` (la variante idempotente que `support` sí usa).
*Corregido:* tabla completa con los 13 slugs reales + sub-sección nueva explicando
`dispatch_notification_once`.

**S1. `security/.AGENT/docs/ARQUITECTURA_COMPLETA_SECURITY.md` no documentaba
`SecurityEvent.AI_ACTION_EXECUTED`.** (P2, resuelto)
Ese evento existe desde `security/migrations/0006` y lo escribe un helper compartido real
(`ecommerce/internal_ai_utils.py::log_ai_action()`) invocado desde 5 apps, incluido
`support/api/internal_ai.py::AiOpenSupportTicketView` — exactamente la integración que esta fase
pidió verificar. Sin esta entrada, alguien auditando seguridad desde el doc concluiría
(incorrectamente) que las escrituras del AI Core no dejan rastro de auditoría.
*Corregido:* agregado a la lista de `event_type` del modelo + fila nueva en "Integraciones reales".

**F1/F2. `frontend/.AGENT/doc/ARQUITECTURA_COMPLETAFRONEND.md` §5.1 describía el estado
INTERMEDIO (mismo día) de la migración del Communication Center, ya superado.** (P2, resuelto)
Dos afirmaciones quedaron obsoletas por un cambio posterior el mismo día (2026-07-31):
1. Decía que "Asistente IA"/"Solicitar llamada"/"Enviar mensaje" eran placeholders deshabilitados
   con badge "Próximamente" — en realidad son entry points activos que abren el chat real de
   `support` (mismo canal WebSocket que `SupportChatWidget`).
2. Decía que `CommunicationCenter` se apilaba arriba de `SupportChatWidget` (`bottom:88px`) para
   evitar colisión — en realidad `SupportChatWidget` ya no tiene botón flotante propio (su
   trigger se migró a las 3 opciones de arriba), así que `CommunicationCenter` es el único FAB
   permanente (`bottom:20px` fijo), sin apilamiento condicional.
*Corregido:* ambos párrafos reescritos para reflejar el estado final.

## Módulos sin hallazgos (confirmado, no solo asumido)

`organization`, `core`, `marketing`, `operations` no mencionan `support` — verificado que es
correcto en cada caso (sin integración real de código que documentar; en el caso de
`organization`, confirma la separación deliberada Communication Center/`support` ya cerrada en
Fase 1). `accounts` tiene una única mención, correcta y sin relación con el chat (lista `support`
entre las apps desacopladas de `UserProfile.user_type`).

## I1 — Menor (P4, resuelto)

`IMPLEMENTATION_SUMMARY.md`: el título de la sección `support` decía "doc propio desactualizado"
pese a que el propio cuerpo de esa sección ya documentaba la resolución del 2026-07-31. Corregido
el título para que coincida con el contenido.

## Resumen ejecutivo

De 8 documentos de arquitectura auditados en la dirección "¿cómo describen a `support`?", 4 están
genuinamente libres de hallazgos (sin mención porque no hay integración real, no por omisión).
Los 3 hallazgos reales — slug de notificación inventado, evento de seguridad no documentado, y
arquitectura de UI descrita en un estado ya superado — comparten un patrón: todos describían un
estado *anterior* al actual, no inventado desde cero, lo que confirma que la causa raíz es
sincronización tardía, no documentación de mala fe. Los 3 se cerraron el mismo día junto con un
ajuste cosmético en `IMPLEMENTATION_SUMMARY.md`. Cero bugs de código nuevos encontrados en esta
fase — coherente con que las Fases 1 y 2 ya habían auditado el código real de `support` y
`ai_engine` directamente.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1 — Auditoría global de `support` | **Hecha, 11/11 hallazgos cerrados** |
| 2 — Sincronización con AI Engine | **Hecha, 7/8 hallazgos cerrados** (A3 pendiente, latente) |
| 3 — Sincronización documental cross-módulo | **Hecha, 4/4 hallazgos cerrados (este documento)** |
| 4-16 | Pendientes |
