# HARDENING — FASE 4 (hardening de Tools y agentes)

**Estado: C1-C5 APROBADOS (2026-09-24, con C6 = confirmacion en los `*Update*`), IMPLEMENTADOS Y VERIFICADOS EN DEV; PRODUCCION SIN DESPLEGAR.** Ver "Resultado en DEV" al final.

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §8. Nada implementado. Toca permisos/politicas de Tools
=> `SECURITY_REVIEW_REQUIRED` + aprobacion humana (§0.3, §26.2).

## Inventario real (introspeccion del registro en la imagen `ecommerce_sintel_ai_adk`, 2026-09-24)
57 Tools registradas (`ai_engine/tools/registry.py::_TOOLS`), 10 perfiles de agente.

| Metrica | Valor |
|---|---|
| Riesgo declarado | low 35 / medium 11 / high 11 |
| Con efectos secundarios (`side_effects=True`) | 23 (34 de solo lectura) |
| Requieren confirmacion humana | 14 |
| Escritura con `audit_level=full` y `permissions` declarados | 23/23 (OK) |
| Tools de borrado (`delete`/`remove`) | 0 (OK: cumple "no dar delete al agente") |
| Schema de argumentos presente | 57/57, pero `additionalProperties` sin declarar en 57/57 |
| Timeouts | 8 s (mayoria) y 12 s |
| **Escritura sin rate limit propio** | **18 de 23** |
| **Escritura sin confirmacion** | 9: `CatalogBrand/Category/Product CreateDraft/Update*`, `ServiceCreateDraft/UpdateDraft`, `OpenSupportTicketTool` |
| **Idempotencia** | **0 Tools** con `idempotency_key` (grep en `ai_engine/tools` y `sintel_adapter.py`) |

Escritura por agente: `CatalogAgent` 13 (admin), `AdminAgent` 5 (banners/navbar/slider, todas `risk=high` con confirmacion), `RentalAgent` 2
(`CreateRentalRequestTool` medium, `CancelRentalTool` high con confirmacion), `SalesAgent` 1 (`StartQuotationTool`), `SupportAgent` 1
(`OpenSupportTicketTool`, low), `AccountAgent` 1 (`RequestKycUpgradeTool`). Los agentes de cliente tienen 0-2 escrituras; el peso esta en admin.

Sin rate limit propio (solo aplican el tope de 6 tool calls/turno y 200 turnos/dia/usuario), 18 Tools: 5 de `Core*` (banners/navbar/slider), 2 de `CatalogTax*`
(Create, Update), 3 `Catalog*SetPublishedState` (marca/categoria/producto), 6 `Catalog{Brand,Category,Product}{Create,Update}` y 2 `Service{Create,Update}Draft`.

## Lo que YA cumple el plan (no tocar)
Gate `IsAdminUser` en la Policy Layer, `require_confirmation` de ADK en high-risk, `source=admin|customer`, auditoria completa de escrituras, sin Tools
de borrado, `before_tool_callback` con tope por turno, `on_tool_error_callback` con degradacion por Tool (`sintel_adapter.py`).

## Gaps y cambios propuestos

### C1 — Clasificacion formal + invariantes de registro (riesgo bajo)
Agregar a `ToolMetadata` (con defaults compatibles): `level: int` (0 lectura, 1 escritura local no destructiva/borrador, 2 escritura de consecuencia,
3 efecto externo, 4 destructivo/financiero/seguridad), `idempotent: bool`, `resource_scope: str`. Mapeo propuesto: lecturas=0; `*CreateDraft`/`*UpdateDraft`
(`is_active=False`)=1; `SetPublishedState`, `CatalogTax*`, `Core*`=2; `CancelRentalTool`, `CreateRentalRequestTool`=3; nada en 4 (correcto: el agente no
borra ni mueve dinero). Un test de invariantes recorre el registro y falla si: una escritura no tiene `rate_limit`/`audit_level=full`/`permissions`;
`level>=2` sin `requires_confirmation`; una lectura declara efectos; falta `level`.

### C2 — Validacion estricta de argumentos (riesgo medio)
- `additionalProperties: false` en los 57 schemas y rechazo explicito de campos desconocidos en el wrapper (`adapt_sintel_tool`), con error uniforme.
- Validacion central por schema antes de invocar la Tool: tipos, `format: uuid` (regex), `enum`, `minimum/maximum` (precios, cantidades), largo maximo de textos.
  Requiere completar los schemas hoy incompletos. Sin `eval`/`exec`/`subprocess`/SQL: verificar con un escaner AST en test (hoy no comprobado).
- Errores 4xx de Django ya se traducen; se agrega el mismo formato para errores de validacion locales.

### C3 — Idempotencia server-side (riesgo medio)
Deduplicacion en el adapter, no dependiente del LLM: clave `ai:idem:{session_id}:{tool}:{sha256(args normalizados)}` en Redis con TTL 10 min; una escritura
identica dentro de la ventana devuelve el resultado anterior en vez de re-ejecutar (cubre reintento del modelo, doble envio, timeout seguido de reintento).
Las escrituras con confirmacion ya tienen barrera humana; esto protege sobre todo las 9 sin confirmacion. Fail-open documentado si Redis cae (igual que
`rate_limit.py`). Como mejora posterior: enviar `Idempotency-Key` a los endpoints de Django que lo soporten (no verificado cuales).

### C4 — Rate limits para las 18 escrituras sin limite (riesgo bajo)
Propuesta inicial en `ToolMetadata.rate_limit` (formato existente `n/hour/user`): borradores y updates de catalogo/servicios `30/hour/user`;
`SetPublishedState`, `CatalogTax*`, `Core*` (high) `10/hour/user`. Calibrar con uso real de los admins.

### C5 — Contrato de auditoria estructurada por Tool (riesgo bajo)
Un unico evento `ai_tool_audit` con: request_id, session_id, user_id, agent, tool, level, resultado de autorizacion, resultado de confirmacion, estado,
latencia, clase de error, timestamp. Sin argumentos con PII ni secretos (solo claves de campos y `resource` id). Verificar primero que `audit_level=full`
ya cubre esto (no auditado a fondo en esta pasada).

### C6 — Decisiones pendientes de negocio
- ¿Las 9 escrituras sin confirmacion siguen asi? Son borradores/tickets (`is_active=False` o alta de ticket); mi recomendacion: mantener sin
  confirmacion los borradores (bajo riesgo, reversibles) y agregar confirmacion a los `*Update*` que modifican precio/estado de algo ya publicado.
- `CreateRentalRequestTool` (level 3) NO figura entre las 9 escrituras sin confirmacion, por lo tanto ya la exige: sin cambio.

## Tests
Invariantes del registro (C1), campo desconocido rechazado, UUID malformado, precio fuera de rango, replay idempotente devuelve el mismo resultado,
rate limit alcanzado, escaner AST sin `eval/exec/subprocess`, auditoria sin secretos. Regresion: mismos 31 fallos preexistentes de la suite del ADK.

## Riesgos / rollback
C2 puede rechazar llamadas que hoy "funcionan" por permisividad (p. ej. campos extra que el LLM inventa): activar primero en modo monitor (log) y luego
estricto, con un flag `AI_TOOL_STRICT_ARGS`. C3: una clave demasiado amplia podria bloquear una repeticion legitima: incluir `session_id` y args completos en el hash.
Rollback: flags a `false` / imagen anterior de `sintel_ai_adk`. Todo cambio solo en DEV primero.

## Preguntas para aprobar
1. ¿Apruebas C1-C5 (dev primero)? ¿Con `AI_TOOL_STRICT_ARGS` en monitor antes de estricto?
2. C6: ¿confirmacion para los `*Update*` de catalogo/servicios que tocan datos ya publicados?
3. ¿Limites iniciales de C4 (30/h borradores, 10/h high) o prefieres otros?

## Resultado en DEV (2026-09-24)
Decisiones del usuario: C1-C5 aprobados; confirmacion humana para los `*Update*` de marca/categoria/producto/servicio (C6); limites 30/h (escrituras)
y 10/h (riesgo alto); `AI_TOOL_STRICT_ARGS` primero en modo monitor.
Implementado:
- `ai_engine/tools/classification.py`: `TOOL_LEVELS` (23 escrituras: nivel 1 borradores/ticket, 2 actualizaciones/publicacion/impuestos/contenido/KYC/cotizacion,
  3 reservas de renting; ninguna en nivel 4), `FORCE_CONFIRMATION` (4 Update), limites por riesgo y `apply_policy()` invocado desde `registry.register_tool`.
  `ToolMetadata` gana `level`, `idempotent`, `resource_scope`. Toda escritura nueva sin clasificar => el test de invariantes falla.
- `ai_engine/tools/arg_validation.py` + `sintel_adapter.validate_tool_args_before` (before_tool_callback encadenado con el tope por turno):
  campos desconocidos, requeridos, tipo, UUID, enum, rangos, largos; errores sin valores. Flag `AI_TOOL_STRICT_ARGS` (default false = monitor).
  Hallazgo: el ADK descarta en silencio los campos ajenos a la firma; por eso el rechazo vive en el callback (que recibe los args crudos), no en el wrapper.
- `ai_engine_adk/idempotency.py` (Redis, TTL 600 s): escritura identica => resultado anterior marcado `idempotent_replay`; en curso => 409; los errores no se
  cachean; Redis caido => fail-open. La comprobacion ocurre ANTES del rate limit (una repeticion no consume cupo) y libera la clave si el rate limit la corta.
- Auditoria: un evento `ai_tool_audit` por ejecucion (invocation_id, session_id, user_id, agent, tool, level, authz, confirmation, status, status_code,
  latency_ms, error_class, replay), sin argumentos.
Tests: `ai_engine_adk/tests/test_tool_hardening.py` (31, incluye invariantes del registro y escaner AST sin eval/exec/subprocess). Regresion:
suite del ADK 31 fallos identicos a la linea base (preexistentes) y 55 -> 114 aprobados; suite del runtime antiguo `ai_engine/tests` identica con y sin cambios
(4 fallos preexistentes, 164 aprobados, 16 omitidos).
E2E real en DEV (contenedor con la imagen F4, Redis y Django REALES de dev, JWT de un admin, sin LLM): `CatalogCategoryCreateDraftTool` dos veces con los mismos
argumentos => 1 sola fila en BD (borrador `is_active=False`), 2a llamada = replay con el mismo uuid; auditoria `status=ok` y `status=replayed`;
callback en monitor deja pasar y en estricto devuelve 400 con `['campo desconocido: hack', 'uuid: UUID malformado']`. Datos de prueba borrados.
No verificado: turno de chat real con LLM que dispare una escritura y su confirmacion; efecto de la nueva confirmacion en la UI de `/panel/asistente`
(los `*Update*` ahora devuelven `needs_confirmation`); modo estricto con trafico real (primero observar `ai_tool_args_invalid` en monitor).

## Pasos pendientes para PRODUCCION (no ejecutados)
1. Rebuild `--no-cache` de `sintel_ai_adk` (+ `up -d --no-deps`); las variables tienen defaults, no requieren `.env.production` (idempotencia activa, estricto apagado).
2. Observar `security_event=ai_tool_args_invalid` en monitor durante un periodo real y solo despues `AI_TOOL_STRICT_ARGS=true`.
3. Avisar a los admins: los `*Update*` piden confirmacion. Rollback: `AI_TOOL_IDEMPOTENCY_ENABLED=false` / `AI_TOOL_STRICT_ARGS=false` / imagen anterior.
