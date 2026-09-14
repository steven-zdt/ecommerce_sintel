# Card Group Section — Contrato API

Fecha: 2026-08-06. **Cero endpoints nuevos, cero rutas renombradas.** Los mismos
ViewSets/rutas de `HomeCard`/`HomeCardGroup` ya existentes ahora aceptan y devuelven los
campos nuevos.

## Público (solo lectura, sin auth)

### `GET /api/v1/core/home-feed/`

Sin cambios de shape del endpoint — `home_cards` y `card_groups` ahora incluyen los campos
nuevos:

```json
{
  "...": "resto del payload sin cambios",
  "card_groups": [
    {
      "uuid": "...", "name": "cursos", "title": "Cursos",
      "layout_type": "slider", "columns": 3, "padding": "normal",
      "columns_tablet": 2, "columns_mobile": 1, "gap": "1.25",
      "carousel_autoplay": true, "carousel_loop": true, "carousel_speed": 40,
      "show_arrows": true, "show_indicators": true
    }
  ],
  "home_cards": [
    {
      "uuid": "...", "title": "Curso Python", "group_name": "cursos",
      "card_type": "vertical", "redirect_url": "/cursos/python",
      "url_type": "INTERNA", "url_target": "_self",
      "badge_text": "Nuevo", "badge_color": "#22c55e",
      "stats": [{"label": "Duracion", "value": "8 semanas"}],
      "secondary_label": "Ver temario", "secondary_icon": "bi-list-check",
      "secondary_url": "/temario", "secondary_url_type": "INTERNA", "secondary_target": "_self"
    }
  ]
}
```

## Admin (JWT, `ADMIN_PERMISSIONS`)

### Tarjetas — `dashboard/home-cards/` (`AdminHomeCardViewSet`, sin cambios de rutas)

| Método | Ruta | Cambio |
|---|---|---|
| GET | `home-cards/` | Respuesta incluye los campos nuevos. |
| POST | `home-cards/create/` | `HomeCardInputSerializer` acepta `badge_color`, `url_type`, `url_target`, `stats`, `secondary_*`. |
| PATCH | `home-cards/<uuid>/` | idem, parcial. |
| DELETE | `home-cards/<uuid>/delete/` | Sin cambios. |

`HomeCardCommands.create_card()` se refactorizó de kwargs explícitos a `**data` + whitelist
(`_ALLOWED_FIELDS`, mismo patrón que `update_card` ya usaba) — mismo comportamiento, sin
duplicar la lista de campos dos veces.

### Grupos — `dashboard/home-card-groups/` (`AdminHomeCardGroupViewSet`, sin cambios de rutas)

| Método | Ruta | Cambio |
|---|---|---|
| GET | `home-card-groups/` | Respuesta incluye los campos nuevos. |
| POST | `home-card-groups/upsert/` | `HomeCardGroupInputSerializer` acepta `columns_tablet`, `columns_mobile`, `gap`, `carousel_autoplay`, `carousel_loop`, `carousel_speed`, `show_arrows`, `show_indicators`. También se corrigió una brecha ya documentada en `HOME_MODULE_URLS.md`: este serializer no llamaba `_strip_html_fields()` — ahora sí. |
| PATCH | `home-card-groups/<uuid>/` | idem. |
| DELETE | `home-card-groups/<uuid>/delete/` | Sin cambios. |

## Validaciones server-side

`HomeCard.clean()` (nuevo, corre en `save()` vía `full_clean()`):

| `url_type` / `secondary_url_type` | Regla | Ejemplo válido |
|---|---|---|
| `INTERNA` | debe empezar con `/` | `/tienda` |
| `EXTERNA` | debe empezar con `http://` o `https://` | `https://ejemplo.com` |
| `ANCHOR` | debe empezar con `#` | `#seccion-2` |

Una URL vacía no se valida (botón opcional). Regla centralizada en
`core/validators.py::validate_url_type_pair()`.
