# HOME_MODULE_CERTIFICATION.md — Checklist de certificación vs. criterios de aceptación

**Fecha:** 2026-08-06. Cierre del sprint de auditoría + remediación acotada del módulo
"Home Config → Módulos". Documento de certificación honesta: qué se cumplió, qué quedó pendiente
por decisión explícita, y por qué.

**Documentos relacionados:** `HOME_MODULE_GRAPH.md` (Fase 1, grafo completo), `HOME_MODULE_SYNC_
REPORT.md` (Fase 2, auditoría campo a campo, estado final), `HOME_MODULE_URLS.md` (Fase 3,
auditoría de URLs), `HOME_MODULE_REFACTOR.md` (Fase 7, los 5 fixes aplicados con evidencia).

## Alcance realmente ejecutado (acordado explícitamente con el usuario, 2 rondas de preguntas)

1. Solo cerrar la brecha admin→render con los campos que ya existen en el formulario — sin
   agregar campos nuevos al modelo/API (nada de `url_type`, imágenes responsive por breakpoint,
   ni los 16 layouts alternativos de "Presentación").
2. Solo `HomeModuleConfig` (los módulos base + custom vía `ModuleBuilderModal.vue`) — no
   `HomeCard`/`HomeCardGroup` (auditoría indica que estos están mejor sincronizados: contrato REST
   1:1 con el modelo, sin JSON de layout suelto).
3. Para el layout dinámico, solo ajustar el carrusel horizontal existente (columnas/gap) — sin
   construir componentes de grid/masonry/hero/banner/etc. nuevos.

## Criterios de aceptación del brief original — estado real

- [x] **"Toda la configuración de 'Editar sección — Seguridad Electrónica' se refleje
  correctamente en `localhost`."** — Verificado end-to-end para los campos dentro del alcance
  acordado: título, subtítulo, descripción, icono, badge, CTA/url, texto/icono/estilo/posición de
  botón (bottom/top), estadísticas, overlay, orden, visibilidad, animación, columnas/gap del
  carrusel, cantidad de elementos destacados, imagen de fondo de sección completa. La imagen de
  fondo por tarjeta (subida de archivo real) se verificó con una prueba adicional pedida por el
  usuario y encontró un sexto bug real (`media.type` congelado en `'color'` bloqueaba la imagen
  subida) — corregido y reverificado (Fix 6, `HOME_MODULE_REFACTOR.md`). Ver
  `HOME_MODULE_SYNC_REPORT.md` para la tabla completa por campo.
- [ ] **"Todas las URLs provengan exclusivamente del administrador y estén validadas."** —
  Parcialmente cierto hoy (las URLs ya provienen 100% del admin, ninguna está hardcodeada en el
  componente Vue), pero **no hay validación de formato ni campo `url_type` explícito** — el
  interno/externo se infiere por regex sobre el valor. Este es un cambio de modelo + migración +
  serializer, explícitamente fuera del alcance acordado ("sin campos nuevos"). Documentado en
  detalle en `HOME_MODULE_URLS.md`, con la propuesta concreta lista para un sprint aparte si se
  decide abordarlo.
- [ ] **"Las tarjetas admitan imágenes de fondo responsivas y configurables."** — Hoy admiten UNA
  imagen de fondo por tarjeta (sin variantes desktop/tablet/mobile) y sin blur/brightness/opacity
  de la imagen en sí (solo del overlay). Fuera del alcance acordado (implica campos nuevos en el
  modelo). No se tocó.
- [~] **"El layout, el número de elementos destacados y la visibilidad sean 100% configurables
  desde `/panel/home-config/modulos`."** — El número de elementos destacados y la visibilidad ya
  eran 100% configurables (confirmado, sin cambios necesarios). El layout es parcialmente
  configurable: columnas/gap del carrusel ahora sí se respetan (Fix 4); el selector de 17
  "Presentaciones" (grid/masonry/hero/banner/...) sigue sin efecto porque implementarlas
  requeriría construir componentes de render que hoy no existen — decisión de producto explícita
  pendiente (¿implementar los layouts reales, o simplificar el selector admin para no ofrecer
  opciones sin efecto?). Documentado en `HOME_MODULE_SYNC_REPORT.md`.
- [x] **"No existan valores codificados en componentes Vue cuando deban provenir del backend"**
  (para el alcance de este sprint) — Los 5 valores hardcodeados identificados en la auditoría
  (ícono del botón, estilo ghost/minimal, posición, columnas/gap del carrusel, campo de imagen de
  sección) fueron corregidos. Colores secundarios (`color_secondary/text/bg`) siguen sin
  conectarse — deliberadamente, por riesgo de alterar visualmente tarjetas ya publicadas sin
  aviso (ver razón abajo).
- [x] **"Se eliminen configuraciones duplicadas y exista una única fuente de verdad"** — No se
  encontraron configuraciones verdaderamente duplicadas en el alcance auditado (el sistema
  "columnas" vs. "carrusel.items_desktop" no es una duplicación sino dos conceptos con
  solapamiento parcial de propósito — se resolvió con precedencia clara, no eliminando ninguno).
  La invalidación de cache duplicada (explícita + signals) es intencional/defensiva, documentada
  en `HOME_MODULE_GRAPH.md`, no se tocó por ser correcta tal como está.
- [x] **"Cada corrección quede documentada con archivo afectado, causa raíz, solución aplicada y
  evidencia"** — Ver `HOME_MODULE_REFACTOR.md`, un fix por sección con esa estructura exacta.

## Pendientes explícitos (decisión de producto, no de este sprint)

| Ítem | Por qué no se hizo ahora | Esfuerzo estimado |
|---|---|---|
| `url_type` + validación de formato de URL | Requiere campo nuevo en modelo + migración, fuera del alcance acordado | Medio — 1 migración + serializer + form + `MarketplaceCard.vue` |
| Imágenes de fondo responsive (desktop/tablet/mobile/blur/brightness) | Requiere campos nuevos en modelo, fuera del alcance acordado | Alto — varios campos nuevos + UI de subida múltiple |
| Layouts reales para `display_type` (grid/masonry/hero/banner/...) | Requiere decidir primero si se implementan de verdad o se recorta el selector; construir componentes nuevos está fuera de "solo cerrar brecha" | Alto si se implementan de verdad; bajo si solo se simplifica el selector admin |
| Colores custom (`color_secondary/text/bg`, tamaños de fuente) | Riesgo real de alterar visualmente tarjetas ya publicadas sin que el admin lo sepa | Bajo, pero requiere decidir si aplicar solo a tarjetas nuevas o a todas |
| Categoría, target explícito para `custom_url`, posición `inline`/`overlay` del botón | No mencionados en el alcance acordado con el usuario | Bajo cada uno |
| `is_visible` sin filtro a nivel de backend en `home-feed` | Funciona hoy correctamente (el frontend sí filtra); es una mejora de "defensa en profundidad", no un bug activo | Bajo — un `.filter(is_visible=True)` en `HomeFeedSelector.get_module_configs()` |

## Documentos NO generados (y por qué)

El brief original pedía 9 documentos. Se generaron 5 (`HOME_MODULE_GRAPH.md`, `HOME_MODULE_SYNC_
REPORT.md`, `HOME_MODULE_URLS.md`, `HOME_MODULE_REFACTOR.md`, este `HOME_MODULE_CERTIFICATION.md`).
No se generaron `HOME_MODULE_CACHE.md`, `HOME_MODULE_LAYOUT.md`, `HOME_MODULE_IMAGES.md` como
documentos independientes porque sus fases correspondientes (9, 5, 4) no tuvieron cambios de
código en este sprint — su contenido real (hallazgos, estado, pendientes) ya está cubierto dentro
de `HOME_MODULE_GRAPH.md` (cache) y las tablas de pendientes de este documento (layout, imágenes).
Generarlos como archivos separados sin contenido nuevo habría sido documentación redundante — si
se decide abordar esas fases en un sprint futuro, se crean en ese momento con contenido real.
