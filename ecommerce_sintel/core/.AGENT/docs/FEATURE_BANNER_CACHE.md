# Feature Banner — Cache

Fecha: 2026-08-06. Sin cambios de mecanismo: Feature Banner reusa integramente el cache ya
existente de `core/home-feed/`, sin un cache propio ni un TTL distinto.

## Mecanismo (sin cambios)

- Clave: `HOME_FEED_CACHE_KEY = 'sintel_home_feed_v1'` (`core/api/views.py`).
- TTL: 300s (5 minutos).
- Backend: `LocMemCache` si `DEBUG` (local), `RedisCache` en produccion
  (`ecommerce/settings/base.py`).
- Invalidacion: dos mecanismos redundantes, ambos ya usados por el resto del Home Builder --
  1. **Signal** (`core/signals.py`): `post_save`/`post_delete` sobre `FeatureBannerSection` y
     `FeatureBannerBlock`, cada uno llama `cache.delete(HOME_FEED_CACHE_KEY)`.
  2. **Invalidacion explicita** (`dashboard/api/views.py`): cada accion de los dos ViewSets
     admin (`create_section`, `update_section`, `delete_section`, `create_block`,
     `update_block`, `delete_block`, `reorder`) llama `_invalidate_home_feed_cache()` justo
     despues de la mutacion.

La redundancia (signal + invalidacion explicita) es intencional y preexistente en el patron
del Home Builder -- no se introduce nada nuevo para Feature Banner, solo se conecta a los 2
modelos nuevos exactamente igual que a `HomeBanner`/`HomeModuleConfig`/`HomeCard`/
`HomeCardGroup`/`BrandSliderConfig`.

## Verificacion

- Test `test_creating_section_invalidates_home_feed_cache` (`core/tests/
  test_feature_banner.py`): setea un valor falso en `HOME_FEED_CACHE_KEY`, crea una
  `FeatureBannerSection` via `FeatureBannerSectionCommands.create()`, confirma que el cache
  quedo invalidado (`cache.get(HOME_FEED_CACHE_KEY) is None`).
- No se requiere un test de invalidacion por bloque por separado: el signal esta registrado
  para `FeatureBannerBlock` con el mismo receiver generico, y el mecanismo de invalidacion
  (`cache.delete`) es identico independientemente de cual de los 2 modelos dispara la senal.
