# AI_AGENTS_TOOLS_AUDIT.md — Auditoría FASE 5-8: AI Engine, Agentes, Tools, Prompt Base

> **Fecha:** 2026-08-07. Alcance: `ai_engine/action_graph.py` (Router/Intent/Agentes/Tools),
> `ai_engine/tools/support_tools.py`, pruebas en vivo contra `POST /chat` del contenedor
> `ecommerce_sintel_ai` (Ollama local real, sin mocks). Continúa
> [WS_AUDIT.md](WS_AUDIT.md) y [AI_BRIDGE_AUDIT.md](AI_BRIDGE_AUDIT.md).

## Resultado global

**El AI Engine está operativo** — `POST /chat` responde correctamente, con los 6 campos
esperados (`response`, `agent`, `intent`, `metrics`, `tool_calls`, `tool_results`) en el
100% de las 9 llamadas reales ejecutadas en esta fase. Se encontraron **2 bugs reales y
reproducibles**: uno **corregido y verificado en vivo** (BUG B — validación de argumentos
opcionales), otro **documentado, sin corregir** (BUG A — enrutamiento de intención de
compra). Ninguna llamada quedó sin respuesta (0/9 timeouts, 0/9 silencios).

## FASE 5 — AI Engine operativo (`POST /chat`)

| Verificación | Resultado |
|---|---|
| Health check (`GET /health`) | 200 OK, 16ms |
| `POST /chat` con `"Hola"` | 200 OK, 9.87s. Campos completos: `response`, `agent=SupportAgent`, `intent=unknown`, `metrics` (con `llm_calls`, `llm_tokens_in/out`, `duration_ms`, etc.), `tool_calls`, `tool_results`. |
| Autenticación | JWT real (`AccessToken.for_user`) validado correctamente por el motor — sin JWT válido no se pudo probar el fallo (fuera de alcance reproducir un 401 real sin tocar el gateway). |

**Hallazgo (P2, no corregido):** el saludo simple `"Hola"` tardó **9.87s** en la primera
llamada — muy por encima del criterio de FASE 15 ("saludo inicial en menos de 2 segundos").
Llamadas posteriores al mismo mensaje bajaron a ~9.5s de forma consistente (no fue solo
"cold start" del LLM). Causa observada: el agente ejecuta 2 llamadas al LLM (`llm_calls: 2`,
patrón consistente en las 9 pruebas) + 1 tool call (`buscar_pedido`) incluso para un saludo
sin intención clara — ver hallazgo relacionado en FASE 6 abajo. Con Ollama local (sin GPU
dedicada confirmada en este host), 2 round-trips de LLM + 1 tool call fácilmente superan 2s;
cumplir ese criterio requeriría either (a) un saludo de baja latencia sin tool-calling para
intents claramente conversacionales, o (b) infraestructura de inferencia más rápida — ambas
son decisiones de producto/infra, no correcciones de FASE 14.

## FASE 6 — Auditoría de Agentes (Router/Intent/Planner)

Se probaron los 7 mensajes del brief (más 2 reverificaciones tras el fix). Ningún caso
terminó "sin agente asignado" — el router SIEMPRE asigna un `agent` (nunca null/vacío) y
SIEMPRE produce una respuesta en lenguaje natural, incluso cuando la tool subyacente falla.
Esto confirma el principio del brief ("El agente siempre debe responder. Nunca quedarse en
silencio") — a nivel de respuesta HTTP se cumple 9/9.

**BUG A (P2, NO corregido — requiere decisión de producto, documentado):** el mensaje
`"Quiero comprar cámaras"` fue clasificado `intent=order_status`, enrutado a `OrderAgent`,
que ejecutó `buscar_pedido` (una búsqueda de PEDIDOS existentes, no de PRODUCTOS). El brief
esperaba explícitamente "Debe consultar Shop". La respuesta final ("no tengo información
sobre pedidos de compra relacionados con cámaras") es coherente con lo que el agente
ejecutó, pero no resuelve la intención real del usuario (buscar productos para comprar).

Causa: el router de intención no distingue "quiero comprar X" (búsqueda de catálogo,
`shop`/`ShopAgent` si existe) de "cuál es el estado de mi pedido" (`order_status`). Se
inspeccionó el mapeo de intents en `action_graph.py` (`INTENT_FALLBACK_CAPABILITY` y la
clasificación previa al bloque auditado) — corregir esto implica ajustar la lógica de
clasificación de intención o el prompt del router para reconocer verbos de intención de
compra ("quiero comprar", "necesito", "busco") como distintos de consulta de pedido
existente. **No se corrige en esta fase**: es un cambio de comportamiento del router/prompt
(FASE 8), con superficie de impacto más amplia que una validación puntual — amerita
revisión y aprobación explícita antes de tocar la clasificación de intents en producción,
a diferencia del BUG B (abajo), que es un fix de una función pura sin ambigüedad de
producto.

Casos que SÍ enrutaron correctamente (confirman que el router funciona bien en general):

| Mensaje | Intent | Agente | Tool ejecutada | ¿Correcto? |
|---|---|---|---|---|
| "Quiero alquilar un equipo" | `renting_search` | `RentalAgent` | `EquipmentSearchTool` | ✅ |
| "Necesito soporte tecnico" | `support` | `SupportAgent` | `OpenSupportTicketTool` | ✅ |
| "Quiero consultar mi pedido" | `order_status` | `OrderAgent` | `OrderStatusTool` | ✅ |

## FASE 7 — Auditoría de Tools

**BUG B (P1 — CORREGIDO Y VERIFICADO EN VIVO).** Causa raíz encontrada en
`ai_engine/action_graph.py`, en **dos** lugares con el mismo patrón defectuoso:

1. `_sanitize_args()` (línea ~289) — usada para Tools de **lectura**.
2. El bloque de validación inline para Tools de **escritura** (línea ~404, dentro del loop
   principal de ejecución de `tool_calls`).

Ambos construían el diccionario de argumentos "limpios" filtrando solo por presencia de la
clave en el schema (`if k in properties`), **sin excluir valores `None`**. Cuando el LLM
arma su `tool_call` incluyendo explícitamente un parámetro opcional con valor `null` (en vez
de omitir la clave — ambas formas son válidas y equivalentes según el `args_schema`, ya que
el parámetro no está en `required`), el valor `None` caía en el chequeo de formato
UUID/fecha (`_UUID_RE.match(str(None))` → `str(None) == "None"`, nunca matchea) y la llamada
se marcaba como inválida:

- **Tools de escritura** (ej. `OpenSupportTicketTool`/`abrir_ticket_soporte`): generaba un
  error 400 sintético *de cara al usuario* pidiendo datos (`order_uuid`, `rental_uuid`) que
  en realidad **nunca eran requeridos** (`args_schema.required = ["message"]` únicamente,
  confirmado en `ai_engine/tools/support_tools.py`). Reproducido en vivo con "Necesito
  ayuda" y "No estoy satisfecho con la respuesta" — ambos casos del brief de E2E (Casos 2 y
  6) fallaban exactamente por esto.
- **Tools de lectura**: la llamada se **descartaba en silencio** (`continue`, solo un
  `logger.info`, sin warning ni señal al usuario) y quedaba enmascarada por el fallback
  determinístico — un filtro que el usuario sí especificó podía perderse sin que nadie lo
  notara.

**Fix aplicado** (mínimo, sin tocar arquitectura/contratos/modelos/frontend): excluir
explícitamente `v is not None` en ambos filtros, tratando "parámetro opcional en null" igual
que "parámetro opcional omitido" — exactamente el comportamiento que la propia
implementación Python de la tool (`open_support_ticket_tool`, con `if order_uuid:`) ya
asumía. Un valor `None` en un campo **requerido** (`message`) sigue detectándose
correctamente como faltante (el chequeo de `required` es independiente y no se tocó).

**Verificación en vivo (antes/después del fix, mismo motor corriendo, sin mocks):**

| Caso | Antes | Después |
|---|---|---|
| "Necesito ayuda" | 400 sintético, pide `order_uuid`/`rental_uuid`, ningún ticket creado | 200, `write_executed=true`, ticket creado (`room_uuid` real), respuesta pregunta el problema |
| "No estoy satisfecho con la respuesta" | 400 sintético, mismo error, sin escalar | 200, `write_executed=true`, ticket creado, respuesta reconoce la insatisfacción y escala a la sala de soporte |

**Regresión verificada:** "Hola" (sin argumentos opcionales involucrados) se comportó
idéntico antes/después (mismo agente, misma tool, latencia equivalente) — el fix no afectó
el camino feliz existente.

**No se hizo en esta fase:** no existe un test unitario/automatizado para
`action_graph.py` en el repo (`ai_engine/` no tiene suite de tests propia, a diferencia de
`support/tests.py` del lado Django) — la verificación fue 100% en vivo contra el motor real.
Se recomienda, como seguimiento, agregar un test unitario para `_sanitize_args()` y el
bloque de validación de escritura con casos `{"campo_opcional": None}` — hoy cualquier
regresión futura de este bug pasaría desapercibida hasta reproducirse en producción.

**Advertencia operativa importante:** el fix se aplicó al archivo montado en
`ai_engine/action_graph.py` (fuente) **y** se copió manualmente al contenedor
`ecommerce_sintel_ai` (`/app/action_graph.py`) para que `uvicorn --reload` lo recogiera —
se confirmó que **`/app` dentro del contenedor es una copia estática del build de la
imagen, NO el bind mount de `/workspace`**, así que editar el archivo fuente por sí solo
NO alcanza el proceso corriendo en este entorno de desarrollo. Esto es en sí mismo un
hallazgo de FASE 12 (observabilidad/reproducibilidad): el flujo normal de desarrollo
(editar código, ver el cambio reflejado) está roto para `ai_engine` a menos que se sepa
copiar manualmente el archivo o reconstruir la imagen — documentado para que no se pierda,
sin corregirlo aquí (es de infraestructura de desarrollo, no del chat en sí). **El fix
está confirmado en el contenedor de desarrollo en ejecución; no se ha reconstruido la
imagen ni desplegado a producción** — requiere el flujo normal de build/deploy (o
autorización explícita) antes de considerarse persistente.

## FASE 8 — Prompt Base (evaluación indirecta)

No se auditó un archivo de "system prompt" único y aislado — el prompt se arma
dinámicamente dentro de `action_graph.py` (visto en el bloque alrededor de la línea 370,
con contexto optimizado inyectado: `state.get("optimized_context", "")`). No se encontró:

- Prompt vacío o no cargado: las 9 llamadas reales generaron respuestas coherentes en
  español, contextualizadas al negocio (Sintel, alquiler, pedidos) — el prompt claramente
  se está cargando y aplicando.
- Pérdida de contexto evidente dentro de una sola llamada (no se probó continuidad
  multi-turno con el mismo `conversation_id` más allá de 1-2 mensajes — fuera del alcance
  cubierto por las pruebas de esta fase).
- Herramientas deshabilitadas: las tools se ejecutaron correctamente en 6/9 casos donde
  aplicaba.

**Relacionado con BUG A (FASE 6):** la inconsistencia de enrutamiento para intención de
compra probablemente se resuelve mejor a nivel de prompt/clasificación de intents que a
nivel de código de validación — queda como recomendación para una fase de ajuste de
prompt/router explícita, no autoexecutada aquí por su ambigüedad de producto.

## Verificación

- `python -m py_compile action_graph.py` (dentro del contenedor `ecommerce_sintel_ai`): limpio.
- 9 llamadas reales a `POST /chat` (Ollama real, sin mocks): 9/9 con 200 OK y payload completo.
- Regresión confirmada: caso "Hola" idéntico antes/después del fix.
- **Pendiente:** persistir el fix más allá del contenedor de desarrollo en ejecución
  (rebuild de imagen / pipeline de deploy normal) — no se hizo en esta sesión, requiere
  decisión explícita de despliegue.

## Roadmap — estado actualizado

| Fase (brief 2026-08-07) | Estado |
|---|---|
| FASE 2-4 | Hechas — ver `WS_AUDIT.md` / `AI_BRIDGE_AUDIT.md`. |
| FASE 5 — AI Engine operativo | **Hecha.** `POST /chat` funcional, 9/9 respuestas completas. Hallazgo de latencia (~9.5s en saludo) documentado, no corregido (decisión de infra/producto). |
| FASE 6 — Agentes | **Hecha.** Router nunca deja sin agente. BUG A (routing de intención de compra) documentado, no corregido. |
| FASE 7 — Tools | **Hecha.** BUG B encontrado, corregido y verificado en vivo (2/2 casos de E2E que fallaban ahora pasan). |
| FASE 8 — Prompt Base | **Hecha (evaluación indirecta).** Sin prompt vacío/no cargado. Recomendación de ajuste de intents ligada a BUG A. |
| FASE 9-15 | Pendientes. |

---

## Actualización 2026-08-07 (tarde) — fix persistido + Nivel A de migración aplicado

- **Cerrado lo pendiente de esta misma tabla:** el fix de BUG B se persistió más allá del
  contenedor en ejecución — commit `ae400e9`, `docker compose build sintel_ai && docker
  compose up -d sintel_ai`, verificado de nuevo en vivo contra la imagen reconstruida.
- **Nivel A del plan de migración aplicado** (ver artifact "AI Engine — motores locales
  intercambiables, sin fijar ninguno" y `SUPPORT_CHAT_CERTIFICACION.md`): `LLM_PROVIDER`
  fue reemplazado por `LOCAL_MODEL_CHAIN` — el motor ya no depende de un único proveedor,
  soporta una cadena con fallback automático (`.with_fallbacks()`) hacia cualquier motor
  compatible con OpenAI (LM Studio, vLLM, DeepSeek, etc.), sin tocar `action_graph.py`.
  Commit `e5f07ef`, verificado en vivo (fallback forzado + `.bind_tools()` sobre la
  cadena), imagen reconstruida. Detalle técnico completo en
  `ai_engine/.AGENT/FLIJO_COMPLETO_IA_ENGINE.md` sección 3bis.
- El hallazgo de latencia (~9.5s en "Hola") sigue sin resolver — es del modelo/hardware,
  no del mecanismo de selección de proveedor, y no se ve afectado por este cambio.
