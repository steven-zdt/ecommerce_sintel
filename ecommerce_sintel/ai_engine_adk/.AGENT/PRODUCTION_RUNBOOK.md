# PRODUCTION_RUNBOOK — operación del asistente en producción

> Documento vivo (HARDENING F19, 2026-09-24). **Reglas del proyecto**: (1) todo cambio se prueba primero en DEV; (2) nunca editar ni ejecutar comandos ad-hoc en `sintel_prod_*`; (3) cada contenedor construye su propia imagen; (4) toda bandera nueva se replica en `.env` y `.env.production` en el mismo cambio; (5) `Documentacion/` y `notas.txt` nunca se commitean; (6) **el asistente IA no ejecuta tests, benchmarks ni despliegues**: los pasos de este runbook los hace el usuario.

## 1. Componentes (prod)
`nginx` -> `django` (Daphne, Channels) -> `sintel_ai_adk` (`/chat`, un worker uvicorn, puerto 8101 interno) -> `sintel_ollama` (Qwen3.5-9B, `0.30.10`) y LM Studio (host, respaldo). Datos: `db` (Postgres pgvector; BD `sintel_adk_sessions` para sesiones ADK), `redis` (auth). Celery worker/beat (`--concurrency=4`; WhatsApp usa `ask_ai` síncrono de hasta 300 s). Red privada de inferencia `ai_private` definida en `docker-compose.prod.yml` **pero sin aplicar** (edición pendiente de recrear).

## 2. Configuración (defaults en código; solo lo NO obvio)
Modelo: `LOCAL_MODEL_CHAIN` (Ollama primario + LM Studio). Sesión: `ADK_SESSION_BACKEND=database` + `ADK_SESSION_DB_URL`. Seguridad: `AI_SERVICE_TOKEN` (+`_PREVIOUS`, `_REQUIRED`). Resto de las variables (topes, monitor/enforce, admisión, canary, handoff): tablas en `MODEL_RUNTIME.md` §3, `SECURITY_MODEL.md` §5, `TOOL_SECURITY.md`, `HARDENING_F17_PROPOSAL_*`, `HARDENING_F18_PROPOSAL_*`. `LOG_FORMAT=json` es opt-in.

## 3. Despliegue (F17: DEV -> STAGING -> CANARY -> PRODUCCIÓN) — lo ejecuta el usuario
1. F10: regenerar reportes y `./deploy/promote_check.sh --reports ...` (gate, secretos, manifest de versiones, banderas dev/prod sincronizadas).
2. `./deploy/release_ai.sh snapshot` (deja `:prev` y `:rel-<ts>`, guarda banderas no secretas).
3. Construir/levantar el canary con `docker-compose.canary.yml` (perfil `canary`); `AI_CANARY_USER_EMAILS` (internos) y `AI_CANARY_PERCENT=0`.
4. Comparar con `manage.py ai_canary_report --hours 24` (HOLD/PROCEED/ROLLBACK sugerido); subir 5 -> 25 -> 50 -> 100.
5. Promover: reconstruir `sintel_ai_adk` (deploy.sh **no** lo reconstruye: `docker compose ... build --no-cache sintel_ai_adk`), vaciar `AI_CANARY_ENGINE_URL`, bajar el canary.
6. Migraciones: aditivas; **hacer backup antes** (`deploy/backup.sh`).
Rollback: vaciar `AI_CANARY_ENGINE_URL` y/o `./deploy/release_ai.sh rollback adk|django|all` (no revierte migraciones, modelo, RAG ni `.env.production`).

## 4. Operación
- **Salud**: `./deploy/healthcheck.sh`; el ADK expone `/health` (liveness). Logs: `docker logs sintel_prod_ai_adk` (correlar por `rid`).
- **Métricas**: `manage.py ai_observability_report --days 7`; `ai_turn_metrics` en logs.
- **Backups**: `deploy/backup.sh` (dump + media **cifrados con openssl** si existe `SINTEL_BACKUP_KEY_FILE`; **sin secretos**; local, sin copia externa). Restaurar: `deploy/restore.sh <timestamp>` (descifra `.enc`; pide `RESTAURAR`). Limpiar secretos viejos: `deploy/purge_legacy_secret_backups.sh` (dry-run por defecto).
- **Rotación de secretos**: runbook en `HARDENING_F15_SECRETS_AUDIT_2026-09-24.md` §3.
- **Soporte humano**: responder como admin pausa la IA; reactivar con `POST /api/v1/support/chats/<uuid>/resume-ai/` (falta botón en la UI).
- **Kill switches**: `INCIDENT_RESPONSE.md` §3.

## 5. Estado de despliegue a producción (verificar; reflejaba el 2026-09-24)
Hecho en prod: Ollama de producción (F1/C1) y ADK con cadena Ollama primario + LM Studio respaldo. **F2–F18 NO están desplegadas en producción** (código en la rama `fix/audit-p0-remediation`, probado solo en DEV). Para llevarlas: reconstruir `sintel_ai_adk` y `django` (+celery), aplicar migraciones `ai_knowledge.0002`, `customer_memory.0002` y `security.0010` (con backup previo), poner `AI_SERVICE_TOKEN` (con `_REQUIRED=false` al inicio) y aplicar la red `ai_private`. Todas las banderas nuevas tienen default inocuo; las que cambian comportamiento por defecto: `AI_PAUSE_ON_HUMAN_REPLY=true`, `AI_DEGRADED_ADMIN_ALERT=true`, guardias de entrada/salida activas.

## 6. Pendientes operativos
Baseline en vivo de F10 y SLO (F24); mediciones de F12 (`num_ctx`, `keep_alive`) y F13 (carga/concurrencia); simulacros de F14 (`chaos_dev.py`); conectar el lock del ADK al build y fijar digests (F16); copia externa cifrada de backups (F15); mover confirmaciones pendientes a Redis (F14); cola dedicada de Celery para `ask_ai` (F13); healthcheck del ADK de dev.

## Troubleshooting: el chat o el panel no conectan con LM Studio (agregado 2026-09-25)
1. En el host: `curl http://127.0.0.1:1234/v1/models` debe listar modelos (LM Studio con el servidor local iniciado).
2. Log de LM Studio (`~/.lmstudio/apps/bionic/server-logs`): al probar debe aparecer `Received request: GET to /v1/models`. **Si no aparece, el fallo es de red/URL**, no del modelo.
3. URL en el panel / `LOCAL_MODEL_CHAIN`: `http://host.docker.internal:1234/v1`, nunca `localhost`/`127.0.0.1`.
4. `docker inspect <contenedor> --format '{{.HostConfig.ExtraHosts}}'` debe incluir `host.docker.internal:host-gateway` (django, sintel_ai, sintel_ai_adk).
5. Reproducir con un contenedor desechable con las mismas redes/DNS/`--add-host` (no con los defaults de Docker).
6. Cambios de entorno/compose: `up -d --force-recreate <servicio>`; de codigo: rebuild. Ver `AUDITORIA/INCIDENTE_IA_CONFIG_LOCALHOST_2026-09-25.md`.

## Troubleshooting: el chat del cliente no responde (agregado 2026-09-25)
Recorrer en orden; cada paso descarta una capa:
1. **Django recibe el mensaje?** Log de `django`: `[CHAT] room=... status=sent`. Si no aparece: WebSocket/nginx/cloudflared o login.
2. **Se llama a la IA?** Debe seguir `[CHAT] room=... AI request status=started`. Si falta, el log trae `ai_operation_event=ai_inactive reason=paused|assigned|closed|flag_off` (desde 2026-09-25) => IA inactiva en esa sala: `ai_paused`, `assigned_admin`, sala cerrada, o
   `AI_SUPPORT_CHAT_ENABLED`/`AI_GLOBAL_ENABLED` en falso. Solucion habitual: "Reactivar IA" (`POST /api/v1/support/chats/<uuid>/resume-ai/`).
3. **Llega al ADK?** Log de `sintel_ai_adk`: `POST /chat`. Si no llega: `AI_ENGINE_URL`, `AI_SERVICE_TOKEN` (si `AI_SERVICE_TOKEN_REQUIRED=true`), red `ai_private`.
4. **El ADK llega al modelo?** Log de LM Studio: `POST /v1/chat/completions`. Si no aparece: ver el troubleshooting de LM Studio (arriba) y `LOCAL_MODEL_CHAIN` / Registry.
5. Con `ai_operation_event=turn_timeout|turn_rejected|provider_failed|breaker_opened` el problema es del modelo/carga (ver INCIDENT_RESPONSE playbook A).

