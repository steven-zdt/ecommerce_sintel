# ARQUITECTURA COMPLETA — APP core

**Ultima actualizacion:** 2026-07-15

## Responsabilidad

Gestiona el contenido publico del sitio: landing page, home feed agregado, grupos de tarjetas editables (con Constructor Visual), navegacion (navbar/footer nav), banners, CTA final y modulos. Expone 4 endpoints publicos sin autenticacion:

**[CAMBIO 2026-07-12] `core` ya NO es dueno de datos institucionales de la empresa.**
`SiteBrandConfig` (marca), `CompanyContactInfo` (contacto) y las filas de
`FooterLink` con `category='social'` se migraron a la nueva app `organization`
(`Company`, `Branding`, `ContactInfo`, `SocialLink`) — ver
`Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md`
y `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`. `core`
sigue exponiendo los mismos 4 endpoints publicos y los mismos endpoints de
`dashboard/`, pero ahora **consume** esos datos vía `OrganizationSelector`/
`OrganizationCommands` en vez de poseerlos. `core` retiene unicamente
contenido de la propia pagina de inicio (banners, tarjetas, modulos, CTA) y
navegacion del sitio (`NavbarLink`, `FooterLink` solo `category='nav'`).

1. `home-feed` — Contenido destacado (productos, servicios, equipos, flash offers, tarjetas, grupos de tarjetas, titulos de grupos, CTA final, slider de marcas/clientes)
2. `footer` — Columnas de navegacion (`FooterGroup` + `FooterLink`), redes sociales, contacto
3. `site-config` — Marca, logo, navbar
4. `about-us` *(nuevo 2026-07-19)* — Filosofia institucional: historia, mision, vision, valores (`AboutUsConfig` + `AboutUsValue`)
5. `enums/{name}` — Catalogo contract-first de enums compartidos (badges/labels) consumido por todo el frontend, no solo por landing/home

Cada endpoint de contenido (1-3) usa **cache manual con claves conocidas** (5 min TTL). `enums/{name}` NO usa cache (es estatico en memoria por request, de costo insignificante). La invalidacion de cache se realiza por dos vias:
- **Signals automaticos** — `core/signals.py` (registrado en `apps.py`) invalida por `post_save`/`post_delete`. Cubre 8 modelos; **NO cubre `HomeCardGroup`** (decision de diseno intencional, ver seccion Cache Strategy).
- **Invalidacion explicita** — `dashboard/api/views.py` llama `_invalidate_home_feed_cache()` / `_invalidate_footer_cache()` / `_invalidate_site_config_cache()` en cada write de los ViewSets admin, incluyendo los 2 modelos sin signal.

---

## Estructura de Directorios

```
core/
├── models.py                          # 10 modelos (2026-07-15: +BrandSliderItem/BrandSliderConfig/FooterGroup)
├── apps.py                            # CoreConfig.ready() importa core.signals
├── signals.py                         # Signal handlers para invalidacion de cache (10 modelos)
├── urls.py                            # router.register(r'', HomeFeedView)
├── audit_queries.py                   # Queries de auditoria ad-hoc
├── api/
│   ├── views.py                       # HomeFeedView (3 endpoints publicos + enums/{name})
│   └── serializers.py                 # serializers (lectura y entrada) + normalize_icon_class()/ICON_SHORTHAND_MAP
├── services/
│   └── selectors.py                   # Selector/Commands classes (incluye FooterGroup*, BrandSlider*)
├── migrations/
│   ├── 0001_initial.py                # HomeBanner, HomeModuleConfig
│   ├── 0002_...                       # UUID index fix
│   ├── 0003_homebanner_video.py
│   ├── 0004_homecard.py
│   ├── 0005_homecard_media.py
│   ├── 0006_footer_models.py          # FooterLink, CompanyContactInfo
│   ├── 0007_homemoduleconfig_custom_fields.py
│   ├── 0008_homemoduleconfig_background_image.py
│   ├── 0009_sitebrandconfig_navbarlink.py
│   ├── 0010_alter_navbarlink_updated_at_and_more.py
│   ├── 0011_homecardgroup.py          # HomeCardGroup (2026-06-30)
│   ├── 0012_visual_builder.py         # HomeModuleConfig.display_type/layout_config (2026-06-30)
│   ├── 0013_homebanner_visual_fields.py # HomeBanner.eyebrow/background_color/cta_ghost_* (2026-06-30)
│   ├── 0014_footer_cta_config.py      # FooterCTAConfig nuevo modelo (2026-06-30)
│   ├── 0015_expand_display_choices.py # Amplia DISPLAY_CHOICES a 18 tipos + ajustes de indices (2026-06-30)
│   ├── 0016_alter_companycontactinfo_address_and_more.py # Ampliacion de max_length (2026-07-01)
│   ├── 0017_migrate_company_data_to_organization.py # Data migration -> organization (2026-07-12)
│   ├── 0018_delete_companycontactinfo_delete_sitebrandconfig.py # Elimina los 2 modelos migrados (2026-07-12)
│   ├── 0019_seed_renting_home_cards.py
│   ├── 0020_homecard_badge_text_homecardgroup_glass_and_more.py
│   ├── 0021_alter_homecardgroup_layout_type.py
│   ├── 0022_brandsliderconfig_brandslideritem.py # Slider de Marcas/Clientes (2026-07-15)
│   ├── 0023_footergroup.py            # FooterGroup + FooterLink.group FK (nullable) + open_new_tab (2026-07-15)
│   ├── 0024_backfill_footer_groups.py # Data migration: FooterLink.group_name -> FooterGroup (2026-07-15)
│   └── 0025_footerlink_finalize_group.py # FooterLink.group NOT NULL + elimina group_name (2026-07-15)
└── tests/
    └── test_models_and_signals.py
```

---

## Modelos

**Base:** todos extienden `SintelBaseModel` (uuid, created_at, updated_at, is_deleted).

### 1. HomeBanner

```python
class HomeBanner(SintelBaseModel):
    title             = CharField(max_length=255)
    subtitle          = CharField(max_length=500, blank=True, default='')
    eyebrow           = CharField(max_length=150, blank=True, default='')       # (2026-06-30)
    image             = ImageField(upload_to='home_banners/images/', null=True, blank=True)
    video             = FileField(upload_to='home_banners/videos/', null=True, blank=True)
    background_color  = CharField(max_length=30, blank=True, default='')        # (2026-06-30)
    link_url          = CharField(max_length=500, blank=True, default='')
    link_label        = CharField(max_length=150, blank=True, default='')
    cta_ghost_label   = CharField(max_length=150, blank=True, default='')        # (2026-06-30) boton secundario
    cta_ghost_url     = CharField(max_length=500, blank=True, default='')        # (2026-06-30)
    is_active         = BooleanField(default=True, db_index=True)
    display_order     = PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['display_order', '-created_at']
```

**Validacion:** `clean()` exige `link_label` si `link_url` esta presente. `save()` llama `full_clean()`.

### 2. HomeModuleConfig

```python
class HomeModuleConfig(SintelBaseModel):
    MODULE_SHOP     = 'shop'
    MODULE_RENTING  = 'renting'
    MODULE_SERVICES = 'services'
    MODULE_QUOTES   = 'quotes'

    MODULE_META = {
        'shop':     {'label': 'Tienda',       'url': '/tienda',    'icon': 'bi-shop',             'color': '#3b82f6'},
        'renting':  {'label': 'Alquiler',     'url': '/alquiler',  'icon': 'bi-truck',            'color': '#8b5cf6'},
        'services': {'label': 'Servicios',    'url': '/servicios', 'icon': 'bi-tools',            'color': '#f59e0b'},
        'quotes':   {'label': 'Cotizaciones', 'url': '/cotizar',   'icon': 'bi-file-earmark-text','color': '#10b981'},
    }

    module_key           = CharField(max_length=40, unique=True)
    is_visible           = BooleanField(default=True, db_index=True)
    display_order        = PositiveIntegerField(default=0, db_index=True)
    featured_items_limit = PositiveIntegerField(default=8)
    custom_label         = CharField(max_length=255, blank=True, default='')
    custom_icon          = CharField(max_length=100, blank=True, default='')
    custom_url           = CharField(max_length=300, blank=True, default='')
    custom_color         = CharField(max_length=30,  blank=True, default='')
    background_image     = ImageField(upload_to='home_modules/images/', null=True, blank=True)

    # Constructor Visual (2026-06-30, migr. 0012 + 0015)
    display_type  = CharField(max_length=30, default='grid', choices=DISPLAY_CHOICES)  # 18 tipos: grid, grid_modern,
                                                                                          # slider, carousel, cards_h, cards_v,
                                                                                          # hero, banner, list, timeline,
                                                                                          # accordion, tabs, masonry, highlight,
                                                                                          # premium, compact, split, minimal
    layout_config = JSONField(default=dict, blank=True)  # config libre por display_type (columnas, spacing, etc.)

    class Meta:
        ordering = ['display_order']
```

**Logica de fallback en serializacion:**
```python
label = custom_label or MODULE_META[module_key]['label']
icon  = custom_icon  or MODULE_META[module_key]['icon']
url   = custom_url   or MODULE_META[module_key]['url']
color = custom_color or MODULE_META[module_key]['color']
```

**Validacion:** `clean()` acepta claves fuera de MODULE_META solo si `custom_label`, `custom_url` y `custom_icon` estan completos. `save()` llama `full_clean()`.

### 3. HomeCard

```python
class HomeCard(SintelBaseModel):
    title            = CharField(max_length=255)
    subtitle         = CharField(max_length=500, blank=True, default='')
    description      = TextField(blank=True, default='')
    group_name       = CharField(max_length=150, db_index=True)  # clave tecnica de agrupacion
    icon_class       = CharField(max_length=100, default='bi-star')
    background_color = CharField(max_length=30, default='#3b82f6')
    image            = ImageField(upload_to='home_cards/images/', null=True, blank=True)
    video            = FileField(upload_to='home_cards/videos/', null=True, blank=True)
    redirect_url     = CharField(max_length=500, blank=True, default='')
    display_order    = PositiveIntegerField(default=0, db_index=True)
    is_active        = BooleanField(default=True, db_index=True)

    # Constructor Visual (2026-06-30, migr. 0012)
    card_type   = CharField(max_length=30, default='vertical', choices=CARD_TYPE_CHOICES)  # vertical, horizontal,
                                                                                              # premium, compact, glass,
                                                                                              # dark, gradient, image_bg
    animation   = CharField(max_length=30, blank=True, default='')
    is_featured = BooleanField(default=False, db_index=True)
    priority    = PositiveIntegerField(default=0)

    class Meta:
        ordering = ['group_name', 'display_order']
```

**Relacion con HomeCardGroup:** `HomeCard.group_name` es la clave tecnica. `HomeCardGroup.name` mapea esa clave a un titulo editable por el admin. No hay FK — relacion por valor de cadena.

### 4. HomeCardGroup

```python
class HomeCardGroup(SintelBaseModel):
    name          = CharField(max_length=150, unique=True, db_index=True)  # clave == HomeCard.group_name
    title         = CharField(max_length=255)                               # titulo publico editable
    display_order = PositiveIntegerField(default=0, db_index=True)
    is_visible    = BooleanField(default=True, db_index=True)

    # Constructor Visual (2026-06-30, migr. 0012)
    subtitle     = CharField(max_length=500, blank=True, default='')
    description  = TextField(blank=True, default='')
    bg_color     = CharField(max_length=30, blank=True, default='')
    bg_image     = ImageField(upload_to='home_groups/', null=True, blank=True)
    layout_type  = CharField(max_length=30, default='grid', choices=LAYOUT_CHOICES)      # grid, slider, cards,
                                                                                            # timeline, tabs, accordion
    padding      = CharField(max_length=20, default='normal', choices=PADDING_CHOICES)   # none, sm, normal, lg, xl
    divider      = BooleanField(default=False)
    columns      = PositiveSmallIntegerField(default=3)

    class Meta:
        ordering = ['display_order', 'name']
```

**Patron upsert:** El admin llama `POST dashboard/home-card-groups/upsert/` con `{name, title, ...campos Visual Builder}`. Si el grupo no existe se crea; si existe se actualiza. No hay FK hacia HomeCard para no romper cards existentes.

**[CORREGIDO 2026-07-09]** `PATCH dashboard/home-card-groups/{uuid}/` (`update_group` en `dashboard/api/views.py`) solo aceptaba `title`, `display_order`, `is_visible` — los campos Visual Builder (`subtitle`, `description`, `bg_color`, `bg_image`, `layout_type`, `padding`, `divider`, `columns`) solo se podian setear via `upsert/`, no via el PATCH por uuid. Corregido: `update_group` ahora acepta el mismo set de campos que `upsert`.

**Sin signal propio:** la invalidacion de cache se hace explicitamente en `AdminHomeCardGroupViewSet` (`_invalidate_home_feed_cache()`), no via signal.

### 5. FooterCTAConfig *(nuevo — migr. 0014, 2026-06-30)*

```python
class FooterCTAConfig(SintelBaseModel):
    """Bloque CTA final antes del footer. Singleton (solo un registro activo)."""
    eyebrow           = CharField(max_length=150, blank=True, default='Empieza hoy')
    title_prefix      = CharField(max_length=255, blank=True, default='Impulsa tu empresa con')
    title_highlighted = CharField(max_length=255, blank=True, default='Sintel Technology')
    subtitle          = CharField(max_length=500, blank=True,
                            default='Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar.')
    btn_primary_label = CharField(max_length=150, blank=True, default='Solicitar cotizacion')
    btn_primary_url   = CharField(max_length=300, blank=True, default='/cotizar')
    btn_ghost_label   = CharField(max_length=150, blank=True, default='Explorar catalogo')
    btn_ghost_url     = CharField(max_length=300, blank=True, default='/tienda')
    is_active         = BooleanField(default=True)
```

**Patron singleton:** `save()` desactiva todos los demas registros cuando `is_active=True`.

**[CORREGIDO 2026-07-09]** Ahora tiene signal propio en `core/signals.py` (`invalidate_home_feed_on_footer_cta_change`, `post_save`+`post_delete` → invalida `HOME_FEED_CACHE_KEY`, no un cache propio, porque `footer_cta` viaja dentro de la respuesta de `home-feed`, no de `footer`). Antes solo se invalidaba manualmente en `AdminFooterCTAViewSet.update_cta()` — la manual sigue ahi tambien (redundante pero inofensiva, mismo patron que los otros 6 modelos con signal).

### 6. FooterGroup *(nuevo — migr. 0023, 2026-07-15)*

```python
class FooterGroup(SintelBaseModel):
    """Columna del footer publico: agrupa FooterLink(category='nav')."""
    title            = CharField(max_length=150)
    icon_class       = CharField(max_length=100, blank=True, default='bi-folder')
    description      = CharField(max_length=500, blank=True, default='')
    background_color = CharField(max_length=30, blank=True, default='')
    text_color       = CharField(max_length=30, blank=True, default='')
    display_order    = PositiveIntegerField(default=0, db_index=True)
    is_active        = BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['display_order', 'title']
```

**Reemplaza el `group_name` de texto libre** que tenia `FooterLink` hasta el
2026-07-14 — el grid publico ahora agrupa por FK real, no por string. Sin
`row_order` (decision explicita del usuario): el grid de 6/4/3/1 columnas por
fila es 100% automatico via flexbox (`CustomerFooter.vue`), nunca manual.

### 6b. FooterLink (actualizado 2026-07-15)

```python
class FooterLink(SintelBaseModel):
    CATEGORY_SOCIAL = 'social'
    CATEGORY_NAV    = 'nav'

    title         = CharField(max_length=255)
    url           = CharField(max_length=500)
    category      = CharField(max_length=10, choices=CATEGORY_CHOICES, default='nav', db_index=True)
    group         = ForeignKey(FooterGroup, related_name='links', on_delete=CASCADE)  # (2026-07-15, reemplaza group_name)
    icon_class    = CharField(max_length=100, blank=True, default='')
    open_new_tab  = BooleanField(default=False)  # (2026-07-15)
    display_order = PositiveIntegerField(default=0, db_index=True)
    is_active     = BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['category', 'display_order']
```

**[CORREGIDO 2026-07-15]** `group_name` (CharField) fue **eliminado** —
migracion en 3 pasos (`0023` crea `FooterGroup` + FK nullable, `0024`
backfilea un `FooterGroup` por cada `group_name` distinto que existiera
(incluye filas soft-deleted/`category='social'` legadas, ya que la columna
pasa a ser NOT NULL para TODAS las filas), `0025` hace el FK obligatorio y
borra `group_name`). `category`/`CATEGORY_CHOICES` no cambian — `social`
sigue siendo exclusivamente `organization.SocialLink`, sin FK a
`FooterGroup`.

### 6c. BrandSliderItem / BrandSliderConfig *(nuevo — migr. 0022, 2026-07-15)*

```python
class BrandSliderItem(SintelBaseModel):
    name          = CharField(max_length=150)
    logo          = ImageField(upload_to='brand_slider/logos/', null=True, blank=True)
    website       = CharField(max_length=500, blank=True, default='')
    display_order = PositiveIntegerField(default=0, db_index=True)
    is_active     = BooleanField(default=True, db_index=True)
    open_new_tab  = BooleanField(default=True)

class BrandSliderConfig(SintelBaseModel):
    """Singleton -- una unica fila (mismo criterio que FooterCTAConfig, sin el
    truco de 'desactivar hermanos en save()': Commands.upsert nunca crea una
    segunda fila)."""
    title = CharField(max_length=255, blank=True, default='Marcas y clientes')
    subtitle, autoplay, speed, direction('left'|'right'), loop, pause_on_hover,
    items_desktop(6), items_tablet(4), items_mobile(2), background_color,
    padding_top, padding_bottom (choices de HomeCardGroup.PADDING_CHOICES), is_visible
```

Slider de marcas/clientes con scroll horizontal continuo, CSS puro (sin
Swiper/Embla — decision explicita del usuario). Viaja dentro de
`home-feed.brand_slider = {config, items}`, sin endpoint publico propio. Ver
[[project_brand_slider_icon_renderer]].

### 6d. AboutUsConfig / AboutUsValue *(nuevo — migr. 0026, 2026-07-19)*

```python
class AboutUsConfig(SintelBaseModel):
    """Contenido de la pagina publica 'Sobre Nosotros'. Singleton (una unica fila)."""
    title      = CharField(max_length=255, blank=True, default='Sobre Nosotros')
    subtitle   = CharField(max_length=500, blank=True, default='')
    hero_image = ImageField(upload_to='about_us/hero/', null=True, blank=True)
    history    = TextField(blank=True, default='')
    mission    = TextField(blank=True, default='')
    vision     = TextField(blank=True, default='')
    is_visible = BooleanField(default=True)

class AboutUsValue(SintelBaseModel):
    """Valor/pilar de la filosofia institucional mostrado en 'Sobre Nosotros'."""
    title, description, icon_class(default 'bi-gem'), display_order, is_active
```

Mismo patron singleton+items que `BrandSliderConfig`/`BrandSliderItem` (sin el
truco de "desactivar hermanos en save()" — `AboutUsCommands.upsert_config`
nunca crea una segunda fila). A diferencia del slider de marcas, tiene
**endpoint publico propio** (`GET /api/v1/core/about-us/`) en vez de viajar
dentro de `home-feed` — es su propia pagina (`/nosotros` en el frontend), no
un bloque de la Home. Consumido por
`frontend/src/views/customer/AboutUsView.vue` (publico) y
`frontend/src/modules/core/AboutUsAdminView.vue` (admin, `/panel/nosotros`).

### [MIGRADO 2026-07-12] SiteBrandConfig → `organization.Company` + `organization.Branding`

Ya no existe en `core`. Datos reales copiados via migracion de datos
(`core/migrations/0017_migrate_company_data_to_organization.py`), modelo
eliminado (`0018_delete_companycontactinfo_delete_sitebrandconfig.py`). Ver
`organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`.

### 7. NavbarLink

```python
class NavbarLink(SintelBaseModel):
    label           = CharField(max_length=150)
    url             = CharField(max_length=300)
    icon_class      = CharField(max_length=100, blank=True, default='')
    display_order   = PositiveIntegerField(default=0, db_index=True)
    is_visible      = BooleanField(default=True, db_index=True)
    open_in_new_tab = BooleanField(default=False)

    class Meta:
        ordering = ['display_order']
```

### [MIGRADO 2026-07-12] CompanyContactInfo → `organization.ContactInfo`

Ya no existe en `core`. Mismos campos (`phone`, `email`, `address`,
`working_hours`), mismo patron singleton. Ver
`organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`.

---

## Endpoints Publicos (Sin Autenticacion)

**Vista:** `HomeFeedView(GenericViewSet)` — `permission_classes = []`, `authentication_classes = []`

### GET `/api/v1/core/home-feed/`

**Cache:** `sintel_home_feed_v1`, TTL 300s

**Respuesta (campos actuales):**
```json
{
  "banners": [ {"id": 1, "uuid": "...", "title": "...", "subtitle": "", "eyebrow": "",
                "image": "...", "video": null, "background_color": "",
                "link_url": "/tienda", "link_label": "Ver tienda",
                "cta_ghost_label": "", "cta_ghost_url": "",
                "is_active": true, "display_order": 0, "created_at": "..."} ],
  "modules": [ {"key": "shop", "label": "Tienda", "url": "/tienda", "icon": "bi-shop",
                "color": "#3b82f6", "is_visible": true, "background_image": null} ],
  "flash_offers": [ {"uuid": "...", "name": "...", "discount_percentage": "20.00",
                      "ends_at": "...", "seconds_remaining": 3600,
                      "variant_type": "product", "item_uuid": "...", "item_name": "...",
                      "item_url": "/tienda/producto/...", "item_thumbnail": "..."} ],
  "featured_products":  [ {"uuid": "...", "name": "...", "slug": "...", "type": "product",
                           "is_featured": true, "category_name": "...",
                           "min_price": "150000", "thumbnail": "...",
                           "item_url": "/tienda/producto/..."} ],
  "featured_equipment": [ "..." ],
  "featured_services":  [ "..." ],
  "home_cards": [ {"id": 1, "uuid": "...", "title": "...", "subtitle": "", "description": "",
                    "group_name": "E2E_UI_GROUP 2", "icon_class": "bi-star",
                    "background_color": "#3b82f6", "image": null, "video": null,
                    "redirect_url": "", "display_order": 0, "is_active": true, "created_at": "...",
                    "card_type": "vertical", "animation": "", "is_featured": false, "priority": 0} ],
  "card_group_titles": { "E2E_UI_GROUP 2": "¿Por que elegirnos?" },
  "card_groups": [ {"uuid": "...", "name": "E2E_UI_GROUP 2", "title": "¿Por que elegirnos?",
                     "display_order": 0, "is_visible": true, "subtitle": "", "description": "",
                     "bg_color": "", "bg_image": null, "layout_type": "grid",
                     "padding": "normal", "divider": false, "columns": 3} ],
  "footer_cta": {"uuid": "...", "eyebrow": "Empieza hoy", "title_prefix": "Impulsa tu empresa con",
                 "title_highlighted": "Sintel Technology", "subtitle": "...",
                 "btn_primary_label": "Solicitar cotizacion", "btn_primary_url": "/cotizar",
                 "btn_ghost_label": "Explorar catalogo", "btn_ghost_url": "/tienda",
                 "is_active": true, "updated_at": "..."},
  "brand_slider": {
    "config": {"uuid": "...", "title": "Marcas y clientes", "subtitle": "", "autoplay": true,
               "speed": 3500, "direction": "left", "loop": true, "pause_on_hover": true,
               "items_desktop": 6, "items_tablet": 4, "items_mobile": 2,
               "background_color": "", "padding_top": "normal", "padding_bottom": "normal",
               "is_visible": true, "updated_at": "..."},
    "items": [{"uuid": "...", "name": "Hikvision", "logo": "...", "website": "https://...",
               "display_order": 0, "is_active": true, "open_new_tab": true, "created_at": "..."}]
  }
}
```

**[NUEVO 2026-07-15]** `brand_slider` — agregado por el Slider de
Marcas/Clientes. Ver [[project_brand_slider_icon_renderer]].

**Notas:**
- `card_group_titles` (dict `{group_name_key: titulo}`) y `card_groups` (lista completa `HomeCardGroupSerializer`, con campos Visual Builder) **coexisten** — `card_group_titles` es el formato legado simple, `card_groups` es el nuevo formato usado por `TrustSection.vue` para leer padding/columnas/layout. Llaves ausentes en `card_group_titles` significan que ese grupo no tiene titulo personalizado; el frontend usa `group_name` como fallback.
- `footer_cta` puede ser `null` si no existe ningun `FooterCTAConfig` activo — el frontend debe tener un default local (ver `HomeView.vue`).
- `modules` es lista de dicts (no ModelSerializer) — la serializa `HomeFeedSelector.get_module_configs(request)`. Desde esta auditoria acepta `request` opcional para construir la URL absoluta de `background_image`.

### GET `/api/v1/core/footer/`

**Cache:** `sintel_footer_v1`, TTL 300s

```json
{
  "contact": {"uuid": "...", "phone": "+57...", "email": "...", "address": "...",
              "working_hours": "...", "is_active": true, "updated_at": "..."},
  "social_links": [{"uuid": "...", "title": "Facebook", "url": "https://...",
                    "category": "social", "group_name": "", "icon_class": "bi-facebook",
                    "display_order": 0, "is_active": true, "created_at": "..."}],
  "groups": [
    {"uuid": "...", "title": "Legales", "icon_class": "bi-folder", "description": "",
     "background_color": "", "text_color": "", "display_order": 0,
     "links": [{"uuid": "...", "title": "Terminos", "url": "/terminos", "icon_class": "",
                "open_new_tab": false, "display_order": 0, "is_active": true, "created_at": "..."}]}
  ]
}
```

**[CAMBIO 2026-07-15]** `nav_groups` (agrupado por `group_name` de texto
libre, formato `{title, links}`) fue **reemplazado** por `groups` (agrupado
por FK real `FooterGroup`, con `icon_class`/`description`/colores propios y
`links[].open_new_tab`). `CustomerFooter.vue` y `HomeConfigView.vue` (tab
Footer) se actualizaron en el mismo cambio — ningun consumidor sigue
esperando `nav_groups`. Ver [[project_footer_visual_builder]].

### GET `/api/v1/core/site-config/`

**Cache:** `sintel_site_config_v1`, TTL 300s

```json
{
  "brand": {"uuid": "...", "site_name": "Sintel", "logo": "https://...",
            "tagline": "Tu plataforma de confianza", "updated_at": "..."},
  "navbar_links": [
    {"uuid": "...", "label": "Tienda", "url": "/tienda",
     "icon_class": "bi-shop", "display_order": 1,
     "is_visible": true, "open_in_new_tab": false}
  ]
}
```

### GET `/api/v1/core/about-us/` *(nuevo 2026-07-19)*

**Cache:** `sintel_about_us_v1`, TTL 300s

```json
{
  "config": {"uuid": "...", "title": "Sobre Nosotros", "subtitle": "", "hero_image": null,
             "history": "...", "mission": "...", "vision": "...", "is_visible": true, "updated_at": "..."},
  "values": [{"id": 1, "uuid": "...", "title": "Integridad", "description": "...",
              "icon_class": "bi-gem", "display_order": 0, "is_active": true, "created_at": "..."}]
}
```

`config` nunca es `null` (`get_or_create_config()` asegura una fila con
defaults) — a diferencia de `footer_cta` en `home-feed`. Devuelve el
contenido aunque `is_visible=False`; el frontend (`AboutUsView.vue`) decide
si oculta la pagina, para que el admin pueda previsualizar antes de publicar.

### GET `/api/v1/core/enums/{name}/`

**Sin cache.** Endpoint contract-first de enums compartidos consumido por `useEnums.ts` en todo el panel admin (no solo landing/home). Si `name` no existe en el catalogo interno retorna `404 {"detail": "..."}`.

**Catalogo actual (17 claves):** `order-statuses`, `payment-statuses`, `payment-methods`, `service-priorities`, `service-order-statuses`, `rental-statuses`, `quote-statuses`, `operation-statuses`, `operation-types`, `quote-types`, `kyc-verification-statuses`, `kyc-document-statuses`, `service-operation-statuses`, `shipment-statuses` *(2026-07-09, ver [[project_shop_operations_module]])*, `order-payment-methods`, `contractor-types`, `user-types`.

```json
{ "name": "shipment-statuses", "values": {
  "PREPARING": {"label": "Preparando", "class": "bg-secondary-subtle text-secondary border border-secondary-subtle"},
  "delivered": {"label": "Entregado", "class": "bg-success-subtle text-success border border-success-subtle"}
}}
```

**Nota de mantenimiento:** cada app duena de un modelo con estados (`orders.Shipment`, `technical_services.ServiceOperation`, `kyc.UserVerification`, etc.) es responsable de agregar su catalogo aqui cuando expone un badge nuevo en el panel admin — `core/api/views.py::enums()` importa esos modelos directamente (no hay indireccion via signal ni registro dinamico). Ver `frontend/src/composables/useEnums.ts` para el consumo (incluye una `fallbackCatalog()` local para los enums historicos; los nuevos requieren forzar reactividad manualmente si se leen antes de que `ensure()` resuelva — ver [[project_renting_operations_module]] y memorias de Technical Services de esta sesion).

---

## Selectores y Commands (`core/services/selectors.py`)

### HomeConfigSelector

```python
list_banners_active()           # banners activos y no eliminados, por display_order
list_banners_for_admin()        # todos (incluidos inactivos)
get_banner_by_uuid(uuid)        # get_object_or_404
list_module_configs()           # todos los modulos ordenados
get_module_config_by_uuid(uuid)
get_or_create_default_modules() # asegura 4 modulos con defaults
```

### HomeConfigCommands

```python
create_banner(title, subtitle='', link_url='', link_label='', display_order=0, image=None, video=None)
update_banner(banner, data)     # data = {'title': '...', 'is_active': True, 'eyebrow', 'background_color',
                                 #         'cta_ghost_label', 'cta_ghost_url', ...}
deactivate_banner(banner)       # is_active=False, is_deleted=True
update_module_config(config, data)  # incluye 'display_type', 'layout_config' (Constructor Visual)
create_module(module_key, custom_label='', custom_icon='bi-grid',
              custom_url='/', custom_color='#6b7280',
              is_visible=True, display_order=0,
              featured_items_limit=8, background_image=None,
              display_type='grid', layout_config=None)
delete_module(config)           # soft delete (is_deleted=True)
```

### HomeCardSelector

```python
list_active()       # is_active=True, is_deleted=False, orden: group_name, display_order
list_for_admin()    # is_deleted=False
get_by_uuid(uuid)   # get_object_or_404
```

### HomeCardCommands

```python
create_card(title, subtitle='', description='', group_name='',
            icon_class='bi-star', background_color='#3b82f6',
            redirect_url='', display_order=0, image=None, video=None,
            card_type='vertical', animation='', is_featured=False, priority=0)
update_card(card, data)
delete_card(card)   # is_active=False, is_deleted=True
```

### HomeCardGroupSelector

```python
list_all()          # is_deleted=False, orden: display_order, name
get_titles_map()    # {g.name: g.title} — solo is_visible=True, is_deleted=False
get_by_uuid(uuid)   # get_object_or_404
get_by_name(name)   # .first() o None
```

### HomeCardGroupCommands

```python
@transaction.atomic
upsert(name, title, display_order=0, is_visible=True, **kwargs)
    # kwargs Constructor Visual: subtitle, description, bg_color, bg_image,
    # layout_type, padding, divider, columns
    # Busca por name; si existe actualiza, si no crea

@transaction.atomic
update(group, data)     # data puede incluir title, display_order, is_visible + Visual Builder
                         # (subtitle, description, bg_color, bg_image, layout_type, padding,
                         # divider, columns) -- dashboard/api/views.py::update_group ya pasa
                         # el set completo desde 2026-07-09

@transaction.atomic
delete(group)           # soft delete (is_deleted=True)
```

### HomeFeedSelector

```python
get_flash_offers()        # delega a MarketingSelector.list_active_flash_offers()
get_featured_products()   # ProductSelector.list_featured()[:limit]
get_featured_equipment()  # RentingSelector.list_featured()[:limit]
get_featured_services()   # ServiceSelector.list_featured()[:limit]
get_module_configs(request=None)  # retorna lista de dicts con label/url/icon/color (fallback MODULE_META);
                                   # request opcional para absolutizar background_image
build_home_feed()         # consolida todo en un dict (no usada por la vista directamente -- la vista
                           # arma su propio dict con card_groups/footer_cta que este metodo no incluye)
_get_limit(module_key)    # lee HomeModuleConfig.featured_items_limit; default 8
```

### SiteBrandSelector / SiteBrandCommands

```python
get_active()            # primer registro con is_active=True, is_deleted=False
upsert(data)            # crea o actualiza el unico registro activo
                        # data puede incluir: site_name, tagline, logo, remove_logo
```

### NavbarLinkSelector / NavbarLinkCommands

```python
list_visible()                                      # is_visible=True, is_deleted=False
list_all()                                          # is_deleted=False
get_by_uuid(uuid)
create(label, url, icon_class='', display_order=0, is_visible=True, open_in_new_tab=False)
update(link, data)
delete(link)    # soft delete
```

### FooterGroupSelector / FooterGroupCommands *(nuevo, 2026-07-15)*

```python
# Selector
list_all()              # is_deleted=False, orden: display_order, title
list_visible()           # is_active=True, is_deleted=False
get_by_uuid(uuid)

# Commands
create(title, icon_class='bi-folder', description='', background_color='', text_color='',
       display_order=0, is_active=True)
update(group, data)
delete(group)            # soft: is_active=False, is_deleted=True
reorder_groups(ordered_uuids)   # @transaction.atomic, mismo patron que BrandSliderCommands.reorder_items
```

### FooterSelector / FooterCommands (actualizado 2026-07-15)

```python
# Selector
list_active_links()         # FooterLink category='nav', is_active=True, is_deleted=False, select_related('group')
list_all_links()            # is_deleted=False, category='nav'
get_link_by_uuid(uuid)
build_footer_payload(contact=None, social_links=None)
    # retorna {'contact': obj, 'social_links': [...], 'groups': [FooterGroup con .visible_links via Prefetch]}
    # (2026-07-15: 'nav_groups' agrupado por group_name -> 'groups' agrupado por FooterGroup FK)

# Commands
create_link(title, url, category, group=None, icon_class='', open_new_tab=False, display_order=0)
update_link(link, data)     # 'group' ahora es una instancia FooterGroup, no un string group_name
delete_link(link)           # is_active=False, is_deleted=True
reorder_links(ordered_uuids)  # @transaction.atomic (2026-07-15, drag&drop dentro de un grupo)
```
`upsert_contact()` ya no vive aqui — es `OrganizationCommands.upsert_contact_info()` desde el
2026-07-12 (`CompanyContactInfo` migro a `organization.ContactInfo`).

### FooterCTASelector / FooterCTACommands *(nuevo, 2026-06-30)*

```python
# Selector
get_active()            # primer registro con is_active=True, is_deleted=False

# Commands
@transaction.atomic
upsert(data)            # crea (si no existe ninguno) o actualiza el unico registro activo
                         # data puede incluir: eyebrow, title_prefix, title_highlighted, subtitle,
                         # btn_primary_label, btn_primary_url, btn_ghost_label, btn_ghost_url
```

### BrandSliderSelector / BrandSliderCommands *(nuevo, 2026-07-15)*

```python
# Selector
list_items_active()     # is_active=True, is_deleted=False, orden display_order
list_items_for_admin()  # is_deleted=False
get_item_by_uuid(uuid)
get_config() / get_or_create_config()   # singleton, usado por home-feed publico

# Commands
create_item(name, logo=None, website='', display_order=0, is_active=True, open_new_tab=True)
update_item(item, data)
delete_item(item)           # soft delete
reorder_items(ordered_uuids)  # @transaction.atomic, drag&drop del panel
upsert_config(data)          # singleton, nunca crea una segunda fila
```

### AboutUsSelector / AboutUsCommands *(nuevo, 2026-07-19)*

```python
# Selector
list_values_active()     # is_active=True, is_deleted=False, orden display_order
list_values_for_admin()  # is_deleted=False
get_value_by_uuid(uuid)
get_config() / get_or_create_config()   # singleton, usado por about-us publico

# Commands
create_value(title, description='', icon_class='bi-gem', display_order=0, is_active=True)
update_value(value, data)
delete_value(value)           # soft delete
reorder_values(ordered_uuids)  # @transaction.atomic
upsert_config(data)            # singleton, nunca crea una segunda fila; acepta 'remove_hero_image'
```

Ambas clases viven en `core/services/commands.py` (no en `selectors.py` —
sigue el patron real del archivo desde el refactor "Sprint 1" del
2026-07-16, ver nota al inicio de ese archivo; `selectors.py` hoy solo
contiene `HomeConfigSelector`, todo lo demas se movio a `commands.py`).

---

## Cache Strategy

```python
HOME_FEED_CACHE_KEY   = 'sintel_home_feed_v1'     # TTL: 300s
FOOTER_CACHE_KEY      = 'sintel_footer_v1'        # TTL: 300s
SITE_CONFIG_CACHE_KEY = 'sintel_site_config_v1'   # TTL: 300s
ABOUT_US_CACHE_KEY    = 'sintel_about_us_v1'      # TTL: 300s (2026-07-19)
```

### Invalidacion automatica via signals (`core/signals.py`)

| Signal | Modelos cubiertos | Cache invalidada |
|--------|-------------------|-----------------|
| `post_save` + `post_delete` | HomeBanner, HomeCard, HomeModuleConfig, FooterCTAConfig, BrandSliderItem, BrandSliderConfig *(2026-07-15)* | `HOME_FEED_CACHE_KEY` |
| `post_save` + `post_delete` | FooterLink (`category='nav'`), FooterGroup *(2026-07-15)* | `FOOTER_CACHE_KEY` |
| `post_save` + `post_delete` | NavbarLink | `SITE_CONFIG_CACHE_KEY` |
| `post_save` + `post_delete` | AboutUsConfig, AboutUsValue *(2026-07-19)* | `ABOUT_US_CACHE_KEY` |

**[CAMBIO 2026-07-12]** Antes tambien invalidaban `FOOTER_CACHE_KEY`/`SITE_CONFIG_CACHE_KEY`
los signals de `CompanyContactInfo`/`SiteBrandConfig` — esos modelos se migraron a
`organization`, que **no usa signals** (regla del plan de migracion). La invalidacion de esas
2 claves de cache para datos de marca/contacto ahora es **explicita** en
`dashboard/api/views.py` (`_invalidate_site_config_cache()`/`_invalidate_footer_cache()`),
llamada justo despues de `OrganizationCommands.upsert_company/upsert_branding/upsert_contact_info`.

Registrado en `CoreConfig.ready()` via `import core.signals`.

**[GAP CONOCIDO] `HomeCardGroup` sigue sin signal propio** — es intencional (documentado desde 2026-06-30): depende exclusivamente de la invalidacion manual en `AdminHomeCardGroupViewSet`. `FooterCTAConfig` gano su signal el 2026-07-09 (ver Cambios Recientes) porque no habia razon de diseno real para que fuera la excepcion — a diferencia de `HomeCardGroup`, no tiene ninguna caracteristica que justifique omitir el signal.

### Invalidacion explicita (dashboard writes)

- `AdminHomeCardGroupViewSet` llama `_invalidate_home_feed_cache()` en cada write (unico modelo sin signal).
- El resto de ViewSets admin (`AdminHomeConfigViewSet`, `AdminHomeCardViewSet`, `AdminFooterViewSet`, `AdminSiteBrandViewSet`, `AdminNavbarViewSet`, `AdminFooterCTAViewSet`) invalidan de forma redundante ademas del signal — no es un problema (doble `cache.delete()` es idempotente), pero confirma que el signal por si solo ya bastaria para esos 8 modelos.

---

## Serializers (21 en core, 2026-07-12: 2 migrados a organization + 1 reemplazado por adaptador)

### Lectura publica

| Serializer | Modelo/Fuente | Campos clave | Endpoint |
|------------|--------------|--------------|---------|
| `HomeBannerSerializer` | HomeBanner | id, uuid, title, subtitle, eyebrow, image, video, background_color, link_url, link_label, cta_ghost_label, cta_ghost_url, is_active, display_order, created_at | home-feed |
| `FlashOfferCardSerializer` | FlashOffer (marketing) | uuid, name, discount_percentage, ends_at, seconds_remaining, variant_type, item_uuid, item_name, item_url, item_thumbnail | home-feed |
| `FeaturedProductCardSerializer` | Product | uuid, name, slug, type, is_featured, category_name, min_price, thumbnail, item_url | home-feed |
| `FeaturedEquipmentCardSerializer` | Equipment | uuid, name, slug, type, is_featured, category_name, min_price, thumbnail, item_url | home-feed |
| `FeaturedServiceCardSerializer` | TechnicalService | uuid, name, slug, type, is_featured, category_name, thumbnail, item_url | home-feed |
| `HomeCardSerializer` | HomeCard | id, uuid, title, subtitle, description, group_name, icon_class, background_color, image, video, redirect_url, display_order, is_active, created_at, card_type, animation, is_featured, priority | home-feed |
| `HomeCardGroupSerializer` | HomeCardGroup | uuid, name, title, display_order, is_visible, subtitle, description, bg_color, bg_image, layout_type, padding, divider, columns | home-feed (`card_groups`) + dashboard/home-card-groups |
| `FooterCTAConfigSerializer` | FooterCTAConfig | uuid, eyebrow, title_prefix, title_highlighted, subtitle, btn_primary_label, btn_primary_url, btn_ghost_label, btn_ghost_url, is_active, updated_at | home-feed (`footer_cta`) + dashboard/footer-cta |
| `FooterLinkSerializer` | FooterLink | id, uuid, title, url, category, group(uuid), icon_class, open_new_tab, display_order, is_active, created_at | footer |
| `FooterGroupPublicSerializer` *(nuevo 2026-07-15)* | FooterGroup | uuid, title, icon_class, description, background_color, text_color, display_order, links (FooterLinkSerializer anidado via Prefetch) | footer (`groups`) |
| `organization.api.serializers.ContactInfoSerializer` *(migrado 2026-07-12)* | organization.ContactInfo | id, uuid, phone, email, address, working_hours, is_active, updated_at | footer |
| `social_link_to_footer_link_shape()` *(adaptador, no ModelSerializer)* | organization.SocialLink | id, uuid, title(=platform), url, category='social', group_name='', icon_class, display_order, is_active, created_at | footer |
| brand dict construido a mano en `site_config()` *(ya no hay serializer dedicado)* | organization.Company + organization.Branding | uuid, site_name(=trade_name), logo, tagline, updated_at | site-config |
| `NavbarLinkSerializer` | NavbarLink | uuid, label, url, icon_class, display_order, is_visible, open_in_new_tab | site-config |
| `BrandSliderItemSerializer` *(nuevo 2026-07-15)* | BrandSliderItem | id, uuid, name, logo, website, display_order, is_active, open_new_tab, created_at | home-feed (`brand_slider.items`) |
| `BrandSliderConfigSerializer` *(nuevo 2026-07-15)* | BrandSliderConfig | uuid, title, subtitle, autoplay, speed, direction, loop, pause_on_hover, items_desktop, items_tablet, items_mobile, background_color, padding_top, padding_bottom, is_visible, updated_at | home-feed (`brand_slider.config`) |
| `AboutUsConfigSerializer` *(nuevo 2026-07-19)* | AboutUsConfig | uuid, title, subtitle, hero_image, history, mission, vision, is_visible, updated_at | about-us (`config`) |
| `AboutUsValueSerializer` *(nuevo 2026-07-19)* | AboutUsValue | id, uuid, title, description, icon_class, display_order, is_active, created_at | about-us (`values`) |

### Admin (lectura)

| Serializer | Campos extra | Uso |
|------------|-------------|-----|
| `HomeModuleConfigSerializer` | module_label, module_url, module_icon, module_color, is_core (computed) + todos los custom_* + display_type, layout_config | dashboard/home-config |

### Entrada (escritura)

| Serializer | Campos | Accion |
|------------|--------|--------|
| `HomeBannerInputSerializer` | title, subtitle, eyebrow, link_url, link_label, background_color, cta_ghost_label, cta_ghost_url, display_order, is_active, image, video, remove_image, remove_video | crear/editar banner |
| `HomeModuleConfigInputSerializer` | is_visible, display_order, featured_items_limit, custom_*, background_image, remove_background_image, display_type, layout_config | editar modulo |
| `HomeModuleCreateSerializer` | module_key, custom_*, is_visible, display_order, featured_items_limit, background_image, display_type, layout_config | crear modulo |
| `HomeCardInputSerializer` | title, subtitle, description, group_name, icon_class, background_color, image, video, redirect_url, display_order, is_active, card_type, animation, is_featured, priority, remove_image, remove_video | crear/editar tarjeta |
| `HomeCardGroupInputSerializer` | name, title, display_order, is_visible, subtitle, description, bg_color, bg_image, layout_type, padding, divider, columns | upsert grupo de tarjetas |
| `FooterLinkInputSerializer` | title, url, category, group(uuid), icon_class, open_new_tab, display_order, is_active | crear/editar enlace footer |
| `FooterGroupInputSerializer` *(nuevo 2026-07-15)* | title, icon_class, description, background_color, text_color, display_order, is_active | crear/editar columna del footer |
| `FooterGroupReorderSerializer` / `FooterLinkReorderSerializer` *(nuevo 2026-07-15)* | items (lista de uuid) | drag&drop de grupos / enlaces |
| `CompanyContactInfoInputSerializer` | phone, email, address, working_hours | editar contacto |
| `SiteBrandConfigInputSerializer` | site_name, tagline, logo, remove_logo | editar marca |
| `NavbarLinkInputSerializer` | label, url, icon_class, display_order, is_visible, open_in_new_tab | crear/editar enlace navbar |
| `FooterCTAConfigInputSerializer` | eyebrow, title_prefix, title_highlighted, subtitle, btn_primary_label, btn_primary_url, btn_ghost_label, btn_ghost_url | editar CTA final |
| `BrandSliderItemInputSerializer` *(nuevo 2026-07-15)* | name, logo, website, display_order, is_active, open_new_tab, remove_logo | crear/editar logo del slider |
| `BrandSliderConfigInputSerializer` *(nuevo 2026-07-15)* | title, subtitle, autoplay, speed, direction, loop, pause_on_hover, items_desktop, items_tablet, items_mobile, background_color, padding_top, padding_bottom, is_visible | editar config del slider |
| `AboutUsValueInputSerializer` *(nuevo 2026-07-19)* | title, description, icon_class, display_order, is_active | crear/editar valor institucional |
| `AboutUsValueReorderSerializer` *(nuevo 2026-07-19)* | items (lista de uuid) | drag&drop de valores |
| `AboutUsConfigInputSerializer` *(nuevo 2026-07-19)* | title, subtitle, hero_image, remove_hero_image, history, mission, vision, is_visible | editar contenido de Sobre Nosotros |

---

## Endpoints de Escritura (dashboard BFF)

Todos bajo `/api/v1/dashboard/` — requieren JWT admin (`IsAdminUser`).

| Ruta | Metodo | ViewSet | Accion |
|------|--------|---------|--------|
| `dashboard/home-config/banners/` | GET | AdminHomeConfigViewSet | listar banners |
| `dashboard/home-config/banners/create/` | POST | AdminHomeConfigViewSet | crear banner (multipart) |
| `dashboard/home-config/banners/{uuid}/` | PATCH | AdminHomeConfigViewSet | editar banner |
| `dashboard/home-config/banners/{uuid}/delete/` | DELETE | AdminHomeConfigViewSet | borrar banner (soft) |
| `dashboard/home-config/modules/` | GET | AdminHomeConfigViewSet | listar modulos |
| `dashboard/home-config/modules/create/` | POST | AdminHomeConfigViewSet | crear modulo |
| `dashboard/home-config/modules/{uuid}/` | PATCH | AdminHomeConfigViewSet | editar modulo |
| `dashboard/home-config/modules/{uuid}/delete/` | DELETE | AdminHomeConfigViewSet | borrar modulo |
| `dashboard/home-cards/` | GET | AdminHomeCardViewSet | listar tarjetas |
| `dashboard/home-cards/create/` | POST | AdminHomeCardViewSet | crear tarjeta (multipart) |
| `dashboard/home-cards/{uuid}/` | PATCH | AdminHomeCardViewSet | editar tarjeta |
| `dashboard/home-cards/{uuid}/delete/` | DELETE | AdminHomeCardViewSet | borrar tarjeta |
| `dashboard/home-card-groups/` | GET | AdminHomeCardGroupViewSet | listar grupos con titulos |
| `dashboard/home-card-groups/upsert/` | POST | AdminHomeCardGroupViewSet | crear o actualizar grupo (incluye Visual Builder) |
| `dashboard/home-card-groups/{uuid}/` | PATCH | AdminHomeCardGroupViewSet | editar grupo por uuid (title/display_order/is_visible + campos Visual Builder) |
| `dashboard/home-card-groups/{uuid}/delete/` | DELETE | AdminHomeCardGroupViewSet | borrar grupo (soft) |
| `dashboard/footer/contact/` | GET/POST | AdminFooterViewSet | contacto |
| `dashboard/footer/links/` | GET | AdminFooterViewSet | listar enlaces footer |
| `dashboard/footer/links/create/` | POST | AdminFooterViewSet | crear enlace |
| `dashboard/footer/links/{uuid}/` | PATCH | AdminFooterViewSet | editar enlace |
| `dashboard/footer/links/{uuid}/delete/` | DELETE | AdminFooterViewSet | borrar enlace |
| `dashboard/site-brand/` | GET | AdminSiteBrandViewSet | marca global |
| `dashboard/site-brand/update/` | POST/PATCH | AdminSiteBrandViewSet | actualizar (upsert) marca |
| `dashboard/navbar/` | GET | AdminNavbarViewSet | listar links navbar |
| `dashboard/navbar/create/` | POST | AdminNavbarViewSet | crear link |
| `dashboard/navbar/{uuid}/` | PATCH | AdminNavbarViewSet | editar link |
| `dashboard/navbar/{uuid}/delete/` | DELETE | AdminNavbarViewSet | borrar link |
| `dashboard/footer-cta/` | GET | AdminFooterCTAViewSet | obtener config CTA final (default si no existe) |
| `dashboard/footer-cta/update/` | POST/PATCH | AdminFooterCTAViewSet | actualizar (upsert) CTA final |
| `dashboard/footer-groups/` | GET | AdminFooterGroupViewSet | listar columnas del footer *(2026-07-15)* |
| `dashboard/footer-groups/create/` | POST | AdminFooterGroupViewSet | crear columna |
| `dashboard/footer-groups/{uuid}/` | PATCH | AdminFooterGroupViewSet | editar columna |
| `dashboard/footer-groups/{uuid}/delete/` | DELETE | AdminFooterGroupViewSet | borrar columna (soft) |
| `dashboard/footer-groups/reorder/` | POST | AdminFooterGroupViewSet | drag&drop de columnas |
| `dashboard/footer/links/reorder/` | POST | AdminFooterViewSet | drag&drop de enlaces dentro de un grupo *(2026-07-15)* |
| `dashboard/brand-slider/` | GET | AdminBrandSliderViewSet | listar logos del slider *(2026-07-15)* |
| `dashboard/brand-slider/create/` | POST | AdminBrandSliderViewSet | crear logo (multipart) |
| `dashboard/brand-slider/{uuid}/` | PATCH | AdminBrandSliderViewSet | editar logo |
| `dashboard/brand-slider/{uuid}/delete/` | DELETE | AdminBrandSliderViewSet | borrar logo (soft) |
| `dashboard/brand-slider/reorder/` | POST | AdminBrandSliderViewSet | drag&drop de logos |
| `dashboard/brand-slider/config/` | GET | AdminBrandSliderViewSet | obtener config del slider |
| `dashboard/brand-slider/config/update/` | POST/PATCH | AdminBrandSliderViewSet | actualizar (upsert) config del slider |
| `dashboard/about-us/` | GET | AdminAboutUsViewSet | listar valores institucionales *(2026-07-19)* |
| `dashboard/about-us/create/` | POST | AdminAboutUsViewSet | crear valor |
| `dashboard/about-us/{uuid}/` | PATCH | AdminAboutUsViewSet | editar valor |
| `dashboard/about-us/{uuid}/delete/` | DELETE | AdminAboutUsViewSet | borrar valor (soft) |
| `dashboard/about-us/reorder/` | POST | AdminAboutUsViewSet | drag&drop de valores |
| `dashboard/about-us/config/` | GET | AdminAboutUsViewSet | obtener config de Sobre Nosotros |
| `dashboard/about-us/config/update/` | POST/PATCH | AdminAboutUsViewSet | actualizar (upsert) config |

**Nota:** `create_link`/`update_link` de `AdminFooterViewSet` siguen
despachando entre `core.FooterLink` (`category='nav'`, ahora requiere
`group` uuid) y `organization.SocialLink` (`category='social'`, sin FK a
`FooterGroup`) exactamente igual que antes del 2026-07-15 — el cambio de
`group_name` a `group` no toco esa rama.

---

## Frontend — Consumo de core

### HomeView.vue (`src/views/customer/HomeView.vue`)

```javascript
const [feedRes, configRes] = await Promise.all([
  api.get('core/home-feed/'),
  api.get('core/site-config/'),
]);

banners.value           = data.banners            || [];
modules.value           = data.modules            || [];
flashOffers.value       = data.flash_offers       || [];
featuredProducts.value  = data.featured_products  || [];
featuredEquipment.value = data.featured_equipment || [];
featuredServices.value  = data.featured_services  || [];
homeCards.value         = data.home_cards         || [];
cardGroupTitles.value   = data.card_group_titles  || {};
cardGroups.value        = data.card_groups        || [];
if (data.footer_cta) footerCta.value = data.footer_cta;  // conserva default local si es null
```

`cardGroupTitles` se pasa como prop `:groupTitles="cardGroupTitles"` a `TrustSection.vue`; `cardGroups` (visible-only, via `computed`) alimenta el layout Visual Builder de esa misma seccion; `footerCta` se pasa a `<FooterCTA :config="footerCta" />` (`src/components/ui/landing/FooterCTA.vue`).

### TrustSection.vue (`src/components/ui/landing/TrustSection.vue`)

- Prop `groupTitles: { type: Object, default: () => ({}) }`
- Agrupa cards por `c.group_name`
- Muestra `:title="props.groupTitles[groupName] || groupName"` en `SectionHeader`

### HomeConfigView.vue (`src/modules/core/HomeConfigView.vue`)

Panel admin de una sola pagina con 8 secciones (no tabs con router, todas montadas y controladas con `v-show`/scroll): **Modulos**, **Banners**, **Tarjetas**, **Footer** (contacto + columnas `FooterGroup` con drag&drop + enlaces por columna con su propio drag&drop + redes sociales), **Marca**, **Navbar**, **CTA Final**, **Slider de Marcas** *(nueva, 2026-07-15: config + logos con drag&drop)*. Cada seccion llama 1:1 los endpoints de la tabla anterior. Los inputs de icono (Footer/BrandSlider) usan `normalizeIconInput()` (`frontend/src/utils/iconShorthand.js`) para vista previa en vivo via `IconRenderer`.

- Tab "Tarjetas" — edicion inline del titulo por grupo:
  - `groupTitlesMap`: `ref({})` — mapa `{name: title}` cargado desde `GET dashboard/home-card-groups/`
  - `startEditGroupTitle(gName)` / `saveGroupTitle(gName)` — usan solo `title` (edicion rapida inline via `upsert/`)
  - Invalidacion implicita: el ViewSet llama `_invalidate_home_feed_cache()` internamente
- Tab "Modulos" — el boton "Editar" de cada modulo abre `ModuleBuilderModal.vue` para el Constructor Visual completo (`display_type`, `layout_config`, y demas campos), no un form inline.

### ModuleBuilderModal.vue (`src/modules/core/ModuleBuilderModal.vue`, ~1542 lineas) *(nuevo, 2026-06-30)*

Modal con pestanas (`general`, y al menos una pestana de diseno/layout) para crear/editar un `HomeModuleConfig` con todos los campos del Constructor Visual (`display_type` entre los 18 tipos disponibles, `layout_config` JSON libre, colores, textos). Recibe `props.module` (null = creacion) y emite `close`/`saved`. Es el unico punto de la UI donde se edita `display_type`/`layout_config` — el form inline de la seccion "Modulos" en `HomeConfigView.vue` solo cubre visibilidad/orden/limite.

---

## Anti-Patrones Prohibidos

```python
# NO: queries N+1 en home-feed — usar select_related en los Selectors de cada app
for product in ProductSelector.list_featured():
    product.category.name  # N+1

# NO: autenticacion en endpoints publicos
permission_classes = [IsAuthenticated]  # rompe landing page (sin auth publica)

# NO: cache.clear() masivo — usar cache.delete(key) selectivo
cache.clear()  # invalida todas las claves, no solo las del home

# NO: limites hardcoded en vistas
products = ProductSelector.list_featured()[:8]  # usar HomeModuleConfig.featured_items_limit

# NO: FK de HomeCardGroup a HomeCard — la relacion es por valor de cadena (group_name)
# Agregar FK romperia cards existentes sin grupo registrado
class HomeCardGroup(SintelBaseModel):
    cards = ManyToManyField(HomeCard)  # PROHIBIDO

# NO: ignorar el fallback de group_name en frontend
# Si card_group_titles no tiene la clave, mostrar group_name como fallback (no vacio)
title = groupTitles[groupName]          # puede ser undefined => bug visual
title = groupTitles[groupName] || groupName  # CORRECTO

# NO: agregar un enum nuevo en core/api/views.py::enums() sin agregarlo tambien al
# 'catalog' dict que valida 404 -- si se olvida, el frontend recibe 404 silencioso
# y useEnums.ts cae al fallback generico sin avisar visualmente.

# NO: asumir que un modelo nuevo sin FK a User/Order en core hereda invalidacion de cache
# automaticamente -- HomeCardGroup demuestra que si no se registra un signal en
# core/signals.py, CUALQUIER escritura fuera de su ViewSet admin (shell, comando,
# fixture) dejara la cache de home-feed desactualizada hasta el TTL de 300s. Es la unica
# excepcion intencional que queda; todo modelo nuevo deberia registrar su signal salvo
# que haya una razon explicita para no hacerlo (documentarla si se omite).
```

---

## Cambios Recientes

### 2026-07-15 — Slider de Marcas/Clientes + Footer Visual Builder + IconRenderer

Dos modulos nuevos completos, mas una correccion de renderizado de iconos
(ver memorias [[project_brand_slider_icon_renderer]] y
[[project_footer_visual_builder]] para el detalle completo de cada sesion):

- **`BrandSliderItem`/`BrandSliderConfig`** (migr. 0022): slider de logos con
  scroll continuo, CSS puro (sin Swiper/Embla). Viaja en
  `home-feed.brand_slider = {config, items}`.
- **`FooterGroup`** (migr. 0023-0025): reemplaza `FooterLink.group_name`
  (texto libre, eliminado) por una FK real con icono/color/descripcion
  propios. `footer.nav_groups` renombrado a `footer.groups` con la forma
  rica `{title, icon_class, description, background_color, text_color,
  links[]}`. Grid publico 6/4/3/1 columnas por fila 100% automatico
  (flexbox, sin `row_order` manual — decision explicita del usuario).
  `FooterLink` gano `open_new_tab`. Redes sociales
  (`organization.SocialLink`) quedaron fuera de alcance, sin cambios.
- **`IconRenderer.vue`** (`frontend/src/components/ui/IconRenderer.vue`):
  unico componente de render de iconos Bootstrap Icons del proyecto. Valida
  si la clase existe midiendo `getComputedStyle(el, '::before').content` en
  el DOM (sin lista propia que mantener), cae a `bi-question-circle` si no.
  `core/api/serializers.py::normalize_icon_class()` (+ `ICON_SHORTHAND_MAP`)
  normaliza atajos como `camera`→`bi-camera-video`,
  `shield`→`bi-shield-check`, `alarm`→`bi-bell` antes de guardar en BD.
- **Bug real corregido en el mismo dia**: 3 componentes publicos usaban
  `RouterLink` sin detectar URLs externas absolutas (`https://...`), por lo
  que un `custom_url`/`btn_primary_url`/`btn_ghost_url`/`NavbarLink.url`
  externo quedaba silenciosamente roto — `ModuleCard.vue`, `FooterCTA.vue`,
  `CustomerNavbar.vue` (mas un bug relacionado en `BrandSlider.vue` que
  anulaba el `href` segun `open_new_tab`). Corregidos reutilizando el patron
  `isExternal` ya existente en `HeroCTA.vue`.
- **Migracion de datos real**: `core/migrations/0024_backfill_footer_groups.py`
  debio cubrir TODAS las filas de `FooterLink` (no solo `category='nav',
  is_deleted=False`) porque el `AlterField` de `0025` exige `group` NOT NULL
  para cada fila de la tabla, incluidas legadas soft-deleted/`social` — gap
  real encontrado y corregido en la propia migracion antes de aplicarla a
  produccion.
- **Verificado en produccion** el mismo dia (`sintel_prod_*`): tras
  `build --no-cache` + `up -d`, nginx debio reiniciarse aparte
  (`docker restart sintel_prod_nginx`) porque quedo con la IP vieja de
  `django` cacheada — bug real de deploy, no de codigo de esta feature (ver
  `feedback_nginx_stale_dns_after_django_recreate` en memoria de sesion).
- **Auditoria de sincronizacion `ai_engine`** (mismo dia): `PROJECT_MAP.json`
  y derivados llevaban desde 2026-07-11 sin regenerar (`organization`
  invisible para el motor, `core` con 9 migraciones de menos, modelos
  fantasma `SiteBrandConfig`/`CompanyContactInfo` todavia listados como
  vivos) — corregido: `organization` agregado a `DJANGO_APPS`/`API_PREFIXES`/
  keywords en `auditor.py`/`incremental_updater.py`/`loaders.py`/
  `retrievers.py`/`project_map.py`, globs de ingesta de Vue ampliados
  (`components/ui/*`, `components/ui/landing/*`, `components/customer/*`
  no se ingestaban en absoluto), `PROJECT_MAP.json` regenerado.

### 2026-07-12 — Migracion de datos institucionales a `organization`

A peticion explicita del usuario ("core solo debe operar como una app de administracion y
supervision"): `SiteBrandConfig`, `CompanyContactInfo` y `FooterLink(category='social')`
se migraron a la nueva app `organization` (`Company`, `Branding` — separados en 2 modelos
por decision del usuario —, `ContactInfo`, `SocialLink`). `core` deja de poseer datos
institucionales de la empresa.

- **Migracion de datos real**: `core/migrations/0017_migrate_company_data_to_organization.py`
  (RunPython) copio el `SiteBrandConfig`/`CompanyContactInfo` activos y las 4 filas sociales
  reales de produccion (WhatsApp, Instagram, Facebook, LinkedIn) antes de que
  `0018_delete_companycontactinfo_delete_sitebrandconfig.py` eliminara los modelos.
- **`core/services/selectors.py`**: eliminados `SiteBrandSelector`/`SiteBrandCommands`;
  `FooterSelector.build_footer_payload()` ahora combina `FooterLink` (solo nav) con
  `OrganizationSelector.get_contact_info()`/`list_social_links()`.
- **`core/api/views.py`**: `site_config()` combina `organization.Company` +
  `organization.Branding` en la misma forma JSON `{uuid, site_name, logo, tagline,
  updated_at}` de siempre — el frontend no cambia. `footer()` usa el adaptador
  `social_link_to_footer_link_shape()` (`core/api/serializers.py`) para que `SocialLink`
  seguir viendose como `FooterLink(category='social')` en la respuesta publica.
- **`core/signals.py`**: eliminados los handlers de `SiteBrandConfig`/`CompanyContactInfo`
  (esos modelos ya no existen aqui; `organization` no usa signals por diseno). La
  invalidacion de `SITE_CONFIG_CACHE_KEY`/`FOOTER_CACHE_KEY` para esos datos es ahora
  explicita en `dashboard/api/views.py`.
- **`dashboard/api/views.py`** (`AdminFooterViewSet`, `AdminSiteBrandViewSet`): reescritos
  para leer/escribir en `organization` en vez de `core`, manteniendo el MISMO contrato HTTP
  (`dashboard/footer/*`, `dashboard/site-brand/*`) para no romper `HomeConfigView.vue` antes
  de la Fase 6 ("Frontend SPA" es el ultimo consumidor en migrar, todavia sin tocar).
  `create_link`/`update_link`/`delete_link` despachan entre `core.FooterLink` (nav) y
  `organization.SocialLink` (social) segun `category`, con lookup dual por `uuid` en
  update/delete ya que ahora son 2 tablas distintas.
- **`FooterLinkInputSerializer.category`** ahora solo acepta `'nav'` (antes aceptaba
  `'social'` tambien) — evita que se vuelva a crear un enlace social duplicado directamente
  en `core.FooterLink`; `dashboard` intercepta `category='social'` ANTES de llegar a este
  serializer y lo enruta a `OrganizationCommands`.
- Ver detalle completo de la auditoria y las decisiones de diseno confirmadas en
  `Documentacion/Arquitectura_general/MIGRACION_ORGANIZATION_FASE1_AUDITORIA.md` y
  `organization/.AGENT/docs/ARQUITECTURA_COMPLETA_ORGANIZATION.md`.

### 2026-07-09 (b) — Correcciones de codigo tras la auditoria

Aplicadas inmediatamente despues de la auditoria de alineacion (ver entrada anterior), a peticion explicita de corregir los 2 gaps reales detectados:

- **`dashboard/api/views.py::AdminHomeCardGroupViewSet.update_group`** (PATCH `dashboard/home-card-groups/{uuid}/`) ahora acepta los 8 campos Visual Builder (`subtitle`, `description`, `bg_color`, `bg_image`, `layout_type`, `padding`, `divider`, `columns`) ademas de `title`/`display_order`/`is_visible` — antes solo `upsert/` los aceptaba, generando una inconsistencia entre "crear/upsert" y "editar por uuid".
- **`core/signals.py`** gano `invalidate_home_feed_on_footer_cta_change` (`post_save`+`post_delete` sobre `FooterCTAConfig` → `cache.delete(HOME_FEED_CACHE_KEY)`), import de `FooterCTAConfig` agregado. `HomeCardGroup` se deja tal cual (su falta de signal es una decision de diseno documentada desde 2026-06-30, no un descuido).
- Verificado: `python manage.py check` sin errores nuevos; suite `core`+`dashboard` corrida tras el cambio.

### 2026-07-09 (a) — Auditoria de alineacion

**Discrepancias encontradas en el documento** (auditoria pura, sin cambios de codigo en este paso — los 2 gaps reales se corrigieron en la entrada siguiente, el mismo dia):

- **Modelo `FooterCTAConfig` faltaba por completo** en el documento (migr. 0014, existe desde 2026-06-30): singleton, endpoint `dashboard/footer-cta/`, viaja dentro de `home-feed.footer_cta`.
- **Endpoint `enums/{name}/` no documentado**: existe en `HomeFeedView` junto a los 3 endpoints publicos ya documentados, con 17 catalogos (incluye `shipment-statuses`, agregado en la sesion de [[project_shop_operations_module]] el mismo dia).
- **"Constructor Visual" (2026-06-30, migraciones 0012/0013/0015) no documentado**: `HomeModuleConfig.display_type/layout_config` (18 tipos de layout), `HomeCard.card_type/animation/is_featured/priority` (8 tipos de tarjeta), `HomeCardGroup.subtitle/description/bg_color/bg_image/layout_type/padding/divider/columns`, `HomeBanner.eyebrow/background_color/cta_ghost_label/cta_ghost_url`. Se agregaron a los 4 modelos existentes en el documento.
- **`home-feed` respuesta desactualizada**: le faltaban `card_groups` (lista completa, distinta de `card_group_titles`) y `footer_cta`.
- **`HomeFeedSelector.get_module_configs()` gano parametro `request` opcional** (no documentado) para absolutizar `background_image`.
- **2 gaps de arquitectura reales detectados** (corregidos el mismo dia, ver entrada "(b)" arriba):
  - `dashboard/home-card-groups/{uuid}/` (PATCH) no aceptaba los campos Visual Builder, solo `upsert/` los aceptaba.
  - `FooterCTAConfig` no tenia signal de invalidacion de cache propio.
- **Frontend**: documentados `ModuleBuilderModal.vue` (nuevo, ~1542 lineas) y la estructura real de 7 secciones de `HomeConfigView.vue` (creceio de un documento que no lo mencionaba en detalle).
- **Migraciones 0012-0016** documentadas (el doc anterior llegaba solo hasta 0011).
- **Contador de modelos corregido:** 8 → 9 (FooterCTAConfig).
- **Contador de serializers corregido:** 17 → 23.
- **Contador de selectores corregido:** documento anterior decia 10, el conteo real (incluyendo clases ya existentes que no se habian contado bien) es 15 — incluye `FooterCTASelector` + `FooterCTACommands`, nuevas desde 2026-06-30.

### 2026-06-30 — Auditoria completa y sincronizacion

**Discrepancias encontradas y corregidas:**

- **Modelo HomeCardGroup agregado:** `group_name` desacoplado del titulo publico; patron upsert sin FK; invalidacion manual en dashboard.
- **Endpoint home-feed actualizado:** respuesta incluye `card_group_titles: {name: title}`.
- **Signals IMPLEMENTADOS** (el doc anterior decia "sugerido, no implementado"): `core/signals.py` existe con 7 handlers registrados en `CoreConfig.ready()`.
- **Serializers faltantes documentados:** `HomeModuleCreateSerializer`, `HomeCardInputSerializer`, `HomeCardGroupSerializer`, `HomeCardGroupInputSerializer`, `FooterLinkInputSerializer`, `CompanyContactInfoInputSerializer`, `SiteBrandConfigInputSerializer`, `NavbarLinkInputSerializer` (17 total vs 11 en el doc anterior).
- **FooterSelector metodos reales documentados:** `get_active_contact()`, `list_active_links()`, `list_all_links()`, `get_link_by_uuid()`, `build_footer_payload()` — el doc anterior tenia metodos inventados (`list_active_social()`, `list_active_nav()`).
- **HomeModuleConfigSerializer campos reales:** `module_label`, `module_url`, `module_icon`, `module_color`, `is_core` (computed), campos `custom_*`.
- **Bug corregido en `CompanyContactInfo.save()`:** lineas 240-244 eran codigo muerto duplicado dentro del metodo `save()` (atributos Meta huerfanos + `__str__` duplicado). Eliminado.
- **Tabla de endpoints dashboard/core** agregada completa.
- **Seccion de consumo frontend** agregada (HomeView, TrustSection, HomeConfigView).
- **Migraciones** documentadas (0001-0011).
- **Contador de modelos corregido:** 7 → 8 (HomeCardGroup).
- **Contador de selectores corregido:** 8 → 10 clases (HomeCardGroupSelector + HomeCardGroupCommands).

### 2026-06-28 — Auditoria inicial
- 5 modelos faltantes documentados, 3 endpoints publicos, sistema de cache.

### 2026-06-27 — Version inicial
- Documento simplificado (solo HomeBanner y HomeModuleConfig).
