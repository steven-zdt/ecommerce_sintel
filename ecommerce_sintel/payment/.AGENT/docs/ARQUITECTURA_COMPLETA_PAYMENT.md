# ARQUITECTURA COMPLETA — app `payment` (SSoT de Metodos de Pago)

> **Ultima actualizacion:** 2026-07-22 (smoke test E2E post-ADR-001 en Shop/Servicios/Renting --
> 2 bugs reales encontrados y corregidos, kill-switch simetrico Tarjeta/Widget -- ver seccion 10.6)
> **Mantenido por:** Claude Code — sincronizado con el estado real del codigo
>
> **ADR-001 (10 fases, todas completas):** `docs/deployment/` no -- vive en este mismo directorio,
> `payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md`, con un informe detallado por fase
> (`FASE0_..` a `FASE9_..`). Ese ADR es la fuente de verdad del *diseno y razonamiento*; este
> documento es la fuente de verdad del *estado actual del codigo*. Cuando difieran, confiar en el
> codigo (y corregir este documento), nunca al reves.

---

## [CRITICAL] REGLA FUNDAMENTAL

> **`payment` es la UNICA fuente de verdad (SSoT) para todos los metodos de pago del sistema.**

> **Nota de nomenclatura:** el label de la app Django es `payment` (`payment/apps.py` → `name = 'payment'`),
> montada en `INSTALLED_APPS` y en `ecommerce/urls.py` bajo `path('api/v1/payment/', include('payment.urls'))`.
> El nombre comercial de la pasarela ("Wompi") se usa solo para el metodo de pago con widget online
> (`payment/online/`), no para el nombre de la app. No existe una app de nivel superior llamada `wompi` ni
> una app de nivel superior llamada `nequi`: el cliente HTTP y el ViewSet de Nequi viven en `payment/nequi/`.

| Regla | Detalle |
|---|---|
| **Modelos de transaccion** | Todo modelo que registre el ciclo de vida de un pago VIVE en `payment/models.py`. Ninguna otra app puede tener su propio modelo de transaccion de pago. |
| **Logica post-pago compartida** | `confirm_order_payment()` y `_deduct_inventory_for_order()` viven en `payment/shared/commands.py`. Ninguna otra app puede duplicar esta logica. |
| **Nuevos metodos de pago** | Al agregar un nuevo metodo (PSE, Bancolombia, PayU...), el modelo y los commands van en `payment/`. La app/subpaquete de integracion (si existe) puede tener su client HTTP y su ViewSet, pero debe delegar a `payment/shared/commands.py`. |
| **Inventario post-pago** | El descuento de stock post-pago siempre pasa por `_deduct_inventory_for_order()` en `payment/shared/commands.py`, nunca se reimplementa en otras apps. |

**Violacion de esta regla = cambio rechazado.**

---

## 1. Modelos (`payment/models.py`)

### 1.1 `Transaction` — Wompi Online

Registra cada intento de pago a traves del widget de Wompi Colombia.

```python
class Transaction(SintelBaseModel):
    STATUS_CHOICES = [PENDING, APPROVED, DECLINED, VOIDED, ERROR]

    order               → ForeignKey(Order, null=True, blank=True, related_name='transactions')
    rental_request      → ForeignKey('renting.RentalRequest', null=True, blank=True, related_name='wompi_transactions')
    wompi_id            → CharField(unique=True, null=True)   # ID externo asignado por Wompi
    amount_in_cents     → BigIntegerField
    currency            → CharField(default='COP')
    status              → CharField(default='PENDING', db_index=True)
    payment_method_type → CharField          # 'CARD', 'PSE', 'NEQUI_WIDGET', etc.
    redirect_url        → URLField
    integrity_signature → CharField          # SHA256 calculado para el widget
    correlation_id      → CharField(max_length=36, null=True, db_index=True)  # ADR-001 Fase 4
    initiation_channel  → CharField(choices=[CHANNEL_CARD_API, CHANNEL_WIDGET], null=True,
                                     blank=True)  # migration 0012, 2026-07-22

    class Meta:
        constraints = [CheckConstraint("exactamente uno de order/rental_request", name='payment_transaction_exactly_one_target')]
```

**Solo uno de `order` / `rental_request` debe estar establecido** — el modelo sirve tanto para pagos
de tienda/servicios (Order) como para pagos de alquiler (RentalRequest). **Garantizado a nivel de BD**
desde 2026-07-03 (migration `0007_...`) con un `CheckConstraint`; antes solo era una convencion de
codigo sin proteccion en la base de datos.

**`correlation_id` (ADR-001 Fase 4, 2026-07-13):** se minta **una sola vez** en
`WompiPaymentViewSet.initialize()` (un UUID por intento de pago) y se propaga automaticamente a
traves de todo el ciclo de vida de la transaccion porque todo lo que la toca despues (creacion
sincrona, sync por polling, webhook) lee este mismo campo -- no hace falta pasarlo entre capas
manualmente. Permite seguir un intento de pago completo con un solo grep en los logs (`corr=<uuid>`)
y queda tambien en cada fila de `TransactionEvent` (seccion 1.5).

**`initiation_channel` (migration 0012, 2026-07-22):** lo fija `WompiCommands.initialize_transaction()`
segun si se paso `card_token`/`payment_source_id` (`CHANNEL_CARD_API`) o no (`CHANNEL_WIDGET`) --
puramente informativo, no cambia ningun comportamiento de negocio. Visible en `/panel/pagos` como
columna "Canal" (badge "Tarjeta (API)"/"Widget"), util para diagnosticar en produccion si un pago
que deberia haber usado el flujo directo cayo silenciosamente al Widget (exactamente el sintoma del
bug de la seccion 10.6).

**Lifecycle:** `PENDING` → `APPROVED | DECLINED | VOIDED | ERROR` (via webhook de Wompi, via
sincronizacion activa `_sync_wompi_status()`, o -- desde ADR-001 Fase 2 -- via creacion sincrona en
`WompiCommands._create_transaction_sync()` cuando el checkout usa el flujo de tarjeta backend-directo,
ver seccion 10.2). **Los 5 estados de arriba son los UNICOS estados reales de Wompi** -- no existe
`EXPIRED` ni ningun otro inventado; un timeout de UI es un concepto de presentacion, nunca se guarda
como valor de `status` (leccion de un bug real de 2026-07-07, repetida al disenar la reconciliacion
de transacciones abandonadas en la Fase 6 del ADR-001).

---

### 1.2 `CodTransaction` — Pago Contra Entrega

```python
class CodTransaction(SintelBaseModel):
    STATUS_CONFIRMED = 'CONFIRMED'
    STATUS_DELIVERED = 'DELIVERED'
    STATUS_CANCELLED = 'CANCELLED'

    order        → OneToOneField(Order, related_name='cod_transaction')
    status       → CharField(default='CONFIRMED', db_index=True)
    delivered_at → DateTimeField(null=True)
    notes        → TextField(blank=True)
```

**Lifecycle:** `CONFIRMED` (automatico al crear orden) → `DELIVERED` (admin) | `CANCELLED` (admin)

**Diferencia clave vs Wompi/Nequi:** El inventario se descuenta en el momento de creacion de la orden (no al confirmar pago externo), porque no hay gateway que apruebe el pago.

---

### 1.3 `NequiTransaction` — Nequi Push Notification

```python
class NequiTransaction(SintelBaseModel):
    STATUS_PENDING  = 'PENDING'
    STATUS_APPROVED = 'APPROVED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_ERROR    = 'ERROR'

    order          → ForeignKey(Order, null=True, blank=True, related_name='nequi_transactions')
    rental_request → ForeignKey('renting.RentalRequest', null=True, blank=True, related_name='nequi_transactions')
    phone_number   → CharField(max_length=20)
    message_id     → CharField(unique=True, null=True)
    amount         → DecimalField(max_digits=12, decimal_places=2)
    status         → CharField(default='PENDING', db_index=True)

    class Meta:
        constraints = [CheckConstraint("exactamente uno de order/rental_request", name='payment_nequitransaction_exactly_one_target')]
```

**Solo uno de `order` / `rental_request`**, mismo `CheckConstraint` que `Transaction` (migration `0007_...`, 2026-07-03).

**Solo uno de `order` / `rental_request` debe estar establecido**, igual que `Transaction`.

> **Nota historica:** `NequiTransaction` vivio brevemente en un modulo `nequi` independiente.
> Los modelos de pago de todo metodo viven exclusivamente en `payment/models.py`.

---

### 1.4 `TokenizedCard` — Tarjetas guardadas del cliente (migration 0005)

Almacena datos de tarjetas tokenizadas desde Wompi.js para pagos rapidos del Customer Dashboard.

```python
class TokenizedCard(SintelBaseModel):
    user           → ForeignKey(AUTH_USER_MODEL, related_name='tokenized_cards')
    token_id       → CharField(max_length=255, unique=True)   # token Wompi
    masked_number  → CharField(max_length=20)                  # ej: XXXXXXXXXXXX1234
    brand          → CharField(max_length=30)                  # VISA, MASTERCARD, AMEX, DINERS
    exp_month      → CharField(max_length=2)
    exp_year       → CharField(max_length=4)
    cardholder_name → CharField(max_length=255, blank=True)
    is_default     → BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(fields=['user'], condition=Q(is_default=True, is_deleted=False),
                              name='payment_tokenizedcard_one_default_per_user'),
        ]
```

**Soft-delete:** `TokenizedCard` NO tiene campo `is_active` (a diferencia de otros modelos del
proyecto) — solo usar `is_deleted=True; save()`. **Corregido 2026-07-03**: `destroy()` intentaba
asignar y guardar un campo `is_active` inexistente, lo que provocaba `ValueError` (500) en
**toda** llamada a `DELETE /api/v1/payment/cards/{uuid}/` — el endpoint nunca funciono en
produccion hasta este fix.

**Bug critico corregido 2026-07-22 (smoke test E2E, `_serialize_card()` en `payment/cards/views.py`):**
el serializer de esta vista (una funcion module-level, no un `Serializer` DRF) devolvia `uuid` pero
**nunca `token_id`** en el JSON de `GET payment/cards/` -- pese a que el modelo si lo tiene. El
frontend (`useCardOrWidgetPayment.js`, seccion 10.4/10.6) siempre referencio `card.token_id` para
resolver que token mandar a `payment/payments/initialize/` al pagar con una tarjeta guardada.
Efecto real: **toda seleccion de tarjeta guardada resolvia `card_token: undefined`**, y
`initialize()` -- que trata `card_token`/`payment_source_id` como opcionales -- silenciosamente
tomaba el flujo Widget completo en vez de cobrar la tarjeta elegida, sin ningun error visible para
el usuario ni en consola (justo el tipo de fallo silencioso que `initiation_channel`, arriba, existe
para diagnosticar). Bug pre-existente desde la Fase 3a del ADR-001 (2026-07-13) -- nunca se habia
detectado porque ninguna verificacion previa habia probado pagar con una tarjeta *ya guardada* (solo
tarjeta nueva). **Corregido** agregando `'token_id': card.token_id` a `_serialize_card()`. Verificado
end-to-end: pago con tarjeta guardada en Shop resuelve `Transaction.status='APPROVED'` /
`initiation_channel='CARD_API'`.

**Default:** Solo una tarjeta puede ser `is_default=True` por usuario, **garantizado a nivel de
BD** desde 2026-07-03 con `UniqueConstraint(user, condition=is_default & ~is_deleted)` (migration
`payment/0007_...`). Antes solo se garantizaba a nivel de aplicacion (dos UPDATE/SAVE separados,
sin bloqueo) y `destroy()` no limpiaba el flag de la tarjeta eliminada al promover la siguiente,
lo que podia dejar 2 filas con `is_default=True` para el mismo usuario. `create()` y
`set_default()` ahora envuelven la escritura en `transaction.atomic()` y capturan
`IntegrityError` -> `409 Conflict` limpio si la constraint bloquea una condicion de carrera.

**Modulo:** `payment/cards/` (sub-paquete separado)
- `payment/cards/__init__.py`
- `payment/cards/views.py` → `TokenizedCardViewSet`
- `payment/cards/urls.py` → router registrado en `payment/urls.py`

**Alta automatizada desde el frontend (ADR-001 Fase 3a, 2026-07-13):** el formulario de
`CustomerCardsView.vue` (`/mi-cuenta/tarjetas`) ya NO le pide al usuario pegar el token a mano.
Captura numero/MM/AA/CVC/titular reales y usa `useCardTokenization.js`
(`frontend/src/composables/useCardTokenization.js`) para tokenizar **directo desde el navegador
hacia `https://api.wompi.co/v1/tokens/cards`** (llave publica, `VITE_WOMPI_PUBLIC_KEY`) -- deliberada
y explicitamente **sin pasar por `useApi()`/axios** (nuestro backend nunca ve datos crudos de
tarjeta, requisito PCI confirmado en la documentacion oficial de Wompi). La respuesta de Wompi se
mapea directo a los campos que `POST payment/cards/` (arriba) ya esperaba -- **no hizo falta ningun
endpoint backend nuevo**: `TokenizedCard.token_id` ya guardaba un token reutilizable, este proyecto
nunca necesito el concepto de "payment source" de Wompi. El formulario limpia sus campos
incondicionalmente (exito o error) para que numero/CVC nunca queden en memoria de mas.

---

### 1.5 `TransactionEvent` — historial de auditoria (ADR-001 Fase 4, migration 0009)

Historial **append-only** de cada evento real de una `Transaction`, separado de `Transaction.status`
(que sigue siendo el estado *actual*, sin cambios de significado para nada que ya lo consulte).

```python
class TransactionEvent(SintelBaseModel):
    SOURCE_CHOICES = [WEBHOOK, API_SYNC, API_CREATE]

    transaction     → ForeignKey(Transaction, related_name='events')
    source          → CharField(choices=SOURCE_CHOICES, db_index=True)
    previous_status → CharField(blank=True)
    new_status      → CharField(blank=True)
    correlation_id  → CharField(max_length=36, null=True, db_index=True)
    raw_payload     → JSONField(null=True)   # payload de Wompi -- nunca datos de tarjeta
    processed       → BooleanField(default=True)
    error_detail    → TextField(blank=True)
```

**Se escribe en los 3 puntos de contacto reales con Wompi:**
- `WompiCommands._create_transaction_sync()` (`source=API_CREATE`) — creacion sincrona (Fase 2/3b).
- `payment/online/api/views.py::_sync_wompi_status()` (`source=API_SYNC`) — **solo cuando el status
  realmente cambia** (evita ruido en cada poll sin novedades); tambien escribe un evento
  `processed=False` cuando la consulta a Wompi falla (no-200 o excepcion) -- antes ese fallo solo
  dejaba un `logger.warning` que se perdia al rotar logs.
- `WompiCommands.process_webhook_notification()` (`source=WEBHOOK`) — **incluye el caso de webhook
  duplicado** (`processed=False`, para que quede constancia de que Wompi reintento y por que se
  ignoro).

**Deliberadamente NO tiene un campo de "ID de evento de Wompi":** se investigo contra
`docs.wompi.co` (Fase 2 del ADR-001) y el payload de webhook no documenta un identificador de
evento unico separado del ID de transaccion -- no se inventa ese campo.

**Admin:** `TransactionEventAdmin` (`payment/admin.py`) es de **solo lectura** (`has_add/change/delete_permission`
→ `False`) — nunca se edita ni se borra a mano, coherente con "append-only". Tambien visible desde el
panel Vue (`/panel/pagos`, boton "Historial" por transaccion, ADR-001 Fase 7).

---

### 1.6 `PaymentFeatureFlags` — kill-switch operativo (ADR-001 Fase 5, migration 0010)

Singleton (mismo patron ya usado en `organization`/`core`: guardar un registro con `is_active=True`
desactiva cualquier otro; **duplicado localmente, no importado entre apps**, siguiendo la convencion
ya existente del proyecto de no crear dependencias cruzadas para un mixin de 3 lineas).

```python
class PaymentFeatureFlags(SintelBaseModel):
    card_api_flow_enabled → BooleanField(default=True)
    widget_flow_enabled    → BooleanField(default=True)   # migration 0013, 2026-07-22
    is_active              → BooleanField(default=True)

    @classmethod
    def get_active(cls) -> 'PaymentFeatureFlags': ...       # self-healing, crea el default si no existe
    @classmethod
    def set_card_api_flow_enabled(cls, enabled: bool) -> 'PaymentFeatureFlags': ...
    @classmethod
    def set_widget_flow_enabled(cls, enabled: bool) -> 'PaymentFeatureFlags': ...   # 2026-07-22
```

**`card_api_flow_enabled`:** si esta activo (default), el checkout ofrece el sub-metodo "Tarjeta"
(flujo backend-directo, seccion 10.2) ademas de "PSE / Otros". Si se desactiva, el checkout **solo**
ofrece "PSE / Otros" (Widget completo de Wompi, que ya incluye tarjeta) — reversion instantanea sin
necesidad de desplegar codigo nuevo si el flujo nuevo da problemas en produccion.

**`widget_flow_enabled` (2026-07-22, plan "Eliminar el Widget como mecanismo principal de pago para
tarjetas"):** simetrico al de arriba, pero para el sub-metodo "PSE / Otros" -- permite apagar el
Widget completo de Wompi independientemente de la Tarjeta backend-directo (ej. si Wompi reporta un
incidente con su widget embebido, o cuando el rollout planeado sea confiar 100% en el flujo API y
usar el Widget solo como respaldo temporal, no al reves como era antes de este cambio). Los dos
flags son independientes -- pueden estar ambos activos (default), ambos desactivados (checkout de
Wompi/Nequi/COD sin online, solo si se hace a proposito), o cualquier combinacion.

**Son kill-switches REALES, no solo cosmeticos:** `WompiPaymentViewSet.initialize()` **rechaza con
403** cualquier request con `card_token`/`payment_source_id` si `card_api_flow_enabled` esta
desactivado, **y tambien rechaza con 403** cualquier request SIN esos campos (es decir, un intento
de abrir el Widget) si `widget_flow_enabled` esta desactivado -- ambos aplicados en el backend, no
solo ocultando el boton en el frontend (alguien podria llamar al endpoint directo saltandose la UI).
Mismo par de checks, replicado identico en `renting/api/views.py::process_payment()` para que
Renting respete los mismos 2 flags (antes del 2026-07-22 Renting no tenia ningun kill-switch backend
para el pago online). El frontend (`CheckoutView.vue`/`ServiceCheckoutModal.vue`/
`RentalConfirmationView.vue`, via `useCardOrWidgetPayment.js`, seccion 10.6) tambien **falla
cerrado**: si la consulta al endpoint de flags falla por cualquier motivo, asume
`card_api_flow_enabled=false` (nunca ofrece Tarjeta sin confirmar el flag) y deja
`widget_flow_enabled` en su default `true` -- prefiere el camino Widget, ya probado, ante la duda.
Si el backend responde que ambos flags estan apagados (mala configuracion del admin), el frontend
prefiere mostrar Tarjeta antes que dejar al cliente sin ningun sub-metodo visible.

**Togglable desde 2 lugares, ambos auditados (ver seccion 1.7):**
- Django `/admin/` (`PaymentFeatureFlagsAdmin.save_model()`).
- Panel Vue `/panel/pagos` (switch en `PaymentTransactionsAdminView.vue` → `GET`/`PATCH
  dashboard/payment-transactions/feature-flags/`).

---

### 1.7 `SecurityEvent` — tipos nuevos relacionados con pagos (ADR-001 Fase 4/8)

`security.models.SecurityEvent.EVENT_CHOICES` (app `security`, no `payment`) gano 3 tipos nuevos
durante este proyecto, disparados exclusivamente via `SecurityCommands.log_event()`:

| Evento | Severidad | Disparado en |
|---|---|---|
| `PAYMENT_APPROVED` | INFO | `PaymentCommands.confirm_payment()` (Fase 4) — simetria con `PAYMENT_DECLINED`, que ya existia; cubre Order y RentalRequest, automatico para las 3 formas de aprobar un pago (webhook/sync/creacion sincrona) porque `confirm_payment()` es el chokepoint comun de las tres. |
| `PAYMENT_TRANSACTION_ABANDONED` | WARNING | `reconcile_pending_wompi_transactions()` (`payment/tasks.py`, Fase 6/8) — cuando una transaccion `PENDING` sin `wompi_id` supera el umbral de "abandonada" (seccion 5.1). |
| `PAYMENT_FEATURE_FLAG_CHANGED` | WARNING | `AdminPaymentViewSet.feature_flags()` (panel Vue) y `PaymentFeatureFlagsAdmin.save_model()` (Django admin) — **solo si el valor realmente cambia**, con `metadata.source` distinguiendo `'panel_admin'` de `'django_admin'`. |

**Decision de diseno (por que `SecurityEvent` y no `dispatch_notification`):** para "transaccion
abandonada" el unico `user` disponible seria el **cliente** de la transaccion, no un admin --
`dispatch_notification()` resuelve canales (incluido email) contra ese `user`, asi que usarlo
arriesgaba notificar por error al cliente sobre algo que la Fase 6 decidio explicitamente NO
comunicarle (no se sabe con certeza si su pago se completo). `SecurityEvent` ya esta visible en
`/panel/seguridad` sin construir nada nuevo, y no tiene ningun riesgo de notificar a un cliente.

---

## 2. Servicios (`payment/shared/commands.py`)

### 2.1 Helpers compartidos (privados al modulo)

```python
_get_stock_record(variant) -> StockRecord | None
    # Busca StockRecord activo via ContentType + variant.uuid

_has_sufficient_stock(variant, quantity) -> bool
    # Usa InventorySelector.get_current_stock() — SSoT de inventory

_deduct_inventory_for_order(order, reference: str) -> None
    # Descuenta stock de items fisicos (variant + equipment_variant)
    # Omite ServiceVariant (sin StockRecord fisico)
    # UNICO punto del sistema donde se llama InventoryCommands.register_exit() por pago
```

> **Historial:** estas tres funciones estuvieron temporalmente convertidas en no-ops
> (`return None` / `return True` / `pass`) durante un refactor incompleto que buscaba desacoplar
> `payment` de `inventory`, sin haber conectado un reemplazo (ni signal ni llamada a API). Esto dejaba
> **todo pago aprobado sin descuento de stock real**. Restaurado el 2026-07-03 a la implementacion
> que importa directamente `inventory.services.commands.InventoryCommands` e
> `inventory.services.selectors.InventorySelector` (sin dependencia circular: `inventory` no importa
> `payment` ni `orders`). Si en el futuro se desea desacoplar via signal, debe hacerse reemplazando
> **ambas** puntas (`payment/shared/commands.py` y `payment/online/services/commands.py`) en el mismo
> cambio, nunca dejando una stubeada mientras la otra sigue en uso.

### 2.2 `confirm_order_payment(order, reference)` — SSoT post-pago online

```python
@transaction.atomic
def confirm_order_payment(order: Order, reference: str) -> None
```

| Paso | Accion |
|---|---|
| 1 | `select_for_update()` sobre la orden |
| 2 | Si `order.status == Order.STATUS_PAID` → return (idempotente, evita doble descuento) |
| 3 | `order.status = Order.STATUS_PAID` → save |
| 4 | `ServiceCommands.confirm_slot_on_payment(order)` |
| 5 | `_deduct_inventory_for_order(order, reference)` |
| 6 | `OperationCommands.ensure_tickets_for_order(order)` |
| 7 | `FulfillmentCommands.ensure_shipment_for_order(order)` |
| 8 | `transaction.on_commit(NotificationCommands.dispatch_notification('order_paid', ...))` |

> **Correccion de este documento (2026-07-13, ADR-001 Fase 10):** el paso 7
> (`FulfillmentCommands.ensure_shipment_for_order`) existe en el codigo real
> (`payment/shared/commands.py`) desde antes de este proyecto, pero esta tabla nunca lo habia
> documentado — se detecto durante la auditoria de Fase 0 del ADR-001 y se corrige aqui.

**Callers:** `PaymentCommands.confirm_payment(wompi_tx)` y `NequiCommands.check_and_update_status(nequi_tx)`.
Ambos, tras `confirm_order_payment()`, disparan ademas `SecurityCommands.log_event(SecurityEvent.PAYMENT_APPROVED, ...)`
(seccion 1.7) — no es parte de `confirm_order_payment()` en si (esa funcion es agnostica de la
pasarela), vive en cada caller.

---

### 2.3 `WompiCommands` (`payment/online/services/commands.py`)

```python
WompiCommands.initialize_transaction(
    order=None, rental_request=None, *,
    card_token=None, payment_source_id=None, correlation_id=None,
) -> Transaction
    # Requiere order O rental_request (excluyentes)
    # Convierte total a centavos (Decimal seguro, ROUND_DOWN)
    # Crea Transaction(PENDING, correlation_id=...)
    # Calcula integrity_signature = SHA256(reference + cents + currency + INTEGRITY_SECRET)
    #
    # ADR-001 Fase 2/3b (2026-07-13): card_token/payment_source_id son OPCIONALES y mutuamente
    # excluyentes. Si se pasa alguno -> WompiCommands._create_transaction_sync() (abajo), la
    # transaccion se crea TAMBIEN de forma sincrona en Wompi via WompiApiClient (seccion 10.1),
    # wompi_id/status quedan disponibles de inmediato sin depender del webhook. Si NO se pasa
    # ninguno -- el camino de "PSE / Otros" en CheckoutView.vue, que sigue abriendo el Widget
    # completo -- el comportamiento es IDENTICO al de siempre (esta funcion solo crea la
    # Transaction local, es el Widget quien crea la transaccion del lado de Wompi).

WompiCommands._create_transaction_sync(wompi_tx, order, rental_request, card_token, payment_source_id) -> None
    # ADR-001 Fase 2. Llama WompiApiClient().create_transaction(...) (seccion 10.1).
    # Exito: guarda wompi_id/status/payment_method_type, escribe TransactionEvent(API_CREATE),
    #        y si status=='APPROVED' llama PaymentCommands.confirm_payment() en el mismo request.
    # Fallo (WompiApiError): Transaction.status='ERROR' explicito (nunca queda huerfana en PENDING
    #        sin rastro), TransactionEvent(API_CREATE, processed=False, error_detail=...), re-raise
    #        (el ViewSet responde 502 al frontend).

WompiCommands.process_webhook_notification(payload: dict) -> None
    # Extrae reference, status, wompi_id del payload
    # Ignora webhooks duplicados si el estado previo ya era APPROVED (TransactionEvent processed=False)
    # Actualiza Transaction existente, escribe TransactionEvent(WEBHOOK, processed=True)
    # Si APPROVED → PaymentCommands.confirm_payment()
    # Si DECLINED|VOIDED|FAILED → SecurityEvent.PAYMENT_DECLINED + ServiceCommands.release_slot_on_failure()
    #   (o RentalRequestCommands.release_on_payment_failure() si es de RentalRequest)
```

### 2.4 `PaymentCommands`

```python
PaymentCommands.confirm_payment(wompi_transaction: Transaction) -> None
    # Si status != APPROVED → return (no-op)
    # Si tiene rental_request → RentalRequestCommands.confirm_payment(), return
    # Re-valida stock ANTES de descontar: select_for_update sobre order.items
    #   dentro de su PROPIO `with transaction.atomic()` (no decorador de metodo)
    # Si stock insuficiente → guarda Transaction.status = ERROR FUERA de ese bloque
    #   atomic, y solo entonces raise ValueError
    # Si OK → confirm_order_payment(order, f"Wompi {wompi_id}")
```

> **Nota (bug corregido 2026-07-03):** este metodo tenia `@transaction.atomic` envolviendo
> **todo** el cuerpo. Al detectar stock insuficiente, guardaba `status='ERROR'` y luego hacia
> `raise ValueError` dentro del mismo bloque atomico — Django revierte toda la transaccion
> (incluido ese `save()`) al propagar la excepcion, asi que en BD la `Transaction` quedaba como
> `'APPROVED'` pese al error. Se separo el `select_for_update()`/chequeo de stock (en su propio
> `with transaction.atomic()`) del guardado del estado `ERROR` (fuera de cualquier atomic que
> luego se revierta). Cubierto por
> `payment.tests.PaymentInventoryIntegrationTestCase.test_payment_commands_confirm_payment_blocks_on_insufficient_stock`.

### 2.5 `CodCommands` (`payment/cod/services/commands.py`)

```python
CodCommands.confirm_order(order) -> CodTransaction
    # Llamado desde OrderCommands.create_from_cart() con payment_method='COD'
    # Descuenta inventario inmediatamente (_deduct_inventory_for_order)
    # Crea CodTransaction(CONFIRMED)
    # order.status = Order.STATUS_PAID  <- mismo gate que confirm_order_payment()
    #   usa para Wompi/Nequi; desbloquea el motor de fulfillment (prepare/pack/...)
    # OperationCommands.ensure_tickets_for_order(order)
    # on_commit: dispatch_notification('order_cod_confirmed')

CodCommands.mark_delivered(cod_transaction) -> CodTransaction
    # cod_transaction.status = DELIVERED, delivered_at = now(), order.status = 'delivered'

CodCommands.cancel(cod_transaction, notes='') -> CodTransaction
    # cod_transaction.status = CANCELLED, order.status = 'cancelled'
```

> **Bug corregido 2026-07-03 (checkout COD completo, no solo tarjetas/Nequi):**
> `OrderCommands.create_from_cart()` (`orders/services/commands.py`) habia dejado de llamar a
> `CodCommands.confirm_order()` por completo — quedaba solo como comentario aspiracional en este
> mismo documento, nunca verificado contra el codigo real hasta que se audito `orders/`. Efecto: toda
> orden de tienda/servicio con `payment_method='COD'` quedaba creada en `STATUS_PENDING_PAYMENT` para
> siempre, sin `CodTransaction`, sin descuento de inventario. Restaurada la llamada al final de
> `create_from_cart()`. Ademas, `CodCommands.confirm_order()` antes no tocaba `order.status` — se le
> agrego la transicion a `STATUS_PAID` (ver arriba) porque nada mas en el sistema lo hacia para COD.
> Cubierto por `orders.tests.CodCheckoutEndToEndTestCase` (2 tests: comando directo + endpoint HTTP
> real) y `payment.tests.PaymentInventoryIntegrationTestCase.test_cod_confirm_order_deducts_stock_immediately`.

No expone endpoints publicos (`payment/cod/urls.py` está vacío intencionalmente) — todas las
operaciones son invocadas internamente desde `orders` y desde el panel admin.

---

## 3. Sub-modulo `payment/cards/` — Tarjetas tokenizadas

### 3.1 `TokenizedCardViewSet` (`payment/cards/views.py`)

```python
class TokenizedCardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedActiveUser]
    lookup_field = 'uuid'

    def list(request)     # GET payment/cards/ — tarjetas activas del usuario
    def create(request)   # POST payment/cards/ — guardar nueva tarjeta
    def destroy(request, uuid)  # DELETE payment/cards/{uuid}/ — soft-delete
    @action set_default(request, uuid)  # POST payment/cards/{uuid}/set-default/
```

**Endpoints:**

| Metodo | URL | Descripcion |
|--------|-----|-------------|
| GET | `/api/v1/payment/cards/` | Lista tarjetas del usuario autenticado |
| POST | `/api/v1/payment/cards/` | Guarda nueva tarjeta tokenizada |
| DELETE | `/api/v1/payment/cards/{uuid}/` | Soft-delete (is_active=False, is_deleted=True) |
| POST | `/api/v1/payment/cards/{uuid}/set-default/` | Marca como tarjeta predeterminada |

**Comportamiento al eliminar la default:**
Al eliminar la tarjeta que era `is_default=True`, se promueve automaticamente la siguiente tarjeta activa del usuario (por `created_at` mas reciente) como nueva default.

**Registro en `payment/urls.py`:**
```python
path('cards/', include('payment.cards.urls'))
```

---

## 4. Sub-paquete `payment/nequi/` (cliente HTTP + ViewSet)

`payment/nequi/` maneja la comunicacion con la API externa de Nequi.
Sus **modelos viven en `payment/models.py`**, no en un modulo separado.

### 4.1 `payment/nequi/client.py` — `NequiApiClient`

```python
NequiApiClient.get_access_token() -> str
NequiApiClient.request_push_payment(phone, amount, reference) -> message_id
NequiApiClient.get_payment_status(message_id) -> 'PENDING'|'APPROVED'|'REJECTED'|'ERROR'
```

**Mapeo de status codes Nequi:** `'00'` → PENDING, `'20'` → APPROVED, `'09'` → REJECTED, `'96'` → ERROR

**URLs segun entorno:**

| Entorno | OAuth | API |
|---|---|---|
| sandbox | `oauth.sandbox.nequi.com` | `sandbox-api.nequi.com` |
| production | `oauth.nequi.com` | `api.nequi.com` |

> **Bug corregido 2026-07-03 (bloqueaba el checkout completo):** `WompiPaymentViewSet.initialize()` y
> `NequiPaymentViewSet.initialize()` comparaban `order.status` contra el string legacy `'pending'`,
> pero `OrderCommands.create_from_cart()` crea las órdenes con `Order.STATUS_PENDING_PAYMENT`
> (`'PENDING_PAYMENT'`) desde que se migró al "nuevo flujo de fulfillment". Efecto real: **toda orden
> recién creada era rechazada por `initialize/` con 400** ("La orden no esta pendiente de pago."),
> para ambos métodos de pago online. Corregido comparando contra `Order.STATUS_PENDING_PAYMENT` en los
> dos archivos. Cubierto por
> `payment.tests.PaymentInitializeAcceptsPendingPaymentStatusTestCase` (2 tests, uno por método).

### 4.2 `payment/nequi/services/commands.py` — `NequiCommands`

```python
NequiCommands.initialize_transaction(order, phone_number) -> NequiTransaction
NequiCommands.initialize_rental_transaction(rental_request, phone_number) -> NequiTransaction
NequiCommands.check_and_update_status(nequi_tx) -> NequiTransaction
    # Si APPROVED y tiene order → payment.shared.commands.confirm_order_payment()
    # Si APPROVED y tiene rental_request → renting.services.commands.RentalRequestCommands.confirm_payment()
```

### 4.3 Endpoints REST (`/api/v1/payment/nequi/`)

```
POST /api/v1/payment/nequi/initialize/
    Auth:   IsAuthenticatedActiveUser
    Body:   { order_uuid: UUID, phone_number: str (10 digitos) }
    Return: NequiTransactionSerializer (201)
    Error:  502 si NequiApiError, 403 si order.user != request.user

GET /api/v1/payment/nequi/status/?tx=<uuid>
    Auth:   IsAuthenticatedActiveUser
    Logica: Ownership vía NequiSelector.get_transaction_by_uuid(); si PENDING → llama
            check_and_update_status() en tiempo real
    Return: NequiTransactionSerializer (200)
```

---

## 5. Endpoints REST Wompi Online (`/api/v1/payment/payments/`)

Router registrado en `payment/online/urls.py`, montado en `payment/urls.py` bajo `payments/`.
`WompiPaymentViewSet` (`payment/online/api/views.py`) expone:

```
POST /api/v1/payment/payments/initialize/
    Auth:   IsAuthenticated
    Body:   { order_uuid: UUID, card_token?: str, payment_source_id?: int }
            card_token/payment_source_id son OPCIONALES y mutuamente excluyentes (ADR-001 Fase 2/3b,
            ver seccion 10.2) -- el checkout en vivo solo los envia desde el sub-metodo "Tarjeta".
    Return: { uuid, transaction_uuid, amount_in_cents, currency, status, wompi_id, correlation_id,
               public_key, integrity_signature, widget_url }
            wompi_id/correlation_id son campos NUEVOS y aditivos (Fase 2/4) -- si no se paso
            card_token/payment_source_id, wompi_id viene null (igual que siempre, hasta que el
            webhook lo rellene).
    Valida: order.user == request.user (via get_object_or_404), order.status == Order.STATUS_PENDING_PAYMENT
    Errores nuevos (ADR-001):
        400 -- se pasaron card_token Y payment_source_id a la vez
        403 -- card_token/payment_source_id presentes pero PaymentFeatureFlags.card_api_flow_enabled
               esta desactivado (kill-switch real, seccion 1.6 -- no solo oculta el boton en la UI)
        502 -- WompiApiError al crear la transaccion sincrona (Transaction.status queda 'ERROR')

GET /api/v1/payment/payments/feature-flags/
    Auth:   AllowAny (se consulta ANTES de que el usuario inicie sesion/pague, desde
            CheckoutView.vue al montar)
    Return: { card_api_flow_enabled: bool, widget_flow_enabled: bool }  -- 2do campo agregado
            2026-07-22 (seccion 1.6/10.6)
    Nota:   endpoint de SOLO LECTURA, distinto del endpoint de administracion
            (GET/PATCH dashboard/payment-transactions/feature-flags/, seccion 10.5) que si permite
            togglear ambos flags y vive en la app `dashboard`, no en `payment`.

POST /api/v1/payment/payments/webhook/
    Auth:   AllowAny (firma HMAC-SHA256 validada internamente con WOMPI_EVENTS_SECRET)
    Return: 200 OK siempre (o 400 si firma invalida)

GET /api/v1/payment/payments/transaction-status/?tx=<uuid>&id=<wompi_id opcional>
    Auth:   IsAuthenticated + ownership (order__user o rental_request__user)
    Logica: Igual que confirmation/ -- si status==PENDING, llama _sync_wompi_status()
            (con `id` como hint). Pensado como endpoint ligero para polling (usado por
            PaymentResultView.vue cada 5s mientras el pago esta PENDING).
    Uso:    consultado por OrderConfirmedView.vue y por el polling de PaymentResultView.vue

GET /api/v1/payment/payments/confirmation/?tx=<uuid>&id=<wompi_id opcional>
    Auth:   IsAuthenticated + ownership
    Logica: `tx` es SIEMPRE la clave primaria de busqueda (existe desde initialize()).
            `id` (ID de Wompi) es solo un hint opcional para _sync_wompi_status cuando
            wompi_id aun no esta guardado en BD -- nunca se usa como fuente de verdad
            del status (ver Fase 1 2026-07-07 mas abajo).
            Si status == PENDING → _sync_wompi_status() consulta la API de Wompi en vivo
            antes de responder (cubre el caso en que el usuario vuelve del widget antes
            de que llegue el webhook)
    Return: payload consolidado con payment/order/customer/shipping/service/timeline/next_steps,
            o bloque 'rental' en vez de 'order' si la Transaction es de una RentalRequest
    Uso:    consultado por PaymentResultView.vue

GET  /api/v1/payment/cards/
POST /api/v1/payment/cards/
DELETE /api/v1/payment/cards/{uuid}/
POST /api/v1/payment/cards/{uuid}/set-default/
    Auth:   IsAuthenticatedActiveUser
```

### 5.1 `_sync_wompi_status(wompi_tx, wompi_id_hint=None)` — fallback de sincronizacion activa

**Reescrito 2026-07-07** (bug real corregido, ver "Sincronizacion Wompi" mas abajo). Definida en
`payment/online/api/views.py`. Si la transaccion sigue `PENDING`, hace un GET directo a la API de
Wompi (`/v1/transactions/{wompi_tx.wompi_id or wompi_id_hint}`) con `WOMPI_PRIVATE_KEY`, actualiza
`status`/`payment_method_type` (y rellena `wompi_id` en BD si aun no estaba, usando el hint), y
cuando el status cambia delega en `WompiCommands.handle_status_change(wompi_tx, new_status)`. Usa
`select_for_update()` sobre la Transaction para no pisar una escritura concurrente del webhook, y
muta el objeto que le pasaron (no reasigna la variable local) para que el caller
(`confirmation()`/`transaction_status()`) vea los campos actualizados al construir su respuesta.

#### Bug corregido — reconciliacion no liberaba RentalRequest/Order en DECLINED/VOIDED (2026-07-14)

Roadmap de renting "Reconciliacion de pagos: verificar estado Wompi vs RentalRequest en caso de
discrepancia". Antes, `_sync_wompi_status()` solo manejaba `new_status == "APPROVED"`
(`PaymentCommands.confirm_payment()`); el webhook real (`process_webhook_notification()`) SI
manejaba `DECLINED/VOIDED/FAILED` (`RentalRequestCommands.release_on_payment_failure()` /
`ServiceCommands.release_slot_on_failure()`), pero esa rama vivia solo ahi. Si el webhook se
perdia o llegaba tarde y el fallback de reconciliacion (polling de `PaymentResultView` o la tarea
periodica `reconcile_pending_wompi_transactions`) descubria un `DECLINED`/`VOIDED`/`FAILED`, la
`Transaction` se actualizaba en BD pero el `RentalRequest`/`Order` asociado quedaba huerfano en
`pending_payment` -- exactamente la discrepancia Wompi-vs-RentalRequest que el roadmap pedia cerrar
(mitigado hasta ahora solo indirectamente por `renting/tasks.py::
expire_abandoned_pending_payment_requests`, que lo limpiaria recien a las 48h). Corregido
extrayendo la logica de branching (`APPROVED` → `confirm_payment`; `DECLINED/VOIDED/FAILED` →
`release_on_payment_failure`/`release_slot_on_failure` + `SecurityEvent.PAYMENT_DECLINED`) a
`WompiCommands.handle_status_change(wompi_tx, new_status)`, unica fuente de verdad usada ahora por
ambos caminos (`process_webhook_notification()` y `_sync_wompi_status()`).

#### Bug corregido — "Pago en proceso" atascado para siempre (2026-07-07)

Antes, `_sync_wompi_status()` se abortaba de inmediato si `wompi_tx.wompi_id` era `None` -- y
`wompi_id` **solo** se escribia desde el webhook. En el momento exacto en que el usuario vuelve del
widget (antes de que el webhook, asincrono, haya llegado), `wompi_id` siempre es `None`, asi que la
funcion nunca llegaba a consultar Wompi. Ademas `PaymentResultView.vue` solo hacia `load()` una vez
(sin polling), asi que aunque el webhook llegara despues la pantalla ya renderizada nunca se
enteraba. Corregido con:
1. `wompi_id_hint`: el callback del widget (`useWompiWidget.js`) ahora manda `id: tx.id` (el ID de
   Wompi, disponible de inmediato via `result.transaction.id`, sin llamada extra) junto a `tx` al
   navegar a `/payment/result` -- así el backend puede consultar Wompi aunque el webhook no haya
   llegado. El status en si SIEMPRE viene de la respuesta de la API de Wompi, nunca del hint (per
   la doc oficial: "Do not use the redirection as a validation method of your transactions").
2. Polling real en `PaymentResultView.vue` (mismo patron que `NequiPendingView.vue`): mientras el
   pago esta `PENDING`, consulta `transaction-status/` cada 5s (timeout 120s) y refresca el payload
   completo (`load()`) en cuanto el status deja de ser `PENDING`.
3. `payment/tasks.py::reconcile_pending_wompi_transactions` (Celery beat, `django_celery_beat`
   `DatabaseScheduler` -- el `PeriodicTask` se siembra via
   `payment/migrations/0008_seed_reconcile_periodic_task.py`, NO via un dict `CELERY_BEAT_SCHEDULE`
   en settings, que ese scheduler ignora por completo): cada 5 min re-consulta Wompi para
   Transactions `PENDING` con `wompi_id` ya conocido y mas de 1 minuto de antiguedad -- cubre al
   usuario que cierra la pestaña antes de que llegue el webhook o antes de volver a la pagina.
   **Segunda pasada (ADR-001 Fase 6, 2026-07-13):** Transactions `PENDING` **sin** `wompi_id` (Wompi
   no ofrece busqueda por `reference`, asi que estas NUNCA se pueden reconciliar de verdad) que
   superan 30 minutos de antiguedad se marcan **una sola vez** (no se re-marcan en corridas
   siguientes) con `TransactionEvent(processed=False)` + `SecurityEvent.PAYMENT_TRANSACTION_ABANDONED`
   -- visibles en `/panel/seguridad` y en el historial de la transaccion en `/panel/pagos`, en vez
   de quedar invisibles para siempre. `Transaction.status` **nunca** se toca en este caso -- sigue
   `PENDING`, fiel al ultimo estado real conocido de Wompi. El flujo de tarjeta backend-directo
   (seccion 10.2) reduce estructuralmente este problema porque `wompi_id` queda disponible desde la
   creacion, no solo con el webhook.

### 5.2 `_verify_wompi_event_signature(payload)` — validacion HMAC del webhook

Definida en `payment/online/api/views.py`. **Ya implementada** (no es un pendiente):
1. Extrae `signature.properties` y `signature.checksum` del payload.
2. Para cada propiedad, navega `payload['data']` y concatena el valor.
3. Concatena `str(timestamp) + WOMPI_EVENTS_SECRET`.
4. Compara SHA256 calculado vs `checksum` con `hmac.compare_digest` (timing-safe).
5. Si `WOMPI_EVENTS_SECRET` no esta configurado, **loggea warning y permite el paso** (modo desarrollo) —
   antes de ir a produccion, `WOMPI_EVENTS_SECRET` debe estar seteado siempre.

---

## 6. Flujos end-to-end por metodo de pago

### 6.1 Wompi (dos sub-flujos desde ADR-001 Fase 3b, 2026-07-13)

`CheckoutView.vue`, al elegir "Pago en linea", ofrece un sub-selector: **Tarjeta** (backend-directo,
default, solo si `PaymentFeatureFlags.card_api_flow_enabled`) y **PSE / Otros** (Widget completo,
sin cambios respecto a como funcionaba este proyecto siempre). Ver seccion 10 para el detalle
completo del diseno; aqui solo los flujos end-to-end.

**6.1.a — Tarjeta (nueva o guardada), backend-directo:**
```
1. POST orders/orders/create_from_cart/ {payment_method:'WOMPI'} → Order.status = 'PENDING_PAYMENT'
   (si es tarjeta NUEVA, este paso ocurre DESPUES de tokenizar -- ver seccion 10.2 -- para no dejar una
   orden huerfana si la tokenizacion falla)
2. POST payment/payments/initialize/ {order_uuid, card_token} → WompiCommands crea la Transaction
   Y la crea SINCRONAMENTE en Wompi (WompiApiClient, seccion 10.1) -- wompi_id/status disponibles
   de inmediato, sin abrir ningun widget
3. Frontend redirige directo a /payment/result?tx=<uuid> (PaymentResultView.vue hace polling si
   sigue PENDING, igual que siempre)
4. Wompi: POST /api/v1/payment/payments/webhook/ {status:'APPROVED'} -- SIGUE siendo la unica
   fuente de verdad autoritativa (nunca se confia en la respuesta sincrona del paso 2 por si sola)
   → WompiCommands.process_webhook_notification() → PaymentCommands.confirm_payment()
     → confirm_order_payment() → order='paid', stock deducido, SecurityEvent.PAYMENT_APPROVED
```

**6.1.b — PSE / Otros, Widget completo (sin cambios de comportamiento respecto a como funcionaba
este proyecto antes de ADR-001):**
```
1. POST orders/orders/create_from_cart/ {payment_method:'WOMPI'} → Order.status = 'PENDING_PAYMENT'
2. POST payment/payments/initialize/ {order_uuid} (SIN card_token) → Transaction(PENDING) +
   integrity_signature, comportamiento identico al de siempre
3. openWompiWidget(data) → usuario paga en widget embebido (tarjeta, PSE, Bancolombia...)
4. Wompi: POST /api/v1/payment/payments/webhook/ {status:'APPROVED'}
   → WompiCommands.process_webhook_notification() → PaymentCommands.confirm_payment()
     → confirm_order_payment() → order='paid', stock deducido, SecurityEvent.PAYMENT_APPROVED
5. Frontend → /payment/result (PaymentResultView.vue consulta payment/payments/confirmation/,
   que fuerza sync via _sync_wompi_status() si sigue PENDING)
```

### 6.2 COD (contra entrega)

```
1. POST orders/orders/create_from_cart/ {payment_method:'COD'}
   → Order.status = 'processing'
   → CodCommands.confirm_order()
     → _deduct_inventory_for_order() (INMEDIATO)
     → CodTransaction(CONFIRMED)
     → on_commit: dispatch_notification('order_cod_confirmed')
2. Frontend: cartStore.reset() → /orden-confirmada?status=COD_APPROVED&order_uuid=<uuid>
```

### 6.3 Nequi Push

```
1. POST orders/orders/create_from_cart/ {payment_method:'NEQUI'} → Order.status = 'pending'
2. POST payment/nequi/initialize/ {order_uuid, phone_number}
   → push al celular del usuario → NequiTransaction(PENDING)
3. Frontend → /nequi-pendiente?tx=<uuid>
4. NequiPendingView.vue: polling GET payment/nequi/status/?tx=<uuid> cada 5s (max 180s)
   → Si APPROVED → confirm_order_payment() → order='paid'
5. Si APPROVED → /mi-cuenta/pedidos
   Si REJECTED/ERROR/TIMEOUT → pantalla de error con boton retry
```

### 6.4 Wompi/Nequi para RentalRequest

`Transaction` y `NequiTransaction` tambien pueden vincularse a una `renting.RentalRequest` (campo
`rental_request` en vez de `order`). El flujo es equivalente, pero al aprobarse el pago:
- `PaymentCommands.confirm_payment()` detecta `rental_request_id` y delega directamente a
  `RentalRequestCommands.confirm_payment(rental_request)` (no pasa por `confirm_order_payment`).
- `NequiCommands.check_and_update_status()` hace la misma bifurcacion.
- El endpoint `confirmation/` devuelve un bloque `rental` en vez de `order`/`shipping`/`service`.

---

## 7. Configuracion

```env
WOMPI_PUBLIC_KEY=pub_test_...
WOMPI_PRIVATE_KEY=prv_test_...
WOMPI_INTEGRITY_SECRET=test_integrity_...
WOMPI_EVENTS_SECRET=test_events_...
WOMPI_ENVIRONMENT=test
WOMPI_WIDGET_URL=...

NEQUI_CLIENT_ID=your_client_id
NEQUI_CLIENT_SECRET=your_client_secret
NEQUI_API_KEY=your_api_key
NEQUI_ENVIRONMENT=sandbox
```

```python
INSTALLED_APPS = [
    ...
    'payment',   # SSoT de pagos — Wompi Online, COD, Nequi y tarjetas tokenizadas
]
```

```python
# ecommerce/urls.py
path('api/v1/payment/', include('payment.urls')),
```

---

## 8. Migraciones

| App | Migracion | Contenido |
|---|---|---|
| `payment` | `0001_initial` | Modelo `Transaction` |
| `payment` | `0002_transaction_is_deleted` | Soft-delete en `Transaction` |
| `payment` | `0003_codtransaction_nequitransaction_and_more` | `CodTransaction` + `NequiTransaction` |
| `payment` | `0004_multipayment` | Soporte multi-pago |
| `payment` | `0005_tokenizedcard` | Modelo `TokenizedCard` (FK a AUTH_USER_MODEL) |
| `payment` | `0006_transaction_rental_request_alter_transaction_order` | `Transaction`/`NequiTransaction` vinculables a `RentalRequest`, `order` pasa a nullable |
| `payment` | `0007_alter_transaction_status_and_more` | `db_index` en `Transaction.status`; `CheckConstraint` "exactamente uno de order/rental_request" en `Transaction` y `NequiTransaction`; `UniqueConstraint` "un solo default por usuario" en `TokenizedCard` (Fase 6, auditoria de BD) |
| `payment` | `0008_seed_reconcile_periodic_task` | Siembra el `PeriodicTask`/`CrontabSchedule` de `reconcile_pending_wompi_transactions` (cada 5 min, `django_celery_beat.DatabaseScheduler`) |
| `payment` | `0009_transaction_correlation_id_transactionevent` | `Transaction.correlation_id` + modelo nuevo `TransactionEvent` (ADR-001 Fase 4) |
| `payment` | `0010_paymentfeatureflags` | Modelo nuevo `PaymentFeatureFlags` (ADR-001 Fase 5) |
| `payment` | `0011_seed_notify_declined_payments_periodic_task` | Siembra `PeriodicTask` de notificacion de pagos rechazados (previo a esta auditoria) |
| `payment` | `0012_transaction_initiation_channel` | Campo `Transaction.initiation_channel` (2026-07-22) |
| `payment` | `0013_paymentfeatureflags_widget_flow_enabled` | Campo `PaymentFeatureFlags.widget_flow_enabled` (2026-07-22) |
| `security` | `0004_alter_securityevent_event_type` | Agrega `PAYMENT_APPROVED` a `EVENT_CHOICES` (ADR-001 Fase 4) |
| `security` | `0005_alter_securityevent_event_type` | Agrega `PAYMENT_TRANSACTION_ABANDONED`/`PAYMENT_FEATURE_FLAG_CHANGED` a `EVENT_CHOICES` (ADR-001 Fase 8) |
| `orders` | `0008_order_payment_method` | Campo `payment_method` en `Order` |
| `orders` | `0009_alter_order_payment_method` | Agrega `NEQUI` a los choices |

---

## 9. Anti-patrones especificos de pagos

| Prohibido | Alternativa correcta |
|---|---|
| Definir modelo de transaccion fuera de `payment/models.py` | Agregar el modelo en `payment/models.py` |
| Re-implementar `_deduct_inventory_for_order()` en otra app | Importar desde `payment.shared.commands` |
| Llamar `InventoryCommands.register_exit()` directamente por pago | Solo via `_deduct_inventory_for_order()` |
| Setear `order.status = Order.STATUS_PAID` fuera de `confirm_order_payment()` | Siempre delegar a esa funcion |
| Crear logica COD en `orders/services/commands.py` | Delegar a `CodCommands.confirm_order()` |
| Usar `float` para montos de pago | `Decimal` siempre |
| Eliminar `TokenizedCard` con `.delete()` | Soft-delete: `is_deleted=True; save()` (el modelo NO tiene campo `is_active`) |
| Acceder a `NequiTransaction` sin validar ownership | Usar `NequiSelector.get_transaction_by_uuid(uuid, user)` |
| Inicializar pago sin verificar `order.user == request.user` | Siempre validar ownership |
| Stubear `_deduct_inventory_for_order` / `_has_sufficient_stock` "temporalmente" para desacoplar de `inventory` sin conectar un reemplazo real | Si se desacopla, hacerlo en un solo cambio atomico que reemplace ambas puntas (shared + online) por el mecanismo nuevo (signal/API), nunca dejar un no-op en produccion |
| Inventar un estado nuevo en `Transaction.status` (ej. `EXPIRED`, `ABANDONED`, `TIMEOUT`) | Los 5 estados reales de Wompi (`PENDING/APPROVED/DECLINED/VOIDED/ERROR`) son los unicos validos -- un timeout de UI o una transaccion abandonada se representan con `TransactionEvent`/`SecurityEvent`, nunca mutando `status` |
| Llamar a la API real de Wompi (sandbox o produccion) desde un test o una verificacion manual sin autorizacion explicita del usuario | Mockear `WompiApiClient`/`requests`/`page.route()` en tests y verificaciones; una llamada real solo se hace con permiso explicito, caso por caso (ADR-001, todas las fases) |
| Usar `dispatch_notification()` para alertas puramente operativas/internas cuando el unico `user` disponible es el cliente de la transaccion | Usar `SecurityEvent`/`SecurityCommands.log_event()` -- cero riesgo de notificar por error al cliente vía email/WhatsApp (ADR-001 Fase 8) |
| Togglear `PaymentFeatureFlags` directo con `PaymentFeatureFlags.objects.filter(...).update(...)` | Usar `PaymentFeatureFlags.set_card_api_flow_enabled()` o pasar por los 2 endpoints ya auditados (panel Vue / Django admin) -- un `.update()` directo salta el log de `SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED` |

---

## 10. Migracion a integracion API propia con Wompi (ADR-001, 2026-07-13)

Proyecto de 10 fases, todas completas. Documento de diseno completo:
`payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md`; informe detallado por fase:
`payment/.AGENT/docs/FASE{0..9}_*.md`. Resumen de lo que cambio realmente en el codigo (el "por que"
y el detalle de cada decision viven en esos documentos, no se repiten aqui):

### 10.1 `WompiApiClient` (`payment/online/wompi_client.py`, Fase 2) — el adaptador

Cliente HTTP aislado hacia la API de Wompi, calcado del patron ya probado en
`payment/nequi/client.py::NequiApiClient` (sin logica de negocio de Sintel adentro, solo HTTP +
serializacion). Contrato validado contra `docs.wompi.co`, no asumido:

```python
WompiApiClient.get_acceptance_tokens() -> dict
    # GET /merchants/{public_key} (llave PUBLICA, sin Bearer) -- acceptance_token/
    # accept_personal_auth son JWT presignados CON EXPIRACION, se piden frescos en
    # cada llamada, nunca se cachean

WompiApiClient.create_payment_source(*, card_token, customer_email) -> dict
    # POST /payment_sources (llave PRIVADA) -- NO USADO hoy en el flujo real (ver 10.2,
    # TokenizedCard.token_id ya es reutilizable directo, nunca hizo falta el concepto
    # de "payment source" de Wompi) -- se deja implementado y testeado por si algun
    # caso futuro lo necesita

WompiApiClient.create_transaction(*, amount_in_cents, currency, reference, customer_email,
                                    signature, payment_source_id=None, card_token=None,
                                    installments=1, redirect_url=None) -> dict
    # POST /transactions (llave PRIVADA) -- exactamente uno de payment_source_id/card_token

WompiApiClient.get_transaction(wompi_id) -> dict
    # GET /transactions/{wompi_id} (llave PRIVADA) -- reemplaza el requests.get() crudo
    # que antes vivia embebido en _sync_wompi_status()
```

**Excepciones:** `WompiApiError` (definitivo, 4xx, no reintentable), `WompiApiTransientError`
(timeout/5xx, reintentable), `WompiDuplicateReferenceError` (**Wompi NO deduplica por
`reference`** -- reintentar con el mismo reference da 422 "Duplicate reference", nunca la
transaccion ya creada; en la practica casi imposible aqui porque `reference` es siempre un UUID
recien generado por `initialize_transaction()`).

**Este cliente NO expone ningun metodo de tokenizacion a proposito** — la tokenizacion de tarjeta
(`POST /tokens/cards`) nunca debe pasar por el backend, es responsabilidad exclusiva del navegador
(ver 10.3).

### 10.2 Flujo de tarjeta backend-directo (Fases 2-3, checkout real)

Ver seccion 6.1.a para el flujo end-to-end. Piezas de codigo:
- `WompiCommands.initialize_transaction(..., card_token=, payment_source_id=)` y
  `WompiCommands._create_transaction_sync(...)` (seccion 2.3).
- `WompiPaymentViewSet.initialize()` (seccion 5) — kill-switch del feature flag, mint del
  `correlation_id`.
- **Alcance real, decidido explicitamente:** este flujo aplica SOLO a tarjeta (nueva o guardada).
  **PSE queda excluido a proposito** — sigue usando el Widget completo porque requiere
  redireccion al banco, no es algo que se pueda eliminar; no es una limitacion tecnica pendiente.

### 10.3 Tokenizacion automatica de tarjeta (Fase 3a, frontend)

`frontend/src/composables/useCardTokenization.js` — `tokenizeCard()` hace un `fetch()` **directo
desde el navegador hacia `https://api.wompi.co/v1/tokens/cards`** con la llave publica
(`VITE_WOMPI_PUBLIC_KEY`, en `frontend/.env.development`/`.env.production`, misma llave que
`WOMPI_PUBLIC_KEY` del backend — segura de exponer en el bundle por diseno, es literalmente para
eso que existen las llaves publicas). Deliberadamente **nunca usa `useApi()`/axios** — los datos
crudos de tarjeta (numero, CVC) no deben acercarse a nuestro backend en ningun punto.

Usado desde 2 lugares:
- `CustomerCardsView.vue` (`/mi-cuenta/tarjetas`) — alta de tarjeta guardada (seccion 1.4).
- `CheckoutView.vue` (sub-metodo "Tarjeta") — tarjeta nueva en el checkout, que **siempre se guarda**
  automaticamente (decision del usuario, sin checkbox opcional) antes de usarse para pagar.

### 10.4 `CheckoutView.vue` — sub-metodo Tarjeta (Fase 3b)

Dentro de "Pago en linea": sub-botones **Tarjeta** (default, oculto si el feature flag esta
desactivado) / **PSE / Otros**. El sub-metodo Tarjeta:
1. Carga tarjetas guardadas (`GET payment/cards/`) al montar la pagina.
2. Permite elegir una guardada, o "Agregar tarjeta nueva" (mismo `useCardTokenization`, 10.3).
3. Al enviar: resuelve el `card_token` **antes** de crear direccion/orden -- si la tokenizacion
   falla, no queda ninguna orden huerfana (mejora real sobre el comportamiento historico del
   checkout, que siempre creaba la orden primero).
4. `POST payment/payments/initialize/` con `{order_uuid, card_token}` -- el backend crea la
   transaccion sincrona en Wompi (10.2). Redirect directo a `/payment/result?tx=...`, **sin abrir
   ningun widget**.

### 10.5 Panel administrativo de pagos (Fase 7 — antes 100% de solo lectura)

`AdminPaymentViewSet` (`dashboard/api/views.py`, montado en `/api/v1/dashboard/payment-transactions/`)
gano 3 acciones sobre la base de lectura ya existente (seccion "Vista centralizada de transacciones"):

```
POST /api/v1/dashboard/payment-transactions/{uuid}/resync/
    Auth: IsAuthenticated + IsAdminUser (is_staff Y is_superuser)
    Dispara _sync_wompi_status() bajo demanda (mismo camino que /payment/result y la
    reconciliacion periodica). 409 si la transaccion no tiene wompi_id (nada que consultar).

GET /api/v1/dashboard/payment-transactions/{uuid}/events/
    Historial TransactionEvent de una transaccion (seccion 1.5), mas reciente primero.

GET/PATCH /api/v1/dashboard/payment-transactions/feature-flags/
    Consulta/actualiza PaymentFeatureFlags.card_api_flow_enabled Y widget_flow_enabled
    (seccion 1.6, 2do flag agregado 2026-07-22) desde el panel Vue, sin salir a /admin/ de
    Django, en un solo PATCH. Dispara SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED
    (seccion 1.7) por cada flag que realmente cambia (no si el valor enviado es igual al actual).
```

Reflejado en `PaymentTransactionsAdminView.vue`: columna "Acciones" nueva **solo** en la pestaña
Wompi (Nequi/COD no tienen el mismo problema de reconciliacion, sin cambios ahi) con botones
"Reconciliar"/"Historial", mas **dos** switches de feature flag arriba de las pestañas ("Flujo de
pago con tarjeta via API" / "Flujo de pago via Widget (PSE/Otros)", 2026-07-22) y una columna
"Canal" nueva (badge "Tarjeta (API)"/"Widget", derivada de `Transaction.initiation_channel`,
seccion 1.1) para diagnosticar de un vistazo por que ruta se proceso cada transaccion.

**Capas nuevas:** `PaymentAdminSelector.get_wompi_transaction()`/`list_transaction_events()`
(`payment/services/selectors.py`); `PaymentAdminOrchestrator.resync_wompi_transaction()`/
`list_transaction_events()`/`get_feature_flags()`/`set_card_api_flow_enabled()`/
`set_widget_flow_enabled()` (2026-07-22) (`dashboard/services/admin_orchestrators.py`, delega la
mutacion real a `PaymentFeatureFlags.set_card_api_flow_enabled()`/`set_widget_flow_enabled()`,
siguiendo el mismo patron ya usado en `NotificationAdminOrchestrator.update_template()`); helper
module-level `_log_feature_flag_change()` (`dashboard/api/views.py`, 2026-07-22) que centraliza el
disparo condicional de `SecurityEvent.PAYMENT_FEATURE_FLAG_CHANGED` para los 2 flags.

### 10.6 Generalizacion a Servicios/Renting + kill-switch simetrico + smoke test E2E (2026-07-22)

Hasta este punto, el flujo hibrido Tarjeta/Widget (10.2-10.4) solo existia realmente en
`CheckoutView.vue` (Shop) -- Servicios Tecnicos y Renting seguian con el Widget completo como unico
camino. Esta fase lo generaliza a las 3 superficies de checkout que ofrecen Wompi, a pedido
explicito del usuario ("Eliminar el Widget como mecanismo principal de pago para tarjetas,
definitivamente"), y agrega el kill-switch simetrico (10.5's `card_api_flow_enabled` ya existia;
`widget_flow_enabled`, seccion 1.6, es nuevo).

**Extraccion de composable/componente compartido (frontend):**
- `frontend/src/composables/useCardOrWidgetPayment.js` -- estado (`wompiSubMethod`,
  `cardApiFlowEnabled`, `widgetFlowEnabled`, `savedCards`, `loadingCards`, `selectedCardId`,
  `newCardRaw`, `cardStepValid`) + funciones (`fetchFeatureFlags`, `fetchSavedCards`,
  `resolveCardToken`, `resetNewCard`) que antes estaban duplicadas linea por linea en
  `CheckoutView.vue`.
- `frontend/src/components/shared/checkout/CardOrWidgetPanel.vue` -- UI presentacional
  (tabs Tarjeta/PSE, lista de tarjetas guardadas, formulario de tarjeta nueva), props/emits puro.
- Usado hoy identico por `CheckoutView.vue` (Shop), `ServiceCheckoutModal.vue` (Servicios
  Tecnicos, reemplaza el antiguo `ServicePaymentMethodSelector.vue` documentado en
  `technical_services/.AGENT/docs/ARQUITECTURA_COMPLETA_SERVICES.md` §13.4) y
  `RentalConfirmationView.vue` (Renting, reemplaza el Widget-only descrito en
  `renting/.AGENT/docs/ARQUITECTURA_COMPLETA_RENTIG.md` "Integracion con Wompi").
- **Kill-switch backend simetrico replicado en Renting:** `renting/api/views.py::process_payment()`
  gano el mismo par de checks 403 que `WompiPaymentViewSet.initialize()` (seccion 1.6) -- antes
  Renting no tenia ningun kill-switch backend para su pago online.

**2 bugs reales encontrados durante el smoke test E2E de esta fase (no introducidos por la
extraccion en si, pero SI propagados a las 3 superficies porque comparten el mismo codigo):**

1. **`_serialize_card()` sin `token_id`** (seccion 1.4) -- afectaba a Shop desde 2026-07-13, y ahora
   tambien a Servicios/Renting por compartir `useCardOrWidgetPayment.js`. Corregido agregando el
   campo faltante.
2. **Tarjetas guardadas nunca cargaban en Servicios/Renting** -- `ServiceCheckoutModal.vue` y
   `RentalConfirmationView.vue` disparaban `fetchSavedCards()` desde un `watch()` sobre el metodo de
   pago (`store.paymentMethod`/`method`) **sin `{ immediate: true }`**. Como `'WOMPI'` ya es el
   valor por defecto de ese ref/estado al montar el checkout, el watcher nunca detectaba un
   "cambio" real y `fetchSavedCards()` jamas se ejecutaba -- el usuario solo veia "Agregar tarjeta
   nueva", nunca sus tarjetas ya guardadas. `CheckoutView.vue` (Shop) no tenia este bug porque
   llama `fetchSavedCards()` sin condicion en su `onMounted`. Corregido agregando
   `{ immediate: true }` a ambos watchers. Verificado end-to-end en las 3 superficies: pago con
   tarjeta guardada resuelve `Transaction.status='APPROVED'` / `initiation_channel='CARD_API'`.

**Gap real encontrado, NO corregido (fuera de alcance de esta auditoria, requiere credenciales que
el usuario no tiene a mano):** el checkout de Shop (`CheckoutView.vue`) no oculta la opcion "Nequi
Push" aunque `NEQUI_CLIENT_ID`/`NEQUI_CLIENT_SECRET`/`NEQUI_API_KEY` sigan siendo placeholders en
`.env` -- a diferencia de `RentalConfirmationView.vue`, que si consulta y oculta Nequi cuando no
esta configurado (ver comentario `nequiEnabled` en ese archivo). Si un cliente de Shop selecciona
Nequi y paga, `payment/nequi/initialize/` intentaria un OAuth real contra
`oauth.sandbox.nequi.com` con credenciales invalidas y respondería `502 Bad Gateway` (no crashea,
pero es una experiencia de cliente rota). Pendiente: replicar en `CheckoutView.vue` el mismo patron
de `nequiEnabled` que ya usa Renting.

---

## 11. Guia para agregar un nuevo metodo de pago

```
1. payment/models.py → class NuevoMetodoTransaction(SintelBaseModel)
2. payment/<nuevometodo>/services/commands.py → class NuevoMetodoCommands:
       initialize_transaction(order, ...) -> NuevoMetodoTransaction
       check_and_update_status(tx) -> NuevoMetodoTransaction
         → Al APPROVED: llamar payment.shared.commands.confirm_order_payment(order, reference)
3. orders/models.py → PAYMENT_METHOD_CHOICES += [('NUEVOMETODO', 'Nombre')]
4. orders/services/commands.py → bloque if payment_method == 'NUEVOMETODO'
5. Si tiene API externa → crear subpaquete payment/nuevometodo/ con:
       client.py  → solo HTTP client
       api/        → ViewSet + Serializers
       services/commands.py → delega a payment.shared.commands
6. ecommerce/settings/base.py → variables NUEVOMETODO_*
7. .env → credenciales placeholder
8. payment/urls.py → path('nuevometodo/', include('payment.nuevometodo.urls'))
9. Frontend → CheckoutView.vue + vista pendiente si async
10. Migraciones: makemigrations payment orders && migrate
```
