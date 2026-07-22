# App: ecommerce (core) — Instrucciones IA

## LEER PRIMERO (obligatorio)

```
ecommerce_sintel/ecommerce/.AGENT/docs/ARQUITECTURACOMPLETA_SETTING.md
```

## Responsabilidad de esta app

Núcleo del proyecto: configuración Django, modelo base compartido, URLs raíz,
utilidades globales (WebSocket notify, base_models).

## Archivos clave

| Archivo | Propósito |
|---------|-----------|
| `settings.py` | Configuración completa Django (DB, JWT, Celery, Channels, CORS) |
| `urls.py` | Router raíz — incluye URLs de todas las apps |
| `base_models.py` | `SintelBaseModel` — herencia obligatoria para todos los modelos |
| `ws_notify.py` | `ws_notify(group, event_type, payload)` — WebSocket helper global |
| `asgi.py` | ASGI config con Django Channels |

## Patrones obligatorios en esta app

- `SintelBaseModel` provee: `uuid`, `created_at`, `updated_at`, `is_deleted`
- Todos los modelos de negocio DEBEN heredar de `SintelBaseModel`
- `ws_notify()` siempre dentro de `transaction.on_commit(lambda: ...)`
- Variables sensibles via `env()` — nunca hardcodeadas en settings

## ⚠ Precaución

Cambios en `settings.py` afectan todo el proyecto. Revisar `.AGENT.md` antes de modificar.

## Reglas globales

Ver `.AGENT.md` en la raíz del proyecto.
