# Fase 2 — Infraestructura del Panel (completada)

**Fecha:** 2026-07-13
**Diseño de referencia:** `docs/deployment/ADR_001_PANEL_DOMAIN_ISOLATION.md` §3.1
**Alcance respetado:** sin cambios en API, backend, base de datos, autenticación, WebSockets, contratos REST, ni Cloudflare Tunnel (ya tenía la regla de ingress para `panel.sintel.net.co`, no requirió tocarse).

## Qué se hizo

1. **`ecommerce_sintel/nginx.prod.conf`** — el bloque `server{}` único de 443 (que trataba los 4 dominios igual) se dividió en:
   - Un `server{}` para `sintel.net.co www.sintel.net.co api.sintel.net.co` (sitio público + API) — **comportamiento idéntico al anterior**, solo perdió `panel.sintel.net.co` de su `server_name` y ganó logs propios (`public.access.log` / `public.error.log`).
   - Un `server{}` **nuevo, dedicado**, con `server_name panel.sintel.net.co;`, mismo `upstream django`, mismo certificado, mismas cabeceras de seguridad, con sus propios logs (`panel.access.log` / `panel.error.log`) y un comentario marcando dónde endurecer políticas de seguridad del panel en el futuro (rate limiting, IP allowlist) sin tocar el virtual host público.
   - El bloque de redirect HTTP→HTTPS (puerto 80) se mantuvo compartido por los 4 dominios — comportamiento idéntico, no necesitaba separarse (mismo `return 301`).

2. **`ecommerce_sintel/nginx-common.conf`** (nuevo archivo) — se factorizaron ahí las directivas que **deben** permanecer idénticas entre ambos virtual hosts (certificado SSL, protocolos/cifrados, `client_max_body_size`, `gzip`, cabeceras de seguridad, CSP, y los 4 `location{}` — `/`, `/static/`, `/favicon.ico`, `/media/`). Motivo: duplicar ~80 líneas en dos `server{}` habría creado riesgo de que un futuro cambio de CSP/gzip se aplicara solo a uno de los dos dominios por descuido. Se montó **fuera** de `conf.d/` (en `/etc/nginx/nginx-common.conf`) porque el `nginx.conf` base incluye automáticamente `conf.d/*.conf`; si el archivo viviera ahí se cargaría dos veces (el include automático + el `include` explícito dentro de cada `server{}`) y la segunda carga fallaría (los `location{}` no son válidos directamente en el contexto `http{}`).

3. **`ecommerce_sintel/docker-compose.prod.yml`** — una línea nueva de volumen para montar `nginx-common.conf` (misma read-only, mismo patrón que `nginx-upgrade-map.conf` ya existente). Ningún servicio, puerto, red ni variable de entorno cambió.

## Qué NO se tocó

- `Dockerfile`, imagen de Django, Celery, Postgres, Redis, `cloudflared` — sin cambios.
- `C:\Users\Administrator\.cloudflared\sintel-production\config.yml` — ya tenía la regla de ingress `panel.sintel.net.co → nginx:443`, no requería ajuste.
- Certificados — se sigue usando el mismo Origin Certificate wildcard (`*.sintel.net.co`), no se emitió nada nuevo.
- `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS`/settings de Django — sin cambios (queda para revisión, probablemente sin acción, en Fase 4).

## Verificación realizada

- `nginx -t` (syntax + validación semántica) contra los 3 archivos nuevos/modificados, ejecutado en un contenedor `nginx:1.26-alpine` desechable (mismo tag que usa `docker-compose.prod.yml`), con un certificado autofirmado de prueba (nunca el real) y el upstream `django` apuntado temporalmente a una dirección resoluble solo para el test — **exitoso**.
- `nginx -T` (dump de configuración ya fusionada) confirmó los 3 bloques `server{}` esperados con los `server_name`/`access_log`/`error_log` correctos:
  - Redirect 80 → 443: los 4 dominios.
  - 443 público: `sintel.net.co www.sintel.net.co api.sintel.net.co`, logs `public.*`.
  - 443 panel: `panel.sintel.net.co`, logs `panel.*`.
- Artefactos de la prueba (cert autofirmado, copias temporales de config) se generaron y limpiaron en el directorio de scratchpad de la sesión — nunca se escribió nada fuera de él ni se tocaron los certificados reales en `C:\Users\Administrator\sintel_secrets\certs`.
- **No se desplegó** — este cambio vive en el árbol de trabajo, listo para el próximo `docker compose -f docker-compose.prod.yml --env-file .env.production up -d nginx` cuando el usuario decida aplicarlo (fuera del alcance de esta fase, que es solo preparar la infraestructura).

## Impacto esperado al desplegar

- Sitio público (`sintel.net.co`/`www`/`api`): cero cambio de comportamiento observable.
- `panel.sintel.net.co`: sigue sirviendo exactamente el mismo bundle Vue que antes (la exclusividad real de rutas se logra en Fase 3, a nivel de Vue Router) — el cambio de esta fase es invisible para el usuario final, solo prepara la infraestructura (logs separados, virtual host propio) para lo que viene.
- Ningún downtime esperado: `nginx -s reload` (o el ciclo normal de `docker compose up -d nginx`) recarga la config sin tumbar conexiones existentes de forma abrupta.

## Siguiente paso

Me detengo aquí y solicito aprobación para pasar a **Fase 3 (Frontend Administrativo)**: agregar el guard de host en `frontend/src/apps/admin/router.js` (según lo diseñado en el ADR §3.2/§3.3, incluyendo el redirect que preserva el path para bookmarks antiguos), sin tocar Axios, endpoints, stores ni componentes.
