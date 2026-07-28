# 09 — API (DRF, Contratos REST, Permisos)
**Fecha:** 2026-07-16

> **Sincronizado 2026-07-27**: la columna "Estado" de la matriz de permisos se actualizó fila por
> fila contra `01_AUDITORIA_GENERAL.md` §2-3 y la Auditoría Enterprise. La columna "Permiso Actual"
> original queda como referencia histórica (ya no describe el código actual en las filas marcadas).

---

## Matriz de Permisos

| Endpoint | Permiso Esperado | Permiso Actual (2026-07-16) | Estado (2026-07-27) |
|---|---|---|---|
| `POST /api/v1/auth/login/` | AllowAny + rate limit | AllowAny + ScopedRateThrottle (10/hr) | ✓ Correcto |
| `POST /api/v1/admin-auth/login/` | AllowAny + rate limit | AllowAny — **sin rate limit** | ✅ Resuelto (SEC-H1) — `throttle_scope='admin_login'`, 5/hora |
| `GET /api/v1/inventory/stock-records/` | IsAdminUser | IsAuthenticated (cualquier usuario) | ✅ Resuelto (SEC-H7) |
| `POST /api/v1/inventory/stock-records/` | IsAdminUser custom | Django `IsAdminUser` (solo is_staff) | ✅ Resuelto (SEC-C1) |
| `POST /api/v1/inventory/stock-records/{id}/adjust-stock/` | IsAdminUser custom | Django `IsAdminUser` (solo is_staff) | ✅ Resuelto (SEC-C1) |
| `POST /api/v1/quotes/quotations/` | AllowAny | AllowAny (sin validación de archivos) | ✅ Resuelto (SEC-H2/Q-02) — `validate_file()` agregado |
| `GET /api/v1/quotes/quotations/{id}/download_pdf/` | IsAuthenticated + owner | AllowAny | ✅ Resuelto (Q-01, Auditoría Enterprise) — `get_object()` scoped al dueño |
| `GET /api/v1/internal/ai/*` | Solo red interna | IsAuthenticatedActiveUser + accesible externamente | ✅ Resuelto (SEC-H5) — bloqueado en nginx, verificado en vivo |
| `POST /api/v1/internal/ai/core/banners/create/` | Solo red interna | IsAdminUser + accesible externamente | ✅ Resuelto (mismo fix SEC-H5) |
| `GET /api/v1/core/home-feed/` | AllowAny | `[]` (vacío explícito) | ✓ Intencional |
| `POST /api/v1/notifications/whatsapp-webhook/` | AllowAny | AllowAny sin firma | ✅ Resuelto (N-01) — verifica `X-Hub-Signature-256`, fail-closed |
| `GET /api/schema/` | IsAdminUser | IsAuthenticated (default) | ✅ Resuelto (SEC-C3) |
| `GET /api/docs/` | IsAdminUser | IsAuthenticated (default) | ✅ Resuelto (SEC-C3) |
| `/api/v1/dashboard/*` | IsAdminUser | `[IsAuthenticated, IsAdminUser]` | ✓ Correcto (IsAuthenticated redundante pero inofensivo) |
| `GET /api/v1/renting/*` (catálogo) | AllowAny | AllowAny | ✓ Intencional |
| `GET /api/v1/shop/*` (catálogo) | AllowAny | AllowAny | ✓ Intencional |
| `GET /api/v1/accounts/contractors/` | AllowAny | AllowAny | ✓ Intencional (marketplace) |

---

## Endpoints Públicos (AllowAny) — Evaluación de Riesgo

| Endpoint | Nivel de Riesgo | Notas |
|---|---|---|
| `POST /api/v1/auth/register` | Bajo | Rate-limited 5/hr, crea solo CUSTOMER |
| `POST /api/v1/auth/login` | Bajo | Rate-limited 10/hr |
| `POST /api/v1/admin-auth/login/` | ~~Alto~~ ✅ Resuelto | `throttle_scope='admin_login'` (5/hora) |
| `POST /api/v1/auth/register-request/` | Bajo | Rate-limited, flujo OTP |
| `POST /api/v1/auth/register-verify/` | Bajo | OTP requerido |
| `GET /api/v1/accounts/contractors/` | Bajo | Solo lectura, marketplace público |
| `GET /api/v1/accounts/contractors/search/` | Bajo | Solo lectura |
| `POST /api/v1/quotes/quotations/` | ~~Alto~~ ✅ Resuelto | `validate_file()` agregado (SEC-H2/Q-02) |
| `GET /api/v1/quotes/quotations/{id}/download_pdf/` | ~~Medio~~ ✅ Resuelto | Ya no `AllowAny`, scoped al dueño (Q-01) |
| `GET /api/v1/quotes/quote-template-*` | Bajo | Catálogo estático |
| `GET /api/v1/shop/*` | Bajo | Catálogo de lectura |
| `GET /api/v1/renting/*` | Bajo | Catálogo de lectura |
| `GET /api/v1/services/*` | Bajo | Catálogo de lectura |
| `GET /api/v1/marketing/offers/` | Bajo | Flash offers activas |
| `GET /api/v1/core/home-feed/` | Bajo | Caché 5 min, solo lectura |
| `GET /api/v1/core/footer/` | Bajo | Config pública |
| `GET /api/v1/core/site-config/` | Bajo | Branding público |
| `GET /api/v1/core/enums/{name}/` | Bajo | Expone enums internos pero sin datos sensibles |
| `POST /api/v1/notifications/whatsapp-webhook/` | ~~Medio~~ ✅ Resuelto | Verifica `X-Hub-Signature-256` (N-01) |
| `GET /api/v1/payment/feature-flags/` | Bajo | Solo estado del kill-switch |
| `GET /api/schema/` | ~~Medio~~ ✅ Resuelto | `IsAdminUser` (SEC-C3) |
| `GET /api/docs/` | ~~Medio~~ ✅ Resuelto | `IsAdminUser` (SEC-C3) |
| `GET /api/v1/health/` | Bajo | `{status: ok}` |

---

## Endpoints Duplicados / Solapados

### Rutas que comparten prefijo `api/v1/auth/` (accounts + kyc)
```python
path('api/v1/auth/', include('accounts.urls')),
path('api/v1/auth/', include('kyc.api.urls')),   # comparte prefijo
```
Esto funciona correctamente en Django (los URL patterns se concatenan), pero puede generar confusión para desarrolladores que esperan una app por prefijo. No es un bug pero sí un riesgo de mantenimiento.

### ViewSets con tanto GET público como POST admin en el mismo endpoint
- `FlashOfferViewSet` (`/api/v1/marketing/offers/`): GET es AllowAny (correcto, catálogo público), pero POST/PUT/DELETE son ModelViewSet completo con `IsAdminUser`. El patrón es correcto, solo documentar explícitamente que la escritura es admin-only.

### `ServiceOrderViewSet` vive en `orders/api/service_orders.py` (no en `technical_services`)
Potencial confusión para nuevos desarrolladores que busquen el ciclo de vida de órdenes de servicio en `technical_services/api/`.

---

## Rate Limiting — Estado Actual

| Endpoint / Scope | Throttle configurado |
|---|---|
| `register` | `ScopedRateThrottle` — 5/hora |
| `login` | `ScopedRateThrottle` — 10/hora |
| `admin_login` | ✅ Resuelto — `5/hora` (SEC-H1) |
| `kyc_upload` | `ScopedRateThrottle` — 20/hora |
| `kyc_upgrade` | `ScopedRateThrottle` — 5/hora |
| `order_create` | `ScopedRateThrottle` — 30/hora |
| Resto de endpoints | `DEFAULT_THROTTLE_RATES` (configuración base) |

---

## Contratos REST — Inconsistencias

### PUT vs PATCH
- La mayoría de los ViewSets exponen solo PATCH (correcto para actualizaciones parciales en DRF)
- Verificar que ningún ViewSet de dashboard exponga PUT sin restricción — algunas escrituras vía `partial_update` llaman `quotation.save()` directamente (ver `08_BACKEND.md` ARCH-H4)

### HTTP Status codes
Los endpoints de escritura del AI Engine devuelven `200 OK` por defecto en vez de `201 Created` para creaciones. Verificar `AiCoreBannerCreateView`, `AiCoreNavbarLinkCreateView`. El convenio del proyecto es `201` para POST que crean recursos.

### Paginación
- Los catálogos públicos (`/api/v1/shop/products/`, `/api/v1/renting/equipment/`) usan paginación de DRF
- Los endpoints internos AI (`/api/v1/internal/ai/`) devuelven listas sin paginación
- Algunos endpoints del dashboard retornan todos los registros sin límite (riesgo de performance con datasets grandes)

---

## OpenAPI / drf-spectacular

`drf-spectacular` está configurado. No se auditaron en detalle las anotaciones `@extend_schema`, pero los siguientes endpoints son candidatos con alta probabilidad de schema incorrecto o faltante:

- Todas las vistas de `core/api/internal_ai.py` (nuevas en Fase 8)
- `AdminMetricsView` — respuesta calculada, no serializer estándar
- Endpoints de fulfillment en `OrderViewSet` (FSM states con payloads variables)
- `ServiceOperationViewSet` actions (11 estados FSM)

**Recomendación:** Agregar `@extend_schema(tags=['AI Internal'])` a todos los endpoints en `internal_ai.py` y marcarlos como `exclude=True` en el schema público si se restringe el schema a admins.

---

## Configuración de CORS

```python
# development.py
CORS_ALLOW_ALL_ORIGINS = True  # RIESGO: si settings apunta a dev en prod

# base.py (producción)
CORS_ALLOWED_ORIGINS = [...]   # leído desde env — correcto
# FALTA: CORS_ALLOW_ALL_ORIGINS = False explícito como guard
```

---

## Webhook — Verificación de Firmas

| Webhook | Verificación | Estado |
|---|---|---|
| Wompi (`/api/v1/payment/payments/webhook/`) | `_verify_wompi_event_signature()` — HMAC SHA256 | ✓ Implementado |
| WhatsApp Meta (`/api/v1/notifications/whatsapp-webhook/`) | HMAC-SHA256 sobre `X-Hub-Signature-256`, fail-closed (N-01) | ✅ Resuelto 2026-07-27 |
| Nequi | Polling interno, sin webhook entrante | N/A |
