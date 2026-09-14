# 20 — Auditoría Enterprise: omnicanalidad (Fase 6)

> **Fase 6 completada 2026-08-01 — cerrada sin lanzar una auditoría nueva completa.** La pregunta
> de fondo de esta fase ("transformar `support` en un sistema omnicanal, todos los canales
> compartiendo Conversation/Timeline/Contexto/Memoria/Historial/Customer360") es la MISMA pregunta
> que [19_AUDITORIA_COMMUNICATION_CENTER_CANALES.md](19_AUDITORIA_COMMUNICATION_CENTER_CANALES.md)
> (Fase 5) ya investigó a fondo con evidencia de código real, ese mismo día. Repetir el análisis
> completo hubiera producido la misma conclusión con otro informe largo — en vez de eso, esta fase
> se limita a (a) confirmar que la conclusión de Fase 5 sigue aplicando y (b) cubrir el terreno
> genuinamente nuevo: el estado real de los 2 canales que el brief menciona y que nunca se habían
> tocado en ninguna fase anterior (Llamadas, Video Atención).

## Conclusión de Fase 5 — sigue vigente, no se repite el análisis

Fusionar todo bajo un modelo de datos único sigue siendo prematuro: 3 implementaciones de
"conversación" sin modelo compartido, canal con IA apagado en producción, volumen bajo. La única
acción concreta que valía la pena (M2 — visibilidad de WhatsApp en `ChatRoom`) ya se implementó y
desplegó el mismo día. Ver Fase 5 para el detalle completo — no se repite aquí.

## Estado real de los 8 canales del brief

| Canal | Estado | Comparte `ChatRoom`/Customer 360 |
|---|---|---|
| Web Chat | Real, en producción | Sí (es la fuente) |
| WhatsApp | Real, en producción | **Sí, desde hoy (M2)** — antes no |
| Correo | Real (plantilla `ticket_soporte_sin_seguimiento` con `email_body`) | No (push-only, sin conversación) |
| IA | Real, apagada en producción (`AI_SUPPORT_CHAT_ENABLED=False`) | Sí, vía `ChatMessage.ai_metrics` |
| Operador Humano | Real (`SupportDashboardView.vue`, Human Handoff) | Sí |
| Tickets | No es un canal — es terminología para `ChatRoom` con `ai_paused=True` (Fase 5, M3) | N/A |
| **Llamadas** | Parcialmente preparado: `CommunicationPanel.vue` tiene la opción "Solicitar llamada", que abre el chat real de `support` con un prefill pidiendo el número de contacto — **no hay integración telefónica real** (sin Twilio/proveedor de voz, confirmado por ausencia total en el repo), es una solicitud manual vía chat, no una llamada en sí | Sí (vía el chat que abre) |
| **Video Atención** | **No preparado en absoluto** — cero menciones de video/WebRTC en todo el repo, ningún componente, endpoint, ni placeholder | No |

## Recomendación

No crear infraestructura nueva para Llamadas/Video Atención ahora. "Solicitar llamada" ya cubre la
necesidad real de forma pragmática (un agente humano ve la solicitud y llama por fuera de la
plataforma) sin inventar telefonía VoIP para un volumen que no lo justifica. Video Atención no
tiene ninguna señal de necesidad real en el proyecto — construir un placeholder "preparado sin
requerir cambios de arquitectura" (como se hizo antes con las 3 opciones que luego SÍ se
activaron) sería razonable únicamente si hay una decisión de negocio concreta de ofrecerlo; no es
un gap técnico a cerrar de oficio.

## Resumen ejecutivo

Fase 6 no aportó una conclusión nueva sobre unificación de canales — la de Fase 5 sigue vigente y
ya se actuó sobre ella (M2). El único terreno genuinamente nuevo (Llamadas, Video Atención) se
verificó: Llamadas tiene una solución pragmática ya en producción (solicitud manual vía chat, sin
telefonía real), Video Atención no existe ni como placeholder. Ninguno de los dos amerita trabajo
nuevo sin una decisión de negocio explícita que lo respalde primero.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1 — Auditoría global de `support` | Hecha, 11/11 cerrados |
| 2 — Sincronización con AI Engine | Hecha, 7/8 cerrados |
| 3 — Sincronización documental cross-módulo | Hecha, 4/4 cerrados |
| 4 — Producción y resiliencia WS | Hecha, 3/12 cerrados |
| 5 — Communication Center y canales | Hecha, M2 cerrado |
| 6 — Omnicanalidad | **Hecha (este documento) — confirma Fase 5, sin trabajo nuevo requerido** |
| 7-16 | Pendientes |
