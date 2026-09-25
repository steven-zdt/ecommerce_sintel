# ARQUITECTURA COMPLETA — app `dashboard` (BFF administrativo)

> **Creado:** 2026-07-03 — este documento no existia antes (`dashboard` era la unica app de
> negocio sin `.AGENT/docs/ARQUITECTURA_COMPLETA_*.md` propio, referenciada como "Pendiente" en
> `IMPLEMENTATION_SUMMARY.md`). Escrito verificando `dashboard/api/views.py`,
> `dashboard/api/urls.py` y `dashboard/services/admin_orchestrators.py` linea por linea.
>
> **Actualizado:** 2026-07-05 — nueva clave `marketplace` en `AdminMetricsOrchestrator.get_metrics()`
> (Marketplace de Contratistas + Asignación de Técnicos).

---

## [CRITICAL] Responsabilidad de esta app

`dashboard` es el **unico Backend for Frontend (BFF) del panel administrativo**. El SPA de Vue
en `/panel/*` consume **exclusivamente** `/api/v1/dashboard/*` — nunca llama directamente a
`/api/v1/shop/`, `/api/v1/renting/`, etc. para escritura.

**Regla SSoT:** `dashboard` no contiene logica de negocio propia ni toca el ORM directamente.
Cada `ViewSet` delega a un `Orchestrator` en `dashboard/services/admin_orchestrators.py`, que a
su vez delega a los `Commands`/`Selectors` reales de la app dueña del dominio (`shop`, `renting`,
`orders`, `quotes`, `technical_services`, `marketing`, `core`, `support`, `operations`).

```
Vue SPA (/panel/*)
    |
    +-- /api/v1/dashboard/*  ->  dashboard/api/views.py  (34 ViewSets + 1 APIView)
                                        |
                                dashboard/services/admin_orchestrators.py  (~770 lineas)
                                        |
                        Commands + Selectors de cada app dueña del dominio
```

`dashboard/models.py` esta practicamente vacio — esta app no es dueña de ningun modelo de
negocio, solo orquesta.

---

## Permisos — uniformes en toda la app

```python
ADMIN_PERMISSIONS = [permissions.IsAuthenticated, IsAdminUser]  # IsAdminUser de users.api.permissions
```

Verificado: **36 de 37 clases** en `dashboard/api/views.py` declaran
`permission_classes = ADMIN_PERMISSIONS` explicitamente (la que falta es la clase de paginacion,
que no es un ViewSet). A diferencia de otros gaps encontrados en `renting`/`marketing` (ver
`IMPLEMENTATION_SUMMARY.md`), `dashboard` **no tiene ViewSets sin permiso declarado** — es el
patron correcto a seguir en el resto del proyecto.

---

## Endpoints reales (verificados contra `dashboard/api/urls.py`, 2026-07-03)

Todos bajo `/api/v1/dashboard/`, todos `IsAuthenticated + IsAdminUser` salvo que se indique lo
contrario.

### Metricas y usuarios

| Ruta | ViewSet/View |
|---|---|
| `metrics/` | `AdminMetricsView` (APIView) — ventas, ordenes, clientes, productos, **marketplace** (NUEVO, ver abajo) |

**Usuarios NO se administran aca** — `AdminUserViewSet`/`UserAdminOrchestrator` existieron en este
BFF y se eliminaron (2026-07-05): duplicaban `users.api.views.UserViewSet` (`/api/v1/users/`) sin
que el frontend los llamara nunca, y ya habian divergido (bug real: `update_user` ignoraba
`is_active`/`is_verified`). El panel `/panel/usuarios` consume `/api/v1/users/` directamente. Ver
`users/.AGENT/docs/ARQUITECTURA_COMPLETA_USER.md` para paginacion/filtros/audit log/reset de
contrasena/verificacion/grupos.

### Shop

| Ruta | ViewSet |
|---|---|
| `products/` (+ `variants/`, `variants/create`, `variants/<pk>`) | `AdminProductViewSet` |
| `categories/` | `AdminCategoryViewSet` — multipart (image) |
| `brands/` | `AdminBrandViewSet` — multipart (logo) |
| `taxes/` | `AdminTaxViewSet` |
| `shop-cost-rules/` | `AdminShopCostRuleViewSet` — motor de precios descentralizado |

### Orders

| Ruta | ViewSet |
|---|---|
| `orders/` | `AdminOrderViewSet` |

### Pagos (`AdminPaymentViewSet`, agregado ADR-001 Fase 7 2026-07-13 — faltaba en este documento hasta 2026-07-22)

| Ruta | Accion |
|---|---|
| `payment-transactions/` | Lectura de transacciones Wompi/Nequi/COD (vista centralizada) |
| `payment-transactions/{uuid}/resync/` | POST — fuerza `_sync_wompi_status()` bajo demanda (409 si la transaccion no tiene `wompi_id`) |
| `payment-transactions/{uuid}/events/` | GET — historial `TransactionEvent` de una transaccion |
| `payment-transactions/feature-flags/` | GET/PATCH — `PaymentFeatureFlags.card_api_flow_enabled`/`widget_flow_enabled` (2do flag agregado 2026-07-22) en un solo PATCH |

Documentado con detalle completo (incluye el porque de cada decision) en
`payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` §10.5/10.6 — este documento solo lista la
ruta, siguiendo el mismo patron que Operations (nota abajo).

### Renting

| Ruta | ViewSet |
|---|---|
| `equipment/` (+ `variants/`, `variants/create`, `variants/<pk>`) | `AdminEquipmentViewSet` |
| `renting-categories/` | `AdminRentingCategoryViewSet` |
| `renting-brands/` | `AdminRentingBrandViewSet` |
| `rental-labor/` | `AdminRentalLaborViewSet` |
| `rental-cost-rules/` | `AdminRentalCostRuleViewSet` |

### Quotes — catalogo/custom + Constructor de Cuestionarios Tecnicos

| Ruta | ViewSet |
|---|---|
| `quotations/` | `AdminQuotationViewSet` |
| `quote-template-categories/` | `AdminQuoteTemplateCategoryViewSet` |
| `quote-template-subcategories/` | `AdminQuoteTemplateSubcategoryViewSet` |
| `quote-templates/` | `AdminQuoteTemplateViewSet` |
| `quote-template-attributes/` | `AdminQuoteTemplateAttributeViewSet` |
| `quote-equipment-types/` | `AdminQuoteEquipmentTypeViewSet` |
| `quote-template-modules/` | `AdminQuoteTemplateModuleViewSet` (EQUIPMENT/MATERIALS/LABOR) |
| `quote-questions/` | `AdminQuoteQuestionViewSet` |
| `quote-question-options/` | `AdminQuoteQuestionOptionViewSet` |

### Technical Services

| Ruta | ViewSet |
|---|---|
| `services/` | `AdminTechnicalServiceViewSet` |
| `service-categories/` | `AdminServiceCategoryViewSet` |
| `service-levels/` | `AdminServiceLevelViewSet` |
| `service-variants/` | `AdminServiceVariantViewSet` |
| `service-cost-rules/` | `AdminServiceCostRuleViewSet` |
| `technical-services/requests/` (2026-08-14) | `AdminServiceRequestViewSet` -- fachada admin sobre `orders.Order`+`ServiceOperation`, sin ownership propio. `list`/`retrieve` + `POST {uuid}/plan\|assign\|schedule\|notify\|cancel/`. Sin `/approve/` a proposito -- ver ARQUITECTURA_COMPLETA_SERVICES.md §22 |

### Marketing

| Ruta | ViewSet |
|---|---|
| `marketing/` | `AdminMarketingViewSet` |

### Core (contenido publico de la landing)

| Ruta | ViewSet |
|---|---|
| `home-config/` | `AdminHomeConfigViewSet` |
| `home-cards/` | `AdminHomeCardViewSet` |
| `home-card-groups/` | `AdminHomeCardGroupViewSet` |
| `footer/` | `AdminFooterViewSet` |
| `site-brand/` | `AdminSiteBrandViewSet` |
| `navbar/` | `AdminNavbarViewSet` |
| `footer-cta/` | `AdminFooterCTAViewSet` |
| `about-us/` (+ `<uuid>/`, `config/`, `config/update/`, `reorder/`) | `AdminAboutUsViewSet` — ver `core/.AGENT/docs/ARQUITECTURA_COMPLETA_CORE.md` *(agregado a este doc 2026-07-31, feature de 2026-07-19)* |

### SEO (metaetiquetas del `<head>`) *(nuevo 2026-07-31)*

| Ruta | ViewSet |
|---|---|
| `seo/meta-tags/` (+ `<uuid>/`, `<uuid>/duplicate/`, `<uuid>/toggle/`, `<uuid>/preview/`, `<uuid>/history/`, `reorder/`, `export/`, `import/`) | `AdminSeoMetaTagViewSet` — logica en `seo.services.selectors.MetaTagSelector` / `seo.services.commands.MetaTagCommands`, ver `seo/.AGENT/docs/ARQUITECTURA_COMPLETA_SEO.md` |
| `seo/verification-files/` (+ `<uuid>/`, `<uuid>/toggle/`) | `AdminSiteVerificationFileViewSet` — CRUD de `SiteVerificationFile` (archivos servidos en la raiz del dominio via `seo/views.py`, fuera de este BFF) |

### Support

| Ruta | ViewSet |
|---|---|
| `support/chats/` (+ `<uuid>/close/`, `<uuid>/assign/`, `<uuid>/ticket-status/`, `<uuid>/ticket-priority/` [2026-09-15]) | `AdminSupportChatViewSet` — ver `support/.AGENT/docs/ARQUITECTURA_COMPLETA_SUPPORT.md` |

### Operations (ViewSets viven en `operations`, registrados aqui)

| Ruta | ViewSet |
|---|---|
| `operations/` | `AdminOperationViewSet` (importado de `operations.api.views`) |
| `dispatchers/` | `AdminDispatcherViewSet` (importado de `operations.api.views`) |

> **Nota de patron:** estos dos son la unica excepcion donde el `ViewSet` no vive fisicamente en
> `dashboard/api/views.py` sino en la app dueña del dominio (`operations`) y solo se registra en
> el router de `dashboard`. Mantiene la regla SSoT (la logica de `operations` vive en
> `operations`) pero es una variante estructural del patron "todo vive en dashboard/api/views.py"
> que domina el resto del archivo — tenerlo en cuenta al buscar un ViewSet admin que no aparezca
> en `dashboard/api/views.py`.

### [ELIMINADO] Inventario

**No existe `inventory/` bajo `/api/v1/dashboard/`.** Hubo un `InventoryAdminOrchestrator` +
rutas `/api/v1/dashboard/inventory/...` en versiones anteriores del proyecto — se eliminaron por
completo (sin referencias colgantes) en favor de `/api/v1/inventory/stock-records/...`
(`inventory/api/views.py`, app dueña del dominio). Verificado 2026-07-03: `GET/POST
/api/v1/dashboard/inventory/...` devuelve 404. **No reintroducir esta ruta.**

---

## Orchestrators (`dashboard/services/admin_orchestrators.py`, ~770 lineas)

Cada `Orchestrator` es una clase con solo `@staticmethod`, sin estado, que envuelve llamadas a
`Commands`/`Selectors` de la app dueña, normalmente agregando `@transaction.atomic` en las
operaciones de escritura.

| Orchestrator | Domain real (app dueña) |
|---|---|
| `AdminMetricsOrchestrator` | Metricas consolidadas (`orders`, `users`, `shop`, `accounts`, `technical_services` vía `marketplace`) |
| `ShopAdminOrchestrator` | `ProductSelector/Commands`, `CategorySelector/Commands`, `BrandSelector/Commands`, `TaxSelector/Commands` |
| `ServiceAdminOrchestrator` | `ServiceSelector/Commands`, `ServiceCategoryCommands` |
| `ServiceAdminRequestSelector`/`ServiceAdminRequestOrchestrator` (2026-08-14) | **Fachada cross-domain** -- combina `orders.Order` + `technical_services.OrderServiceDetail`/`ServiceOperation`, sin ownership propio. Escritura delega siempre a `ServiceOperationCommands` (`technical_services`), nunca `Model.objects.update()` directo. Ver `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` §22 para el detalle completo (incluye por que NO hay `approve_request()`) |
| `RentingAdminOrchestrator` | `RentingSelector`, `EquipmentCommands`, `EquipmentVariantCommands`, `RentingBrandCommands`, `RentingCategoryCommands` |
| `QuotationAdminOrchestrator` | `QuotationSelector`, `QuotationCommands` |
| `QuoteTemplateAdminOrchestrator` | Comandos del Constructor de Cuestionarios (`QuoteTemplate`, `QuoteQuestion`, etc.) |
| `OrderAdminOrchestrator` | `OrderSelector` |
| `MarketingAdminOrchestrator` | `MarketingSelector` |
| `SupportAdminOrchestrator` | `ChatSelector`/`ChatCommands` (app `support`) |
| `PaymentAdminOrchestrator` | `PaymentAdminSelector` (`payment/services/selectors.py`), `PaymentFeatureFlags.set_card_api_flow_enabled()`/`set_widget_flow_enabled()` — faltaba en esta tabla hasta 2026-07-22, ver `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_PAYMENT.md` §10.5/10.6 |

**Patron de escritura tipico** (ejemplo `ShopAdminOrchestrator.create_product`):
```python
@staticmethod
@transaction.atomic
def create_product(vendor, data):
    return ProductCommands.create_product(vendor=vendor, **data)
```
El Orchestrator no valida datos (eso ya lo hizo el Serializer en la ViewSet) ni contiene reglas
de negocio — solo desempaqueta `validated_data` y llama al Command real con la firma que espera.

**Riesgo conocido de este patron (no confirmado como bug real, solo como observacion):** como
los Orchestrators pasan `**data` directo a los Commands, si un serializer de `dashboard/api/
serializers.py` llega a declarar un campo que el Command real no acepta como parametro, la
request explota con `TypeError` (500) en vez de un 400 limpio del serializer. Ya paso una vez
de forma evitada (ver `IMPLEMENTATION_SUMMARY.md`, caso del campo `sku` en
`ProductVariantInputSerializer` que casi se reintroduce incorrectamente el 2026-07-03) — al
tocar cualquier serializer de `dashboard`, verificar siempre la firma real del Command que lo
consume antes de agregar/quitar campos.

---

## `AdminMetricsOrchestrator.get_metrics()` — clave `marketplace` (NUEVO 2026-07-05)

`GET /api/v1/dashboard/metrics/` ahora incluye, junto a `total_sales`/`orders_count`/
`customers_count`/`products_count`/`recent_orders`, una clave nueva `marketplace` con las métricas
del Marketplace de Contratistas + Asignación de Técnicos, calculada por el método privado
`AdminMetricsOrchestrator._get_marketplace_metrics()`:

```json
{
  "marketplace": {
    "professionals_count": 0,
    "professionals_by_type": {"TECHNICIAN": 0, "PROFESSIONAL": 0, "SPECIALIST": 0, "CONTRACTOR": 0},
    "technicians_available": 0,
    "technicians_busy": 0,
    "average_rating": 0.0,
    "service_status_counts": {"pending": 0, "assigned": 0, "in_progress": 0, "completed": 0, "cancelled": 0},
    "top_categories": [{"name": "...", "count": 0}],
    "top_professionals": [{"uuid": "...", "first_name": "...", "last_name": "...", "user__email": "...", "completed_count": 0}]
  }
}
```

**De donde sale cada campo (sin duplicar lógica):**
- `professionals_count`, `professionals_by_type`, `technicians_available`
  (`available_count`), `technicians_busy` (`unavailable_count`), `average_rating` — se reusan
  **tal cual** de `accounts.services.selectors.ContractorAdminSelector.get_metrics()` (el mismo
  selector que alimenta `/panel/profesionales`). El Orchestrator no recalcula nada.
- `service_status_counts` — conteo de órdenes de servicio por **"último evento"**. Requiere
  `Subquery(OuterRef('pk'))` sobre `OrderServiceTimeline.objects.filter(order=OuterRef('pk'))
  .order_by('-created_at').values('status')[:1]` porque `OrderServiceTimeline` es un log
  append-only (sin campo de estado vivo en `Order`/`OrderServiceDetail`).
- `top_categories` — top 5 categorías de servicio por cantidad de órdenes con
  `current_status='completed'` (usando la misma `Subquery` de arriba), agrupado por
  `items__service_variant__service__category__name`.
- `top_professionals` — top 5 profesionales por `completed_count`, un `Count('user__
  assigned_services', filter=Q(user__assigned_services__order__status=Order.STATUS_COMPLETED),
  distinct=True)` **agregado real en SQL**, no iterando las properties Python del modelo.

**Consumido por:** `DashboardView.vue` (`/panel`), sección "Marketplace de Contratistas" — 4
tarjetas KPI (profesionales registrados, disponibles/ocupados, rating promedio, servicios en
curso) + 2 listas ("Categorías top", "Profesionales top") + link "Ir a Asignación de Técnicos"
hacia `/panel/asignacion-tecnicos`.

---

## Serializers

`dashboard/api/serializers.py` **re-exporta** los serializers de cada app dueña (`shop.api.
serializers`, `renting.api.serializers`, `quotes.api.serializers`, etc.) mas unos pocos propios
para Support (`ChatRoomSerializer`, `ChatRoomListSerializer`) y para Home/Core. No define
serializers de negocio propios — es un punto de entrada unico para el frontend admin, no una
fuente adicional de logica de validacion.

---

## Patrones obligatorios en esta app

1. **Toda nueva funcionalidad admin pasa por un Orchestrator** — nunca importar un `Command`/
   `Selector` de otra app directamente en `dashboard/api/views.py` sin pasar por
   `admin_orchestrators.py`.
2. **`permission_classes = ADMIN_PERMISSIONS` siempre**, en toda `ViewSet`/`APIView` nueva — no
   depender del default del proyecto (a diferencia del gap encontrado en `renting`/`marketing`).
3. **Multipart:** cualquier ViewSet que reciba archivos (`AdminCategoryViewSet`,
   `AdminBrandViewSet`) declara `parser_classes = [MultiPartParser, FormParser, JSONParser]`.
4. **Nunca duplicar logica de negocio** en un Orchestrator — si una regla de negocio nueva no
   cabe en un simple `**data` pass-through, esa regla va en el `Command` de la app dueña, no en
   `dashboard`.
5. **ViewSets que viven fisicamente en otra app** (como `AdminOperationViewSet`,
   `AdminDispatcherViewSet` en `operations`) se registran en `dashboard/api/urls.py` pero se
   documentan en el `.AGENT/docs/` de su app dueña, no aqui — este documento solo lista la ruta.

---

## Pendiente

- No existe test suite dedicada para permisos de `dashboard/api/views.py` mas alla de
  `dashboard/tests.py` (que cubre principalmente Renting/fulfillment) — considerar agregar un
  test parametrizado que confirme `IsAdminUser` en las 34 ViewSets si se quiere blindar contra
  regresiones de permisos en esta app tan sensible.

## Cambios Recientes

### 2026-09-22 — Migración WhatsApp Web Session → Baileys (Fases 1-24): acciones reales de sesión QR
- **Qué cambió**: `AdminWhatsAppConnectionStatusView` (GET) ahora incluye `qr_image` (data URL PNG
  real cuando el gateway Baileys tiene un QR vigente, `None` si no) en la entrada `qr_web_session`.
  Nueva vista `AdminWhatsAppSessionActionView` (`POST /api/v1/dashboard/whatsapp/session-action/`,
  body `{"action": "connect"|"disconnect"|"reconnect"}`) — opera siempre sobre
  `CONNECTION_TYPE_QR_WEB_SESSION` explícitamente, nunca sobre `settings.WHATSAPP_CONNECTION_TYPE`
  (esas acciones no aplican a Meta Cloud API, stateless por token).
- **Por qué**: Fase 16 del plan (`PLAN_ACCION_MIGRACION_WHATSAPP_BAILEYS_SINTEL.md`) — el panel
  necesita poder conectar/reconectar/desconectar la sesión QR real y mostrar el código.
- **Archivos afectados**: `dashboard/api/views.py` (+1 vista, +qr_image en la existente),
  `dashboard/api/urls.py` (+1 ruta).
- **Seguridad**: mismo `ADMIN_PERMISSIONS` que el resto de la app. Sin gateway configurado,
  `WhatsAppQRNotImplementedError`/`WhatsAppGatewayError` se traducen a 409/502 con un mensaje
  sanitizado — nunca un 500 ni un stack trace expuesto al frontend.
- **Tests**: verificado en vivo con `curl` real contra el servidor de desarrollo (connect sin
  gateway → `NOT_IMPLEMENTED` limpio, acción inválida → 400, `qr_image` presente en el shape) —
  ver `AUDITORIA/WHATSAPP_BAILEYS_ARCHITECTURE.md`.

### 2026-09-25 - Endpoint de identidad para el servidor MCP
- `GET /api/v1/dashboard/mcp/whoami/` (`dashboard/api/mcp_views.py::AdminMcpWhoAmIView`, `ADMIN_PERMISSIONS`): solo lectura; devuelve `{uuid, email, is_admin, is_staff, is_superuser}` del propio token.
  Existe porque `/api/v1/auth/profile/` no expone `is_superuser`. Lo consume `mcp_server/auth.py` para validar el bearer de los clientes MCP con la autoridad de Django (sin RBAC paralelo).
- Tests escritos (no ejecutados): `dashboard/tests_mcp_whoami.py`. Ver `mcp_server/.AGENT/ARCHITECTURE.md` y `AUDITORIA/MCP_IMPLEMENTATION_REPORT.md`.

