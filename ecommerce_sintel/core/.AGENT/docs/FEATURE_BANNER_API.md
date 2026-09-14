# Feature Banner — Contrato API

Fecha: 2026-08-06.

## Publico (solo lectura, sin auth)

### `GET /api/v1/core/home-feed/`

Agrega `feature_banner_sections` al payload existente (mismo endpoint que ya alimenta
Hero/Modulos/Flash/Featured/Tarjetas/CTA/Slider de marcas). Cache: `HOME_FEED_CACHE_KEY`
(`sintel_home_feed_v1`), TTL 300s -- ver `FEATURE_BANNER_CACHE.md`.

Filtrado real en backend: solo secciones con `is_visible=True`, con solo los bloques
`is_active=True` (`FeatureBannerSectionSelector.list_active_with_blocks()`).

```json
{
  "...": "resto del payload de home-feed sin cambios",
  "feature_banner_sections": [
    {
      "uuid": "653cfb96-...",
      "title": "Nuevas tecnologias",
      "subtitle": "...",
      "description": "...",
      "is_visible": true,
      "display_order": 0,
      "theme": "light",
      "background_type": "color",
      "background_color": "",
      "background_gradient_from": "",
      "background_gradient_to": "",
      "background_image": null,
      "overlay_enabled": false,
      "overlay_opacity": 45,
      "padding": "normal",
      "blocks": [
        {
          "uuid": "f141e65a-...",
          "layout_type": "fifty_fifty",
          "title": "Verificacion",
          "title_highlighted": "Feature Banner",
          "description": "...",
          "image": null,
          "image_alt": "",
          "benefits": [{"icon": "bi-check-circle", "text": "Beneficio A"}],
          "stats": [{"value": "99%", "label": "Uptime"}],
          "badge_text": "NUEVO",
          "badge_color": "#22c55e",
          "btn_primary_text": "Ir a la tienda",
          "btn_primary_icon": "bi-cart",
          "btn_primary_color": "#2563eb",
          "btn_primary_style": "filled",
          "btn_primary_url": "/tienda",
          "btn_primary_url_type": "INTERNA",
          "btn_primary_target": "_self",
          "btn_secondary_text": "Sitio externo",
          "btn_secondary_url": "https://www.sintel.net.co",
          "btn_secondary_url_type": "EXTERNA",
          "btn_secondary_target": "_blank",
          "display_order": 1,
          "is_active": true
        }
      ]
    }
  ]
}
```

## Admin (JWT, `ADMIN_PERMISSIONS`)

Base: `/api/v1/dashboard/`. Multipart para el campo imagen (`MultiPartParser, FormParser,
JSONParser`).

### Secciones -- `feature-banner-sections/`

| Metodo | Ruta | Body / Query | Respuesta |
|---|---|---|---|
| GET | `feature-banner-sections/` | -- | Todas las secciones (visibles u ocultas), con `blocks` (solo activos) precargados. |
| POST | `feature-banner-sections/create/` | `FeatureBannerSectionInputSerializer` | 201 + seccion creada. |
| PATCH | `feature-banner-sections/<uuid>/` | idem, `partial=True` | 200 + seccion actualizada. |
| DELETE | `feature-banner-sections/<uuid>/delete/` | -- | 204 (soft-delete, `is_deleted=True`). |

Campos de `FeatureBannerSectionInputSerializer`: `title, subtitle, description, is_visible,
display_order, theme, background_type, background_color, background_gradient_from,
background_gradient_to, background_image, remove_background_image, overlay_enabled,
overlay_opacity, padding`.

### Bloques -- `feature-banner-blocks/`

| Metodo | Ruta | Body / Query | Respuesta |
|---|---|---|---|
| GET | `feature-banner-blocks/?section=<uuid>` | `section` requerido | Bloques de esa seccion, ordenados. |
| POST | `feature-banner-blocks/create/` | `section` (uuid) + `FeatureBannerBlockInputSerializer` | 201 + bloque creado. |
| PATCH | `feature-banner-blocks/<uuid>/` | idem, `partial=True` | 200 + bloque actualizado. |
| DELETE | `feature-banner-blocks/<uuid>/delete/` | -- | 204 (soft-delete). |
| POST | `feature-banner-blocks/reorder/` | `{section, ordered_uuids: [...]}` | 200. Actualiza `display_order` por posicion en el arreglo. |

Campos de `FeatureBannerBlockInputSerializer`: `layout_type, title, title_highlighted,
description, image, remove_image, image_alt, benefits, stats, badge_text, badge_color,
btn_primary_text, btn_primary_icon, btn_primary_color, btn_primary_style, btn_primary_url,
btn_primary_url_type, btn_primary_target, btn_secondary_* (idem), display_order, is_active`.

Validaciones server-side (`FeatureBannerBlock.clean()`, corren en `save()` via
`full_clean()`):

| `url_type` | Regla | Ejemplo valido |
|---|---|---|
| `INTERNA` | debe empezar con `/` | `/tienda` |
| `EXTERNA` | debe empezar con `http://` o `https://` | `https://www.sintel.net.co` |
| `ANCHOR` | debe empezar con `#` | `#seccion-2` |

Una URL vacia no se valida (boton opcional). `overlay_opacity` de la seccion debe estar
entre 0 y 100 (`FeatureBannerSection.clean()`).

Toda mutacion (create/update/delete, ambos ViewSets) llama `_invalidate_home_feed_cache()`
explicitamente ademas de los signals -- mismo patron que el resto del Home Builder (ver
`FEATURE_BANNER_CACHE.md`).
