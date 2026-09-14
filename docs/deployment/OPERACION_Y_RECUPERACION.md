# Sintel E-Commerce — Operación y Recuperación (Producción)

> Complementa `ROADMAP_CLOUDFLARE_TUNNEL.md` (las 22 fases y su historial).
> Este documento es la referencia rápida del día a día: cómo desplegar,
> revisar salud, ver logs, respaldar y restaurar.

## Arquitectura en producción

```
Internet → Cloudflare Edge → Tunnel "sintel-production" → cloudflared (Docker)
    → Nginx (TLS con Origin Certificate, 443) → Django/Daphne (8000, interno)
                                               → Redis, PostgreSQL (internos)
Celery worker + beat (internos, sin puertos)
```

Dominios: `sintel.net.co`, `www.sintel.net.co`, `api.sintel.net.co`,
`panel.sintel.net.co` → todos CNAME al túnel, proxy Cloudflare activado.

Archivo principal: `ecommerce_sintel/docker-compose.prod.yml` (7 servicios:
`redis`, `db`, `django`, `celery_worker`, `celery_beat`, `nginx`, `cloudflared`).

## Ubicación de secretos (todos fuera del repositorio)

| Contenido | Ruta |
|---|---|
| `.env.production` (real) | `ecommerce_sintel/.env.production` (protegido por `.gitignore`, no fuera del repo por convención de Docker Compose, pero nunca se commitea) |
| Certificado de origen Cloudflare | `C:\Users\Administrator\sintel_secrets\certs\origin.pem` / `origin.key` |
| Config + credenciales del túnel | `C:\Users\Administrator\.cloudflared\sintel-production\config.yml` / `<tunnel-id>.json` |
| Certificado de cuenta Cloudflare (CLI) | `C:\Users\Administrator\.cloudflared\cert.pem` |
| Backups | `C:\Users\Administrator\sintel_backups\` |

## Operación diaria

**Desplegar / actualizar tras un cambio de código:**
```bash
cd ecommerce_sintel
./deploy/deploy.sh
```
Reconstruye imágenes, aplica migraciones (automático vía `entrypoint.sh`),
crea el superusuario si no existe, espera a que Django esté `healthy`.

**Ver estado y salud:**
```bash
./deploy/healthcheck.sh
```
Muestra `docker compose ps`, `docker stats`, health interno de Django,
últimas líneas de `logs/nginx/access.log` y `error.log`, y estado del túnel.

**Ver logs de un servicio específico:**
```bash
docker logs sintel_prod_django -f      # Django/Daphne
docker logs sintel_prod_celery_worker -f
docker logs sintel_prod_celery_beat -f
docker logs sintel_prod_cloudflared -f
tail -f logs/nginx/access.log          # Nginx (archivo real, no docker logs)
tail -f logs/nginx/error.log
```

**Apagar / reiniciar todo el stack:**
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production down
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```
⚠️ `down` sin `-v` NO borra los volúmenes (datos persisten). Nunca usar
`down -v` en producción salvo que se quiera borrar todo intencionalmente.

## Backups y restauración

**Manual:**
```bash
./deploy/backup.sh                  # respalda BD + media/KYC + config y valida los archivos
./deploy/restore.sh <timestamp>     # crea snapshot preventivo y luego pide "RESTAURAR"
```

**Automático:** la tarea de Windows `SintelEcommerceBackup` debe ejecutarse con una cuenta de
servicio que tenga acceso al daemon de Docker Desktop; no usar `SYSTEM`, que no puede acceder al
named pipe de Docker en esta instalación. Instalar o actualizar la tarea (solicita credenciales
sin guardarlas en el repositorio):
```powershell
.\deploy\install_backup_task.ps1
```
Después de instalarla, iniciar una ejecución de prueba y comprobar resultado `0` antes de confiar
en la programación diaria de las 3:00 AM:
```powershell
Start-ScheduledTask -TaskName "SintelEcommerceBackup"
Get-ScheduledTask -TaskName "SintelEcommerceBackup"
Get-ScheduledTaskInfo -TaskName "SintelEcommerceBackup"   # ultima ejecucion
```
El script valida cada dump con `pg_restore --list`, valida el archivo de media y evita ejecuciones
simultáneas. Retención: 14 días (`SINTEL_BACKUP_RETENTION_DAYS` en `backup.sh`).

## Seguridad configurada (consolidado)

- **TLS**: Cloudflare Full (Strict) de extremo a extremo — Edge↔Cliente
  (cert. Cloudflare automático) y cloudflared↔Nginx (Origin Certificate,
  15 años, `*.sintel.net.co`+`sintel.net.co`).
- **Django** (`settings/production.py`): `DEBUG=False`, `SECURE_SSL_REDIRECT`,
  `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` (1 año,
  incluye subdominios + preload), `SECURE_PROXY_SSL_HEADER`, `ALLOWED_HOSTS`
  y `CSRF_TRUSTED_ORIGINS` restringidos a los 4 dominios reales (sin
  `localhost`, sin wildcard).
- **Nginx** (`nginx.prod.conf`): rate limiting (20r/s, burst 40), gzip,
  HTTP/2, cabeceras `HSTS`/`X-Frame-Options`/`X-Content-Type-Options`/
  `Referrer-Policy`/`Permissions-Policy`/CSP. Nota: Django también añade
  algunas de estas cabeceras (HSTS, X-Frame-Options) — quedan duplicadas
  pero con el mismo valor, inofensivo.
- **Red**: cero puertos publicados al host salvo lo estrictamente necesario
  (nada — ni siquiera Nginx). `redis`, `postgres`, `celery` inalcanzables
  desde fuera de Docker por diseño, no por regla añadida.
- **Wompi**: deliberadamente en modo `test` — pagos reales deshabilitados
  hasta activar llaves `prod_...` reales en `.env.production` (ver sección
  "Activar pagos reales" abajo).

## Pruebas de despliegue realizadas (2026-07-10)

1. `docker compose config` — archivo completo validado sintácticamente en
   cada fase que lo modificó (2, 3, 16, 17, 18).
2. `nginx -t` con certificados y configs reales montadas — válido.
3. Ciclo real de backup → destrucción de contenedores → restauración,
   contra datos de prueba, con verificación de integridad (fila de BD +
   archivos media/KYC exactos tras restaurar). Dos bugs reales encontrados
   y corregidos en el proceso (ver `ROADMAP_CLOUDFLARE_TUNNEL.md` Fase 19).
4. **Despliegue real del stack completo** (`deploy.sh`): 7 contenedores
   arriba, migraciones aplicadas contra PostgreSQL real, superusuario
   creado. Bug real encontrado y corregido: el healthcheck de Django usaba
   `Host: localhost`, rechazado por `ALLOWED_HOSTS` estricto — se corrigió
   pasando un `Host` header válido en el propio healthcheck.
5. **Prueba real de extremo a extremo vía Internet púbico**: `curl` desde
   este servidor hacia `https://api.sintel.net.co/api/v1/health/` →
   `200 {"status": "ok"}`, atravesando Cloudflare Edge → Tunnel → Nginx
   (TLS con Origin Certificate) → Django. Bug real encontrado y corregido:
   cloudflared verificaba el certificado de origen contra el hostname
   literal `nginx` (del `service:` en `config.yml`), no contra el hostname
   público de cada regla — se corrigió agregando `originServerName`
   explícito por regla.
6. **Hallazgo NO corregido, disclosed y diferido** (decisión del usuario):
   `www.sintel.net.co`, `panel.sintel.net.co` y `sintel.net.co` devuelven
   `404` porque no existe ninguna vista/plantilla Django que sirva el shell
   HTML de la SPA de Vue (`django-vite` con `rollupOptions.input` apuntando
   a JS puro, sin `index.html`). Es una tarea de desarrollo de aplicación
   pre-existente, fuera del alcance de este roadmap de infraestructura —
   ver sección siguiente.

## Cómo se sirve la SPA (Vue) en producción

`frontend/src/apps/admin/main.js` es la app real y única (monta en
`#shop-spa-root`, `vue-router` en modo `history`) — contiene TODAS las
rutas: tienda pública (`/`, `/tienda`, `/mi-cuenta/*`, etc.) y panel
(`/panel/*`). `frontend/src/apps/customer/main.js` es un placeholder muerto,
sin usar.

- **Plantilla shell**: `ecommerce_sintel/templates/spa_shell.html` —
  replica `frontend/index.html` (el HTML real de desarrollo de Vite):
  Bootstrap 5.3.3 + Bootstrap Icons + Google Fonts (Inter) vía CDN, spinner
  de carga inicial, `{% vite_asset 'src/apps/admin/main.js' %}`, monta en
  `#shop-spa-root`. El proyecto NUNCA empaqueta Bootstrap (no es dependencia
  de npm) — depende 100% de esos CDN; si `spa_shell.html` no los incluye,
  navbar/footer/banner cargan sin ningún error pero sin ningún estilo.
  El CSP en `nginx.prod.conf` debe permitir `cdn.jsdelivr.net` y
  `fonts.google*` acorde.
- **URL catch-all**: `ecommerce/urls.py`, última entrada —
  `re_path(r'^(?!api/|admin/|static/|media/).*$', ...)` sirve ese shell
  para cualquier ruta no-API. Vue Router maneja el routing real en el
  cliente.
- **`DJANGO_VITE['default']['static_url_prefix'] = 'panel/js/bundle'`**
  (`settings/base.py`) — necesario porque `collectstatic` preserva la ruta
  completa (`STATICFILES_DIRS = [BASE_DIR / 'static']`), así que los
  archivos quedan en `staticfiles/panel/js/bundle/assets/...`, no en
  `staticfiles/assets/...` como `vite_asset` asume por defecto.
- **`base: '/static/panel/js/bundle/'`** en `vite.config.js` — DEBE coincidir
  con `static_url_prefix` de arriba. Controla las URLs que Vite hornea
  dentro del propio bundle para imports dinámicos (code-splitting por ruta)
  y su precarga de CSS. Con `base: '/'` (valor original), esas URLs
  quedaban sin el prefijo y cada ruta lazy-loaded fallaba con
  `Failed to load module script... MIME type "text/html"` — pantalla en
  blanco real en el navegador, aunque `curl` a la página principal diera
  `200` (bug encontrado solo al revisar la consola del navegador).
- **`frontend/.env.production`**: `VITE_API_BASE_URL=https://api.sintel.net.co/api/v1/`
  — Vite lo usa en tiempo de build (`vite build` = mode production) para
  hornear la URL de la API en el bundle JS. Sin este archivo, el código cae
  al fallback `http://localhost:8000/api/v1/`, que nunca resuelve en el
  navegador de un visitante real. No es secreto (la URL es pública en el
  bundle JS de todas formas) — sí está versionado en git (excepción
  explícita en `.gitignore`/`.dockerignore`, que por regla general excluyen
  `.env.*`).

**Si se agrega una ruta nueva en Vue Router**, no hace falta tocar Django —
el catch-all ya cubre cualquier path no-API. Solo hay que reconstruir el
frontend (`./deploy/deploy.sh`, que corre `npm run build` dentro del
Dockerfile) para que el nuevo bundle se hornee y sirva.

## Activar pagos reales (Wompi)

1. Conseguir llaves `prod_...` reales desde el dashboard de Wompi.
2. Editar `ecommerce_sintel/.env.production`:
   `WOMPI_PUBLIC_KEY`, `WOMPI_PRIVATE_KEY`, `WOMPI_EVENTS_SECRET`,
   `WOMPI_INTEGRITY_SECRET`, `WOMPI_ENVIRONMENT=production`.
3. `./deploy/deploy.sh` (recrea `django`/`celery_worker`/`celery_beat` con
   las nuevas variables).

## Troubleshooting rápido

| Síntoma | Causa probable | Dónde mirar |
|---|---|---|
| `502` en cualquier dominio | cloudflared no puede conectar a Nginx (TLS/SNI, o Nginx caído) | `docker logs sintel_prod_cloudflared` |
| `526 Invalid SSL certificate` | Certificado de origen vencido/mal montado | `docker exec sintel_prod_nginx nginx -t` |
| Django nunca queda `healthy` | `ALLOWED_HOSTS` rechaza el healthcheck, o migraciones fallando | `docker logs sintel_prod_django` |
| `404` en `www`/`panel`/raíz | El catch-all de `urls.py` no está matcheando, o `spa_shell.html` no existe | `docker logs sintel_prod_django` |
| Assets JS/CSS del frontend en `404` | `static_url_prefix` desalineado con `collectstatic`, o falta rebuild | `docker exec sintel_prod_django find /code/staticfiles -iname '*.js'` |
| El sitio carga pero la API nunca responde desde el navegador | `frontend/.env.production` falta o desactualizado (bundle apuntando a `localhost`) | `docker exec sintel_prod_django grep -o 'baseURL:.[^,]*' /code/static/panel/js/bundle/assets/admin-*.js` |
| Emails no salen | Credenciales SMTP o `EMAIL_HOST_PASSWORD` inválida | `docker logs sintel_prod_celery_worker` |
| Backup no corrió anoche | Tarea de Windows fallida | `Get-ScheduledTaskInfo -TaskName SintelEcommerceBackup`, `sintel_backups\backup.log` |
| Outlook/cliente de correo no conecta (`0x800CCC0E` u otro "no se puede conectar al servidor") | DNS de correo roto en Cloudflare — ver "Incidentes resueltos" abajo | `nslookup -type=MX sintel.net.co`, `nslookup -type=A mail.sintel.net.co` |

## Incidentes resueltos

### Correo (`ceo@sintel.net.co` y demás cuentas) dejó de conectar tras migrar el DNS a Cloudflare (2026-07-10)

**Síntoma:** Outlook fallaba con `0x800CCC0E` ("No se puede conectar con el servidor")
al sincronizar `ceo@sintel.net.co`. El correo lo sigue prestando **Colombia
Hosting** (cPanel) — Cloudflare solo administra el DNS del dominio desde la
Fase 5 del roadmap de despliegue, nunca aloja el correo.

**Causa raíz — tres registros DNS quedaron mal tras la migración de
nameservers a Cloudflare** (probablemente por el escaneo automático de zona
al agregar el sitio, no por nada hecho manualmente):

| Registro | Estado roto | Efecto |
|---|---|---|
| `MX` de `sintel.net.co` | Apuntaba a `_dc-mx.00eb2fa97e95.sintel.net.co`, un hostname que **no resolvía a ninguna IP** | Correo entrante sin ruta de entrega |
| `mail.sintel.net.co` | Era un `CNAME` → `sintel.net.co` (¡apuntaba a nuestro propio túnel/sitio web!) | El hostname de conexión de Outlook no resolvía a ningún servidor de correo real |
| `autodiscover.sintel.net.co` | Registro `A` **proxiado** por Cloudflare (nube naranja) | Cloudflare solo soporta HTTP/HTTPS en el proxy — IMAP/SMTP nunca pasan por ahí |

**Fix aplicado** (todo en Cloudflare, dashboard → `sintel.net.co` → DNS):

1. `MX` → corregido a `mail.sintel.net.co`.
2. `mail.sintel.net.co` → cambiado de CNAME a registro **`A`** apuntando a
   `190.8.176.201` (IP real del servidor de Colombia Hosting, confirmada por
   PTR: `marcos.colombiahosting.com.co`), con proxy **DNS only** (nube gris)
   — obligatorio, IMAP/SMTP no son HTTP.
3. Se agregó `_autodiscover._tcp.sintel.net.co` tipo **SRV** →
   `0 0 443 cpanelemaildiscovery.cpanel.net`, DNS only — es el mecanismo
   estándar que recomienda cPanel para autodiscover cuando el DNS del
   dominio vive fuera de sus propios servidores (nuestro caso exacto). Deja
   obsoleto (pero no bloqueante) al registro `autodiscover.sintel.net.co`
   proxiado que quedó de antes.

**Verificación:** `nslookup -type=MX sintel.net.co` → `mail.sintel.net.co`;
`nslookup -type=A mail.sintel.net.co` → `190.8.176.201` (IP real, no rango
de Cloudflare); conexión TCP real confirmada a los puertos 993 (IMAPS) y
587 (SMTP) del servidor.

**Lección para el futuro:** cualquier subdominio de servicios que NO pasen
por el túnel/Nginx (correo, FTP, paneles de terceros) debe quedar
explícitamente en **DNS only** en Cloudflare, nunca proxiado — el proxy
naranja solo sirve para HTTP/HTTPS. Ver también la Fase 5 del roadmap
(`ROADMAP_CLOUDFLARE_TUNNEL.md`), donde ya se había detectado -- pero
correctamente no tocado en ese momento, por no tener aún la información
necesaria -- que `mail`/`ftp` eran registros preexistentes ajenos a este
proyecto de e-commerce.
