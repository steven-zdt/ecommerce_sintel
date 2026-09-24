# PDP Publica (Renting) — Baseline real (Fase 0, mision "Remodelar PDP Renting", 2026-09-16)

Metodo: lectura directa de router/componentes/serializers/modelos + `curl` real contra
un equipo de dev. Nada se infiere de documentacion vieja sin releer el codigo real.

## 0. UUID objetivo del brief -- NO existe en dev (mismo patron que la mision Shop)

`d443139b-7b94-4c41-9fed-9e96c409ac7f` -> confirmado `None` via ORM
(`Equipment.objects.filter(uuid=...)`). Se uso el fallback real
`6f02beb4-4144-411e-9941-6a3ab1521d36` ("taladro", marca "stanlie") para toda la
verificacion de contrato de esta fase. **Aviso real:** este equipo tiene
`stock: 0` (`availability.status: "unavailable"`) y CERO imagenes/variantes/
caracteristicas/specs/FAQ/reviews en dev -- sirve para confirmar el contrato JSON,
pero NO es representativo de un equipo con contenido rico. Antes de construir la
Fase 2+ conviene buscar un equipo real con stock>0 y variantes reales para probar
el flujo de disponibilidad de verdad (`Equipment.objects.filter(is_deleted=False,
variants__stock__gt=0).first()` o similar).

## 1. Ruta real (CHECKPOINT 0 — CONFIRMADO)

Identica a Shop en la capa de routing: `frontend/src/apps/admin/routes/
customer.routes.js` -> `alquiler/:uuid` (`name: rental-detail`) -> mismo componente
compartido `views/customer/detail/PublicDetailView.vue` (`moduleType` se deriva de
`route.path.includes('alquiler')` -> `'renting'`) -> renderiza
`views/customer/detail/RentingDetailContent.vue` con **una sola prop `:detail`**
(a diferencia de Shop, que necesita 2 props `product`+`initial-reviews`).

**Un solo fetch real** (`PublicDetailView.vue::fetchDetail()`):
`GET /api/v1/unified/detail/{uuid}/?module=renting` -- confirmado leyendo el
codigo, Renting NO complementa con un segundo/tercer fetch como si hace Shop.

## 2. Hallazgo arquitectonico mas importante: NO hay variant/period/availability picker hoy

`RentingDetailContent.vue` (824 lineas) es hoy una pagina **puramente
informativa/marketing**, sin ningun estado interactivo de reserva:

- No hay `selectedVariant`, no hay selector de variante en el template.
- No hay rental_mode (dia/hora) toggle.
- No hay date pickers.
- No hay llamada a `check-availability` desde esta vista -- `detail.availability`
  viene YA resuelto (status/label/detail/total_stock/available_now) desde el
  backend, es informacion agregada de "ahora mismo", no de un rango de fechas
  elegido por el usuario.
- El UNICO CTA interactivo real es un `RouterLink :to="{name:'rental-request',
  params:{uuid}}"` ("Reservar ahora"/`detail.hero.cta_label`) que manda
  DIRECTO al wizard (`RentalBookingWizard.vue`) -- ahi es donde HOY viven
  variante, fechas, modalidad, disponibilidad, cantidad y costo.

**Esto es distinto del hallazgo de Shop.** En Shop, `ProductPurchaseCard.vue` ya
existia completo (precio, stock, cantidad, agregar al carrito) y el rediseno fue
"reubicar en su propia columna". En Renting, el "Panel de Reserva" que pide la
Fase 2-24 del brief (variante + modalidad + periodo + disponibilidad + resumen de
costo + CTA) **no existe como componente en ningun lado del arbol actual** -- ni
en el detalle, ni siquiera factorizado aparte del wizard. Construirlo tal como lo
describe el brief es una **feature nueva real**, no una reorganizacion de grid.

## 3. Contrato de datos real -- 2 DTOs distintos, ninguno trae variantes

### 3a. `GET /api/v1/unified/detail/{uuid}/?module=renting` (el que usa HOY `RentingDetailContent.vue`)

Campos reales top-level: `uuid, slug, module_type, hero{...con pricing anidado},
gallery{principal,principal_images,installation_images,detail_images,
view_360_images,all_images}, pricing{price_per_day,price_per_hour,
formatted_*,discount_*,has_promotion,components[],currency_*}, marketing,
availability{status,status_label,status_detail,total_stock,available_now,
next_available_date}, description, technical{features[],specification_groups[],
requirements[]}, included_items[], excluded_items[], requirements[], faq[],
documents[], videos[], reviews, related_items[], recommendations[], seo{...}`.

Confirmado con curl real (equipo "taladro"): `price_per_day: 125000.0` Y
`price_per_hour: 12500.0` ambos presentes simultaneamente -- el modelo dual
dia/hora del brief (seccion 12) es real. **No hay clave `variants` en este DTO.**

### 3b. `GET /api/v1/renting/equipment/{uuid}/detail/` (endpoint RICO real, existe, pero HOY nadie en el frontend publico lo llama)

`renting/api/views.py:369` (`EquipmentViewSet.full_detail`, `AllowAny`,
`EquipmentPublicDetailPresenter` + `EquipmentPublicDetailDTOSerializer`).
Campos reales confirmados con curl: `uuid, slug, hero{...}, pricing{...},
marketing, technical{features,specification_groups,requirements},
services{included_items,excluded_items,optional_services,services_included},
media{gallery{...},videos,documents}, faqs, reviews, availability{...},
**commercial_options**[{modality:"renting",enabled,terms}, {modality:"comodato",
enabled,terms:[12,24]}], **logistics**{delivery_cost,pickup_cost,
installation_cost,calibration_cost,training_cost,startup_cost,formatted_*},
related_equipment, seo`.

**Confirma que COMODATO es real** (`EquipmentCommercialOption`, ver
`renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` linea 24) -- el brief NO lo
inventa, secciones 13/54 son correctas. **Confirma que
`EquipmentLogisticsConfig` es real y esta expuesto** (`logistics` block, brief
seccion 30 correcto). **Este DTO TAMPOCO trae `variants`** -- ni siquiera el
endpoint "rico" las expone.

### 3c. Variantes: tercer endpoint, separado

`GET /api/v1/renting/variants/?equipment={uuid}` (`EquipmentVariantViewSet.list`,
`renting/api/views.py:386-396`, `AllowAny`) -> `EquipmentVariantSerializer` sobre
`EquipmentVariantSelector.list_for_equipment(equipment_uuid)`. Campos reales del
modelo (confirmado en `renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md`):
**`sku, rental_price_per_day, rental_price_per_hour, stock, is_active`
UNICAMENTE** -- regla arquitectonica vigente desde la migracion `0022` (Equipment
= aggregate root con TODO el contenido descriptivo; Variant = solo
inventario/precio). **Esto significa que una variante de Renting NUNCA puede
tener imagenes/atributos propios como si tiene `ProductVariant` en Shop** -- el
brief seccion 6 ("si una variante tiene imagenes especificas, cambiar la
galeria") no aplica a Renting: el modelo real no lo permite, no es un caso a
soportar "por si acaso", es estructuralmente imposible hoy. Documentado como
diferencia real de dominio, no como gap a resolver.

## 4. Disponibilidad -- contrato real y seguro para reusar (CHECKPOINT 16-17)

`GET /api/v1/renting/equipment/{uuid}/check-availability/` (`renting/api/
views.py:145-151`, `AllowAny`).

Query params reales: `variant=<uuid>` (requerido), `start_date=YYYY-MM-DD`
(requerido), `end_date=YYYY-MM-DD` (requerido, debe ser posterior a start_date),
`quantity=<int>` (default `1`), `rental_mode=days|hours` (default
`RentalRequest.RENTAL_MODE_DAYS`).

Respuesta real: `{available: bool, variant_uuid, start_date, end_date, quantity,
rental_mode, next_available_date, next_available_time, occupied_slots[]}`.
Motor real detras: `AvailabilityEngine.is_available()` (calendario propio via
`RentalPeriod`, **NO Inventory/StockRecord** -- confirmado en el `.AGENT.md` del
dominio, brief seccion 55 es correcto en advertir esto). Validacion server-side
real de fechas/formato/orden -- 400 si `end_date <= start_date` o formato
invalido. Este es el endpoint que hay que llamar desde el nuevo panel de reserva
para cumplir la regla del brief "nunca declarar disponible sin verificar" --
ya existe, ya lo usa el wizard, es seguro reusarlo tal cual.

## 5. Arbol de componentes real (el que SI se renderiza)

```
PublicDetailView.vue (shell: loading/error/breadcrumb/SEO)
└─ RentingDetailContent.vue (TODA la logica/markup de Renting vive aqui, 2 columnas hoy)
   ├─ BaseGallery.vue (components/base/) -- MISMO componente que Shop, sin `lightbox` activado hoy
   ├─ MediaImage.vue (components/ui/) -- usado en "Equipos relacionados"
   ├─ DiscountBadge.vue, UrgencyBanner.vue, TagBadge.vue (components/marketplace/)
   ├─ EquipmentIncludedList.vue, EquipmentExcludedList.vue, EquipmentRequirementList.vue,
   │  EquipmentVideoGallery.vue, EquipmentDocumentList.vue (components/renting/detail/,
   │  lazy via defineAsyncComponent) -- estos son los MISMOS componentes que Shop
   │  reusa (`ShopDetailContent.vue` los importa identicos)
   ├─ BaseAccordion.vue (components/base/) -- FAQ
   └─ BaseReviews.vue (components/base/) -- reviews, via `base-path="renting/equipment"`
      (patron GENERICO reusable por entidad, distinto del patron de Shop que
      resuelve resenas manualmente en el padre -- Renting delega TODO el CRUD de
      resenas a este componente compartido)
```

**Componentes de `renting/detail/` que Shop NO usa (Renting-only en el arbol
actual):** ninguno adicional a nivel visual -- `EquipmentFeatureTable.vue` y
`EquipmentSpecificationTable.vue` SI existen en el directorio pero
`RentingDetailContent.vue` los reemplaza con markup inline propio (`feature-card`/
`spec-group-card` a mano, ver lineas 198-249) en vez de reusarlos -- Shop en
cambio SI los importa. Es decir: **Renting tiene el markup duplicado de lo que
esos 2 componentes ya resuelven** -- una limpieza real disponible (no
obligatoria para esta mision, pero se documenta como oportunidad, brief seccion
25 pide explicitamente no crear equivalentes de algo que ya existe: aqui ya
existe y no se usa).

## 6. Layout actual real (NO es 3 columnas)

`row g-4 g-lg-5`: `col-lg-5` (galeria + trust-grid + `availability-card`
informativo con link "Consultar fechas exactas" al wizard) + `col-lg-7` (TODO lo
demas: badges, titulo, urgency banner, discount badge, quick-benefits,
quick-specs, Y el `package-panel` -- precio+CTA "Reservar ahora" -- anidado al
final del mismo bloque, mismo patron que Shop tenia antes de su rediseno).
Sticky: `.gallery-sticky { position: sticky; top:88px }`, estatico bajo 992px.

**Para llegar a 3 columnas** (mismo movimiento estructural que Shop): partir
`col-lg-7` en columna central (info: badges/titulo/urgency/quick-specs/
features/included-excluded/specs) + columna derecha dedicada al panel de
reserva. La diferencia real con Shop es que ese panel derecho hoy es solo un
`package-panel` estatico (precio + 1 boton) -- convertirlo en el "Rental/
Reservation Panel" completo del brief (variante+modalidad+periodo+
disponibilidad+resumen+CTA) es trabajo nuevo, no reubicacion.

## 7. Estado / composables reales

Sin Pinia store dedicado. Estado local minimo en `RentingDetailContent.vue`:
`isFavorite` (localStorage), nada de variante/fecha/disponibilidad (no existe
porque la interaccion no existe). El `detail` completo llega ya resuelto via
prop desde el padre -- ni `watch` de variante ni computed de precio dinamico
(los `computed` existentes, `rentingVariantsCount`/`rentingPackageLabel`, son
**derivaciones cosmeticas de `pricing.components`**, no relacionadas con
variantes reales del modelo -- nombre confuso, no hacen lo que su nombre sugiere).

`RentalBookingWizard.vue` (`views/customer/renting/`) es donde SI vive hoy toda
la logica real: fetch de variantes (`GET renting/variants/?equipment=`), fechas,
`rental_mode`, llamada a `check-availability`, calculo de costo, y finalmente
`RentalRequestCommands.create_request()` en el backend. No se leyo linea por
linea en esta fase (fuera del alcance de "solo lectura, no codigo" del research,
tiempo limitado) -- **antes de construir el nuevo panel, releer este archivo
completo para no reimplementar su logica de availability/pricing de forma
distinta/incompatible.**

## 8. Modelos backend reales confirmados (vs. asumidos por el brief)

Verificado en `renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` +
`renting/api/views.py` -- TODOS reales, ninguno inventado por el brief:

`Equipment` (aggregate root), `EquipmentVariant` (SOLO `sku`,
`rental_price_per_day`, `rental_price_per_hour`, `stock`, `is_active` -- nada
mas), `EquipmentImage`, `RentalIncludedItem`, `RentalExcludedItem`,
`RentalFeature`, `RentalSpecificationGroup`/`RentalSpecification`,
`RentalRequirement`, `RentalServiceIncluded`, `RentalOptionalService`,
`RentalFAQ`, `RentalVideo`, `RentalDocument`, `EquipmentLogisticsConfig`,
`RentalCostRule`/`RentalCostAssignment` (FK a Variant, reglas de PRECIO --
IVA/descuento/deposito/seguro/recargo, NO logistica pese al nombre parecido),
`RentalPeriod` (calendario real de disponibilidad), `RentalRequest` (+
Location/Contact/Costs/PaymentInfo), `EquipmentCommercialOption` (RENTING vs
COMODATO, con `comodato_enabled`/plazos en meses -- **confirma que COMODATO es
real**, brief secciones 13/54 correctas).

## 9. Gaps reales vs. lo que asume el brief de 59 secciones

1. **El panel de reserva interactivo (variante+modalidad+periodo+disponibilidad+
   costo) NO existe hoy en ningun componente del detalle** -- es la Fase 2-24 del
   brief completa por construir desde cero, reusando el contrato de
   `check-availability` (seguro, ya probado por el wizard) y el endpoint de
   variantes (`renting/variants/?equipment=`), pero sin un componente base
   existente equivalente a `ProductPurchaseCard.vue` de Shop. Alcance real
   mayor que el de la mision Shop -- considerar si esta mision se acota primero
   a layout+datos-ya-resueltos (Fase 2, reorganizar a 3 columnas con lo que YA
   trae el DTO) antes de construir el panel interactivo completo (Fase 3+).
2. **Variantes de Renting no pueden tener imagenes propias** (a diferencia de
   lo que el brief seccion 6 asume por simetria con Shop) -- estructuralmente
   imposible en el modelo real (`EquipmentVariant` no tiene ese campo, regla
   vigente desde migracion 0022). No construir esa capacidad.
3. **Ni el DTO unificado ni el DTO "rico" (`renting/equipment/{uuid}/detail/`)
   traen variantes** -- hay que llamar a un TERCER endpoint
   (`renting/variants/?equipment=`) para poblar el selector, algo que Shop no
   necesito (su DTO rico ya traia `variants[]` inline).
4. **El equipo real usado para validar tiene stock 0 y cero contenido rico** --
   antes de dar por buena visualmente la Fase 2+, conseguir/usar un equipo real
   de dev con stock>0, variantes reales y galeria para probar el flujo de
   disponibilidad de verdad (positivo Y negativo, brief seccion 42).
5. **`EquipmentFeatureTable.vue`/`EquipmentSpecificationTable.vue` existen pero
   no se usan hoy en Renting** (markup duplicado a mano en su lugar) -- limpieza
   disponible, no bloqueante.
6. **COMODATO y `EquipmentLogisticsConfig` SI son reales y estan expuestos**
   (unico caso donde el brief acerto sin matices en una suposicion no trivial) --
   pero SOLO en el DTO "rico" (`renting/equipment/{uuid}/detail/`), que HOY el
   frontend publico no consume -- `RentingDetailContent.vue` tendria que migrar
   de `unified/detail` al DTO rico (o complementar con una segunda llamada,
   igual que hizo Shop) para poder mostrar modalidad/logistica reales.

## 10. Cobertura de la verificacion

- **Verificado a nivel de codigo + curl real:** routing completo, los 2 DTOs
  de detalle, el endpoint de variantes (URL y campos del modelo, no el JSON en
  vivo -- el equipo de prueba no tiene variantes creadas), el endpoint de
  disponibilidad (codigo fuente completo, no se ejecuto una llamada real con
  fechas en esta fase de solo-lectura), el arbol de componentes completo de
  `RentingDetailContent.vue`, el layout/CSS actual.
- **No leido linea por linea (fuera de alcance de esta fase, marcado
  explicitamente arriba):** `RentalBookingWizard.vue` completo (solo se
  confirmo su rol y responsabilidades por nombre/ubicacion) -- **releer antes
  de construir el panel de reserva nuevo**, para no duplicar ni contradecir su
  logica de calculo de costo/disponibilidad.
- **Ningun modelo/campo que el brief asume resulto inventado** -- todos los
  nombres de modelo del brief (`RentalIncludedItem`, `EquipmentLogisticsConfig`,
  `RentalCostRule`, COMODATO, etc.) son reales. La principal desviacion no es
  "esto no existe" sino "esto existe pero en un DTO que el frontend publico
  todavia no consume", y "el panel de reserva en si no existe como componente".
