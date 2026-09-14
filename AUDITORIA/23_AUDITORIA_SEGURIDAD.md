# 23 — Auditoría Enterprise: Seguridad (Fase 11)

> **Fase 11 completada y cerrada 2026-08-01** — continúa el plan iniciado en
> [15](15_AUDITORIA_SUPPORT_OMNICANAL.md)-[22](22_AUDITORIA_AI_CONTEXT_RAG.md). El brief pedía
> validar JWT, Refresh, Origin, Rate Limit, Flood, Spam, DoS, Replay, Permissions, Anonymous,
> Escalamiento, Logs, Auditoría. Varios ya se cubrieron a fondo en fases previas (JWT/Refresh —
> bug de producción resuelto el mismo día; Origin — B5 de Fase 4, riesgo bajo evaluado; Permisos —
> F1/F2 de Fase 2; Logs/Auditoría — S1 de Fase 3, `SecurityEvent.AI_ACTION_EXECUTED`). Esta fase
> se concentró en lo genuinamente sin verificar: **Flood/Spam/DoS a nivel del WS crudo**,
> Anonymous, y Escalamiento.

## Hallazgo real — WS sin límite de frecuencia ni tamaño de mensaje (resuelto el mismo día)

`SupportChatConsumer.receive()` no tenía **ningún** límite de frecuencia ni de tamaño de mensaje,
distinto del rate-limit de turnos de IA (`ai_bridge.is_ai_rate_limited`, Fase 1 C1), que solo
protege las respuestas del LLM — no la escritura cruda en BD ni la difusión en vivo. Un cliente
(o un admin comprometido) podía:

1. **Enviar mensajes ilimitados por segundo** — cada uno dispara un `ChatMessage.objects.create()`
   (escritura real en BD) más `group_send` a `support_admins` (difunde a **todos** los admins
   conectados en tiempo real). Sin IA de por medio, sin ningún costo de LLM que lo frenara.
2. **Enviar un mensaje de tamaño arbitrario** (megabytes) — `ChatMessage.message` es un
   `TextField` sin límite, y se difunde completo a todas las conexiones del grupo.

Ambos son vectores de DoS reales: saturar la base de datos y saturar los navegadores de todos los
agentes de soporte conectados, sin necesidad de comprometer ninguna cuenta ni evadir el rate-limit
de IA (que nunca aplicaba a este camino).

**Resuelto:** `support/services/commands.py` gana `ChatCommands.is_message_flood_limited(user)`
(ventana fija de 60s, 30 mensajes por usuario — mismo patrón `cache.add`/`cache.incr` atómico ya
usado por `ai_bridge.is_ai_rate_limited`) y la constante `MAX_MESSAGE_LENGTH=4000` (mismo valor ya
establecido del lado de `ai_engine`, Fase 2 G1, por consistencia). `consumers.py::receive()` ahora
trunca el mensaje al límite y aplica el chequeo de flood **antes de cualquier escritura**, para
ambas ramas (cliente y admin) por igual — un mensaje descartado por flood ni se guarda ni se
transmite, sin cerrar la conexión (evita que un flood accidental de un cliente legítimo lo deje
sin poder reconectar).

## Otros ítems verificados sin hallazgos nuevos

- **Anonymous**: `connect()` cierra con `code=4001` si `scope['user']` no está autenticado —
  confirmado, sin cambios necesarios.
- **Escalamiento de privilegios**: la rama cliente de `receive()` siempre opera sobre `self.room`
  (la propia sala del usuario, fijada en `connect()`) — sin forma de manipular `room_uuid` para
  acceder a la sala de otro. La rama admin exige `user.is_staff and user.is_superuser` resuelto
  directamente del JWT validado, sin ningún camino alternativo. Sin hallazgo.
- **Replay**: fuera del WS, `notifications/api/whatsapp_webhook.py` ya tiene dedupe por
  `message.id` (hallazgo cerrado en una auditoría previa, documentado en su propio archivo). El
  WS en sí no tiene un concepto de "replay" aplicable (JWT con expiración corta, sin firma
  reutilizable de mensajes individuales).

## Resumen ejecutivo

De la lista completa del brief de seguridad, el único gap real y no cubierto por fases anteriores
era la ausencia total de rate-limiting y de límite de tamaño a nivel del WS crudo — un vector de
DoS concreto y explotable por cualquier cliente autenticado, sin necesidad de comprometer nada.
Cerrado con el mismo patrón ya validado en producción (`cache.add`/`cache.incr` atómico), 2 tests
nuevos, y verificación completa de la suite (24/24). El resto de los ítems del brief (Anonymous,
Escalamiento, Replay) se verificaron sin hallazgos nuevos — ya cubiertos por el diseño existente o
por fases previas.

## Roadmap — estado actualizado

| Fase | Estado |
|------|--------|
| 1-8 | Hechas — ver documentos 15-22 |
| 9 | Hecha — ver [24](24_AUDITORIA_NOTIFICATIONS_SUPPORT.md) |
| 11 — Seguridad | **Hecha (este documento) — flood/DoS del WS cerrado** |
| 10, 12-16 | Fuera de alcance de esta sesión (decisión explícita del usuario) |
