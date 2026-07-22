# Auditoría Fase 0 — Aislamiento de dominio del Panel de Administración

**Fecha:** 2026-07-13
**Alcance:** Solo lectura. Ningún archivo de código/infra fue modificado en esta fase.
**Objetivo del proyecto completo:** que `panel.sintel.net.co` deje de ser un alias más de la misma SPA/backend y pase a ser el dominio exclusivo del Panel Administrativo, sin tocar la API, el frontend público, la autenticación ni el flujo de pagos.

---

## 1. Estado actual (resumen ejecutivo)

`panel.sintel.net.co` **ya existe como hostname** en DNS (Cloudflare, proxiado), en el Cloudflare Tunnel (regla de ingress propia) y en `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS` — pero a nivel de aplicación **no hay ninguna separación real**:

- **Un único proyecto Django**, un único `ecommerce/urls.py`, con un catch-all (`re_path` al final) que sirve el mismo `spa_shell.html` para cualquier `Host` que llegue, incluido `panel.sintel.net.co`.
- **Una única SPA Vue** (`frontend/src/apps/admin/main.js`, montada en `#shop-spa-root`) con **un único `router.js`** que contiene tanto las rutas públicas (`CustomerLayout`, sin prefijo, colgando de `/`) como las rutas de panel (`AppShell`, prefijo `/panel/*`). El segundo entry point que ya existe en `vite.config.js` (`customer`) está huérfano: se compila pero no lo carga ningún HTML servido.
- **Un único bloque `server{}` en Nginx** (`nginx.prod.conf:16-27` y `19-27`) — el mismo `server_name sintel.net.co www.sintel.net.co api.sintel.net.co panel.sintel.net.co;` aparece idéntico en los dos bloques (HTTP→HTTPS redirect y HTTPS real). Los 4 hostnames caen en el mismo `proxy_pass http://django;`, sin ningún `location`/`map` que los distinga.
- **Django admin nativo (`/admin/`) sigue expuesto sin condición** (`ecommerce/urls.py:25`, `path('admin/', admin.site.urls)`), montado incondicionalmente en los 4 dominios (mismo Nginx los sirve a todos). **Precisión sobre la memoria del proyecto:** la fase SSoT de 2026-07-06 (`project_ssot_consolidation_phase`) no cerró la ruta `/admin/` en sí — cerró un vector de escritura específico dentro de ella (`UserProfileInline.readonly_fields = ('user_type',)`, para impedir editar `user_type` sin pasar por `AccountCommands`/`KycCommands`). La ruta `/admin/` sigue siendo alcanzable en los 4 dominios; nunca estuvo en el alcance de esa fase cerrarla por completo. Separado en `docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md` solo se prohibió crear el **subdominio** `admin.sintel.net.co`, un control distinto que no afecta la ruta `/admin/` dentro de los dominios existentes.
- **Autenticación del panel ya está parcialmente aislada a nivel de endpoint**: `POST /api/v1/admin-auth/login/` (`AdminLoginView`, `users/api/admin_auth.py`) es un login exclusivo para superusuarios, desacoplado de `accounts.urls` y con comentario explícito de "no fusionar". El frontend ya tiene `/panel/login` como ruta aislada con su propio cliente Axios (`adminAuthClient`).
- **La sesión vive 100% en `localStorage`** (`sintel_access`, `sintel_refresh`, `sintel_user`), sin cookies, gestionada por un único store Pinia (`useAuthStore`) compartido entre cliente y panel. `localStorage` está aislado por origen — esto es el hallazgo más importante para el diseño de Fase 1/2.

---

## 2. Riesgos

| # | Riesgo | Severidad | Detalle |
|---|---|---|---|
| R1 | **Pérdida de sesión al separar orígenes** | Alta | Si `panel.sintel.net.co` pasa a ser un origen realmente distinto (HTML/bundle servido de forma diferenciada), cualquier usuario que hoy navega entre `/` y `/panel/*` en el mismo origen y comparte `localStorage` dejará de tener esa sesión compartida. Hay que decidir explícitamente: (a) sesiones independientes por dominio (aceptable, ya que hoy los logins de cliente y admin ya son flujos separados), o (b) mecanismo cross-domain. **Recomendación preliminar: (a) es compatible con "mínimo impacto" y no requiere tocar auth/JWT.** |
| R2 | **`/admin/` de Django expuesto en los 4 dominios, incluido el futuro `panel.sintel.net.co`** | Media-Alta | No es parte del alcance pedido ("no modificar autenticación/lógica de negocio"), pero es un hallazgo de seguridad que vale la pena señalar aparte, fuera de esta fase, para decisión del usuario. |
| R3 | **`vite.config.js` es el mismo archivo para dev y build** (`base` condicionado solo por `command`, no por dominio) | Media | Ya hay un incidente documentado (romper `localhost:5173`) por tocar este archivo sin condicional. Cualquier cambio de Fase 3 (Frontend Administrativo) que module `base`/rutas por dominio debe probarse en dev Y en build, igual que la regla ya existente en memoria del proyecto. |
| R4 | **Nginx: mismo `server_name` para los 4 dominios** | Media | Separar el panel requiere either un `server{}` nuevo con `server_name panel.sintel.net.co;` exclusivo, o un `map $host` dentro del bloque actual. Un error aquí (ej. faltar el `server_name` correcto o duplicar `listen 443 ssl` sin `server_name` distintivo) puede romper los 4 dominios a la vez porque comparten el mismo Nginx/contenedor. |
| R5 | **Conflicto de puertos con proyecto CRM ajeno** | Baja (solo dev) | `docker-compose.yml` de desarrollo compite por el puerto 80 con contenedores `crm_sintel-*` en la misma máquina. No afecta producción (compose prod no publica puertos al host), pero sí puede afectar pruebas locales de Fase 3/5. |
| R6 | **`FRONTEND_BASE_URL` solo apunta a `www.sintel.net.co`** | Baja | Usado para armar enlaces en emails (verificación, notificaciones). Si en el futuro el panel necesita sus propios enlaces de email, esta variable no lo contempla — no bloqueante para Fase 1, pero a documentar. |
| R7 | **`spa_shell.html` (prod) e `index.html` (dev) son dos shells HTML paralelos** que deben evolucionar en conjunto | Baja | Ya ocurrió antes (post-roadmap Cloudflare, 6 bugs corregidos por esta razón). Cualquier cambio de Fase 3 debe replicarse en ambos. |
| R8 | **CSP en `nginx.prod.conf`** ya fija `connect-src`/`wss` a `api.sintel.net.co` pero no diferencia `panel.` de `sintel.net.co` | Baja | Si Fase 3/4 introduce cualquier diferencia de origen para el panel, revisar CSP para no romper conexiones (API, WebSocket de soporte/notificaciones). |

**Riesgos explícitamente fuera de alcance de esta fase (según reglas del usuario) y por tanto NO se tocan:** JWT, WebSockets, flujo de pagos (Wompi/PSE — `VITE_WOMPI_REDIRECT_BASE` usa el dominio público), lógica de negocio, contratos de API.

---

## 3. Dependencias

- **`AdminLoginView` (`users/api/admin_auth.py`)** — ya aislado, es el punto de apoyo natural para cualquier lógica futura de origen/dominio del panel, sin tocar `accounts.urls`.
- **`django-vite`** (`ecommerce/settings/base.py:66-81`) — el manifest y `static_url_prefix` (`panel/js/bundle`) están acoplados al bundle único actual. Cualquier separación de build (activar el entry `customer` huérfano) depende de esta configuración.
- **`nginx.prod.conf`** — depende de los certificados Origin wildcard (`*.sintel.net.co`) ya emitidos, que cubren cualquier subdominio sin necesidad de nuevo certificado.
- **Cloudflare Tunnel `config.yml`** — ya tiene una regla de ingress dedicada para `panel.sintel.net.co` → `nginx:443`; no depende de cambios en Fase 2, ya está listo para que Nginx empiece a diferenciar por `originServerName`/`Host`.
- **Vue Router (`router.js`)** — el árbol de rutas `/panel/*` ya está bien delimitado (todas cuelgan de un único nodo padre con `component: AppShell`), lo cual facilita separarlas en un router propio si Fase 3 lo requiere, sin reescribir rutas individuales.
- **`useAuthStore` (Pinia)** — es compartido; cualquier cambio de Fase 3/4 relacionado con sesión debe pasar por este store único, no crear uno paralelo (regla de mínimo impacto).

---

## 4. Archivos afectados (mapa para fases futuras — ninguno tocado todavía)

| Archivo | Fase que probablemente lo toque | Motivo |
|---|---|---|
| `ecommerce_sintel/nginx.prod.conf` | Fase 2 (Infraestructura) | Necesita un `server{}`/`map` dedicado para `panel.sintel.net.co` |
| `C:\Users\Administrator\.cloudflared\sintel-production\config.yml` (fuera del repo) | Fase 2 | Ya tiene la regla de ingress; puede necesitar ajuste de `originServerName` si Nginx cambia |
| `ecommerce_sintel/frontend/vite.config.js` | Fase 3 (con extremo cuidado, ver R3) | Si se decide separar builds/bases por dominio |
| `ecommerce_sintel/frontend/src/apps/admin/router.js` | Fase 3 | Si se decide separar el router en dos (público vs panel) |
| `ecommerce_sintel/frontend/index.html` + `ecommerce_sintel/templates/spa_shell.html` | Fase 3 | Deben evolucionar en conjunto (R7) |
| `ecommerce_sintel/frontend/.env.production` / `.env.development` | Fase 3 | Nuevas variables `VITE_*` si aplica |
| `ecommerce_sintel/ecommerce/settings/base.py` / `production.py` | Fase 4 (mínimo) | Revisar `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS` (ya incluyen `panel.sintel.net.co`, probablemente sin cambios) |
| `ecommerce_sintel/.env.production` / `.env.production.example` | Fase 4 (si aplica) | Mismo motivo |
| `ecommerce_sintel/ecommerce/urls.py` | Probablemente **no** se toca | El catch-all ya sirve cualquier host; separar por dominio es responsabilidad de Nginx, no de Django, bajo el principio de mínimo impacto |

---

## 5. Impacto esperado

- **Sitio público:** ninguno, si Fase 2/4 se implementan correctamente (mismo backend, misma API, mismos contratos).
- **Panel administrativo:** dejará de responder en `sintel.net.co/panel/*` — solo será accesible vía `panel.sintel.net.co`. Esto es una **regresión intencional** que hay que comunicar (cualquier bookmark/enlace interno a `sintel.net.co/panel/...` dejará de funcionar). El propio `notas.txt` del usuario ya tiene un enlace `https://sintel.net.co/panel/home-config` que quedaría obsoleto.
- **Sesión:** los administradores probablemente deberán volver a iniciar sesión en `panel.sintel.net.co` la primera vez tras el corte (por `localStorage` aislado por origen) — no hay pérdida de datos, solo un re-login.
- **SEO/UX del sitio público:** ninguno.
- **Infraestructura:** un `server{}` adicional en Nginx (o `map`), sin nuevos contenedores, sin nuevos certificados (el wildcard ya cubre `panel.sintel.net.co`).

---

## 6. Plan de migración (alto nivel, sujeto a Fase 1 — ADR)

1. **Fase 1 (ADR):** decidir explícitamente el modelo de sesión (independiente por dominio, recomendado) y si el panel sigue siendo el mismo bundle Vue servido condicionalmente por `Host`, o si se activa el segundo entry point `customer`/`admin` ya presente en `vite.config.js` para generar dos bundles reales.
2. **Fase 2 (Infraestructura):** `server{}` dedicado en `nginx.prod.conf` para `panel.sintel.net.co`, logs propios, sin tocar el resto.
3. **Fase 3 (Frontend):** adaptar `router.js`/`vite.config.js`/shells HTML según lo decidido en el ADR, manteniendo Axios/contratos intactos.
4. **Fase 4 (Backend):** verificar (probablemente sin cambios, ya están puestos) `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS`.
5. **Fase 5 (Validación):** checklist funcional completo (login, CRUD, KYC, permisos, etc.) contra `panel.sintel.net.co`, y confirmar que `sintel.net.co` sigue sirviendo solo el sitio público.

---

## 7. Consistencia con documentación existente

- `docs/deployment/ROADMAP_CLOUDFLARE_TUNNEL.md`: documenta el estado actual (4 dominios, mismo Nginx/bundle) como resultado deliberado de esa fase — no hay contradicción, simplemente esa fase no perseguía separación de aplicación, solo de DNS/TLS. Esta auditoría es el siguiente paso lógico.
- `docs/deployment/OPERACION_Y_RECUPERACION.md`: sin cambios necesarios en esta fase; su lección sobre DNS-only vs proxiado para servicios no-HTTP sigue vigente y no aplica aquí (el panel sí es HTTP/HTTPS puro).
- **No se encontró** ningún `IMPLEMENTATION_SUMMARY(6).md` en el repo (sí existen `IMPLEMENTATION_SUMMARY.md` por app, ya auditados en fases previas según memoria del proyecto) — si el usuario tiene ese archivo en otra ubicación, indicarlo para validar consistencia adicional.

---

## Siguiente paso

Según las reglas del propio encargo: **DETENERSE aquí y solicitar aprobación antes de avanzar a Fase 1 (Diseño del nuevo dominio del Panel / ADR)**.
