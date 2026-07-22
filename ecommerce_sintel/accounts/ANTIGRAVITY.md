# App: accounts — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/accounts/.AGENT/docs/ARQUITECTURA_COMPLETA_ACCOUNTS.md
```

## Responsabilidad de esta app

Registro, login, logout, verificación de email, cambio de contraseña y gestión de perfil propio.
Autenticación JWT vía `djangorestframework-simplejwt`.

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `api/views.py` | AuthViewSet: register, login, logout, profile, change-password |
| `api/serializers.py` | RegisterSerializer, LoginSerializer, ChangePasswordSerializer |
| `services/commands.py` | AccountCommands: register_user(), update_profile() |
| `services/selectors.py` | AccountSelector: get_profile() |

## Patrones obligatorios en esta app

- Toda escritura en `AccountCommands` con `@transaction.atomic`
- Registro siempre crea `UserProfile` automáticamente
- Password: nunca plaintext — usar `set_password()` / `check_password()`
- Tokens JWT: `access` (15 min) + `refresh` (7 días)
- Logout invalida el refresh token en BD

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
