# Fase 4 — Backend (completada, sin cambios de código)

**Fecha:** 2026-07-13
**Diseño de referencia:** `docs/deployment/ADR_001_PANEL_DOMAIN_ISOLATION.md` §7
**Resultado:** verificación confirma que el backend **ya estaba correctamente provisionado** para `panel.sintel.net.co` desde el despliegue de Cloudflare Tunnel (2026-07-10) — no hizo falta modificar ningún archivo. Se documenta la verificación realizada, punto por punto, en lugar de un diff.

## Verificación realizada (solo lectura)

| Variable / configuración | Archivo | Estado verificado |
|---|---|---|
| `ALLOWED_HOSTS` | `.env.production` (real) | Incluye `panel.sintel.net.co` junto a los otros 3 dominios. Sin cambios necesarios. |
| `CSRF_TRUSTED_ORIGINS` | `.env.production` (real) | Incluye `https://panel.sintel.net.co`. Sin cambios necesarios. |
| `CORS_ALLOWED_ORIGINS` | `.env.production` (real) | Incluye `https://panel.sintel.net.co` (correctamente sin `api.sintel.net.co`, que no es un origen de navegador). Sin cambios necesarios. |
| `SESSION_COOKIE_SECURE` / `CSRF_COOKIE_SECURE` | `ecommerce/settings/production.py:21-22` | `True`, sin `Domain=` explícito (no hay `SESSION_COOKIE_DOMAIN`/`CSRF_COOKIE_DOMAIN` en ningún settings). Coherente con el diseño del ADR (§5): no se comparte sesión entre subdominios, cada uno es un origen independiente — no había nada que ajustar aquí porque la app no usa cookies de sesión Django (auth es 100% JWT vía `localStorage`, ver Fase 0). |
| `SECURE_PROXY_SSL_HEADER` / `SECURE_SSL_REDIRECT` / HSTS | `ecommerce/settings/production.py:20-30` | Sin relación con el dominio específico — aplican igual a los 4 hostnames vía el proxy Nginx/Cloudflare. Sin cambios. |
| `FRONTEND_BASE_URL` | `.env.production` (real) + `ecommerce/settings/base.py:304` + `accounts/services/commands.py:442-445` | Usada **únicamente** para el link de verificación de email de clientes (`/verificar-cuenta`, ruta pública). No hay ningún flujo de admin/panel que dependa de esta variable — confirmado con grep en todo el backend. Sin cambios necesarios. |
| WebSocket / Channels (`ecommerce/asgi.py`) | `ecommerce/asgi.py:11-16` | `JWTAuthMiddlewareStack` sin `AllowedHostsOriginValidator` ni ninguna otra validación de `Origin` — los WebSockets ya no discriminan por dominio (autenticación es 100% JWT, no por origen). Confirmado que no hay nada que ajustar para que funcionen igual desde `panel.sintel.net.co` — coherente con la restricción del encargo de no tocar WebSockets. |
| `ecommerce/urls.py` (catch-all, `/admin/`, rutas API) | `ecommerce/urls.py` | Sin cambios — por diseño (ADR §3.2), la exclusividad de dominio se resuelve en el Vue Router (Fase 3), no en Django. El catch-all sigue sirviendo el mismo `spa_shell.html` a cualquier host, tal como antes. |

## Por qué no hizo falta ningún cambio

Cuando se desplegó Cloudflare Tunnel (Fase 0-22 del roadmap previo, completado 2026-07-10), `panel.sintel.net.co` ya se dio de alta como uno de los 4 dominios oficiales del proyecto (junto a `sintel.net.co`, `www`, `api`) — en ese momento ya se añadió a `ALLOWED_HOSTS`/`CSRF_TRUSTED_ORIGINS`/`CORS_ALLOWED_ORIGINS`/DNS/Cloudflare Tunnel/certificado wildcard, aunque en ese momento el dominio todavía no tuviera un comportamiento diferenciado (servía lo mismo que los otros 3). Este proyecto de aislamiento (Fases 0-3) solo necesitó **usar** esa base ya existente — la separación real ocurrió en Nginx (Fase 2) y en el Vue Router (Fase 3), no en Django.

## Siguiente paso

Me detengo aquí y solicito aprobación para pasar a **Fase 5 (Validación)** — pruebas funcionales completas del panel (login, navegación, dashboard, CRUD, carga de imágenes, formularios, permisos/roles, KYC, operaciones, marketing, inventario, renting, servicios, home config, notificaciones), confirmando que todas las llamadas siguen usando la API existente sin cambios. Dado que no hay un entorno de `panel.sintel.net.co` real accesible desde aquí (requiere DNS/despliegue real), esta fase se hará contra `localhost`/el entorno de desarrollo disponible, dejando explícito qué SÍ se pudo verificar end-to-end y qué queda pendiente de confirmar en el despliegue real.
