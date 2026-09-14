# Card Group Section — Arquitectura

Fecha: 2026-08-06. "Card Group Section" es un componente reutilizable del Home Builder
capaz de mostrar cualquier tipo de colección (cursos, productos, servicios, noticias,
eventos, marcas, casos de éxito, personal, o cualquier colección futura), administrable
100% desde `/panel/home-config` y renderizado en `/` vía el mismo Home Feed.

## Decisión de diseño: extender, no duplicar

El Home Builder **ya tenía** un sistema de grupos de tarjetas genérico —
`HomeCardGroup` (contenedor) + `HomeCard` (item) — usado por la pestaña "Tarjetas". En vez
de crear un modelo `CardGroupSection`/`CardGroupItem` paralelo (como pedía el brief
original), se **extendieron los modelos existentes** con los campos que le faltaban. Esto
respeta directamente el principio "reutilizar completamente, no crear lógica paralela": el
Home Feed, el cache, los signals, la capa de servicios, los serializers y los endpoints
admin siguen siendo exactamente los mismos que ya existían — solo con más campos.

## Grafo admin → render

```
Admin (panel/home-config, tab "Tarjetas")
  frontend/src/modules/core/home-builder/CardsSection.vue
    |
    v (acciones CRUD -- SIN cambios de firma, ya existian)
  frontend/src/store/coreAdmin.js
    createCard / updateCard / upsertCardGroup / deleteCard / deleteCardGroup
    |
    v
  dashboard/api/views.py
    AdminHomeCardViewSet       (list / create_card / update_card / delete_card)
    AdminHomeCardGroupViewSet  (list / upsert / update_group / delete_group)
    -- mismas rutas, mismo shape de respuesta + campos nuevos
    |
    v
  core/services/commands.py
    HomeCardSelector / HomeCardCommands
    HomeCardGroupSelector / HomeCardGroupCommands
    |
    v
  core/models.py
    HomeCardGroup(SintelBaseModel)  1--N  HomeCard(SintelBaseModel)
    |
    v (post_save / post_delete, sin cambios -- ya invalidaban HOME_FEED_CACHE_KEY)
  core/signals.py
```

```
Home publica (/)
  frontend/src/views/customer/HomeView.vue
    GET core/home-feed/
    |
    v
  core/api/views.py :: HomeFeedView.home_feed()
    home_cards:  HomeCardSerializer(...)       -- sin cambios de shape de endpoint
    card_groups: HomeCardGroupSerializer(...)  -- sin cambios de shape de endpoint
    |
    v
  frontend/src/renderers/HomeRenderer.vue  (showSection('cards'))
    |
    v
  frontend/src/renderers/SectionRenderer.vue  (una instancia por HomeCardGroup)
    |
    v  useLayoutEngine.js::resolveGroupLayout()  -- layout_type -> nombre de componente
    |
    +-- CardsGrid.vue    (grid, con columnas responsive nuevas)
    +-- CardsSlider.vue  (slider, reescrito para envolver MarketplaceCarousel.vue)
    +-- (TimelineSection/AccordionSection/TabsSection/LogoStrip/MarqueeStrip -- sin cambios)
        |
        v
      CardItem.vue  (una tarjeta -- 9 variantes visuales, ahora con stats/boton
                      secundario/badge de color/url_type)
```

## Reutilización explícita (no se crea nada paralelo)

| Necesidad del brief | Se resuelve reutilizando |
|---|---|
| "Grupo de tarjetas" configurable | `HomeCardGroup` (ya existía) |
| "Tarjeta" con imagen/texto/botón | `HomeCard` (ya existía) |
| Carrusel con autoplay/loop/flechas/indicadores | `MarketplaceCarousel.vue` + `MarketplaceIndicators.vue` (ya construidos y probados para Modulos) |
| URL con tipo explícito (interna/externa/ancla) | El patrón `url_type` de `FeatureBannerBlock` (2026-08-06) — extraído a `core/validators.py::validate_url_type_pair()` para que ningún tercer modelo lo reimplemente |
| Chips genéricos de datos (duración, precio, stock...) | El shape `[{label, value}]` de `FeatureBannerBlock.stats` — reusado literal, no un formato nuevo |
| Resolución de navegación INTERNA/EXTERNA/ANCHOR en el frontend | `frontend/src/utils/urlNavigation.js::resolveUrlNavigation()` — extraído del código ya existente en `FeatureBannerButton.vue`, ahora usado también por `CardItem.vue` |
| Vista previa Desktop/Tablet/Mobile sin guardar | Ya existe genéricamente en `HomeConfigView.vue` (botones Desktop/Tablet/Mobile sobre el `<HomeRenderer>` compartido) — cero código nuevo |
| Cache/invalidación | `HOME_FEED_CACHE_KEY`, signals de `core/signals.py` — sin cambios de mecanismo |

## Campos del brief excluidos deliberadamente

Ver `CARD_GROUP_TRACEABILITY.md` para el detalle completo con justificación de cada uno:
rating decorativo, precio/precio-anterior dedicados, SEO/fechas de publicación/idioma/tags/
tracking por tarjeta, motor de auto-auditoría de accesibilidad/SEO/404, 3 imágenes por
breakpoint, editor rich-text.
