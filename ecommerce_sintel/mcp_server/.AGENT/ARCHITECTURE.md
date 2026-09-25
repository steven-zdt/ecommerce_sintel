# ARCHITECTURE - SINTEL E-Commerce MCP Server

Creado 2026-09-25 (PROMPT_IMPLEMENTAR_MCP_ECOMMERCE_ADMIN_CODE_AGENT_SINTEL). Estado: **FASES 0-6 parciales + plano de codigo de solo lectura**, verificado en desarrollo. Produccion: NO desplegado.

## Responsabilidad
Adapter/orquestador que expone a clientes MCP externos (Streamable HTTP) la administracion del ecommerce **a traves de la API REST existente**. No contiene logica de negocio: no
calcula precios, IVA, envios, stock ni transiciones de pedido, y no accede a PostgreSQL, Redis, shell, Docker socket ni filesystem irrestricto.

```
Cliente MCP --Streamable HTTP /mcp (Bearer = JWT de un admin de Django)--> SINTEL MCP
   auth.py: DjangoTokenVerifier -> GET /api/v1/dashboard/mcp/whoami/ (Django decide: IsAdminUser)
   policy.py (perfil) -> limits.py (rate/presupuesto) -> tools -> audit.py
        |- API plane:  crud.py -> django_client.py -> /api/v1/dashboard/<recurso>/  (con el token del propio admin)
        |- Code plane: code_read.py -> workspace montado SOLO LECTURA (code.search / code.read)
```

## Modulos
| Modulo | Funcion |
|---|---|
| `config.py` | Variables de entorno (`MCP_*`); falla cerrado si el modo de auth no esta implementado |
| `auth.py` | Verificador de tokens (delegado en Django), `Principal`, cache 60 s (positiva) / 5 s (negativa) |
| `policy.py` | Clases de Tool (READ/WRITE/DESTRUCTIVE...) y perfiles READ_ONLY/ADMIN_CRUD/CODE_REVIEW/CODE_CHANGE/FULL_MAINTAINER |
| `registry.py` | Recursos permitidos (declarativo), riesgo por operacion, dominios bloqueados con motivo |
| `openapi.py` | Contrato: `/api/schema/` de Django; las escrituras no confirmadas en OpenAPI fallan cerrado |
| `crud.py` | list/get/preview_*/create/update/delete con confirmacion, idempotencia, version y auditoria |
| `confirmations.py` | Fichas HMAC de un solo uso atadas a principal+tool+recurso+objetivo+payload+version; almacen de idempotencia |
| `limits.py` | Ventana deslizante (global, principal, operacion, recurso), tope de registros, profundidad de paginacion, bytes |
| `sanitize.py` | Redaccion de secretos, enmascarado de PII, marca de datos no confiables, tope de salida |
| `audit.py` | Logging JSON, ids de traza, auditoria de escrituras/denegaciones, contadores |
| `code_read.py` | Lectura/busqueda de codigo con anti-traversal, sin symlinks, rutas sensibles bloqueadas |
| `server.py` | Ensamblado: Tools, Resources, Prompts, `/mcp-health` |

## Runtime
Imagen propia `sintel_ecommerce_mcp` (`mcp_server/Dockerfile`, contexto = raiz del repo, `Dockerfile.dockerignore` deja solo `mcp_server/`). No root (uid 10001), `read_only`, `cap_drop ALL`,
`no-new-privileges`, limites de memoria/CPU/PIDs, healthcheck. Sin `env_file` (no hereda secretos de `.env`). Solo habla con Django (`http://django:8000`).
Compose: perfil `mcp` en `docker-compose.yml` (dev): `docker compose --profile mcp up -d mcp_server`. En produccion NO esta definido todavia.

## Que falta (ver AUDITORIA/MCP_IMPLEMENTATION_REPORT.md)
Integracion con `ai_editor`/`graph_sdk` (propose/validate/tests/approval/promote/rollback), `business.audit`, acciones de dominio (activate/publish/send...), workflows de marketing,
OAuth/tokens de larga duracion, despliegue a produccion detras de nginx/Cloudflare, canary.
