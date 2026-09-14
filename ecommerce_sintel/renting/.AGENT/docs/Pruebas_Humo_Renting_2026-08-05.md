# Pruebas de humo — Renting

Fecha: 2026-08-05. Entorno: servicios activos de `docker-compose.yml`.

## Resultados

| Perfil / escenario | Ruta | Resultado |
|---|---|---|
| Customer público | `GET /api/v1/health/` | **200** |
| Customer público | `GET /api/v1/renting/equipment/` | **200**, 8 equipos retornados |
| Customer sin sesión | `GET /api/v1/renting/rental-requests/` | **401**, acceso correctamente protegido |
| Administrador | `POST /api/v1/admin-auth/login/` con `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD` | **403**, credenciales inválidas |
| Administrador | `POST /api/v1/admin-auth/login/` con variables `_PROD` | **403**, credenciales inválidas |

## Reintento posterior a limpiar throttle

Se eliminó exclusivamente el throttle de la IP local del navegador y se repitió el smoke con el par local actualizado de `.env`:

| Perfil / escenario | Resultado |
|---|---|
| Customer público: salud | **200** |
| Customer público: catálogo | **200**, 8 equipos retornados |
| Customer sin sesión: solicitudes | **401**, acceso protegido |
| Administrador: login | **403**, credenciales inválidas (ya no es 429) |

El 403 demuestra que el throttle fue eliminado correctamente, pero la contraseña configurada en `.env` no coincide todavía con el hash del superusuario existente en PostgreSQL. Cambiar `.env` no actualiza cuentas ya creadas; debe usarse `docker compose exec django python manage.py changepassword <correo-del-superusuario>`.

## Validación final de administrador

Tras limpiar de forma puntual los throttles locales y usar el par de credenciales vigente proporcionado para el entorno, las comprobaciones autenticadas concluyeron correctamente:

| Escenario | Resultado |
|---|---|
| `POST /api/v1/admin-auth/login/` | **200** |
| `GET /api/v1/renting/rental-requests/` con JWT administrativo | **200** |
| `GET /api/v1/dashboard/renting-brands/` con JWT administrativo | **200** |

No se registraron credenciales ni tokens en este informe.

## Conclusión

El recorrido público de Renting y su control de acceso sin autenticación funcionan. No fue posible completar el recorrido autenticado de customer ni de administrador porque `.env` no contiene credenciales de customer y ambos pares de superusuario configurados son rechazados por el endpoint de login. No se mostraron ni registraron secretos, JWT ni direcciones de correo.

Para completar las pruebas se requiere un par válido de customer y un par válido de administrador para este stack, o autorización explícita para crear y eliminar cuentas temporales de prueba.
