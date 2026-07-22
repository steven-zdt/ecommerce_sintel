# ARQUITECTURA COMPLETA - MÓDULO INVENTORY

## 📋 Descripción General

El módulo **Inventory** es el sistema central de gestión de stock y movimientos de inventario en la plataforma Sintel E-Commerce. 

**Responsabilidades principales:**
- Mantener un registro maestro de stock (StockRecord) para todos los artículos vendibles (ProductVariant, EquipmentVariant, ServiceVariant)
- Registrar transacciones de movimiento (ENTRY/EXIT/RESERVE) con trazabilidad completa
- Proporcionar vistas read-only para consulta de movimientos y saldos
- Permitir ajustes manuales de stock desde el dashboard administrativo
- Calcular balances en tiempo real usando patrones Kardex (entrada/salida)

---

## 📁 Estructura de Directorios

```
inventory/
├── __init__.py
├── apps.py                          # Configuración de la app
├── models.py                        # StockRecord, InventoryTransaction
├── urls.py                          # Router raíz del módulo
│
├── api/
│   ├── __init__.py
│   ├── views.py                     # StockRecordViewSet, InventoryTransactionViewSet
│   ├── serializers.py               # Serializadores de entrada/salida
│   └── urls.py                      # Router REST con endpoints
│
├── services/
│   ├── __init__.py                  # Exports: Commands, Selectors, Kardex
│   ├── commands.py                  # InventoryCommands (write operations)
│   ├── selectors.py                 # Selectores (read operations)
│   └── kardex.py                    # Lógica matemática pura de cálculos
│
└── migrations/
    ├── __init__.py
    ├── 0001_initial.py              # Creación inicial de modelos
    └── 0002_stockrecord_and_more.py  # Ajustes y campos adicionales
```

---

## 🏗️ Diagramas de Arquitectura

### Flujo de Capas (Layered Architecture)

```
┌─────────────────────────────────────────────────────────┐
│  CLIENTE (Dashboard Admin / API Consumer)                │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼──────────────┐
         │   REST API (DRF)         │
         │  ViewSets + Routers      │
         └───────────┬──────────────┘
                     │
         ┌───────────▼──────────────────────────┐
         │   API Layer (api/views.py)           │
         │  - StockRecordViewSet                │
         │  - InventoryTransactionViewSet       │
         └───────────┬──────────────────────────┘
                     │
         ┌───────────▼──────────────────────────┐
         │  Serializers (api/serializers.py)    │
         │  - StockRecordSerializer             │
         │  - InventoryTransactionSerializer    │
         │  - StockAdjustmentInputSerializer    │
         └───────────┬──────────────────────────┘
                     │
         ┌───────────▼──────────────────────────────────┐
         │   Business Logic Layer (services/)           │
         │  ┌────────────────────────────────────────┐  │
         │  │ InventoryCommands                      │  │
         │  │ - register_entry()                     │  │
         │  │ - register_exit()                      │  │
         │  └────────────────────────────────────────┘  │
         │  ┌────────────────────────────────────────┐  │
         │  │ Selectors (read-only queries)          │  │
         │  │ - StockRecordSelector                  │  │
         │  │ - InventorySelector                    │  │
         │  └────────────────────────────────────────┘  │
         │  ┌────────────────────────────────────────┐  │
         │  │ InventoryKardex (Pure Functions)       │  │
         │  │ - calculate_new_balance()              │  │
         │  │ - validate_stock_availability()        │  │
         │  └────────────────────────────────────────┘  │
         └───────────┬──────────────────────────────────┘
                     │
         ┌───────────▼──────────────────────────┐
         │   ORM Layer (Django Models)          │
         │  - StockRecord (master record)       │
         │  - InventoryTransaction (audit log)  │
         └───────────┬──────────────────────────┘
                     │
         ┌───────────▼──────────────────────────┐
         │   Database (PostgreSQL)              │
         │  Tables: inventory_stockrecord       │
         │          inventory_inventorytransaction
         └──────────────────────────────────────┘
```

### Flujo de Registro de Movimiento (Entry/Exit)

```
┌─────────────────────────────────────────────────┐
│  API Request: POST /api/v1/inventory/stock-records/UUID/adjust_stock/
└────────┬────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  StockRecordViewSet.adjust_stock()       │
│  - Obtiene el stock_record por UUID      │
│  - Valida serializer (mov_type, qty)     │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Determina tipo de movimiento            │
│  - ENTRY: compra/restock                 │
│  - EXIT: venta/ajuste negativo           │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  InventoryCommands.register_entry() o            │
│  InventoryCommands.register_exit()               │
│  @transaction.atomic (ACID garantizado)          │
│                                                  │
│  1. InventorySelector.get_current_stock()       │
│     → Lee balance_after más reciente             │
│                                                  │
│  2. InventoryKardex.validate_stock_availability() │
│     (solo para EXIT: validar suficiencia)        │
│                                                  │
│  3. InventoryKardex.calculate_new_balance()     │
│     → Calcula nuevo saldo (±qty)                 │
│                                                  │
│  4. InventoryTransaction.objects.create()       │
│     → Registra transacción en audit log          │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Response: 201 Created                   │
│  {                                       │
│    "uuid": "...",                       │
│    "movement_type": "ENTRY",             │
│    "quantity": 50,                       │
│    "balance_after": 150,                 │
│    "reference": "Manual adjustment...",  │
│    "created_at": "2026-05-14T..."       │
│  }                                       │
└──────────────────────────────────────────┘
```

### Flujo de Lectura de Movimientos (Movements List)

```
┌──────────────────────────────────────────────────┐
│  API Request: GET /api/v1/inventory/stock-records/UUID/movements/
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  StockRecordViewSet.movements()          │
│  - Obtiene stock_record por UUID         │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────┐
│  InventorySelector.list_movements()              │
│                                                  │
│  SELECT * FROM inventory_inventorytransaction   │
│  WHERE stock_record_id = ?                       │
│  ORDER BY created_at DESC                        │
│                                                  │
│  Optimization: .only() para reducir campos       │
└────────┬─────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Paginate QuerySet                       │
│  (PAGE_SIZE = 20 por defecto)            │
└────────┬─────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  Serialize to JSON                       │
│  InventoryTransactionSerializer(many=True)
└────────┬─────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────┐
│  Response: 200 OK (Paginated List)              │
│  {                                             │
│    "count": 127,                               │
│    "next": "/api/v1/inventory/stock-records/...",
│    "previous": null,                           │
│    "results": [                                │
│      {                                         │
│        "uuid": "...",                         │
│        "movement_type": "ENTRY",               │
│        "quantity": 50,                         │
│        "balance_after": 150,                   │
│        "reference": "Purchase Order #123",     │
│        "created_at": "2026-05-14T10:30:00Z"   │
│      },                                        │
│      ...más transacciones...                  │
│    ]                                           │
│  }                                             │
└────────────────────────────────────────────────┘
```

### Gestión de GenericForeignKey para Items Vendibles

```
StockRecord (Master Record)
│
├─ content_type = ContentType para ProductVariant
├─ object_id = UUID del ProductVariant específico
├─ item_variant = GenericForeignKey ("content_type", "object_id")
│
├─ content_type = ContentType para EquipmentVariant
├─ object_id = UUID del EquipmentVariant específico
├─ item_variant = GenericForeignKey ("content_type", "object_id")
│
└─ content_type = ContentType para ServiceVariant
   ├─ object_id = UUID del ServiceVariant específico
   └─ item_variant = GenericForeignKey ("content_type", "object_id")

Beneficio: Un único StockRecord maneja stock para cualquier tipo
de artículo sin necesidad de múltiples modelos especializados.
```

---

## 📄 Descripción Detallada de Archivos

### `models.py` — Modelos de Dominio

#### **StockRecord (Master Record)**

```python
class StockRecord(SintelBaseModel):
    """
    MASTER RECORD: Acts as the core anchor for any item that can be 
    sold, rented, or quoted in the Sintel platform.
    """
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    item_variant = GenericForeignKey('content_type', 'object_id')
    
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
```

**Responsabilidades:**
- Mantiene un registro maestro único por cada variante de producto/equipo/servicio
- `content_type` + `object_id` + `GenericForeignKey`: Permite referenciar diferentes tipos de items (ProductVariant, EquipmentVariant, ServiceVariant) sin redundancia de código
- `sku` (Stock Keeping Unit): Identificador único global para consultas rápidas
- `stock`: Campo desnormalizado que se lee para vista rápida (aunque la fuente de verdad es InventoryTransaction.balance_after más reciente)
- `is_active` / `is_deleted`: Control de activación y borrado lógico

**Índices:**
- `(content_type, object_id)`: Búsquedas rápidas por item_variant
- `sku`: Búsquedas por código de artículo

**Heredado de SintelBaseModel:**
- `uuid`: Identificador único global UUID (read: UUID4, no integers)
- `created_at`, `updated_at`: Timestamps automáticos

#### **InventoryTransaction (Audit Log / Kardex)**

```python
class InventoryTransaction(SintelBaseModel):
    MOVEMENT_TYPES = (
        ('ENTRY', 'Entry (Purchase/Restock)'),
        ('EXIT', 'Exit (Sale/Adjustment)'),
        ('RESERVE', 'Reserve (Quote)'),
    )
    
    stock_record = models.ForeignKey(StockRecord, related_name='transactions')
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES)
    quantity = models.PositiveIntegerField()
    balance_after = models.IntegerField()
    reference = models.CharField(max_length=255, blank=True)
```

**Responsabilidades:**
- Registra CADA movimiento de stock con trazabilidad completa
- `balance_after`: Campo crucial que almacena el saldo tras esta transacción (permite reconstruir histórico sin cálculos)
- `reference`: Contexto (ej: "Purchase Order #123", "Sale Order #456", "Manual adjustment via API")
- `movement_type`: Clasificación para análisis y auditoría

**Diseño Immutable:**
- Las transacciones nunca se editan, solo se crean (append-only log)
- Garantiza integridad del histórico

**Ordenamiento:**
- `ordering = ['-created_at']`: Más recientes primero

---

### `api/views.py` — API REST Endpoints

#### **StockRecordViewSet**

```python
class StockRecordViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = StockRecordSelector.list_all_for_admin()
    serializer_class = StockRecordSerializer
    lookup_field = 'uuid'
```

**Tipo:** ReadOnlyModelViewSet (solo GET, no POST/PUT/DELETE en listado)

**Acciones implementadas:**

1. **list()** (heredado)
   - GET `/api/v1/inventory/stock-records/`
   - Retorna todos los StockRecords paginados
   - Usa `StockRecordSelector.list_all_for_admin()` para queryset optimizado

2. **retrieve()** (heredado)
   - GET `/api/v1/inventory/stock-records/{uuid}/`
   - Retorna un StockRecord específico por UUID

3. **movements()** (custom action)
   ```python
   @action(detail=True, methods=['get'])
   def movements(self, request, uuid=None):
   ```
   - GET `/api/v1/inventory/stock-records/{uuid}/movements/`
   - Retorna histórico de transacciones para un StockRecord
   - Paginado con PAGE_SIZE = 20

4. **adjust_stock()** (custom action - POST)
   ```python
   @action(detail=True, methods=['post'])
   def adjust_stock(self, request, uuid=None):
   ```
   - POST `/api/v1/inventory/stock-records/{uuid}/adjust_stock/`
   - Registra ajuste manual de stock (ENTRY o EXIT)
   - Valida serializer `StockAdjustmentInputSerializer`
   - Delega lógica a `InventoryCommands.register_entry()` o `register_exit()`
   - Retorna 201 Created con transacción creada

#### **InventoryTransactionViewSet**

```python
class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryTransaction.objects.all().order_by('-created_at')
    serializer_class = InventoryTransactionSerializer
    lookup_field = 'uuid'
```

**Tipo:** ReadOnlyModelViewSet (solo lectura)

**Acciones:**
1. **list()** - GET `/api/v1/inventory/transactions/`
2. **retrieve()** - GET `/api/v1/inventory/transactions/{uuid}/`

**Propósito:** Vista global de todas las transacciones de inventario (sin filtrar por StockRecord)

---

### `api/serializers.py` — Serializadores de Entrada/Salida

#### **StockRecordSerializer** (Output)

```python
class StockRecordSerializer(serializers.ModelSerializer):
    fields = ['id', 'uuid', 'sku', 'stock', 'is_active', 'created_at', 'updated_at']
    read_only_fields = fields
```

**Propósito:** Serialización de StockRecord para respuestas API

**Campos:**
- `id`: Primary key (integer)
- `uuid`: Identificador único global
- `sku`: Código de artículo
- `stock`: Cantidad en stock (desnormalizada)
- `is_active`: Indica si está activo
- `created_at`, `updated_at`: Timestamps

**Nota:** No incluye `item_variant` (GenericForeignKey) porque es complejo de serializar; se maneja a nivel de aplicación.

#### **InventoryTransactionSerializer** (Output)

```python
class InventoryTransactionSerializer(serializers.ModelSerializer):
    fields = ['id', 'uuid', 'movement_type', 'quantity', 'balance_after', 'reference', 'created_at']
    read_only_fields = fields
```

**Propósito:** Serialización de transacciones para respuestas API

**Campos:**
- `movement_type`: ENTRY, EXIT, o RESERVE
- `quantity`: Cantidad movida
- `balance_after`: Saldo resultante tras la transacción
- `reference`: Contexto de la transacción

#### **StockAdjustmentInputSerializer** (Input)

```python
class StockAdjustmentInputSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(choices=['ENTRY', 'EXIT'])
    quantity = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(max_length=255, required=False)
```

**Propósito:** Validación de ajustes manuales de stock desde el dashboard

**Validaciones:**
- `movement_type`: Solo ENTRY o EXIT (no RESERVE manual)
- `quantity`: Entero positivo (min_value=1)
- `reference`: Opcional, hasta 255 caracteres

---

### `api/urls.py` — Enrutamiento REST

```python
router = DefaultRouter()
router.register(r'stock-records', StockRecordViewSet, basename='stock-record')
router.register(r'transactions', InventoryTransactionViewSet, basename='inventory-transaction')

urlpatterns = [path('', include(router.urls))]
```

**Endpoints generados:**

| Método | Ruta | Acción | Propósito |
|--------|------|--------|-----------|
| GET | `/api/v1/inventory/stock-records/` | list | Listar todos los StockRecords |
| GET | `/api/v1/inventory/stock-records/{uuid}/` | retrieve | Obtener StockRecord específico |
| GET | `/api/v1/inventory/stock-records/{uuid}/movements/` | movements | Histórico de movimientos |
| POST | `/api/v1/inventory/stock-records/{uuid}/adjust_stock/` | adjust_stock | Registrar ajuste manual |
| GET | `/api/v1/inventory/transactions/` | list | Listar todas las transacciones |
| GET | `/api/v1/inventory/transactions/{uuid}/` | retrieve | Obtener transacción específica |

---

### `urls.py` — Router del Módulo

```python
from django.urls import path, include

urlpatterns = [
    path('', include('inventory.api.urls')),
]
```

**Propósito:** Incluir las rutas de `api/urls.py` bajo el prefijo `/api/v1/inventory/` (configurado en `ecommerce/urls.py`)

---

### `services/commands.py` — Operaciones de Escritura (Write)

#### **InventoryCommands**

Patrón de Comando: Clase con métodos estáticos para operaciones de escritura/modificación

#### **register_entry(stock_record, quantity, reference)**

```python
@staticmethod
@transaction.atomic
def register_entry(stock_record: StockRecord, quantity: int, reference: str = "") -> InventoryTransaction:
    """
    Register a stock entry (purchase/restock).
    """
    current = InventorySelector.get_current_stock(stock_record.pk)
    new_balance = InventoryKardex.calculate_new_balance(current, 'ENTRY', quantity)
    tx = InventoryTransaction.objects.create(
        stock_record=stock_record,
        movement_type='ENTRY',
        quantity=quantity,
        balance_after=new_balance,
        reference=reference,
    )
    logger.info("[inventory:register_entry] SKU=%s qty=%s new_balance=%s", stock_record.sku, quantity, new_balance)
    return tx
```

**Responsabilidades:**
1. Obtiene el saldo actual del StockRecord
2. Calcula nuevo balance (actual + cantidad)
3. Crea transacción en la base de datos
4. Registra en logs

**ACID Guarantee:**
- `@transaction.atomic`: Si algo falla, rollback completo

**Casos de uso:**
- Entrada de compra a proveedores
- Restock desde bodega central
- Ajustes positivos del inventario

#### **register_exit(stock_record, quantity, reference)**

```python
@staticmethod
@transaction.atomic
def register_exit(stock_record: StockRecord, quantity: int, reference: str = "") -> InventoryTransaction:
    """
    Register a stock exit (sale/adjustment).
    Raises: ValidationError if stock insufficient
    """
    current = InventorySelector.get_current_stock(stock_record.pk)
    InventoryKardex.validate_stock_availability(current, quantity)  # Valida antes de crear
    new_balance = InventoryKardex.calculate_new_balance(current, 'EXIT', quantity)
    tx = InventoryTransaction.objects.create(
        stock_record=stock_record,
        movement_type='EXIT',
        quantity=quantity,
        balance_after=new_balance,
        reference=reference,
    )
    logger.info("[inventory:register_exit] SKU=%s qty=%s new_balance=%s", stock_record.sku, quantity, new_balance)
    return tx
```

**Diferencia clave con ENTRY:**
- `InventoryKardex.validate_stock_availability(current, quantity)`: Valida que haya suficiente stock
- Lanza `ValidationError` si stock insuficiente (previene overselling)

**Casos de uso:**
- Venta de productos
- Retiro de artículos vendidos
- Ajustes negativos por merma/daño

---

### `services/selectors.py` — Operaciones de Lectura (Read-Only)

#### **StockRecordSelector**

Patrón Selector: Clase con métodos estáticos para consultas optimizadas

```python
class StockRecordSelector:
    LIST_FIELDS = ('id', 'uuid', 'sku', 'stock', 'is_active', 'created_at')
    DETAIL_FIELDS = LIST_FIELDS + ('content_type', 'object_id')

    @staticmethod
    def list_all_active() -> QuerySet:
        """Returns all active stock records optimized."""
        return StockRecord.objects.filter(is_active=True)

    @staticmethod
    def list_all_for_admin() -> QuerySet:
        """Returns all stock records (including inactive) optimized."""
        return StockRecord.objects.all()

    @staticmethod
    def get_by_uuid(uuid: str) -> StockRecord:
        return StockRecord.objects.get(uuid=uuid)
```

**Métodos:**

| Método | Propósito | Retorna |
|--------|-----------|---------|
| `list_all_active()` | Listar solo registros activos (para frontend) | QuerySet |
| `list_all_for_admin()` | Listar todos incluyendo inactivos (para admin) | QuerySet |
| `get_by_uuid(uuid)` | Obtener StockRecord específico | StockRecord |

#### **InventorySelector**

```python
class InventorySelector:
    LIST_FIELDS = ('id', 'uuid', 'stock_record_id', 'movement_type', 'quantity', 'balance_after', 'reference', 'created_at')

    @staticmethod
    def get_current_stock(stock_record_id: int) -> int:
        """Returns the last balance_after for a StockRecord or 0 if no transactions exist."""
        last_tx = (
            InventoryTransaction.objects
            .filter(stock_record_id=stock_record_id)
            .only('balance_after')
            .order_by('-created_at')
            .first()
        )
        return last_tx.balance_after if last_tx else 0

    @staticmethod
    def list_movements(stock_record_id: int) -> QuerySet:
        """Returns all movements for a StockRecord optimized with only()."""
        return (
            InventoryTransaction.objects
            .filter(stock_record_id=stock_record_id)
            .only(*InventorySelector.LIST_FIELDS)
            .order_by('-created_at')
        )
```

**Métodos:**

1. **get_current_stock(stock_record_id)**
   - Retorna el saldo actual (integer)
   - Lógica: Lee el `balance_after` de la transacción más reciente
   - Si no hay transacciones, retorna 0
   - Optimization: `.only('balance_after')` reduce campos innecesarios

2. **list_movements(stock_record_id)**
   - Retorna QuerySet de todas las transacciones para un StockRecord
   - Ordenado por `-created_at` (más recientes primero)
   - Optimization: `.only()` limita campos para reducir memoria

---

### `services/kardex.py` — Lógica Matemática Pura

```python
class InventoryKardex:
    """Mathematical logic for stock calculation (pure functions)"""
    
    @staticmethod
    def calculate_new_balance(current_balance: int, movement_type: str, quantity: int) -> int:
        if movement_type == 'ENTRY':
            return current_balance + quantity
        elif movement_type == 'EXIT':
            return current_balance - quantity
        raise ValueError("Invalid movement type")

    @staticmethod
    def validate_stock_availability(current_balance: int, requested_quantity: int):
        if current_balance < requested_quantity:
            raise ValidationError(
                f"Insufficient stock. Available: {current_balance}, Requested: {requested_quantity}"
            )
```

**Responsabilidades:**
- Cálculo puro de balances (sin efectos secundarios, sin BD)
- Validación de disponibilidad

**Métodos:**

1. **calculate_new_balance(current, movement_type, quantity)**
   - ENTRY: `current + quantity`
   - EXIT: `current - quantity`
   - Pure function (sin I/O)

2. **validate_stock_availability(current, requested)**
   - Lanza `ValidationError` si `current < requested`
   - Usada en `register_exit()` antes de crear la transacción

**Patrón:**
- Funciones puras (idempotentes, sin estado)
- Fáciles de testear
- Pueden ser llamadas sin miedo a side effects

---

### `services/__init__.py` — Exports del Módulo de Servicios

```python
from .selectors import StockRecordSelector, InventorySelector
from .commands import InventoryCommands

__all__ = [
    'StockRecordSelector',
    'InventorySelector',
    'InventoryCommands',
]
```

**Propósito:**
- Facilita imports: `from inventory.services import InventoryCommands`
- Encapsula implementación interna (kardex no se exporta)

---

### `apps.py` — Configuración de la App

```python
from django.apps import AppConfig

class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
```

**Configuración:**
- `default_auto_field`: Usa BigAutoField para primary keys (más escalable que AutoField)
- `name`: Nombre canónico de la app ('inventory')

---

## 🔄 Flujos de Casos de Uso

### Caso 1: Registrar Entrada de Mercancía (Purchase Order)

```
Admin crea orden de compra en dashboard
  ↓
Frontend: POST /api/v1/inventory/stock-records/{sku}/adjust_stock/
  Body: {"movement_type": "ENTRY", "quantity": 100, "reference": "PO #2024001"}
  ↓
StockRecordViewSet.adjust_stock()
  ↓
InventoryCommands.register_entry(stock_record, 100, "PO #2024001")
  ↓
@transaction.atomic
  1. current_balance = 50 (desde última transacción)
  2. new_balance = 50 + 100 = 150
  3. INSERT InventoryTransaction(movement_type='ENTRY', qty=100, balance_after=150)
  ↓
Response: 201 Created
{
  "uuid": "abc123...",
  "movement_type": "ENTRY",
  "quantity": 100,
  "balance_after": 150,
  "reference": "PO #2024001",
  "created_at": "2026-05-14T10:30:00Z"
}
```

### Caso 2: Registrar Salida por Venta

```
Cliente realiza compra en tienda
  ↓
Sistema crea Order y CartItems
  ↓
Frontend: POST /api/v1/inventory/stock-records/{sku}/adjust_stock/
  Body: {"movement_type": "EXIT", "quantity": 5, "reference": "Sale Order #SO2024001"}
  ↓
StockRecordViewSet.adjust_stock()
  ↓
InventoryCommands.register_exit(stock_record, 5, "Sale Order #SO2024001")
  ↓
@transaction.atomic
  1. current_balance = 150
  2. validate_stock_availability(150, 5) → OK (150 >= 5)
  3. new_balance = 150 - 5 = 145
  4. INSERT InventoryTransaction(movement_type='EXIT', qty=5, balance_after=145)
  ↓
Response: 201 Created
{
  "uuid": "def456...",
  "movement_type": "EXIT",
  "quantity": 5,
  "balance_after": 145,
  "reference": "Sale Order #SO2024001",
  "created_at": "2026-05-14T11:00:00Z"
}
```

### Caso 3: Consultar Histórico de Movimientos

```
Admin abre Stock detail en dashboard
  ↓
Frontend: GET /api/v1/inventory/stock-records/{uuid}/movements/
  ↓
StockRecordViewSet.movements()
  ↓
InventorySelector.list_movements(stock_record_id)
  ↓
SELECT * FROM inventory_inventorytransaction
  WHERE stock_record_id = {id}
  ORDER BY created_at DESC
  LIMIT 20 OFFSET 0
  ↓
Serialize to JSON → InventoryTransactionSerializer(many=True)
  ↓
Response: 200 OK
{
  "count": 127,
  "next": "/api/v1/inventory/stock-records/.../movements/?page=2",
  "previous": null,
  "results": [
    {
      "uuid": "def456...",
      "movement_type": "EXIT",
      "quantity": 5,
      "balance_after": 145,
      "reference": "Sale Order #SO2024001",
      "created_at": "2026-05-14T11:00:00Z"
    },
    {
      "uuid": "abc123...",
      "movement_type": "ENTRY",
      "quantity": 100,
      "balance_after": 150,
      "reference": "PO #2024001",
      "created_at": "2026-05-14T10:30:00Z"
    },
    ... más transacciones ...
  ]
}
```

---

## 🏗️ Patrones de Diseño Utilizados

### 1. **Service Layer Pattern**
- **Commands**: Operaciones de escritura/mutación (CQRS principle)
- **Selectors**: Operaciones de lectura (CQRS principle)
- **Kardex**: Lógica de negocio pura (sin I/O)

**Beneficio:** Separación clara de responsabilidades, fácil de testear

### 2. **Generic Foreign Key (Polymorphism)**

```python
content_type = models.ForeignKey(ContentType)
object_id = models.UUIDField()
item_variant = GenericForeignKey('content_type', 'object_id')
```

**Caso de uso:** Un StockRecord puede apuntar a ProductVariant, EquipmentVariant, o ServiceVariant

**Beneficio:** Reutilización de código, evita tres modelos redundantes

**Trade-off:** GenericForeignKey no es verdadera relación en BD (sin constraint), requiere validación en aplicación

### 3. **Append-Only Audit Log**

```python
class InventoryTransaction:
    # Nunca se edita, solo se crea (immutable)
```

**Beneficio:** 
- Integridad histórica garantizada
- Auditabilidad completa
- Reconstrucción de estado en cualquier momento

### 4. **Denormalization para Lectura Rápida**

```python
class StockRecord:
    stock = models.PositiveIntegerField()  # Desnormalizado
```

**Propósito:** Lectura rápida del saldo actual

**Nota:** La fuente de verdad es `InventoryTransaction.balance_after`, no `StockRecord.stock`

### 5. **Read-Only ViewSets**

```python
class StockRecordViewSet(viewsets.ReadOnlyModelViewSet):
    # Solo GET, no POST/PUT/DELETE en listado
    # Las escrituras pasan por custom actions (adjust_stock)
```

**Beneficio:** Controla qué operaciones están permitidas, previene mutaciones no autorizadas

### 6. **Pagination**

```python
DEFAULT_PAGINATION_CLASS = 'rest_framework.pagination.PageNumberPagination'
PAGE_SIZE = 20
```

**Propósito:** Limita resultados por página, permite browsing de datos grandes

---

## ⚡ Consideraciones de Rendimiento

### 1. **Lectura del Saldo Actual**
```python
def get_current_stock(stock_record_id: int) -> int:
    last_tx = InventoryTransaction.objects.filter(...).order_by('-created_at').first()
    return last_tx.balance_after if last_tx else 0
```

**Optimización:** `.only('balance_after')` reduce bytes transmitidos desde BD

**Complejidad:** O(1) (índice en `created_at` en `InventoryTransaction`)

### 2. **Índices en Base de Datos**

```python
class StockRecord:
    indexes = [
        models.Index(fields=['content_type', 'object_id']),  # Para GenericFK lookup
        models.Index(fields=['sku']),  # Para búsqueda por código
    ]
    
    sku = CharField(unique=True, db_index=True)  # Índice único
```

**Beneficio:** Búsquedas por SKU y GenericFK en O(log n) en lugar de O(n)

### 3. **Transactions Atómicas**

```python
@transaction.atomic
def register_entry(...):
    current = get_current_stock(...)
    new_balance = calculate_new_balance(...)
    tx = InventoryTransaction.objects.create(...)
```

**Propósito:** Garantiza consistencia bajo concurrencia

**Nota:** No hay pessimistic locking (select_for_update), por lo que bajo ALTA concurrencia podrían haber race conditions. Solución: agregar `stock_record = StockRecord.objects.select_for_update().get(...)`

### 4. **Campos `.only()` en QuerySets**

```python
InventoryTransaction.objects.filter(...).only('balance_after').first()
```

**Beneficio:** Reduce columnas SELECT, menor memoria

---

## 🔐 Validaciones y Seguridad

### 1. **Validación de Cantidades**
```python
class StockAdjustmentInputSerializer:
    quantity = serializers.IntegerField(min_value=1)
```

**Propósito:** Previene cantidades negativas o cero desde API

### 2. **Validación de Stock Suficiente**
```python
def validate_stock_availability(current, requested):
    if current < requested:
        raise ValidationError(...)
```

**Propósito:** Previene overselling (vender más de lo que hay en stock)

### 3. **Transacciones Atómicas**
```python
@transaction.atomic
def register_exit(...):
    # Si anything falla, rollback
```

**Propósito:** Previene estados inconsistentes (ej: registrar venta sin actualizar transacción)

### 4. **GenericForeignKey Validation**
```python
item_variant = GenericForeignKey('content_type', 'object_id')
```

**Nota:** Django NO valida automáticamente que `object_id` realmente exista en la tabla ContentType. Recomendación: Agregar signal para validar en creación.

---

## 📊 Ejemplo Completo: Registrar una Venta

```python
# 1. Frontend hace request
POST /api/v1/inventory/stock-records/550e8400-e29b-41d4-a716-446655440000/adjust_stock/
{
    "movement_type": "EXIT",
    "quantity": 3,
    "reference": "Order #ORD-2024-001"
}

# 2. StockRecordViewSet.adjust_stock() recibe request
def adjust_stock(self, request, uuid=None):
    stock_record = self.get_object()  # Busca por UUID
    serializer = StockAdjustmentInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    movement_type = 'EXIT'
    quantity = 3
    reference = 'Order #ORD-2024-001'
    
    # 3. Llama a InventoryCommands.register_exit()
    tx = InventoryCommands.register_exit(
        stock_record=stock_record,
        quantity=quantity,
        reference=reference
    )
    
    # 4. register_exit() transaccionalmente:
    #    a) current = InventorySelector.get_current_stock(stock_record.pk)
    #       → Query: SELECT balance_after FROM inventory_inventorytransaction 
    #                WHERE stock_record_id = X ORDER BY created_at DESC LIMIT 1
    #       → Resultado: 50
    #
    #    b) InventoryKardex.validate_stock_availability(50, 3)
    #       → 50 >= 3? SÍ, continúa
    #
    #    c) new_balance = InventoryKardex.calculate_new_balance(50, 'EXIT', 3)
    #       → 50 - 3 = 47
    #
    #    d) InventoryTransaction.objects.create(
    #           stock_record=stock_record,
    #           movement_type='EXIT',
    #           quantity=3,
    #           balance_after=47,
    #           reference='Order #ORD-2024-001'
    #       )
    #       → INSERT inventory_inventorytransaction (...)
    #
    # 5. Si todo OK, retorna transacción creada
    
    # 6. InventoryTransactionSerializer serializa el resultado
    output_serializer = InventoryTransactionSerializer(tx)
    return Response(output_serializer.data, status=status.HTTP_201_CREATED)
    
# 7. Respuesta al cliente
{
    "uuid": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "movement_type": "EXIT",
    "quantity": 3,
    "balance_after": 47,
    "reference": "Order #ORD-2024-001",
    "created_at": "2026-05-14T12:34:56Z"
}
```

---

## 🚀 Mejoras Futuras / Roadmap

### 1. **Pessimistic Locking para Alta Concurrencia**
```python
def register_exit(stock_record, quantity):
    stock_record = StockRecord.objects.select_for_update().get(pk=stock_record.pk)
    current = InventorySelector.get_current_stock(stock_record.pk)
    # ... rest of logic
```

**Beneficio:** Evita race conditions bajo ALTA concurrencia

### 2. **Caching de Saldo Actual**
```python
def get_current_stock(stock_record_id):
    cache_key = f"inventory:stock:{stock_record_id}"
    stock = cache.get(cache_key)
    if stock is None:
        stock = InventoryTransaction.objects...
        cache.set(cache_key, stock, timeout=300)  # 5 min TTL
    return stock
```

**Beneficio:** Reduce hits a base de datos para lecturas frecuentes

### 3. **Movimiento Type RESERVE**
```python
MOVEMENT_TYPES = (
    ('ENTRY', 'Entry'),
    ('EXIT', 'Exit'),
    ('RESERVE', 'Reserve (Quote)'),  # No implementado aún
)
```

**Propósito:** Reservar stock para cotizaciones sin confirmación inmediata

### 4. **Integración con Orders**
```python
# En orders/services/commands.py
def create_order(...)
    for cart_item in cart.items:
        InventoryCommands.register_exit(
            stock_record=cart_item.variant.stock_record,
            quantity=cart_item.quantity,
            reference=f"Order #{order.id}"
        )
```

**Propósito:** Automáticamente rebajar stock al confirmar orden

### 5. **Validación de GenericForeignKey**
```python
# En signals
@receiver(post_save, sender=StockRecord)
def validate_item_variant_exists(sender, instance, **kwargs):
    if not instance.item_variant:
        raise ValidationError(f"Item variant {instance.object_id} doesn't exist")
```

**Propósito:** Prevenir referencias rotas (orfandad en BD)

### 6. **Reporting y Analytics**
```python
# Agregar vistas de:
# - Stock por categoría
# - Movimiento promedio (velocidad de rotación)
# - Items bajo stock (reordenar)
# - Items con rotación lenta
```

**Propósito:** Dashboards de inteligencia de negocio

---

## 📝 Resumen de la Arquitectura

| Aspecto | Detalles |
|---------|----------|
| **Patrón Principal** | Service Layer (Commands/Selectors) + Append-Only Audit Log |
| **Modelos** | StockRecord (master), InventoryTransaction (audit) |
| **Operaciones** | Commands para escritura, Selectors para lectura |
| **Atomicidad** | @transaction.atomic en operaciones críticas |
| **Auditoria** | Todas las transacciones inmutables en BD |
| **Polimorfismo** | GenericForeignKey para múltiples tipos de items |
| **Escalabilidad** | Índices en SKU y (content_type, object_id) |
| **API** | DRF ViewSets ReadOnly + custom actions |
| **Validación** | Serializers + Kardex (pure functions) |

---

**Última actualización:** 2026-05-14
