# 06 — SEGURIDAD
**Fecha:** 2026-07-16  
**Herramienta:** Auditoría estática de código

> **Sincronizado 2026-07-27** contra `01_AUDITORIA_GENERAL.md` §2-3 y la Auditoría Enterprise
> (commit `a457ac6`). **Los 3 CRÍTICO y los 7 ALTA PRIORIDAD de este documento están todos
> resueltos.** MEDIA PRIORIDAD parcialmente verificada — ver anotaciones por item.

---

## CRÍTICO

### SEC-C1 — `inventory/api/views.py` usa `permissions.IsAdminUser` de DRF (solo `is_staff`)
**Estado: ✅ RESUELTO** — usa `users.api.permissions.IsAdminUser` en todas las acciones.
**Archivos:** `inventory/api/views.py:41, 145`  
**Impacto:** Cualquier usuario con `is_staff=True` (sin ser superusuario) puede crear registros de stock y ajustar inventario. Todo el resto del proyecto (79 instancias) usa `from users.api.permissions import IsAdminUser` (`is_staff AND is_superuser`).

```python
# ACTUAL (incorrecto)
from rest_framework import permissions
return [permissions.IsAdminUser()]

# CORRECTO
from users.api.permissions import IsAdminUser
return [IsAdminUser()]
```

**Prioridad:** Corregir inmediatamente antes del próximo despliegue.

---

### SEC-C2 — `integrity_signature` expuesta en respuesta API de pagos
**Estado: ✅ RESUELTO CON MATIZ** — ya no está en el serializer ni en respuestas de solo-lectura/confirmación/webhook. Sigue expuesta únicamente en `initialize()` (`views.py:415`), **a propósito**: `useWompiWidget.js` la necesita para abrir el Widget; queda expuesta solo al dueño autenticado de su propio pago, en el único punto funcionalmente necesario.
**Archivos:** `payment/online/api/serializers.py:10`, `payment/online/api/views.py:335`  
**Impacto:** `integrity_signature` es la firma HMAC derivada de `WOMPI_INTEGRITY_SECRET`. Exponerla en la respuesta permite a un comprador reconstruir o falsificar verificaciones de pago.

```python
# payment/online/api/serializers.py — QUITAR del fields list:
'integrity_signature'  # eliminar o marcar write_only=True

# payment/online/api/views.py:335 — QUITAR de la respuesta:
"integrity_signature": wompi_tx.integrity_signature  # eliminar
```

**Prioridad:** Crítico — fix inmediato.

---

### SEC-C3 — `/api/schema/` y `/api/docs/` accesibles por cualquier usuario autenticado
**Estado: ✅ RESUELTO** — ambas rutas tienen `permission_classes=[IsAdminUser]` en `ecommerce/urls.py`.
**Archivo:** `ecommerce/urls.py:29-30`  
**Impacto:** Expone el contrato completo de la API (nombres de campos, endpoints, modelos) a cualquier usuario con token válido. Un atacante con una cuenta de comprador puede mapear toda la superficie de ataque.

```python
# AGREGAR permission_classes a ambas vistas:
path('api/schema/', SpectacularAPIView.as_view(
    permission_classes=[IsAdminUser]
), name='schema'),
path('api/docs/', SpectacularSwaggerView.as_view(
    url_name='schema',
    permission_classes=[IsAdminUser]
), name='swagger-ui'),
```

---

## ALTA PRIORIDAD

### SEC-H1 — `AdminLoginView` sin rate limiting (fuerza bruta)
**Estado: ✅ RESUELTO** — `throttle_scope='admin_login'`, `'5/hour'` en settings.
**Archivo:** `users/api/admin_auth.py:67`  
**Impacto:** Permite ataques de fuerza bruta sin límite contra cuentas de superusuario. El endpoint de login de clientes (`AccountViewSet.login`) sí tiene `ScopedRateThrottle` (10/hora), pero el admin login no.

```python
# AGREGAR a AdminLoginView:
throttle_classes = [ScopedRateThrottle]
throttle_scope = 'admin_login'

# AGREGAR en REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']:
'admin_login': '5/hour'
```

---

### SEC-H2 — Quotations `create` + `add_attachment`: file upload sin validación para anónimos
**Estado: ✅ RESUELTO** — `validate_file()` en ambos, más Q-01/Q-02 de la Auditoría Enterprise (`download_pdf` ya no `AllowAny` + límite tamaño/extensión/magic-bytes en adjuntos), cubierto por `quotes/tests.py` (nuevo).
**Archivo:** `quotes/api/views.py:39-42`, `quotes/services/commands.py:179`  
**Impacto:** Cualquier usuario no autenticado puede subir archivos arbitrarios. Sin límite de tamaño, sin restricción de extensiones, sin verificación de magic bytes.

```python
# AGREGAR validación en QuotationCommands.create_quotation():
from ecommerce.file_validators import validate_file
for f in attachments:
    validate_file(f, max_size_mb=10,
                  allowed_extensions=['.pdf', '.doc', '.docx', '.jpg', '.png'],
                  magic_bytes_check=True)
```

---

### SEC-H3 — `SuccessCase` upload sin verificación de magic bytes
**Estado: ✅ RESUELTO** — `magic_bytes_check=True` en `accounts/services/commands.py`.
**Archivo:** `accounts/services/commands.py:733`  
**Impacto:** `validate_file()` se llama con `magic_bytes_check=False` (default). Un archivo `.jpg` con contenido malicioso (webshell) puede ser almacenado. KYC docs sí usan `magic_bytes_check=True`.

```python
# CAMBIAR de:
validate_file(img_file, max_size_mb=5, allowed_extensions=['.jpg', '.jpeg', '.png'])
# A:
validate_file(img_file, max_size_mb=5,
              allowed_extensions=['.jpg', '.jpeg', '.png'],
              magic_bytes_check=True)
```

---

### SEC-H4 — Operations `upload_document`: sin validación de archivo
**Estado: ✅ RESUELTO** — `validate_file()` presente, `max_size_mb=10`, `magic_bytes_check=True`.
**Archivo:** `operations/services/commands.py:426-443`  
**Impacto:** Usuarios `IsOperationalUser` pueden subir archivos sin restricciones de tipo o tamaño.

---

### SEC-H5 — `/api/v1/internal/ai/*` accesible externamente — nginx no bloquea la ruta
**Estado: ✅ RESUELTO** — `location /api/v1/internal/ { deny all; return 403; }` en `nginx-common.conf`, verificado en vivo contra producción.
**Archivo:** `ecommerce_sintel/nginx-common.conf`  
**Impacto:** El comentario en `ecommerce/internal_ai_urls.py` afirma "Nginx no proxea /internal/ hacia afuera" pero el nginx no tiene ningún bloque `location /api/v1/internal/` con `deny all`. El tráfico externo (Cloudflare → nginx → Django) puede alcanzar estos endpoints. Los endpoints de escritura del AI Engine (`AiCoreBannerCreateView`, `AiCoreNavbarLinkCreateView`) son accesibles desde internet con un token de admin.

```nginx
# AGREGAR en nginx-common.conf antes de location /:
location /api/v1/internal/ {
    deny all;
    return 403;
}
```

---

### SEC-H6 — Cambio de contraseña no invalida tokens JWT existentes
**Estado: ✅ RESUELTO y verificado 2026-07-27** — `AccountCommands._blacklist_all_refresh_tokens()` conectado en `change_password`, `admin_reset_password` y `confirm_reset`; 3/3 tests en vivo.
**Archivo:** `accounts/api/views.py:160-170`  
**Impacto:** Un atacante que obtenga un `refresh_token` válido puede seguir emitiendo nuevos `access_tokens` aunque la víctima cambie su contraseña.

```python
# En AccountViewSet.change_password(), AGREGAR después de cambiar la contraseña:
from rest_framework_simplejwt.tokens import RefreshToken
try:
    token = RefreshToken(request.data.get('refresh'))
    token.blacklist()
except Exception:
    pass  # token ya expirado o inválido
```

---

### SEC-H7 — Inventory list/retrieve accesible por cualquier usuario autenticado
**Estado: ✅ RESUELTO** — `get_permissions()` exige `IsAdminUser` en todas las acciones.
**Archivo:** `inventory/api/views.py:42`  
**Impacto:** Cualquier usuario autenticado (compradores regulares) puede ver todos los registros de stock, SKUs, y tipos de contenido del inventario completo.

```python
# CAMBIAR de:
return [permissions.IsAuthenticated()]
# A:
return [IsAdminUser()]
```

---

## MEDIA PRIORIDAD

### SEC-M1 — `integrity_signature` en respuesta hardcoded de `confirmation` action
**Archivo:** `payment/online/api/views.py:335`  
Segunda instancia de SEC-C2 fuera del serializer.
**Estado: ✅ RESUELTO** — mismo fix que SEC-C2, ya no aparece en `confirmation`.

### SEC-M2 — `CORS_ALLOW_ALL_ORIGINS = True` en settings de desarrollo
**Archivo:** `ecommerce/settings/development.py:5`  
Si `DJANGO_SETTINGS_MODULE` se configura mal en producción, todos los orígenes quedan habilitados. Agregar `CORS_ALLOW_ALL_ORIGINS = False` explícito en `base.py`.
**Estado: ⚪ Sin re-verificar en esta pasada** — no aparece en ninguna lista de items cerrados de `01_AUDITORIA_GENERAL.md` ni `12_CHECKLIST_IMPLEMENTACION.md`; verificar directamente en `base.py` antes de asumir.

### SEC-M3 — JWT: `ACCESS_TOKEN_LIFETIME=60 minutos`
**Archivo:** `ecommerce/settings/base.py`  
Estándar para e-commerce de alto valor es 15 minutos. Un token robado es válido 60 minutos sin revocación posible. Reducir a 15-20 minutos.
**Estado: ⚪ Sigue abierto** — `11_QUICK_WINS.md` QW-17 lo recomendaba pero no aparece marcado `[x]` en `12_CHECKLIST_IMPLEMENTACION.md`; probablemente sigue en 60 minutos.

### SEC-M4 — Quotation `download_pdf` es `AllowAny`
**Archivo:** `quotes/api/views.py:160`  
Cualquier persona con un UUID de cotización puede descargar el PDF con datos del cliente (nombre, email, precios). Cambiar a `IsAuthenticated` con verificación de ownership.
**Estado: ✅ RESUELTO** — cerrado como Q-01 en la Auditoría Enterprise (commit `a457ac6`): usa `get_object()` scoped al dueño, ya no `AllowAny`.

### SEC-M5 — WhatsApp webhook sin verificación de firma `X-Hub-Signature-256`
**Archivo:** `notifications/api/whatsapp_webhook.py:26`  
Meta Cloud API envía `X-Hub-Signature-256` HMAC en los POSTs. Sin verificación, cualquier actor externo puede enviar payloads arbitrarios y disparar `process_whatsapp_inbound_task.delay()`.
**Estado: ✅ RESUELTO** — cerrado como N-01 en la Auditoría Enterprise: verifica `X-Hub-Signature-256` (HMAC-SHA256, fail-closed) antes de procesar cualquier evento.

### SEC-M6 — `UserDetailSerializer` expone `AdminVerificationDetailSerializer` a usuarios normales
**Archivo:** `users/api/serializers.py:69-77`  
`GET /api/v1/auth/profile/` devuelve la verificación KYC en formato admin-level. Verificar qué campos expone `AdminVerificationDetailSerializer` y crear un `CustomerVerificationSerializer` con solo los campos necesarios para el cliente.
**Estado: ⚪ Sin re-verificar en esta pasada.**

### SEC-M7 — `AdminLoginView` con `authentication_classes = []` explícito
**Archivo:** `users/api/admin_auth.py:67`  
Sin clases de autenticación, los middlewares de throttling de DRF no pueden correlacionar por usuario — solo por IP. Esto debilita aún más la protección contra fuerza bruta.
**Estado: ⚪ Sin re-verificar en esta pasada** — el rate-limit por IP (SEC-H1) ya está resuelto; este ítem específico (correlación por usuario) no aparece confirmado en ninguna auditoría posterior.

---

## Configuración JWT (referencia)
```python
# ecommerce/settings/base.py — RECOMENDACIONES
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=15),   # reducir de 60
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
}
```
