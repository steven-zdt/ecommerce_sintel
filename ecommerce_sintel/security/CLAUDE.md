# App: security — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/security/.AGENT/docs/ARQUITECTURA_COMPLETA_SECURITY.md
```

## Responsabilidad de esta app

Dominio transversal de auditoria de seguridad (`SecurityEvent`). NO reemplaza
`users.UserAuditLog` ni `kyc.VerificationEvent` -- es complementario, enfocado en senales de
seguridad (logins fallidos, rate-limit, archivos rechazados, KYC bloqueado/rechazado).

## Patron obligatorio

- `SecurityCommands.log_event(...)` es el UNICO punto de escritura de `SecurityEvent`. Cualquier
  app que quiera registrar un evento de seguridad hace `from security.services.commands import
  SecurityCommands` de forma diferida (dentro del metodo, nunca a nivel de modulo) para evitar
  ciclos de import -- mismo patron que `notifications.dispatch_notification`.
- `log_event()` nunca debe romper el flujo de negocio del caller: internamente atrapa cualquier
  excepcion y solo deja constancia en el logger.
- `SecurityEvent` es append-only -- nunca editar ni borrar filas, ni exponer un endpoint de
  escritura fuera de `log_event()`.

## Archivos clave

| Archivo | Proposito |
|---------|-----------|
| `models.py` | `SecurityEvent` |
| `services/commands.py` | `SecurityCommands.log_event()` |
| `services/selectors.py` | `SecuritySelector.list_events()`, `.get_health_snapshot()` |
| `api/views.py` | `SecurityHealthView` (`GET /api/v1/security/health/`, solo admin) |

## Reglas globales

Ver `.AGENT.md` en la raiz del proyecto.
