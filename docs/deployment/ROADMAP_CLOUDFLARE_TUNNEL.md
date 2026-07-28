# Hoja de Ruta — Publicación Sintel E-Commerce vía Cloudflare Tunnel

> Documento vivo. Es la única fuente de verdad del avance de este despliegue.
> Se actualiza al cerrar cada fase (checkboxes + estado + fecha). No se avanza
> a la fase N+1 sin: (a) cerrar todos los checkboxes de la fase N, (b)
> confirmación explícita del usuario para iniciar la fase N+1.

## Protocolo de ejecución

1. Cada fase se ejecuta **solo** tras confirmación explícita del usuario en el chat.
2. Al terminar una fase se marcan sus checkboxes, se cambia el Estado en la
   tabla global, se anota la fecha, y se resume qué se hizo/qué falta antes de
   pedir permiso para la siguiente.
3. Si una fase revela que hay que tocar algo fuera de su alcance, se anota
   como hallazgo dentro de la fase y se resuelve en la fase que corresponda —
   no se hacen saltos de fase no solicitados.
4. Restricciones duras que aplican a TODAS las fases (no negociables salvo
   instrucción explícita del usuario):
   - No abrir puertos en el router. Todo el tráfico entra por Cloudflare Tunnel.
   - Un único túnel: `Sintel Production`.
   - Solo Cloudflare Tunnel + DNS + SSL Full (Strict) + CDN/caché gratuita.
     Nada de Argo, Load Balancer, Workers, Pages, R2, Zero Trust/Access Premium.
   - `ai_engine`, `sintel_ollama`, `sintel_chromadb` nunca se exponen a Internet
     ni se referencian desde Cloudflare DNS. Permanecen solo en `sintel-network`.
   - Nunca cambiar `DJANGO_SETTINGS_MODULE` ni promover a producción sin
     instrucción explícita (ver `feedback_production_gate` en memoria).
   - Certificado en Nginx = Cloudflare Origin Certificate, nunca Let's Encrypt.
   - Subdominios: solo `www`, `api`, `panel`. Nada de mail/ftp/test/beta/staging/dev/admin/internal.

Leyenda de estado: `PENDIENTE` · `EN CURSO` · `COMPLETADA` · `BLOQUEADA`

## Estado global

| # | Fase | Estado | Fecha cierre |
|---|------|--------|---------------|
| 1 | Auditoría previa | COMPLETADA | 2026-07-10 |
| 2 | Dockerización completa (prod) | COMPLETADA | 2026-07-10 |
| 3 | Red Docker única | COMPLETADA | 2026-07-10 |
| 4 | Cloudflare Tunnel | COMPLETADA | 2026-07-10 |
| 5 | DNS en Colombia Hosting | COMPLETADA | 2026-07-10 |
| 6 | Cloudflare DNS (CNAME) | COMPLETADA | 2026-07-10 |
| 7 | SSL Full (Strict) | COMPLETADA | 2026-07-10 |
| 8 | Certificados (Origin Certificate) | COMPLETADA | 2026-07-10 |
| 9 | Nginx (seguridad + performance) | COMPLETADA | 2026-07-10 |
| 10 | Django producción | COMPLETADA | 2026-07-10 |
| 11 | Daphne (solo interno) | COMPLETADA | 2026-07-10 |
| 12 | Static/Media servidos por Nginx | COMPLETADA | 2026-07-10 |
| 13 | Celery (worker + beat) aislado | COMPLETADA | 2026-07-10 |
| 14 | Redis aislado | COMPLETADA | 2026-07-10 |
| 15 | PostgreSQL aislado | COMPLETADA | 2026-07-10 |
| 16 | Variables `.env.production` | COMPLETADA | 2026-07-10 |
| 17 | Logs locales + rotación | COMPLETADA | 2026-07-10 |
| 18 | Monitoreo básico (sin Prometheus/Grafana) | COMPLETADA | 2026-07-10 |
| 19 | Backups automatizados | COMPLETADA | 2026-07-10 |
| 20 | Seguridad — servicios internos bloqueados | COMPLETADA | 2026-07-10 |
| 21 | Costos mínimos en Cloudflare (verificación) | COMPLETADA | 2026-07-10 |
| 22 | Entregables finales + documentación de operación | COMPLETADA | 2026-07-10 |

**Roadmap COMPLETO.** Sintel E-Commerce está publicado en producción real vía
Cloudflare Tunnel, backend Y frontend verificados end-to-end con TLS válido
en los 4 dominios (`sintel.net.co`, `www`, `api`, `panel`). El gap de
serving de la SPA de Vue (identificado al cerrar la Fase 22) se resolvió a
petición explícita del usuario — ver "Post-roadmap: SPA de Vue en
producción" más abajo.

---

## Snapshot de auditoría inicial (contexto ya revisado, 2026-07-10)

Esto NO reemplaza la Fase 1 formal, pero ya deja hallazgos detectados al leer
el repo, para que la Fase 1 no repita trabajo:

- `ecommerce_sintel/docker-compose.yml` expone actualmente al host: `6380→6379`
  (redis), `5432` (db), `8000` (django), `5173` (frontend vite dev),
  `11434` (ollama), `8200` (chromadb), `8100` (ai_engine), `80` (nginx). En
  producción solo Nginx debe tener un puerto publicado, y ni siquiera ese
  puerto debe llegar directo a Internet (lo recibe `cloudflared` internamente).
- `ecommerce_sintel/Dockerfile` ya compila el frontend Vue dentro de la imagen
  runtime (`frontend-builder` stage → `/code/static/panel/js/bundle`). El
  servicio `frontend` (vite dev server, puerto 5173) es solo de desarrollo y
  **no debe existir** en el compose de producción — Nginx sirve el bundle ya
  construido como estático.
- `ecommerce/settings/production.py` ya tiene `SECURE_SSL_REDIRECT`,
  `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_*`. Faltan
  `SECURE_PROXY_SSL_HEADER` (necesario porque Nginx/cloudflared terminan TLS
  antes de Daphne) y `CSRF_TRUSTED_ORIGINS` con los 3 subdominios.
- `nginx.conf` actual es mínimo (proxy_pass + estáticos). No tiene gzip,
  brotli, http2, cache headers completos, rate limiting ni cabeceras de
  seguridad (CSP, X-Frame-Options, etc.) — la Fase 9 requiere una reescritura
  sustancial, no solo un ajuste.
- No existe ninguna configuración de `cloudflared` en el repo — la Fase 4
  parte de cero (no hay túnel previo que migrar).
- `.env` de desarrollo tiene ~60 variables (Wompi, Nequi, Meta/WhatsApp,
  Google Business, OpenAI/Anthropic/Gemini, JWT, Chroma/Ollama). La Fase 16
  debe separar un `.env.production` real y un `.env.production.example` sin
  secretos, sin tocar el `.env` de desarrollo existente.
- `sintel_ollama` reserva GPU NVIDIA vía `deploy.resources` — confirma que es
  un servicio pesado que jamás debe quedar accesible desde fuera de Docker.

---

## Fase 1 — Auditoría previa ✅ COMPLETADA (2026-07-10)

**Objetivo:** verificar el estado real de docker-compose, variables ENV,
volúmenes, Nginx, Daphne, Redis, Celery, Channels; eliminar configuraciones
duplicadas, certificados antiguos, puertos abiertos innecesarios y
configuración de desarrollo que no deba ir a producción.

- [x] Inventario completo de `docker-compose.yml` actual (servicios, puertos, volúmenes, redes)
- [x] Inventario de `.env` actual: qué variables son de desarrollo puro vs. necesarias en producción
- [x] Revisión de `entrypoint.sh` (migraciones, collectstatic, comportamiento en prod)
- [x] Revisión de `settings/base.py`, `development.py`, `production.py` (`ALLOWED_HOSTS`, `CORS`, `CHANNEL_LAYERS`, `CACHES`)
- [x] Búsqueda de certificados/config TLS antiguos o residuales en el repo
- [x] Búsqueda de configuración de desarrollo filtrada en archivos de producción (DEBUG, `*` en hosts/CORS, credenciales hardcodeadas)
- [x] Listado final de "qué se elimina" y "qué se conserva" antes de tocar nada

### Resultados

**1. `docker-compose.yml`** — 8 servicios: `redis`, `db`, `django`, `frontend`
(vite dev), `celery_worker`, `celery_beat`, `sintel_ollama`, `sintel_chromadb`,
`sintel_ai`, `nginx`. Puertos publicados al host: `6380→6379`, `5432`, `8000`,
`5173`, `11434`, `8200`, `8100`, `80`. Una sola red (`ecommerce_sintel_network`,
bridge). Sin configuraciones duplicadas — un solo compose, no hay que eliminar
nada aquí, solo crear el de producción en Fase 2.

**2. `entrypoint.sh`** — Solo el servicio `daphne` corre `migrate` +
`collectstatic --clear` al arrancar. `DEV_RELOAD=true` envuelve Daphne con
`watchmedo` (polling cada 2s) — **debe ir en `"false"` en producción**
(ya está aislado como variable de entorno, no hace falta tocar el script).

**3. `settings/base.py`** — `SECRET_KEY`/`ALLOWED_HOSTS`/`CORS_ALLOWED_ORIGINS`
ya vienen 100% de `config()` (decouple), sin hardcodear. `CHANNEL_LAYERS` y
`CACHES` ya usan `REDIS_URL` vía env. No hay ningún `ALLOWED_HOSTS = ['*']`
ni CORS wildcard en código — el control real está en las variables de entorno.

**4. Certificados / TLS residuales** — Ninguno. No hay `.pem/.crt/.key/.cert`
en el repo. Nginx aún no tiene bloque `ssl` (coherente: hoy solo sirve HTTP 80).

**5. Configuración de desarrollo filtrada** — Hallazgo relevante: el `.env`
actual tiene `DJANGO_SETTINGS_MODULE=ecommerce.settings.production` **pero
con valores de desarrollo**: `DEBUG=True`, `SECURE_SSL_REDIRECT=False`,
`ALLOWED_HOSTS=localhost,127.0.0.1`, `SECRET_KEY`/`JWT_SECRET_KEY` de
ejemplo ("insecure"/"12345"), `WOMPI_ENVIRONMENT=test`. Es decir: hoy corre
el *módulo* de producción pero con la *postura* de desarrollo. Esto es
consistente con [[feedback_production_gate]] — no se toca `.env` ni
`DJANGO_SETTINGS_MODULE` en esta auditoría; queda registrado para resolverse
explícitamente en la Fase 16 (`.env.production` separado) y Fase 10.

**6. Hallazgos fuera del alcance original de la Fase 1, pero relevantes para fases posteriores:**
   - No existe **ningún `.gitignore`** (ni en la raíz ni en `ecommerce_sintel/`).
     Si en algún momento se hace `git add` amplio, el `.env` con secretos reales
     (Wompi, Gmail app-password, JWT) quedaría trackeado. **Prerequisito duro
     antes de la Fase 16**: crear `.gitignore` con `.env`, `*.pem`, `*.key`, `*.crt`.
   - El repositorio Git local está inicializado pero vacío/no funcional:
     `.git/` solo contiene `info/exclude` (sin `HEAD`, `refs` ni `objects` —
     `git status`/`git log` fallan con "not a git repository"). No bloquea el
     plan de despliegue, pero significa que hoy no hay control de versiones
     real protegiendo el código ni historial de commits. Se deja anotado, sin
     tocarlo (inicializar o reparar git es una decisión del usuario, fuera del
     alcance de este roadmap de infraestructura).
   - `frontend/.env.development` (`VITE_API_BASE_URL=http://localhost:8000/api/v1/`)
     es dev-only y no debe influir en el build de producción (el build de Vite
     para prod ya se hace dentro del `Dockerfile`, stage `frontend-builder`,
     sin depender de este archivo salvo que exista un `.env.production` de Vite
     — a verificar en Fase 2 si el build necesita una URL de API distinta).

### Qué se elimina vs. qué se conserva

| Elemento | Decisión |
|---|---|
| `docker-compose.yml` (desarrollo) | Se conserva tal cual, para uso local. No se toca. |
| `nginx.conf` / `nginx-upgrade-map.conf` | Se conservan como base; en Fase 9 se crea versión de producción (probablemente `nginx.prod.conf`), sin eliminar los actuales. |
| `Dockerfile` (multi-stage) | Se conserva; ya sirve para producción tal cual (target `runtime`). |
| `entrypoint.sh` | Se conserva; el switch `DEV_RELOAD` ya soporta producción sin cambios de código. |
| Certificados antiguos | No aplica — no existen. |
| `.env` actual | Se conserva intacto para desarrollo. Se crea `.env.production` nuevo en Fase 16 (no se sobreescribe el existente). |
| `.gitignore` | No existe — se crea antes de la Fase 16 (paso previo obligatorio). |

## Fase 2 — Dockerización completa (producción) ✅ COMPLETADA (2026-07-10)

**Objetivo:** `docker-compose.prod.yml` con nginx, django, postgres, redis,
celery, celery-beat, cloudflared. Sin ollama/ai_engine/chromadb.

- [x] Crear `docker-compose.prod.yml` (nuevo archivo, no reemplaza el de desarrollo)
- [x] Servicio `django` con `target: runtime`, sin bind mount de código fuente
- [x] Servicio `celery_worker` y `celery_beat` en modo producción (sin `DEV_RELOAD`)
- [x] Sin servicio `frontend` (vite dev) — el bundle ya vive en la imagen runtime
- [x] Sin servicios `sintel_ollama`, `sintel_chromadb`, `sintel_ai`
- [x] `Dockerfile.production` si aplica (o confirmar que el `Dockerfile` actual multi-stage ya sirve tal cual)

### Resultados

Archivo creado: `ecommerce_sintel/docker-compose.prod.yml` (7 servicios:
`redis`, `db`, `django`, `celery_worker`, `celery_beat`, `nginx`, `cloudflared`).

- **Confirmado antes de excluir la IA del stack de producción**: se buscó en
  todo `ecommerce_sintel/**/*.py` cualquier referencia en tiempo de ejecución
  a `ai_engine`/puerto `8100`. Solo aparece en
  `notifications/management/commands/audit_notifications.py`, un comando de
  gestión (herramienta de auditoría, no código de request/response de la app).
  Confirma que Django/Celery en producción **no dependen** de `ai_engine`,
  `ollama` ni `chromadb` en ningún momento — excluirlos es seguro.
  > **[ACTUALIZADO 2026-07-23]** Esta confirmación es de 2026-07-10, **anterior
  > al AI Core** (Fases 1-8, 2026-07-16). Desde entonces `support/services/ai_bridge.py`
  > (usado por el widget de soporte web vía `SupportChatConsumer` y por el bot de
  > WhatsApp vía `notifications/tasks.py`) SÍ hace una llamada HTTP saliente real a
  > `settings.AI_ENGINE_URL/chat` — ya no es cierto que "nada dependa de `ai_engine`"
  > en un sentido literal. La exclusión del stack de IA de `docker-compose.prod.yml`
  > sigue siendo segura porque esa dependencia es **condicional y con degradación
  > controlada**: `ask_ai()` atrapa `requests.RequestException` y devuelve `None` si
  > el motor es inalcanzable (el chat sigue funcionando 100% humano, nunca rompe), y
  > `AI_SUPPORT_CHAT_ENABLED` (gate que decide si se intenta siquiera) tiene
  > `default=False` en `settings/base.py` — confirmado que `.env.production.example`
  > (actualizado 2026-07-20, después de esta fase) documenta explícitamente dejarla
  > sin definir en producción para ese efecto. Si en el futuro se decide desplegar el
  > AI Core a producción, hace falta: (1) agregar `sintel_ai`/`sintel_ollama`/
  > `sintel_chromadb` a `docker-compose.prod.yml` (en `sintel-network`, sin exponer
  > puertos — mismo patrón que el resto), y (2) activar `AI_SUPPORT_CHAT_ENABLED=True`
  > en `.env.production` real — ninguna de las dos cosas está hecha hoy.
- **`Dockerfile.production`: no se crea.** El `Dockerfile` multi-stage
  existente (`builder` → `frontend-builder` → `runtime`) ya produce una
  imagen de producción correcta (usuario no-root, `target: runtime`, bundle
  de Vue horneado). Crear un segundo Dockerfile sería duplicar lo que ya
  existe — se reutiliza el mismo con `target: runtime` en `docker-compose.prod.yml`.
- **`django`/`celery_worker`**: se quitó el bind mount `.:/code` que tiene el
  compose de desarrollo (necesario ahí para hot-reload). En producción el
  código vive horneado en la imagen; solo quedan montados los volúmenes de
  datos persistentes (`staticfiles`, `media`, `beat_schedule`).
  `DEV_RELOAD` no se define — el propio `entrypoint.sh` ya toma `false` por defecto.
- **`nginx`**: sin `ports:`, solo `expose: 80/443` — no se publica ningún
  puerto al host. El único servicio con salida a Internet es `cloudflared`
  (conexión saliente hacia el edge de Cloudflare, sin necesidad de puertos
  publicados ni abiertos en el router).
- **Volúmenes y nombre de proyecto Compose distintos a desarrollo**
  (`name: sintel_production`, volúmenes `sintel_prod_*`, contenedores
  `sintel_prod_*`) para poder correr ambos stacks (dev y prod) en el mismo
  host sin colisión de nombres ni de datos — en línea con
  [[project_docker_entorno_compartido]].
- **Red única `sintel-network`** ya definida en este archivo para los 7
  servicios (adelanta el objetivo de la Fase 3; esa fase ahora es
  principalmente de verificación, no de creación).

### Archivos que este compose referencia pero **aún no existen** (se crean en fases posteriores — el stack no es ejecutable todavía)

| Referencia | Se crea en |
|---|---|
| `.env.production` | Fase 16 |
| ~~`cloudflared/config.yml` + credenciales del túnel~~ | ✅ Fase 4 — pero fuera del repo, en `C:\Users\Administrator\.cloudflared\sintel-production\` (el compose se actualizó para montar esa ruta absoluta, no `./cloudflared`) |
| `certs/` (Cloudflare Origin Certificate) | Fase 8 |
| `nginx.prod.conf` | Fase 9 |

## Fase 3 — Red Docker única ✅ COMPLETADA (2026-07-10)

**Objetivo:** una sola red `sintel-network`; nunca publicar 5432/6379/11434/8200/8100.

- [x] Definir red `sintel-network` en `docker-compose.prod.yml`
- [x] Todos los servicios de producción en esa red, sin `ports:` salvo Nginx (y ese solo accesible por cloudflared)
- [x] Confirmar que `sintel_ollama`/`sintel_chromadb`/`sintel_ai` (si se levantan aparte para uso interno) NO comparten esta red

### Resultados (fase de verificación, sin cambios de código)

- `grep -c "ports:"` sobre `docker-compose.prod.yml` → **0 coincidencias**.
  Ningún servicio de producción publica un puerto al host — ni siquiera
  Nginx (usa `expose: 80/443`, solo alcanzable dentro de `sintel-network`).
  Esto cumple 5432/6379/11434/8200/8100 (y de hecho también 80/443) nunca
  publicados — más estricto de lo que pedía el objetivo original.
- Búsqueda de `sintel-network` / `ecommerce_sintel_network` en todo el
  repositorio: los dos nombres de red aparecen únicamente en sus respectivos
  compose (`docker-compose.prod.yml` usa `sintel-network`;
  `docker-compose.yml` de desarrollo usa `ecommerce_sintel_network`, donde
  viven `sintel_ollama`/`sintel_chromadb`/`sintel_ai`). No existe ningún
  archivo que declare una red `external` compartida entre ambos stacks, así
  que Docker las crea como redes `bridge` completamente aisladas — los
  servicios de IA no tienen ninguna ruta de red hacia `sintel-network`.

## Fase 4 — Cloudflare Tunnel ✅ COMPLETADA (2026-07-10)

**Objetivo:** un único túnel `Sintel Production`, contenedor `cloudflared` en `docker-compose.prod.yml`, todo el tráfico Tunnel → Nginx → apps.

- [x] Crear el túnel en el dashboard/CLI de Cloudflare (requiere acción del usuario: cuenta + `cloudflared tunnel login`)
- [x] Generar credenciales del túnel y guardarlas fuera del repo
- [x] `config.yml` de cloudflared con reglas de ingress hacia `nginx:80`
- [x] Contenedor `cloudflared` en `sintel-network`, sin puertos publicados al host
- [x] Verificar que no se cree más de un túnel

### Resultados

- **Login de `cloudflared`**: requirió varios reintentos. El primer intento
  (autorización desde un navegador en un equipo distinto al servidor) falló
  con `Failed to fetch resource` — cloudflared no pudo escribir el
  certificado automáticamente y ofreció como respaldo la descarga manual del
  archivo. Los primeros intentos de transcribir manualmente ese archivo
  resultaron en un `cert.pem` inválido (solo el cuerpo del certificado, sin
  cabeceras `BEGIN/END` ni la línea de token) — `cloudflared tunnel list`
  lo rechazó con `missing token in the certificate`. Se resolvió cuando el
  usuario localizó y entregó el archivo real con el bloque
  `-----BEGIN ARGO TUNNEL TOKEN-----` (contiene `accountID`, `zoneID`,
  `serviceKey` y `apiToken`), que sí validó correctamente.
- **Hallazgo crítico durante la verificación**: al correr
  `cloudflared tunnel list` con el certificado ya válido, apareció un túnel
  preexistente **`sintel-erp-prod`** (creado 2026-06-17, con conexiones
  activas en el momento de la consulta). El usuario confirmó que es **otro
  sistema Sintel (ERP), no relacionado con este e-commerce** — no se tocó ni
  se modificó de ninguna forma. Se creó un túnel nuevo y separado para este
  proyecto.
- **Túnel creado**: `sintel-production`, ID `a106a654-bbf9-4a6e-ab8a-73f98138d32c`.
  Verificado con `cloudflared tunnel list` que solo existen esos dos túneles
  en la cuenta — ninguno duplicado para este proyecto.
- **Incidente de seguridad evitado**: se intentó por error copiar el archivo
  de credenciales del túnel (`<tunnel-id>.json`, contiene el secreto real)
  dentro de `ecommerce_sintel/cloudflared/` — el clasificador de permisos de
  Claude Code bloqueó la acción señalando correctamente que contradecía el
  propio requisito de esta fase ("guardarlas fuera del repo") y que no había
  `.gitignore` protegiendo el repositorio. Se corrigió el enfoque:
  - Credenciales (`config.yml` + `<tunnel-id>.json`) viven en
    `C:\Users\Administrator\.cloudflared\sintel-production\`, **fuera del
    repositorio por completo** (no en `~/.cloudflared/` directo, para no
    exponer también el `cert.pem` de cuenta al contenedor — principio de
    mínimo privilegio).
  - `docker-compose.prod.yml` monta esa ruta absoluta del host
    (`C:/Users/Administrator/.cloudflared/sintel-production:/etc/cloudflared:ro`)
    en vez de una carpeta del proyecto.
  - Se creó `.gitignore` en la raíz del repo (no existía — hallazgo de la
    Fase 1) como medida defensiva inmediata, cubriendo `.env*`, `*.pem`,
    `*.key`, `*.crt`, `cert.pem`, `cloudflared/`, `certs/`, además de
    patrones estándar de Python/Node. Esto es una desviación puntual y
    justificada del roadmap (no una fase nueva): se adelantó parte de lo
    previsto para la Fase 16 porque el riesgo ya se había materializado una
    vez en esta misma fase.
- **`config.yml`** (en `C:\Users\Administrator\.cloudflared\sintel-production\config.yml`):
  ingress `www.sintel.net.co`, `api.sintel.net.co`, `panel.sintel.net.co` →
  `http://nginx:80` (nombre del servicio Nginx dentro de `sintel-network`),
  catch-all `http_status:404`.
- **Aún no se ha corrido `cloudflared tunnel run`** ni se ha probado
  conectividad real de punta a punta — eso requiere que Nginx/Django estén
  arriba (fases posteriores) y que el DNS apunte al túnel (Fase 6). El
  túnel existe y está configurado, pero todavía no sirve tráfico.
- **Enrutamiento DNS del túnel** (`cloudflared tunnel route dns`) se deja
  deliberadamente para la Fase 6, no se ejecutó aquí.

## Fase 5 — DNS en Colombia Hosting ✅ COMPLETADA (2026-07-10)

**Objetivo:** el dominio `sintel.net.co` mantiene únicamente NS apuntando a Cloudflare; sin subdominios extra.

- [x] Confirmar registrador actual y nameservers en Colombia Hosting
- [x] Apuntar NS del dominio a Cloudflare (acción del usuario en el panel de Colombia Hosting)
- [x] Confirmar que no quedan registros de `mail`/`ftp`/`test`/`beta`/`staging`/`dev`/`admin`/`internal` (con excepción documentada abajo)

### Resultados

- **NS delegado correctamente**: verificado con `nslookup -type=NS sintel.net.co`
  contra el resolver local y contra `1.1.1.1` — ambos devuelven
  `jo.ns.cloudflare.com` y `yadiel.ns.cloudflare.com`. El cambio hecho por
  el usuario en Colombia Hosting quedó bien aplicado.
- **Hallazgo — registros preexistentes que NO se crearon en este proyecto**:
  al verificar el tercer punto del checklist, `sintel.net.co` (raíz),
  `www.sintel.net.co`, `ftp.sintel.net.co` y `mail.sintel.net.co` ya
  resuelven (proxiados por Cloudflare) a `172.67.168.148` / `104.21.26.232`
  — probablemente registros por defecto heredados del hosting compartido en
  Colombia Hosting al importarse la zona a Cloudflare. `api`, `panel`,
  `test`, `beta`, `staging`, `dev`, `admin`, `internal` no tienen registro,
  como se esperaba.
- **Decisión del usuario**: dejar `mail.sintel.net.co` y `ftp.sintel.net.co`
  **intactos** (riesgo real: podría haber correo o FTP en uso; FTP además no
  funciona detrás del proxy de Cloudflare, así que tocarlo sin certeza podría
  romperlo). No forman parte del trabajo de este proyecto — no se tocan en
  ninguna fase posterior salvo instrucción explícita en el futuro.
- **Decisión del usuario**: `sintel.net.co` (raíz) y `www.sintel.net.co` sí
  serán reemplazados en la Fase 6 por el tráfico del túnel — confirmado
  explícitamente, sabiendo que hoy apuntan a un sitio real distinto que
  quedará reemplazado.

## Fase 6 — Cloudflare DNS (CNAME) ✅ COMPLETADA (2026-07-10)

**Objetivo:** `www`, `api`, `panel` como CNAME al túnel, proxy activado, TTL Auto.

- [x] CNAME `www` → túnel (proxied)
- [x] CNAME `api` → túnel (proxied)
- [x] CNAME `panel` → túnel (proxied)
- [x] Confirmar que no hay registros adicionales

### Resultados

Los 3 CNAME se crearon con `cloudflared tunnel route dns sintel-production <host>`
(TTL Auto y proxy activado son el comportamiento por defecto de este comando):

- `www.sintel.net.co` → tenía un registro A preexistente en conflicto; se
  usó `--overwrite-dns` **con confirmación explícita del usuario**, ya
  advertido de que reemplazaría el sitio que hoy sirve ahí.
- `api.sintel.net.co` → creado sin conflicto (no existía).
- `panel.sintel.net.co` → creado sin conflicto (no existía).

**Adición fuera del alcance original de la Fase 6, con doble confirmación
explícita del usuario**: el dominio raíz `sintel.net.co` (sin `www`) también
se enruta al túnel. El plan original solo mencionaba `www`/`api`/`panel`,
pero el usuario confirmó dos veces (en Fase 5 y de nuevo aquí) que quería
que la raíz sirviera el mismo sitio. `cloudflared tunnel route dns` se negó
a sobrescribir el registro A de la raíz incluso con `--overwrite-dns`
(a diferencia de `www`, que sí aceptó el overwrite); el usuario borró el
registro A conflictivo manualmente desde el dashboard de Cloudflare y el
comando se reintentó con éxito.

Verificación final (`nslookup` contra `1.1.1.1`): `sintel.net.co`, `www`,
`api` y `panel` resuelven los 4 a las mismas IPs proxiadas de Cloudflare
(`172.67.168.148` / `104.21.26.232`). `mail.sintel.net.co` y
`ftp.sintel.net.co` verificados sin cambios, tal como se decidió en la
Fase 5. `cloudflared tunnel list` confirma que siguen existiendo
exactamente los mismos 2 túneles (`sintel-erp-prod` intacto,
`sintel-production` sin duplicados).

**Nota:** estos registros ya enrutan tráfico hacia el túnel, pero el túnel
(`cloudflared`) todavía no está corriendo como contenedor (eso ocurre cuando
se levante `docker-compose.prod.yml` en una fase posterior) — hasta entonces
estos hostnames no responderán con el sitio (error 502/523 de Cloudflare es
el comportamiento esperado por ahora, no es un fallo de esta fase).

## Fase 7 — SSL Full (Strict) ✅ COMPLETADA (2026-07-10)

- [x] Configurar modo SSL/TLS = Full (Strict) en Cloudflare (nunca Flexible/Off)
- [~] Verificar que Nginx sirve HTTPS válido hacia el edge de Cloudflare (depende de Fase 8 — **no verificable todavía**)

### Resultados

Cambio manual del usuario en el dashboard (SSL/TLS → Overview → Full (strict)) —
no verificable por API/CLI en esta sesión (no hay token de Cloudflare con permisos
de zona configurado, solo el certificado de gestión del túnel). Se confirma
por declaración directa del usuario.

**Importante:** con Full (Strict) activo pero sin certificado de origen aún
en Nginx (Fase 8) ni Nginx corriendo (fases posteriores), visitar cualquiera
de los 4 hostnames por HTTPS dará error `526 Invalid SSL certificate` — es
el comportamiento esperado en este punto, no una falla. La verificación real
de HTTPS extremo a extremo queda pendiente hasta que Fase 8 y el despliegue
del stack estén completos.

## Fase 8 — Certificados (Cloudflare Origin Certificate) ✅ COMPLETADA (2026-07-10)

- [x] Generar Origin Certificate en Cloudflare (15 años, cubre `*.sintel.net.co` y `sintel.net.co`)
- [x] Guardar cert/key fuera del repo (o como secret montado, nunca commiteado)
- [~] Configurar Nginx para usarlo en `listen 443 ssl` — **diferido a la Fase 9**, donde se escribe `nginx.prod.conf` completo (evita escribir configuración parcial que la Fase 9 tendría que reescribir)

### Resultados

- **Mismo problema de transcripción que en la Fase 4**: el certificado y la
  llave privada generados por el usuario en el dashboard de Cloudflare
  llegaron sin las cabeceras PEM (`-----BEGIN/END CERTIFICATE-----` /
  `-----BEGIN/END PRIVATE KEY-----`) — solo el cuerpo base64. A diferencia
  de la Fase 4, esta vez se reconstruyeron directamente sin necesidad de
  pedirle al usuario que reintentara: el cuerpo base64 de la llave decodifica
  a una estructura `PrivateKeyInfo` (PKCS#8: `SEQUENCE { version, rsaEncryption
  AlgorithmIdentifier, OCTET STRING }`), lo que identifica inequívocamente la
  cabecera correcta como `-----BEGIN PRIVATE KEY-----` (no `RSA PRIVATE KEY`/PKCS#1).
- **Validado con OpenSSL** antes de dar la fase por cerrada:
  - Emisor: `CloudFlare Origin SSL Certificate Authority` ✅
  - SAN: `DNS:*.sintel.net.co, DNS:sintel.net.co` ✅ (wildcard cubre www/api/panel con un solo certificado)
  - Vigencia: `2026-07-10` → `2041-07-06` (~15 años, la máxima disponible) ✅
  - Modulus de la llave privada coincide exactamente con el del certificado (par válido) ✅
- **Ubicación final**: `C:\Users\Administrator\sintel_secrets\certs\origin.pem`
  y `origin.key` — fuera del repositorio, mismo patrón que las credenciales
  del túnel (Fase 4). `docker-compose.prod.yml` ya se actualizó para montar
  esta ruta absoluta en el servicio `nginx` (`/etc/nginx/certs`, read-only).
- **Incidente repetido y resuelto**: el usuario guardó también una copia de
  ambos archivos directamente en la **raíz del repositorio**
  (`ecommerce_sintel_rest\origin.pem` / `origin.key`) — mismo patrón de
  riesgo que con las credenciales del túnel en la Fase 4. Se verificó el
  contenido, se confirmó con el usuario, y se eliminaron esas dos copias del
  repo. La copia válida y única sobrevive únicamente en `sintel_secrets\certs\`.

## Fase 9 — Nginx (seguridad + performance) ✅ COMPLETADA (2026-07-10)

**Objetivo:** toda la seguridad concentrada en Nginx.

- [x] gzip
- [x] brotli (si la imagen/base lo soporta; si no, documentar por qué se omite) — **omitido, documentado**
- [x] http2
- [x] cache de estáticos (ya hay `expires`/`Cache-Control`, revisar y completar con `etag`)
- [x] security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- [x] `client_max_body_size` (ya existe en 50M, confirmar valor correcto para producción)
- [x] rate limiting (`limit_req_zone`)
- [x] confirmar que sigue soportando WebSocket (Channels) sin romper `proxy_set_header Upgrade/Connection`

### Resultados

Archivo creado: `ecommerce_sintel/nginx.prod.conf`. Validado con
`nginx -t` dentro de un contenedor `nginx:1.26-alpine` real, montando el
archivo, `nginx-upgrade-map.conf` y los certificados de
`sintel_secrets/certs/` — **`configuration file test is successful`**.

- **HTTP/2**: confirmado disponible verificando `nginx -V` de la imagen base
  (`--with-http_v2_module` presente, y hasta `--with-http_v3_module`).
  Activado con la sintaxis moderna `listen 443 ssl; http2 on;` (la forma
  antigua `listen 443 ssl http2;` está deprecada desde nginx 1.25.1).
- **Brotli: omitido a propósito.** `nginx -V` confirma que la imagen oficial
  `nginx:1.26-alpine` **no** trae `ngx_http_brotli_module` compilado, y no
  existe como paquete `apk` oficial — requeriría compilar Nginx desde código
  fuente o cambiar a una imagen no oficial, lo cual añade mantenimiento
  (rebuilds, parches de seguridad manuales) no justificado para el beneficio
  marginal sobre gzip en este proyecto. Se usa `gzip` (sí incluido) con
  `gzip_types` cubriendo JSON/JS/CSS/SVG/fuentes — mismo objetivo de
  compresión.
- **TLS en el tramo interno `cloudflared → nginx`**: se decidió (no estaba
  explícito en el plan original, que solo hablaba del certificado en Nginx)
  que este tramo también use HTTPS con el Origin Certificate de la Fase 8,
  coherente con el modo SSL Full (Strict) activado en la Fase 7 — evita que
  "Full Strict" quede aplicado solo de cara al visitante y no de extremo a
  extremo. Se actualizó `config.yml` del túnel
  (`C:\Users\Administrator\.cloudflared\sintel-production\config.yml`):
  `service: https://nginx:443` en las 4 reglas de ingress (la verificación
  del certificado usa por defecto el `hostname` de cada regla como SNI, que
  coincide con el SAN wildcard del Origin Certificate).
- **Corrección de un vacío real encontrado**: `config.yml` del túnel nunca
  tenía una regla de ingress para el dominio raíz `sintel.net.co` (solo
  www/api/panel), a pesar de que en la Fase 6 sí se enrutó ese hostname por
  DNS hacia el túnel. Sin esta corrección, las visitas a `sintel.net.co`
  hubieran caído en el catch-all `http_status:404` del túnel. Se agregó la
  regla faltante.
- **Cabeceras de seguridad**: `HSTS`, `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy` y una `Content-Security-Policy` de
  partida (permite el widget de Wompi en `checkout.wompi.co` y WebSocket hacia
  `api.sintel.net.co`). **Advertencia honesta**: la CSP no se ha probado contra
  el SPA real en un navegador (no hay stack corriendo todavía) — es la mejor
  aproximación posible con la información disponible del proyecto (Wompi,
  Channels), pero puede necesitar ajustes en la Fase 22 (pruebas de despliegue)
  si el navegador bloquea algún recurso legítimo no anticipado aquí.
- **HSTS duplicado (nota menor, no bloqueante)**: `settings/production.py`
  ya activa `SECURE_HSTS_SECONDS` en Django. Con esta fase, Nginx *también*
  añade la cabecera para que `/static/` y `/media/` (que Django nunca ve)
  la lleven igual. Para las respuestas que sí pasan por Django, esto podría
  producir dos cabeceras `Strict-Transport-Security` idénticas — no rompe
  nada en la práctica (los navegadores toleran el valor repetido), pero se
  deja anotado por si se prefiere desactivar la de Django en la Fase 10.
- **Rate limiting**: `limit_req_zone` por IP (20r/s, burst 40, nodelay) en
  la zona compartida `sintel_limit`, aplicado a `location /`. No afecta la
  duración de conexiones WebSocket ya establecidas (Channels), solo la tasa
  de solicitudes/conexiones nuevas.
- **WebSocket**: se mantuvieron intactos `proxy_set_header Upgrade $http_upgrade`
  y `proxy_set_header Connection $connection_upgrade` (vía `00-upgrade-map.conf`,
  sin cambios) y `proxy_read_timeout 86400` para conexiones largas de Channels.

## Fase 10 — Django producción ✅ COMPLETADA (2026-07-10)

- [~] `DEBUG=False` confirmado vía `.env.production` — código ya correcto (`default=False`); el valor real depende de que la Fase 16 cree `.env.production` sin `DEBUG=True`
- [x] `SECURE_SSL_REDIRECT` (ya existía, `default=True` confirmado)
- [x] `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` (ya existían)
- [x] `SECURE_HSTS_SECONDS` (ya existía)
- [x] `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` (agregado — necesario por Nginx/cloudflared)
- [~] `ALLOWED_HOSTS` con `sintel.net.co, www.sintel.net.co, api.sintel.net.co, panel.sintel.net.co` — código ya lee de env (`base.py`, sin cambios necesarios); los valores reales se fijan en Fase 16
- [x] `CSRF_TRUSTED_ORIGINS` con los subdominios en `https://` (agregado, lee de env)

### Resultados

Editado `ecommerce/settings/production.py`, dos adiciones:

```python
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [
    origin for origin in config('CSRF_TRUSTED_ORIGINS', default='').split(',') if origin
]
```

- **`SECURE_PROXY_SSL_HEADER`**: sin esto, Django ve toda request como HTTP
  plano (Nginx/cloudflared terminan TLS antes de llegar a Daphne) y
  `SECURE_SSL_REDIRECT=True` habría causado un bucle infinito de redirects
  en producción real.
- **`CSRF_TRUSTED_ORIGINS`**: se implementó leyendo de variable de entorno
  (no hardcodeado en el código) — mismo patrón que `ALLOWED_HOSTS` en
  `base.py` y consistente con la regla del proyecto ("variables sensibles
  vía `env()`, nunca hardcodeadas en settings", ver `ecommerce/CLAUDE.md`).
  Sin valor por defecto: si `.env.production` no la define, queda como
  lista vacía (falla cerrado, no abierto).
- **Validado con `python -m py_compile`**: sin errores de sintaxis.
- **`ALLOWED_HOSTS` y `DEBUG` reales**: el código en `base.py`/`production.py`
  ya estaba correcto (ambos leen de `config()`, sin hardcodear). Lo único
  pendiente es que la Fase 16 escriba esos valores correctamente en
  `.env.production` — no requería cambios de código en esta fase.
- **Nota de la Fase 9 (HSTS duplicado)**: se decidió no tocarlo — Django
  sigue enviando `SECURE_HSTS_SECONDS` como pide explícitamente esta misma
  fase; el duplicado con el header de Nginx es cosmético, no funcional.

## Fase 11 — Daphne (solo interno) ✅ COMPLETADA (2026-07-10)

- [x] Confirmar que Daphne solo escucha `8000` dentro del contenedor
- [x] Confirmar que `docker-compose.prod.yml` NO publica `8000` al host
- [x] Solo Nginx accede a `django:8000` vía la red interna

### Resultados (fase de verificación, sin cambios de código)

- `Dockerfile`: `EXPOSE 8000` + `CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", ...]` — Daphne escucha en el puerto 8000 dentro del contenedor, sin cambios necesarios.
- `docker-compose.prod.yml`: el servicio `django` no tiene ninguna directiva `ports:` ni `expose:` — la única mención de `8000` es el `healthcheck` (`curl http://localhost:8000/...`), que corre *dentro* del propio contenedor y nunca toca la red del host.
- `nginx.prod.conf`: `upstream django { server django:8000; }` — único punto de acceso a Daphne, resuelto por nombre de servicio dentro de `sintel-network`.

## Fase 12 — Static/Media servidos por Nginx ✅ COMPLETADA (2026-07-10)

- [x] Confirmar volumen `staticfiles`/`media` compartido entre `django` y `nginx` en el compose de producción
- [x] `collectstatic` corre en el `entrypoint.sh`/build, no en cada request
- [x] Nginx sirve `/static/` y `/media/` directamente (ya está en `nginx.conf`, validar en el compose de prod)

### Resultados (fase de verificación, sin cambios de código)

- `sintel_prod_static_volume` y `sintel_prod_media_volume`: montados
  read-write en `django` (y `media` también en `celery_worker`, para tareas
  que generan/leen archivos), y read-only en `nginx` — mismos volúmenes
  nombrados en los tres servicios.
- `entrypoint.sh`: `collectstatic --noinput --clear` corre una sola vez, solo
  cuando arranca el servicio `daphne`, no en cada request.
- `nginx.prod.conf`: `alias /code/staticfiles/` y `alias /code/media/`
  coinciden exactamente con los mountpoints de los volúmenes — Nginx sirve
  ambos directamente sin pasar por Django.

## Fase 13 — Celery aislado ✅ COMPLETADA (2026-07-10)

- [x] `celery_worker` y `celery_beat` en `docker-compose.prod.yml`, sin puertos publicados
- [x] Confirmar colas (`default,marketing,notifications`) y `DatabaseScheduler` igual que en desarrollo

### Resultados (fase de verificación, sin cambios de código)

- Sin `ports:` en `celery_worker` ni `celery_beat` (confirmado por búsqueda dirigida en el archivo).
- Comandos idénticos a desarrollo:
  `celery -A ecommerce worker --loglevel=info --concurrency=4 -Q default,marketing,notifications`
  y `celery -A ecommerce beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler`.

## Fase 14 — Redis aislado ✅ COMPLETADA (2026-07-10)

- [x] Redis en `sintel-network`, sin `ports:` publicados al host
- [~] `REDIS_URL` interno (`redis://redis:6379`) en `.env.production` — código ya lo lee vía `config()`; el valor real se fija en Fase 16

### Resultados (fase de verificación, sin cambios de código)

Servicio `redis` en `docker-compose.prod.yml`: sin `ports:`, solo `networks: [sintel-network]`. `CHANNEL_LAYERS`, `CACHES` y `CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` en `settings/base.py` ya leen `REDIS_URL` desde `config()` — sin cambios de código necesarios, solo falta que `.env.production` (Fase 16) defina `REDIS_URL=redis://redis:6379/0`.

## Fase 15 — PostgreSQL aislado ✅ COMPLETADA (2026-07-10)

- [x] Postgres en `sintel-network`, sin `5432` publicado
- [~] Confirmar estrategia de respaldo local programado (enlaza con Fase 19) — enlace confirmado, implementación real en Fase 19

### Resultados

Servicio `db` en `docker-compose.prod.yml`: sin `ports:`, solo `networks: [sintel-network]` — `5432` nunca publicado al host. Volumen `sintel_prod_postgres_data` persiste los datos. El script de respaldo (`pg_dump` programado) se implementa en la Fase 19; aquí solo se confirma que la topología (contenedor aislado + volumen nombrado) es compatible con esa estrategia.

## Fase 16 — Variables `.env.production` ✅ COMPLETADA (2026-07-10)

- [x] Crear `.env.production` (real, protegido por `.gitignore` — a diferencia de cloudflared/certs, este SÍ vive dentro de `ecommerce_sintel/`, igual que el `.env` de desarrollo, pero cubierto por el `.gitignore` creado en Fase 4)
- [x] Crear `.env.production.example` (plantilla sin secretos, sí versionable)
- [x] Confirmar que ningún secreto queda en `docker-compose.prod.yml` ni en `settings.py`

### Decisiones tomadas con el usuario

- **Wompi**: se mantiene en modo `test` (llaves `pub_test_.../prv_test_...`)
  para este primer despliegue — el sitio queda publicado y funcional pero
  los pagos reales quedan deshabilitados hasta activar llaves `prod_...`
  reales más adelante. Decisión explícita del usuario, no un olvido.
- **Nequi**: sin configurar (placeholders vacíos) — integración inactiva,
  decisión explícita del usuario.
- **Secretos de infraestructura generados por Claude** (con `secrets` de
  Python, no reutilizados de desarrollo): `SECRET_KEY`, `JWT_SECRET_KEY`,
  `DB_PASSWORD`, `DJANGO_SUPERUSER_PASSWORD` — mostrados una única vez al
  usuario en el chat para que los guarde en su gestor de contraseñas (no se
  vuelven a imprimir en este documento).
- **Email SMTP**: se reutilizan las credenciales de Gmail ya usadas en
  desarrollo (`sintel.technology@gmail.com`) — son credenciales reales
  funcionales, no de prueba, así que no había razón para generar otras.
- **`FRONTEND_BASE_URL`**: variable que no existía en el `.env` de
  desarrollo (usa el default `http://localhost:5173` de `base.py`) — se
  agregó explícitamente en `.env.production` como
  `https://www.sintel.net.co` porque `base.py` la usa para armar enlaces en
  emails (ej. verificación de cuenta); sin esto, los emails de producción
  habrían apuntado a `localhost`.
- **Variables del AI Engine omitidas** (`LLM_PROVIDER`, `OLLAMA_BASE_URL`,
  `CHROMA_HOST`, etc.): no se incluyeron en `.env.production` — confirmado
  en la Fase 2 que nada en el stack de producción (Django/Celery) las lee en
  tiempo de ejecución, y `ollama`/`chromadb`/`sintel_ai` no forman parte de
  `docker-compose.prod.yml`.

### Hallazgos y correcciones reales encontrados en esta fase

- **Volumen faltante para documentos KYC**: `docker-compose.prod.yml` no
  tenía ningún volumen para `/code/private_media/kyc` (almacenamiento de
  documentos de identidad de los usuarios, fuera de `MEDIA_ROOT` a propósito
  según `settings/base.py`). Sin corregirlo, cualquier recreación del
  contenedor `django` (rebuild, restart tras actualizar imagen) habría
  **borrado esos documentos**. Se agregó `sintel_prod_kyc_volume` montado en
  `django` (`/code/private_media/kyc`).
- **Bug real de mecánica de Docker Compose**: el servicio `db` usa
  sustitución `${DB_NAME}`/`${DB_USER}`/`${DB_PASSWORD}` en su bloque
  `environment`. Docker Compose solo resuelve ese estilo de variable desde
  un archivo literalmente llamado `.env` o desde el flag `--env-file` — el
  `env_file: .env.production` que usan `django`/`celery_worker`/`celery_beat`
  **no alimenta esa sustitución** (son dos mecanismos distintos de Compose).
  Sin corregirlo, Postgres habría arrancado con credenciales vacías. Se
  verificó con `docker compose -f docker-compose.prod.yml --env-file
  .env.production config` que las tres variables resuelven correctamente, y
  se agregó una advertencia prominente al inicio de `docker-compose.prod.yml`
  con el comando exacto a usar siempre (`--env-file .env.production`).
  Este comando también validó que **todo el archivo `docker-compose.prod.yml`
  es sintácticamente válido** de punta a punta (bonus de esta verificación).
- **`.gitignore` verificado con una prueba real** (repo temporal aislado,
  sin tocar el repo del proyecto): `git add -A` sobre una copia de prueba
  con `.env`, `.env.production`, `cert.pem`, `origin.key` y los `.example`
  correspondientes — confirmado que solo los `.example` y el propio
  `.gitignore` quedan en stage; los secretos reales quedan excluidos.
- **Sin secretos en `docker-compose.prod.yml` ni en `settings.py`**:
  confirmado — el compose solo referencia nombres de variables (`${DB_NAME}`,
  `env_file: .env.production`), nunca valores; `settings/*.py` solo usa
  `config()` de `decouple`, sin ningún valor hardcodeado.

## Fase 17 — Logs locales + rotación ✅ COMPLETADA (2026-07-10)

- [~] Estructura `logs/nginx/`, `logs/django/`, `logs/celery/`, `logs/cloudflared/` — **decisión de alcance disclosed abajo**: solo `logs/nginx/` se implementó como carpeta de archivos reales
- [~] Volúmenes de log montados desde cada contenedor — nginx sí (bind mount); el resto usa el almacenamiento interno rotado de Docker, no una carpeta montada
- [x] Rotación automática (`logrotate` o equivalente en Docker) — **para los 7 servicios**, vía driver nativo de Docker

### Decisión de alcance (disclosed, no un olvido)

`logrotate` no es una herramienta práctica en este host Windows (no está
disponible de forma nativa fuera de WSL, y añadirlo solo para esto sería un
proceso extra que mantener). Se optó por el mecanismo nativo de Docker en su
lugar, más simple y consistente entre servicios:

```yaml
x-logging: &default-logging
  driver: json-file
  options:
    max-size: "10m"
    max-file: "5"
```

Aplicado a los 7 servicios (`redis`, `db`, `django`, `celery_worker`,
`celery_beat`, `nginx`, `cloudflared`) vía anchor YAML (evita repetir el
bloque 7 veces). Máximo 50MB por servicio (10MB × 5 archivos), el log más
viejo se descarta automáticamente — satisface "rotación automática" sin
herramientas externas.

**Solo Nginx tiene carpeta de archivos reales en el host**
(`ecommerce_sintel/logs/nginx/`, montada en `docker-compose.prod.yml`).
Se verificó con `docker run ... nginx:1.26-alpine ls -la /var/log/nginx/`
que la imagen oficial symlinkea `access.log -> /dev/stdout` y
`error.log -> /dev/stderr` por defecto. Al montar `./logs/nginx` sobre ese
directorio, esos symlinks se reemplazan por el directorio del host, y Nginx
empieza a escribir archivos reales ahí automáticamente — **no hizo falta
tocar `nginx.prod.conf`**, el comportamiento por defecto ya apunta a esas
rutas. Como efecto colateral esperado, `docker logs sintel_prod_nginx` deja
de mostrar accesos/errores (el symlink a stdout ya no existe) — esto es
coherente con la Fase 18 del plan original, que ya trata "Nginx logs" como
un punto de revisión aparte de "docker logs", no mezclado con él.

`django`, `celery_worker`, `celery_beat` y `cloudflared` **no** tienen una
carpeta `logs/<servicio>/` dedicada — sus logs se revisan vía `docker logs
<contenedor>`, respaldados por la rotación de Docker ya configurada arriba
(los archivos rotados sí existen físicamente en el disco de la VM de Docker
Desktop, es almacenamiento local igual, solo que no expuesto como carpeta
del proyecto). Se evitó configurar `--logfile` en Celery o cloudflared para
escribir archivos adicionales porque son flags no probados en este entorno
todavía (el stack completo no está corriendo aún) — el riesgo de introducir
un flag mal formado que rompa esos servicios en el primer arranque real no
se justificaba frente al beneficio. Si el usuario prefiere logs de archivo
dedicados para estos tres servicios más adelante, es un ajuste incremental
sencillo una vez el stack esté validado en vivo (Fase 22).

Se agregó `logs/` al `.gitignore` (contenido de runtime, no versionable).

### Validación

- `nginx -t` (con el nuevo volumen de logs montado): configuración válida.
- `docker compose -f docker-compose.prod.yml --env-file .env.production config --quiet`: sin errores — confirma que el archivo completo (con los 7 bloques `logging:` nuevos) sigue siendo válido de punta a punta.

## Fase 18 — Monitoreo básico ✅ COMPLETADA (2026-07-10)

- [x] Healthchecks de cada servicio en `docker-compose.prod.yml` — 5 de 7 con healthcheck activo, 2 con excepción justificada abajo
- [x] Confirmar que `docker logs`/`docker stats` son suficientes (sin Prometheus/Grafana en esta fase)

### Resultados

Estado final de healthchecks por servicio:

| Servicio | Healthcheck | Método |
|---|---|---|
| `redis` | ✅ (ya existía) | `redis-cli ping` |
| `db` | ✅ (ya existía) | `pg_isready` |
| `django` | ✅ (ya existía) | `curl /api/v1/health/` |
| `nginx` | ✅ agregado esta fase | `curl -f http://localhost/` (puerto 80, el redirect 301 a HTTPS cuenta como éxito para `curl -f`; se eligió a propósito para no depender de `ALLOWED_HOSTS`/TLS de Django) |
| `celery_worker` | ✅ agregado esta fase | `celery -A ecommerce inspect ping` |
| `celery_beat` | ⚠️ sin healthcheck — justificado | ver abajo |
| `cloudflared` | ⚠️ sin healthcheck — justificado | ver abajo |

**`celery_beat` sin healthcheck activo**: a diferencia de un worker, `beat`
es un scheduler sin comando `inspect`/`ping` equivalente — no expone una
interfaz para consultar "¿estoy sano?" más allá de que el proceso siga
vivo. Se decidió no inventar un chequeo débil (ej. verificar que un archivo
se modificó "recientemente") por ser más ruido que señal. `restart:
unless-stopped` ya cubre el caso real que importa: si el proceso muere,
Docker lo reinicia solo.

**`cloudflared` sin healthcheck activo — verificado, no es pereza**: se
intentó usar `curl`/`wget`/`sh` dentro de la imagen oficial
`cloudflare/cloudflared:latest` y **ninguno de los tres existe** (imagen
minimalista sin shell, confirmado con
`docker run --entrypoint sh cloudflare/cloudflared:latest` → `exec: "sh":
executable file not found in $PATH`). Sin shell no hay forma de ejecutar un
`CMD-SHELL` healthcheck, y sin curl/wget no hay forma de golpear el
endpoint `/ready` de su servidor de métricas (que sí existe vía la flag
`--metrics`, confirmada en `cloudflared tunnel help run`, pero es
inalcanzable desde dentro del propio contenedor sin herramientas HTTP). Se
documenta como limitación real de la imagen, no una omisión. `restart:
unless-stopped` cubre el mismo caso que en `celery_beat`.

**Monitoreo sin Prometheus/Grafana**: confirmado que el conjunto
`docker logs <contenedor>` + `docker stats` + los 5 healthchecks activos +
los archivos de `logs/nginx/` (Fase 17) es suficiente para esta fase del
proyecto — no se instaló nada adicional, tal como pide el plan.

### Validación

`docker compose -f docker-compose.prod.yml --env-file .env.production config --quiet`
sin errores tras agregar los dos healthchecks nuevos.

## Fase 19 — Backups automatizados ✅ COMPLETADA (2026-07-10)

- [x] Script de backup de PostgreSQL (dump programado, almacenamiento local)
- [x] Script de backup de `media/`
- [x] Backup de `.env.production` y certificados (almacenamiento local seguro, no en Git)
- [x] Backup de `docker-compose.prod.yml`
- [x] Script de restore documentado y **probado de punta a punta** (no solo escrito)

### Resultados

Archivos creados: `ecommerce_sintel/deploy/backup.sh` y `ecommerce_sintel/deploy/restore.sh`.
Almacenamiento local en `C:\Users\Administrator\sintel_backups\` (fuera del
repositorio, mismo patrón que cloudflared/certs — contiene dumps de BD y
documentos KYC, son datos sensibles).

- **`backup.sh`**: `pg_dump --format=custom` de PostgreSQL, `tar.gz` de
  `media/` + `private_media/` (KYC incluido) vía un contenedor `alpine`
  temporal con `--volumes-from django`, copia de `.env.production`,
  `docker-compose.prod.yml`, `nginx.prod.conf`, certificados de origen y
  config del túnel a una carpeta timestamped. Retención de 14 días
  (configurable vía `SINTEL_BACKUP_RETENTION_DAYS`) con `find -mtime -delete`.
- **`restore.sh`**: `pg_restore --clean --if-exists`, restaura el tar de
  media/KYC, reinicia `django`/`celery_worker`/`celery_beat`. Requiere
  confirmación interactiva explícita (escribir `RESTAURAR`) antes de
  sobreescribir datos — es una operación destructiva por diseño.

### Prueba real de punta a punta (no solo escrito, sino ejecutado)

Dado que un script de restauración roto solo se descubre en una emergencia
real, se probó el ciclo completo contra contenedores desechables (mismos
nombres que usan los scripts en producción, para probar el código exacto
que se va a usar):

1. Contenedores de prueba `sintel_prod_db` (con una tabla y una fila) y
   `sintel_prod_django` (con un archivo en `media/` y otro en
   `private_media/kyc/`).
2. `backup.sh` ejecutado contra ellos → **falló en el primer intento**:
   bug real de compatibilidad Windows/Git Bash (MSYS2 traduce
   automáticamente rutas del lado del contenedor como `/backup_out` en
   `docker run -v host:/backup_out` como si fueran rutas de host,
   corrompiéndolas a `C:/Program Files/Git/backup_out`). Corregido con
   `export MSYS_NO_PATHCONV=1` al inicio de ambos scripts (no-op inofensivo
   si algún día corren en Linux real).
3. Contenedores destruidos y recreados **completamente vacíos** (BD sin la
   tabla, volúmenes de media/kyc nuevos y vacíos) — para probar que
   `restore.sh` repuebla los datos desde el backup, no que "ya estaban ahí".
4. `restore.sh` ejecutado → **segundo bug real encontrado**: el paso final
   (`docker restart django celery_worker celery_beat` en un solo comando
   atómico) fallaba por completo si cualquiera de los tres contenedores no
   existía/no corría — en un incidente real, si `celery_beat` estuviera
   caído por una razón no relacionada, el script habría reportado "fallo"
   aunque la restauración de BD y media (lo crítico) ya hubiera funcionado
   correctamente. Corregido: reinicio uno por uno con manejo de error
   individual, solo avisa por los que fallan sin abortar el resto.
5. Verificación final: `SELECT * FROM sanity_check` devolvió la fila
   original: `id=1, msg='hola backup test'`; `cat` de los archivos
   restaurados en `media/` y `private_media/kyc/` devolvió el contenido
   exacto original. **Integridad de datos confirmada de extremo a extremo.**
6. Limpieza completa de contenedores, volúmenes y directorio de backup de
   prueba — no queda ningún residuo de la prueba en el sistema.

### Automatización real (no solo el script)

Se registró una **tarea programada de Windows** (`Register-ScheduledTask`,
ya que `logrotate`/`cron` no aplican en este host Windows):

- Nombre: `SintelEcommerceBackup`
- Trigger: diario a las 3:00 AM
- Acción: `C:\Program Files\Git\bin\bash.exe -lc "deploy/backup.sh >> sintel_backups/backup.log 2>&1"`
- Usuario: `SYSTEM` (no depende de una sesión de usuario abierta)
- Confirmado con `Get-ScheduledTask`: estado `Ready`.

## Fase 20 — Seguridad: servicios internos bloqueados ✅ COMPLETADA (2026-07-10)

- [x] Confirmar que `ai_engine`, `ollama`, `chromadb`, `redis`, `postgres`, `celery` son inalcanzables desde fuera de Docker (ni por IP local, ni por el túnel)
- [x] Revisión final de `docker-compose.prod.yml` sin `ports:` sobrantes

### Resultados (fase de consolidación final, sin cambios de código)

Verificación exhaustiva de todo lo construido en las fases 2–19:

- `grep -n "^\s*ports:" docker-compose.prod.yml` → **0 coincidencias** en
  todo el archivo (ni siquiera Nginx publica puerto — usa `expose:`).
- `grep -in "ollama|chromadb|ai_engine|sintel_ai"` → la única coincidencia
  es el comentario del encabezado que documenta explícitamente su exclusión,
  no una referencia real a ningún servicio.
- Los 7 servicios (`redis`, `db`, `django`, `celery_worker`, `celery_beat`,
  `nginx`, `cloudflared`) están **exclusivamente** en `sintel-network`.
- `config.yml` del túnel (Fase 4/9) solo enruta hacia `https://nginx:443` —
  ningún otro servicio es alcanzable a través del túnel, ni siquiera
  accidentalmente.
- `docker compose -f docker-compose.prod.yml --env-file .env.production
  config --quiet` → sin errores, archivo completo validado de punta a punta.

Conclusión: `ai_engine`, `ollama`, `chromadb`, `redis`, `postgres` y
`celery` son inalcanzables desde fuera de Docker por diseño estructural
(nunca publicados, nunca enrutados por el túnel), no por una regla de
firewall añadida después — no hay superficie que bloquear porque nunca se
abrió.

## Fase 21 — Costos mínimos en Cloudflare (verificación) ✅ COMPLETADA (2026-07-10)

- [x] Confirmar en el dashboard de Cloudflare que solo están activos: DNS, Tunnel, SSL, CDN/caché gratuita
- [x] Confirmar que NO están habilitados: WAF de pago, Argo Smart Routing, Load Balancer, Workers, Queues, R2, Images, Stream, Durable Objects, Magic WAN, Spectrum, Access Premium

### Resultados

No verificable por API/CLI (el certificado disponible en esta sesión es
solo de gestión del túnel, sin alcance de billing/plan) — confirmado
directamente por el usuario en el dashboard de Cloudflare (Billing/Plan +
pestañas de la zona `sintel.net.co`): solo plan gratuito activo, ningún
servicio adicional de pago habilitado. Consistente con que en todo este
roadmap solo se usaron `cloudflared tunnel create/route dns` (Tunnel + DNS)
y el cambio manual de modo SSL (Fase 7) — nunca se tocó Workers, Load
Balancer, R2, Images, Stream, Access, Argo Smart Routing, ni ningún otro
producto de pago.

## Fase 22 — Entregables finales + documentación de operación ✅ COMPLETADA (2026-07-10)

- [x] `docker-compose.prod.yml` (Fase 2/3)
- [x] `Dockerfile.production` — decisión: no se creó, el `Dockerfile` multi-stage existente sirve tal cual (documentado en Fase 2)
- [x] `nginx.conf` de producción (Fase 9) — `nginx.prod.conf`
- [x] Integración `cloudflared` (Fase 4)
- [x] `settings/production.py` actualizado (Fase 10)
- [x] `.env.production.example` (Fase 16)
- [x] Scripts: `deploy.sh`, `backup.sh`, `restore.sh`, `healthcheck.sh` — los 4 creados en `ecommerce_sintel/deploy/`
- [x] Configuración de seguridad documentada (headers, cookies, HSTS, CSP) — consolidado en `docs/deployment/OPERACION_Y_RECUPERACION.md`
- [x] Pruebas de despliegue documentadas (qué se probó y cómo) — real, no solo planeado (ver abajo)
- [x] Documento de operación y recuperación ante fallos — `docs/deployment/OPERACION_Y_RECUPERACION.md`

### Resultados: se ejecutó el go-live real, no solo se prepararon los archivos

Con confirmación explícita del usuario (incluyendo la advertencia de que
esto pondría el dominio real en vivo para cualquiera en Internet), se
completó el despliegue real:

1. **`.dockerignore` corregido antes de construir** — hallazgo real: existía
   un `.dockerignore` en `ecommerce_sintel/.dockerignore`, pero el build
   context real es la raíz del repo (`context: ..`), donde Docker busca el
   archivo — nunca se aplicaba, ni en dev ni en prod. `.venv/` (232MB) se
   habría enviado al daemon en cada build. Se creó el `.dockerignore`
   correcto en la raíz; confirmado con el build real: contexto de 441.80kB
   en vez de cientos de MB.
2. **`deploy.sh` ejecutado**: build de la imagen, `up -d` de los 7
   servicios, ~150 migraciones aplicadas contra PostgreSQL real, superusuario
   creado (`admin@sintel.net.co`).
3. **Bug real #1 encontrado y corregido en vivo**: el healthcheck de
   `django` (heredado del compose de desarrollo) probaba
   `http://localhost:8000/...` sin header `Host` — rechazado por
   `ALLOWED_HOSTS` estricto de producción (`DisallowedHost`), dejando a
   Django eternamente "unhealthy" y bloqueando el arranque de `nginx`/
   `celery` (dependían de `django: condition: service_healthy`). Corregido
   agregando `-H "Host: api.sintel.net.co"` al propio healthcheck, sin
   debilitar `ALLOWED_HOSTS`.
4. **Los 7 contenedores confirmados arriba y sanos**: `redis`, `db`,
   `django`, `nginx` en `healthy`; `celery_worker`/`celery_beat`/
   `cloudflared` corriendo. Confirmado con `docker ps` que ningún puerto
   quedó publicado al host (columna `PORTS` muestra solo puertos internos
   sin `0.0.0.0:X->Y`).
5. **Bug real #2 encontrado y corregido en vivo — el más importante**:
   prueba real vía Internet público (`curl https://api.sintel.net.co/...`)
   devolvía `502` en las 4 rutas. Diagnóstico en `docker logs cloudflared`:
   `tls: failed to verify certificate: x509: certificate is valid for
   *.sintel.net.co, sintel.net.co, not nginx` — cloudflared verifica el
   certificado del origen contra el hostname literal de `service:` (`nginx`),
   no contra el `hostname:` público de la regla, contradiciendo la suposición
   documentada en la Fase 9. Corregido agregando `originRequest.originServerName`
   explícito (igual al hostname público) en cada regla de `config.yml`, y
   reiniciando `cloudflared`.
6. **Verificación final end-to-end exitosa**:
   `curl https://api.sintel.net.co/api/v1/health/` → `200 {"status": "ok"}`,
   con TLS válido, atravesando Cloudflare Edge → Tunnel → Nginx → Django
   real, de punta a punta, sin ningún puerto abierto en el router.
7. **Hallazgo disclosed y diferido (no corregido, por decisión explícita del
   usuario)**: `www`/`panel`/raíz devuelven `404` — gap de aplicación
   pre-existente (no hay vista/plantilla Django sirviendo el shell HTML de
   la SPA de Vue), fuera del alcance de este roadmap de infraestructura.
   Documentado en detalle en `OPERACION_Y_RECUPERACION.md`.

### Entregables finales

| Archivo | Contenido |
|---|---|
| `ecommerce_sintel/docker-compose.prod.yml` | 7 servicios, sin puertos publicados, logging rotado, healthchecks |
| `ecommerce_sintel/nginx.prod.conf` | TLS, headers de seguridad, rate limit, gzip, http2 |
| `ecommerce_sintel/.env.production` | Real, fuera de Git |
| `ecommerce_sintel/.env.production.example` | Plantilla versionable |
| `ecommerce_sintel/deploy/deploy.sh` | Build + up + migraciones + superusuario |
| `ecommerce_sintel/deploy/backup.sh` | Backup BD + media + config, probado |
| `ecommerce_sintel/deploy/restore.sh` | Restore, probado de punta a punta |
| `ecommerce_sintel/deploy/healthcheck.sh` | Estado del stack |
| `.dockerignore` (raíz) | Corrige un bug real de build context |
| `.gitignore` (raíz) | Protege secretos (creado en Fase 4) |
| `docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md` | Este documento — historial completo de las 22 fases |
| `docs/deployment/OPERACION_Y_RECUPERACION.md` | Manual de operación día a día |
| Tarea de Windows `SintelEcommerceBackup` | Backup automático diario 3:00 AM |

---

## Post-roadmap: SPA de Vue en producción (2026-07-10)

Al cerrar la Fase 22 se documentó como "limitación conocida, disclosed y
diferida" que `www`/`panel`/raíz devolvían `404`. El usuario pidió
resolverlo de inmediato en la misma sesión — esto ya no es infraestructura
de despliegue (las 22 fases originales), pero se documenta aquí por
continuidad. Se encontraron y corrigieron **tres bugs reales adicionales**,
uno detrás de otro, cada uno descubierto probando en el navegador/curl real:

**1. No existía ninguna vista/plantilla Django sirviendo el shell de la SPA.**
Investigación: `frontend/src/apps/customer/main.js` es un placeholder muerto
sin usar; la app real es `frontend/src/apps/admin/main.js` (monta en
`#shop-spa-root`, `vue-router` en modo `history`, con TODAS las rutas —
tienda pública Y `/panel/*` — en un único router). Fix:
- `ecommerce_sintel/templates/spa_shell.html` — plantilla nueva (no se tocó
  `base_panel.html`, que es un sistema HTMX/Bootstrap distinto y legado) con
  `{% vite_asset 'src/apps/admin/main.js' %}`.
- `ecommerce/urls.py` — `re_path` catch-all al final (`^(?!api/|admin/|static/|media/).*$`)
  sirviendo esa plantilla para cualquier ruta no-API.

**2. Los assets JS/CSS de esa plantilla daban 404.** `vite_asset` generaba
URLs como `/static/assets/admin-XXXX.js`, pero `collectstatic` (con
`STATICFILES_DIRS = [BASE_DIR / 'static']`) preserva la ruta completa:
los archivos quedan en `/staticfiles/panel/js/bundle/assets/...`. Fix:
`DJANGO_VITE['default']['static_url_prefix'] = 'panel/js/bundle'` en
`settings/base.py` (opción de `django-vite` para alinear la URL generada
con la ubicación real tras `collectstatic`).

**3. El bundle JS ya cargaba, pero horneaba `http://localhost:8000/api/v1/`
como URL de la API.** No existía `frontend/.env.production` — Vite usa ese
archivo (convención propia, mode=production en `vite build`) para inyectar
`import.meta.env.VITE_API_BASE_URL` en tiempo de build; sin él, el código
caía al fallback hardcodeado a `localhost`, que en el navegador de un
visitante real nunca resuelve. Fix: se creó
`frontend/.env.production` con `VITE_API_BASE_URL=https://api.sintel.net.co/api/v1/`.
Se ajustaron `.dockerignore` y `.gitignore` (que por regla general excluyen
`.env.*` por ser secretos) con una excepción explícita para este archivo
específico, ya que no contiene ningún secreto (la URL queda públicamente
visible en el bundle JS de todas formas) y sí hace falta versionarlo/
incluirlo en el build de la imagen para que el despliegue sea reproducible.

**Verificación tras los tres fixes anteriores**: todas las rutas devolvían
`200` vía `curl`, pero el usuario reportó pantalla en blanco real en el
navegador — **cuarto bug real, el que de verdad rompía la app**, solo
visible con la consola del navegador (no hay MCP de navegador disponible en
este entorno; el usuario pegó el error directamente):

```
Failed to load module script: Expected a JavaScript-or-Wasm module script
but the server responded with a MIME type of "text/html".
Refused to apply style from '.../assets/HomeView-rqWovCh2.css' because its
MIME type ('text/html') is not a supported stylesheet MIME type.
```

**Causa**: `frontend/vite.config.js` tenía `base: '/'`. Esto no afecta la
etiqueta `<script>` inicial (esa la genera `django-vite` vía
`static_url_prefix`, ya corregido), pero SÍ afecta las URLs que **Vite
hornea dentro del propio bundle** para las importaciones dinámicas
(code-splitting por ruta — cada `.vue` cargado con `() => import(...)` en
`router.js`) y su precarga de CSS asociado. Con `base: '/'`, esas URLs
salían como `/assets/HomeView-rqWovCh2.css` (sin el prefijo
`/static/panel/js/bundle/`), Nginx no encontraba ese archivo y devolvía el
shell HTML (vía el catch-all de la Fase "SPA de Vue") con `Content-Type:
text/html` — el navegador rechaza correctamente un módulo/CSS con ese MIME
type, y la app nunca terminaba de montar (pantalla en blanco, aunque la
petición inicial del HTML/JS principal sí diera `200`).

**Fix**: `base: '/static/panel/js/bundle/'` en `vite.config.js` — debe
coincidir exactamente con `static_url_prefix` del lado de Django. Verificado
descargando directamente el chunk que fallaba
(`HomeView-*.js`/`.css`) → `200` con `Content-Type` correcto, y un segundo
chunk al azar (`ShopCatalogView-*.js`) también `200`.

**Bug menor adicional corregido** (visto en la misma consola): `favicon.ico`
en `404` — nunca existió ese archivo, solo `favicon.svg` (parte del bundle
de Vite). `nginx.prod.conf` ahora apunta `location = /favicon.ico` a ese SVG
existente (solo requirió `nginx -s reload`, sin rebuild).

**Verificación**: `sintel.net.co`, `www`, `www/tienda`, `panel/dashboard`,
`api/v1/health/` → todos `200`; los chunks lazy-loaded que antes fallaban →
`200` con MIME type correcto; `favicon.ico` → `200`.

**Quinto bug real**: el usuario reportó, después de los fixes anteriores,
que navbar/footer/banner cargaban sin ningún error en consola pero **sin
ningún estilo visual** — página funcional pero fea/sin diseño. Causa:
`templates/spa_shell.html` (creado desde cero en el primer fix de esta
sección) era un shell HTML minimalista inventado, sin verificar contra
`frontend/index.html` (el HTML real que usa el servidor de desarrollo de
Vite). Ese archivo real incluye Bootstrap 5.3.3 + Bootstrap Icons +
Google Fonts (Inter) vía CDN — dependencias que los componentes Vue
consumen directamente como clases utilitarias (`navbar`, `container`,
`d-flex`, etc., confirmado: `grep` de `bootstrap` en `package.json` y en
el código fuente no encontró ninguna dependencia empaquetada — el proyecto
depende 100% del CDN, nunca se bundlea). Fix: se reescribió
`spa_shell.html` para replicar `frontend/index.html` casi exactamente
(mismos links CDN, mismo spinner de carga inicial, mismo bundle JS de
Bootstrap), sustituyendo solo el `<script type="module" src="/src/...">`
de desarrollo por `{% vite_asset %}`. Se actualizó el CSP en
`nginx.prod.conf` para permitir `cdn.jsdelivr.net` (script-src, style-src,
font-src) y `fonts.googleapis.com`/`fonts.gstatic.com` (style-src/font-src).

**Verificación final**: los 4 recursos CDN (`bootstrap.min.css`,
`bootstrap-icons.min.css`, `bootstrap.bundle.min.js`, Google Fonts) →
`200`; CSP actualizado confirmado en las cabeceras de respuesta real.
En total, cinco fixes reales requirieron cinco ciclos de
`./deploy/deploy.sh`/`nginx -s reload`, cada uno verificado con `curl` real
contra los dominios públicos y, para los dos últimos, con el reporte
directo de la consola del navegador del usuario (sin MCP de navegador
disponible en este entorno) antes de pasar al siguiente.

**Sexto bug real — el fix de producción rompió desarrollo**: al fijar
`base: '/static/panel/js/bundle/'` en `vite.config.js` (fix del quinto bug
de esta sección), se rompió el servidor de desarrollo (`npm run dev` /
`docker-compose.yml` servicio `frontend`, puerto 5173): navegar a cualquier
ruta anidada como `http://localhost:5173/panel/dashboard` devolvía `404`.
Causa: `vite.config.js` es el mismo archivo para `vite dev` y `vite build`
— `base` fijo afecta a ambos, pero cada uno necesita un valor distinto (dev
sirve todo desde `/`, incluido el fallback SPA para rutas anidadas; build
de producción necesita el prefijo real donde Django/Nginx sirven los
archivos). Fix: `base` condicional según el comando —

```js
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/static/panel/js/bundle/' : '/',
  ...
}));
```

Verificado: `http://localhost:5173/panel/dashboard` → `200` (tras reiniciar
el contenedor `frontend` de desarrollo, ya que Vite no recarga su propio
archivo de configuración en caliente); `https://sintel.net.co/` en
producción (tras rebuild) sigue sirviendo con el prefijo correcto
(`/static/panel/js/bundle/assets/...`) y respondiendo `200`.
