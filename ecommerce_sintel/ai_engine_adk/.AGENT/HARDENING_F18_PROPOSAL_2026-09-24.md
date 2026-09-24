# HARDENING — FASE 18 (soporte humano y safe handoff, P1): IMPLEMENTADO EN DEV (defaults = comportamiento exigido por el plan)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §22 ("human takeover => la IA deja de responder automaticamente, salvo reactivacion explicita"). Regla firme: **el asistente no ejecuta tests**; los tests se escribieron y NO se ejecutaron (solo `py_compile` + ASCII + inspeccion). Nada se aplico en produccion.

## 1. Hallazgos (lectura de codigo)
| # | Requisito §22 | Hallazgo | Estado |
|---|---|---|---|
| G1 | Toma de control humana => la IA se calla | `is_ai_mode_active` exige `not ai_paused` y `assigned_admin is None`. Un admin que **responde por el WebSocket** (`consumers.py`, rama admin) **no se asigna ni pausa la IA**: el siguiente mensaje del cliente disparaba OTRA respuesta automatica sobre la del humano (salvo que el panel asignara la sala por otro camino) | **Corregido** (C1) |
| G2 | "salvo reactivacion explicita" | **Nada en todo el codigo pone `ai_paused=False`**: tras un handoff (ticket abierto por el asistente o por el cliente) la IA nunca vuelve a esa sala; no existia la reactivacion explicita | **Corregido** (C2) |
| G3 | Modelo no disponible => handoff humano | El asistente responde "un agente humano revisara tu mensaje" (marcador degradado, timeout de F3, cola llena de F13) pero **no avisaba a nadie**: promesa sin respaldo. La sala tampoco se pausa (correcto: es transitorio) | **Corregido** (C3) |
| G4 | Low confidence / peticion sensible / conflicto de politica / fallo de tool => handoff | El unico disparador real es que el **LLM decida** llamar a `abrir_ticket_soporte`; ningun camino determinista. (`grounding` UNSUPPORTED y los fallos de tool se resuelven dentro del turno sin escalar) | **Pendiente** (propuesta abajo) |
| G5 | Seguimiento de salas escaladas | Existe `notify_unattended_escalated_tickets` (2 h sin actividad, dedupe por sala) | OK |
| G6 | WhatsApp | `process_whatsapp_inbound_task` respeta `is_ai_mode_active`/`ai_paused`; **no** avisa a admins cuando el motor esta caido (camino `ask_ai() is None` de Celery) | **Pendiente** |

## 2. Cambios entregados
### C1 — Toma de control humana (`support/consumers.py`, `ChatCommands.pause_ai_for_human_takeover`)
Cuando un admin responde en una sala se ejecuta un **UPDATE atomico y condicional** `ai_paused=False -> True` (no depende de una instancia vieja del modelo) y se registra `ai_operation_event=ai_paused_human_reply`. Flag `AI_PAUSE_ON_HUMAN_REPLY` (default **true** = lo que exige el plan; `false` = comportamiento anterior).
### C2 — Reactivacion explicita (`POST /api/v1/support/chats/<room_uuid>/resume-ai/`, `ChatCommands.resume_ai`)
Solo administradores (`IsAdminUser`: 401 sin sesion, 403 a clientes). Solo salas abiertas (400 en cerradas), uuid mal formado o inexistente -> 404 (no 500). Pone `ai_paused=False` y **libera `assigned_admin`** (porque `is_ai_mode_active` tambien lo exige), deja un mensaje visible del asistente ("volvio a atender esta conversacion...") transmitido en vivo al cliente y a los admins, y registra `ai_operation_event=ai_resumed room=... admin=...`. Es el unico camino para volver a la IA.
### C3 — Aviso real ante un turno degradado (`ChatCommands.alert_admins_ai_degraded`)
Cuando el turno termina degradado (`engine_unavailable`: sin respuesta, timeout de turno F3, cola llena de F13) se avisa en vivo al grupo `support_admins` con la etiqueta "[Asistente no disponible]", con **cooldown por sala** (`cache.add` atomico; default 15 min) para no inundar durante una caida y sin romper nunca el chat (excepciones capturadas y logueadas). Flags: `AI_DEGRADED_ADMIN_ALERT` (default true) y `AI_DEGRADED_ALERT_COOLDOWN_SECONDS` (900).
Flags nuevas en `ecommerce/settings/base.py` con default inocuo; si las cambias en un entorno, replicarlas en `.env` **y** `.env.production` en el mismo cambio (incidente del 503).
Tests escritos, NO ejecutados: `support/test_handoff_f18.py` (pausa idempotente y sin depender de instancia vieja, reactivacion 401/403/200/400/404, libera asignacion, mensaje del asistente, aviso una vez por ventana, apagable, fallo del aviso no rompe, puntos de conexion en el consumer).

## 3. Pendiente (no implementado; con propuesta)
1. **Disparadores deterministas de handoff (G4)**: (a) peticion EXPLICITA de un humano ("hablar con una persona/agente"): el router ya detecta el intent `support`; el workflow abriria el ticket sin depender de que el LLM lo decida; (b) temas sensibles (fraude, cobros no reconocidos, datos personales): lista de patrones -> handoff directo; (c) fallo repetido de una tool critica o grounding UNSUPPORTED dos veces seguidas en la sesion -> ofrecer handoff. Cambia el runtime del ADK: propuesta aparte con casos de F10 antes de activarlo.
2. **Boton "Reactivar asistente" en `/panel/soporte`** (frontend): el endpoint ya existe; falta el control en la UI (con confirmacion) y mostrar el estado (IA activa / pausada / asignada a X).
3. **WhatsApp (G6)**: en `process_whatsapp_inbound_task`, si `ask_ai()` devuelve `None`, llamar `ChatCommands.alert_admins_ai_degraded(room, 'no_response')` (una linea; toca la tarea de Celery).
4. **Reactivacion automatica al cerrar/reabrir**: hoy una sala cerrada + nueva sala arranca con la IA activa (correcto); no se propone reactivar automaticamente una sala abierta escalada (el plan pide explicitud).
