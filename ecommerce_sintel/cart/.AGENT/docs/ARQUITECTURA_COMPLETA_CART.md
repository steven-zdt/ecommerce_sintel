# Arquitectura Completa - Modulo Cart

> **Ultima actualizacion:** 2026-07-03
> **Mantenido por:** Claude Code — sincronizado con el estado real del codigo

## Tabla de Contenidos
1. [Descripcion General](#descripcion-general)
2. [Estructura de Directorios](#estructura-de-directorios)
3. [Modelos de Datos](#modelos-de-datos)
4. [Flujo Completo de la Aplicacion](#flujo-completo-de-la-aplicacion)
5. [Descripcion de Cada Archivo](#descripcion-de-cada-archivo)
6. [Endpoints Disponibles](#endpoints-disponibles)
7. [Flujo de Datos](#flujo-de-datos)
8. [Patrones de Diseno](#patrones-de-diseno)
9. [Caracteristicas Especiales](#caracteristicas-especiales)

---

## Descripcion General

El modulo **cart** gestiona el carrito de compras en la aplicacion e-commerce. Implementa un sistema flexible que:

- **Soporta productos y servicios**: CartItem puede referenciar ProductVariant o ServiceVariant
- **Gestión por usuario autenticado**: Carrito asociado al usuario logueado
- **Soporte para invitados**: Carrito temporal con guest_id (UUID)
- **Operaciones CRUD completas**: Agregar, actualizar, eliminar, vaciar
- **Optimización de queries**: Prefetch_related para evitar N+1 queries
- **Protección contra race conditions**: select_for_update() en operaciones críticas
- **Wishlist integrada**: Gestión de favoritos en el mismo módulo

**Patrón Arquitectónico**: Service Layer + API ViewSets (Session-based)
- **Services**: Contienen lógica de negocio (commands para escritura, selectors para lectura)
- **API**: Views (ViewSets) + Serializers para validación y serialización
- **Models**: Cart, CartItem, WishlistItem con relaciones polimórficas

---

## Estructura de Directorios

```
ecommerce_sintel/cart/
├── api/
│   ├── __init__.py                          # Inicializador del paquete API
│   ├── views.py                             # ViewSets REST con endpoints del carrito
│   ├── serializers.py                       # Validadores y serializadores
│   └── urls.py                              # Rutas del API REST
├── services/
│   ├── __init__.py                          # Exporta CartSelector y CartCommands
│   ├── commands.py                          # Lógica de negocio (escritura)
│   └── selectors.py                         # Lógica de lectura/consulta
├── static/
│   └── cart/
│       ├── js/
│       │   ├── cart.api.js                  # Cliente HTTP para API del carrito
│       │   ├── cart.table.js                # Renderizado de tabla del carrito
│       │   ├── cart.ui.js                   # Lógica de interfaz de usuario
│       │   └── cart.utils.js                # Funciones utilitarias
│       └── css/
│           └── cart.css                     # Estilos del carrito
├── migrations/
│   ├── __init__.py
│   ├── 0001_initial.py                      # Creación inicial de tablas
│   └── 0002_cartitem_service_variant...     # Adición de soporte para servicios
├── apps.py                                  # Configuración de la aplicación Django
├── models.py                                # Modelos ORM (Cart, CartItem, WishlistItem)
├── urls.py                                  # Enrutador principal
└── ARQUITECTURA_COMPLETA_CART.md            # Este documento
```

---

## Modelos de Datos

### 1. **Cart** (Carrito Principal)

```python
class Cart(SintelBaseModel):
    user = ForeignKey(AUTH_USER_MODEL, null=True, blank=True)
    guest_id = UUIDField(null=True, blank=True, db_index=True)
```

**Campos**:
- `uuid` (heredado de SintelBaseModel): Identificador único del carrito
- `created_at`: Timestamp de creación
- `updated_at`: Timestamp de última actualización
- `user`: Relación con Usuario (null = carrito de invitado)
- `guest_id`: UUID para identificar carritos de invitados

**Características**:
- Un usuario tiene UN carrito (relación 1:N inversa)
- Soporta carritos anónimos con guest_id
- `on_delete=CASCADE`: Elimina carrito si usuario se borra
- `related_name='cart'`: Acceso desde User.cart

**Relación**:
```
User (1) ──────→ (N) Cart (1) ──────→ (N) CartItem
                           └──→ (N) WishlistItem
```

---

### 2. **CartItem** (Ítems en el Carrito)

```python
class CartItem(SintelBaseModel):
    cart = ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    variant = ForeignKey(ProductVariant, on_delete=models.CASCADE, null=True, blank=True)
    service_variant = ForeignKey(ServiceVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = PositiveIntegerField(default=1)
```

**Campos**:
- `uuid`: Identificador único del item
- `cart`: Relación con el carrito (obligatorio)
- `variant`: ProductVariant (opcional, para productos)
- `service_variant`: ServiceVariant (opcional, para servicios)
- `quantity`: Cantidad del item (mínimo 1)
- `created_at`, `updated_at`: Timestamps

**Características**:
- **Polimórfico**: Un CartItem puede ser Producto O Servicio (no ambos)
- `on_delete=CASCADE`: Elimina item si variante se borra
- `related_name='items'`: Acceso desde Cart.items.all()
- `null=True, blank=True`: Permite que uno u otro sea null
- `db_index=False` implícito: No indexados, búsquedas por FK

**Validación en Views**:
```python
# Uno u otro, no ambos
if not variant_uuid and not service_variant_uuid:
    raise ValidationError("Debe proporcionar variant_uuid o service_variant_uuid")
```

**Relaciones**:
```
ProductVariant ──→ CartItem ←─ ServiceVariant
                      │
                    (N) ↓
                     Cart ← User
```

---

### 3. **WishlistItem** (Lista de Favoritos)

```python
class WishlistItem(SintelBaseModel):
    user = ForeignKey(AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    variant = ForeignKey(ProductVariant, on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ('user', 'variant')
```

**Campos**:
- `uuid`: Identificador único
- `user`: Usuario propietario de la lista
- `variant`: Producto en favoritos
- `created_at`, `updated_at`: Timestamps

**Características**:
- **Solo productos**, no servicios (solo variant, no service_variant)
- **Unique together**: Un usuario no puede agregar el mismo producto dos veces
- `on_delete=CASCADE`: Elimina si usuario o producto se borra
- `related_name='wishlist'`: Acceso desde User.wishlist.all()

**Restricción**:
```sql
UNIQUE INDEX (user_id, variant_id)
```

---

## Flujo Completo de la Aplicación

### 1️⃣ **LISTA DE CARRITO (List Flow)**

```
Cliente (GET /api/v1/cart/)
    ↓
[AUTH] IsAuthenticated (JWT token requerido)
    ↓
[SELECTOR] CartSelector.get_for_user(user)
    ├─ get_or_create(user=user) si no existe
    ├─ prefetch_related para optimización (items → variant → product)
    └─ Retorna Cart con items precargados
    ↓
[SERIALIZER] CartSerializer
    ├─ Serializa Cart completo
    ├─ CartItemSerializer para cada item
    ├─ Calcula total_items (suma de quantities)
    └─ Retorna estructura completa
    ↓
Retornar 200 OK con datos del carrito
```

### 2️⃣ **AGREGAR ÍTEM (Add Item Flow)**

```
Cliente (POST /api/v1/cart/add_item/)
    {
        "variant_uuid": "uuid...",          # O service_variant_uuid
        "quantity": 3
    }
    ↓
[AUTH] IsAuthenticated
    ↓
[SERIALIZER] AddCartItemSerializer
    ├─ Valida variant_uuid XOR service_variant_uuid
    ├─ Valida quantity >= 1
    └─ Retorna validated_data
    ↓
[VIEWS] Resuelve variantes
    ├─ Busca ProductVariant(uuid=variant_uuid) o 404
    ├─ Busca ServiceVariant(uuid=service_variant_uuid) o 404
    └─ Obtiene cart del usuario
    ↓
[COMMANDS] CartCommands.add_item()
    ├─ Transacción atómica (@transaction.atomic)
    ├─ select_for_update() para evitar race conditions
    ├─ get_or_create() con (cart, variant, service_variant)
    ├─ Si existe: incrementa quantity
    ├─ Si nuevo: crea con quantity especificada
    └─ Retorna CartItem
    ↓
[SERIALIZER] CartItemSerializer
    └─ Retorna item creado/actualizado
    ↓
Retornar 201 Created con item
```

### 3️⃣ **VACIAR CARRITO (Clear Flow)**

```
Cliente (POST /api/v1/cart/clear/)
    ↓
[AUTH] IsAuthenticated
    ↓
[SELECTOR] Obtiene carrito del usuario
    ↓
[COMMANDS] CartCommands.clear_cart(cart)
    ├─ Transacción atómica
    ├─ cart.items.all().delete()
    └─ Todos los CartItems se borran
    ↓
Retornar 200 OK con mensaje
```

### 4️⃣ **ELIMINAR ÍTEM (Remove Item Flow)**

```
Cliente (POST /api/v1/cart/remove-item/{item_uuid}/)
    ↓
[AUTH] IsAuthenticated
    ↓
[VIEWS] Resuelve item
    ├─ Busca CartItem(cart=cart, uuid=item_uuid) o 404
    └─ Valida que pertenezca al carrito del usuario
    ↓
Item.delete()
    ↓
Retornar 200 OK con mensaje
```

### 5️⃣ **ACTUALIZAR CANTIDAD (Update Quantity Flow)** - Interno

```
[COMMANDS] CartCommands.update_item_quantity()
    ├─ Parámetros: cart, variant/service_variant, quantity
    ├─ Si quantity <= 0: Elimina el item
    ├─ Si quantity > 0:
    │   ├─ select_for_update() para lock
    │   ├─ item.quantity = quantity
    │   └─ item.save()
    └─ Retorna CartItem o None

# Útil para:
# - Cambios de cantidad desde UI
# - Decrementar stock
# - Eliminar si quantity=0
```

---

## Descripción de Cada Archivo

### **📁 api/ (API Layer)**

#### `api/views.py` - CartViewSet Principal
**Responsabilidad**: Exponer endpoints REST y orquestar requests/responses

**Clase**: `CartViewSet(viewsets.ViewSet)`
- No es ModelViewSet porque las acciones son session-based (basadas en usuario autenticado)
- `permission_classes = [IsBuyerOrAdmin]` (de `users.api.permissions`, no `IsAuthenticated` generico -- ver [CORRECCION 2026-07-03] abajo)

**Métodos principales**:

1. **get_cart()** - Método helper
   ```python
   def get_cart(self):
       return CartSelector.get_for_user(self.request.user)
   ```
   - Obtiene carrito optimizado del usuario actual
   - Usado por todos los demás métodos

2. **list(request)** [GET, IsAuthenticated]
   ```python
   GET /api/v1/cart/
   Retorna: CartSerializer (carrito completo con items)
   Status: 200 OK
   ```
   - Retorna carrito actual del usuario
   - Incluye todos los items con detalles
   - Calcula total_items

3. **add_item(request)** [POST, IsAuthenticated]
   ```python
   POST /api/v1/cart/add_item/
   Body: {variant_uuid, service_variant_uuid, quantity}
   Retorna: CartItemSerializer
   Status: 201 Created
   ```
   - Agrega o actualiza cantidad de un item
   - Acepta ProductVariant o ServiceVariant
   - Crea CartItem si no existe, incrementa cantidad si existe

4. **clear(request)** [POST, IsAuthenticated]
   ```python
   POST /api/v1/cart/clear/
   Body: (vacío)
   Retorna: {"detail": "Carrito vaciado."}
   Status: 200 OK
   ```
   - Vacía completamente el carrito
   - Borra todos los CartItems

5. **remove_item(request, item_uuid)** [POST, IsAuthenticated]
   ```python
   POST /api/v1/cart/remove-item/{item_uuid}/
   Retorna: {"detail": "Item eliminado."}
   Status: 200 OK
   ```
   - Elimina un item específico del carrito
   - Usa UUID del CartItem

**Integración**:
- Usa `drf-spectacular` para documentación (@extend_schema)
- Importa serializers de `cart.api.serializers`
- Importa services de `cart.services` (CartCommands, CartSelector)
- Obtiene ProductVariant y ServiceVariant por UUID
- Valida autenticación en clase (no por endpoint)

---

#### `api/serializers.py` - Validadores de Datos
**Responsabilidad**: Validar y transformar datos de entrada/salida

**Clases**:

**[CORRECCION 2026-07-03]** La forma real de estos serializers es distinta a la descrita
originalmente aqui (no usan `depth=1` ni un campo `total_price` simple) -- corregido abajo.

1. **CartItemSerializer** (ModelSerializer, todos los campos via `SerializerMethodField`)
   - **Modelo**: CartItem
   - **Campos reales**: `uuid`, `item_type` ('product'|'service'|'unknown'), `variant_uuid`,
     `product_name`, `variant_sku`, `quantity`, `unit_price`, `subtotal`,
     `unit_price_with_tax`, `final_price`, `created_at`
   - `unit_price_with_tax` usa `PricingService.calculate_variant_price(variant, include_active_taxes=True)`
     para productos; para servicios usa `fixed_price` o `ServiceSelector.get_variant_quotation()`
   - `final_price = unit_price_with_tax * quantity`
   - **Uso**: Respuesta en `add_item()`/`update_item()`, lista en `CartSerializer`

2. **CartSerializer** (ModelSerializer)
   - **Modelo**: Cart
   - **Campos reales**: `uuid`, `items` (CartItemSerializer many=True), `total_items`, `total`,
     `total_cart_value` (alias de `total`), `created_at`
   - **Read-only**: Todos los campos (no se puede editar carrito directamente)
   - **Métodos personalizados**:
     ```python
     def get_total_items(self, obj):
         return sum(item.quantity for item in obj.items.all())

     def get_total(self, obj):
         # Suma final_price (con impuestos) de cada item via CartItemSerializer
         ...
     ```
   - **Uso**: Respuesta en `list()`, información general

3. **AddCartItemSerializer** (Serializer - No ModelSerializer)
   - **Campos**:
     - `variant_uuid`: UUIDField (requerido=False)
     - `service_variant_uuid`: UUIDField (requerido=False)
     - `quantity`: IntegerField (min_value=1, default=1)
   - **Validación**:
     ```python
     def validate(self, data):
         if not data.get('variant_uuid') and not data.get('service_variant_uuid'):
             raise ValidationError("Debe proporcionar un variant_uuid o service_variant_uuid.")
         return data
     ```
   - **XOR Logic**: Uno u otro, no ambos, no ninguno
   - **Uso**: Request en `add_item()`

---

#### `api/urls.py` - Rutas del API
**Responsabilidad**: Mapear URLs a endpoints

```python
router = DefaultRouter()
router.register(r'', CartViewSet, basename='cart')
```

**Endpoints generados**:
- `GET /api/v1/cart/` → list()
- `POST /api/v1/cart/add_item/` → add_item()
- `POST /api/v1/cart/clear/` → clear()
- `POST /api/v1/cart/remove-item/{item_uuid}/` → remove_item()

**Nota**: Las rutas son prefijadas por `urls.py` principal que hace `include('cart.api.urls')`

---

### **📁 services/ (Business Logic Layer)**

#### `services/commands.py` - Comandos (Escritura)
**Responsabilidad**: Centralizar lógica de negocio para operaciones de escritura

**Clase**: `CartCommands()`

**Métodos principales**:

1. **add_item(cart, variant=None, service_variant=None, quantity=1) → CartItem**
   ```python
   @staticmethod
   @transaction.atomic
   def add_item(cart, variant=None, service_variant=None, quantity=1):
   ```
   - **Transacción atómica**: Rollback si falla algo
   - **Parámetros**:
     - `cart`: Objeto Cart (requerido)
     - `variant`: ProductVariant (opcional)
     - `service_variant`: ServiceVariant (opcional)
     - `quantity`: Cantidad a agregar (default=1)
   - **Lógica**:
     ```
     select_for_update() → bloquea la fila para evitar race conditions
     get_or_create(cart, variant, service_variant, defaults=quantity)
     Si existe:
         item.quantity += quantity
         item.save()
     Si es nuevo:
         crea con quantity especificada
     ```
   - **Excepciones**: ValueError si no hay variant ni service_variant
   - **Retorna**: CartItem (creado o actualizado)
   - **Caso de uso**: Agregar producto/servicio al carrito

2. **update_item_quantity(cart, variant=None, service_variant=None, quantity=0) → CartItem or None**
   ```python
   @staticmethod
   @transaction.atomic
   def update_item_quantity(cart, variant=None, service_variant=None, quantity=0):
   ```
   - **Transacción atómica**
   - **Parámetros**: Igual a add_item, pero quantity es absoluto (no aditivo)
   - **Lógica**:
     ```
     Si quantity <= 0:
         Elimina el CartItem
         Retorna None
     Si quantity > 0:
         select_for_update() → bloquea para evitar race conditions
         item.quantity = quantity
         item.save()
         Retorna CartItem actualizado
     ```
   - **Casos de uso**: 
     - Cambiar cantidad manualmente
     - Decrementar stock
     - Eliminar si quantity=0

3. **remove_item(cart, variant=None, service_variant=None)**
   ```python
   @staticmethod
   @transaction.atomic
   def remove_item(cart, variant=None, service_variant=None):
   ```
   - **Transacción atómica**
   - **Parámetros**: cart (requerido), variant O service_variant
   - **Lógica**: Elimina CartItem con lookup específico
   - **Casos de uso**: Remover producto/servicio del carrito

4. **clear_cart(cart)**
   ```python
   @staticmethod
   @transaction.atomic
   def clear_cart(cart):
   ```
   - **Transacción atómica**
   - **Parámetro**: `cart` (requerido)
   - **Lógica**: `cart.items.all().delete()` - Elimina todos los items
   - **Casos de uso**: Vaciar carrito completamente (checkout, cancelación)

**Patrones**:
- Transacciones atómicas en todas las operaciones
- `select_for_update()` para lock pesimista (prevenir race conditions)
- `get_or_create()` para idempotencia
- Operaciones atómicas garantizan integridad

---

#### `services/selectors.py` - Selectores (Lectura)
**Responsabilidad**: Centralizar lógica de lectura y consultas optimizadas

**Clase**: `CartSelector()`

**Métodos principales**:

1. **get_for_user(user) → Cart**
   ```python
   @staticmethod
   def get_for_user(user) -> Cart:
       cart, _ = Cart.objects.get_or_create(user=user)
       return (
           Cart.objects
           .prefetch_related(
               'items__variant__product',
               'items__service_variant__service'
           )
           .get(id=cart.id)
       )
   ```
   - **Función**: Obtiene carrito del usuario (crea si no existe)
   - **Optimización**: 
     - `get_or_create()`: Crea carrito si usuario no lo tiene
     - `prefetch_related()`: Evita N+1 queries
   - **Prefetch chains**:
     - `items__variant__product`: Trae variants y sus productos
     - `items__service_variant__service`: Trae service_variants y servicios
   - **Retorna**: Cart completo con items precargados
   - **Caso de uso**: Obtener carrito actual (en cada request autenticado)

2. **get_by_guest_id(guest_id: str) → Cart**
   ```python
   @staticmethod
   def get_by_guest_id(guest_id: str) -> Cart:
       return (
           Cart.objects
           .prefetch_related(
               'items__variant__product',
               'items__service_variant__service'
           )
           .get(guest_id=guest_id)
       )
   ```
   - **Función**: Obtiene carrito de invitado por UUID
   - **Optimización**: Mismo prefetch que get_for_user()
   - **Excepciones**: Cart.DoesNotExist si guest_id no existe
   - **Casos de uso**:
     - Recuperar carrito de invitado sin login
     - Merge carrito invitado después de login

3. **get_cart_queryset(cart_id: int) → QuerySet**
   ```python
   @staticmethod
   def get_cart_queryset(cart_id: int) -> QuerySet:
       return Cart.objects.filter(id=cart_id).prefetch_related(
           'items__variant__product', 
           'items__service_variant__service'
       )
   ```
   - **Función**: Obtiene QuerySet optimizado de carrito por ID
   - **Optimización**: prefetch_related (no ejecuta query)
   - **Retorna**: QuerySet (no instancia, para reutilizar)
   - **Casos de uso**: Cuando necesitas QuerySet (bulk operations, filtros)

**Optimización de Queries**:
```
SIN prefetch_related:
GET /cart/               → 1 query (Cart)
Listar items            → N queries (CartItem x cantidad)
Ver variant de cada     → N queries (ProductVariant x cantidad)
Ver product de cada     → N queries (Product x cantidad)
TOTAL: 1 + 3N queries

CON prefetch_related:
GET /cart/               → 1 query (Cart)
Prefetch items          → 1 query (CartItem)
Prefetch variants       → 1 query (ProductVariant)
Prefetch products       → 1 query (Product)
Prefetch service_variants → 1 query (ServiceVariant)
Prefetch services       → 1 query (Service)
TOTAL: 6 queries (independiente de N items)
```

---

#### `services/__init__.py` - Exportador
**Responsabilidad**: Exportar clases principales para facilitar imports

```python
from .selectors import CartSelector
from .commands import CartCommands

__all__ = ['CartSelector', 'CartCommands']
```

**Uso**:
```python
from cart.services import CartSelector, CartCommands
```

---

### **📁 Configuración de Aplicación**

#### `apps.py` - Configuración Django
```python
class CartConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cart'
```

---

#### `models.py` - Definición de Modelos
**Modelos principales**: Cart, CartItem, WishlistItem

**Herencia**: Todos heredan de `SintelBaseModel`
- `uuid`: UUID único
- `created_at`, `updated_at`: Timestamps automáticos

---

#### `urls.py` - Enrutador Principal
```python
urlpatterns = [
    path('', include('cart.api.urls')),
]
```

Delega a `api/urls.py` para las rutas REST.

---

### **📁 static/ (Archivos Estáticos Frontend)**

#### `static/cart/js/cart.api.js` - Cliente HTTP
**Responsabilidad**: Interfaz HTTP para llamar API del carrito

```javascript
window.Sintel.Cart.API = {
    list: (params) => fetch(`/api/v1/cart/?...`),
    get: (uuid) => fetch(`/api/v1/cart/${uuid}/`),
    clear: () => fetch(`/api/v1/cart/clear/`, { method: 'DELETE' }),
    
    authHeaders: () => ({
        'Authorization': `Bearer ${localStorage.getItem('access')}`
    })
}
```

**Métodos**:
- `list()`: GET carrito actual
- `get(uuid)`: GET carrito específico
- `clear()`: DELETE carrito (vaciar)
- `authHeaders()`: Construye headers con JWT token

**Patrón**:
```javascript
// Uso desde otro módulo
Sintel.Cart.API.list()
    .then(r => r.json())
    .then(data => console.log(data))
```

---

#### `static/cart/js/cart.table.js` - Tabla del Carrito
**Responsabilidad**: Renderizar tabla con items del carrito

**Funcionalidades probables**:
- Renderizar filas de items
- Mostrar cantidad, precio, subtotal
- Botones de eliminar item

---

#### `static/cart/js/cart.ui.js` - Lógica de UI
**Responsabilidad**: Lógica de interfaz de usuario

**Funcionalidades probables**:
- Eventos de botones (agregar, eliminar, vaciar)
- Validaciones de UI
- Feedback visual (mensajes, spinners)

---

#### `static/cart/js/cart.utils.js` - Utilidades
**Responsabilidad**: Funciones auxiliares

**Funcionalidades probables**:
- Formateo de precios
- Cálculos (subtotales, totales)
- Conversiones de datos

---

#### `static/cart/css/cart.css` - Estilos
**Responsabilidad**: Estilos visuales del carrito

---

---

## Endpoints Disponibles

### Resumen de Endpoints

| Metodo | Endpoint | Autenticacion | Funcion |
|--------|----------|---------------|---------|
| GET | `/api/v1/cart/` | IsBuyerOrAdmin | Obtiene carrito del usuario |
| POST | `/api/v1/cart/add_item/` | IsBuyerOrAdmin | Agrega item al carrito |
| POST | `/api/v1/cart/update_item/` | IsBuyerOrAdmin | Actualiza cantidad (0 = elimina el item) |
| POST | `/api/v1/cart/clear/` | IsBuyerOrAdmin | Vacia el carrito |
| POST | `/api/v1/cart/remove-item/{uuid}/` | IsBuyerOrAdmin | Elimina item del carrito |
| POST | `/api/v1/cart/checkout/` | IsBuyerOrAdmin | Preview de checkout: precios congelados + verificacion de stock |
| GET | `/api/v1/cart/wishlist/` | IsAuthenticatedActiveUser | Lista favoritos del usuario |
| POST | `/api/v1/cart/wishlist/` | IsAuthenticatedActiveUser | Agrega producto a favoritos |
| DELETE | `/api/v1/cart/wishlist/{uuid}/` | IsAuthenticatedActiveUser | Elimina de favoritos (soft-delete) |

**[CORRECCION 2026-07-03]** El permiso real de `CartViewSet` es `IsBuyerOrAdmin` (requiere
`accounts.UserProfile.user_type` en `BUYER_TYPES`), no `IsAuthenticated` generico como decia este
documento -- ver `users/api/permissions.py`. Un usuario sin `UserProfile` recibe 403, no 401.

#### 5. **POST /api/v1/cart/update_item/** - Actualizar Cantidad (no documentado antes)
```
Body: { "variant_uuid": "...", "quantity": 5 }   # o service_variant_uuid
Response (200 OK): CartItemSerializer del item actualizado
Response (200 OK): {"detail": "Item eliminado del carrito."}   # si quantity <= 0
```
Delega a `CartCommands.update_item_quantity()`.

#### 6. **POST /api/v1/cart/checkout/** - Preview de Checkout (no documentado antes)
```
Body: (vacio)
Response (200 OK): payload de CartCommands.checkout_cart() -- ver seccion de Bugs Corregidos
```
Congela precios (con y sin impuestos via `PricingService`) y **valida stock real** antes de
mostrar el total al usuario. Es un preview de solo lectura -- la orden real se crea despues via
`POST /api/v1/orders/orders/create_from_cart/` (ver `orders/.AGENT/docs/ARQUITECTURA_COMPLETA_ORDERS.md`),
que vuelve a validar todo de forma independiente (no confia en este preview).

### WishlistViewSet — Detalle

**Clase:** `WishlistViewSet` en `cart/api/views.py`
**Router:** `router.register(r'wishlist', WishlistViewSet, basename='wishlist')`

#### GET /api/v1/cart/wishlist/
Retorna la lista de `WishlistItem` activos del usuario (no eliminados).

**Respuesta:**
```json
[
  {
    "uuid": "...",
    "product_name": "Alarma Paradox HD88",
    "sku": "ELEC-SKU-001",
    "price": "450000.00",
    "created_at": "2026-06-26T10:00:00Z"
  }
]
```

Los campos `product_name`, `sku`, `price` se leen desde `item.variant.product.name`, `item.variant.sku`, `item.variant.price`.

#### POST /api/v1/cart/wishlist/
Body: `{ "variant_uuid": "<uuid>" }`

Crea un `WishlistItem(user=request.user, variant=variant)`. Respeta la restriccion `unique_together(user, variant)` — retorna error si ya existe y no ha sido eliminado.

#### DELETE /api/v1/cart/wishlist/{uuid}/
**SOFT-DELETE** — no elimina fisicamente:
```python
item.is_deleted = True
item.save()
```

**IMPORTANTE:** No usar `.delete()` en WishlistItem. Usar siempre soft-delete.

### Detalle de Endpoints

#### 1. **GET /api/v1/cart/** - Listar Carrito
```
Headers:
Authorization: Bearer <access_token>

Response (200 OK):
{
    "id": 1,
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "items": [
        {
            "uuid": "550e8400-e29b-41d4-a716-446655440001",
            "variant": {
                "uuid": "550e8400-e29b-41d4-a716-446655440002",
                "sku": "PROD-001",
                "price": 29.99,
                "product": {
                    "uuid": "550e8400-e29b-41d4-a716-446655440003",
                    "name": "Producto A",
                    ...
                }
            },
            "service_variant": null,
            "quantity": 2,
            "total_price": 59.98,
            "created_at": "2026-05-14T10:00:00Z"
        },
        {
            "uuid": "550e8400-e29b-41d4-a716-446655440004",
            "variant": null,
            "service_variant": {
                "uuid": "550e8400-e29b-41d4-a716-446655440005",
                "sku": "SVC-001",
                "price": 99.99,
                "service": {
                    "uuid": "550e8400-e29b-41d4-a716-446655440006",
                    "name": "Servicio X",
                    ...
                }
            },
            "quantity": 1,
            "total_price": 99.99,
            "created_at": "2026-05-14T10:05:00Z"
        }
    ],
    "total_items": 3,
    "created_at": "2026-05-14T10:00:00Z"
}
```

**Validaciones**:
- Bearer token requerido y válido

**Información retornada**:
- Carrito con todos los items
- Detalles anidados de variantes (product/service)
- Total de items (suma de quantities)
- Timestamps

---

#### 2. **POST /api/v1/cart/add_item/** - Agregar Ítem
```
Headers:
Authorization: Bearer <access_token>
Content-Type: application/json

Request:
{
    "variant_uuid": "550e8400-e29b-41d4-a716-446655440002",
    "quantity": 3
}

O para servicios:
{
    "service_variant_uuid": "550e8400-e29b-41d4-a716-446655440005",
    "quantity": 1
}

Response (201 Created):
{
    "uuid": "550e8400-e29b-41d4-a716-446655440001",
    "variant": {
        "uuid": "550e8400-e29b-41d4-a716-446655440002",
        ...
    },
    "service_variant": null,
    "quantity": 3,
    "total_price": 89.97,
    "created_at": "2026-05-14T10:00:00Z"
}
```

**Validaciones**:
- Bearer token requerido
- `variant_uuid` O `service_variant_uuid` (exactamente uno)
- `quantity >= 1`
- Variante existe (404 si no)

**Comportamiento**:
- Si item ya existe en carrito: incrementa quantity
- Si item es nuevo: crea con quantity especificada

**Side Effects**:
- Crea CartItem si no existe
- Actualiza quantity si existe
- Retorna item actualizado

---

#### 3. **POST /api/v1/cart/clear/** - Vaciar Carrito
```
Headers:
Authorization: Bearer <access_token>

Request: (vacío)

Response (200 OK):
{
    "detail": "Carrito vaciado."
}
```

**Validaciones**:
- Bearer token requerido

**Comportamiento**:
- Elimina todos los CartItems
- Carrito queda vacío pero existe

**Side Effects**:
- Base de datos: DELETE FROM cart_cartitem WHERE cart_id = X

---

#### 4. **POST /api/v1/cart/remove-item/{item_uuid}/** - Eliminar Ítem
```
Headers:
Authorization: Bearer <access_token>

URL Parameters:
item_uuid: UUID del CartItem a eliminar

Response (200 OK):
{
    "detail": "Item eliminado."
}
```

**Validaciones**:
- Bearer token requerido
- CartItem existe y pertenece al carrito del usuario (404 si no)

**Comportamiento**:
- Elimina CartItem específico
- Otros items se mantienen

**Side Effects**:
- Base de datos: DELETE FROM cart_cartitem WHERE uuid = X

---

## Flujo de Datos

### Diagrama de Dependencias

```
┌─────────────────────────────────────────────────────┐
│                    Cliente REST                      │
│        (Frontend JS + Browser HTTP)                  │
└──────────────────────┬──────────────────────────────┘
                       │
            HTTP Request/Response
          (con JWT token en Authorization)
                       │
┌──────────────────────▼──────────────────────────────┐
│   urls.py → api/urls.py - Enrutador (DefaultRouter)│
│  Mapea GET/POST → CartViewSet methods               │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│    api/views.py - CartViewSet                       │
│  • list() → CartSelector.get_for_user()             │
│  • add_item() → CartCommands.add_item()             │
│  • clear() → CartCommands.clear_cart()              │
│  • remove_item() → CartItem.delete()                │
└──────────────────────┬──────────────────────────────┘
                       │
        Validación de Datos (Serializers)
         + Resolución de UUIDs → DB
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼──────────────┐    ┌────────▼──────────────┐
│ api/serializers.py   │    │ shop/services.py      │
│ • CartSerializer     │    │ • ProductVariant      │
│ • CartItemSer.       │    │ • Product             │
│ • AddCartItemSer.    │    │                       │
└──────────────────────┘    │ technical_services.py │
        │                    │ • ServiceVariant      │
        │                    │ • Service             │
        │                    └───────────────────────┘
        │ validated_data
        │
        ├──────────────────────┬──────────────────────┐
        │                      │                      │
┌───────▼──────────────┐  ┌────▼─────────────────┐  │
│ services/commands.py │  │ services/selectors.py│  │
│ CartCommands:        │  │ CartSelector:        │  │
│ • add_item()         │  │ • get_for_user()     │  │
│ • update_quantity()  │  │ • get_by_guest_id()  │  │
│ • remove_item()      │  │ • get_cart_queryset()│  │
│ • clear_cart()       │  │                      │  │
└───────┬──────────────┘  └────┬─────────────────┘  │
        │                      │                      │
        │ Lógica de negocio    │                      │
        │ (escritura, locks)   │                      │
        │                      │                      │
        ├──────────────────────┼──────────────────────┤
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   BD (via ORM)      │
                    │ • Cart              │
                    │ • CartItem          │
                    │ • ProductVariant    │
                    │ • ServiceVariant    │
                    │ • WishlistItem      │
                    └─────────────────────┘
```

### Flujo de Datos - Agregar Ítem (add_item)

```
1. Cliente envía POST /api/v1/cart/add_item/
   └─ Datos: variant_uuid, quantity (O service_variant_uuid)

2. urls.py → api/urls.py → DefaultRouter → CartViewSet.add_item()

3. IsAuthenticated (middleware): Valida JWT token
   └─ request.user se llena

4. AddCartItemSerializer valida:
   ├─ variant_uuid XOR service_variant_uuid (no ambos, no ninguno)
   ├─ quantity >= 1
   └─ Retorna validated_data

5. Views resuelve variantes (O-O logic):
   ├─ Si variant_uuid:
   │  └─ ProductVariant.objects.get(uuid=variant_uuid) → 404 si no existe
   ├─ Si service_variant_uuid:
   │  └─ ServiceVariant.objects.get(uuid=service_variant_uuid) → 404 si no existe
   └─ Obtiene: cart = CartSelector.get_for_user(request.user)

6. CartCommands.add_item(cart, variant, service_variant, quantity)
   ├─ BEGIN TRANSACTION (atomic)
   ├─ SELECT FOR UPDATE (lock pesimista)
   ├─ GET_OR_CREATE(cart, variant, service_variant)
   ├─ Si existe:
   │  ├─ item.quantity += quantity
   │  └─ item.save()
   ├─ Si es nuevo:
   │  └─ Crea CartItem con quantity
   └─ COMMIT TRANSACTION

7. CartItemSerializer serializa respuesta
   └─ Incluye detalles de variant (depth=1)

8. ViewSet retorna Response(data, status=201)

9. Cliente recibe item creado + 201 Created
```

### Flujo de Datos - Lista de Carrito (list)

```
1. Cliente envía GET /api/v1/cart/
   └─ Headers: Authorization: Bearer <token>

2. urls.py → api/urls.py → DefaultRouter → CartViewSet.list()

3. IsAuthenticated: Valida JWT token
   └─ request.user se llena

4. CartViewSet.get_cart():
   └─ CartSelector.get_for_user(request.user)
      ├─ Cart.objects.get_or_create(user=user)
      │  └─ Crea carrito si no existe
      ├─ PREFETCH RELATED:
      │  ├─ items__variant__product (1 query cada)
      │  └─ items__service_variant__service (1 query cada)
      └─ Retorna Cart con items precargados

5. CartSerializer(cart):
   ├─ Serializa Cart
   ├─ CartItemSerializer.many=True para items
   ├─ Para cada item:
   │  ├─ variant (nested, depth=1)
   │  └─ service_variant (nested, depth=1)
   ├─ Calcula total_items:
   │  └─ sum(item.quantity for item in items)
   └─ Retorna dict serializado

6. ViewSet retorna Response(data, status=200)

7. Cliente recibe carrito completo + 200 OK
```

---

## Patrones de Diseño

### 1. **Service Layer Pattern**
- **Commands**: Lógica de escritura + cambios de estado
- **Selectors**: Lógica de lectura + consultas optimizadas
- **Beneficio**: Testeable, reutilizable, separación de responsabilidades

### 2. **ViewSet Pattern (DRF)**
- Centraliza múltiples acciones en una sola clase
- Reutiliza routers automáticos
- Acción decorada con `@action` para funciones específicas
- No es ModelViewSet porque no hay CRUD estándar (session-based)

### 3. **Serializer Pattern (DRF)**
- **Validación** de entrada (AddCartItemSerializer)
- **Serialización** de salida (CartSerializer, CartItemSerializer)
- **Nesting**: CartSerializer anida CartItemSerializer
- **Depth**: depth=1 para relaciones simples

### 4. **Transacciones Atómicas**
- `@transaction.atomic` en operaciones críticas (add, update, delete)
- Rollback automático si algo falla
- Integridad de datos garantizada

### 5. **Locking Pesimista (select_for_update)**
- Bloquea fila en BD antes de leerla
- Previene race conditions (ej: dos clientes agregando mismo item simultáneamente)
- Garantiza que cantidad final sea correcta

### 6. **Optimización de Queries - Prefetch_related**
- Evita N+1 problema
- Trae relaciones en queries separadas (Python-side join)
- Mejor para relaciones reverse (items → product)

### 7. **Get-Or-Create Idempotencia**
- `get_or_create()` retorna (object, created_bool)
- Agregar mismo item 2 veces = incrementa cantidad
- Útil para operaciones idempotentes

### 8. **Polimorfismo Blando (Soft Polymorphism)**
- CartItem tiene variant O service_variant (no ambos)
- Validado en serializer y views
- XOR logic: exactamente uno debe ser null

---

## Características Especiales

### 1. **Carrito por Usuario + Invitado**
```python
class Cart(SintelBaseModel):
    user = ForeignKey(AUTH_USER_MODEL, null=True)      # Usuario registrado
    guest_id = UUIDField(null=True, db_index=True)     # Invitado anónimo
```

**Casos de uso**:
- **Usuario autenticado**: cart.user = usuario
- **Invitado sin login**: cart.guest_id = UUID temporal
- **Conversión**: Después de login, merge carrito invitado con usuario

**Flujo típico**:
```
1. Invitado añade items → Cart con guest_id
2. Invitado se registra → Crea cuenta
3. Merge: CartItem.objects.filter(cart__guest_id=old_id).update(cart=new_user_cart)
4. Carrito invitado ahora es del usuario
```

### 2. **Items Polimórficos (Producto O Servicio)**
```python
class CartItem(SintelBaseModel):
    variant = ForeignKey(ProductVariant, null=True)        # Producto
    service_variant = ForeignKey(ServiceVariant, null=True) # Servicio
```

**Ventaja**:
- Un carrito puede mezclar productos y servicios
- Mismo modelo, lógica unificada

**Restricción**:
```python
# Validación en AddCartItemSerializer
if not variant_uuid and not service_variant_uuid:
    raise ValidationError("...")
```

**Cálculo de precios**:
```python
def get_item_price(item):
    if item.variant:
        return item.variant.price * item.quantity
    else:
        return item.service_variant.price * item.quantity
```

### 3. **Wishlist Separada**
```python
class WishlistItem(SintelBaseModel):
    user = ForeignKey(AUTH_USER_MODEL)
    variant = ForeignKey(ProductVariant)
    
    class Meta:
        unique_together = ('user', 'variant')
```

**Características**:
- Solo productos (variant), no servicios
- Un usuario no puede guardar mismo producto 2 veces
- Separada del carrito

**Casos de uso**:
- Guardar para más tarde
- "Me gusta" / Favoritos
- Sugerencias basadas en wishlist

### 4. **Índices de BD**
```python
# Búsqueda rápida de carrito invitado
guest_id = UUIDField(null=True, blank=True, db_index=True)

# Unique constraint en wishlist
unique_together = ('user', 'variant')
```

---

## Notas Técnicas

### Dependencias Externas
- `djangorestframework`: REST API
- `drf-spectacular`: Documentación Swagger
- `django`: Framework web

### Configuración Requerida (settings.py)
```python
INSTALLED_APPS = [
    ...
    'rest_framework',
    'drf_spectacular',
    'cart',
    'shop',                    # Para ProductVariant
    'technical_services',      # Para ServiceVariant
    ...
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
}
```

### Integraciones
- **shop app**: ProductVariant, Product models
- **technical_services app**: ServiceVariant, Service models
- **users app**: AUTH_USER_MODEL

### Seguridad
- JWT authentication (IsAuthenticated en ViewSet)
- Validación XOR de variantes (un tipo u otro)
- Acceso controlado por usuario (get_cart() usa request.user)

### Performance
- Transacciones atómicas evitan inconsistencias
- select_for_update() previene race conditions
- prefetch_related() evita N+1 queries
- db_index en guest_id para búsquedas rápidas

### Consideraciones de Diseño
- **No hay precios en CartItem**: Se calculan en serializer desde variant.price
- **No hay descuentos**: Manejo separado en checkout/order
- **No hay historial**: CartItem se borra al comprar
- **Cantidades no negativas**: PositiveIntegerField + validación

---

## Mejoras Potenciales

1. ~~**Cálculo de Precios**~~ — Implementado: `CartItemSerializer` calcula `unit_price_with_tax`/
   `final_price` via `PricingService`, sin descuentos de cupon (esos se aplican en `orders`).

2. ~~**Stock Management**~~ — Implementado (`_check_availability()` en `add_item`/`update_item_quantity`,
   y validacion en `checkout_cart()`), via `InventorySelector.get_current_stock()`. Estuvo roto/deshabilitado
   entre un refactor incompleto y el 2026-07-03 -- ver "Bugs Corregidos" abajo. Sigue pendiente: reservar
   stock temporalmente mientras el item esta en el carrito (hoy solo se valida en el momento, no se reserva).

3. **Caducidad de Carrito**
   - Limpiar carritos invitados después de X días
   - Expiración de sesión

4. **Historial y Recuperación**
   - Guardar carritos abandonados
   - Sugerencias "Volviste a ver estos items"

5. **Optimizaciones Avanzadas**
   - Caché Redis para carritos
   - Actualización en tiempo real con WebSockets
   - Analytics: Items populares, carros abandonados

6. **Validación de Stock**
   ```python
   if not variant.in_stock or variant.quantity < item_quantity:
       raise ValidationError("Stock insuficiente")
   ```

---

## Conclusión

El módulo **cart** es un sistema flexible y robusto de carrito de compras que:

- ✅ **Polimórfico**: Soporta productos y servicios
- ✅ **Optimizado**: Prefetch_related, índices, transacciones
- ✅ **Seguro**: Locks pesimistas, validación XOR
- ✅ **Escalable**: Service layer desacoplado de views
- ✅ **Invitados**: Soporte para carritos anónimos
- ✅ **Testeable**: Servicios aislados sin dependencias HTTP
- ✅ **Extensible**: Fácil agregar nuevas features

El patron Service Layer + Selector/Commands permite reutilizar logica en checkout, ordenes, analytics y otros modulos sin duplicar codigo.

---

## Auditoria y Actualizaciones

### [2026-07-03] Bug critico: validacion de stock deshabilitada en carrito (regresion)

**Contexto:** al auditar `payment/` y `orders/` en la misma sesion se encontro el mismo patron de
refactor incompleto repetido tres veces ("desacoplar de `inventory` via un signal que nunca se
construyo"). Al revisar `cart/` por el mismo patron, se confirmo una cuarta instancia.

**Bug real encontrado:**
- `cart/services/commands.py::_check_availability()` para productos fisicos siempre retornaba
  `9999` (hardcodeado), con el comentario *"Inventario gestionado desde inventory/ app — se asume
  stock disponible"*. Efecto: **se podia agregar cualquier cantidad de un producto sin stock al
  carrito**, sin ningun aviso.
- `cart/services/commands.py::checkout_cart()` ya no validaba `item.quantity > stock` para
  productos antes de generar el preview de checkout.
- `cart/tests.py` estaba **roto de verdad**: tenia el import de `StockRecord`/`InventoryTransaction`
  comentado (`# INVENTORY_REMOVED: ...`) pero el `setUp()` seguia usando esas clases -- los 5 tests
  fallaban con `NameError` antes de correr, confirmado ejecutando la suite en el contenedor Docker.

**Riesgo real:** ninguno de sobreventa en BD -- el guardian final
(`InventoryCommands.register_exit()` -> `InventoryKardex.validate_stock_availability()`, verificado
y ya cubierto por tests esta misma sesion) segia intacto y sigue disparando al confirmar el pago
(Wompi/Nequi) o al crear la orden COD. El riesgo era de **UX**: un cliente podia armar un carrito
entero con productos sin stock y solo enterarse muy tarde, con un error generico al pagar.

**Corregido:**
- `_check_availability()`: restaurada la consulta real via `InventorySelector.get_current_stock(variant)`.
- `checkout_cart()`: restaurada la validacion de stock para productos antes de calcular precios.
- `cart/tests.py`: restaurado el import real de `StockRecord`/`InventoryTransaction`; se agrego ademas
  `UserProfile(user_type='CUSTOMER')` al usuario de test (el permiso real `IsBuyerOrAdmin` lo requiere
  y no existia en el test, causando un 403 adicional una vez arreglado el `NameError`).
- Eliminados `cart/services/commands.py.bak` y `cart/tests.py.bak` (ya superados).
- Suite verificada en el contenedor real: 5/5 tests en verde.

**Regla derivada:** mismo patron de las auditorias de `payment/` y `orders/` -- un comentario
`# INVENTORY_REMOVED: ... -> usar signal` en este proyecto historicamente NO significa que exista un
reemplazo funcional. Antes de confiar en ese comentario, verificar que el signal/API prometido
realmente exista.

### [2026-06] WishlistViewSet — Customer Dashboard

- **Agregado** `WishlistViewSet` en `cart/api/views.py` con acciones `list`, `create`, `destroy`.
- **Registrado** en `cart/api/urls.py`: `router.register(r'wishlist', WishlistViewSet, basename='wishlist')`.
- **Permiso:** `IsAuthenticatedActiveUser` (de `users.api.permissions`) — NO `IsAuthenticated` standard.
- **Soft-delete** en `destroy`: `item.is_deleted = True; item.save()` — nunca `.delete()` fisico.
- **Serializacion inline** en `list()` — no requiere serializador separado.
- **Frontend:** `CustomerWishlistView.vue` en `/mi-cuenta/wishlist`.
