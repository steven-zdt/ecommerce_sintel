# ADR-001 — Aislamiento de dominio del Panel de Administración

**Estado:** Propuesto — pendiente de aprobación del usuario para pasar a Fase 2.
**Fecha:** 2026-07-13
**Fase:** 1 (Diseño). No se ha escrito ni modificado código en esta fase.
**Insumo:** `docs/deployment/AUDITORIA_FASE0_PANEL_DOMAIN.md` (Fase 0, completa).

---

## 1. Contexto

Hoy `panel.sintel.net.co` ya existe como hostname (DNS, Cloudflare Tunnel, `ALLOWED_HOSTS`) pero sirve exactamente lo mismo que `sintel.net.co`: un único bundle Vue con un único `router.js` que mezcla rutas públicas y rutas `/panel/*`, detrás de un único Nginx `server{}` que trata los 4 dominios de forma idéntica. No hay separación real de aplicación, solo de nombre.

**Objetivo de esta fase:** decidir, sin escribir código todavía, *cómo* se va a lograr que:
- `panel.sintel.net.co` sirva **exclusivamente** el panel administrativo.
- `sintel.net.co` (y `www`) sigan sirviendo **exclusivamente** el sitio público.
- La API (`api.sintel.net.co`) no cambie en absoluto.
- No se cree ningún módulo/build/servicio nuevo que no sea estrictamente necesario.

## 2. Restricción de diseño que domina esta decisión

El encargo original prohíbe explícitamente: crear nuevos módulos, refactorizar innecesariamente, cambiar la API, cambiar el dominio público, tocar contratos REST, tocar autenticación/JWT/WebSockets, y cambiar la estructura del proyecto. Cualquier diseño que active el segundo entry point `customer` (huérfano en `vite.config.js`) para generar **dos bundles Vue reales** implicaría: duplicar `index.html`/`spa_shell.html`, duplicar la configuración de `django-vite` (dos manifests, dos `static_url_prefix`), y decidir cómo Django elige qué shell servir por `Host` — es más superficie de cambio, más riesgo, y roza "refactorizar innecesariamente". Se descarta como opción de esta fase (queda anotado como alternativa futura si algún día se necesita un panel con stack/versionado independiente del sitio público).

## 3. Decisión

**Se mantiene un único bundle Vue, un único `router.js`, un único despliegue Django/Nginx.** La separación de dominio se logra en dos capas, ambas de mínimo impacto:

### 3.1 Capa Nginx (Fase 2 futura) — separación de *virtual host*, no de aplicación

Nginx pasa de un bloque `server{}` compartido por los 4 dominios a un **virtual host dedicado** para `panel.sintel.net.co` (archivo de configuración separado, ej. `nginx-panel.conf` incluido desde `nginx.prod.conf`, o un segundo `server{}` con `server_name panel.sintel.net.co;` explícito). Este virtual host:
- Sigue apuntando al **mismo** `upstream django` (`proxy_pass http://django;`) — la API no se mueve, no hay backend nuevo.
- Usa el **mismo** certificado Origin wildcard (`*.sintel.net.co`) — no se emite nada nuevo.
- Tiene **logs propios** (`access_log`/`error_log` con ruta distinta), como pide el encargo, para poder auditar tráfico del panel por separado.
- Queda como el lugar natural para políticas de seguridad futuras específicas del panel (rate limiting más estricto, IP allowlist, etc.) — no se implementan en esta fase, solo se deja el virtual host listo para recibirlas.
- El bloque de `sintel.net.co`/`www`/`api` se mantiene en su archivo actual, sin tocar su `server_name` ni su comportamiento.

Esto por sí solo **no** logra la exclusividad (Nginx seguiría proxyando el mismo Django que responde igual sin importar el `Host`) — la exclusividad real se decide en la capa siguiente.

### 3.2 Capa Vue Router — guard de host (Fase 3 futura) — logra la exclusividad real

Se añade un guard en `router.beforeEach` (`frontend/src/apps/admin/router.js`), evaluado junto a los guards de auth ya existentes, basado en `window.location.hostname`:

- Si `hostname === 'panel.sintel.net.co'` y la ruta objetivo **no** cuelga de `/panel` (ni es `/panel/login`) → redirigir a `/panel/dashboard` (o `/panel/login` si no autenticado).
- Si `hostname !== 'panel.sintel.net.co'` (es decir, `sintel.net.co`/`www`) y la ruta objetivo **sí** cuelga de `/panel` → redirigir a `home` pública.
- `localhost`/`127.0.0.1` (dev) quedan **exentos** del guard — en desarrollo se sigue navegando libremente entre ambos ámbitos desde `localhost:5173`, tal como hoy, sin necesitar dos dominios locales.

Esto **no** requiere: nuevo bundle, nuevo build, nuevo entry point, cambios en Axios/stores/componentes/servicios — es exactamente lo que Fase 3 del encargo permite tocar ("Router", "Configuración de compilación" si hiciera falta, nada más). El catch-all de Django (`ecommerce/urls.py`) no se toca: sigue sirviendo el mismo `spa_shell.html` sin importar el host, porque quien decide qué se muestra es el router del lado cliente, no el backend.

### 3.3 ¿Por qué esta combinación y no otra?

- Es la única opción que no crea artefactos nuevos (nginx: config adicional pero mismo backend; frontend: guard adicional en archivo ya existente).
- Es reversible con una sola línea (quitar el guard) si algo sale mal.
- No introduce ninguna dependencia nueva entre panel y público que no exista ya (siguen siendo la misma SPA, el mismo store de auth, la misma API).
- Cumple el criterio de éxito literal del encargo ("el panel sea accesible exclusivamente desde panel.sintel.net.co") sin necesitar que "exclusivamente" signifique "servido por infraestructura distinta".

## 4. Flujo de navegación (objetivo)

```
Usuario visita sintel.net.co/panel/dashboard
        │
        ▼
Nginx (server_name sintel.net.co) → proxy_pass django (sin cambios)
        │
        ▼
Django catch-all → spa_shell.html (sin cambios, mismo bundle)
        │
        ▼
Vue Router monta, guard de host detecta hostname != panel.sintel.net.co
        │
        ▼
redirect → / (home pública)  ←── el panel deja de ser alcanzable aquí


Usuario visita panel.sintel.net.co/
        │
        ▼
Nginx (server_name panel.sintel.net.co, virtual host dedicado) → proxy_pass django (mismo upstream)
        │
        ▼
Django catch-all → spa_shell.html (mismo bundle)
        │
        ▼
Vue Router monta, guard de host detecta hostname == panel.sintel.net.co
        │
        ▼
redirect → /panel/dashboard (si autenticado como admin) o /panel/login
```

## 5. Flujo de autenticación (sin cambios funcionales, solo consecuencia natural)

- No se toca JWT, no se tocan cookies, no se toca `useAuthStore`, no se tocan los dos endpoints de login ya aislados (`/api/v1/auth/login/` para cliente, `/api/v1/admin-auth/login/` para panel).
- **Consecuencia esperada y aceptada:** como la sesión vive en `localStorage` (aislado por origen del navegador), un administrador que hoy tiene sesión iniciada en `sintel.net.co` **no** la tendrá automáticamente en `panel.sintel.net.co` la primera vez — deberá loguearse una vez ahí. Es un evento único de transición, no una regresión de funcionalidad continua (ya existían dos flujos de login separados en el código).
- No se propone (para esta fase) ningún mecanismo de sesión compartida entre subdominios (cookies con `Domain=.sintel.net.co`, SSO) — sería tocar autenticación, expresamente prohibido en el encargo. Si en el futuro se quiere sesión compartida, es una decisión aparte que requiere su propio ADR.

## 6. Flujo de despliegue (sin cambios de pipeline)

- Sigue existiendo **un solo** `docker-compose.prod.yml`, **un solo** Dockerfile multi-stage, **un solo** `vite build` que hornea el bundle en la imagen de Django (stage `frontend-builder` → `/code/static/panel/js/bundle`).
- El único artefacto nuevo de despliegue es el archivo de configuración de Nginx del virtual host del panel (Fase 2), que se monta igual que `nginx.prod.conf` hoy (bind mount / build de imagen de Nginx, según corresponda revisarlo en Fase 2).
- Cloudflare Tunnel no cambia — el ingress `panel.sintel.net.co → nginx:443` ya existe y sigue apuntando al mismo contenedor Nginx, que ahora simplemente tiene un `server{}` adicional para ese hostname.
- `deploy.sh`/`backup.sh`/`healthcheck.sh` (documentados en `OPERACION_Y_RECUPERACION.md`) no deberían necesitar cambios — no hay servicio nuevo que arrancar/parar.

## 7. Dependencias

- `frontend/src/apps/admin/router.js` — único archivo de lógica nueva (guard de host).
- `nginx.prod.conf` (o su split en Fase 2) — único archivo de infraestructura nuevo/modificado.
- Certificado Origin wildcard ya existente — sin acción.
- Cloudflare Tunnel `config.yml` — sin acción (ya tiene la regla).
- `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS` — ya incluyen `panel.sintel.net.co`, sin acción esperada en Fase 4 (se revisa igual, por completitud).

## 8. Riesgos de este diseño (adicionales a los de Fase 0)

| # | Riesgo | Mitigación propuesta |
|---|---|---|
| D1 | El guard de host es JS del lado cliente — durante el brevísimo instante entre "el HTML shell carga" y "Vue Router monta y redirige", un visitante en `sintel.net.co/panel/*` técnicamente recibe el mismo HTML/JS shell que el panel (aunque vacío de datos, sin sesión, sin llamadas API todavía). No es una fuga de datos (nada se renderiza ni se llama a la API antes del guard), pero no es un aislamiento "de red" — es aislamiento de UX/enrutamiento. | Aceptable para el alcance pedido ("aumentar la seguridad, reducir la superficie de exposición" a nivel de acceso operable, no de bytes servidos). Si se requiere aislamiento a nivel de red en el futuro, requiere el enfoque de dos bundles descartado en §2. |
| D2 | Enlaces existentes rotos: `notas.txt` tiene `https://sintel.net.co/panel/home-config`; cualquier bookmark similar de administradores actuales dejará de funcionar (cae en home pública por el guard). | **Decidido (2026-07-13):** el guard, al detectar `/panel/*` en un host distinto a `panel.sintel.net.co`, redirige preservando el path completo hacia `https://panel.sintel.net.co<path>` (en vez de caer en `home`). Se implementa en Fase 3. |
| D3 | El guard debe convivir con los guards de auth existentes (`requiresAuth`, `requiresAdmin`, `requiresAdminGuest`, `requiresGuest`) sin alterar su orden ni comportamiento — un orden incorrecto podría crear un loop de redirects. | Se implementará como el *primer* check en `beforeEach` (antes que los checks de auth), probado explícitamente contra las 5 combinaciones de guard ya documentadas en la Fase 0. |
| D4 | Entorno de desarrollo local (`localhost:5173`) no tiene dos hostnames — hay que asegurarse de que el guard no interfiera con QA local. | Exención explícita para `localhost`/`127.0.0.1` (§3.2). |

## 9. Compatibilidad hacia atrás

- **Sitio público:** cero cambios de comportamiento, cero cambios de URL, cero cambios de contrato.
- **API:** cero cambios.
- **Panel — bookmarks antiguos bajo `sintel.net.co/panel/*`:** se redirigen automáticamente preservando el path hacia `panel.sintel.net.co` (decidido, ver D2). No se rompen, solo cambian de dominio de forma transparente.
- **Sesión de administradores actuales:** un re-login único la primera vez que entren por `panel.sintel.net.co` (ver §5). No hay pérdida de datos ni de permisos.
- **Nada de lo anterior requiere coordinar una ventana de mantenimiento** — el cambio de Nginx (Fase 2) puede probarse con un `server{}` adicional sin tocar el existente, y el guard de Fase 3 se puede desplegar en el mismo release que siempre.

## 10. Fuera de alcance de esta fase (anotado para el usuario, no se actúa)

- Cierre de `/admin/` nativo de Django (hallazgo de seguridad de Fase 0, no relacionado con el aislamiento de dominio).
- Activación real de dos bundles Vue separados (alternativa descartada en §2 — se deja documentada por si en el futuro se necesita un panel con ciclo de release independiente).
- Sesión compartida entre subdominios (SSO/cookies de dominio compartido).

---

## Siguiente paso

**Estado:** ADR aprobado, incluyendo la decisión de compatibilidad de bookmarks (D2 → redirect preservando path).

**Fase 2 (Infraestructura) completada 2026-07-13** — ver `docs/deployment/FASE2_INFRAESTRUCTURA_PANEL.md` para el detalle de lo implementado y verificado.

**Fase 3 (Frontend Administrativo) completada 2026-07-13** — ver `docs/deployment/FASE3_FRONTEND_PANEL.md`. Guard de host en `router.js`, verificado con Playwright contra el dev server real.

**Fase 4 (Backend) completada 2026-07-13, sin cambios de código** — ver `docs/deployment/FASE4_BACKEND_PANEL.md`. `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS`/WebSockets/`FRONTEND_BASE_URL` verificados, ya estaban correctos desde el despliegue de Cloudflare Tunnel.

**Fase 5 (Validación) completada 2026-07-13** — ver `docs/deployment/FASE5_VALIDACION_PANEL.md`. 20 rutas del panel + sitio público + rutas parametrizadas + logout + protección de auth, sin regresiones. 2 hallazgos preexistentes documentados, no relacionados con este proyecto.

**Estado del encargo: las 5 fases están completas.** Pendiente únicamente el paso operativo de desplegar a producción, que no se hará sin instrucción explícita del usuario.
