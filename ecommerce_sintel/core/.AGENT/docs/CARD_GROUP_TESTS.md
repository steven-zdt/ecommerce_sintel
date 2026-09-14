# Card Group Section — Tests backend

Fecha: 2026-08-06. `core/tests/test_card_group.py`, 16 tests, estilo pytest +
`pytest-django` (mismo patrón que `core/tests/test_feature_banner.py`).

## Cobertura

| Clase | Qué cubre | Tests |
|---|---|---|
| `TestValidateUrlTypePair` | El helper compartido `core/validators.py::validate_url_type_pair()` — URL vacía siempre válida, reglas INTERNA/EXTERNA/ANCHOR | 4 |
| `TestHomeCardUrlValidation` | `HomeCard.clean()` (nuevo) valida `redirect_url`+`url_type` y `secondary_url`+`secondary_url_type` | 4 |
| `TestHomeCardCommandsNewFields` | `HomeCardCommands.create_card()`/`update_card()` persisten `stats`/`badge_color`/`secondary_*`, ignoran campos desconocidos (whitelist) | 3 |
| `TestHomeCardGroupCommandsNewFields` | `HomeCardGroupCommands.upsert()` persiste y actualiza los 8 campos nuevos de responsive/carrusel | 2 |
| `TestHomeCardGroupDefaults` | Los defaults de los campos de carrusel no cambian la apariencia de un grupo `slider` ya existente (`carousel_autoplay=False` por defecto) | 1 |
| `TestCardGroupInHomeFeed` | `GET core/home-feed/` expone los campos nuevos en `home_cards`/`card_groups` | 1 |
| `TestUrlTypeBackfillLogic` | Replica la query exacta del `RunPython` de la migración 0029 y confirma que el resultado es coherente con `validate_url_type_pair()` | 1 |

**Total: 16/16 passed** (`pytest core/tests/test_card_group.py -v`, corrida real contra
Postgres del contenedor de desarrollo, sin mocks del ORM).

## Regresión

`pytest core/tests/` (suite completa de `core`, incluyendo `test_models_and_signals.py` y
`test_feature_banner.py`): el único test que falla es el mismo ya documentado como
preexistente en `FEATURE_BANNER_TESTS.md`
(`TestCacheInvalidationOnDelete::test_footer_link_deletion_invalidates_cache`, no
relacionado con Card Group ni con Feature Banner). No se introdujeron regresiones nuevas.

## Nota de diseño del test de backfill

`TestUrlTypeBackfillLogic` no puede re-ejecutar la migración histórica dentro de un test
unitario estándar (requeriría el framework de "migration testing" de Django con estado
congelado). En su lugar, crea las filas de prueba con `HomeCard.objects.bulk_create()`
(que **no** llama a `save()`/`clean()` — igual que el modelo histórico que usa
`apps.get_model()` dentro del `RunPython`, que tampoco tiene el `full_clean()` del modelo
real) y luego ejecuta la **misma query exacta** que usa la migración
(`filter(redirect_url__startswith='http').update(url_type='EXTERNA')`), verificando que el
resultado es coherente. Esto prueba la lógica real de la migración sin necesitar re-simular
el estado histórico completo de Django.
