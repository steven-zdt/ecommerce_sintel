---
app_name: users_accounts
layer: api
doc_type: spec
critical_rules:
  - IsAdminUser_definition
  - no_role_field
  - soft_delete_double
  - IsAuthenticatedActiveUser_alias
  - names_in_profile_not_user
  - customer_user_type
associated_models:
  - User
  - UserProfile
  - TechnicianProfile
  - VendorProfile
cross_app_dependencies: []
permissions_required:
  - IsAdminUser
  - IsAuthenticatedActiveUser
  - IsTechnicianUser
---

# Apps: users + accounts

## Separacion de Responsabilidades

- **users/**: Auth pura. Modelo `User`, JWT, permisos, tokens.
- **accounts/**: Perfiles. `UserProfile` (tipo de usuario), `TechnicianProfile` (especialidades).

## Permisos DRF Disponibles

```python
from users.api.permissions import (
    IsAdminUser,               # is_staff AND is_superuser — creados por CLI
    IsAuthenticatedActiveUser, # cualquier usuario autenticado y activo
    IsCustomerUser,            # ALIAS de IsAuthenticatedActiveUser (compatibilidad)
    IsTechnicianUser,          # perfil con user_type='TECHNICIAN'
    IsOwnerOrAdmin,            # object-level: el propio user o admin
    IsAdminOrReadOnly,         # admins escriben; resto solo lee
)
```

## IsAdminUser: Definicion Exacta

```python
class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_staff      # <-- AMBOS requeridos
            and request.user.is_superuser  # <-- AMBOS requeridos
        )
```

Los administradores se crean EXCLUSIVAMENTE via `python manage.py createsuperuser`. La API nunca crea admins.

## No Existe Campo role en User

```python
# INCORRECTO
user.role
user.role == 'ADMIN'
request.user.role

# CORRECTO — tipo de perfil en accounts.UserProfile
profile = getattr(request.user, 'profile', None)
if profile:
    profile.user_type  # 'TECHNICIAN' | 'PROFESSIONAL' | 'SPECIALIST'
```

## UserProfile: Tipos de Usuario

```python
class UserProfile(SintelBaseModel):
    USER_TYPE_CHOICES = [
        ('TECHNICIAN',   'Tecnico'),
        ('PROFESSIONAL', 'Profesional'),
        ('SPECIALIST',   'Especialista'),
        ('CUSTOMER',     'Comprador'),   # agregado 2026-06 — cliente del portal
    ]
    user      = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='TECHNICIAN')
    # No tiene 'ADMIN' — los admins se identifican por is_staff + is_superuser
```

## UserProfile: Campos Personales (CRITICO)

`first_name` y `last_name` **SOLO existen en `UserProfile`**, NO en `users.User`.
El modelo `User` solo tiene: `email`, `password`, `is_active`, `is_staff`, `is_superuser`, `is_verified`.

```python
# INCORRECTO — genera FieldError: Invalid field name(s) for model User
User.objects.create(first_name='Ana', last_name='Lopez')
User.objects.filter(first_name='Ana')

# CORRECTO
user = User.objects.create(email='ana@sintel.co', is_active=True)
UserProfile.objects.create(user=user, first_name='Ana', last_name='Lopez')

# Acceso desde request.user
request.user.profile.first_name
request.user.profile.last_name
request.user.profile.phone_number
request.user.profile.profile_picture  # avatar (ImageField, upload_to='profiles/pictures/')
```

Campos completos de `UserProfile` relevantes para el Customer Dashboard:

| Campo | Tipo | Nota |
|-------|------|------|
| `first_name` | CharField(50) | blank=True |
| `last_name` | CharField(50) | blank=True |
| `phone_number` | CharField(20) | unique=True, null=True |
| `profile_picture` | ImageField | `upload_to='profiles/pictures/'` — avatar |
| `company` | CharField(100) | null=True |
| `city` | CharField(50) | null=True |
| `address` | CharField(250) | null=True |

## Avatar Upload

```
PATCH /api/v1/auth/profile/   (Content-Type: multipart/form-data)
campo: profile_picture (archivo de imagen)
```

El ViewSet fusiona `request.FILES` en el dict antes de serializar:
```python
data = {**request.data}
if request.FILES:
    data.update(request.FILES)
serializer = UserProfileUpdateSerializer(data=data, partial=True)
```

## TechnicianProfile

```python
class TechnicianProfile(SintelBaseModel):
    user       = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='technician_profile')
    specialties = models.ManyToManyField('ServiceCategory', related_name='technician_profiles')
    # related_name='technician_profiles' — no 'technicians'
```

## IsTechnicianUser

```python
class IsTechnicianUser(BasePermission):
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        profile = getattr(request.user, 'profile', None)
        return profile is not None and profile.user_type == 'TECHNICIAN'
```

## Soft-Delete en User

Los usuarios nunca se eliminan fisicamente. Para desactivar:

```python
user.is_active  = False
user.is_deleted = True
user.save(update_fields=['is_active', 'is_deleted', 'updated_at'])
```

El campo `is_deleted` viene de `SintelBaseModel`. `is_active` es campo nativo de `AbstractBaseUser`.
