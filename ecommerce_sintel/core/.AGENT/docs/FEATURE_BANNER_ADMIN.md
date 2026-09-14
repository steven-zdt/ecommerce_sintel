# Feature Banner — Formulario admin

Fecha: 2026-08-06. `frontend/src/modules/core/home-builder/FeatureBannerSection.vue`,
montado como pestaña "Feature Banner" en `/panel/home-config` (icono `bi-window-stack`,
contador = numero de secciones).

Cada campo listado abajo llega al modelo, a la API y se renderiza en la home publica -- sin
excepciones (ver checklist completo en `FEATURE_BANNER_TRACEABILITY.md`). Esta garantia es
deliberada: la auditoria `HOME_MODULE_CERTIFICATION.md` (cerrada en esta misma sesion)
documento el costo real de un formulario con campos que no producen efecto visible.

## Vista de lista

Una fila por seccion: titulo, badge de visibilidad (Visible/Oculta), tema, boton "Agregar
bloque", boton "Configurar" (abre modal Seccion), boton "Eliminar". Debajo, grid de
mini-tarjetas por cada bloque de esa seccion (editar/eliminar por bloque).

## Modal "Seccion"

| Campo UI | Campo modelo | Tipo |
|---|---|---|
| Titulo de la seccion | `title` | texto, opcional |
| Subtitulo | `subtitle` | texto, opcional |
| Texto de apoyo | `description` | textarea, opcional |
| Tema (Light/Dark/Corporate/Minimal/Glass) | `theme` | select |
| Orden | `display_order` | numero |
| Tipo de fondo (Color solido/Gradiente/Imagen) | `background_type` | select -- condiciona los campos siguientes |
| Color de fondo | `background_color` | color picker, si `background_type=color` |
| Gradiente desde / hasta | `background_gradient_from/to` | 2 color pickers, si `background_type=gradient` |
| Imagen de fondo | `background_image` | upload real (multipart), si `background_type=image` -- con preview y boton quitar |
| Padding (Sin padding/Pequeno/Normal/Grande/Extra grande) | `padding` | select |
| Activar overlay | `overlay_enabled` | checkbox -- revela el campo de opacidad |
| Opacidad del overlay | `overlay_opacity` | numero 0-100 |
| Visible | `is_visible` | checkbox |

## Modal "Bloque"

| Campo UI | Campo modelo | Tipo |
|---|---|---|
| Layout (7 opciones) | `layout_type` | select -- condiciona si se muestra el campo de imagen |
| Activo | `is_active` | checkbox |
| Titulo | `title` | texto |
| Titulo resaltado | `title_highlighted` | texto (se concatena visualmente con color de acento) |
| Descripcion | `description` | textarea |
| Orden | `display_order` | numero |
| Imagen | `image` + `image_alt` | upload real (multipart), condicional segun layout (oculto en `text_centered`) |
| Beneficios | `benefits` | lista dinamica de `{icono, texto}` -- agregar/quitar filas |
| Estadisticas | `stats` | lista dinamica de `{valor, etiqueta}` -- agregar/quitar filas |
| Badge (texto + color) | `badge_text`, `badge_color` | texto + color picker |
| Boton primario: texto/icono/color/estilo/URL/tipo de URL/target | `btn_primary_*` | bloque de 7 campos; `url_type` (Interna/Externa/Ancla) condiciona si se muestra `target` (solo relevante para Externa) |
| Boton secundario: idem | `btn_secondary_*` | mismo bloque de 7 campos, opcional |

`saveBlock()` serializa `benefits`/`stats` a JSON antes de enviar (`JSON.stringify(...)`),
consistente con el shape `JSONField` de Django.

## Patron de subida de imagen

Mismo patron file/preview/remove que `CardsSection.vue`/`ModuleBuilderModal.vue`: al elegir
un archivo se genera un preview local (`URL.createObjectURL`), se envia como multipart en el
submit, y un boton "Quitar imagen" setea `remove_background_image`/`remove_image` para que el
backend borre el campo existente sin requerir un archivo nuevo.

## Vista previa compartida

El mismo `<HomeRenderer>` usado en la home publica real se reutiliza para el preview del
builder (`SECTION_TO_RENDERER['feature_banner'] = 'feature_banner'`), alimentado con el
estado en memoria del formulario -- lo que el admin ve en el preview es exactamente lo que
vera un visitante real tras guardar, sin una segunda implementacion de render paralela.
