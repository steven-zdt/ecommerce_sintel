# Arquitectura Completa: Módulo Users (Autenticación)

> **Actualizado:** 2026-08-07 — Identity Management Lote 1 (bajo riesgo): acciones masivas,
> timeline unificado, auditoria enriquecida con IP/user-agent (ver seccion 4d).
> `erase()` corregido a soft-delete real (ver seccion 4c); refactor DDD (2026-06-19) sigue
> vigente sin cambios. `users` = solo identidad/auth. Todos los datos de perfil viven en
> `accounts`.

---

## Resumen Ejecutivo

El módulo **Users** implementa UNICAMENTE autenticación y control de acceso. Extiende
`AbstractBaseUser` + `PermissionsMixin` usando email como identificador. No contiene
datos personales ni clasificación de negocio: eso es responsabilidad de
`accounts.UserProfile`.

La clasificación de administradores se hace con `is_staff=True AND is_superuser=True`
(solo vía CLI `createsuperuser`, nunca por API). La clasificación de usuarios regulares
(TECHNICIAN, PROFESSIONAL, SPECIALIST) vive en `accounts.UserProfile.user_type`.

Los permisos DRF centralizados (`IsAdminUser`, `IsOwnerOrAdmin`, etc.) se exportan desde
este módulo y son reutilizables en cualquier ViewSet del proyecto.

---

## 1. Capas de Arquitectura

```
+----------------------------------------------------------+
|               REST API (DRF ViewSets)                    |
|  users/api/views.py  — UserViewSet (CRUD admin cuentas)  |
|  accounts/api/views.py — AccountViewSet (register/login) |
+------------------------------+---------------------------+
                               |
+------------------------------v---------------------------+
|           Serializers — users/api/serializers.py         |
|  UserDetailSerializer, UserAdminCreateSerializer,        |
|  UserAdminUpdateSerializer                               |
+------------------------------+---------------------------+
                               |
+------------------------------v---------------------------+
|         Permisos — users/api/permissions.py              |
|  IsAdminUser, IsAuthenticatedActiveUser, IsTechnicianUser|
|  IsOwnerOrAdmin, IsAdminOrReadOnly                       |
+------------------------------+---------------------------+
                               |
+------------------------------v---------------------------+
|         Service Layer                                    |
|  users/services/commands.py  — change_password()         |
|  users/services/selectors.py — list_all(), get_by_*()   |
+------------------------------+---------------------------+
                               |
+------------------------------v---------------------------+
|        Modelos — users/models.py                         |
|  User (AbstractBaseUser), PhoneOtp                       |
|                                                          |
|        Perfiles — accounts/models.py (app separada)      |
|  UserProfile, VendorProfile, TechnicianProfile           |
+----------------------------------------------------------+
```

---

## 2. Archivos del Modulo

| Archivo | Responsabilidad |
|---------|----------------|
| `users/models.py` | `User` (solo auth) y `PhoneOtp` |
| `users/api/views.py` | `UserViewSet` — CRUD admin de cuentas |
| `users/api/serializers.py` | Serializers de entrada/salida para UserViewSet |
| `users/api/permissions.py` | Clases de permiso DRF exportadas al proyecto |
| `users/api/urls.py` | Registro del router de `users` |
| `users/services/commands.py` | `UserCommands.change_password()`, `UserCommands.erase_user()` (2026-07-17) |
| `users/services/selectors.py` | `UserSelector.list_all()`, `get_by_email()`, `get_by_id()` |
| `users/admin.py` | Registro del admin con inlines de perfiles de `accounts` |
| `users/forms.py` | `CustomUserCreationForm`, `CustomUserChangeForm` |
| `users/migrations/` | Migraciones de la tabla `users_user` y `users_phoneotp` |

---

## 3. Modelo User — Campos Post-Refactor DDD

El modelo `User` (`users/models.py`) contiene SOLO campos de identidad y autenticacion:

```
email, password, is_active, is_staff, is_superuser, is_verified, date_joined,
uuid, is_deleted, created_at, updated_at
```

**Campos eliminados en el refactor 2026-06-19:**

| Campo eliminado | Nuevo hogar |
|----------------|-------------|
| `first_name` | `accounts.UserProfile.first_name` |
| `last_name` | `accounts.UserProfile.last_name` |
| `phone_number` | `accounts.UserProfile.phone_number` |
| `role` (ADMIN/CUSTOMER/VENDOR/TECHNICIAN) | Eliminado — ver seccion 5 |

**Reglas inmutables del modelo:**
- `USERNAME_FIELD = 'email'` — nunca usar username
- `REQUIRED_FIELDS = []` — `createsuperuser` solo pide email + password
- `get_full_name()` delega a `user.profile.get_full_name()` (en `accounts.UserProfile`)
- Soft-delete en dos niveles, nunca DELETE fisico (bug real corregido 2026-07-17, ver
  seccion 4c): `user.is_active = False` (desactivar, reversible — `destroy()`) y
  `user.is_deleted = True` (eliminar permanentemente de la UI, irreversible por diseno —
  `erase()`). `UserSelector.list_all()` ya filtra `is_deleted=False`.

---

## 4. Modelo PhoneOtp

Definido en `users/models.py`. Almacena OTPs temporales para verificacion por SMS.
- Validez: 5 minutos desde `created_at` (metodo `is_expired()`)
- Unicidad: un OTP activo por `phone_number`
- No hereda `SintelBaseModel` (modelo simple, sin UUID)

---

## 4b. Modelo UserAuditLog (nuevo, 2026-07-05)

Definido en `users/models.py`. Registro append-only de acciones administrativas sobre un usuario,
poblado con llamadas explicitas desde `UserViewSet` (no via signals).
- `actor`/`target_user`: FK a `User` con `on_delete=SET_NULL`. Desde 2026-07-17 `erase()` ya
  no borra la fila del usuario (ver seccion 4c) por lo que este `SET_NULL` en la practica ya
  no se dispara vía `erase` — se mantiene como red de seguridad para cualquier hard-delete
  real que exista o se agregue en el futuro en otro punto del proyecto.
- `actor_email`/`target_user_email`: denormalizados, mantienen el log legible aun despues de que la
  fila objetivo (o la cuenta del propio admin) ya no exista.
- `action`: choices (`created`, `activated`, `deactivated`, `updated`, `password_reset`,
  `verification_resent`, `groups_changed`, `erased`).
- `metadata`: JSONField, contexto libre por accion (ej. `group_ids` en `groups_changed`).
- Consultado via `UserAuditLogSelector.list_for_user(user)`, expuesto en
  `GET /api/v1/users/{uuid}/audit-log/`.

---

## 4c. Eliminacion de usuarios — `erase()` (corregido 2026-07-17, bug real de HTTP 500)

**Antes:** `UserViewSet.erase()` hacia `user.delete()` (hard delete) directo, sin capturar
excepciones — violaba la regla de soft-delete de la seccion 3 y `.AGENT.md` seccion 6.1.

**Bug real encontrado:** ninguna FK directa a `User` en todo el proyecto usa
`PROTECT`/`RESTRICT`, y aun asi `erase()` lanzaba `django.db.models.deletion.ProtectedError`
(500 sin control) para cualquier usuario con una `RentalRequest` real. Causa: Django's
deletion `Collector` recorre TODO el grafo de cascada, no solo el primer nivel —
`RentalRequest.user` es CASCADE (nivel 1), pero `renting.RentalOperation.rental_request` es
PROTECT (nivel 2). Al cascadear el borrado de `User` hacia su `RentalRequest`, Django
encuentra que esa `RentalRequest` esta protegida por una `RentalOperation` y aborta.
Segundo punto de choque identico encontrado en la auditoria (nunca disparado aun, mismo
riesgo): `technical_services.ServiceOperation.order` (PROTECT sobre `orders.Order`, tambien
CASCADE desde `User`). Auditoria completa: ~26 FKs `CASCADE` mas hacia `User` (Orders,
Payments, Reviews, Chat, TokenizedCard, etc.) que un hard-delete real hubiera borrado en
cascada o abortado a medias — perdida de datos de negocio real.

**Fix:** `UserCommands.erase_user(actor, user)` (`users/services/commands.py`) —
`user.is_deleted = True` (nunca `.delete()`), dentro de `@transaction.atomic`. Como
`UserSelector.list_all()` ya filtraba `is_deleted=False`, el usuario desaparece de
`/panel/usuarios` sin tocar ninguna fila relacionada. Esto elimina la clase de bug
completa (no solo el caso `RentalOperation`) sin necesidad de re-ordenar ni tocar ninguno
de los ~28 modelos relacionados auditados.

```python
# users/services/commands.py — UserCommands.erase_user()
if user == actor:
    raise ValidationError({'detail': 'No puedes eliminarte a ti mismo.'})
if user.is_active:
    raise ValidationError({'detail': 'Solo se pueden eliminar usuarios inactivos. Desactiva primero la cuenta.'})
if user.is_deleted:
    raise NotFound('Este usuario ya fue eliminado.')
user.is_deleted = True
user.save(update_fields=['is_deleted'])
UserAuditCommands.log(actor, user, UserAuditLog.ACTION_ERASED, target_user_email=user.email)
```

`UserViewSet.erase()` queda solo como orquestador: obtiene el user, llama al Command, y
envuelve en `except (ProtectedError, IntegrityError)` → `409 Conflict` como defensa
adicional (ya no deberia poder dispararse con el diseño actual, pero nunca debe propagarse
como 500 si a futuro se reintroduce un hard-delete en algun otro lugar del grafo).

**Contrato HTTP de `DELETE /api/v1/users/{uuid}/erase/`:**

| Escenario | Codigo |
|---|---|
| Usuario inactivo, sin errores | 204 |
| Usuario ya eliminado (`is_deleted=True`) | 404 |
| Usuario activo (no desactivado primero) | 400 |
| El admin intenta eliminarse a si mismo | 400 |
| Solicitante sin `IsAdminUser` | 403 |
| Usuario inexistente | 404 |
| (defensa) `ProtectedError`/`IntegrityError` inesperado | 409 |

**Frontend:** `UserList.vue::executeDelete()` no necesito cambios — ya mostraba
`err.response?.data?.detail` correctamente (confirmacion inline `bg-danger-subtle`, loading,
toast, `loadPage()` sin recarga completa); solo nunca recibia un `detail` limpio porque el
backend devolvia un 500 crudo.

**Tests:** `users/tests.py::UserEraseTestCase` (7 casos, incluye recrear el escenario real
con `RentalRequest`+`RentalOperation` via `RentalOperationCommands.ensure_for_request` y
confirmar que sobreviven intactas tras el erase).

---

## 4d. Identity Management Lote 1 (2026-08-07) — acciones masivas, timeline, auditoria IP/UA

Primer lote (bajo riesgo) de un plan mas amplio de "Identity Management Center" pedido para
`/panel/usuarios`. La Fase 0 (auditoria) encontro que **no hay duplicidad real** en
`users`/`accounts`/`organization`/`dashboard`/`security`/`notifications`/`kyc` — los flujos que
parecen duplicados (3 rutas de "resetear contrasena", 2 flujos OTP admin/cliente) son
aislamiento deliberado y documentado. Pero varias piezas de un "Identity Management" completo
**no existen aun como concepto** y quedan fuera de este lote: sesiones/JWT con IP/geo/dispositivo,
bloqueo automatico por intentos fallidos, 2FA, una matriz de permisos real (los Groups de
`UserDetail.vue` siguen sin efecto en la autorizacion — ver seccion 5), purga fisica validada
cross-app, import/export Excel/PDF, dashboard de KPIs, buscador global indexado, endpoints
`/internal/ai/users/`, `correlation_id` en auditoria.

**Decisiones de alcance (confirmadas con el usuario):**
- Sin cambios al modelo de autorizacion, sin subsistemas nuevos.
- "Suspendido"/"Bloqueado" son **solo etiquetas visuales** sobre `is_active=False`, resueltas
  por texto libre en `UserAuditLog.metadata.reason` — **sin campo `status` nuevo en `User`**,
  sin migracion de esquema.

**Cambios:**

1. **`UserAuditCommands.log(actor, target_user, action, metadata=None, target_user_email='',
   request=None)`** (`users/services/commands.py`) — nuevo parametro opcional `request`, mismo
   patron exacto que `security.SecurityCommands.log_event()`: si se pasa, extrae
   `request.META.get('REMOTE_ADDR')`/`HTTP_USER_AGENT` (truncado a 255) dentro de `metadata`.
   Todas las llamadas existentes en `UserViewSet` (`create`, `partial_update`, `destroy`,
   `erase`, `reset_password`, `resend_verification`, `update_groups`) ahora pasan `request=request`.
2. **Motivo opcional al desactivar** — `destroy()` y `partial_update()` (cuando cambia
   `is_active` a `False`) leen un `reason` opcional del body (no es un campo de serializer, se
   lee directo de `request.data`, igual que el patron ya usado para otros campos no-modelo) y lo
   guardan en `UserAuditLog.metadata.reason`.
3. **`UserDetailSerializer.last_deactivation_reason`** (`SerializerMethodField`) — `None` si
   `is_active=True`; si no, el `reason` del `UserAuditLog` de tipo `deactivated` mas reciente
   para ese usuario. El frontend hace matching de texto (`bloque`/`suspend`) sobre este campo
   para mostrar "Bloqueado"/"Suspendido"/"Inactivo" en vez de un generico "Inactivo".
4. **`POST /api/v1/users/bulk-action/`** (`UserViewSet.bulk_action`) — body
   `{uuids: [...], action: 'activate'|'deactivate'|'resend_verification', reason: ''}`. Reusa
   `AccountCommands.admin_update_user`/`resend_verification_email` en un loop, cada usuario
   dentro de su propio `transaction.atomic()` (un fallo no revierte a los demas), un
   `UserAuditLog` por usuario afectado con `metadata={'bulk': True, 'batch_size': N, ...}`.
   Responde `{updated: [uuid, ...], failed: [{uuid, email, detail}, ...]}`. Guarda contra
   auto-desactivacion masiva (`user == request.user` + `action='deactivate'`). **Sin
   eliminacion masiva** — el borrado permanente sigue siendo uno-por-uno via `erase()`.
5. **`UserTimelineSelector.get_timeline(user, limit=100)`** (`users/services/selectors.py`) —
   mezcla `UserAuditLog`, `kyc.VerificationEvent` (via `verification__user=user`) y
   `security.SecurityEvent` en 3 querysets pequenos separados (sin UNION SQL), normaliza cada
   uno a `{timestamp, source, event_type, description, actor_email, metadata}` y ordena
   descendente en Python. Expuesto en `GET /api/v1/users/{uuid}/timeline/`.
6. **Frontend** — `UserList.vue`: seleccion por fila + "seleccionar todo visible" (patron
   `selectedIds` Set de `BrandList.vue`), barra de acciones masivas, boton "Exportar CSV" (BOM
   UTF-8, todo o solo la seleccion), etiqueta de estado via `statusLabel()`/`statusBadgeClass()`.
   `UserDetail.vue`: nueva seccion "Timeline" con `StatusTimeline.vue` (`mode="events"`),
   alimentada por `store.fetchTimeline(uuid)`.

**Tests:** `users/tests.py` — `UserAuditLogRequestMetadataTestCase` (2), `UserBulkActionTestCase`
(7), `UserTimelineTestCase` (2). 11/11 OK.

Ver tambien `users/.AGENT/docs/AUDIT_USER_MANAGEMENT.md` (entregable completo de la Fase 0).

---

## 5. Clasificacion de Usuarios (reemplaza campo role)

| Tipo de usuario | Como se detecta | Como se crea |
|-----------------|----------------|--------------|
| Admin | `user.is_staff=True AND user.is_superuser=True` | Solo via CLI `createsuperuser` |
| CUSTOMER | `user.profile.user_type == 'CUSTOMER'` | API register con `user_type='CUSTOMER'` |
| TECHNICIAN | `user.profile.user_type == 'TECHNICIAN'` | API register con `user_type='TECHNICIAN'` |
| PROFESSIONAL | `user.profile.user_type == 'PROFESSIONAL'` | API register con `user_type='PROFESSIONAL'` |
| SPECIALIST | `user.profile.user_type == 'SPECIALIST'` | API register con `user_type='SPECIALIST'` |
| CONTRACTOR | `user.profile.user_type == 'CONTRACTOR'` | API register con `user_type='CONTRACTOR'` |
| TRANSPORTER | `user.profile.user_type == 'TRANSPORTER'` | API register con `user_type='TRANSPORTER'` |
| ACCOUNTANT | `user.profile.user_type == 'ACCOUNTANT'` | API register con `user_type='ACCOUNTANT'` |

La API **NUNCA** asigna `is_staff=True` ni `is_superuser=True`.
`AccountCommands.register_user()` (en `accounts/services/commands.py`) extrae y descarta
esos campos si llegan en el payload.

### Grupos de tipos (constantes en permissions.py)

```python
BUYER_TYPES = frozenset({
    'CUSTOMER', 'TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR',
})
# Pueden: comprar productos, alquilar equipos, contratar servicios.
# Excluye TRANSPORTER y ACCOUNTANT (personal operativo).

SERVICE_PROVIDER_TYPES = frozenset({
    'TECHNICIAN', 'PROFESSIONAL', 'SPECIALIST', 'CONTRACTOR',
})
# Pueden ademas: gestionar CV profesional, skills, experiencias, agenda/disponibilidad.
# Subconjunto de BUYER_TYPES.
```

---

## 6. Perfiles de Usuario (en app accounts)

Los modelos de perfil no viven en `users`. Se acceden desde `User` via related_name:

| Acceso | Modelo | Archivo |
|--------|--------|---------|
| `user.profile` | `UserProfile` | `accounts/models.py` |
| `user.vendor_profile` | `VendorProfile` | `accounts/models.py` |
| `user.technician_profile` | `TechnicianProfile` | `accounts/models.py` |

Ver `accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md` para detalles completos.

---

## 7. Permisos DRF (users/api/permissions.py)

Todos los permisos del proyecto se exportan desde `users/api/permissions.py`.

### 7.1 Permisos basicos

| Clase | Criterio de acceso | Uso tipico |
|-------|-------------------|-----------|
| `IsAdminUser` | `is_staff=True AND is_superuser=True` | Panel admin, CRUD usuarios |
| `IsAuthenticatedActiveUser` | autenticado + `is_active=True` | Cualquier recurso autenticado |
| `IsCustomerUser` | alias de `IsAuthenticatedActiveUser` | Compatibilidad con codigo antiguo |
| `IsTechnicianUser` | `user.profile.user_type == 'TECHNICIAN'` | Recursos exclusivos de tecnicos |
| `IsOwnerOrAdmin` | objeto propio o admin | Datos personales |
| `IsAdminOrReadOnly` | GET libre, escritura requiere admin | Catalogos |
| `IsDispatcherUser` | `user.dispatcher_profile.is_active == True` | Modulo operations |
| `IsDispatcherOrAdmin` | IsDispatcherUser OR admin | Modulo operations |
| `IsOperationalUser` | TECHNICIAN/PROFESSIONAL/SPECIALIST/TRANSPORTER/CONTRACTOR o dispatcher | Tareas operativas |

### 7.2 Permisos granulares por perfil (Plan A — 2026-06-27)

| Clase | Criterio | Donde se usa |
|-------|----------|-------------|
| `IsBuyerUser` | `user_type in BUYER_TYPES` | (raro — usar IsBuyerOrAdmin) |
| `IsBuyerOrAdmin` | `IsBuyerUser` OR admin | `cart/`, `orders/`, `renting/rental-requests/` |
| `IsServiceProviderUser` | `user_type in SERVICE_PROVIDER_TYPES` | CV skills, agenda, disponibilidad |
| `IsServiceProviderOrAdmin` | `IsServiceProviderUser` OR admin | (disponible, no asignado aun) |
| `IsTransporterUser` | `user_type == 'TRANSPORTER'` | (disponible para modulo logistics) |
| `IsAccountantUser` | `user_type == 'ACCOUNTANT'` | (disponible para modulo finanzas) |

### 7.3 Matriz de acceso por endpoint

| user_type | cart/ orders/ renting/ | CV skills agenda/ | /api/v1/users/ |
|-----------|----------------------|-------------------|----------------|
| CUSTOMER | ALLOW | DENY | DENY |
| TECHNICIAN | ALLOW | ALLOW | DENY |
| PROFESSIONAL | ALLOW | ALLOW | DENY |
| SPECIALIST | ALLOW | ALLOW | DENY |
| CONTRACTOR | ALLOW | ALLOW | DENY |
| TRANSPORTER | DENY | DENY | DENY |
| ACCOUNTANT | DENY | DENY | DENY |
| Admin (staff) | ALLOW | ALLOW | ALLOW |

### 7.4 Uso en ViewSets

```python
from users.api.permissions import (
    IsAdminUser, IsAuthenticatedActiveUser, IsOwnerOrAdmin, IsAdminOrReadOnly,
    IsBuyerOrAdmin, IsServiceProviderUser, IsTransporterUser, IsAccountantUser,
)
```

---

## 8. API REST — UserViewSet

Definido en `users/api/views.py`. Es el **unico** ViewSet de administracion de usuarios del
proyecto — el panel `/panel/usuarios` lo consume directamente. Un `AdminUserViewSet` duplicado
existio en `dashboard` y se elimino (2026-07-05): el frontend nunca lo llamaba y ya habia
divergido del comportamiento real.

**Permiso requerido:** `IsAdminUser` (todas las acciones)

### Endpoints

| Metodo | URL | Accion |
|--------|-----|--------|
| GET | `/api/v1/users/` | Lista con paginacion (`page_size=25`) + filtros (`search`, `user_type`, `is_active`, `is_verified`, `company`, `city`, `country`) + `ordering` (`date_joined`/`email`/`last_login`) |
| POST | `/api/v1/users/` | Crear usuario (delega a `AccountCommands.register_user`) + `UserAuditLog` |
| GET | `/api/v1/users/{uuid}/` | Detalle de usuario |
| PATCH | `/api/v1/users/{uuid}/` | Actualizar parcial (delega a `AccountCommands.admin_update_user`) + `UserAuditLog` |
| DELETE | `/api/v1/users/{uuid}/` | Desactivar cuenta (soft-delete: `is_active=False`) + `UserAuditLog` |
| DELETE | `/api/v1/users/{uuid}/erase/` | Elimina permanentemente de la UI (soft-delete real: `is_deleted=True`, solo si ya esta inactivo, corregido 2026-07-17 — ver seccion 4c) + `UserAuditLog` |
| POST | `/api/v1/users/{uuid}/reset-password/` | Genera contrasena temporal, la aplica y la envia por correo (`AccountCommands.admin_reset_password`) |
| POST | `/api/v1/users/{uuid}/resend-verification/` | Reenvia enlace de verificacion firmado a un usuario YA existente (`AccountCommands.resend_verification_email`) — 400 si ya esta verificado |
| GET | `/api/v1/users/groups-catalog/` | Catalogo de Django `Group` existentes |
| PUT | `/api/v1/users/{uuid}/groups/` | Asigna Groups al usuario (`AccountCommands.set_user_groups`) — **sin efecto en la autorizacion real hoy**, ver seccion 5 |
| GET | `/api/v1/users/{uuid}/audit-log/` | Historial paginado de `UserAuditLog` para ese usuario |
| POST | `/api/v1/users/bulk-action/` | Accion masiva sobre una lista de `uuids` (`activate`/`deactivate`/`resend_verification`) — Lote 1, ver seccion 4d |
| GET | `/api/v1/users/{uuid}/timeline/` | Timeline unificado (auditoria + KYC + seguridad) via `UserTimelineSelector` — Lote 1, ver seccion 4d |

**Proteccion de auto-desactivacion:** el admin no puede desactivarse a si mismo.

**Confirmacion publica de verificacion** (no vive en `UserViewSet`, es publica): `POST
/api/v1/auth/verify-email-confirm/` en `accounts/api/views.py::AccountViewSet` (`AllowAny`), body
`{token}` → `AccountCommands.confirm_email_verification_link`.

### Recuperacion self-service del administrador por OTP de correo

Las rutas bajo `/api/v1/admin-auth/` se mantienen aisladas de la recuperacion de clientes:

| Metodo | URL | Accion |
|---|---|---|
| POST | `/api/v1/admin-auth/forgot-password-request/` | Solicita OTP para el correo indicado y siempre devuelve una respuesta generica para no enumerar cuentas. |
| POST | `/api/v1/admin-auth/forgot-password-verify/` | Verifica el OTP sin consumirlo. |
| POST | `/api/v1/admin-auth/reset-password/` | Consume el OTP, cambia la contrasena y devuelve un par JWT nuevo. |

`AdminPasswordResetCommands` solo genera o consume codigos para cuentas activas con
`is_staff=True` e `is_superuser=True`. El serializer de confirmacion aplica
`validate_password` del servidor y exige que ambas contrasenas coincidan; el medidor de seguridad
del frontend no sustituye esta validacion. Cada cambio queda registrado como
`UserAuditLog.ACTION_PASSWORD_RESET` con el metodo `admin_self_service_otp`.

---

## 9. Serializers (users/api/serializers.py)

### UserDetailSerializer (output)
- Expone: `id`, `uuid`, `email`, `first_name`/`last_name`/`full_name` (via `ProfileResolver`),
  `is_verified`, `is_active`, `is_staff`, `date_joined`, `last_login`, `profile` (anidado),
  `technician_profile` (anidado), `dispatcher_profile` (`SerializerMethodField`, import diferido
  de `operations.api.serializers.DispatcherProfileSerializer` para evitar ciclo), `groups`
  (`GroupSerializer`, M2M de Django).
- No expone: `password`, `is_superuser`, `role` (eliminado).
- `VendorProfileSerializer`/`vendor_profile` se eliminaron (2026-07-05) junto con `VendorProfile`.

### UserAdminCreateSerializer (input — crear)
- Campos: `email`, `first_name`, `last_name`, `phone_number`, `password`, `password_confirm`.
- **Sin `user_type` (2026-07-09, SSoT de identidad):** todo usuario creado desde
  `/panel/usuarios` nace `CUSTOMER` (`AccountCommands.register_user()` defaultea a
  `UserProfile.CUSTOMER` cuando el caller no pasa el campo). Un admin ya no puede crear
  TECHNICIAN/PROFESSIONAL/SPECIALIST/CONTRACTOR directamente — solo vía upgrade + KYC
  aprobado. Ver `accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md` sección
  "Auditoria y Correcciones" (2026-07-09).

### UserAdminUpdateSerializer (input — actualizar)
- Campos opcionales: `first_name`, `last_name`, `phone_number`, `is_active`, `is_verified`.
- No permite `is_staff` ni `is_superuser` via API.
- **Sin `user_type` (2026-07-09):** el campo se retiró — ya era ignorado en silencio por
  `AccountCommands.update_profile()` (no está en su allow-list), así que exponerlo en el
  serializer solo era enganoso. El único camino válido para cambiar el tipo de un usuario
  existente es `KycCommands._apply_requested_user_type()` (upgrade aprobado).

### Nuevos: GroupSerializer, UserGroupsUpdateSerializer, UserAuditLogSerializer
- `GroupSerializer`: `id`, `name` (Django `Group`, solo lectura salvo asignacion via `group_ids`).
- `UserGroupsUpdateSerializer`: input `{group_ids: list[int]}`.
- `UserAuditLogSerializer`: output de `UserAuditLog` (`uuid`, `action`, `action_display`,
  `actor_email`, `metadata`, `created_at`), todos read-only.

---

## 10. Service Layer

### UserCommands (users/services/commands.py)
- `change_password(user, old_password, new_password)` — verifica contrasena anterior antes de cambiar.
- `erase_user(actor, user)` (2026-07-17) — soft-delete real (`is_deleted=True`, nunca
  `.delete()`), valida self-erase/activo/ya-eliminado, registra `UserAuditLog`. Ver seccion 4c.
- Registro y actualizacion de perfil delegados a `AccountCommands` en `accounts/services/commands.py`.

### UserAuditCommands (users/services/commands.py) — nuevo (2026-07-05)
- `log(actor, target_user, action, metadata=None, target_user_email='', request=None)` — unico
  punto de escritura de `UserAuditLog`. Se llama explicitamente desde cada accion de
  `UserViewSet` (no via signals, siguiendo el patron de Service Layer del proyecto). El parametro
  `request` (2026-08-07, Lote 1) enriquece `metadata` con `ip_address`/`user_agent` — ver seccion 4d.

### UserSelector (users/services/selectors.py)
- `list_all(search='', user_type='', is_active='', is_verified='', company='', city='', country='',
  ordering='-date_joined')` — acepta filtros/busqueda/ordering (2026-07-05, antes no tenia
  parametros). `select_related('profile', 'technician_profile', 'dispatcher_profile')` +
  `prefetch_related('groups')`.
- `get_by_email(email)` — busca por email (Http404 si no existe)
- `get_by_id(user_id)` — busca por PK (Http404 si no existe)

### UserAuditLogSelector (users/services/selectors.py) — nuevo (2026-07-05)
- `list_for_user(user)` — historial de auditoria acotado a `target_user=user`, mas reciente primero.

### UserTimelineSelector (users/services/selectors.py) — nuevo (2026-08-07, Lote 1)
- `get_timeline(user, limit=100)` — mezcla `UserAuditLog` + `kyc.VerificationEvent` +
  `security.SecurityEvent` en un timeline unico ordenado. Ver seccion 4d.

---

## 11. JWT Authentication

El flujo de autenticacion es responsabilidad de `accounts/api/views.py` (AccountViewSet).
`users` solo exporta el modelo `User` y los permisos. Ver detalles en
`accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md`.

**Rutas de autenticacion (en accounts):**

| Endpoint | Accion |
|----------|--------|
| `POST /api/v1/accounts/register/` | Registro |
| `POST /api/v1/accounts/login/` | Login → access + refresh tokens |
| `POST /api/v1/accounts/logout/` | Logout → invalida refresh token |
| `POST /api/v1/accounts/token/refresh/` | Renovar access token |
| `GET  /api/v1/accounts/profile/` | Perfil propio |
| `PATCH /api/v1/accounts/profile/` | Actualizar perfil propio |
| `POST /api/v1/accounts/change-password/` | Cambio de contrasena |

---

## 12. Django Admin (users/admin.py)

`UserAdmin` registra `User` con tres inlines que muestran los perfiles desde `accounts`:
- `UserProfileInline` — datos personales + `user_type`
- `VendorProfileInline` — datos de tienda
- `TechnicianProfileInline` — especialidades + disponibilidad

**Fieldsets del User en admin:** solo campos de auth (`email`, `password`,
`is_active`, `is_staff`, `is_superuser`, `is_verified`, fechas).
Los campos `first_name`, `last_name`, `phone_number` se editan via `UserProfileInline`.

**Regla critica — `add_fieldsets`:** usar `password1` y `password2`, NO `password`.
`UserCreationForm` genera esos dos campos; usar `'password'` causa HTTP 200 silencioso
sin crear el usuario. Ver `users/forms.py`.

---

## 13. Migraciones

Cadena de dependencias del refactor DDD (2026-06-19):

```
users/0003  -->  accounts/0001_create_profiles
                    -->  accounts/0002_migrate_user_data_to_profiles
                              -->  users/0004_remove_profile_fields_and_models
```

`users/0004` depende explicitamente de `accounts/0002` para garantizar que los datos
esten copiados antes de eliminar las columnas originales de `User`.

---

## 14. Dependencias Entre Modulos

**users exporta hacia:**
- `User` model → ForeignKey desde todos los modulos (orders, shop, cart, technical_services...)
- Permisos DRF → reutilizados en todos los ViewSets del proyecto

**users importa desde:**
- `accounts.services.commands.AccountCommands` — para `register_user` y `admin_update_user`
- `rest_framework_simplejwt` — JWT
- `django.contrib.auth` — hashing, PermissionsMixin

**Regla de dependencia circular:** `users` importa de `accounts`, `accounts` importa de
`users` (via `AUTH_USER_MODEL`). Esto es intencional y seguro porque `accounts` usa
`settings.AUTH_USER_MODEL` (string lazy), no el import directo de `User` en nivel de modulo.

---

## 15. Seguridad — Reglas Fijas

- **Admins SOLO via CLI:** `python manage.py createsuperuser`. La API NUNCA asigna `is_staff=True`.
- **Soft-delete obligatorio, nunca `user.delete()`:** `user.is_active = False` (desactivar,
  `destroy()`) o `user.is_deleted = True` (eliminar de la UI permanentemente, `erase()` —
  corregido 2026-07-17, ver seccion 4c).
- **Password siempre hasheado:** `set_password()` y `check_password()`, nunca plaintext.
- **Auto-desactivacion bloqueada:** un admin no puede desactivarse a si mismo.
- **OTP caduca en 5 minutos:** validar `PhoneOtp.is_expired()` antes de verificar.

---

## 16. Historial de Cambios Relevantes

| Fecha | Cambio |
|-------|--------|
| 2026-05-14 | C1: `add_fieldsets` corregido a `password1`/`password2` |
| 2026-05-14 | C2: frontend `isAdmin` desacoplado de `is_staff` inexistente en serializer |
| 2026-05-14 | C3: `readonly_fields` para fechas en admin |
| 2026-06-19 | Refactor DDD: campo `role` eliminado de `User` |
| 2026-06-19 | Perfiles (`UserProfile`, `VendorProfile`, `TechnicianProfile`) movidos a `accounts` |
| 2026-06-19 | Nuevas clases de permiso: `IsAuthenticatedActiveUser`, `IsTechnicianUser` |
| 2026-06-19 | `UserManager.create_user()` simplificado (sin `phone_number`, `role`) |
| 2026-06-19 | `get_full_name()` delega a `user.profile` |
| 2026-07-17 | Bug real corregido: `erase()` hacia hard-delete (`user.delete()`) y lanzaba `ProtectedError` sin capturar (500) para usuarios con `RentalRequest`/`RentalOperation` reales. Fix: `UserCommands.erase_user()` nuevo, soft-delete via `is_deleted=True` — ver seccion 4c |
| 2026-08-07 | Identity Management Lote 1: `bulk-action`/`timeline` endpoints nuevos, `UserAuditCommands.log(request=...)` para IP/user-agent, `reason` opcional al desactivar, `UserDetailSerializer.last_deactivation_reason`, seleccion masiva + export CSV en `UserList.vue`, pestana Timeline en `UserDetail.vue` — ver seccion 4d |

---

## Estado Actual (2026-06-19)

- Refactor DDD completado y migraciones aplicadas en dev.
- 0 referencias a `user.role`, `User.ADMIN`, `User.CUSTOMER`, `User.TECHNICIAN` en el codebase.
- Admin Django operativo con inlines de perfiles desde `accounts`.
- Permisos DRF actualizados y funcionando en todas las apps del proyecto.
