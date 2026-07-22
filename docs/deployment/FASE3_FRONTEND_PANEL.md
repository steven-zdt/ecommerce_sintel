# Fase 3 — Frontend Administrativo (completada)

**Fecha:** 2026-07-13
**Diseño de referencia:** `docs/deployment/ADR_001_PANEL_DOMAIN_ISOLATION.md` §3.2/§3.3
**Alcance respetado:** no se tocó Axios, endpoints, contratos REST, stores, componentes ni servicios. Único archivo modificado: `frontend/src/apps/admin/router.js`.

## Qué se hizo

Se añadió un guard de host como **primer check** de `router.beforeEach`, antes de la recuperación PSE y de los guards de auth existentes:

- `ADMIN_HOSTNAME = 'panel.sintel.net.co'`, `LOCAL_HOSTNAMES = ['localhost', '127.0.0.1']`.
- `localhost`/`127.0.0.1` (desarrollo) quedan **exentos** — el guard no hace nada ahí, el flujo es idéntico al de siempre.
- Si el hostname es `panel.sintel.net.co` y la ruta objetivo **no** cuelga de `/panel` → redirige internamente (SPA) a `/panel/dashboard` (que a su vez, si no hay sesión, el guard de auth existente ya encadena a `/panel/login` sin ningún cambio adicional).
- Si el hostname **no** es `panel.sintel.net.co` y la ruta objetivo **sí** cuelga de `/panel` → `window.location.replace('https://panel.sintel.net.co' + to.fullPath)` (navegación de página completa, no un push de SPA) y `return false` para cancelar la navegación en curso. Preserva el path completo, incluida query/hash (`to.fullPath`), cumpliendo la decisión D2 del ADR: los bookmarks antiguos a `sintel.net.co/panel/*` (ej. el que hay en `notas.txt`) siguen funcionando, solo cambian de dominio de forma transparente.

No se activó el segundo bundle Vue huérfano (`customer` en `vite.config.js`, descartado en el ADR §2) ni se tocó `vite.config.js`, `index.html`, `spa_shell.html`, ni ninguna variable de entorno — sigue siendo un único bundle, un único build.

## Verificación realizada

Test con Playwright headless contra el Vite dev server real (`localhost:5173`, contenedor `ecommerce_sintel_frontend`), simulando los 3 hostnames relevantes vía interceptación de requests a nivel de contexto del navegador (no fue posible resolver DNS real de `panel.sintel.net.co`/`sintel.net.co` desde este entorno, así que se simuló la navegación completa a esos hosts sirviendo el mismo contenido de `localhost:5173`, lo que permite que `window.location.hostname` refleje el hostname real navegado):

1. **Baseline en `localhost:5173` (regresión):** `/`, `/panel` (sin sesión → `/panel/login`, igual que antes), `/tienda` — comportamiento idéntico al previo, sin errores de consola. El guard no interfiere en absoluto en desarrollo.
2. **Hostname simulado `panel.sintel.net.co`:** `/` y `/tienda` terminan ambos dentro de `/panel/*` (redirige a `/panel/dashboard`, y sin sesión el guard de auth existente encadena a `/panel/login`) — nunca se queda en una ruta pública.
3. **Hostname simulado `sintel.net.co`, ruta `/panel/home-config`:** se confirmó el disparo real de `window.location.replace('https://panel.sintel.net.co/panel/home-config')` (cambio de protocolo `http:`→`https:` observado en el resultado final, prueba de que fue una navegación de página completa y no un push interno de router) — el path se preservó correctamente antes de la segunda redirección por falta de sesión.
4. **Hostname simulado `sintel.net.co`, ruta pública `/`:** confirmado que **no** se dispara ningún redirect cross-domain — el sitio público se comporta con normalidad.

Errores de consola vistos en los casos 2-4 (WebSocket HMR de Vite fallando, CORS del backend real) son artefactos esperados de la técnica de simulación (un hostname que no existe de verdad intentando hablar con servicios configurados para `localhost`), no bugs del guard — no aparecieron en el caso base (1), que es el que importa para no regresionar el desarrollo local.

## Qué falta para que esto tenga efecto en producción

Este cambio vive en el árbol de trabajo del frontend. Para que tenga efecto real hace falta que el pipeline de build (`vite build` dentro del `Dockerfile`, stage `frontend-builder`) empaquete esta versión del router en el próximo despliegue — no requiere ningún paso adicional distinto al deploy normal ya documentado en `OPERACION_Y_RECUPERACION.md`.

## Siguiente paso

Me detengo aquí y solicito aprobación para pasar a **Fase 4 (Backend)** — revisión (probablemente sin cambios, dado que `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS` ya incluyen `panel.sintel.net.co` desde antes) de la configuración mínima necesaria para que el nuevo dominio funcione, sin tocar endpoints/ViewSets/serializers/modelos/BD.
