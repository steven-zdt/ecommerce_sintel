# AI_BRIDGE_AUDIT.md — Auditoría FASE 4: AI Bridge

> **Fecha:** 2026-08-07. Alcance: `support/services/ai_bridge.py`. Continúa
> [WS_AUDIT.md](WS_AUDIT.md) (FASE 2-3) y la serie previa, en particular
> [18](18_AUDITORIA_PRODUCCION_RESILIENCIA_WS.md) (hallazgo B2, aquí retomado).

## Resultado global

**La petición al AI Engine realmente se envía** — confirmado por lectura del código (no
había ninguna duda razonable: `requests.post()` real, sin mocks ni feature-flags que lo
desvíen en producción) y por los 27 tests de `support/tests.py` que mockean exactamente
este punto (`support.services.ai_bridge.requests.post`) para simular ambos casos (motor
disponible / inalcanzable). Se agregó logging estructurado REQUEST/RESPONSE/LATENCY/
TOKENS/ERROR directamente en `ask_ai()` — el único punto de contacto real con el AI
Engine, compartido por el widget web (WS) **y** WhatsApp (`notifications/tasks.py`), así
que instrumentarlo aquí cubre ambos canales con una sola traza en vez de duplicarla en
cada llamador.

## Checklist FASE 4

| Ítem | Estado | Evidencia |
|---|---|---|
| `AI_ENGINE_URL` | ✅ | `ecommerce/settings/base.py`: `config('AI_ENGINE_URL', default='http://sintel_ai:8100')`. Confirmado en dev vía shell: `http://sintel_ai:8100`. Docstring del módulo es explícito: `sintel_ai` nunca se expone a Internet, solo Django le habla. |
| Timeout | ✅ | `AI_CHAT_TIMEOUT_SECONDS = 300` — deliberadamente alto ("LLM local puede tardar mas de un minuto"), no un olvido. Ver riesgo asociado (B2) más abajo. |
| `POST /chat` | ✅ | `requests.post(f"{settings.AI_ENGINE_URL}/chat", json={'message', 'conversation_id'}, ...)`. |
| Headers | ✅ | `Authorization: Bearer <token>`. |
| JWT | ✅ | `AccessToken.for_user(user)` — se acuña un token efímero del usuario real en cada llamada, nunca se persiste ni se reutiliza entre turnos (regla dura documentada en el docstring del módulo). |
| JSON | ✅ | Body `{'message': message, 'conversation_id': conversation_id}`; respuesta parseada con `resp.json()`. |
| Retries | ❌ No implementado | Cero reintentos ante `requests.RequestException` o `status_code != 200` — un solo intento, y ante fallo se degrada directo (`return None`). **No se corrige en esta fase** (ver "Decisión de diseño" abajo) — no es un bug, es una ausencia consciente que vale documentar. |
| Rate Limit | ✅ | `is_ai_rate_limited(room)` — ventana fija de `AI_CHAT_RATE_LIMIT=20` turnos / `AI_CHAT_RATE_WINDOW_SECONDS=600` por sala, con `cache.add` atómico (evita race condition). Se evalúa en `consumers.py` ANTES de llamar `ask_ai()`, no dentro de `ai_bridge.py` — separación correcta (rate-limit es una decisión del canal, no del bridge). |
| Fallback | ✅ | `ask_ai()` devuelve `None` ante cualquier falla (excepción de red, status≠200, o — visto desde el consumer — respuesta vacía). El canal (WS) ya lo maneja: `_save_ai_degraded_marker()` persiste un mensaje de degradación visible para el cliente, nunca deja el chat mudo. |
| Human Handoff | ✅ | `ai_response_opened_ticket(ai_response)` inspecciona `tool_results` buscando `abrir_ticket_soporte` exitoso — usado por el consumer para pausar la IA en la sala (`room.ai_paused=True`). Vive correctamente en `ai_bridge.py` (interpreta la respuesta del Engine), no en el consumer. |

## Trazas agregadas (FASE 4)

`ask_ai()` ahora loguea, sin excepción, en los 3 desenlaces posibles:

- **Antes de la llamada:** `[AI_BRIDGE] request conversation_id=... user=...`
- **Éxito (200):** `[AI_BRIDGE] response ok conversation_id=... latency_ms=N tokens=... tools=N agent=...`
- **Motor inalcanzable (excepción de red):** `[AI_BRIDGE] AI Engine inalcanzable conversation_id=... latency_ms=N error=<Tipo>: <detalle>`
- **Respuesta no-200:** `[AI_BRIDGE] response status=N conversation_id=... latency_ms=N body=<primeros 200 chars>`

Ninguna de estas líneas incluye el texto del mensaje del usuario ni de la respuesta del
modelo (eso ya se cubre, opcionalmente, por `SUPPORT_DEBUG_MODE` del lado del consumer —
ver `WS_AUDIT.md`). `conversation_id` tiene forma `room-<uuid>` (WS) o `wa-<user_id>`
(WhatsApp), suficiente para correlacionar sin exponer contenido.

## Hallazgo retomado: B2 (doc 18) — ahora activo, no latente

`ask_ai()` es una llamada **síncrona** (`requests.post`, bloqueante) invocada dentro de
`@database_sync_to_async` (`consumers.py::_ask_ai`). En el proceso ASGI puro de este
proyecto (un solo Daphne, sin envoltura WSGI), `database_sync_to_async` reutiliza el mismo
threadpool que absorbe TODO el `sync_to_async`/ORM del proceso — una llamada de IA lenta
(hasta 300s de timeout) puede estancar peticiones HTTP normales completamente ajenas al
chat mientras el thread está ocupado.

Doc 18 (2026-08-01/04) marcó esto como **latente** porque `AI_SUPPORT_CHAT_ENABLED=False`
en producción en ese momento. **Verificado hoy: `AI_SUPPORT_CHAT_ENABLED=True` en el
entorno de desarrollo** — no se pudo confirmar el valor en producción en esta sesión (el
clasificador de auto-modo bloqueó el `docker exec` de solo lectura contra
`sintel_prod_django`; requiere que el usuario lo autorice explícitamente o lo verifique
él mismo). Dado el riesgo, **este hallazgo debe tratarse como potencialmente activo hasta
confirmar el valor real en producción**, no como cerrado.

**No se corrige en esta fase** — es un cambio de arquitectura real (mover a un cliente
HTTP async como `httpx.AsyncClient` dentro de una corutina nativa, o aislar estas llamadas
en un pool de threads dedicado separado del pool compartido de `database_sync_to_async`),
fuera del alcance de "corregir errores reales sin tocar arquitectura" de FASE 14. Se deja
documentado con la severidad que corresponde para una decisión explícita del usuario.

## Decisión de diseño: por qué NO se agregan reintentos aquí

Se evaluó agregar reintentos ante fallo de `ask_ai()` y se decidió **no hacerlo** en esta
fase, por una razón concreta ligada a B2: cada intento adicional puede sumar hasta 300s
más bloqueando el mismo thread compartido — un retry ingenuo empeoraría el problema más
severo de esta misma fase en vez de mejorar la resiliencia. Agregar reintentos con
criterio (ej. solo ante error de red, con backoff, y solo después de resolver B2) es una
recomendación para una fase posterior, no una corrección de bajo riesgo aplicable hoy.

## Verificación

- `python -m py_compile support/services/ai_bridge.py`: limpio.
- `manage.py check`: limpio (mismo warning preexistente no relacionado).
- `pytest support/tests.py`: 27/27 passing tras el cambio (ver `WS_AUDIT.md` para el primer
  run; re-ejecutado tras esta fase para confirmar que el nuevo logging en `ask_ai()` no
  rompe los mocks existentes de `requests.post`).

## Roadmap — estado actualizado

| Fase (brief 2026-08-07) | Estado |
|---|---|
| FASE 2-3 | Hechas — ver `WS_AUDIT.md`. |
| FASE 4 — Auditoría AI Bridge | **Hecha.** Checklist 9/9, trazas REQUEST/RESPONSE/LATENCY/TOKENS/ERROR agregadas, B2 re-evaluado (activo en dev, pendiente confirmar en prod), decisión documentada de no agregar retries todavía. |
| FASE 5-15 | Pendientes. |
