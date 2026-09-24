# TOOL_SECURITY — seguridad de las tools del agente

> Documento vivo (HARDENING F19, 2026-09-24). Código: `ai_engine/tools/{classification,arg_validation,registry,metadata}.py`, `ai_engine_adk/{sintel_adapter,idempotency,result_limits}.py`.

## 1. Niveles (F4) — `tools/classification.py::TOOL_LEVELS`
| Nivel | Significado | Ejemplos | Confirmación humana |
|---|---|---|---|
| 0 | Lectura | búsquedas, consultas | no |
| 1 | Escritura local reversible (borradores, alta de ticket) | `OpenSupportTicketTool`, `Catalog*CreateDraftTool` | no |
| 2 | Modifica datos publicados/estado/contenido/identidad | `Catalog*UpdateTool`, `SetPublishedState`, `Core*`, `StartQuotationTool` | **sí (invariante)** |
| 3 | Efecto sobre operaciones reales de un cliente | `CreateRentalRequestTool`, `CancelRentalTool` | **sí** |
| 4 | Destructivo/financiero/seguridad | **ninguna** (el agente no borra ni mueve dinero) | — |
Una escritura nueva sin entrada explícita recibe nivel 2 (conservador). Los 4 `*Update*` de catálogo/servicios tienen confirmación forzada (`FORCE_CONFIRMATION`, decisión del usuario 2026-09-24). Toda escritura es idempotente y tiene rate limit (10/h alto riesgo, 30/h el resto) si no declara uno.

## 2. Orden de la Policy Layer (wrapper `adapt_sintel_tool`)
1. `deny_after_max_tool_calls_per_turn` (6 por turno). 2. `validate_tool_args_before`: schema (campos desconocidos, requeridos, tipos, rangos, longitud, UUID) — **monitor** (`AI_TOOL_STRICT_ARGS=false`: solo `ai_tool_args_invalid`); `true` rechaza con 400.
3. Permiso: `IsAdminUser` contra la identidad real (`permissions.user_lacks_admin_permission`); vacío nunca autoriza a un admin-tool.
4. Idempotencia (Redis): clave = sesión+usuario+tool+args; repetición -> replay; en curso -> 409. **Redis caído: fail-open** por defecto; `AI_TOOL_IDEMPOTENCY_FAIL_CLOSED=true` rechaza la escritura con 503 + handoff.
5. Rate limit por tool y usuario (Redis, fail-open).
6. Llamada real vía `http_bridge` a Django (8–10 s, error como dict, sin reintentos); Django es la autoridad final (permisos/reglas de negocio).
7. Salida: saneo Unicode + detección de inyección (monitor) + **tope de tamaño** (`AI_TOOL_MAX_RESULT_CHARS`, monitor: `tool_result_truncated`; enforce recorta la lista más larga con marcador `_truncated`).
8. Auditoría: `ai_tool_audit` por invocación (invocation_id, sesión, usuario, agente, tool, nivel, authz, confirmación, status, latencia, replay; **sin argumentos ni contenido**).

## 3. Confirmación humana
Las tools que la exigen devuelven `needs_confirmation`; el turno de confirmación (`confirm=true`) ejecuta lo pendiente. **Riesgo conocido**: `_PENDING_CONFIRMATIONS` vive en memoria del proceso -> un reinicio del ADK la pierde (seguro: no ejecuta, pero el usuario repite la petición) y no escala a varios workers (F14).

## 4. Reglas para agregar/cambiar una tool
1. Declarar `ToolMetadata` (`side_effects`, `risk`, `permissions`, `args_schema` estricto, `timeout_ms`, `version`). 2. Clasificar en `TOOL_LEVELS` a propósito. 3. Admin-only => `IsAdminUser`. 4. Sin borrado/pago/nivel 4 sin aprobación arquitectónica explícita. 5. Actualizar `EVALUATION_BASELINE.md`/golden dataset (categorías E, F, G) y `tests/security/test_tool_escalation.py`. 6. Re-correr F10 (cambio de tool = benchmark obligatorio).

## 5. Riesgos residuales
Args en modo monitor; rate limits e idempotencia fail-open sin Redis; `Catalog*` como 24 tools = 75 % del contexto de 4096 (F12); routing de admin hacia `MarketingAgent` solo con `marketing_admin`; mensajes con «campaña» derivan a `SupportAgent` por regla de escalamiento del perfil.
