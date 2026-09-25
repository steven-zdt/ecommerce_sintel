# MCP - Plan de despliegue canary a produccion (BORRADOR PARA REVISION, 2026-09-25)

Estado: **no ejecutado**. Nada de este plan se aplica sin aprobacion humana explicita por fase (CLAUDE.md 0-DEV-FIRST; flujo `./deploy/deploy.sh`, `.AGENT.md` sec. 0-C).
Alcance de produccion: SOLO plano API (CRUD acotado + lectura). El plano de codigo (`ai_editor`) NO se despliega: `AI_EDITOR_CODE_PLANE_ENABLED=false` (ya en `.env.production`).

## 0. Decisiones que necesito de ti antes de empezar
| # | Decision | Recomendacion |
|---|---|---|
| D1 | Quien usa el MCP en produccion (emails) | 1 solo admin (el tuyo) durante el canary |
| D2 | Perfil inicial | `READ_ONLY` toda la fase 1; `ADMIN_CRUD` solo en fase 3 y solo sobre `categories` |
| D3 | M-4: la ficha de confirmacion no es aprobacion humana | Aceptarlo: la decision la toma el cliente MCP que aprueba cada llamada; mantener READ_ONLY por defecto |
| D4 | Exposicion | Ruta `/mcp` por nginx/Cloudflare con HTTPS; `/mcp-health` NUNCA publico; idealmente restringida por Cloudflare Access/IP |
| D5 | Ventana | Fuera de horas pico |

## 1. Prerrequisitos (gates)
- [ ] Commits 4dcf1f5, 8b9287c, 9489591, 4757b74 revisados; decidir si van a `main` (hoy solo locales, rama `fix/audit-p0-remediation`).
- [ ] Security PASS: `MCP_SECURITY_AUDIT.md` sin hallazgos Alta/Media sin decision (M-2, M-3, M-4 aceptados por escrito).
- [ ] E2E PASS en dev (readonly 61, write y code sin fallos; ratelimit) - hecho 2026-09-25; repetir el mismo dia del despliegue.
- [ ] Tests unitarios escritos (`mcp_server/tests/test_core.py`, `security/tests_mcp_tokens.py`, `dashboard/tests_mcp_whoami.py`, `dashboard/tests_code_plane.py`): **ejecutarlos es decision tuya** (regla: no correr suites sin tu orden).
- [ ] Backup de BD de produccion verificado (recordatorio: aun no existe `sintel_secrets/backup.key`, los backups salen sin cifrar).

## 2. Cambios de codigo/config a preparar (en dev primero)
1. `docker-compose.prod.yml`: servicio `mcp_server` (build propio, imagen `sintel_prod_mcp`, container `sintel_prod_mcp`, `read_only`, `cap_drop: ALL`, sin puertos publicados al host; red interna; `extra_hosts` no necesario). Variables: `MCP_DJANGO_API_URL` interno, `MCP_DJANGO_HOST_HEADER` (host publico, como hace `ai_engine`), `MCP_PUBLIC_BASE_URL`, `MCP_ALLOWED_HOSTS/ORIGINS`, `MCP_CONFIRMATION_SECRET` (secreto nuevo en `.env.production`, >= 32 bytes), `MCP_PRINCIPAL_PROFILES` (vacio al inicio), `MCP_WORKSPACE_ROOT` vacio (plano de codigo desactivado en prod).
2. `nginx`/Cloudflare tunnel: publicar solo `/mcp` hacia `sintel_prod_mcp:8200`; bloquear `/mcp-health` desde fuera; timeouts largos para streaming.
3. `.env.production`: `MCP_CONFIRMATION_SECRET`, `MCP_PAT_CACHE_TTL=120`, `MCP_RATE_LIMIT=60`, `MCP_WRITE_RATE_LIMIT=20`; mantener `AI_EDITOR_CODE_PLANE_ENABLED=false` (regla de sincronizar flags dev/prod en el mismo cambio).
4. Migracion Django `security.0011_mcp_access_tokens` (se aplica con el deploy normal).
5. `deploy/deploy.sh`: incluir el servicio nuevo en build `--no-cache`, health-gate y verificacion post-deploy.

## 3. Fases del canary (cada una exige tu "adelante")
**Fase 1 - Django + MCP en solo lectura (riesgo bajo).** Deploy completo; verificar `security.0011` aplicada; `mcp-health` interno OK; 1 token personal (`smcp_`, 30 dias) creado por ti; cliente MCP real: `mcp.whoami`, `api.describe`, `crud.list`, `business.audit`. Criterio de salida: 24 h sin errores 5xx nuevos, 0 `tool_denied` inesperados, 0 secretos en logs (`grep -c Bearer` = 0).
**Fase 2 - Observacion.** 48 h con trafico real de lectura; revisar `SecurityEvent` `MCP_TOKEN_*`, rate limits, latencia de Django.
**Fase 3 - Escritura acotada.** `MCP_PRINCIPAL_PROFILES="tu@email=ADMIN_CRUD"`; solo `categories`: preview -> create -> update -> delete logico de un registro de prueba marcado; verificar `SecurityEvent MCP_ACTION`. Productos/marcas solo tras revisar el resultado.
**Fase 4 - Ampliacion.** Mas admins o mas recursos, uno a la vez, con nuevo visto bueno.

## 4. Rollback (por fase)
- Inmediato (segundos): revocar tokens (`DELETE /dashboard/mcp-tokens/<uuid>/`; efecto en <= `MCP_PAT_CACHE_TTL` s) o vaciar `MCP_PRINCIPAL_PROFILES` y recrear el servicio.
- Servicio: `docker compose -f docker-compose.prod.yml stop mcp_server` y quitar la ruta `/mcp` (el resto de la tienda no depende del MCP).
- Django: la migracion `0011` solo agrega tabla/choices; no requiere revertirse para apagar el MCP. Datos escritos por el MCP: son borrados logicos/ediciones auditadas (`MCP_ACTION`), reversibles desde el panel.

## 5. Riesgos residuales aceptados al desplegar
M-2 (idempotencia/fichas/rate limit en memoria: 1 sola replica), M-3 (TOCTOU), M-4 (ficha != aprobacion humana), OAuth inexistente (solo tokens personales <= 90 dias), revocacion con retraso de hasta 120 s.

## 6. Lo que NO se hace en produccion
Plano de codigo/`ai_editor`, dominios bloqueados (marketing, support, inventory, users, notifications), `/mcp-health` publico, OAuth, escrituras sobre pedidos/pagos/cotizaciones.

## 7. Avance (2026-09-25): decisiones D1-D5 aceptadas con las recomendaciones; cambios preparados, SIN desplegar
- **Decisiones:** D1 solo el admin del propietario; D2 READ_ONLY (ADMIN_CRUD solo en fase 3, solo `categories`); D3 M-4 aceptado; D4 `/mcp` por HTTPS **solo en `panel.sintel.net.co`** (host administrativo aislado; se decidio no publicarlo en api/sintel.net.co); D5 fuera de horas pico.
- **Hecho en el repo (verificado sin tocar contenedores `sintel_prod_*`):**
  - `docker-compose.prod.yml`: servicio `mcp_server` (profile `mcp`, imagen `sintel_ecommerce_mcp:prod`, container `sintel_prod_mcp`, sin `ports`, sin `env_file`, `read_only`, `cap_drop ALL`, sin workspace => plano de codigo apagado, `MCP_CONFIRMATION_SECRET` obligatorio). No arranca con `up -d` a secas. `docker compose config` valido (con y sin profile).
  - `nginx.prod.conf` (bloque del panel): `location = /mcp` (sin buffering, timeout 300 s, cuerpo <= 256 KB, `limit_req`), `/.well-known/oauth-protected-resource/mcp`, y `location = /mcp-health { return 404; }`. `nginx -t` OK en un contenedor desechable.
  - `deploy/deploy.sh`: paso opcional `DEPLOY_MCP=1` (build `--no-cache` + up del servicio). `bash -n` OK.
  - `.env.production` (no versionado): `MCP_CONFIRMATION_SECRET` aleatorio nuevo, `MCP_PRINCIPAL_PROFILES=` vacio, limites; `AI_EDITOR_CODE_PLANE_ENABLED=false` ya estaba.
  - Prueba de arranque con las variables de produccion (contenedor desechable en la red de dev): responde 401 sin token en `/mcp`.
- **Falta (requiere tu "adelante" explicito):** Fase 1 = `DEPLOY_MCP=1 ./deploy/deploy.sh` (reconstruye Django con `security.0011`, recrea celery/django brevemente, levanta MCP), luego `nginx -s reload`/recrear nginx. Comprobar tambien que la ruta del tunel de Cloudflare para `panel.sintel.net.co` no filtre `/mcp` (configuracion fuera del repo).

## 8. Fase 1 EJECUTADA (2026-09-25, ~17:10-17:25 hora local): MCP en produccion, solo lectura
- Backup previo (`deploy/backup.sh`): dump + media verificados (sin cifrar: falta `sintel_secrets/backup.key`).
- `DEPLOY_MCP=1 ./deploy/deploy.sh`: imagenes django/celery reconstruidas `--no-cache`, `sintel_prod_mcp` (imagen `sintel_ecommerce_mcp:prod`) creado y healthy; `nginx -s reload` aplicado (config validada antes).
- Verificado: `security.0011_mcp_access_tokens` aplicada; todos los contenedores healthy; `POST https://panel.sintel.net.co/mcp` sin token = 401; `/mcp-health` desde fuera = 404; `api.sintel.net.co/mcp` = 403 (no expuesto); `sintel.net.co` y `panel.sintel.net.co` = 200; sin trazas en django ni ai_adk.
- NO verificado: un cliente MCP autenticado contra produccion (requiere que el admin cree su token personal desde una sesion suya: `POST /api/v1/dashboard/mcp-tokens/`); chat de cliente con un mensaje real.
- Siguiente: crear el token personal (30 dias), probar `mcp.whoami` / `api.describe` / `crud.list` / `business.audit`, observar 24-48 h (Fases 1-2). Escritura (Fase 3) solo con nuevo visto bueno.
