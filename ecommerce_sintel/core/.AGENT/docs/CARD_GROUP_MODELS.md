# Card Group Section — Modelos

Fecha: 2026-08-06. `HomeCardGroup`/`HomeCard` (`core/models.py`) extendidos con los campos
de Card Group Section. Ningún modelo nuevo.

## `HomeCardGroup` (el "Card Group Section")

Campos preexistentes (sin cambios): `name`, `title`, `display_order`, `is_visible`,
`subtitle`, `description`, `bg_color`, `bg_image`, `layout_type` (grid/slider/cards/
timeline/tabs/accordion/logos/marquee), `padding`, `divider`, `columns`, `glass`, `hover`.

Campos nuevos:

| Campo | Tipo | Default | Uso |
|---|---|---|---|
| `columns_tablet` | `PositiveSmallIntegerField` | 2 | Columnas del grid en tablet (`layout_type` grid/cards). |
| `columns_mobile` | `PositiveSmallIntegerField` | 1 | Columnas del grid en mobile. |
| `gap` | `DecimalField(4,2)` | 1.25 | Espaciado entre tarjetas, en rem (grid y slider). |
| `carousel_autoplay` | `BooleanField` | False | Solo con efecto si `layout_type='slider'`. |
| `carousel_loop` | `BooleanField` | True | idem. |
| `carousel_speed` | `PositiveIntegerField` | 40 | px/segundo del autoscroll. |
| `show_arrows` | `BooleanField` | True | idem. |
| `show_indicators` | `BooleanField` | True | idem. |

`autoplay` por defecto es `False`: los grupos `slider` ya configurados antes de este cambio
se ven exactamente igual hasta que el admin active autoplay explícitamente.

## `HomeCard` (el "Card")

Campos preexistentes (sin cambios): `title`, `subtitle`, `description`, `group_name`,
`icon_class`, `background_color`, `image`, `video`, `redirect_url`, `display_order`,
`is_active`, `card_type` (9 variantes visuales), `animation`, `is_featured`, `priority`,
`badge_text`.

Campos nuevos:

| Campo | Tipo | Default | Uso |
|---|---|---|---|
| `badge_color` | `CharField` | `#2563eb` | El badge estaba hardcodeado a azul en `CardItem.vue`. |
| `url_type` | `CharField`, choices `INTERNA/EXTERNA/ANCHOR` | `INTERNA` | Reemplaza la inferencia por regex (`redirect_url.startsWith('http')`) de `CardItem.vue::navigate()`. |
| `url_target` | `CharField`, choices `_self/_blank` | `_self` | Solo relevante si `url_type=EXTERNA`. |
| `stats` | `JSONField`, `[{label, value}]` | `[]` | Chips genéricos — cubre duración, precio, stock, cliente, ubicación, certificación, etc. **sin un campo dedicado por cada tipo de contenido futuro**. Mismo shape que `FeatureBannerBlock.stats`. |
| `secondary_label` | `CharField` | `''` | Botón secundario — texto. |
| `secondary_icon` | `CharField` | `''` | idem — ícono `bi-*`. |
| `secondary_url` | `CharField` | `''` | idem — URL. |
| `secondary_url_type` | `CharField`, choices `INTERNA/EXTERNA/ANCHOR` | `INTERNA` | idem. |
| `secondary_target` | `CharField`, choices `_self/_blank` | `_self` | idem. |

## Validación

`HomeCard` no tenía `clean()`/`full_clean()` en `save()` antes de este cambio — se agregó:

```python
def clean(self):
    errors = {}
    err = validate_url_type_pair(self.url_type, self.redirect_url)
    if err: errors['redirect_url'] = err
    err = validate_url_type_pair(self.secondary_url_type, self.secondary_url)
    if err: errors['secondary_url'] = err
    if errors: raise ValidationError(errors)

def save(self, *args, **kwargs):
    self.full_clean()
    super().save(*args, **kwargs)
```

`validate_url_type_pair()` (`core/validators.py`, nuevo) centraliza la regla INTERNA→`/`,
EXTERNA→`http(s)://`, ANCHOR→`#` — la misma que ya usaba `FeatureBannerBlock`, que se
refactorizó para llamar a este helper en vez de reimplementar la regla una segunda vez.

## Migración y backfill de datos

`core/migrations/0029_card_group_section_fields.py`: migración aditiva (17 campos nuevos)
más un `RunPython`:

```python
def backfill_url_type(apps, schema_editor):
    HomeCard = apps.get_model('core', 'HomeCard')
    HomeCard.objects.filter(redirect_url__startswith='http').update(url_type='EXTERNA')
```

Aplica **la misma regla** que tenía `CardItem.vue::navigate()` una sola vez sobre las 55+
tarjetas ya configuradas, para que `url_type` (default `INTERNA`) no quede en un estado
ambiguo para las URLs externas ya existentes. Verificado tras aplicar: 0 tarjetas requerían
`EXTERNA` en los datos reales de este entorno (ninguna usaba `http://`/`https://` en
`redirect_url`); las 67 tarjetas quedaron en `INTERNA`, coherente con sus valores reales
(rutas que empiezan con `/`).
