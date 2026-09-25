# SECURITY_MODEL - SINTEL MCP

Principio: `MCP permission != Django permission != Tool permission != business authorization`. El MCP AGREGA capas; nunca sustituye a Django.

## 1. Identidad y autenticacion
- Bearer = JWT de acceso (simplejwt) de un **admin**. El MCP no tiene el secreto de firma: pregunta a Django (`GET /api/v1/dashboard/mcp/whoami/`, `IsAdminUser` = `is_staff AND is_superuser`).
  Django responde 401 (invalido/caducado) o 403 (no admin) => el MCP responde 401. Django inalcanzable => falla cerrado.
- La identidad NUNCA viene de argumentos (`user_id`, `role`, `is_admin` se ignoran). El token viaja reenviado a Django en cada llamada: **Django aplica sus permisos** (no hay RBAC paralelo).
- **Tokens personales (`smcp_...`)** (2026-09-25): el admin los crea en `POST /api/v1/dashboard/mcp-tokens/` (vigencia 1-90 dias, se muestra UNA vez; solo se guarda el sha256). El MCP los canjea en `POST /api/v1/internal/mcp/exchange/` por un JWT de 15 min del mismo admin con el claim `via=mcp`; Django sigue siendo la autoridad (revocado, caducado o usuario sin `is_superuser`/inactivo => 401 generico auditado; limite 30/min por IP). El canje se cachea `MCP_PAT_CACHE_TTL` s (120 por defecto = lo que tarda en notarse una revocacion).
- **Frontera `via=mcp`**: un JWT canjeado por el MCP NO puede crear ni revocar tokens (evita que un cliente comprometido se de persistencia) y, NO puede aprobar cambios de codigo (`POST code/proposals/<id>/decision/` => 403).
- Un JWT normal de 15 min tambien sirve. `MCP_AUTH_MODE=service_token|oauth` no estan implementados (el servidor no arranca).

## 2. Perfiles MCP (capa adicional)
`READ_ONLY` (por defecto para todo admin), `ADMIN_CRUD`, `CODE_REVIEW`, `CODE_CHANGE`, `FULL_MAINTAINER`. Se asignan por email en `MCP_PRINCIPAL_PROFILES` (`email=PERFIL,...`). Un perfil desconocido cae al por defecto.
CODE_REVIEW = READ_ONLY + analisis por grafo (`code.graph_status|describe_symbol|find_references|impact_analysis|resolve_change|build_context|find_tests|list_changes|change_status`); CODE_CHANGE = CODE_REVIEW + `code.propose_change|promote_change|rollback_change|discard_change`; FULL_MAINTAINER = ADMIN_CRUD + CODE_CHANGE. Ningun perfil aprueba: la decision es humana (ver sec. 7).

## 3. Escrituras
Riesgo por operacion en `registry.py` (create/update medio, delete alto, lecturas bajo). Medio/alto: **preview -> confirmation_token** (HMAC, un solo uso, 5 min, atado a principal+tool+recurso+operacion+objetivo+hash del payload+version).
Alto: ademas `confirm=true` (se comprueba ANTES de consumir la ficha). `create` exige `idempotency_key`; `update/delete` exigen `expected_version` (`VERSION_CONFLICT` si el registro cambio; nunca se sobrescribe en silencio).
Limite honesto: la ficha prueba que se previsualizo con esos parametros; la decision humana la toma el cliente MCP al aprobar la llamada. Entre releer y escribir hay una ventana (TOCTOU) porque la API de Django no admite `If-Match`.

## 4. Sin acceso arbitrario
- Sin URL arbitraria: `django_client.call` solo compone `/api/v1/dashboard/<recurso del registro>/[uuid]/` (regex estricta, uuid validado). No hay SSRF por construccion.
- Sin SQL/ORM/shell/Docker/filesystem: no existen esas capacidades ni Tools con esos nombres. El contenedor no monta Postgres/Redis/socket.
- Borrado: solo logico (regla del proyecto). Sin DELETE fisico.

## 5. Datos no confiables (prompt injection)
Todo texto de la BD (descripciones, mensajes, tickets, campanas) se devuelve como DATO: `data_notice` + `suspicious_fields` (senal informativa). Los prompts MCP no contienen bypass. Ninguna Tool interpreta contenido de un registro como instruccion.

## 6. Salida y secretos
`sanitize.redact` (claves sensibles -> `[REDACTED]`, cadenas y listas acotadas), PII enmascarada en recursos sensibles (`orders`, `quotations`, `payment-transactions`: solo lectura), tope de bytes por respuesta.
Codigo: `redact_text` enmascara `SECRET_KEY = '...'`, `password: ...`, `config('X', default='valor')`. Los tokens jamas entran a logs (`Principal.token` con `repr=False`; auditoria con `redact`).

## 7. Plano de codigo (lectura + propuestas en sandbox; promocion solo tras aprobacion humana)
`MCP_WORKSPACE_ROOT` vacio => desactivado. Rutas relativas normalizadas, sin `..`, sin absolutas/unidades, sin bytes nulos, **sin symlinks**, dentro del workspace, tope 64 KB, solo extensiones de texto, lista de rutas sensibles
(`.env`, `secret`, `credential`, `.pem`, `.key`, `backup`, `.dump`, `private_media`, `.git/`, `token`...). Compose monta el repo `:ro` y tapa `.env` y `.env.production` con `/dev/null`. `code.search` sin regex del usuario ni shell.
Escritura (2026-09-25, solo desarrollo, `AI_EDITOR_CODE_PLANE_ENABLED` apagado por defecto): propuestas en sandbox via `ai_editor` (Django). El MCP no escribe archivos; `promote_change` exige `confirm=true` + aprobacion humana registrada por un admin con sesion normal (via=mcp => 403) + compuertas de ai_editor (F22, deriva, sintaxis). `change_id` con formato estricto `chg-<16 hex>`; tests NUNCA se ejecutan. Detalle en CODE_CONTROL_PLANE.md.

## 8. Limites y abuso
Rate limit por ventana de 60 s: global (x10), principal (`MCP_RATE_LIMIT`, 60), operacion (escrituras `MCP_WRITE_RATE_LIMIT`, 20) y recurso; `limit<=50` registros, `page<=20`, payload de escritura <= 64 KB, cuerpo HTTP <= 256 KB (`413`),
timeout upstream 20 s. Todo en memoria por proceso (varias replicas => cada una cuenta aparte).

## 9. Red y transporte
Proteccion DNS-rebinding activa (`allowed_hosts`/`allowed_origins`). `/mcp-health` es interno (no publicar por nginx). Produccion: HTTPS por Cloudflare/nginx, nunca puertos internos (5432, 6379, 11434, 8100, 8101).

## 10. Auditoria
Cada escritura y cada denegacion deja una linea JSON (`logger mcp.audit`): principal, herramienta, recurso, operacion, objetivo, campos cambiados (solo nombres), riesgo, confirmacion, resultado, `request_id`, `trace_id`. Sin secretos.
Ademas cada escritura/conflicto se copia (best-effort) a Django como `SecurityEvent MCP_ACTION` (`POST /api/v1/dashboard/mcp/audit/`, lista blanca de campos cortos, sin valores; el usuario del evento es el admin real).

## Riesgos residuales
Idempotencia/confirmaciones/rate limit en memoria (se pierden al reiniciar); TOCTOU en update/delete; propuestas de codigo en memoria del proceso Django (se pierden al reiniciar); el LLM de `ai_editor` es independiente del chat; la revocacion de un token personal tarda hasta `MCP_PAT_CACHE_TTL` s en notarse.
