# ASSISTANT_BASELINE — Fase 0 de PLAN_SINTEL_ADMIN_ASISTENTE_RAG_FORMULARIOS_LOOP.md

**Fecha:** 2026-09-23
**Método:** lectura directa de código real (no se asumió nada del plan). Baseline enfocado en los
hechos que determinan el alcance real de las Fases 1+ — no es una relectura línea por línea de los
20 ítems listados en la Fase 0 del plan (dado el tamaño del plan, ver nota al final).

## Estado real vs. lo que el plan asume

| Componente que el plan asume/pide | Estado real |
|---|---|
| `/panel/asistente` | Existe, **solo chat**: `AiAssistantView.vue` es un input de texto + burbujas de conversación + un `<pre>` que vuelca `tool_results` como JSON crudo. **No hay panel de formulario**, no hay UI de propuesta/aprobación estructurada. |
| Identidad "SINTEL ADMIN IA" fija por superficie | **Recién resuelto hoy** (sesión de trabajo sobre el plan anterior, `PLAN_SINTEL_ADMIN_AI_ADK_PANEL_LOOP.md`): `ChatRequest.source="admin"` fuerza `resolve_turn_agent()` a devolver siempre `CatalogAgent`, nunca un agente de cliente. **No existe** un identificador canónico `sintel_admin` — el "agente admin fijo" hoy es literalmente `CatalogAgent` (único agente admin que existe). Si el plan quiere un nombre canónico distinto, es un rename/alias, no lógica nueva. |
| `AdminAIDraft` / `AdminAISession` (Fase 2/5 del plan) | **No existe.** Cero resultados en todo el repo. |
| Form Schema Registry (Fase 4) | **No existe.** Ningún mecanismo de "entregar un schema de formulario dinámico al frontend" en ningún dominio del proyecto (no es exclusivo de IA — no hay un patrón previo que reutilizar). |
| Draft Engine (patch/validate/merge/submit) | **No existe.** |
| Resolvers por capas (exact→normalized→database→semantic→LLM) (Fase 7) | **No existe tal cual.** Lo que hay: Tools de `list` con un parámetro `search` de texto simple (`catalog_category_list_tool(search=...)`) — un solo nivel (substring match en BD), sin normalización ni fallback semántico. La resolución "inteligente" de categorías (sección 16 del plan) NO está implementada — hoy el LLM decide qué hacer con el resultado de `list`, no hay una función Python dedicada. |
| Persistencia de sesión/borrador entre turnos | ADK usa `InMemorySessionService` — **estado en memoria de proceso, se pierde en cada restart del contenedor**, aislado por instancia (`InMemoryRunner crea su propio InMemorySessionService AISLADO`). Un `AdminAIDraft` real (Fase 14 del plan: `expires_at`, estados COLLECTING/AWAITING_APPROVAL/etc.) necesita un modelo Django persistente — no se puede construir solo sobre el session state de ADK. |
| Tool Registry catálogo (19 Tools) | Existe y funciona (verificado en vivo hoy: create/update/list/publish de Product/Category/Brand/Tax). Reutilizable tal cual para Fase 11 del plan nuevo. |
| Contrato JSON `intent`/`domain`/`entity`/`status` (Fase 4-5 del plan) | No existe como contrato formal — hoy el "contrato" real es el par `(intent: str, agent_name: str)` que devuelve `resolve_turn_agent()`, mucho más simple que lo que pide el plan. |

## Conclusión de la Fase 0

**Ningún componente de las Fases 2-16 del plan existe todavía.** A diferencia del plan anterior
(`PLAN_SINTEL_ADMIN_AI_ADK_PANEL_LOOP.md`), que tenía un piloto real ya construido y solo congelado,
este plan es trabajo genuinamente nuevo de principio a fin: un modelo de datos nuevo (`AdminAIDraft`),
un registro de formularios nuevo, un motor de resolución nuevo, y una UI de chat+formulario
sincronizado nueva — cada uno es una pieza de ingeniería real, no una activación de flag.

Lo único que el plan asume que ya está resuelto y **realmente lo está**: identidad fija de agente por
superficie (Fase 1) y el Tool Registry de catálogo (parte de Fase 11).

**GATE: PASS** para declarar la Fase 0 completa (auditoría honesta, sin inventar componentes) — pero
el hallazgo real es que las Fases 2+ representan varias semanas de trabajo, no una tarde.

## Nota sobre el alcance de esta auditoría

El plan pide auditar 20 ítems (router Vue completo, stores, todos los API clients, RAG, Knowledge
Graph, Policy Layer, AdminOrchestrators completos, etc.). Esta pasada se enfocó en los ítems que
determinan si hay algo que reutilizar para las Fases 2-7 (lo estructuralmente nuevo) — no se releyó
línea por línea cada Command/Selector/Orchestrator del panel completo (esos ya están mapeados con
detalle en `ai_engine/.AGENT/ADMIN_AI_ASSISTANT_FASE0_MATRIZ.md`, la auditoría de la misión anterior,
todavía vigente).
