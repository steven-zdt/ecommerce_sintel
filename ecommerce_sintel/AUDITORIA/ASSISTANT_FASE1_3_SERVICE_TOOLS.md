# ASSISTANT_FASE1_3_SERVICE_TOOLS — Cierre de Fase 1-3 de PLAN_SINTEL_ADMIN_ASISTENTE_RAG_FORMULARIOS_LOOP.md

**Fecha:** 2026-09-23
**Alcance ejecutado (alcance elegido explícitamente por el usuario, no todo el plan):** Intent
Registry mínimo para `service.create`/`service.update` — cerrar el hallazgo real de
`ASSISTANT_BASELINE.md`: `CatalogAgent` no tenía Tools de Servicio y usaba su lógica de Producto
para interpretar "crear un servicio" (preguntaba marca/condición, campos que `TechnicalService` ni
siquiera tiene). **Fases 4+ del plan (Form Schema Registry, Draft Engine genérico, resolvers por
capas, `AdminAIDraft`/`AdminAISession`) quedan explícitamente fuera de esta entrega.**

## Qué se construyó

Mismo patrón exacto que la vertical Catálogo (Producto/Categoría/Marca/Impuesto) ya existente —
ninguna abstracción nueva, solo la misma receta aplicada a `TechnicalService`.

| Capa | Archivo | Contenido |
|---|---|---|
| Endpoints internos Django | `technical_services/api/internal_ai.py` | `AiServiceAdminListView`, `AiServiceAdminGetView`, `AiServiceAdminCreateDraftView`, `AiServiceAdminUpdateDraftView`, `AiServiceAdminCategoryListView` — todas bajo `services/admin/*` (prefijo separado de `services/`, ya ocupado por `AiServiceStatusView` preexistente, de cara al cliente) |
| URLs | `ecommerce/internal_ai_urls.py` | 5 rutas nuevas registradas |
| Tools del AI Core | `ai_engine/tools/technical_services_tools.py` (nuevo) | `ServiceListTool`, `ServiceGetTool`, `ServiceCategoryListTool` (lectura); `ServiceCreateDraftTool`, `ServiceUpdateDraftTool` (escritura, `risk="medium"`, `audit_level="full"`) |
| Registro de Tools | `ai_engine/tools/__init__.py` | import del módulo nuevo (dispara `@register_tool`) |
| Capabilities | `ai_engine/capabilities/registry.py` | 5 capabilities nuevas (`listar_servicios`, `ver_servicio`, `listar_categorias_servicio`, `crear_borrador_servicio`, `editar_borrador_servicio`), `apps=["technical_services"]` |
| Routing de intención | `ai_engine/routing.py` | intent `service_admin` (regex de verbos de gestión + "servicio"), insertado **antes** de `service_status` (intent de cliente preexistente, dispara con la palabra suelta "servicio") para que un mensaje admin nunca caiga en el intent de cliente por orden de diccionario — mismo criterio que ya se usó para `catalog_admin` vs. `renting_search` |
| Perfil del agente | `ai_engine/agents/profiles/catalog_agent.yaml` | v1→v2: 5 Tools nuevas en `herramientas`, 5 capacidades nuevas, `service_admin` agregado a `intents`, `personalidad`/`tono` actualizados para prohibir explícitamente preguntar marca/condición al crear/editar un servicio |

Regla dura heredada de Producto (Decision 1 del piloto de Catálogo): `ServiceCreateDraftTool`
**siempre** crea con `is_active=False`, forzado del lado de Django
(`AiServiceAdminCreateDraftView`), nunca confiado al LLM. Publicar/despublicar queda para una Tool
de Nivel 3 (HITL) no construida en esta fase — mismo criterio ya aplicado a Product/Category/Brand.

## Bug real encontrado y corregido durante la verificación (no en el plan original)

El primer smoke test end-to-end (tarea en background `bd82x34ms`, mensaje real: *"crear servicio de
automatizacion de tiendas locales por 1500000 pesos"* — frase de aceptación tomada literal del
plan) confirmó que el bug de marca/condición SÍ estaba resuelto (el agente fue directo a
`ServiceCategoryListTool`, resolvió la categoría real "Optimización de Software", y su propia
respuesta declaró *"Servicios técnicos NO tienen campos de marca ni condición"*), pero reveló un
bug nuevo: el LLM mandaba `price` como objeto
(`{"amount":1500000,"currency":"COP","pricing_strategy":"FIXED"}`) en vez de número plano.
`Decimal(price)` del lado de Django lanzaba `TypeError`/`ValidationError` sin capturar → 500 crudo.
El agente reintentó 5 veces variando el formato (sin éxito, siempre el mismo 500) hasta agotar el
límite de acciones del turno de Google ADK (429).

**Fix:** `_parse_price(raw)` en `technical_services/api/internal_ai.py` — extrae
`amount`/`price`/`value` si recibe un dict, intenta `Decimal(str(raw))`, nunca lanza (retorna
`None` en cualquier falla, tratado como entrada inválida con 400 claro en vez de 500). Aplicado en
`AiServiceAdminCreateDraftView` **y** `AiServiceAdminUpdateDraftView` (esta última tenía el mismo
patrón sin proteger, detectado por inspección al corregir la primera — nunca se disparó en el
smoke test porque el flujo de creación fallaba antes de llegar a edición).

## Verificación real (no solo lectura de código)

- **Reintento del mismo smoke test tras el fix**: mismo patrón de `price` como dict del lado del
  LLM (no cambió el prompt del agente, solo el fix del lado servidor) → creó el servicio en **un
  solo tool call** (antes: 5 fallos + 429 sin crear nada). Verificado directo en base de datos:
  `is_active=False`, `category="Optimización de Software"`, `default_variant.fixed_price=1500000.00`,
  `pricing_strategy=FIXED`.
- **`python manage.py check`**: limpio (1 warning preexistente no relacionado, `cart.Cart.user`).
- **`python manage.py test technical_services`**: **203 tests, OK** (los `WARNING django.request`
  visibles en el log son asserts de rutas negativas 401/403/400 del propio suite, no fallas).
- **Arranque de `AgentRegistry`**: confirmado indirectamente — el smoke test corrió contra el
  runtime ADK real, que valida fail-loud todo Tool declarado en cada perfil `.yaml` al boot; si
  alguna de las 5 Tools nuevas o su capability no existiera, el contenedor habría crasheado al
  levantar en vez de responder 200.
- **Limpieza**: el servicio de prueba (`uuid=6a75024b-...`) y el usuario de prueba
  (`ai-service-smoke@example.com`) creados durante la verificación fueron eliminados. Se confirmó
  que los 5 intentos fallidos del smoke test original (todos con 500) no dejaron `TechnicalService`
  huérfano en base de datos — Django no comitea nada si `Decimal()` lanza antes del `save()`.

## Qué NO se construyó (explícitamente fuera de alcance)

Mismos ítems que `ASSISTANT_BASELINE.md` marcó como inexistentes y que esta entrega no toca:
`AdminAIDraft`/`AdminAISession` (persistencia de borrador entre turnos — ADK sigue en
`InMemorySessionService`, efímero), Form Schema Registry, Draft Engine genérico
(patch/validate/merge/submit), resolvers por capas (hoy sigue siendo un solo nivel: `search` de
texto simple contra BD, sin normalización ni fallback semántico), UI de formulario sincronizado en
`/panel/asistente` (sigue siendo solo chat). Publicar/despublicar un servicio tampoco quedó
resuelto — mismo criterio que Producto: Nivel 3, HITL, pendiente.

## Conclusión

**GATE: PASS** para declarar Fase 1-3 completa dentro del alcance elegido. El hallazgo original del
plan (CatalogAgent sin vocabulario de Servicio, preguntando campos de Producto) está resuelto y
verificado con evidencia real de extremo a extremo (chat → intent → Tool → Django → base de datos),
no solo por inspección de código. El bug de `price` como dict era un riesgo real de producción no
anticipado por el plan — quedó cerrado con defensa en ambas vistas de escritura (create y update),
no solo en la que lo disparó primero.

Las Fases 4+ representan trabajo de ingeniería genuinamente nuevo (mismo diagnóstico que
`ASSISTANT_BASELINE.md` ya hizo para el plan completo) y no se iniciaron en esta entrega.
