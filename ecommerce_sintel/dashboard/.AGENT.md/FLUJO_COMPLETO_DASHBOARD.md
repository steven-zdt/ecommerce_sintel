# FLUJO COMPLETO — App `dashboard`

> Ultima actualizacion: 2026-06-22
> Documento de arquitectura vivo. Actualizar cada vez que se agregue un ViewSet, Orchestrator o endpoint.

---

## 1. Rol y Principios

`dashboard` es el **Backend for Frontend (BFF) exclusivo del panel administrativo**.

- **Unico punto de entrada** para toda escritura del admin SPA (`/api/v1/dashboard/`).
- **Zero ORM** en la capa de vistas: las views solo orquestan, nunca llaman a `Model.objects` directamente.
- **Zero negocio en vistas**: toda logica de dominio vive en los *Orchestrators* y debajo en los servicios de cada app.
- **Admin-only**: todos los endpoints exigen `IsAuthenticated` + `IsAdminUser` (role=ADMIN, de `users.api.permissions`).
- La vista publica del comprador JAMAS llama a `/api/v1/dashboard/`. Las reads publicas van a `/api/v1/{app}/`.

---

## 2. Estructura de Archivos

```
dashboard/
├── api/
│   ├── __init__.py
│   ├── serializers.py        # Re-exporta serializers de cada app (ningun serializer propio)
│   ├── urls.py               # Router unico: registra todos los ViewSets bajo /api/v1/dashboard/
│   └── views.py              # ViewSets BFF — delegan a admin_orchestrators
├── services/
│   └── admin_orchestrators.py  # Orchestrators por dominio — traducen a Commands/Selectors
├── migrations/               # Migraciones del modelo de dashboard (actualmente vacio — sin modelos propios)
├── .AGENT.md/
│   └── FLUJO_COMPLETO_DASHBOARD.md  # Este documento
├── admin.py
├── apps.py
├── models.py                 # Vacio — dashboard no tiene modelos propios
├── tests.py                  # Tests de integracion del BFF
└── views.py                  # Vacio — toda la logica esta en api/views.py
```

---

## 3. Arquitectura por Capas

```
Admin SPA (Vue 3)
    |
    | HTTP → /api/v1/dashboard/
    |
[dashboard/api/views.py]   ← ViewSets (capa presentacion — zero ORM)
    |  delega a
[dashboard/services/admin_orchestrators.py]  ← Orchestrators (capa coordinacion)
    |  llaman a
[{app}/services/commands.py]    ← Commands (escritura por dominio)
[{app}/services/selectors.py]   ← Selectors (lectura por dominio)
    |
[{app}/models.py]               ← ORM / PostgreSQL
```

---

## 4. Endpoints Completos

Prefijo base: `/api/v1/dashboard/`

### 4.1 Metricas

| Metodo | URL | ViewSet/View | Descripcion |
|--------|-----|--------------|-------------|
| GET | `metrics/` | `AdminMetricsView` | KPIs: ventas totales, ordenes, clientes, productos, ordenes recientes |

### 4.2 Usuarios

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `users/` | Lista todos los usuarios |
| POST | `users/` | Crea usuario (via `AccountCommands.register_user`) |
| GET | `users/{pk}/` | Detalle usuario |
| PATCH | `users/{pk}/` | Actualiza usuario |
| DELETE | `users/{pk}/` | Soft-delete (desactiva `is_active=False`) |

**Nota:** `pk` en `users/` es el ID entero. El admin panel debe usar `user.id`, no `user.uuid`.

### 4.3 Shop — Productos, Categorias, Marcas, Impuestos, Variantes

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET/POST | `products/` | Lista / Crea producto |
| GET/PATCH/DELETE | `products/{uuid}/` | Detalle / Edita / Elimina producto |
| GET | `products/{uuid}/variants/` | Lista variantes del producto |
| POST | `products/{uuid}/variants/create/` | Crea variante de producto |
| GET/POST | `categories/` | Lista / Crea categoria |
| GET/PATCH/DELETE | `categories/{uuid}/` | Detalle / Edita / Elimina categoria |
| GET/POST | `brands/` | Lista / Crea marca |
| GET/PATCH/DELETE | `brands/{uuid}/` | Detalle / Edita / Elimina marca |
| GET/POST | `taxes/` | Lista / Crea impuesto |
| GET/PATCH/DELETE | `taxes/{uuid}/` | Detalle / Edita / Elimina impuesto |

**Lookup field:** `uuid` en products, categories, brands, taxes.

### 4.4 Ordenes

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `orders/` | Lista todas las ordenes (admin) |
| GET | `orders/{uuid}/` | Detalle de orden |

**Solo lectura desde dashboard.** Las transiciones de estado (pago, entrega) las maneja `wompi` y `orders` via sus endpoints propios.

### 4.5 Inventario

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `inventory/` | Lista todos los StockRecords |
| GET | `inventory/{uuid}/` | Detalle de StockRecord |
| POST | `inventory/{uuid}/adjust/` | Ajuste de stock (ENTRY / EXIT) |

**Respuesta de adjust:** retorna la lista de movimientos (`InventoryTransaction[]`) del registro.

**Errores:**
- `409 Conflict` → `InsufficientStockError` (stock insuficiente para EXIT)
- `400 Bad Request` → `DjangoValidationError` (datos invalidos)

### 4.6 Renting — Equipos, Variantes, Categorias, Marcas, Labor, Logistica

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET/POST | `equipment/` | Lista / Crea equipo (filtros: `search`, `category__slug`, `brand__slug`) |
| GET/PATCH/DELETE | `equipment/{uuid}/` | Detalle / Edita / Elimina equipo |
| GET | `equipment/{uuid}/variants/` | Lista variantes del equipo |
| POST | `equipment/{uuid}/variants/create/` | Crea variante de equipo |
| PATCH | `equipment/{uuid}/variants/{variant_pk}/` | Actualiza variante |
| DELETE | `equipment/{uuid}/variants/{variant_pk}/delete/` | Elimina variante |
| GET/PUT/DELETE | `equipment/{uuid}/logistics/` | Config. logistica (upsert) |
| GET/POST | `renting-categories/` | Lista / Crea categoria de renting |
| GET/PATCH/DELETE | `renting-categories/{uuid}/` | Detalle / Edita / Elimina |
| GET/POST | `renting-brands/` | Lista / Crea marca de renting |
| GET/PATCH/DELETE | `renting-brands/{uuid}/` | Detalle / Edita / Elimina |
| GET/POST | `rental-labor/` | Lista / Crea labor (mano de obra) |
| GET/PATCH/DELETE | `rental-labor/{uuid}/` | Detalle / Edita / Elimina |

### 4.7 Cotizaciones

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `quotations/` | Lista cotizaciones |
| POST | `quotations/` | Crea cotizacion (via `QuotationBuilder.create_quotation`) |
| GET | `quotations/{uuid}/` | Detalle de cotizacion con items y servicios |

### 4.8 Servicios Tecnicos

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET/POST | `services/` | Lista / Crea servicio tecnico |
| GET/PATCH/DELETE | `services/{uuid}/` | Detalle / Edita / Elimina servicio |
| GET/POST | `service-categories/` | Lista / Crea categoria de servicio |
| GET/PATCH/DELETE | `service-categories/{uuid}/` | Detalle / Edita / Elimina |
| GET | `service-variants/?service={uuid}` | Lista variantes de un servicio |
| POST | `service-variants/` | Crea variante (requiere `service` en body) |
| GET/PATCH/DELETE | `service-variants/{uuid}/` | Detalle / Edita / Elimina variante |
| GET | `service-variants/{uuid}/price_history/` | Historial de precios de variante |

**Nota:** Los Niveles de Servicio se gestionan via el endpoint publico `services/levels/`
(en `technical_services` app) con permisos `IsAdminOrReadOnly`, NO via dashboard BFF.

### 4.9 Costos Adicionales (Motor de Precios)

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `additional-costs/` | Lista todos los costos adicionales |
| POST | `additional-costs/` | Crea costo adicional |
| GET | `additional-costs/{uuid}/` | Detalle de costo adicional |
| PATCH | `additional-costs/{uuid}/update/` | Edita costo adicional (partial) |
| POST | `additional-costs/{uuid}/deactivate/` | Soft-delete (devuelve 204) |
| POST | `additional-costs/{uuid}/assign/` | Asigna costo a variante especifica |

**Parametros de `assign`:**
```json
{
  "target_type": "product_variant" | "equipment_variant" | "technical_service",
  "target_uuid": "uuid-de-la-variante"
}
```
- `product_variant` → busca `shop.ProductVariant`
- `equipment_variant` → busca `renting.EquipmentVariant`
- `technical_service` → busca `technical_services.ServiceVariant` (NO TechnicalService)

### 4.10 Marketing

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `marketing/summary/` | Resumen consolidado multi-app |
| GET | `marketing/campaigns/` | Lista campanas de marketing |
| GET | `marketing/flash-offers/` | Lista ofertas flash |

---

## 5. Orchestrators — `admin_orchestrators.py`

Cada orchestrator agrupa las operaciones de un dominio. Traducen el lenguaje del admin panel al lenguaje de los servicios internos.

| Orchestrator | Dominio | Servicios usados |
|---|---|---|
| `AdminMetricsOrchestrator` | KPIs del dashboard | `Order`, `User`, `Product` (ORM directo, solo para agregacion) |
| `ShopAdminOrchestrator` | Shop | `ProductSelector/Commands`, `CategorySelector/Commands`, `BrandSelector/Commands`, `TaxSelector/Commands`, `ProductVariantSelector/Commands` |
| `ServiceAdminOrchestrator` | Servicios tecnicos | `ServiceSelector/Commands`, `ServiceCategorySelector/Commands`, `ServiceLevelSelector/Commands`, `ServiceVariantSelector/Commands`, `ServiceMaterialSelector/Commands` |
| `RentingAdminOrchestrator` | Renting | `RentingSelector`, `EquipmentCommands/Selector`, `EquipmentVariantCommands/Selector`, `RentingCategoryCommands`, `RentingBrandCommands`, `RentalLaborCommands`, `EquipmentLogisticsConfigCommands` |
| `QuotationAdminOrchestrator` | Cotizaciones | `QuotationSelector`, `QuotationBuilder (alias QuotationCommands)` |
| `OrderAdminOrchestrator` | Ordenes | `OrderSelector` |
| `MarketingAdminOrchestrator` | Marketing | `MarketingSelector` |
| `InventoryAdminOrchestrator` | Inventario | `StockRecordSelector`, `InventorySelector`, `InventoryCommands`, `StockAdjustmentDTO` |

**Costos Adicionales:** `AdminAdditionalCostViewSet` llama directamente a `AdditionalCostSelector` y `AdditionalCostCommands` de `quotes` — no usa un orchestrator intermedio (el ViewSet es suficientemente simple).

---

## 6. Serializers — `api/serializers.py`

`dashboard/api/serializers.py` es **unicamente un re-exportador**. No define ningun serializer propio. Importa y re-exporta de cada app:

| App origen | Serializers re-exportados |
|---|---|
| `shop.api.serializers` | `ProductSerializer`, `ProductInputSerializer`, `CategorySerializer`, `CategoryInputSerializer`, `BrandSerializer`, `BrandInputSerializer`, `TaxSerializer`, `TaxInputSerializer`, `ProductVariantSerializer`, `ProductVariantInputSerializer` |
| `users.api.serializers` | `UserProfileSerializer`, `VendorProfileSerializer`, `UserDetailSerializer`, `UserAdminCreateSerializer`, `UserAdminUpdateSerializer` |
| `orders.api.serializers` | `OrderSerializer`, `OrderItemSerializer`, `ShippingAddressSerializer` |
| `inventory.api.serializers` | `StockRecordSerializer`, `InventoryTransactionSerializer`, `StockAdjustmentInputSerializer` |
| `renting.api.serializers` | `EquipmentSerializer`, `EquipmentInputSerializer`, `EquipmentVariantSerializer`, `EquipmentVariantInputSerializer`, `RentingCategorySerializer`, `RentingCategoryInputSerializer`, `RentingBrandSerializer`, `RentingBrandInputSerializer`, `RentalLaborSerializer`, `RentalLaborInputSerializer`, `EquipmentLogisticsConfigSerializer`, `EquipmentLogisticsConfigInputSerializer` |
| `quotes.api.serializers` | `QuotationSerializer`, `QuotationItemSerializer`, `QuotationServiceSerializer`, `QuotationMaterialSerializer`, `QuotationCreateInputSerializer` |
| `technical_services.api.serializers` | `ServiceCategorySerializer`, `ServiceCategoryInputSerializer`, `ServiceLevelSerializer`, `ServiceLevelInputSerializer`, `ServiceConfigurationSerializer`, `ServiceConfigurationInputSerializer`, `ServiceVariantSerializer`, `ServiceVariantInputSerializer`, `ServiceMaterialSerializer`, `ServiceMaterialInputSerializer`, `TechnicalServiceSerializer`, `TechnicalServiceInputSerializer`, `ServicePriceHistorySerializer` |

Los serializers de `AdditionalCost` se importan directamente desde `quotes.api.serializers` en `views.py` (no pasan por el re-exportador).

---

## 7. Patrones de ViewSet Usados

### 7.1 ViewSet estandar (CRUD manual)

Usado por la mayoria de ViewSets. Hereda de `viewsets.ViewSet` y define metodos manualmente.

```python
class AdminProductViewSet(viewsets.ViewSet):
    permission_classes = ADMIN_PERMISSIONS

    def list(self, request): ...
    def create(self, request): ...
    def retrieve(self, request, pk=None): ...
    def partial_update(self, request, pk=None): ...
    def destroy(self, request, pk=None): ...
```

**Lookup:** `pk` recibe el UUID como string. Los orchestrators usan ese valor como `uuid` en sus queries.

### 7.2 GenericViewSet con mixins (POST habilitado via mixin)

Requerido cuando un `ReadOnlyModelViewSet` bloquearia el POST. Ver nota `DRF mixin POST pattern`.

```python
class AdminAdditionalCostViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    lookup_field = 'uuid'
    serializer_class = AdditionalCostSerializer
    ...
```

Los metodos `list()`, `retrieve()`, `create()` estan todos sobreescritos. Los mixins sirven para que DRF Router genere las URLs correctas (GET list, GET detail, POST).

### 7.3 APIView pura

Solo para `AdminMetricsView` (no necesita router ni CRUD).

```python
class AdminMetricsView(APIView):
    permission_classes = ADMIN_PERMISSIONS
    def get(self, request): ...
```

Registrada en `urls.py` como:
```python
path('metrics/', AdminMetricsView.as_view(), name='admin-metrics')
```

---

## 8. Reglas de Escritura del BFF

### 8.1 Flujo de Request (escritura)

```
Vue POST /api/v1/dashboard/products/
    → AdminProductViewSet.create(request)
        → ProductInputSerializer.is_valid()
        → ShopAdminOrchestrator.create_product(request.user, validated_data)
            → ProductCommands.create_product(vendor=user, **data)
                → Product.objects.create(...)
                → ProductVariant.objects.create(...)  [variant por defecto]
    ← Response(201, ProductSerializer(product).data)
```

### 8.2 Flujo de Request (lectura)

```
Vue GET /api/v1/dashboard/products/{uuid}/
    → AdminProductViewSet.retrieve(request, pk=uuid)
        → ShopAdminOrchestrator.get_product(uuid)
            → ProductSelector.get_by_uuid(uuid)
                → Product.objects.get(uuid=uuid)
    ← Response(200, ProductSerializer(product).data)
```

### 8.3 Flujo Inventario (ajuste de stock)

```
Vue POST /api/v1/dashboard/inventory/{uuid}/adjust/
    → AdminInventoryViewSet.adjust(request, pk=uuid)
        → StockAdjustmentInputSerializer.is_valid()
        → InventoryAdminOrchestrator.adjust_stock(record, movement_type, quantity, reference)
            → StockAdjustmentDTO(stock_record_uuid, quantity, reference)
            → InventoryCommands.register_entry(dto) | register_exit(dto)
                → KardexService.apply_movement(...)
    ← Response(200, InventoryTransactionSerializer(movements, many=True).data)
```

---

## 9. Manejo de Errores

| Error | HTTP | Donde se captura |
|---|---|---|
| `InsufficientStockError` | 409 Conflict | `AdminInventoryViewSet.handle_exception()` |
| `DjangoValidationError` | 400 Bad Request | `AdminInventoryViewSet.handle_exception()` |
| `serializer.is_valid(raise_exception=True)` | 400 Bad Request | DRF automatico |
| `get_object_or_404` / `DoesNotExist` | 404 Not Found | DRF automatico |
| `ValueError` | 400 Bad Request | Capturado manualmente en varios ViewSets admin (ej. `AdminDispatcherViewSet`) |
| Entidad no encontrada en `assign` | 404 Not Found | Try/except en `AdminAdditionalCostViewSet.assign()` |

---

## 10. Permisos

**Un solo guard para todo el BFF:**

```python
ADMIN_PERMISSIONS = [permissions.IsAuthenticated, IsAdminUser]
```

- `IsAuthenticated` → JWT valido con usuario activo
- `IsAdminUser` → `from users.api.permissions import IsAdminUser` — verifica `user.role == ADMIN` (NO es `rest_framework.permissions.IsAdminUser`)

**CRITICO:** Los administradores SOLO se crean via CLI (`createsuperuser` o management command). La API NUNCA puede otorgar `is_staff=True` ni `is_superuser=True`.

---

## 11. Tests — `tests.py`

Actualmente existe `DashboardInventoryAPITestCase` que cubre:
- `GET /api/v1/dashboard/inventory/` — lista correctamente
- `GET /api/v1/dashboard/inventory/{uuid}/` — detalle correcto
- `POST /api/v1/dashboard/inventory/{uuid}/adjust/` — ajuste ENTRY exitoso

**Pendiente de cubrir:**
- Ajuste EXIT (incluyendo error 409 por stock insuficiente)
- CRUD de productos, variantes
- Creacion de cotizacion
- CRUD de costos adicionales
- Asignacion de costo a variante

---

## 12. Bugs Corregidos en Esta Auditoria (2026-06-22)

| # | Bug | Archivo | Correccion |
|---|-----|---------|------------|
| 1 | Imports mid-archivo (`Sum`, `APIView`, `Order`, `User`, `Product`, `mixins`) | `api/views.py` | Movidos al bloque de imports del top del archivo |
| 2 | `AdminMetricsView` accedia al ORM directamente (violaba "Zero ORM in this layer") | `api/views.py` | Extraida logica a `AdminMetricsOrchestrator.get_metrics()` en `admin_orchestrators.py` |
| 3 | `assign()` para `target_type='technical_service'` importaba `TechnicalService` en lugar de `ServiceVariant` | `api/views.py` | Corregido a `ServiceVariant` — el GFK de `CostAssignment` debe apuntar a la variante de servicio (unidad de precio), no al servicio padre |

---

## 13. Checklist para Agregar un Nuevo ViewSet al BFF

```
[ ] Crear la clase ViewSet en dashboard/api/views.py
    [ ] Heredar de viewsets.ViewSet (o GenericViewSet + mixins si se necesita POST)
    [ ] permission_classes = ADMIN_PERMISSIONS
    [ ] lookup_field = 'uuid' si los endpoints usan UUID en la URL
    [ ] Delegar TODA la logica a un Orchestrator o directamente a Commands/Selectors

[ ] Agregar metodos al Orchestrator correspondiente en admin_orchestrators.py
    [ ] Ninguna llamada ORM directa — solo Commands y Selectors de la app destino

[ ] Registrar el ViewSet en dashboard/api/urls.py
    [ ] router.register(r'prefijo', NuevoViewSet, basename='admin-prefijo')

[ ] Agregar import del ViewSet en dashboard/api/urls.py

[ ] Actualizar dashboard/api/serializers.py si se necesita re-exportar nuevos serializers

[ ] Actualizar este documento (FLUJO_COMPLETO_DASHBOARD.md)
    [ ] Agregar la seccion de endpoints en 4.X
    [ ] Agregar el orchestrator en la tabla de la seccion 5
```
