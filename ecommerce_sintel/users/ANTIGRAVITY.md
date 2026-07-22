# App: users — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/users/.AGENT/docs/ARQUITECTURA_COMPLETA_USER.md
```

## Responsabilidad de esta app

Modelo de usuario personalizado (email como login), perfiles de cliente y vendedor,
OTP por teléfono, y clases de permisos DRF reutilizables en todo el proyecto.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `models.py` | User (AbstractBaseUser), UserProfile, VendorProfile, PhoneOtp |
| `api/views.py` | UserViewSet (CRUD admin: list, create, retrieve, partial_update, destroy) |
| `api/serializers.py` | UserDetailSerializer, UserAdminCreateSerializer, UserAdminUpdateSerializer |
| `api/permissions.py` | IsAdminUser, IsCustomerUser, IsOwnerOrAdmin, IsAdminOrReadOnly |
| `services/commands.py` | UserCommands: update_profile(), change_password() |
| `services/selectors.py` | UserSelector: get_by_email(), get_by_id(), list_all() |

## Patrones obligatorios en esta app

- **USERNAME_FIELD = 'email'** — nunca usar `username` para autenticación
- Roles: `ADMIN=1`, `CUSTOMER=2`, `VENDOR=3`
- **Permisos:** SIEMPRE importar desde `users.api.permissions` — no usar `rest_framework.permissions.IsAdminUser`
- **Soft-delete:** `user.is_active = False` — nunca DELETE físico
- Protección anti-autoborrado: admin no puede desactivarse a sí mismo
- `UserProfile` se crea automáticamente vía signal en registro
- `PhoneOtp.is_expired()` → válido 5 minutos

## Clases de permiso (exportadas al proyecto)

```python
# Importar en cualquier ViewSet del proyecto:
from users.api.permissions import IsAdminUser, IsOwnerOrAdmin, IsAdminOrReadOnly, IsCustomerUser
```

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
