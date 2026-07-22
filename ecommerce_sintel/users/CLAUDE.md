# App: users — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/users/.AGENT/docs/ARQUITECTURA_COMPLETA_USER.md
```

## Responsabilidad de esta app

SOLO autenticacion: modelo User con email/password, OTP por telefono y permisos DRF.
Datos de perfil personal y clasificacion viven en `accounts.UserProfile`.

## Archivos clave

| Archivo | Proposito |
|---------|-----------|
| `models.py` | User (AbstractBaseUser), PhoneOtp, EmailVerificationCode, UserAuditLog — SIN first_name/last_name/role |
| `api/views.py` | UserViewSet — único ViewSet de administración de usuarios (paginación/filtros/búsqueda + reset-password/resend-verification/groups/audit-log) |
| `api/serializers.py` | UserDetailSerializer, UserAdminCreateSerializer, UserAdminUpdateSerializer, GroupSerializer, UserGroupsUpdateSerializer, UserAuditLogSerializer |
| `api/permissions.py` | IsAdminUser, IsAuthenticatedActiveUser (alias IsCustomerUser), IsTechnicianUser, IsOwnerOrAdmin, IsAdminOrReadOnly |
| `services/commands.py` | UserCommands: change_password(); UserAuditCommands: log() |
| `services/selectors.py` | UserSelector: get_by_email(), get_by_id(), list_all(search=, user_type=, is_active=, is_verified=, company=, city=, country=, ordering=); UserAuditLogSelector: list_for_user() |

`/panel/usuarios` (frontend `modules/users/UserList.vue` + `UserDetail.vue` + `UserForm.vue`)
consume `/api/v1/users/` directamente. Ver sección 8 de `ARQUITECTURA_COMPLETA_USER.md` para el
inventario completo de endpoints (incluye reset de contraseña por admin, reenvío de verificación
vía enlace firmado — distinto del OTP de registro —, asignación de Groups sin efecto en la
autorización real, y el log de auditoría `UserAuditLog`). Un `AdminUserViewSet` duplicado en
`dashboard` se eliminó (2026-07-05).

`UserAuditLog.ACTION_CHOICES` gano 5 valores nuevos (2026-07-06):
`kyc_submitted`/`kyc_approved`/`kyc_rejected`/`kyc_info_requested`/`kyc_blocked`,
poblados desde `kyc.services.commands.KycCommands` (dual-log junto al
`kyc.VerificationEvent` propio, mas fino) — ver `kyc/CLAUDE.md`.

## NUEVA ARQUITECTURA (post-refactor DDD)

| Campo | Ubicacion anterior | Ubicacion nueva |
|-------|-------------------|-----------------|
| first_name, last_name | User | accounts.UserProfile |
| phone_number | User | accounts.UserProfile |
| role (ADMIN/CUSTOMER/VENDOR/TECHNICIAN) | User | ELIMINADO — usar is_staff/is_superuser + accounts.UserProfile.user_type |
| UserProfile (address, city...) | users.UserProfile | accounts.UserProfile |
| TechnicianProfile | users.TechnicianProfile | accounts.TechnicianProfile |
| VendorProfile | users.VendorProfile | ELIMINADO (2026-07-05) — código muerto, ningún endpoint lo poblaba |

## Campos de User (modelo limpio)

```
email, password, is_active, is_staff, is_superuser, is_verified, date_joined, uuid, is_deleted
```

## Clasificacion de usuarios

- **Admin:** `is_staff=True AND is_superuser=True` — SOLO via `createsuperuser` CLI. La API nunca los crea.
- **Usuarios regulares:** `accounts.UserProfile.user_type` in [TECHNICIAN, PROFESSIONAL, SPECIALIST]
- `get_full_name()`/`get_short_name()` delegan a `accounts.services.profile_resolver.ProfileResolver.get_profile(self)` (no acceder a `self.profile` directo)

## Permisos (exportados al proyecto)

```python
from users.api.permissions import (
    # Basicos
    IsAdminUser,                 # is_staff AND is_superuser
    IsAuthenticatedActiveUser,   # cualquier usuario activo (alias: IsCustomerUser)
    IsTechnicianUser,            # user.profile.user_type == TECHNICIAN
    IsOwnerOrAdmin,
    IsAdminOrReadOnly,
    IsDispatcherUser,            # dispatcher_profile activo
    IsDispatcherOrAdmin,
    IsOperationalUser,           # TECHNICIAN/PROFESSIONAL/SPECIALIST/TRANSPORTER/CONTRACTOR o dispatcher
    # Granulares por perfil (Plan A, 2026-06-27)
    IsBuyerOrAdmin,              # BUYER_TYPES + admin — usar en cart, orders, renting
    IsServiceProviderUser,       # SERVICE_PROVIDER_TYPES — usar en skills/CV/agenda
    IsServiceProviderOrAdmin,
    IsTransporterUser,           # solo TRANSPORTER
    IsAccountantUser,            # solo ACCOUNTANT
)

# Grupos de tipos (fuente unica de verdad — no redefinir en otro lado):
# accounts.services.profile_registry.BUYER_TYPES / SERVICE_PROVIDER_TYPES /
# OPERATIONAL_TYPES / CONTRACTOR_ASSIGNABLE_TYPES
```

Desde 2026-07-05, internamente todas estas clases resuelven el perfil vía
`accounts.services.profile_resolver.ProfileResolver` (nunca `getattr(user, 'profile', None)`
directo) — ver "Política de arquitectura de perfiles" en
`accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md`. Los nombres y el comportamiento externo
de cada clase no cambiaron.

**Regla:** Nunca usar `permissions.IsAuthenticated` directamente en ViewSets de negocio.
Elegir siempre la clase granular que corresponda al dominio del recurso.

## Patrones obligatorios

- **USERNAME_FIELD = 'email'** — nunca usar username
- **Soft-delete:** `user.is_active = False` — nunca DELETE fisico
- Nunca reintroducir el campo `role` en User — clasificacion va en UserProfile
- Para nombre del tecnico usar `technician.get_full_name()` (delega a profile)

## Reglas globales

Ver `.AGENT.md` en la raiz del proyecto.
