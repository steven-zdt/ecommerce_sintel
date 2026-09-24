# HARDENING — FASE 15 (gestion de secretos, P0): AUDITORIA + RUNBOOK (estado: AUDITORIA HECHA, ROTACION = TU)

Plan: `PLAN_HARDENING_LLM_AGENTS_PRODUCCION_SINTEL_QWEN_OLLAMA_PRIMARY_20260924.md` §19. **Ningun valor de secreto se leyo ni se imprimio en esta fase** (solo nombres de archivo, longitudes, entropia y huellas). El asistente **no rota credenciales ni toca `.env.production`, contenedores de produccion ni el host de backups**: la rotacion esta en el runbook para que la hagas tu. Nada se ejecuto de tipo test/benchmark; las lecturas fueron `git`/`docker inspect` de solo metadatos.

## 1. Hallazgos (evidencia de solo lectura, 2026-09-24)
| # | Punto §19 | Resultado | Severidad |
|---|---|---|---|
| 1 | `notas.txt` en Git | **Nunca estuvo en el historial** (`git log --all -- notas.txt` = 0 en raiz y en `ecommerce_sintel/`). Hoy: ignorado (`.gitignore`) y excluido de imagenes (`.dockerignore`). Sigue existiendo en el disco del host | Bajo (Git); el archivo en disco sigue siendo un riesgo local |
| 2 | `.env`, `.env.production` en Git | **Nunca en el historial**; ignorados. `.env.production.example` (2 commits) contiene solo **placeholders** (los 4 valores con marcador textual; el correo vacio) | OK |
| 3 | Patrones de secretos en TODO el historial (224 commits, 3 ramas): claves privadas, AWS, sk-, ghp_, AIza, Slack | **0 coincidencias** | OK |
| 4 | JWT en el historial | **1 archivo**: `.claude/settings.local.json` estaba **rastreado** desde el primer commit (224 apariciones). Contiene 1 access token de simplejwt, **ya EXPIRADO** (exp anterior a hoy; los access token duran 15 min). Un token expirado no da acceso y no revela la clave de firma | Bajo (expirado). Corregido: se deja de rastrear y se ignora |
| 5 | Credenciales genericas en codigo | Las coincidencias revisadas son valores de CI marcados solo-CI (`ci-only-...-never-use-in-prod`), referencias a parametros/variables y placeholders. **Ninguno con forma de secreto real** (revisado por longitud/entropia/contexto, sin imprimir valores) | OK |
| 6 | `Documentacion/` estuvo en el historial (12 commits, ya se dejo de rastrear) | Sin patrones de secreto; contiene libros/docs (`fuente_unica_conocimiento`). Sigue sin poder commitearse | Info |
| 7 | Imagenes Docker (12 imagenes `sintel*` incl. `prod`/`prod-runtime`) | **0** variables `ENV` con secretos y **0** capas de `history` con `.env`/`notas.txt`/`*_PASSWORD=` | OK |
| 8 | `docker-compose*.yml` | Sin secretos literales (las variables llegan por `env_file`/`--env-file`); `MCP_TOKEN_STORE_DIR` es una ruta | OK |
| 9 | Frontend | `VITE_WOMPI_PUBLIC_KEY` es la llave **publica** de Wompi (publica por diseno) y los `.env` del frontend no estan rastreados | OK |
| 10 | **Backups (§19.2)** | `deploy/backup.sh` copia **`.env.production` (todos los secretos), `origin.key` (clave privada del certificado de origen) y las credenciales del tunel Cloudflare EN CLARO** junto con el dump, en `C:\Users\Administrator\sintel_backups` = **el mismo host que produccion**, **sin cifrado y sin copia externa** (sin gpg/openssl/age/rclone/s3). Un solo incidente en el host o un acceso al directorio expone TODO | **ALTA** |
| 11 | Secretos en logs / prompts / memoria / contexto del modelo (§19.1) | Cubierto por F8 (guardia de salida), F9 (`RedactionFilter` de logs: JWT, Bearer y valor exacto de secretos del entorno) y F7 (la memoria rechaza datos sensibles) | Cubierto |
| 12 | Posible exposicion previa de credenciales (mencionada en la documentacion) | Ya hubo una contrasena de admin pegada en el chat (2026-09-24), que **rotaste**. No hay evidencia en Git/imagenes de otras exposiciones; **no puedo descartar** copias fuera de Git (el disco del host, `notas.txt`, el chat, capturas): por eso el runbook trata la rotacion como preventiva | Media (no verificable) |

**Conclusion**: el repositorio y las imagenes estan limpios (no hace falta reescribir el historial: no hay secretos reales que purgar). El riesgo real esta en el **host**: `notas.txt`, los backups en claro y la cadena de rotacion pendiente.

## 2. Entregado (dev; nada aplicado en produccion)
- `.claude/settings.local.json`: `git rm --cached` + entrada en `.gitignore` (queda en tu disco, deja de viajar al remoto en commits futuros; el token del historial esta expirado).
- `ecommerce_sintel/scripts/security/scan_secrets.py` (**NO ejecutado**): escaner stdlib que **nunca imprime valores** (archivo:linea, tipo, longitud y huella sha256[:8]); modos `--staged`, `--tree`, `--history`.
- `.githooks/pre-commit`: ejecuta el escaner sobre lo staged y bloquea el commit si hay un secreto. Activar una vez por clon: `git config core.hooksPath .githooks`.
Ambos sin efecto hasta que los uses tu (el hook no esta activado).

## 3. Runbook de rotacion (lo haces tu; orden sugerido, ventana de mantenimiento corta)
Regla comun: generar con `python -c "import secrets; print(secrets.token_urlsafe(64))"` **en tu terminal** (nunca pegarlo en un chat), guardarlo solo en `.env.production` (y en tu gestor de contrasenas), sin comillas ni espacios; replicar cualquier variable nueva en `.env` de dev cuando aplique.
| Secreto | Como rotarlo | Efecto / cuidado |
|---|---|---|
| `AI_SERVICE_TOKEN` (F2) | 1) poner el valor viejo en `AI_SERVICE_TOKEN_PREVIOUS` y el nuevo en `AI_SERVICE_TOKEN` (django + ADK); 2) redeploy ADK primero y luego Django; 3) tras verificar, vaciar `PREVIOUS` y redeploy | Sin caida (acepta ambos durante la ventana). Hoy `AI_SERVICE_TOKEN_REQUIRED=false` (F2 sin activar en prod) |
| `JWT_SECRET_KEY` | nuevo valor en `.env.production`; redeploy **Django y ADK a la vez** (el ADK valida el JWT con la misma clave) | Cierra la sesion de TODOS los usuarios (deben iniciar sesion de nuevo) |
| Django `SECRET_KEY` | nuevo valor; **conservar el viejo en `SECRET_KEY_FALLBACKS`** unos dias (Django 5) | Sin ello se invalidan sesiones/tokens de restablecer contrasena |
| `DB_PASSWORD` (+ `ADK_SESSION_DB_URL`) | `ALTER USER ... PASSWORD '<nuevo>'` en Postgres; actualizar `.env.production` (incluye la URL de sesion del ADK) y recrear django, celery, ADK | Coordinar: hasta recrear los servicios fallan las conexiones |
| `REDIS_PASSWORD` | nuevo valor en `.env.production` (el compose lo usa en `--requirepass` y en las URLs de Celery/Channels/ADK); recrear Redis y todos los clientes | Redis sin estado critico (idempotencia/breaker/rate limits se regeneran) |
| SMTP (`EMAIL_HOST_PASSWORD`) | generar una nueva contrasena de aplicacion en el proveedor, revocar la anterior | Revisar que el restablecimiento de contrasena siga enviando correo |
| Wompi (llave privada, secreto de integridad, secreto de eventos) | Panel de Wompi: regenerar y actualizar `.env.production` | Verificar la firma del webhook tras el cambio (`PAYMENT_WEBHOOK_INVALID_SIGNATURE` en SecurityEvent) |
| WhatsApp/Meta (`META_ACCESS_TOKEN`, `META_APP_SECRET`, verify token, token interno del gateway) | Consola de Meta/gateway: regenerar y revocar los antiguos | Re-verificar el webhook |
| Cloudflare tunel / certificado de origen | Solo si se sospecha del host o de los backups: rotar credenciales del tunel y reemitir el certificado de origen | Interrumpe brevemente el acceso publico |
| Contrasena del superusuario | Ya rotada por ti (2026-09-24) | — |
Verificar tras rotar: login web/panel, restablecer contrasena (correo), chat de soporte (respuesta del asistente), pago de prueba en sandbox, envio de WhatsApp de prueba; y que las credenciales antiguas **ya no funcionan** (invalidadas).

## 4. Backups (§19.2) -- decisiones del usuario (2026-09-24): disco local por ahora, `openssl`, sin secretos en el backup. IMPLEMENTADO (no ejecutado)
| Cambio | Detalle |
|---|---|
| Secretos fuera del backup | `deploy/backup.sh` YA NO copia `.env.production`, `origin.key` ni las credenciales del tunel. `config/<timestamp>/` solo trae `docker-compose.prod.yml` y `nginx.prod.conf`. Los secretos viven unicamente en tu gestor de contrasenas |
| Cifrado | Dump y media se cifran con `openssl enc -aes-256-cbc -pbkdf2 -iter 200000` (archivos `.dump.enc` / `.tar.gz.enc`); antes de borrar el original se verifica que el cifrado **descifra** con la misma clave. La retencion (14 dias) cubre `.enc` y planos |
| Clave | `SINTEL_BACKUP_KEY_FILE` (default `/c/Users/Administrator/sintel_secrets/backup.key`), FUERA de `sintel_backups`. Generarla UNA vez a mano: `mkdir -p /c/Users/Administrator/sintel_secrets && openssl rand -base64 48 > /c/Users/Administrator/sintel_secrets/backup.key && chmod 600 ...` y **guardar una copia en el gestor de contrasenas (sin ella no hay restauracion)**. Sin clave el backup avisa y queda sin cifrar; con `SINTEL_BACKUP_REQUIRE_ENCRYPTION=true` falla |
| Restauracion | `deploy/restore.sh <timestamp>` detecta `.enc`, descifra a un directorio temporal (se borra al salir) y sigue el flujo normal; falla claro si falta la clave o es incorrecta |
| Backups viejos | `deploy/purge_legacy_secret_backups.sh`: dry-run por defecto; con `--yes` borra `.env.production`, `certs/` y `cloudflared/` de los `config/*` anteriores a F15. **Usalo solo cuando esos secretos ya esten en tu gestor** |
| Sigue igual | Destino = el mismo disco local (decision del usuario): **el backup cifrado protege contra lectura, NO contra perdida del host**; la copia externa cifrada queda pendiente para cuando elijas destino. Prueba de restauracion (`restore.sh` sobre base scratch) a hacer por ti y fechar |
Verificacion hecha: solo `bash -n` de sintaxis en los 3 scripts (no se ejecuto ninguno). Primera vez: ejecuta `./deploy/backup.sh` en una ventana tranquila y comprueba que aparecen los `.enc` y que `restore.sh` los descifra en un entorno de prueba, antes de confiar en el.

## 5. Pendiente / fuera de alcance de esta fase
- Ejecutar el escaner (`--history`) tu mismo para tener la huella de "0 hallazgos" fechada; activar el hook.
- Mover `notas.txt` fuera del arbol del repo (o cifrarlo) y comprobar que ningun proceso de backup/sync lo replica.
- F16 (versionado/supply chain: pin de Ollama, modelo por digest, SBOM) es la siguiente fase del plan.
