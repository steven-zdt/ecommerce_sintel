# HOME_MODULE_GRAPH.md — Grafo completo: `/panel/home-config` → sección "Módulos" (home pública)

**Fecha:** 2026-08-06
**Alcance:** reconstrucción del grafo real (backend + frontend) del módulo administrable desde
`/panel/home-config`, pestaña "Módulos" (tarjetas tipo "Seguridad Electrónica" + los 4 módulos
base Tienda/Alquiler/Servicios/Cotizaciones). Fase 1 del brief `AUDITORÍA Y RECONSTRUCCIÓN DEL
MÓDULO "HOME CONFIG → MÓDULOS"` — solo lectura, cero cambios de código.

**Metodología:** 2 agentes de exploración en paralelo (backend/frontend), leyendo código fuente
real, verificado archivo:línea. Sin asumir comportamiento — todo lo aquí escrito fue confirmado
en el repositorio.

## Corrección de nomenclatura (hallazgo previo, importante)

No existe un modelo `HomeConfig`. `AdminHomeConfigViewSet` es un nombre "paraguas" que administra
**dos modelos distintos**: `HomeBanner` (banners de cabecera) y `HomeModuleConfig` (los 4 módulos
base + módulos custom). Las tarjetas tipo "Seguridad Electrónica" son instancias de `HomeCard`,
agrupadas por `HomeCardGroup`. La pestaña "Módulos" del panel edita `HomeModuleConfig` (a través
de `ModuleBuilderModal.vue`), no un modelo unificado.

## Flujo real (verificado)

```
Admin (ModuleBuilderModal.vue, 13 tabs)
  -> useCoreAdminStore (createModule/updateModule/deleteModule)
  -> POST/PATCH/DELETE dashboard/home-config/modules/...  (AdminHomeConfigViewSet)
  -> HomeConfigCommands.update_module_config() / create_module()
  -> HomeModuleConfig (BD)
  -> _invalidate_home_feed_cache() + signal post_save/post_delete (ambos, redundante)
  -> cache.delete('sintel_home_feed_v1')

Home pública (HomeView.vue)
  -> GET core/home-feed/  (HomeFeedView, cache 5 min)
  -> HomeFeedSelector.get_module_configs()  [construye dict a mano, NO usa HomeModuleConfigSerializer]
  -> HomeRenderer.vue (prop modules)
  -> MarketplaceShowcase.vue (sección "Módulos")
  -> MarketplaceCarousel.vue (layout fijo: carrusel horizontal, SIEMPRE)
  -> MarketplaceCard.vue (tarjeta individual)
```

## Backend

### Modelos (`core/models.py`)

| Modelo | Rol | Campos propios |
|---|---|---|
| `HomeBanner` (7-42) | Banner de cabecera | title, subtitle, eyebrow, image, video, background_color, link_url, link_label, cta_ghost_label, cta_ghost_url, is_active, display_order |
| `HomeModuleConfig` (45-153) | Los 4 módulos base + custom | module_key (unique), is_visible, display_order, featured_items_limit, custom_label/icon/url/color, background_image, display_type (17 choices), layout_config (JSON) |
| `HomeCard` (156-203) | Tarjeta tipo "Seguridad Electrónica" | title, subtitle, description, group_name (string libre, no FK real), icon_class, background_color, image, video, redirect_url, display_order, is_active, card_type (9 choices), animation, is_featured, priority, badge_text |
| `HomeCardGroup` (206-274) | Encabezado de grupo de tarjetas | name (unique), title, display_order, is_visible, subtitle, description, bg_color, bg_image, layout_type (8 choices), padding, divider, columns, glass, hover |

Todos heredan `SintelBaseModel` (uuid, created_at, updated_at, is_deleted — soft delete).
`HomeBanner`/`HomeModuleConfig` fuerzan `full_clean()` en `save()`; `HomeCard`/`HomeCardGroup` no.

`HomeModuleConfig.MODULE_META` (línea 59-64) es un **fallback hardcodeado en el modelo** (no en
BD) con label/url/icon/color por defecto de los 4 módulos base.

### Serializers (`core/api/serializers.py`)

Un mismo `ModelSerializer` se reutiliza para admin y público en `HomeBanner`/`HomeCard`/
`HomeCardGroup`. `HomeModuleConfig` es la excepción: `HomeModuleConfigSerializer` (admin) calcula
`module_label/url/icon/color/is_core` vía `SerializerMethodField`, pero **el endpoint público NO
usa este serializer** — construye el JSON a mano (ver `HomeFeedSelector.get_module_configs()`).

### Servicios (`core/services/selectors.py` + `core/services/commands.py`)

- `HomeConfigSelector` / `HomeConfigCommands` — banners y módulos.
- `HomeCardSelector` / `HomeCardCommands` — tarjetas (viven en `commands.py`, no en `selectors.py`,
  desde el refactor Sprint 1 2026-07-16).
- `HomeCardGroupSelector` / `HomeCardGroupCommands` — grupos.
- `HomeFeedSelector` — agrega banners+modules+cards+groups+destacados de otras apps para el
  endpoint público `home-feed`. `get_module_configs()` no filtra por `is_visible` (expone todo,
  visible u oculto, y delega el filtro al frontend).

### Endpoints

Admin (`api/v1/dashboard/`, `IsAuthenticated + IsAdminUser`):
`home-config/banners/`, `home-config/modules/`, `home-cards/`, `home-card-groups/` — CRUD completo,
ver `dashboard/api/views.py:1693-1950`.

Público (`api/v1/core/`, sin auth):
`GET core/home-feed/` — único endpoint, devuelve `banners`, `modules`, `home_cards`,
`card_group_titles`, `card_groups`, más destacados de shop/renting/services y `footer_cta`/
`brand_slider`. Cache 5 min (`sintel_home_feed_v1`).

### Cache

`cache.get/set` manual en `HomeFeedView.home_feed()` (`core/api/views.py:62-102`), TTL 300s.
Invalidación **duplicada por diseño** (no es un bug, es defensivo): explícita en cada acción admin
(`_invalidate_home_feed_cache()`) + signals `post_save`/`post_delete` en `core/signals.py` sobre
los 4 modelos. Ambas hacen únicamente `cache.delete()` — sin cache warming.

## Frontend

### Admin

`/panel/home-config` (ruta única, sin sub-rutas) → `HomeConfigView.vue`, navegación interna por
`ref` local `currentSection` (no en la URL) → pestaña "modules" monta `ModulesSection.vue` → botón
"Nuevo módulo"/tarjeta existente abre `ModuleBuilderModal.vue` (13 tabs internas, ~55 campos
editables reales, listados completos en el hallazgo del agente de frontend).

Estado: `store/coreAdmin.js` (`fetchModules/createModule/updateModule/deleteModule`), llamadas
HTTP directas vía `useApi()` (no hay capa `services/*.js` separada — convención documentada del
proyecto: los stores admin SON la capa de servicio).

### Público

`HomeView.vue` → `GET core/home-feed/` → `HomeRenderer.vue` (prop `modules`) →
`MarketplaceShowcase.vue` (sección) → `MarketplaceCarousel.vue` (SIEMPRE carrusel horizontal,
sin importar `display_type`) → `MarketplaceCard.vue` (tarjeta).

## Diagrama de dependencia de archivos clave

```
BACKEND
  core/models.py (HomeModuleConfig, HomeCard, HomeCardGroup, HomeBanner)
    -> core/api/serializers.py
    -> core/services/selectors.py + core/services/commands.py
    -> dashboard/api/views.py (Admin*ViewSet, escritura)
    -> core/api/views.py (HomeFeedView, lectura publica)
    -> core/signals.py (invalidacion cache)

FRONTEND ADMIN
  frontend/src/modules/core/HomeConfigView.vue
    -> frontend/src/modules/core/home-builder/ModulesSection.vue
    -> frontend/src/modules/core/ModuleBuilderModal.vue
       -> frontend/src/modules/core/module-builder/{General,Presentation,Style,Icon,Media,
          Layout,Responsive,Animation,Content,Buttons,Background,Carousel,Multimedia}Tab.vue
    -> frontend/src/store/coreAdmin.js

FRONTEND PUBLICO
  frontend/src/views/customer/HomeView.vue
    -> frontend/src/renderers/HomeRenderer.vue
    -> frontend/src/components/ui/showcase/MarketplaceShowcase.vue
    -> frontend/src/components/ui/showcase/MarketplaceCarousel.vue
    -> frontend/src/components/ui/showcase/MarketplaceCard.vue
    -> frontend/src/components/ui/showcase/MarketplaceBackground.vue
    -> frontend/src/components/ui/showcase/MarketplaceHeader.vue
```
