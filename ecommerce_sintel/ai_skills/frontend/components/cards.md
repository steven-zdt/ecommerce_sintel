---
description: Inventario COMPLETO de componentes Vue existentes — layouts, UI generales, landing, customer, cards horizontales. Fuente de verdad de imports validos. Si un componente no aparece aqui, no existe.
metadata:
  domain: components
  supersedes: FRONTEND_COMPONENT_REGISTRY.md (raiz seccion 3-5, ecommerce_sintel secciones 1-5, 12-13)
  last_audited: "2026-07-18"
---

# Cards & Components — Registro completo

## REGLA DE ORO

```
PROHIBIDO importar componentes que no esten en este registro.
Si necesitas algo que no existe, crea un componente nuevo y agregalo aqui.
```

## 1. Layouts

| Componente | Path | Props | Notas |
|---|---|---|---|
| `AppShell` | `@/components/layout/AppShell.vue` | — | Layout admin: Sidebar 270px + Navbar 70px + RouterView + ToastManager. Sin props/emits, uso exclusivo en el router. |
| `Sidebar` | `@/components/layout/Sidebar.vue` | — | 7 grupos colapsables (`shop`, `ops`, `quotes`, `ts`, `renting`, `mkt`, `fulfillment`) |
| `Navbar` | `@/components/layout/Navbar.vue` | — | Barra superior glassmorphism, toggle sidebar mobile |
| `ToastManager` | `@/components/layout/ToastManager.vue` | — | Montado dentro de `AppShell`. No usarlo directo en vistas — los toasts se disparan solo con `useToast()` |
| `CustomerLayout` | `@/components/customer/CustomerLayout.vue` | — | Layout raiz del portal cliente: `CustomerNavbar` + `CustomerFooter` + `CartOffcanvas` + `SupportChatWidget`. Uso exclusivo como wrapper en el router — ver [[feedback_customer_routes_layout]] |
| `CustomerNavbar` | `@/components/customer/CustomerNavbar.vue` | — | Navbar publica con carrito |
| `CustomerFooter` | `@/components/customer/CustomerFooter.vue` | — | Footer publico |

## 2. UI generales (admin + compartidos)

| Componente | Path | Props | Notas |
|---|---|---|---|
| `SintelOffcanvas` | `@/components/ui/SintelOffcanvas.vue` | `modelValue`, `title`, `subtitle`, `width`, `loading` | Panel lateral CRUD — receta completa en [offcanvas.md](offcanvas.md) |
| `StarRating` | `@/components/ui/StarRating.vue` | `rating`, `maxRating(5)`, `size(24)`, `readOnly`, `showValue`, `allowHalf` | Emits `update:rating` |
| `PriceBreakdown` | `@/components/ui/PriceBreakdown.vue` | `breakdown(object\|null)` | Desglose de costos con totales |
| `CostRulesView` | `@/components/shared/CostRulesView.vue` | `entityType`, `entityId` | Vista generica de reglas de costo (renting/technical_services) |
| `IconRenderer` | `@/components/ui/IconRenderer.vue` | `icon`, `fallback('bi-question-circle')`, `extraClass`, `size` | Unico componente de render de iconos Bootstrap Icons: valida existencia real midiendo `::before` en el DOM (sin lista propia), cae a `fallback` si no existe. Usar SIEMPRE en vez de `<i class="bi ...">` crudo para cualquier `icon_class` que venga de BD (2026-07-15) |
| `StatusTimeline` | `@/components/shared/StatusTimeline.vue` | `mode('events'\|'steps')`, `steps[]` (`{key,label,icon}`), `activeIndex`, `accentColor`, `cancelled`, `cancelledMessage`, `events[]` (`{key,label,icon,color,date,description}`), `emptyMessage` | Timeline UNICO del proyecto (reemplazo de `ShipmentTimeline`/`RentalTimeline`/`OperationTimeline`/`ServiceTimeline`/`TrackingTimeline`/`UnifiedTimeline`/`OrderTimeline`, todos ahora wrappers delgados sobre este — ver `AUDITORIA/07_FRONTEND.md` FE-M4). No crear un timeline nuevo — traducir el modelo de datos propio a `steps` o `events` y usar este |

### 2.1 `components/base/` — biblioteca compartida cross-modulo (2026-07-18)

Construida por el `PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md` (`frontend/.AGENT/doc/`)
para fusionar componentes casi-identicos que existian por separado en Renting/Services/Shop.
No confundir con `components/customer/account/*` (design system de Mi Cuenta, sec. 4.0) —
ambos coexisten, `components/base/` es para piezas usadas fuera de `/mi-cuenta/*`.

| Componente | Path | Props principales | Fusiona |
|---|---|---|---|
| `BaseReviews` | `@/components/base/BaseReviews.vue` | `basePath` (`'renting/equipment'\|'services/services'`), `entityUuid`, `accentColor`, `itemLabel` | `EquipmentReviews.vue` + `ServiceReviews.vue` (eliminados) |
| `BaseAccordion` | `@/components/base/BaseAccordion.vue` | `items[]` (acepta `{question,answer}`, `{uuid,question,answer}` o `{q,a}`), `accentColor` | `EquipmentFAQ.vue` + `ServiceFAQAccordion.vue` (eliminados) |
| `BaseGallery` | `@/components/base/BaseGallery.vue` | `images[]` (string[] o `{image\|url,alt_text?}[]`), `title`, `iconClass`, `theme('renting'\|'services')`. Slot `#badge` con scope `{activeImage,activeIndex}` | `EquipmentGallery.vue` + `ServiceGallery.vue` (eliminados) |
| `BaseHorizontalCard` | `@/components/base/BaseHorizontalCard.vue` | `image`, `imageFit`, `placeholderIcon/Bg/Color`, `title`, `description`, `accentColor/Shadow/Border`. Slots `#placeholder-icon`, `#image-badge`, `#tags`, `#badges`, `#price`, `#actions` | Cascaron de `EquipmentHorizontalCard.vue`/`ServiceHorizontalCard.vue`/`ProductHorizontalCard.vue` (los 3 siguen existiendo como wrappers delgados, no eliminados — mismo import path que ya usan `RentalCatalogView`/`ServicesCatalogView`/`ShopCatalogView`) |
| `BaseBrandForm` | `@/components/base/BaseBrandForm.vue` | `item`, `mode`, `endpoint`, `hasLogo`, `hasActiveToggle`, `namePlaceholder` | Cascaron de `modules/shop/BrandForm.vue`/`modules/renting/RentingBrandForm.vue` (wrappers delgados, `hasLogo`/`hasActiveToggle` reflejan diferencia real de schema: `renting.RentingBrand` no tiene esos campos) |
| `BaseCategoryForm` | `@/components/base/BaseCategoryForm.vue` | `item`, `mode`, `endpoint`, `hasImage`, `hasSeo`, `entityLabel`, `namePlaceholder` | Cascaron de `modules/shop/CategoryForm.vue`/`modules/renting/RentingCategoryForm.vue` (wrappers delgados, `hasImage`/`hasSeo` reflejan diferencia real de schema: `renting.RentingCategory` no tiene `image`/`meta_title`/`meta_description`) |
| `BaseModal` | `@/components/base/BaseModal.vue` | `modelValue`(bool,required, v-model), `title`, `wide`(bool, max-width 800px), `bodyClass`(pass-through). Slots default (body) y `footer` (opcional) | Dialogo centrado generico — reemplaza el boilerplate de backdrop/header/footer repetido 7 veces en `HomeConfigView.vue` (Banner/Tarjeta/Grupo/FooterLink/FooterGroup/Nav/BrandItem), y tambien el modal bespoke de `DispatcherList.vue`. **No confundir con `SintelOffcanvas`** (panel lateral) — decision explicita del usuario (§3.4.1 del plan maestro) de mantener el patron centrado para estos casos en vez de forzarlos a panel lateral |
| `BaseContextCard` | `@/components/base/BaseContextCard.vue` | `icon`(required), `iconColor`(default `#1e40af`), `title`(required). Slots `badge` y default (filas `.ctx-row`) | Cascaron de `OrderContextCard.vue`/`PaymentContextCard.vue`/`RentalContextCard.vue` (`components/support/`, wrappers delgados, mismo prop `order`/`rental`, consumidos por `Customer360Panel.vue`). **Nota:** `.ctx-row` se estiliza con `:deep()` porque llega via slot desde el wrapper — el scoped CSS normal no penetra contenido de slots ajenos |
| `BaseInput` | `@/components/base/BaseInput.vue` | `modelValue`(v-model), `label`, `type`(default `text`), `placeholder`, `maxlength`, `required`, `disabled`, `hint`, `error` | Primer componente real del Grupo D (Fase 3 §3.5). Reemplaza `<label>+<input>` repetido en `OrganizationView.vue` (~20 veces) |
| `BaseTextarea` | `@/components/base/BaseTextarea.vue` | Igual que `BaseInput` + `rows`(default 3) | Mismo caso de uso, para `<textarea>` |
| `BaseUpload` | `@/components/base/BaseUpload.vue` | `label`, `accept`(default `image/*`), `previewUrl`. Emite `file-selected` con el `File` crudo (el consumidor arma su propio `FormData`) | Reemplaza el patron `<input type="file">` + `<img>` de preview repetido 3 veces en `OrganizationView.vue` (logo/favicon/og_image) |
| `BaseStatusBadge` | `@/components/base/BaseStatusBadge.vue` | `enumName`(required), `value`, `showIcon`, `fallbackClass`. Wrapper sobre `useEnums()` con workaround de reactividad para enums fuera del catalogo estatico | Resuelve §3.4.2 del plan maestro — fusiona `CustomerStatusBadge`/`OperationStatusBadge`/`ShipmentStatusBadge` (los 3 quedaron como wrappers delgados) |

**Pendiente (ver plan maestro §7.2):** `Payment*` (`components/shared/checkout/`, ya unificado
por su propio plan independiente `PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md`) — no migrado.
Accounts/KYC, Core/Home Builder, Organization (incluyendo su CSS `org-*`, con los 3 `Base*` de
arriba), Operations y Notifications/Security/Support ya migrados (2026-07-18). Grupo D solo
tiene 3 de ~14 componentes disenados construidos — el resto (`BaseSelect`, `BaseAddress`,
`BasePhoneInput`, etc.) se construye segun aparezca un consumidor real, no antes.
| `CheckoutStepper` | `@/components/shared/checkout/CheckoutStepper.vue` | `steps[](required)`, `current(Number,required)`, `clickable(bool,false)`, `ariaLabel` | Emit `update:current`. Stepper UNICO de wizards/checkout del proyecto (2026-07-18, unificacion Services-Renting) — reemplaza el markup propio duplicado de `RentalBookingWizard.vue` y `ServiceRequestWizard.vue`; `clickable` habilita navegar a pasos ya completados (usado por `RentalBookingWizard`), sin el prop el stepper es solo visual (usado por `ServiceRequestWizard` y `CheckoutModal`) |

## 3. Landing Page — `src/components/ui/landing/`

Ver tambien [[project_landing_premium]] en memoria — `HomeView` es orquestador puro, tokens CSS
viven en `.home-root`.

### 3.1 Primitivos (reutilizables en cualquier contexto)

| Componente | Path | Props clave | Descripcion |
|---|---|---|---|
| `LoadingSkeleton` | `.../landing/LoadingSkeleton.vue` | `width`, `height`, `radius`, `dark`, `count`, `gap`, `inline` | Skeleton shimmer configurable. `dark=true` invierte colores para fondos oscuros |
| `GlassCard` | `.../landing/GlassCard.vue` | `dark`, `hoverable`, `padded` | Base glassmorphism. Slot default |
| `SectionHeader` | `.../landing/SectionHeader.vue` | `eyebrow`, `title`, `subtitle`, `align`, `dark` | Titulo de seccion con animacion reveal. `title` soporta `*texto*` → gradiente azul-cian |
| `DividerWave` | `.../landing/DividerWave.vue` | `from`, `fill`, `flip` | Divisor SVG organico entre secciones. `from`=color seccion arriba, `fill`=color seccion abajo |

### 3.2 Hero

| Componente | Path | Props clave | Descripcion |
|---|---|---|---|
| `HeroSection` | `.../landing/HeroSection.vue` | `banners[]`, `loading` | Carousel Bootstrap `carousel-fade`. Fallback estatico si `banners=[]` |
| `HeroSlide` | `.../landing/HeroSlide.vue` | `banner{}`, `isFirst` | Contenido de un slide. Glass panel flotante si `isFirst && !banner.image && !banner.video` |
| `HeroBackground` | `.../landing/HeroBackground.vue` | `image`, `video` | Capa de fondo: video > imagen (Ken Burns) > gradiente animado con orbs |
| `HeroCTA` | `.../landing/HeroCTA.vue` | `primaryLabel`, `primaryUrl`, `ghostLabel`, `ghostUrl` | 2 botones: primary azul pill + ghost glass. Detecta URLs externas automaticamente |

### 3.3 Modulos de negocio

| Componente | Path | Props clave | Descripcion |
|---|---|---|---|
| `ModuleGrid` | `.../landing/ModuleGrid.vue` | `modules[]`, `loading` | Grid CSS auto-fill. Filtra `is_visible !== false`. IntersectionObserver propio |
| `ModuleCard` | `.../landing/ModuleCard.vue` | `module{}`, `visible`, `style` | Card individual. CSS var `--mc` para color dinamico. `visible` activa animacion reveal |

### 3.4 Flash Offers

| Componente | Path | Props clave | Descripcion |
|---|---|---|---|
| `FlashOffers` | `.../landing/FlashOffers.vue` | `offers[]`, `loading` | Seccion dark con header animado. IntersectionObserver propio |
| `FlashOfferCard` | `.../landing/FlashOfferCard.vue` | `offer{}` | Card individual con badge descuento + `CountdownTimer` |
| `CountdownTimer` | `.../landing/CountdownTimer.vue` | `secondsRemaining` | Timer aislado, `setInterval` propio en `onMounted`, limpia en `onUnmounted` |

### 3.5 Items destacados

| Componente | Path | Props clave | Descripcion |
|---|---|---|---|
| `FeaturedSection` | `.../landing/FeaturedSection.vue` | `eyebrow`, `title`, `link`, `linkLabel`, `items[]`, `type`, `loading` | Wrapper para productos/equipos/servicios. `title` soporta `*texto*` → gradiente |
| `FeaturedCarousel` | `.../landing/FeaturedCarousel.vue` | `items[]`, `type`, `loading` | Mobile: scroll horizontal snap. Desktop (≥768px): CSS grid |
| `FeaturedCard` | `.../landing/FeaturedCard.vue` | `item{}`, `type` | `type`: `'product'` \| `'rental'` \| `'service'`. Hover CTA slide-up |

### 3.6 Renderizador de secciones (`home_cards` / `card_groups`) — reemplaza Trust/Info cards

`TrustSection.vue`/`TrustCard.vue` fueron eliminados el 2026-07-11 por no tener uso (ver
[../editor/enterprise_sync_audit_2026_07_11.md](../editor/enterprise_sync_audit_2026_07_11.md)).
El sistema real y vigente que renderiza `home_cards`/`card_groups` en `HomeView.vue` es:

| Componente | Path | Props clave | Descripcion |
|---|---|---|---|
| `SectionRenderer` | `@/renderers/SectionRenderer.vue` | `group{}` (requerido), `cards[]` | Filtra `cards` por `group_name` + `is_active`. Renderiza header (eyebrow/title/desc) y delega el layout segun `group.layout_type` |
| `CardsGrid` | `@/components/ui/home/cards/CardsGrid.vue` | `cards[]`, `columns` | Layout `grid`/`cards`/`tabs` (default) |
| `CardsSlider` | `@/components/ui/home/cards/CardsSlider.vue` | `cards[]`, `columns` | Layout `slider` |
| `TimelineSection` | `@/components/ui/home/sections/TimelineSection.vue` | `cards[]`, `columns` | Layout `timeline` |
| `AccordionSection` | `@/components/ui/home/sections/AccordionSection.vue` | `cards[]`, `columns` | Layout `accordion` |

`useLayoutEngine()` (`@/composables/useLayoutEngine.js`) calcula el estilo de la seccion
(`buildSectionStyle(group)`) a partir de la config del grupo. `SectionRenderer` no importa estos 4
layouts de forma estatica — usa `defineAsyncComponent` para cada uno.

### 3.7 Stats y CTA final

| Componente | Path | Props clave | Descripcion |
|---|---|---|---|
| `AnimatedCounter` | `.../landing/AnimatedCounter.vue` | `value`, `label`, `suffix` | Count-up al entrar en viewport. rAF + easeOutExpo en 1.6s |
| `FooterCTA` | `.../landing/FooterCTA.vue` | `config{}` (FooterCTAConfig serializado) | Bloque CTA final con gradiente azul antes de `CustomerFooter`. Botones detectan URL externa automaticamente (2026-07-15) |
| `BrandSlider` | `.../landing/BrandSlider.vue` | `config{}` (BrandSliderConfig), `items[]` (BrandSliderItem) | Slider de marcas/clientes, scroll continuo CSS puro (sin libreria). Se renderiza en `HomeRenderer.vue` despues de `FooterCTA`. Ver [[project_brand_slider_icon_renderer]] |

### 3.8 Componentes eliminados del repo (Fase 6, auditoria enterprise_sync, 2026-07-11)

Ya NO existen en disco — no importar, no quedan ni como referencia obsoleta:

```
TrustSection.vue        → reemplazado por SectionRenderer.vue (eliminado antes, mismo dia)
TrustCard.vue           → idem
HeroCarousel.vue        → reemplazado por HeroSection.vue
ModuleCardsGrid.vue     → reemplazado por ModuleGrid.vue
FlashOffersSection.vue  → reemplazado por FlashOffers.vue
FeaturedItemCard.vue    → reemplazado por FeaturedCard.vue
InfoCardsGrid.vue       → reemplazado por SectionRenderer.vue (ver 3.6)
```

Verificado antes de borrar: 0 referencias en todo `frontend/src` para cada uno.

## 4. Componentes customer

| Componente | Path | Notas |
|---|---|---|
| `ItemCard` | `@/components/customer/ui/ItemCard.vue` | Props: `item(Object, required)`, `type('product'\|'rental'\|'service')`. Emits: `click`, `view`, `quote`, `add-to-cart`. Usa `PriceDisplay`, `StockBadge` |
| `ServiceCard` | `@/components/customer/ui/ServiceCard.vue` | Card de servicio tecnico (grid) |
| `PriceDisplay` | `@/components/customer/ui/PriceDisplay.vue` | Props: `price`, `discountedPrice`, `discountStart`, `discountEnd`, `mode('final'\|'per-day')`, `cotizar(bool)` |
| `StockBadge` | `@/components/customer/ui/StockBadge.vue` | Props: `stock(num)`, `available(bool)` |
| `FilterPanel` | `@/components/customer/ui/FilterPanel.vue` | Props: `categories[]`, `brands[]`, `showPrice`, `filters{}`. Emits: `change(filtersObject)`, `reset` |
| `FilterSidebar` | `@/components/customer/ui/FilterSidebar.vue` | Sidebar de filtros de catalogo |
| `DateRangePicker` | `@/components/customer/ui/DateRangePicker.vue` | Selector de rango de fechas |
| `DocumentUploader` | `@/components/customer/ui/DocumentUploader.vue` | Upload de documentos |
| `SupportChatWidget` | `@/components/customer/ui/SupportChatWidget.vue` | Montado en `CustomerLayout`. No instanciar directo en vistas |
| `TrackingTimeline` | `@/components/customer/ui/TrackingTimeline.vue` | Timeline de seguimiento de operacion |
| `OperationReviewModal` | `@/components/customer/ui/OperationReviewModal.vue` | Modal de calificacion de operacion (unico modal real del proyecto, fuera del patron de offcanvas) |
| `CartOffcanvas` | `@/components/customer/CartOffcanvas.vue` | Props: `modelValue(bool, required)`. Emits: `update:modelValue`. Usa `useCartStore` internamente — no recrear logica del carrito en otros componentes |
| `AccountSidebar` | `@/components/customer/AccountSidebar.vue` | Sidebar de `/mi-cuenta/*` |
| `ColombianAddressForm` | `@/components/customer/checkout/ColombianAddressForm.vue` | Form de direccion Colombia |

### 4.0 Design System de "Mi Cuenta" — `@/components/customer/account/` (2026-07-17)

Unificacion visual de las 8 vistas bajo `/mi-cuenta/*` (Perfil, Pedidos, Operaciones,
Wishlist, Direcciones, Metodos de Pago, Cotizaciones, Asociado de Negocio) — antes cada
vista reinventaba su propio card/badge/empty-state/skeleton con micro-variaciones. Toda
vista nueva o modificada bajo `views/customer/account/` DEBE usar estos componentes en vez
de CSS propio. No se construyo un Timeline nuevo — se reutiliza `StatusTimeline` (seccion 2).

| Componente | Path | Props / Emits | Notas |
|---|---|---|---|
| `CustomerAccountShell` | `.../account/CustomerAccountShell.vue` | `maxWidth('1100px')` | Reemplaza el wrapper `.account-page`+`<AccountSidebar>`+`.account-content` copy-pasteado. Define los CSS custom properties del sistema (`--acc-radius:14px`, `--acc-shadow-hover`, `--acc-border`, `--acc-text`, `--acc-muted`, `--acc-accent`, etc.) — heredan a todo componente hijo por cascada de CSS vars, sin CSS global |
| `CustomerPageHeader` | `.../account/CustomerPageHeader.vue` | `title(required)`, `subtitle`. Slot `actions` | Titulo+subtitulo+acciones de cabecera, unico para las 8 vistas |
| `CustomerCard` | `.../account/CustomerCard.vue` | `tag('div')`, `highlighted(bool)`, `hoverable(bool, true)`, `variant('default'\|'brand')`, `brandTone('blue'\|'green')` | Card generica (radio/sombra/padding). `variant="brand"` = gradiente de tarjeta de credito (Metodos de Pago), unica variante visual permitida |
| `CustomerStatusBadge` | `.../account/CustomerStatusBadge.vue` | `enumName(required)`, `value`, `showIcon`, `fallbackClass` | Wrapper delgado sobre `@/components/base/BaseStatusBadge.vue` (2026-07-18 — antes wrapeaba `useEnums()` directo; `OperationStatusBadge`/`ShipmentStatusBadge` tambien wrapean el mismo `BaseStatusBadge` ahora, ver §2.1) |
| `CustomerEmptyState` | `.../account/CustomerEmptyState.vue` | `icon('bi-inbox')`, `title(required)`, `description`. Slot `action` | Estado vacio unico (antes 5 variantes con padding distinto) |
| `CustomerErrorState` | `.../account/CustomerErrorState.vue` | `title`, `description`. Emit `retry` | Nuevo — no existia manejo de error de fetch distinto del empty-state |
| `CustomerSkeleton` | `.../account/CustomerSkeleton.vue` | `count(3)`, `height('110px')`, `layout('list'\|'grid')` | Wrapper sobre `LoadingSkeleton` (3.1) — reemplaza las 6 copias de `.skeleton`/`@keyframes shimmer` |
| `CustomerButton` | `.../account/CustomerButton.vue` | `variant('primary'\|'secondary'\|'danger'\|'icon')`, `size('sm'\|'md')`, `loading`, `ariaLabel` (obligatorio si `variant="icon"`, por convencion) | Boton unico — `variant="icon"` sin `ariaLabel` es un bug de accesibilidad |
| `CustomerConfirmInline` | `.../account/CustomerConfirmInline.vue` | `message`, `confirmLabel('Eliminar')`, `loading`. Emits `confirm`, `cancel` | Generaliza `.addr-confirm-delete` — confirmacion destructiva SIEMPRE inline, nunca `confirm()` nativo ni modal (ver dialogs.md) |
| `CustomerOverlayPanel` | `.../account/CustomerOverlayPanel.vue` | `modelValue(required)`, `title`, `subtitle`, `width('560px')`. Slots default + `footer` | Une `.form-overlay`/`.modal-overlay` — exclusivo para formularios/detalle, NUNCA confirmaciones |
| `CustomerDetailRow` | `.../account/CustomerDetailRow.vue` | `label(required)`, `value`, `icon`. Slots default + `action` | Fila label/valor — usado en la ficha de Perfil |
| `CustomerSection` | `.../account/CustomerSection.vue` | `title(required)`, `icon`. Slots default + `actions` | Bloque con titulo de seccion, agrupa contenido (Perfil: Info Personal/Contacto/Ubicacion/Seguridad) |
| `CustomerAvatar` | `.../account/CustomerAvatar.vue` | `src`, `initials`, `size(72)`, `editable(bool)`. Emit `click` | Circulo con imagen o iniciales — reemplaza el markup inline de `AccountSidebar` |
| `CustomerPagination` | `.../account/CustomerPagination.vue` | `page(required)`, `totalPages(required)`. Emit `update:page` | Wrapper sobre `pagination pagination-sm` de Bootstrap |

### 4.1 Renting — componentes de disponibilidad (2026-07-07)

| Componente | Path | Notas |
|---|---|---|
| `RentalStatusCard` | `@/components/customer/renting/RentalStatusCard.vue` | Badge de estado de un `RentalRequest`, usado en `MyRentalsView` |
| `RentalTimeline` | `@/components/customer/renting/RentalTimeline.vue` | Stepper del ciclo de vida del `OperationTicket` de una renta (no del `RentalRequest`) |
| `RentalCostsCard` | `@/components/customer/renting/RentalCostsCard.vue` | Desglose de costos del wizard de renta (paso 4) |
| `AvailabilityPill` | `@/components/customer/renting/AvailabilityPill.vue` | Props: `checking(Bool)`, `available(Bool\|null)`, `nextAvailableDate`, `nextAvailableTime`. Emite `click`. 3 estados: verificando/disponible/no-disponible con sugerencia. Usado en paso 3 del wizard de renta |
| `AvailabilityCard` | `@/components/customer/renting/AvailabilityCard.vue` | Props: `checking`, `available`, `nextAvailableDate`, `nextAvailableTime`, `rentalMode`, `occupiedSlots(Array)`. Emite `select({date,time})`. Solo visible si `available===false` |
| `RentalHourSelector` | `@/components/customer/renting/RentalHourSelector.vue` | Props: `deliveryTime`, `pickupTime`, `disabled`. Emite `update:delivery-time`/`update:pickup-time` (usar con `v-model:delivery-time`/`v-model:pickup-time`) |

### 4.2 Technical Services — componentes de detalle publico y wizard (2026-07-18)

Extraidos de `ServiceDetailView.vue` (antes monolitico, 0 subcomponentes) y del sidebar del
wizard, como Fase 4-5 del plan de unificacion con Renting (ver
`technical_services/.AGENT/docs/PLAN_UNIFICACION_SERVICES_CON_RENTING.md`). Replican el
**patron** de los equivalentes de `components/renting/detail/*`, no el codigo 1:1 (Renting
esta acoplado a `Equipment`/`EquipmentVariant`).

| Componente | Path | Notas |
|---|---|---|
| `ServiceGallery` | `@/components/services/detail/ServiceGallery.vue` | Props: `images[]`, `title`, `iconClass`, `featured(bool)`. Galeria sticky con miniaturas, mismo patron que `EquipmentGallery.vue` |
| `ServiceFeatureList` | `@/components/services/detail/ServiceFeatureList.vue` | Props: `groups[]` (`{title,icon,items[]}`). Grid de grupos de recursos (Caracteristicas/Herramientas/Software/Protocolos/Compatibilidad/Accesorios) con chips |
| `ServiceScopeList` | `@/components/services/detail/ServiceScopeList.vue` | Props: `title(required)`, `icon(required)`, `items[]`, `iconColorClass`. Lista de alcance (usado 3x: Incluye/No incluye/Entregables) |
| `ServiceSpecificationTable` | `@/components/services/detail/ServiceSpecificationTable.vue` | Props: `specs[]` (`{label,value}`). Ficha tecnica en grid de 4 columnas |
| `ServiceFAQAccordion` | `@/components/services/detail/ServiceFAQAccordion.vue` | Props: `items[]` (`{q,a}`). Acordeon nativo `<details>`, datos reales desde `ServiceFAQ` (backend, Fase 2) |
| `ServiceProfessionals` | `@/components/services/detail/ServiceProfessionals.vue` | Props: `serviceUuid(required)`. Consume `GET services/services/{uuid}/technicians/` (nuevo, AllowAny) — muestra tecnicos calificados/disponibles para la categoria del servicio via `TechnicianSelector.get_available_for_category`; sin calificacion/experiencia (no existen esos campos en `TechnicianProfile`) |
| `ServiceReviews` | `@/components/services/detail/ServiceReviews.vue` | Props: `serviceUuid(required)`. Resenas reales via `GET/POST services/services/{uuid}/reviews\|review/` — mismo patron que `EquipmentReviews.vue`, gate de creacion exige `ServiceOperation.CLOSED` (no `RentalRequest.STATUS_FINISHED`, este dominio no tiene modelo "request" unico) |
| `ServiceRequestSummary` | `@/components/customer/services/ServiceRequestSummary.vue` | Props: `serviceName`, `variant`, `pkg`, `priceInfo`, `scheduleLabel`. Sidebar de resumen persistente (pasos 2-3 del wizard), equivalente a `RentalCostsCard`+`AvailabilityPill` de Renting — reutiliza `ServicePriceBreakdown` (ya existia) para el desglose |

## 5. Cards horizontales — vista lista de catalogo

Las 3 vistas de catalogo (`ShopCatalogView`, `RentalCatalogView`, `ServicesCatalogView`) tienen
toggle grid/lista, `viewMode = ref('list')` es el default. Las cards horizontales emiten `@view`
y `@quote` al padre; el padre navega con `router.push`.

| Vista | Ruta | Card grid | Card lista |
|---|---|---|---|
| `ShopCatalogView` | `/tienda` | `ItemCard` | `ProductHorizontalCard` |
| `RentalCatalogView` | `/alquiler` | `ItemCard` (type=rental) | `EquipmentHorizontalCard` |
| `ServicesCatalogView` | `/servicios` | `ServiceCard` | `ServiceHorizontalCard` |

| Componente | Path | Props / Emits | Notas |
|---|---|---|---|
| `ProductHorizontalCard` | `@/components/shop/ProductHorizontalCard.vue` | `product(Object, required)` — emits `view`, `add-to-cart` | 3 col: imagen \| descripcion+stock \| precio+acciones. COP via `Intl.NumberFormat` |
| `ServiceHorizontalCard` | `@/components/services/ServiceHorizontalCard.vue` | `service(Object, required)` — emits `view`, `quote` | 3 col: imagen \| categoria+nivel+descripcion \| precio-desde+acciones. Accent `#d97706`. Precio min de `variants[].calculated_price`. Fallback imagen: `bi-tools` sobre `#fffbeb`. Sin stock — servicios no tienen inventario |
| `EquipmentHorizontalCard` | `@/components/renting/EquipmentHorizontalCard.vue` | `equipment(Object, required)` — emits `view`, `quote` | 3 col: imagen \| descripcion+disponibilidad \| precio/dia+acciones. Accent `#7c3aed`. Sin `useCartStore` — navegacion delegada al padre via emits |

## 6. Vistas — paths por dominio

| Dominio | Path base | Ejemplos |
|---|---|---|
| Admin | `@/views/admin/` | `AdminLoginPage.vue`, `DashboardView.vue`, `ProfileView.vue` |
| Auth publica | `@/views/auth/` | `LoginView.vue`, `RegisterView.vue`, `RegisterContractorView.vue`, `VerifyEmailLinkView.vue` |
| Customer | `@/views/customer/{shop,renting,services,checkout,account,contractors,operations,quotes}/` | `ShopCatalogView.vue`, `RentalRequestWizard.vue`, `CustomerProfileView.vue`, `ContractorOnboardingWizard.vue`, etc. |
| Landing/Home | `@/views/` | `LandingView.vue` (`/`, publica), `HomeView.vue` en `customer/` (`/inicio`, autenticado) |

Mapa completo de rutas ↔ nombre de ruta: [../architecture/routing.md](../architecture/routing.md).

## 7. Modulos admin — componentes por dominio backend

| Modulo | Componentes | Endpoints base |
|---|---|---|
| `shop` | `ProductList`, `ProductForm`, `CategoryList`, `CategoryForm`, `BrandList`, `BrandForm`, `TaxList`, `TaxForm` | `shop/` (R), `dashboard/` (W) |
| `inventory` | `InventoryList` | `inventory/stock-records/` |
| `orders` | `OrderList`, `OrderDetail` | `orders/orders/` |
| `users` | `UserList`, `UserForm`, `UserDetail` | `users/` (paginacion/filtros/busqueda server-side) |
| `quotes` | `QuotationList`, `QuotationDetail`, `AdditionalCostsView`, `AdditionalCostForm` | `quotes/quotations/` |
| `renting` | `RentingList`, `RentingForm`, `RentingDetail`, `RentingCategoryList`, `RentingBrandList`, `RentalLaborList`, `VariantFormModal`, `CostRuleFormModal`, `CostRulesPanel`, `VariantsPanel`, `LogisticsPanel`, `RentingRequestList`, `RentalRequestActionsPanel` | `renting/` (R), `dashboard/` (W) — excepcion: `RentingRequestList`/`RentalRequestActionsPanel` escriben a `renting/rental-requests/{uuid}/...` directo, ver [../architecture/frontend_architect.md](../architecture/frontend_architect.md) |
| `technical_services` | `ServiceList`, `ServiceForm` (7 tabs: General/Imagen/Variantes/Costos/Paquetes/FAQ/Marketing), `ServiceFAQManager` (tab FAQ, `dashboard/service-faqs/`, CRUD+reorder+toggle-active — dedicado, NO una generalizacion de `CatalogListManager` de Renting, ver plan de unificacion), `ServiceDetail`, `ServiceCategoryList`, `ServiceCategoryForm`, `ServiceLevelList`, `ServiceLevelForm`, `ServiceOperationBoard` (tablero de Operaciones de Servicios Tecnicos, `components/shared/BaseOperationBoard` compartido con Renting — faltaba en este registro, agregado 2026-07-18), `TechnicianAssignmentBoard`, `TechnicianCalendarBoard` | `technical_services/` (R), `dashboard/` (W); `TechnicianAssignmentBoard` consume `orders/service-orders/assignment-queue/` + acciones de asignacion + `auth/admin/professionals/{profile_uuid}/schedule/` |
| `accounts` | `ProfessionalsAdminList` | `auth/admin/professionals/` (GET lista+metrics, PATCH toggle-availability, GET schedule) |
| `core` | `HomeConfigView` | `dashboard/site-brand/`, `dashboard/banners/`, `dashboard/modules/`, `dashboard/home-cards/` |
| `marketing` | `MarketingView`, `CampaignForm`, `AgentRunDetail` | `marketing/dashboard/` |
| `operations` | `OperationBoard`, `OperationDetail`, `DispatcherList` | `operations/` |
| `support` | `SupportDashboardView` | `support/` |
| `security` | `SecurityDashboardView` | `dashboard/security-events/` |
| `notifications` (2026-07-11) | `NotificationsAdminView` (tabs Plantillas/Logs) | `dashboard/notification-templates/`, `dashboard/notification-logs/` |
| `payment` (2026-07-11) | `PaymentTransactionsAdminView` (tabs Wompi/Nequi/COD) | `dashboard/payment-transactions/`, `.../nequi/`, `.../cod/` |

`ProductForm.vue` (`@/modules/shop/ProductForm.vue`) tiene 5 tabs: General (create+edit), SEO
(create+edit), Variantes (solo edit), Costos (solo edit, `ProductCostRule` CRUD), Imagenes (solo
edit, upload multipart + set-primary + delete). Endpoints de imagen/variante en
[../architecture/frontend_architect.md](../architecture/frontend_architect.md).

## 8. Imports que NO existen — no inventar

```js
import { Button }   from '@/components/ui/Button.vue'     // NO
import { Badge }    from '@/components/ui/Badge.vue'       // NO
import { Rating }   from '@/components/ui/Rating.vue'      // NO
import { Modal }    from '@/components/ui/Modal.vue'       // NO — ver dialogs.md
import { Spinner }  from '@/components/ui/Spinner.vue'     // NO — usar LoadingSkeleton o <div class="spinner-border">
import { Card }     from '@/components/ui/Card.vue'        // NO — usar GlassCard (landing) o card Bootstrap (admin)
import { Input }    from '@/components/ui/Input.vue'       // NO — usar HTML nativo + BS5
import { Table }    from '@/components/ui/Table.vue'       // NO — ver datatable.md
import { Drawer }   from '@/components/ui/Drawer.vue'      // NO — usar SintelOffcanvas
```

## Ver tambien

- [../architecture/routing.md](../architecture/routing.md) — mapa de vistas por ruta
- [../architecture/state_management.md](../architecture/state_management.md) — stores usados por estos componentes
- [../architecture/vue_patterns.md](../architecture/vue_patterns.md) — composables (`useApi`, `useEnums`, etc.)

*Actualizar este archivo cada vez que se agregue un componente, vista o modulo admin nuevo.*
