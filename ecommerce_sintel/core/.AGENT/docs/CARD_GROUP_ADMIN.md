# Card Group Section — Formulario admin

Fecha: 2026-08-06. `frontend/src/modules/core/home-builder/CardsSection.vue`, pestaña
"Tarjetas" de `/panel/home-config` (sin cambio de nombre ni de posición en el sidebar — es
la misma pestaña que ya existía, ahora con más capacidad).

## Modal "Configurar grupo"

Campos preexistentes sin cambios: Subtítulo, Descripción, Layout, Columnas, Padding, Hover,
Color de fondo, Divisor, Glass, Imagen de fondo.

Campos nuevos:

| Sección | Campo UI | Campo modelo |
|---|---|---|
| Responsive | Columnas tablet | `columns_tablet` |
| Responsive | Columnas mobile | `columns_mobile` |
| Responsive | Espaciado (gap, rem) | `gap` |
| Carrusel *(solo si Layout = Slider)* | Auto scroll | `carousel_autoplay` |
| Carrusel | Loop | `carousel_loop` |
| Carrusel | Flechas | `show_arrows` |
| Carrusel | Indicadores | `show_indicators` |
| Carrusel *(solo si Auto scroll activo)* | Velocidad (px/s) | `carousel_speed` |

La sección "Carrusel" solo se muestra cuando `layout_type === 'slider'` — mismo patrón de
UI condicional ya usado en `FeatureBannerSection.vue` para el tipo de fondo.

## Modal "Tarjeta"

Campos preexistentes sin cambios: Título, Subtítulo, Descripción, Grupo, Tipo visual (9
variantes), Ícono, Color, URL destino, Orden, Prioridad, Animación, Texto del badge, Activa,
Destacada, Imagen adjunta.

Campos nuevos:

| Campo UI | Campo modelo | Condición |
|---|---|---|
| Tipo de URL (Interna/Externa/Ancla) | `url_type` | junto a "URL destino" |
| Abrir en (misma/nueva pestaña) | `url_target` | solo si Tipo de URL = Externa |
| Color del badge | `badge_color` | siempre |
| Estadísticas (lista dinámica valor+etiqueta) | `stats` | agregar/quitar filas, mismo patrón que `benefits`/`stats` de `FeatureBannerSection.vue` |
| Botón secundario: texto/ícono/URL/tipo de URL/target | `secondary_*` (7 campos) | bloque opcional, mismo shape que el botón primario |

`saveCard()` serializa `stats` a JSON (`JSON.stringify`) antes de enviarlo por
`multipart/form-data` cuando hay una imagen adjunta (consistente con el patrón ya usado en
`FeatureBannerSection.vue::saveBlock()` para `benefits`/`stats`).

## Vista previa en vivo

El modal "Tarjeta" ya tenía una columna de vista previa real (`<CardItem :card=
"cardPreviewData" />`) — al agregar los campos nuevos al formulario, la vista previa los
refleja automáticamente sin cambios adicionales, porque `cardPreviewData` es un `computed`
que ya spreadea `cardForm.value` completo.

## Vista previa compartida (Desktop/Tablet/Mobile)

Ya existe genéricamente en `HomeConfigView.vue` (botones Desktop/Tablet/Mobile sobre el
mismo `<HomeRenderer>` compartido con la home pública) — aplica automáticamente a la pestaña
"Tarjetas" igual que a las demás secciones del Home Builder, sin código nuevo.
