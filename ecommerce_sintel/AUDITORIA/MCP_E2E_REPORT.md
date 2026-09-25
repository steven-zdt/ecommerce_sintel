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
