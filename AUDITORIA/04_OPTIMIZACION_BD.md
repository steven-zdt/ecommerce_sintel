# 04 — OPTIMIZACIÓN BASE DE DATOS
**Fecha:** 2026-07-16  
**Motor:** PostgreSQL 16  
**Framework:** Django 5.2 ORM

> **Sincronizado 2026-07-27** contra `01_AUDITORIA_GENERAL.md` §3 y §7.2, y `12_CHECKLIST_IMPLEMENTACION.md`
> SPRINT 2. Crítico y Alta Prioridad anotados con estado real. Media Prioridad no re-verificada.

---

## CRÍTICO

### DB-C1 — `StockRecord.item_variant` GenericForeignKey permanentemente roto
**Estado:** ✅ Resuelto (documentado + mitigado) — opción 1 aplicada: comentario explícito en el modelo, resolución manual vía `batch_load_item_variants()`, 0 callers directos del GFK roto en todo el repo.
**Archivo:** `inventory/models.py:21-30`

`object_id = models.UUIDField(...)` almacena el `uuid` del modelo relacionado, pero Django's `GenericForeignKey` resuelve por `pk` (entero autoincremental). `stock_record.item_variant` siempre retorna `None`. El comentario en el código reconoce esto ("usar `batch_load_item_variants()`") pero el campo sigue siendo confuso y propenso a errores.

**Opciones de fix:**
1. (Preferida) Eliminar el accessor `GenericForeignKey` y documentar explícitamente que la resolución es manual via `batch_load_item_variants()`.
2. Cambiar `object_id` a `IntegerField` que almacene el `pk` del modelo.
3. Crear relaciones explícitas FK concretas por dominio (`product_variant`, `equipment_variant`, `service_variant`) en vez de un GFK.

### DB-C2 — `RentalRequest` tiene 50 campos — candidato prioritario a split
**Estado:** ✅ Resuelto 2026-07-27 — split en 4 sub-modelos (`RentalRequestLocation/Contact/Costs/PaymentInfo`, no exactamente los 3 nombres propuestos abajo pero mismo principio) vía migraciones 0034 (crea tablas)/0035 (backfill)/0036 (elimina las 35 columnas viejas, generada en esta sesión — faltaba y bloqueaba cualquier INSERT nuevo). Ver `01_AUDITORIA_GENERAL.md` §7.2 para el detalle completo, incluyendo un incidente crítico nuevo (`NameError` en `renting/api/views.py` que tumbaba todo el backend) encontrado en el camino.

**Archivo:** `renting/models.py:416-600`

50 campos incluyendo 4 TextFields (`access_conditions`, `location_notes`, `operational_notes`, `admin_notes`) y 13 DecimalFields. Todo SELECT sobre la tabla carga las 50 columnas aunque solo se necesiten estado, usuario y fechas.

**Split propuesto:**
```
RentalRequest          — estado, usuario, variante, fechas, totales, payment_method
  └── RentalRequestContact    — contact_* (8 campos) — 1:1
  └── RentalRequestLocation   — location_* + project_type + access_conditions (7 campos) — 1:1
  └── RentalRequestLogistics  — delivery/pickup/installation costs (6 campos) — 1:1
```

**Impacto:** Reducción del tamaño promedio de row en SELECT de lista del 60-70%.

---

## ALTA PRIORIDAD

### DB-H1 — `ServiceReview` sin `unique_together` — permite reseñas duplicadas
**Estado:** ✅ Resuelto (SPRINT 2) — `unique_together` agregado, migración aplicada, 0 duplicados verificados antes de aplicar. (Nota: este `DB-H1` de este documento es un ID distinto del `DB-H1` usado en `01_AUDITORIA_GENERAL.md`, que allí se refiere al split de `RentalRequest` = `DB-C2` de este documento.)
**Archivo:** `technical_services/models.py:180-187`  
`ProductReview` y `EquipmentReview` ya tienen este constraint (corregido en la auditoría de 2026-07-03). `ServiceReview` no lo tiene — una condición de carrera o INSERT directo puede crear múltiples reseñas por usuario/servicio, corrompiendo los promedios de calificación.

```python
class Meta:
    unique_together = ('user', 'service')  # AGREGAR
```

### DB-H2 — `Quotation.status` sin `db_index`
**Estado:** ✅ Resuelto (SPRINT 2) — `db_index=True` agregado.
**Archivo:** `quotes/models.py:44`  
`Quotation.status` es un `CharField` filtrado constantemente en el panel admin y el flujo CPQ. Sin índice en una tabla que puede tener miles de registros, las queries de lista y filtrado son table-scans.

```python
status = models.CharField(max_length=25, db_index=True)  # AGREGAR db_index
```

### DB-H3 — `ShipmentOrderSummarySerializer.get_items_count` bypasea prefetch cache
**Estado:** ✅ Resuelto (SPRINT 2) — reemplazado por `sum(1 for i in obj.items.all() if i.variant_id is not None)`.
**Archivo:** `orders/api/serializers.py:130`  
```python
# ACTUAL (N+1):
return obj.items.filter(variant__isnull=False).count()

# CORRECTO (usa prefetch cache):
return sum(1 for i in obj.items.all() if i.variant_id is not None)
```
`FulfillmentSelector` ya prefetch `order__items` pero `.filter()` no usa el cache.

### DB-H4 — `UserProfile.total_services_completed`: COUNT query por perfil en listas
**Estado:** ✅ Resuelto (SPRINT 2) — la anotación ya existía en `ContractorAdminSelector` pero el `@property` del modelo no tenía setter y crasheaba con `AttributeError` al materializar el queryset (`/panel/profesionales` estaba roto); corregido con un setter que cachea el valor anotado.
**Archivo:** `accounts/models.py:92-95`  
Propiedad del modelo que emite `self.user.assigned_services.filter(...).count()`. Incluida en `ContractorSerializer` y `AdminContractorSerializer`. Con N perfiles en la lista = N+1 queries.

**Fix:** Mover a anotación en el Selector:
```python
queryset.annotate(
    total_services_completed=Count(
        'user__assigned_services',
        filter=Q(user__assigned_services__order__status=Order.STATUS_COMPLETED)
    )
)
```

### DB-H5 — Cadenas de migraciones largas — candidatos a squash
**Estado:** ⚪ Sigue abierto — sin evidencia de `squashmigrations` ejecutado; baja prioridad, sin urgencia operativa.
| App | Migraciones | Notas |
|---|---|---|
| `technical_services` | 28 | Incluye data migrations semilla |
| `core` | 25 | Alta rotación de modelo de contenido |
| `quotes` | 24 | Sistema CPQ con evolución frecuente |
| `renting` | 23 | AvailabilityEngine + OperationFSM |

Por encima de 20 migraciones el tiempo de `migrate` en CI aumenta visiblemente. Candidatos para `squashmigrations` después de estabilizar el schema.

### DB-H6 — `UserProfile.document` sin constraint de unicidad por `document_type`
**Estado:** ✅ Resuelto (SPRINT 2) — `UniqueConstraint` agregado vía migración 0012, con un bug real corregido en el camino: la condición inicial (`Q(document__isnull=False)`) no excluía `document=''` (default real de `CharField`), lo que rompía el registro de cualquier segundo usuario sin documento.
Dos perfiles pueden almacenar el mismo número de documento nacional. Debe ser único por `(document_type, document)`.

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['document_type', 'document'],
            condition=Q(document__isnull=False),
            name='unique_document_per_type'
        )
    ]
```

---

## MEDIA PRIORIDAD

### DB-M1 — Índices faltantes en campos de filtro frecuente

| Modelo | Campo | Razón |
|---|---|---|
| `renting.EquipmentVariant` | `is_active` | Usado en `variants__is_active=True` JOIN en catálogo público |
| `operations.OperationAssignment` | `status` | `status='ACTIVE'` filtrado directamente en vistas de operaciones |
| `renting.RentalRequest` | `payment_status` | Reconciliación de pagos |
| `users.EmailVerificationCode` | `(email, is_used)` | OTP validation: `(email=X, is_used=False)` — solo index en `email` |
| `technical_services.ServiceVariant` | `is_active` | Filtrado en catálogo y serializer |
| `kyc.VerificationDocument` | `scan_status` | Pipeline AML sin index |

### DB-M2 — `FooterGroupSerializer.get_links_count` N+1
**Archivo:** `core/api/serializers.py:440`  
`.filter(is_deleted=False).count()` por grupo. `FooterGroupSelector.list_all()` no prefetch `links`.

```python
# SELECTOR: agregar
queryset.prefetch_related('links')

# SERIALIZER: cambiar
return sum(1 for l in obj.links.all() if not l.is_deleted)
```

### DB-M3 — `FlashOfferCardSerializer.get_item_thumbnail` N+1
**Archivo:** `core/api/serializers.py:101-115`  
`MarketingSelector.list_active_flash_offers()` no prefetch `variant__product__images`. El `.filter(is_primary=True)` en el serializer crea 1-2 queries por oferta.

```python
# SELECTOR: agregar
.prefetch_related(
    'variant__product__images',
    'service_variant__service__images',
    'equipment_variant__equipment__images'
)
# SERIALIZER: usar obj.variant.product.images.all() con filter en Python
```

### DB-M4 — `Equipment.list_all_for_admin` carga TextFields innecesariamente
`Equipment.description`, `meta_description`, `meta_keywords` se cargan en listados de admin donde solo se necesitan `name`, `slug`, `is_active`, `is_featured`. Agregar `.defer('description', 'meta_description', 'meta_keywords')`.

### DB-M5 — `OrderServiceDetail.contact_person` es JSONField con datos estructurados
**Archivo:** `technical_services/models.py:230`  
`contact_person = JSONField(...)` almacena `{name, position, phone}`. Impide filtrado, indexado y validación de campos individuales. Fix a mediano plazo: normalizar a columnas `contact_name`, `contact_phone`, `contact_position`.

### DB-M6 — Orders: status legacy `'pending'` y `'processing'` en STATUS_CHOICES sin CheckConstraint de deprecación
**Archivo:** `orders/models.py:51`  
Los choices legacy existen pero `create_from_cart()` ya no los usa. Un `CheckConstraint` puede prevenir que codigo nuevo los use:
```python
CheckConstraint(
    check=~Q(status__in=['pending', 'processing']),
    name='no_legacy_order_status'
)
```

### DB-M7 — `Quotation.answers` JSONField para respuestas del cuestionario CPQ
**Archivo:** `quotes/models.py:75`  
Intencional, pero impide queries analíticas sobre respuestas individuales. Si se necesitan métricas sobre respuestas CPQ, planificar migración a `QuotationAnswer` relacional.

---

## Resumen de Acciones Requeridas

| Prioridad | Acción | App | Estado (2026-07-27) |
|---|---|---|---|
| Urgente | Eliminar/refactorizar GFK en StockRecord | inventory | ✅ Resuelto |
| Urgente | `unique_together` en `ServiceReview` | technical_services | ✅ Resuelto |
| Alta | `db_index=True` en `Quotation.status` | quotes | ✅ Resuelto |
| Alta | Fix N+1 en `ShipmentOrderSummarySerializer` | orders | ✅ Resuelto |
| Alta | Fix N+1 en `UserProfile.total_services_completed` (annotation) | accounts | ✅ Resuelto |
| Alta | Split `RentalRequest` (50 campos) | renting | ✅ Resuelto 2026-07-27 |
| Media | 6 índices faltantes (tabla DB-M1) | varios | ⚪ Sin re-verificar |
| Media | Fix N+1 en `FooterGroupSerializer` y `FlashOfferCardSerializer` | core | ✅ Resuelto (SPRINT 2, checklist 12) |
| Media | Constraint unicidad de documento en `UserProfile` | accounts | ✅ Resuelto |
| Baja | Squash de migraciones en 4 apps | varios | ⚪ Sigue abierto |
