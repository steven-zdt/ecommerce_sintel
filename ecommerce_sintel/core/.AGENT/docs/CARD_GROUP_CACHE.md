# Card Group Section — Cache

Fecha: 2026-08-06. **Sin cambios de mecanismo.** Card Group Section extiende modelos
(`HomeCard`/`HomeCardGroup`) que ya estaban conectados al cache del Home Feed — agregar
campos no requiere tocar signals ni invalidación.

## Mecanismo (sin cambios)

- Clave: `HOME_FEED_CACHE_KEY = 'sintel_home_feed_v1'` (`core/api/views.py`).
- TTL: 300s.
- Backend: `LocMemCache` en `DEBUG`, `RedisCache` en producción.
- Invalidación (ya existía antes de este cambio, sin modificar):
  1. **Signal** (`core/signals.py`): `post_save`/`post_delete` sobre `HomeCard` y
     `HomeCardGroup` → `cache.delete(HOME_FEED_CACHE_KEY)`.
  2. **Invalidación explícita** (`dashboard/api/views.py`): cada acción de
     `AdminHomeCardViewSet`/`AdminHomeCardGroupViewSet` (`create_card`, `update_card`,
     `delete_card`, `upsert`, `update_group`, `delete_group`) llama
     `_invalidate_home_feed_cache()`.

## Verificación

Los tests preexistentes de `core/tests/test_models_and_signals.py`
(`TestCacheInvalidationSignals`, `TestCacheInvalidationOnDelete`) ya cubrían
`HomeBanner`/`HomeModuleConfig`/`FooterLink` con este mismo mecanismo genérico — no se
duplicó un test de invalidación específico para `HomeCard`/`HomeCardGroup` en
`test_card_group.py` porque el receiver es el mismo código genérico ya probado, solo
registrado también para estos 2 modelos (registro que ya existía antes de este cambio, sin
modificar `core/signals.py`).
