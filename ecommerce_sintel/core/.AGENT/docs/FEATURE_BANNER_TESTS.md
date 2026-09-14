# Feature Banner — Tests backend

Fecha: 2026-08-06. `core/tests/test_feature_banner.py`, 21 tests, estilo pytest +
`pytest-django` (mismo patron que `core/tests/test_models_and_signals.py`).

## Cobertura

| Clase | Que cubre | Tests |
|---|---|---|
| `TestFeatureBannerSectionValidation` | `overlay_opacity` fuera/dentro de rango (0-100) | 2 |
| `TestFeatureBannerBlockUrlValidation` | Coherencia `url_type`/`url` para los 3 tipos (INTERNA/EXTERNA/ANCHOR), caso valido y caso invalido de cada uno, mas el caso "URL vacia no se valida" | 7 |
| `TestFeatureBannerSectionCommands` | `create()` solo persiste campos permitidos (whitelist), `update()` aplica parcial, `delete()` es soft-delete y excluye del selector admin | 3 |
| `TestFeatureBannerBlockCommands` | `create()` asigna `section` y filtra campos, `update()` soporta `remove_image`, `reorder()` reasigna `display_order` por posicion, `delete()` es soft-delete | 4 |
| `TestFeatureBannerSectionSelectorVisibility` | El filtro de visibilidad real ocurre en el backend: seccion oculta excluida de `list_active_with_blocks()`, bloque inactivo excluido pero la seccion se mantiene | 2 |
| `TestFeatureBannerInHomeFeed` | `GET core/home-feed/` expone `feature_banner_sections` con sus bloques y campos de boton; seccion oculta no aparece; crear una seccion invalida el cache de home-feed | 3 |

**Total: 21/21 passed** (`pytest core/tests/test_feature_banner.py -v`, corrida real dentro
del contenedor de desarrollo, sin mocks del ORM ni de la base de datos).

## Regresion

`pytest core/tests/` (suite completa de `core`, incluyendo los tests preexistentes de
`test_models_and_signals.py`): **30 passed, 1 failed**. El unico test que falla
(`TestCacheInvalidationOnDelete::test_footer_link_deletion_invalidates_cache`) es
**preexistente y no relacionado con Feature Banner** -- se confirmo ejecutandolo aislado
(sin que `test_feature_banner.py` sea recolectado) y sigue fallando igual; ademas no toca
ningun archivo modificado por este modulo (`core/signals.py` mantiene intacto el receiver de
`FooterLink`/`FOOTER_CACHE_KEY`, sin relacion con `FeatureBannerSection`/`Block`). No se
intento corregir por estar fuera del alcance de este plan.

## Nota sobre el entorno de ejecucion

El contenedor Docker de desarrollo (`ecommerce_sintel_django`, imagen `runtime`) no incluye
`pytest`/`pytest-django` por defecto -- esas dependencias viven en el grupo `dev` de
`pyproject.toml`, excluido de la imagen de produccion/runtime. Para esta verificacion se
instalaron temporalmente dentro del contenedor en ejecucion (`pip install`, como root, sin
tocar la imagen ni el `Dockerfile`). Quedan instaladas en el contenedor de desarrollo local
para facilitar corridas futuras; no afecta la imagen versionada ni el despliegue.
