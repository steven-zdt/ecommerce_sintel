# TOOL_REGISTRY - SINTEL MCP

Fuente de verdad: `policy.py::TOOL_CLASS` / `PROFILE_TOOLS` y `registry.py::RESOURCES`. Tambien disponible en vivo: `resource://sintel/tool-registry` y `api.describe`.

## Tools
| Tool | Clase | Perfiles | Notas |
|---|---|---|---|
| `mcp.whoami` | READ | todos | identidad y Tools permitidas (del token) |
| `api.describe` | READ | todos | catalogo verificado contra OpenAPI; dominios bloqueados con motivo |
| `crud.list` | READ | todos | `resource`, `filters` (solo los reales del ViewSet), `limit` (<=50), `page` (<=20) |
| `crud.get` | READ | todos | devuelve `version` |
| `crud.preview_create` / `preview_update` / `preview_delete` | READ (no ejecutan) | ADMIN_CRUD, FULL_MAINTAINER | riesgo, from->to, `confirmation_token` |
| `crud.create` | WRITE | ADMIN_CRUD, FULL_MAINTAINER | `idempotency_key` obligatoria; token si riesgo medio/alto |
| `crud.update` | WRITE | ADMIN_CRUD, FULL_MAINTAINER | `expected_version` obligatoria; `VERSION_CONFLICT` |
| `crud.delete` | DESTRUCTIVE (logico) | ADMIN_CRUD, FULL_MAINTAINER | riesgo alto: token + `confirm=true` + `expected_version` |
| `code.search` / `code.read` | READ | todos | solo lectura del workspace, secretos enmascarados |

NO existen (a proposito): `execute_arbitrary_url`, `code.execute_arbitrary_shell`, `code.write_file`, `code.delete_file`, `execute_arbitrary_steps`, SQL, Docker.
Plano de codigo (solo desarrollo, ver CODE_CONTROL_PLANE.md): `code.graph_status`, `describe_symbol`, `find_references`, `impact_analysis`, `resolve_change`, `build_context`, `find_tests` (READ, CODE_REVIEW); `list_changes`, `change_status` (READ); `propose_change`, `discard_change` (WRITE), `promote_change`, `rollback_change` (DESTRUCTIVE, confirm=true) (CODE_CHANGE). Sin Tool de aprobacion ni de ejecucion de tests.
Pendientes: `business.audit`.

## Resources (solo lectura, sin secretos)
`resource://sintel/architecture`, `business-rules`, `apps`, `openapi` (resumen), `tool-registry`, `agent-registry` (no disponible: dice por que), `environment-status`.

## Prompts
`inspect_module`, `audit_business_rule`, `prepare_crud_change`, `prepare_code_change`, `review_proposed_change`, `run_regression` (ninguno incluye bypass).

## Codigos de error estables
`UNAUTHENTICATED`, `FORBIDDEN_TOOL`, `RESOURCE_NOT_ALLOWED`, `OPERATION_NOT_ALLOWED`, `INVALID_ARGUMENT`, `RATE_LIMITED`, `LIMIT_EXCEEDED`, `CONFIRMATION_REQUIRED`, `CONFIRMATION_INVALID`,
`VERSION_CONFLICT`, `IDEMPOTENCY_KEY_REQUIRED`, `IDEMPOTENCY_KEY_REUSED`, `UPSTREAM_ERROR`, `UPSTREAM_DENIED`, `NOT_FOUND`, `CODE_PLANE_DISABLED`, `PATH_NOT_ALLOWED`, `INTERNAL_ERROR`.
Los errores llegan como `isError` con el JSON `{ok:false,error:{code,message,...}}` (sin trazas ni valores internos).
