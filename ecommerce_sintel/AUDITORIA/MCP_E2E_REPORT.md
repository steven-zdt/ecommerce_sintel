# MCP E2E Report (2026-09-25) - solo DESARROLLO

Entorno: Django dev + Postgres dev + MCP dev (`sintel_ecommerce_mcp`, perfil `mcp`), cliente MCP real (SDK oficial 2.2.0) dentro de la red de compose. Datos de prueba en la BD de dev: categorias "MCP Smoke ..." (creadas y borradas
logicamente) y una categoria de un ciclo previo "MCP Prueba Categoria 2" (borrada logicamente). Comando: `mcp_server/scripts/protocol_smoke.py` con `PHASE=readonly|ratelimit|write`.

## Resultado: 83 comprobaciones OK, 0 fallos (readonly 54, ratelimit 1, write 28)

## Protocolo MCP (sec. 44)
initialize (con y sin token), tools/list (12 Tools, ninguna peligrosa), resources/list (7), prompts/list (6), tools/call (lecturas, previews, escrituras, errores), resources/read (architecture, business-rules, environment-status), prompts/get.

## E2E CRUD (sec. 39) - sobre `categories` (dev)
list -> preview_create (no escribe) -> create sin ficha (`CONFIRMATION_REQUIRED`) -> create con ficha de OTRO payload (`CONFIRMATION_INVALID`) -> create con preview + `idempotency_key` (OK) -> ficha reutilizada (`CONFIRMATION_INVALID`) -> replay (mismo registro, sin duplicado) ->
clave con datos distintos (`IDEMPOTENCY_KEY_REUSED`) -> get (version) -> preview_update (from -> to) -> update sin ficha (`CONFIRMATION_REQUIRED`) -> edicion humana concurrente -> update con version vieja (`VERSION_CONFLICT`, cambio humano conservado) ->
update con version vigente (OK) -> texto con inyeccion guardado y devuelto como dato marcado -> preview_delete (borrado logico, riesgo alto) -> delete sin `confirm=true` (`CONFIRMATION_REQUIRED`, la ficha NO se consume) -> delete con ficha + `confirm=true` (borrado logico) -> el registro desaparece del listado.
Tambien: `orders` y `payment-transactions` no admiten escritura (`OPERATION_NOT_ALLOWED`); payload enorme e `idempotency_key` invalida rechazados.

## Test de concurrencia (sec. 42): PASS (`VERSION_CONFLICT`, no sobrescribe).
## E2E de codigo (sec. 40): PARCIAL - solo `search` y `read` (con guardas). Sin impact/proposal/validate/tests/approval/promotion/rollback: no hay integracion con `ai_editor`.
## E2E alineamiento de negocio (sec. 41): NO REALIZADO - depende de `business.audit` y del plano de codigo con propuestas.
## Auditoria: 23 lineas `mcp.audit` durante el ultimo ciclo; 0 apariciones de JWT/`Bearer` en los logs del contenedor; `write_result` con principal, herramienta, recurso, operacion, objetivo, campos cambiados y resultado.

## Que NO se hizo (y por que)
- Produccion, canary y rollback de produccion: exigen security PASS + E2E PASS completos + aprobacion humana (plan sec. 47/50).
- Escrituras reales sobre `products`/`brands`: no se ejecutaron (el ciclo se valido en `categories`; misma via de codigo, distinto recurso). Los productos requieren datos ricos (variantes, imagenes) que Django valida.
- Los tests unitarios (`mcp_server/tests/test_core.py`, `dashboard/tests_mcp_whoami.py`) se escribieron pero no se ejecutaron (instruccion del usuario de no correr suites automatizadas sin orden directa).

## Adenda 2026-09-25 (tokens personales y auditoria durable)
- **Django (script funcional en dev, 29 comprobaciones OK):** crear (token en claro una sola vez, solo hash en BD), vigencia y nombre validados, canje -> JWT de 15 min con `via=mcp`, `via=mcp` NO crea ni revoca tokens, rechazos genericos (401) y auditados en `SecurityEvent`,
  eventos sin token ni hash, caducado/revocado/usuario sin `is_superuser`/inactivo => 401, otro admin y customer sin acceso (404/403), limite 30/min por IP.
- **Cliente MCP real, fase `pat` (7 OK):** token revocado y token desconocido rechazados, token valido con la identidad del admin dueno y perfil `READ_ONLY`, la API responde con el JWT canjeado, el perfil MCP se respeta,
  revocacion desde el panel (204) y rechazo tras el TTL de cache.
- **Auditoria durable:** un ciclo de escrituras dejo 5 `SecurityEvent MCP_ACTION` (create, 2 update, conflicto, delete) con usuario real, herramienta, recurso, operacion, objetivo y campos cambiados; sin valores ni JWT.
- Migracion `security.0011_mcp_access_tokens` (modelo + nuevos tipos de evento) aplicada en dev; **hay que aplicarla en produccion al desplegar Django**.

## Adenda 2026-09-25 (plano de codigo, Fases 7-8; solo desarrollo)
- **Sec. 40 E2E de codigo: PARCIAL -> mayormente cubierto.** Django (scripts funcionales, 29 comprobaciones OK): analisis por grafo, 401/403, `via=mcp` NO aprueba (403), promocion sin aprobacion rechazada, sin `confirm` => 409, deriva de workspace => 409, promocion real de un archivo de prueba + rollback que lo restaura, 5+ eventos `MCP_ACTION code_*`.
  MCP real (fase `code`, 17 OK): perfil CODE_CHANGE, sin Tool de aprobacion ni de tests, graph_status/describe_symbol/impact_analysis, ids malformados, `promote` sin confirm, propose/status/list/discard. Regresion `readonly` (con secretos reales, 2 comprobados) y `write`: 0 fallos.
- **No verificado:** una propuesta generada por un LLM real (el proveedor de `ai_editor`, Ollama, esta deshabilitado: el camino probado es el de fallo limpio `state=FAILED`) y la promocion de una propuesta real (se uso un sandbox sintetico con el `Sandbox`/`promote_to_workspace` reales).
- Sec. 41 (alineamiento de negocio): sigue pendiente de `business.audit`.

## Adenda 2026-09-25 (business.audit, Fase 9)
Tool `business.audit` (solo lectura, todos los perfiles): registro de recursos vs OpenAPI vivo, soft-delete de modelos (`SintelBaseModel`), recursos sensibles de solo lectura, perfil por defecto sin escrituras, ausencia de Tool de aprobacion y documentacion del propio MCP. Cada hallazgo lleva clasificacion + evidencia.
**Primer resultado real: 1 CONTRACT_DRIFT** - el registro declaraba `payment-transactions.get` y Django solo expone `list` (`AdminPaymentViewSet`). Corregido en `registry.py`/`API_MAPPING.md`. Tras el fix: 0 hallazgos distintos de MATCH. Se corrigio ademas `business-rules.md` regla 9 (decia "codigo solo lectura": obsoleto tras Fase 7-8).
Regresion completa tras el cambio: readonly 61 OK, write 0 fallos, code 0 fallos. Alcance: NO audita reglas de dominio (precios/IVA/pedidos) ni calcula `DEAD_CODE`; sec. 41 del plan queda PARCIAL.

## Adenda 2026-09-25 (ampliacion de dominios: servicios, renting, sitio web)
Registro ampliado tras verificar cada ruta contra el OpenAPI de Django: escritura completa (create/update/delete logico) en `services`, `service-categories`, `equipment`, `renting-categories`, `renting-brands`; edicion (list/get/update, sin crear ni borrar) en 8 recursos del sitio web (`home-cards`, `home-card-groups`, `feature-banner-sections`, `feature-banner-blocks`, `footer-groups`, `navbar`, `brand-slider`, `about-us`), que en Django no tienen GET de detalle (nuevo `detail_via_list`).
Smoke fase `domains` (dev, ADMIN_CRUD): 29 comprobaciones OK (ciclo completo create/get/update/delete logico en `renting-brands`; `navbar` y `home-cards` leidos por uuid y editados por PATCH sin cambio de valor; `navbar` no admite create). Regresion `readonly` y `write`: 0 fallos.
No verificado: create real de `services`/`equipment` (solo preview; Django valida el cuerpo al ejecutar) ni sus sub-recursos (variantes y precios por dia de equipment, logistica, imagenes): siguen fuera del MCP.
