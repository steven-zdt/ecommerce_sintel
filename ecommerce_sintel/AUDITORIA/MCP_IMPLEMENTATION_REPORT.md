# MCP Implementation Report - PROMPT_IMPLEMENTAR_MCP_ECOMMERCE_ADMIN_CODE_AGENT_SINTEL (2026-09-25)

## Estado global: **IN_PROGRESS** - implementado y verificado en DESARROLLO; **no desplegado en produccion**; el plano de codigo con escritura NO esta hecho.

## Estado por fase
| Fase | Estado | Evidencia / nota |
|---|---|---|
| 0 Discovery | Hecha | Hallazgos abajo (sec. 2) |
| 1 Skeleton (runtime, Streamable HTTP, health, config, logging) | Hecha | imagen `sintel_ecommerce_mcp`, `/mcp-health`, logging JSON; contenedor no root, read-only, cap_drop ALL, mem/pids limitados |
| 2 Auth + RBAC | Hecha (modo `django_jwt`) | bearer = JWT de admin validado por Django (`/dashboard/mcp/whoami/`); perfiles MCP por email. **Sin OAuth ni tokens de larga duracion** |
| 3 API discovery | Hecha | `api.describe` + registro declarativo verificado contra `/api/schema/` (808 rutas, 431 del panel); lista blanca de operaciones |
| 4 Read tools | Hecha | `crud.list/get`, 7 resources, 6 prompts |
| 5 Write tools | Hecha | `crud.create/update/delete` + previews, fichas de confirmacion, idempotencia, `expected_version`, auditoria |
| 6 Domain actions | **Parcial** | CRUD habilitado: shop (products, categories, brands). Solo lectura: taxes, services, renting, orders, quotes, payment. **Bloqueados con motivo**: marketing, support, inventory, users, notifications. **No hay acciones** (activate/publish/send...) porque no se inventan sin endpoint verificado |
| 7 Code control plane | **Parcial** | `code.search`/`code.read` (solo lectura, con guardas). Faltan las 11 Tools de analisis/propuesta/promocion |
| 8 Approval / promotion | **No hecha** | requiere integrar `ai_editor` (ver CODE_CONTROL_PLANE.md) |
| 9 Business audit | **No hecha** | `business.audit` sin implementar |
| 10 Security red team | Hecha (parcial, ver MCP_SECURITY_AUDIT.md) | 83 comprobaciones funcionales OK contra un cliente MCP real |
| 11 E2E | Parcial (ver MCP_E2E_REPORT.md) | CRUD y concurrencia si; codigo/alineamiento de negocio no |
| 12 Canary / 13 Production | **No hechas** | exigen security PASS + E2E PASS + canary + aprobacion humana |

## Hallazgos de la Fase 0 que cambian el diseno
1. **`/api/v1/auth/profile/` no expone `is_superuser`** => el MCP no puede saber si un token es admin por ahi. Solucion: endpoint `GET /api/v1/dashboard/mcp/whoami/` (solo lectura, `IsAdminUser`).
2. **No existen tokens personales ni OAuth**; solo SimpleJWT (access 15 min). El MCP usa ese JWT tal cual (Django sigue siendo la autoridad). Limite: hay que renovar el token cada 15 min. Tokens de larga duracion = trabajo futuro (modelo + endpoints en Django).
3. **Los ViewSets del panel no tipan su cuerpo en OpenAPI** (categorias, marcas...): el MCP no puede validar payloads contra el esquema; **valida Django al ejecutar** (400 por campo). El preview no puede prometer validez.
4. **Los filtros que Django soporta son pocos** (products: `search,is_active,is_featured`; equipment: `search,category__slug,brand__slug`; payments: `status`; el resto ninguno) y Django ignora en silencio los desconocidos. El registro solo permite los reales y rechaza el resto (una primera version declaraba filtros inexistentes; corregido tras verificarlo).
5. **Los productos no exponen `updated_at`** => la version para `expected_version` es un hash del registro (ETag). Hay una ventana TOCTOU entre releer y escribir.
6. **`ai_editor` opera sobre el workspace real del repo**; en contenedores de produccion el codigo es la copia de la imagen, no git. Promover alli no llegaria a git. El plano de codigo con escritura debe vivir donde esta el checkout (dev). Detalle en CODE_CONTROL_PLANE.md.
7. **`mcp` 2.x (SDK oficial 2.2.0)**: API `MCPServer` (no `FastMCP`), `TokenVerifier`, `custom_route`, proteccion DNS-rebinding, cliente basado en `httpx2`; `mcp` ya no arrastra `httpx` (se declara aparte).
8. Un borrado logico (`DELETE` 204) deja el registro accesible por uuid pero fuera del listado.

## Bugs encontrados y corregidos durante la verificacion
- El redactado de secretos en codigo no reconocia `SECRET_KEY = '...'` (`\b` no separa `SECRET` de `_KEY`) y un literal en `config('X', default='valor')` salia sin enmascarar. Corregido (`sanitize.redact_text`) y verificado con los valores reales de `SECRET_KEY` y la clave JWT de dev: no aparecen en ninguna respuesta.
- Dos previews del mismo dato en el mismo segundo generaban fichas identicas (la 2.a quedaba "ya utilizada"). Se agrego un nonce. Un olvido de `confirm=true` ya no consume la ficha.
- Filtros declarados que Django ignoraba (ver 4).
- Lista de dependencias: el lock inicial quedo vacio y `httpx` no venia con `mcp` (imagen sin dependencias); regenerado.

## Archivos
`mcp_server/` (config, auth, policy, registry, openapi, crud, confirmations, limits, sanitize, audit, code_read, django_client, errors, prompts, server, `__main__`, `content/`, `scripts/protocol_smoke.py`, `tests/test_core.py`, `Dockerfile`, `.AGENT/*`),
`dashboard/api/mcp_views.py` + ruta en `dashboard/api/urls.py`, `dashboard/tests_mcp_whoami.py`, servicio `mcp_server` (perfil `mcp`) en `docker-compose.yml`.

## Como levantarlo en desarrollo
`docker compose --profile mcp up -d mcp_server` (URL `http://127.0.0.1:8200/mcp`; salud `http://127.0.0.1:8200/mcp-health`). Por defecto TODO admin tiene perfil `READ_ONLY`; para escrituras:
`MCP_PRINCIPAL_PROFILES="admin@sintel.net.co=ADMIN_CRUD" docker compose --profile mcp up -d --force-recreate mcp_server`. Cliente: bearer con un JWT de admin (dura 15 min).

## Pendiente (orden sugerido)
1. Tokens de larga duracion / OAuth (modelo en Django + rotacion) para que un cliente MCP no dependa del JWT de 15 min.
2. Integrar `ai_editor` + `graph_client` (Fases 7-8) en un runtime de desarrollo; decidir como se entrega la aprobacion humana fuera del canal del LLM.
3. `business.audit` (Fase 9) y acciones de dominio con endpoint verificado (activate/deactivate/publish...).
4. Auditoria a `SecurityEvent` de Django (hoy solo logs), idempotencia/rate limit en Redis si hay varias replicas.
5. Despliegue: definir el servicio en `docker-compose.prod.yml`, ruta `/mcp` en nginx/Cloudflare (nunca publicar `/mcp-health`), canary con un cliente limitado y aprobacion humana.
