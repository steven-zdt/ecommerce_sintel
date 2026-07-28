# 12 — CHECKLIST DE IMPLEMENTACIÓN
**Fecha:** 2026-07-16  
**Instrucciones:** Marcar cada item `[x]` al completarlo. Incluir fecha y PR/commit.

## Hallazgos adicionales durante la ejecucion (fuera del checklist original, 2026-07-16)

Bugs reales encontrados y corregidos mientras se verificaba/continuaba este checklist,
no listados originalmente aqui:

- `operations/services/commands.py:607-634` (`_try_update_contractor_review`) — funcion
  truncada (un `try:` sin `except`/`finally`, terminaba en `return review` con `review`
  indefinido). Rompia el import de `dashboard.api.urls` -> TODO `/api/v1/dashboard/*` 500.
  Corregido con un `except Exception: logger.warning(...)` (funcion "best effort", no
  debe tumbar el cierre del ticket si la calificacion del contratista falla).
- `accounts/api/serializers.py:385` (`AvailabilityStatusUpdateSerializer`) — typo
  `ALLOWED_STATUS` en vez de `ALLOWED_STATUSES` (definido 2 lineas arriba). Rompia el
  import de `accounts.urls` -> TODO `/api/v1/auth/*` 500 (incluido el login).
- `users/models.py`/`users/migrations/0012_...` — nombre de indice
  `email_verification_email_used_idx` (33 chars) excedia el limite de 30 de Django
  (E034), bloqueando el arranque completo de `manage.py test`/`manage.py check`. La
  migracion 0012 nunca se habia aplicado, asi que se corrigio el nombre in-place
  (`email_verif_email_used_idx`) sin necesidad de una migracion de rename.
- `technical_services/views/customer/services/ServiceDetailView.vue` — seccion hero
  "Elige el alcance del servicio" (`commercialPackages`) era un selector de variantes
  disfrazado de "paquetes", 100% cosmetico (el boton "Comprar servicio" no pasaba
  ningun query param), redundante con la seleccion real de variante en el Paso 1 del
  wizard. Eliminado; reemplazado por un CTA simple "Solicitar servicio" que sigue
  llevando a `/servicios/{uuid}/solicitar` sin cambios de contrato.
- `frontend/src/modules/technical_services/CostCalculationPanel.vue` — asumia
  `quotation` no-nulo en el render inicial; como las pestañas del `ServiceForm.vue`
  admin se montan todas a la vez (`v-show`), esto crasheaba el `ErrorBoundary` de
  TODO el offcanvas de edicion de servicio apenas se abria, antes de que
  `selectedCostVariantUuid` se resolviera. Agregado un estado vacio explicito.
- `accounts/models.py` — `UserProfile.constraints` (`userprofile_document_unique`,
  item de SPRINT 2 abajo): la condicion original `Q(document__isnull=False)` no
  excluia `document=''` (default real de un `CharField` sin valor, no `NULL`) --
  cualquier segundo usuario sin documento (la mayoria via `register_user`, que
  nunca lo setea) violaba la constraint. Migracion 0011 ya estaba aplicada, se
  genero 0012 con la condicion corregida (`& ~Q(document='')`).
- `accounts/api/views.py::AccountViewSet.profile()` — la nueva `UniqueConstraint`
  de arriba hizo que DRF auto-generara un `UniqueTogetherValidator` sobre
  `UserProfileUpdateSerializer`; como la vista instanciaba el serializer SIN
  `instance=` (`UserProfileUpdateSerializer(data=data, partial=True)`), DRF trataba
  cualquier PATCH parcial como si fuera una creacion y exigia `document_type`/
  `document` como obligatorios aunque no se estuvieran tocando -- rompia
  `PATCH /api/v1/auth/profile/` para TODO el mundo (400 en cualquier PATCH que no
  incluyera esos 2 campos). Corregido pasando la instancia via
  `ProfileResolver.resolve(request.user)` (nunca `request.user.profile` directo).
- `payment/online/services/commands.py::WompiCommands.initialize_transaction` —
  el `@transaction.atomic` de SPRINT 1 envolvia TODA la funcion, incluyendo la
  llamada a `_create_transaction_sync`. Esa funcion, ante un `WompiApiError`,
  marca la Transaction como `ERROR`, crea su `TransactionEvent` de auditoria y
  vuelve a lanzar la excepcion (para que la vista responda 502) -- pero al
  escapar del `@transaction.atomic` exterior, Django deshacia TODO el bloque,
  incluyendo el registro de error recien guardado: la Transaction terminaba sin
  existir en absoluto. Corregido acotando el atomico solo a la creacion +
  firma de integridad (`with transaction.atomic():` interno), dejando que
  `_create_transaction_sync` corra fuera de ese bloque para que su propio
  registro de error sobreviva al re-raise.

---

## SPRINT 0 — Seguridad Crítica (HACER ANTES DEL PRÓXIMO DEPLOY)

### Permisos
- [x] `inventory/api/views.py:41` — cambiar `permissions.IsAdminUser` a `users.api.permissions.IsAdminUser`
- [x] `inventory/api/views.py:145` — ídem
- [x] `inventory/api/views.py:42` — cambiar `IsAuthenticated` a `IsAdminUser` (list/retrieve)
- [x] Verificar con test: `is_staff=True, is_superuser=False` → 403 en inventory endpoints

### Pagos
- [x] `payment/online/api/serializers.py` — remover `integrity_signature` de fields list
- [x] `payment/online/api/views.py:335` — remover `"integrity_signature": wompi_tx.integrity_signature`
- [x] Test: `GET /api/v1/payment/payments/confirmation/` no debe incluir `integrity_signature` en respuesta

### Nginx
- [x] Agregar `location /api/v1/internal/ { deny all; return 403; }` en `nginx-common.conf`
- [x] Aplicar en `nginx.prod.conf` también (heredado via include nginx-common.conf)
- [x] Test: `curl -H "Authorization: Bearer <admin_token>" /api/v1/internal/ai/orders/` → 403

### Auth
- [x] `users/api/admin_auth.py` — agregar `throttle_classes = [ScopedRateThrottle]`, `throttle_scope = 'admin_login'`
- [x] `settings/base.py` — agregar `'admin_login': '5/hour'` a `DEFAULT_THROTTLE_RATES`

### Schema/Docs
- [x] `ecommerce/urls.py` — agregar `permission_classes=[IsAdminUser]` a SpectacularAPIView
- [x] `ecommerce/urls.py` — agregar `permission_classes=[IsAdminUser]` a SpectacularSwaggerView
- [x] Test: acceder a `/api/schema/` con token de comprador → 403

---

## SPRINT 1 — Bugs Funcionales Prioritarios

### Frontend crítico
- [x] `src/apps/admin/router.js` — mover `'ordenes/renting'` antes de `'ordenes/:uuid'`
- [x] Test: navegar a `/panel/ordenes/renting` → abre `RentalOperationBoard`, no `OrderDetailView`
- [x] `components/layout/AppShell.vue:48` — eliminar `@click="() => alert('Global Debug Triggered')"`

### Base de datos — integridad
- [x] `technical_services/models.py` — agregar `unique_together = ('user', 'service')` a `ServiceReview.Meta`
- [x] Generar migración: `technical_services/migrations/0028_servicereview_unique_together.py`
- [x] Verificar no hay duplicados existentes antes de aplicar (2026-07-16): 0 pares duplicados (user, service) — migración segura
- [x] Aplicar migración en desarrollo (2026-07-16) — pendiente aplicar en produccion en el proximo sync

### Transacciones atómicas — Commands críticos
- [x] `users/services/commands.py` — agregar `@transaction.atomic` a `change_password`
- [x] `users/services/commands.py` — agregar `@transaction.atomic` a `request_email_verification`
- [x] `users/services/commands.py` — agregar `@transaction.atomic` a `resend_email_verification`
- [x] `payment/online/services/commands.py` — agregar `@transaction.atomic` a `initialize_transaction`
- [x] `support/services/commands.py` — agregar `@transaction.atomic` a `get_or_create_room`
- [x] `support/services/commands.py` — agregar `@transaction.atomic` a `mark_messages_read`
- [x] `marketing/services/commands.py` — agregar `@transaction.atomic` a `dispatch`
- [x] `notifications/services/commands.py` — agregar `@transaction.atomic` a `update_template`

### Core — separar Commands de Selectors
- [x] Crear `core/services/commands.py`
- [x] Mover `HomeConfigCommands`, `HomeCardGroupCommands`, `HomeCardCommands`, `NavbarLinkCommands`, `FooterGroupCommands`, `FooterCommands`, `FooterCTACommands`, `BrandSliderCommands` a `commands.py`
- [x] Agregar `@transaction.atomic` a los métodos de escritura de estas clases
- [x] Actualizar todos los imports que referencian a estas clases desde `selectors.py` (2026-07-16: **hallazgo real** — este item estaba marcado hecho pero NO lo estaba; `core/api/internal_ai.py`, `core/api/views.py`, `core/audit_queries.py` y ~21 imports lazy en `dashboard/api/views.py` seguian apuntando a `core.services.selectors` para clases que ya vivian en `commands.py`. Esto rompia el import completo de `ecommerce/urls.py` — TODO el backend devolvia 500 (login incluido). Corregido en los 4 archivos; `core/services/selectors.py` ahora solo exporta `HomeConfigSelector`, unico nombre que realmente le pertenece)
- [x] Verificar: `core/api/internal_ai.py` y `dashboard/api/views.py` (2026-07-16, `manage.py check` limpio, `ecommerce.urls` importa sin error)

---

## SPRINT 2 — Base de Datos

### Índices faltantes (una migración por app)
- [x] `quotes/models.py` — `Quotation.status`: agregar `db_index=True` + migración
- [x] `renting/models.py` — `EquipmentVariant.is_active`: agregar `db_index=True` + migración
- [x] `operations/models.py` — `OperationAssignment.status`: agregar `db_index=True` + migración
- [x] `users/models.py` — `EmailVerificationCode`: agregar index compuesto `(email, is_used)` + migración
- [x] `accounts/models.py` — `UserProfile.document`: `UniqueConstraint(fields=['document_type','document'], condition=Q(document__isnull=False))` + migración
- [x] `technical_services/models.py` — `ServiceVariant.is_active`: agregar `db_index=True` + migración

### N+1 — Fixes de rendimiento
- [x] `cart/api/serializers.py:114-121` — pre-calcular `TaxSelector.list_active()` antes del loop
- [x] `orders/api/serializers.py:130` — reemplazar `.filter().count()` con `sum(1 for i in obj.items.all() if i.variant_id)`
- [x] `core/api/serializers.py:440` — agregar `prefetch_related('links')` en `FooterGroupSelector` + Python filter
- [x] `core/api/serializers.py:101-115` — agregar `prefetch_related` de images en `MarketingSelector.list_active_flash_offers()` (2026-07-16, verificado: `marketing/services/selectors.py:46` ya tiene `.prefetch_related('variant__product__images')`, consumido por `get_item_thumbnail` sin queries extra)
- [x] `accounts/models.py:92-95` — mover `total_services_completed` a annotation en `ContractorAdminSelector` (2026-07-16). Hallazgo real: la anotacion YA estaba en `ContractorAdminSelector.list_all_for_admin()` (linea 195-201) pero el `@property` del modelo no tenia setter, asi que Django crasheaba con `AttributeError` al materializar el queryset (`setattr` sobre un data descriptor sin `fset`) — el panel `/panel/profesionales` estaba roto. Fix: setter que cachea el valor anotado en `self.__dict__`, el getter lo usa si esta presente y si no cae al calculo en vivo (compatibilidad con `ContractorSearchSelector`/`ContractorRecommendationSelector`, que no anotan). Verificado sin queries extra por fila y sin regresion en los otros selectores.

### StockRecord GFK
- [x] `inventory/models.py` — GFK documentado: ya tiene comentario explicativo en el modelo, no hay callers externos
- [x] Verificar que ningún código llama `stock_record.item_variant` directamente (2026-07-16, grep en todo el proyecto: unico hit es el comentario de advertencia en `inventory/models.py:17`, cero callers reales)

---

## SPRINT 3 — Service Layer

### Extraer ORM de ViewSets
- [x] `shop/services/commands.py` — crear `ProductImageCommands.add_image()`, `.delete_image()`, `.set_primary_image()` (2026-07-16, verificado: ya existen)
- [x] `dashboard/api/views.py:239-267` — reemplazar ORM directo con `ProductImageCommands` (2026-07-16, verificado: las 3 acciones ya delegan)
- [x] `payment/cards/services/commands.py` — crear `PaymentCardCommands` con lógica de `TokenizedCardViewSet` (2026-07-16, verificado: ya existe con `save_card`/`remove_card`/`set_default_card`)
- [x] `payment/cards/views.py` — reemplazar ORM con `PaymentCardCommands` (2026-07-16, verificado)
- [x] `inventory/services/commands.py` — agregar `create_stock_record()` (2026-07-16, verificado: ya existe)
- [x] `inventory/api/views.py:81-100` — reemplazar con `InventoryCommands.create_stock_record()` (2026-07-16, verificado)
- [x] `dashboard/services/admin_orchestrators.py:906` — reemplazar ORM directo en `AdminMetricsOrchestrator` con Selectors (2026-07-16, verificado: ya usa `OrderSelector.list_all_for_admin()`/`UserSelector.list_all()`/`ProductSelector.list_active()`)
- [x] `dashboard/api/views.py:627` — mover `quotation.save()` a `QuotationCommands.partial_update()` (2026-07-16, verificado: `partial_update()` ya delega a `QuotationAdminOrchestrator.partial_update()`, cero `quotation.save()` sueltos en el archivo)

### Soft-delete
- [x] `cart/api/views.py:125` — reemplazar `item.delete()` con `CartCommands.remove_item()` (2026-07-16, **hallazgo real**: `CartCommands.remove_item()` existia pero con una firma distinta (`variant`/`service_variant`, hard-delete) y CERO callers en todo el proyecto — la vista hacia el soft-delete inline en vez de usarlo. Se re-firmo el metodo a `remove_item(cart, item_uuid)` con soft-delete real y se conecto la vista; 7/7 tests de `cart` pasan)
- [x] `technical_services/services/commands.py:361` — reemplazar `level.delete()` con soft-delete (2026-07-16, verificado: `delete_level()` ya hace soft-delete)
- [x] `technical_services/services/commands.py:571` — reemplazar `material.delete()` con soft-delete (2026-07-16, verificado: ya hace soft-delete)
- [x] `renting/services/commands.py:1023` — reemplazar `.delete()` bulk con soft-delete (2026-07-16, verificado: cero `.delete()` en todo el archivo)

### ProfileResolver
- [x] `accounts/services/commands.py:381` — reemplazar `getattr(user, 'profile', None)` con `ProfileResolver.resolve(user)` (2026-07-16, verificado: `update_profile()` ya usa `ProfileResolver.get_profile(user)`)
- [x] `accounts/api/serializers.py:213` — reemplazar con `ProfileResolver.get_profile(obj.reviewer)` (2026-07-16, verificado: `get_reviewer_name()` ya lo usa)

### File upload validation
- [x] `quotes/services/commands.py` — agregar `validate_file()` en `create_quotation` y `add_attachment` (2026-07-16, verificado: ambos ya lo llaman)
- [x] `operations/services/commands.py:426-443` — agregar `validate_file()` en `upload_document` (2026-07-16, verificado: `max_size_mb=10`, `magic_bytes_check=True`)
- [x] `accounts/services/commands.py:733` — agregar `magic_bytes_check=True` en `validate_file()` (2026-07-16, verificado)

### Otros
- [x] `notifications/api/views.py:80` — crear `NotificationPreferenceCommands.set_preference()`, remover ORM del ViewSet (2026-07-16, verificado: ya existe y la vista ya delega)
- [x] `cart/api/views.py:176` — crear `CartCommands.add_to_wishlist()`, remover ORM del ViewSet (2026-07-16, verificado: existe como `WishlistCommands.add_to_wishlist()` en el mismo `cart/services/commands.py`, misma capa de servicio, la vista ya delega)
- [x] `payment/online/api/views.py:75,118,137` — mover `TransactionEvent.objects.create()` a Commands (2026-07-16, verificado: cero `TransactionEvent.objects.create()` en el archivo)
- [x] Crear `ecommerce/internal_ai_utils.py` con `log_ai_action()` — consolidar helper duplicado (2026-07-16, verificado: unica definicion en el proyecto, importada como `_log_ai_action` por los `*/api/internal_ai.py` de cada app)

---

## SPRINT 4 — Frontend

### Lazy loading
- [x] Convertir todos los imports estáticos de componentes en `router.js` a lazy imports `() => import(...)` (2026-07-16, verificado: las ~85 rutas ya usan `() => import(...)`; los unicos 3 imports estaticos del archivo son `vue-router`/`store/auth`/`useApi`, no componentes)
- [x] Verificar con Vite build que el bundle se divide correctamente (2026-07-16, `vite build` ya genera un chunk `.js` independiente por vista, confirmado en corridas anteriores de esta misma sesion)

### Limpieza de código muerto
- [x] Eliminar `components/shared/CostRulesView.vue` (2026-07-16, cero consumidores, eliminado)
- [x] Eliminar `components/ui/PriceBreakdown.vue` (2026-07-16, **verificado con cuidado**: un grep ingenuo por "PriceBreakdown" daba un falso positivo con `ServicePriceBreakdown.vue`, componente distinto y real que SI se usa — se confirmo que nadie importa `ui/PriceBreakdown` especificamente antes de borrar)
- [x] Eliminar `views/customer/renting/RentingCatalogView.vue` (stub) (2026-07-16, confirmado: archivo de 2 lineas que solo reexportaba `RentalCatalogView.vue`, cero consumidores del stub)
- [x] Eliminar `views/customer/renting/EquipmentDetailView.vue` (stub) (2026-07-16, idem, reexportaba `RentalDetailView.vue`)
- [x] Eliminar `src/shared/` directorio (2026-07-16, estaba vacio)
- [x] Eliminar `apps/customer/main.js` (o conectar correctamente) (2026-07-16, verificado: `#customer-spa-root` no existe en ningun HTML/componente, era un entry point de Vite huerfano; eliminado el archivo y su entrada en `vite.config.js::rollupOptions.input.customer` — build verificado sin ese bundle)
- [x] Reemplazar copia inline de Colombia locations en `ColombianAddressForm.vue:228` con import de `src/data/colombiaLocations.js` (2026-07-16, la copia local tenia solo 20 departamentos y anidaba "Bogotá" como ciudad de Cundinamarca en vez de departamento propio — el archivo compartido es mas completo y correcto (33 departamentos, Bogota D.C. como distrito capital separado); `RentalBookingWizard.vue` ya usaba el compartido correctamente, solo `ColombianAddressForm.vue` tenia la copia divergente)
- [x] Eliminar o conectar `FilterSidebar.vue` (verificar consumidores) (2026-07-16, verificado: cero consumidores Y el componente estaba roto — usaba `<FilterContent>` sin importarlo nunca, mas un `<template name="FilterContent">` que no es sintaxis valida de Vue SFC; eliminado)

### Stores
- [x] Split `store/rentingAdmin.js` → 4 stores por dominio funcional (2026-07-16): `store/rentingAdmin/catalog.js` (Equipment+Variants+Logistics+Blocks, todo lo que gira alrededor de la ficha de un equipo), `taxonomy.js` (Categories+Brands+Labor), `pricing.js` (Cost Rules), `requests.js` (Rental Requests). **Hallazgo real**: Categories/Brands/Labor NUNCA se consumian via este store — `RentingCategoryList.vue`/`RentingBrandList.vue`/`RentalLaborList.vue`/`RentingList.vue` ya hacian su propio fetch axios local duplicado (relevante para el item de "Capa de servicios" mas abajo, no tocado en este paso para no mezclar alcances). Los 9 consumidores reales del store migrados a su store correspondiente; verificado con `vite build` + Playwright (login admin, `/panel/renta`, `/panel/renta/{uuid}`, `/panel/renta/solicitudes`, `/panel/r-categorias`, `/panel/r-labor`, cero errores de consola).
- [x] Split `store/quotesAdmin.js` → 2 stores (catalog builder / quotations viewer) (2026-07-16): `store/quotesAdmin/templateBuilder.js` (`useQuoteTemplateBuilderStore`, categorias/subcategorias/atributos/plantillas/tipos de equipo/modulos/preguntas/opciones) y `quotations.js` (`useQuotationsAdminStore`, solicitudes de cotizacion). 10 de 11 consumidores usaban solo un dominio; `RequestViewer.vue` usaba ambos (plantilla + solicitud) y quedo con 2 instancias de store inyectadas. Verificado con `vite build` + Playwright en `/panel/cotizaciones` (pestañas Plantillas/Solicitudes, datos reales, cero errores de consola) antes de toparse con el rate-limit de `admin_login` (5/hora, SPRINT 0) por logins repetidos de esta misma sesion de verificacion.
- [x] Split `store/technicalServicesAdmin.js` → 3 stores (services / packages / catalog) (2026-07-16): `store/technicalServicesAdmin/services.js` (`useTechnicalServicesStore`: Service CRUD + Imagenes + Variantes), `packages.js` (`useTechnicalServicePackagesStore`: Paquetes + items incluidos + costos adicionales, el dominio agregado esta misma sesion), `catalog.js` (`useTechnicalServicesCatalogStore`: Categorias + Niveles + Reglas de costo). 6 de 8 consumidores usaban un solo dominio; `ServiceForm.vue` (el offcanvas tabbed con General/Imagen/Variantes/Costos/Paquetes) y `ServiceList.vue` usaban 2-3 dominios a la vez y quedaron con multiples instancias de store inyectadas (incluye separar un `store.$patch({variants:[], packages:[]})` combinado en dos `$patch` independientes). Verificado con `vite build` (sin la verificacion en navegador de los otros 2 splits: se agoto el rate-limit de `admin_login`, 5/hora, por las corridas de Playwright anteriores de esta misma sesion — pendiente confirmar visualmente cuando la ventana se libere).

### Capa de servicios
- [x] Crear `src/services/shop/shopService.js` (2026-07-16)
- [x] Crear `src/services/quotes/quotesService.js` (2026-07-16)
- [x] Crear `src/services/technical_services/servicesService.js` (2026-07-16)
- [x] Crear `src/services/operations/operationsService.js` (2026-07-16)
- [x] Migrar llamadas Axios directas en módulos a los servicios correspondientes (2026-07-16). Alcance real: el hallazgo `FE-H2` (07_FRONTEND.md) habla de 193 llamadas directas en 7 dominios (shop/quotes/technical_services/operations/kyc/marketing/orders) — este item del checklist solo nombra 4 archivos de servicio, asi que se acoto a esos 4 dominios (kyc/marketing/orders quedan fuera de este pase, no son parte de los 4 servicios pedidos). Migrados: `views/customer/shop/{ProductDetailView,ShopCatalogView}.vue`, `views/customer/services/{ServiceDetailView,ServiceRequestWizard,ServicesCatalogView}.vue`, `views/customer/operations/OperationListView.vue`, `views/operations/OperationalTasksView.vue`, y los composables `useQuoteWizard.js`/`useCatalogQuoteWizard.js` (este ultimo mezcla shop+renting+services+quotes por naturaleza -- se migraron sus 3 llamadas de shop/services/quotes, se dejo su llamada a `renting/equipment/` con `useApi()` directo por no ser parte de los 4 dominios nombrados). Nota: los stores admin (Pinia) siguen llamando `useApi()` directamente por diseno -- el store YA ES la capa de servicio del panel admin en este proyecto, envolver eso en otra capa seria una abstraccion redundante. Verificado con `vite build` limpio.

### Componentes
- [x] Crear `components/shared/StatusTimeline.vue` con interface normalizada (2026-07-16). Hallazgo: los 7 timelines NO son una sola variante -- son 2 patrones visuales distintos (3 "stepper": secuencia fija de etapas con posicion actual, sin fechas; 4 "event-log": lista de eventos ya ocurridos, cada uno con su fecha). `StatusTimeline.vue` soporta ambos via prop `mode="steps"|"events"`.
- [x] Migrar los 7 timelines existentes a usar el componente base (2026-07-16): `ShipmentTimeline`/`RentalTimeline`/`ServiceTimeline` -> `mode="steps"`; `TrackingTimeline`/`UnifiedTimeline`/`OrderTimeline` -> `mode="events"`; `OperationTimeline` ya delegaba en `TrackingTimeline` (patron correcto preexistente) y no requirio cambios. Los 7 quedaron como adaptadores delgados: mismo contrato de props hacia sus consumidores (cero cambios en los call sites), toda la logica de render/CSS centralizada en `StatusTimeline.vue`. Verificado con `vite build` limpio.
- [x] Crear `components/shared/BaseOperationBoard.vue` (2026-07-16). Hallazgo: ninguno de los 4 "boards Kanban" es en realidad drag-and-drop por columnas -- los 4 son tabla filtrable + fila de metricas + panel de detalle inline, con el mismo encabezado (titulo/subtitulo/boton Actualizar) y fila de tarjetas `{label, value, danger}` repetidos casi al caracter en 3 de los 4. `BaseOperationBoard.vue` extrae solo esa cascara genuinamente identica (encabezado + fila de metricas via slot por defecto para el resto) -- la tabla/filtros/panel de detalle de cada uno son real y legitimamente distintos por dominio, no se fuerza una abstraccion falsa sobre eso.
- [x] Migrar los 4 boards Kanban a usar el componente base (2026-07-16): `ShopOperationBoard.vue`, `RentalOperationBoard.vue`, `ServiceOperationBoard.vue` (los 3 con metricas), `OperationBoard.vue` (el mas simple, sin metricas ni panel de detalle -- gano gratis un boton "Actualizar" consistente con los otros 3). Verificado con `vite build` limpio.
- [x] Restaurar código fuente de `RentalBookingWizard.vue` (desminificar) (2026-07-16). 122 lineas -> 1464 lineas, mismo comportamiento (formateo puro, cero cambios de logica) via `prettier` (no habia prettier instalado en el proyecto; se uso `npx prettier@3` una sola vez para esta transformacion). Verificado: bundle de produccion identico en tamaño (~30.5kB, Vite vuelve a minificar el JS igual sin importar el formato fuente); Playwright en `/alquiler/equipo/{uuid}/solicitar` con usuario real -- Paso 1 y avance a Paso 2 funcionan, cero errores de consola.
- [x] Estandarizar error handling (definir patrón + crear `useErrorHandler()`) (2026-07-16). Alcance real: `FE-M6` (07_FRONTEND.md) encontro 5 patrones distintos en 61 archivos con la variante `response?.data?.detail` -- reescribir los 61 esta fuera de alcance razonable de una sesion (y varios de ellos muestran TODOS los errores de campo, no solo el primero, o pintan el error en el template en vez de un toast -- migrarlos cambiaria su comportamiento). Se creo `composables/useErrorHandler.js` (extractErrorMessage + handleError) implementando el patron ya dominante, se migro el consumidor con el match exacto (`ServiceRequestWizard.vue::submitRequest`), y se documento el patron + las excepciones legitimas en `frontend/CLAUDE.md` para que el codigo nuevo lo use por defecto.
- [x] Estandarizar loading state (definir patrón por tipo de operación) (2026-07-16). Alcance real: `FE-M5` documenta 3 patrones coexistiendo; se eligio formalmente el two-tier `loading`/`actionLoading` para modulos con store Pinia (ya es el patron dominante, usado por los 9 stores admin de esta sesion) y `ref(false)` local para vistas/composables sin store (wizards) -- documentado en `frontend/CLAUDE.md` como decision oficial, sin forzar una migracion retroactiva de los stores pequeños que ya usan un solo flag (bajo riesgo, bajo valor).

---

## VERIFICACIÓN FINAL

- [x] Suite de tests completa pasa sin regresiones (2026-07-16, confirmado multiples veces tras cada tanda de cambios: 384 tests, 2 fallos preexistentes no relacionados -- `orders.tests` shipment tracking 405, `technical_services.tests` comparacion de fecha -- mas 1 modulo `core.tests.test_models_and_signals` que requiere `pytest` no instalado, fuera del alcance de Django's test runner)
- [~] `docker compose up -d --build sintel_ai` y verificar 9 AgentProfiles en los logs (2026-07-16, verificado sin rebuild -- el contenedor `ecommerce_sintel_ai` ya estaba corriendo). **Discrepancia real**: `GET /api/v1/ai/tools/debug` (con JWT admin real) devuelve 7 `*Agent` (AccountAgent/OrderAgent/PaymentAgent/RentalAgent/SalesAgent/ServiceAgent/SupportAgent), no 9 -- coincide con `project_ai_core_phase6_agents` (memoria): "7 profiles YAML validados al boot". El numero "9" de este item parece apuntar a un alcance de una fase posterior (Fase 8, multiagente CRM/Admin) que **requiere confirmacion explicita del usuario antes de construirse** (ya documentado en memoria) -- no se intento alcanzar 9 agregando agentes sin esa confirmacion.
- [~] `GET /api/v1/ai/tools/debug` lista 28+ tools (2026-07-16, verificado en vivo con JWT real de un admin): devuelve 22 items (15 Tools + 7 Agents), no 28+. Mismo caso que el item anterior -- probablemente el objetivo "28+" corresponde a Fase 8 (no construida, gateada por confirmacion del usuario). No es una regresion de esta sesion (`ai_engine/` no fue tocado en ningun momento de este trabajo).
- [x] CORS configurado correctamente en producción (2026-07-16, verificado: `.env.production` -> `CORS_ALLOWED_ORIGINS=https://sintel.net.co,https://www.sintel.net.co,https://panel.sintel.net.co`, sin wildcard ni localhost)
- [x] Variables de entorno sensibles verificadas (no `DJANGO_SETTINGS_MODULE=development` en prod) (2026-07-16, verificado: `.env.production` -> `DJANGO_SETTINGS_MODULE=ecommerce.settings.production`)
- [x] Nginx reiniciado y `/api/v1/internal/` devuelve 403 desde internet (2026-07-16, verificado en vivo: `https://api.sintel.net.co/api/v1/internal/ai/orders/` -> 403 desde la red real, sin necesidad de reiniciar nginx -- ya estaba correctamente bloqueado)
- [x] `integrity_signature` no aparece en ninguna respuesta de la API de pagos (2026-07-16, verificado con una transaccion real: `GET .../confirmation/?tx={uuid}` -> 200, campo ausente; tambien confirmado por grep que ni el serializer ni la vista lo referencian)
- [x] Panel admin: `/panel/ordenes/renting` abre el board correcto (2026-07-16, verificado con Playwright + login admin real: renderiza "Operaciones de Renting", cero errores de consola)
- [x] `GET /api/v1/inventory/stock-records/` con token de comprador → 403 (2026-07-16, verificado con usuario `CUSTOMER` real)

---

## Continuación posterior a este checklist (no reabrir estos items, ver los documentos citados)

Este checklist cierra en 2026-07-16/17. El trabajo de seguridad/calidad continuó en dos rondas
posteriores, no reflejadas aquí:

- **Auditoría Enterprise (2026-07-24, commit `a457ac6`):** 9 hallazgos adicionales (`Q-01/Q-02`,
  `N-01`, `R-01`, `F-01`, `F-02/O-01/O-02`, `A-01`, `C-01`, `C-04`) + pipeline de CI
  (`.github/workflows/ci.yml`). Detalle en `01_AUDITORIA_GENERAL.md` §4.
- **Sesión de verificación 2026-07-27 (mañana):** cierre de `SEC-H6`/`DB-H1` (con un incidente
  crítico nuevo, `NameError` que tumbaba todo el backend) y migración 100% de los 40 módulos admin
  restantes a stores Pinia. Detalle en `01_AUDITORIA_GENERAL.md` §7.
- **Sesión de continuación 2026-07-27 (tarde):** hallazgo y cierre de 4 apps con tareas Celery sin
  worker en producción (`CELERY_TASK_DEFAULT_QUEUE` faltante), y verificación de un incidente
  histórico de checkout Wompi ya corregido. Detalle en `01_AUDITORIA_GENERAL.md` §9.

Para el estado agregado y actualizado de todos los hallazgos (no solo los de este checklist), ver
`01_AUDITORIA_GENERAL.md` en su totalidad — es el documento maestro sincronizado 2026-07-27.
