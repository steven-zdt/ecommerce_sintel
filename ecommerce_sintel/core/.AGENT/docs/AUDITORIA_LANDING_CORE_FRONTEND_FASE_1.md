# Auditoria de sincronizacion Core -> Landing (Fase 1)

**Fecha:** 2026-07-30  
**Alcance:** solo lectura. No se modificaron contratos, modelos, endpoints ni componentes Vue.

## Resultado ejecutivo

La arquitectura base es sana: `GET /api/v1/core/home-feed/` alimenta a
`HomeView.vue`, que delega el render al unico `HomeRenderer.vue`; este mismo
renderer se usa para la vista previa del Home Builder. La configuracion de
marca y navbar se obtiene mediante `appConfig`, y el footer y Nosotros tienen
sus endpoints propios. Hay sincronizacion funcional para la mayor parte del
contenido, pero aun no es 100% configuracion-gobernada: principalmente
`HomeModuleConfig.display_type`, algunos campos de `HomeCard` y la visibilidad
de Nosotros no producen siempre un efecto publico.

| Elemento Core | Endpoint publico | Componente Vue | Store | Composable | Estado actual | Sincronizado | Problemas / recomendacion |
|---|---|---|---|---|---|---|---|
| `HomeBanner` | `core/home-feed/` -> `banners` | `HomeView` -> `HomeRenderer` -> `HeroSection`, `HeroSlide`, `HeroBackground`, `HeroCTA` | No aplica | No aplica | Imagen, video, color, eyebrow, textos y ambos CTA se reciben de API. | **SI** | Los textos de fallback son intencionales para ausencia de datos, pero no son administrables. Mantenerlos como estado vacio, no como contenido normal. |
| `HomeModuleConfig` | `core/home-feed/` -> `modules` | `MarketplaceShowcase` -> `MarketplaceCarousel` -> `MarketplaceCard` | No aplica | `useLayoutEngine`, `useScrollReveal` | Etiqueta, icono, URL, color, visibilidad, imagen y varias claves de `layout_config` se renderizan. | **PARCIAL** | Todo modulo se presenta como tarjeta de carrusel: `display_type` no decide el layout y los 18 tipos del contrato no tienen soporte efectivo. Definir un renderer por `display_type` y un esquema publico versionado para `layout_config`. |
| `HomeCard` | `core/home-feed/` -> `home_cards` | `SectionRenderer` -> layouts y `CardItem` | No aplica | `useLayoutEngine`, `useScrollReveal` | Renderiza titulo, subtitulo, descripcion, icono, imagen, color, URL, tipo, prioridad, destacado, badge y animacion. | **PARCIAL** | El campo `video` se serializa pero no se usa en los layouts de tarjetas. `logo` no es una variante propia de `CardItem` (solo se aprovecha en `LogoStrip`). Incorporar ambos o retirarlos del constructor visual si no forman parte del contrato publico. |
| `HomeCardGroup` | `core/home-feed/` -> `card_groups` | `SectionRenderer` + `CardsGrid`/`CardsSlider`/secciones | No aplica | `useLayoutEngine` | Respeta titulo, subtitulo, descripcion, fondo, imagen, layout, padding, divisor, columnas, glass y hover. | **SI** | Los ocho `layout_type` se mapean; conviene conservar este renderer como referencia para los modulos. |
| `FooterCTAConfig` | `core/home-feed/` -> `footer_cta` | `FooterCTA` | No aplica | `useScrollReveal` | Renderiza jerarquia de texto y los dos CTA; distingue enlaces internos/externos. | **SI** | No existe campo de imagen en el modelo/endpoint, por lo que una imagen opcional requeriria una ampliacion futura de Core (fuera de este alcance). |
| `BrandSliderConfig` y `BrandSliderItem` | `core/home-feed/` -> `brand_slider` | `BrandSlider` | No aplica | `PADDING_MAP` de `useLayoutEngine` | Consume titulo, subtitulo, autoplay, velocidad, direccion, loop, pausa, breakpoints, color, padding, visibilidad, logo, enlace y nueva pestaña. | **SI** | El modo sin `loop` deja el track con estilos de animacion; la animacion queda pausada si autoplay es falso. Verificar visualmente el modo estatico durante la fase de UX. |
| `NavbarLink` y marca/SEO de organizacion | `core/site-config/` | `CustomerNavbar` | `appConfig` | `useAuth` (sesion), no para contenido | Marca y enlaces dinamicos se cargan una vez desde API; soporta icono, externo y nueva pestaña. | **SI** | El navbar no tiene estructura de mega-menu porque el contrato solo expone enlaces planos. No simular jerarquias que Core no emite. Los enlaces estaticos son solo fallback ante API vacia/fallida. |
| `FooterGroup`, `FooterLink`, contacto y sociales de organizacion | `core/footer/` | `CustomerFooter` | No aplica | `useApi` | Grupos, descripcion, iconos, colores, enlaces, contacto y redes se representan dinamicamente. | **PARCIAL** | La identidad y los textos legales inferiores siguen hardcodeados (`Sintel`, descripcion, copyright y "Hecho con..."). Vincularlos al contrato de organizacion o dejar el alcance explicitamente institucional/fijo. |
| `AboutUsConfig` y `AboutUsValue` | `core/about-us/` | `AboutUsView` | No aplica | `useApi` | Renderiza hero, titulo, subtitulo, historia, mision, vision, imagen y valores. | **PARCIAL** | `is_visible` se entrega por API pero no se consulta: la pagina se muestra aunque Core la despublique. Aplicar un estado publico de no-disponible o redireccion controlada. |
| `FlashOffers` | `core/home-feed/` -> `flash_offers` | `FlashOffers` -> `FlashOfferCard` | No aplica | `useScrollReveal` | El feed de ofertas se recibe y se muestra con skeleton y reveal. | **SI** | El encabezado, textos y destino "Ver todas" son fijos; no pertenecen hoy a un modelo Core. Mantenerlos como chrome de presentacion o exponer configuracion si deben ser administrables. |
| Productos destacados | `core/home-feed/` -> `featured_products` | `FeaturedSection` -> `FeaturedCarousel` | No aplica | No aplica | Datos del catalogo se muestran mediante la misma familia de componentes. | **PARCIAL** | Eyebrow, titulo, URL, etiqueta y color de la seccion estan hardcodeados en `HomeRenderer`. Extraer una definicion declarativa comun o recibirla desde Core si debe ser editable. |
| Equipos destacados | `core/home-feed/` -> `featured_equipment` | `FeaturedSection` -> `FeaturedCarousel` | No aplica | No aplica | Datos del catalogo se muestran en el componente compartido. | **PARCIAL** | Mismo gap: copy, enlace y color de seccion fijos en renderer. |
| Servicios destacados | `core/home-feed/` -> `featured_services` | `FeaturedSection` -> `FeaturedCarousel` | No aplica | No aplica | Datos del catalogo se muestran en el componente compartido. | **PARCIAL** | Mismo gap: copy, enlace y color de seccion fijos en renderer. |

## Hallazgos priorizados para las fases siguientes

1. **P0 de sincronizacion:** implementar el efecto visual real de todos los
   valores admitidos por `HomeModuleConfig.display_type`; hoy el contrato ofrece
   18 opciones y la Landing siempre usa el mismo carrusel.
2. **P0 de sincronizacion:** decidir y aplicar el comportamiento de
   `HomeCard.video`, `HomeCard.card_type='logo'` y `AboutUsConfig.is_visible`.
3. **P1 de gobernanza de contenido:** separar el chrome de presentacion que
   puede seguir fijo de los textos/URLs que deben editarse desde Core. Las tres
   secciones destacadas y el footer contienen valores fijos visibles.
4. **P1 de sistema visual:** centralizar los tokens hoy repartidos entre
   `HomeRenderer`, Hero, CTA, cards y footer antes de un rediseño amplio.

## Decisiones que preservan la arquitectura

- No introducir llamadas HTTP en subcomponentes de Landing: `HomeView` sigue
  siendo el cargador y `HomeRenderer` el renderer compartido.
- No sustituir `core/home-feed/`, `core/footer/`, `core/site-config/` ni
  `core/about-us/`; los contratos actuales ya separan correctamente cada
  responsabilidad.
- El Home Builder debe continuar usando `HomeRenderer` para su preview, de modo
  que todo cambio guardado y todo cambio en memoria produzcan la misma salida.
