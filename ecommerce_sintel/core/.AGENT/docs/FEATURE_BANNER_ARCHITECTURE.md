# Feature Banner — Arquitectura (grafo completo)

Fecha: 2026-08-06. Modulo nuevo del Home Builder: secciones promocionales genericas
(imagen + texto + beneficios + stats + botones), reutilizables para cualquier proposito
comercial. No especifico de "empleo" ni de ningun modulo de negocio en particular.

Mirror exacto del patron arquitectonico ya usado por Modulos/Banners/Tarjetas/CTA/
Slider de Marcas (ver `HOME_MODULE_GRAPH.md`), sin desviaciones de capa.

## Grafo admin -> render

```
Admin (panel/home-config, tab "Feature Banner")
  frontend/src/modules/core/home-builder/FeatureBannerSection.vue
    |
    v  (acciones CRUD)
  frontend/src/store/coreAdmin.js
    fetchFeatureBannerSections / createFeatureBannerSection / updateFeatureBannerSection /
    deleteFeatureBannerSection / createFeatureBannerBlock / updateFeatureBannerBlock /
    deleteFeatureBannerBlock / reorderFeatureBannerBlocks
    |
    v  (HTTP, JWT admin)
  dashboard/api/urls.py
    router.register('feature-banner-sections', AdminFeatureBannerSectionViewSet)
    router.register('feature-banner-blocks',   AdminFeatureBannerBlockViewSet)
    |
    v
  dashboard/api/views.py
    AdminFeatureBannerSectionViewSet  (list / create_section / update_section / delete_section)
    AdminFeatureBannerBlockViewSet    (list / create_block / update_block / delete_block / reorder)
    -- cada mutacion llama _invalidate_home_feed_cache()
    |
    v
  core/services/commands.py
    FeatureBannerSectionSelector / FeatureBannerSectionCommands
    FeatureBannerBlockSelector   / FeatureBannerBlockCommands
    |
    v
  core/models.py
    FeatureBannerSection(SintelBaseModel)  1--N  FeatureBannerBlock(SintelBaseModel)
    |
    v  (post_save / post_delete)
  core/signals.py
    cache.delete(HOME_FEED_CACHE_KEY)
```

```
Home publica (/)
  frontend/src/views/customer/HomeView.vue
    GET core/home-feed/
    |
    v
  core/api/views.py :: HomeFeedView.home_feed()
    feature_banner_sections = FeatureBannerSectionSelector.list_active_with_blocks()
    -- filtro real de visibilidad EN EL BACKEND (is_visible=True, bloques is_active=True)
    'feature_banner_sections': FeatureBannerSectionSerializer(..., many=True).data
    -- cache manual: HOME_FEED_CACHE_KEY, TTL 300s (sin cambios de mecanismo)
    |
    v
  frontend/src/renderers/HomeRenderer.vue
    <FeatureBannerRenderer :sections="featureBannerSections" v-if="showSection('feature_banner')">
    |
    v
  frontend/src/components/ui/showcase/FeatureBannerRenderer.vue   (orquestador de secciones)
    |
    v
  frontend/src/components/ui/showcase/FeatureBannerBlock.vue      (un bloque: imagen+texto+botones)
    |
    v
  frontend/src/components/ui/showcase/FeatureBannerButton.vue     (resuelve url_type -> href real)
```

El mismo `<HomeRenderer>` alimenta tambien la Vista Previa del builder admin
(`HomeConfigView.vue`, `SECTION_TO_RENDERER['feature_banner'] = 'feature_banner'`), con el
estado en memoria del formulario -- no hay markup ni logica de render exclusiva de ninguno
de los dos consumidores (mismo principio que el resto del Home Builder).

## Modelo de datos

```
FeatureBannerSection (SintelBaseModel: uuid, created_at, updated_at, is_deleted)
  title, subtitle, description
  is_visible, display_order
  theme: light | dark | corporate | minimal | glass
  background_type: color | gradient | image
  background_color, background_gradient_from, background_gradient_to, background_image
  overlay_enabled, overlay_opacity (0-100)
  padding (reusa HomeCardGroup.PADDING_CHOICES)

FeatureBannerBlock (SintelBaseModel)
  section -> FK real a FeatureBannerSection, related_name='blocks', on_delete=CASCADE
  layout_type: image_left | image_right | fifty_fifty | sixty_forty | forty_sixty |
               full_image | text_centered
  title, title_highlighted, description
  image, image_alt
  benefits: JSONField [{icon, text}]
  stats:    JSONField [{value, label}]
  badge_text, badge_color
  btn_primary_{text,icon,color,style,url,url_type,target}
  btn_secondary_{text,icon,color,style,url,url_type,target}
  display_order, is_active
```

`url_type` (`INTERNA|EXTERNA|ANCHOR`) es un campo explicito elegido por el admin -- reemplaza
el patron legado de inferencia por regex (`isExternal = /^https?:\/\//.test(url)`) que usa
`MarketplaceCard.vue` para `HomeModuleConfig` (documentado como pendiente de migrar en
`HOME_MODULE_URLS.md`). Para este modelo nuevo se implementa correctamente desde el inicio.

## Decisiones de diseno (vs. patron legado del Home Builder)

| Decision | Patron legado (HomeCard) | Feature Banner | Razon |
|---|---|---|---|
| Relacion seccion-item | `group_name` (string libre, sin FK) | `section` FK real | La auditoria de esta sesion penalizo el string-key por fragil; en un modelo nuevo no hay motivo para replicarlo. |
| Filtro de visibilidad | Delegado al frontend (`HomeFeedSelector.get_module_configs()` no filtra) | Filtrado en el backend (`FeatureBannerSectionSelector.list_active_with_blocks()`) | Evita que un cliente sin JS oculte contenido que el backend ya deberia haber excluido. |
| Resolucion de URL de boton | Regex sobre el valor (`MarketplaceCard.vue`) | Campo `url_type` explicito | Elimina ambiguedad (ej. una URL interna que empiece con `http` por error de config). |
| Saneamiento de texto | Si (`_strip_html_fields`) en Banner/Card, no en `HomeCardGroupInputSerializer` | Si, incluyendo `benefits[].text` | Consistencia XSS en todo input de texto libre expuesto en la home publica. |

## Alcance v1 (acordado explicitamente con el usuario)

- Una sola imagen por seccion/bloque, responsive por CSS -- no 3 uploads por breakpoint.
- Texto plano (`description`, `subtitle`) -- no editor WYSIWYG/rich text.
- Sin SEO/fechas de publicacion/idioma/tags/categoria/tracking/parallax/blur-brightness
  independientes -- ninguno de esos campos tiene precedente en otra seccion del Home
  Builder existente; quedan fuera de v1 y documentados como pendientes (no implementados).
- 7 layouts (no los 12+ del brief original) y 5 temas predefinidos (no colores sueltos por
  campo) -- combinaciones CSS ya cubren los casos reales pedidos (overlay = `full_image`,
  cards laterales queda fuera de v1).
