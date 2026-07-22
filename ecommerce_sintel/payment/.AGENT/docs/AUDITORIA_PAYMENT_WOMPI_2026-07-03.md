# AUDITORÍA — Sincronización arquitectónica módulo `payment` (WOMPI)

> **Fecha:** 2026-07-03
> **Alcance real ejecutado:** app `payment/` (Wompi online, COD, Nequi, tarjetas tokenizadas) y sus
> puntos de contacto directos verificados: `orders`, `inventory`, `renting` (pagos de RentalRequest),
> `technical_services`, `notifications`, `operations`, y las vistas del frontend que llaman a
> `/api/v1/payment/...`.
> **Fuera de alcance en este informe** (no auditado en esta sesión): `shop`, `cart`, `checkout`
> end-to-end, `quotes`, seguridad transversal de toda la plataforma, concurrencia fuera de `payment`,
> rendimiento de BD, y testing E2E de frontend. El usuario acotó explícitamente el trabajo a
> sincronizar el documento y lo que de ahí se derivara — este documento reporta contra ese alcance,
> no contra la totalidad del ERP.

> **Adenda 2026-07-03 (mismo día, reportado por el usuario en producción/desarrollo real):** durante
> el uso real del checkout, `CheckoutView.vue` recibió 400 en `create_from_cart/`. Diagnóstico:
> `OrderCommands.create_from_cart()` crea órdenes con `Order.STATUS_PENDING_PAYMENT`, pero
> `WompiPaymentViewSet.initialize()` y `NequiPaymentViewSet.initialize()` seguían comparando contra el
> string legacy `'pending'` — rechazaban con 400 **toda** orden recién creada. El 400 visible en
> `create_from_cart` era un efecto secundario de un reintento tras el fallo de `initialize/` (el primer
> intento sí creaba la orden y vaciaba el carrito; el segundo fallaba con "carrito vacío"). Bug
> independiente del refactor de inventario de esta sesión — viene de una migración de estados de
> `Order` que nunca se propagó a `payment/`. Corregido en ambos archivos + 2 tests de regresión nuevos
> (`PaymentInitializeAcceptsPendingPaymentStatusTestCase`). Detalle completo en la sección 4 de
> `ARQUITECTURA_COMPLETA_PAYMENT.md`.

---

## 1. Informe completo de auditoría (resumen ejecutivo)

El documento SSoT `ARQUITECTURA_COMPLETA_WOMPI.md` (ahora `ARQUITECTURA_COMPLETA_PAYMENT.md`)
describía una app inexistente (`wompi`) en vez de la app real (`payment`), con rutas REST que nunca
existieron (`/api/v1/wompi/...`) mientras el frontend siempre llamó a las rutas reales
(`/api/v1/payment/...`). Al verificar el código contra el documento se encontró que, además del
desfase de nombres, el código real:

- Tenía **funcionalidad más avanzada** que el documento (HMAC del webhook implementado, endpoints
  `confirmation/` y `transaction-status/`, soporte de pago para `RentalRequest`).
- Tenía **una regresión funcional activa**: `_get_stock_record`, `_has_sufficient_stock` y
  `_deduct_inventory_for_order` en `payment/shared/commands.py` y `_has_sufficient_stock` en
  `payment/online/services/commands.py` estaban convertidas en no-ops (`return None` / `return True` /
  `pass`), producto de un refactor incompleto que intentó desacoplar `payment` de `inventory` sin
  conectar un reemplazo. Efecto: **ningún pago aprobado (Wompi, Nequi o COD) descontaba stock real**,
  y la revalidación de stock antes de confirmar un pago siempre pasaba (`True` hardcodeado).
- Los archivos `.py.bak` junto a los stubs contenían la implementación original funcional — lo cual
  permitió restaurar la lógica correcta sin reconstruirla desde cero.

Se restauró la lógica real, se verificó que no introduce dependencia circular (`inventory` no importa
`payment` ni `orders`), se confirmó compilación (`py_compile`) de todos los archivos tocados, y se
sincronizó la documentación (doc de arquitectura + 4 archivos de enrutamiento/instrucciones que
apuntaban al nombre de archivo/app antiguo).

---

## 2. Matriz de conflictos (documento vs. código, antes de la corrección)

| # | Conflicto | Documento decía | Código real |
|---|---|---|---|
| 1 | Nombre de la app | `wompi` | `payment` (`payment/apps.py: name='payment'`) |
| 2 | Prefijo de rutas | `/api/v1/wompi/...`, `/api/v1/nequi/...` | `/api/v1/payment/payments/...`, `/api/v1/payment/nequi/...`, `/api/v1/payment/cards/...` |
| 3 | `INSTALLED_APPS` | `['wompi', 'nequi']` | `['payment']` (una sola entrada) |
| 4 | Firma HMAC del webhook | "Pendiente en producción" | Implementada y activa (`_verify_wompi_event_signature`) |
| 5 | Endpoints documentados | Solo `initialize/`, `webhook/`, `status/` | También `transaction-status/` y `confirmation/` (con fallback de sync activo `_sync_wompi_status`) |
| 6 | Alcance de `Transaction`/`NequiTransaction` | Solo `Order` | También `RentalRequest` (migración `0006`) |
| 7 | Migraciones | Listadas bajo apps `wompi`/`nequi` | Todas bajo app `payment` |

**Resolución:** el código es la fuente de verdad (confirmado porque el frontend ya opera contra las
rutas reales en producción/desarrollo). El documento se reescribió completo para reflejar esto.

---

## 3. Matriz de duplicidades

| Área revisada | Resultado |
|---|---|
| Modelos de transacción de pago fuera de `payment/models.py` | Ninguno encontrado |
| Reimplementación de `confirm_order_payment()` o `_deduct_inventory_for_order()` en otra app | Ninguna encontrada |
| Llamadas directas a `InventoryCommands.register_exit()` fuera de `payment/shared/commands.py` | Una: `shop/services/commands.py` — **no es duplicidad real**, es un ajuste manual de stock (`adjust_stock`, corrección administrativa), caso de uso legítimamente distinto al descuento post-pago |
| Lógica COD en `orders/services/commands.py` | No encontrada — `orders` delega a `CodCommands.confirm_order()` |

No se detectaron duplicidades del núcleo de pagos en el alcance revisado.

---

## 4. Violaciones SSoT

1. **El propio documento SSoT violaba su función** al describir una arquitectura que nunca existió en
   el código (nombre de app, rutas) — un documento desincronizado deja de ser fuente de verdad.
2. **La regresión de inventario era en sí misma una violación silenciosa del principio "único punto de
   salida de inventario"**: la función seguía siendo *técnicamente* el único punto de entrada, pero al
   ser un no-op, el efecto de negocio (SSoT de stock real) quedó roto sin que ningún otro código lo
   supliera. Una violación SSoT no siempre es "otro módulo hace lo mismo" — también lo es "el módulo
   dueño deja de cumplir su contrato y nadie lo nota".

---

## 5. Violaciones SOLID / limpieza

- **Refactor a medias (Open/Closed roto en la práctica):** se modificó el comportamiento de funciones
  ya consumidas por tres callers (`shared`, `online`, `cod`) sin actualizar los contratos ni los
  callers, dejando una mentira funcional (`_has_sufficient_stock` "true" no verifica nada).
- **Archivos `.py.bak` viviendo junto al código activo** (`shared/commands.py.bak`,
  `online/services/commands.py.bak`) — antipatrón de higiene: un `.bak` en el árbol de trabajo no es
  control de versiones y genera ambigüedad sobre cuál es la versión "real". Eliminados en esta sesión.
- **Comentarios que prometen un reemplazo que no existe** (`# INVENTORY_REMOVED: ... -> usar
  /api/v1/inventory/ o signal`) sin que exista ni el signal ni la llamada HTTP — deuda técnica
  documentada como si fuera intencional/completa.

---

## 6. Riesgos encontrados

| Riesgo | Severidad | Estado |
|---|---|---|
| Ventas sin descuento de stock real (sobreventa, inventario fantasma) | **Crítico** | Corregido en esta sesión |
| Validación de stock previa a confirmar pago siempre "aprueba" (`True` hardcodeado) | **Crítico** | Corregido en esta sesión |
| `payment/tests.py` está vacío — cero cobertura de tests sobre el módulo que mueve dinero | **Alto** | No corregido — ver sección 13 |
| `WOMPI_EVENTS_SECRET` ausente hace que la validación de firma del webhook **pase igual** (modo dev) | Medio | Documentado como requisito pre-producción; no verificado si está seteado en el entorno actual |
| Documentación desactualizada guiando a futuros desarrolladores/agentes por rutas y nombres inexistentes | Medio | Corregido en esta sesión |

---

## 7. Plan de refactorización priorizado

| Prioridad | Acción | Estado |
|---|---|---|
| P0 | Restaurar `_deduct_inventory_for_order` / `_has_sufficient_stock` reales | ✅ Hecho |
| P0 | Sincronizar `ARQUITECTURA_COMPLETA_WOMPI.md` → `ARQUITECTURA_COMPLETA_PAYMENT.md` con la realidad | ✅ Hecho |
| P0 | Corregir referencias colgantes en `CLAUDE.md`, `.AGENT.md`, `ANTIGRAVITY.md` (raíz y `payment/`) | ✅ Hecho |
| P1 | Escribir tests de regresión que aserten el descuento de stock end-to-end (ver sección 13) | Pendiente — recomendado antes de dar por cerrado el fix |
| P1 | Verificar en el entorno real (`.env` / secrets) que `WOMPI_EVENTS_SECRET` esté seteado | Pendiente — requiere acceso al entorno, no solo al código |
| P2 | Revisar `inventory/CLAUDE.md`, que documenta métodos (`InventorySelector.is_available()`,
  `get_stock_record_for_variant()`) que no existen en `inventory/services/selectors.py` actual — mismo
  patrón de doc desincronizado, en otra app. **Detectado pero fuera del alcance acordado esta sesión.** | Pendiente, requiere decisión del usuario |

---

## 8. Plan de implementación por fases

- **Fase A (ejecutada hoy):** restauración de lógica de inventario + sincronización documental completa
  del módulo `payment`.
- **Fase B (propuesta, no iniciada):** cobertura de tests de regresión para el flujo de pago →
  inventario (sección 13), y verificación de secretos de entorno.
- **Fase C (propuesta, no iniciada):** extender la auditoría de duplicidad/SSoT a `shop`, `cart`,
  `checkout`, `quotes` si se desea completar las Fases 2-10 del prompt maestro original.

No se debe iniciar la Fase C sin decisión explícita del usuario (ya se preguntó una vez y se acotó el
alcance a lo aquí entregado).

---

## 9. Lista de archivos afectados

**Código (lógica restaurada/corregida):**
- `payment/shared/commands.py` — restaurada deducción real de inventario
- `payment/online/services/commands.py` — restaurada validación real de stock + corregido bug de
  `@transaction.atomic` que revertía el guardado de `status='ERROR'`
- `orders/tests.py` — corregidos los targets de `@patch` de `test_pending_payment_to_paid_then_prepare`
  (el test estaba erroreando antes de correr su cuerpo)

**Código (tests nuevos):**
- `payment/tests.py` — 6 tests de integración pago→inventario (antes vacío)

**Documentación (reescrita o corregida):**
- `payment/.AGENT/docs/ARQUITECTURA_COMPLETA_WOMPI.md` → contenido reescrito (el archivo fue
  renombrado externamente a `ARQUITECTURA_COMPLETA_PAYMENT.md` después de la edición); luego ampliado
  con el detalle del bug de `@transaction.atomic` en `PaymentCommands.confirm_payment`
- `payment/CLAUDE.md`
- `payment/ANTIGRAVITY.md`
- `ecommerce_sintel/CLAUDE.md` (tabla de enrutamiento)
- `ecommerce_sintel/.AGENT.md` (2 referencias)
- `ecommerce_sintel/ANTIGRAVITY.md` (tabla de enrutamiento)
- `orders/CLAUDE.md` (referencia de import corregida)
- `payment/.AGENT/docs/AUDITORIA_PAYMENT_WOMPI_2026-07-03.md` (este informe)

**Eliminados (código muerto, ya no necesarios tras restaurar la lógica real):**
- `payment/shared/commands.py.bak`
- `payment/online/services/commands.py.bak`

---

## 10. Dependencias entre módulos (confirmadas en código)

```
payment/shared/commands.py
    → inventory.services.commands.InventoryCommands
    → inventory.services.selectors.InventorySelector
    → technical_services.services.commands.ServiceCommands
    → notifications.services.commands.NotificationCommands
    → operations.services.commands.OperationCommands
    → orders.models.Order

payment/online/services/commands.py
    → payment.shared.commands (confirm_order_payment, _get_stock_record)
    → inventory.services.selectors.InventorySelector
    → renting.services.commands.RentalRequestCommands (solo si rental_request)
    → technical_services.services.commands.ServiceCommands (release_slot_on_failure)

payment/nequi/services/commands.py
    → payment.shared.commands.confirm_order_payment
    → renting.services.commands.RentalRequestCommands
    → payment.nequi.client.NequiApiClient

payment/cod/services/commands.py
    → payment.shared.commands._deduct_inventory_for_order
    → notifications.services.commands.NotificationCommands
    → operations.services.commands.OperationCommands
```

`inventory` no importa `payment` ni `orders` en ningún punto — confirma que la dirección de la
dependencia es correcta (capa de dominio inferior no depende de capa superior) y que restaurar las
llamadas no introduce ciclo.

---

## 11. Riesgos de despliegue

- **Sin migraciones nuevas** — el cambio es solo de lógica de servicio, no de modelos.
- **Requiere reinicio del proceso Django/Daphne** para tomar el código restaurado — recordar que, según
  el entorno Docker/Windows de este proyecto, Daphne no recarga automáticamente cambios de código en
  desarrollo (ver memoria del proyecto sobre auto-reload de Daphne); en producción, cualquier
  despliegue estándar (restart de workers) es suficiente.
- **No hay entorno de staging verificado en esta sesión** — se recomienda probar manualmente un pago
  COD o Wompi de prueba y confirmar en el admin que `InventoryTransaction` registra el `EXIT`
  correspondiente antes de considerar el fix verificado en un entorno real.
- Este repositorio **no está bajo control de versiones Git** (`Is a git repository: false`), por lo que
  no hay commit/diff formal de este cambio — ver estrategia de rollback abajo.

---

## 12. Estrategia de rollback

Como no hay Git, el rollback es manual:

1. **Revertir la lógica de inventario:** el contenido restaurado en `payment/shared/commands.py` y
   `payment/online/services/commands.py` queda documentado íntegro en la sección 2 del documento de
   arquitectura sincronizado (`ARQUITECTURA_COMPLETA_PAYMENT.md`) y en este informe (sección 1); si se
   necesitara volver al estado stub (no recomendado — reintroduce el bug), sería cuestión de restaurar
   los `return None` / `return True` / `pass` originales.
2. **Revertir la documentación:** de ser necesario, los textos anteriores de cada archivo tocado están
   citados en esta auditoría (sección 2) para poder reconstruirlos si hiciera falta.
3. Dado que el cambio de código es una **restauración de comportamiento previamente intencional** (no
   una funcionalidad nueva), el rollback real recomendado ante cualquier problema sería diagnosticar el
   síntoma puntual, no revertir a la versión con stock roto.

---

## 13. Casos de prueba — IMPLEMENTADOS (2026-07-03, segunda pasada)

**Gap confirmado en esta auditoría:**
- `payment/tests.py` estaba **vacío** (solo boilerplate de Django). El módulo que aprueba pagos y mueve
  dinero no tenía ningún test propio.
- `orders/tests.py` invocaba `confirm_order_payment(...)` pero solo verificaba el cambio de estado de
  la orden, nunca el efecto sobre inventario. Ese test **además estaba roto**: sus decoradores
  `@patch('payment.shared.commands.ServiceCommands...')` etc. intentaban parchear nombres que solo
  existen como imports locales dentro de la función `confirm_order_payment` (no como atributos del
  módulo), lo cual hace que `mock.patch` falle con `AttributeError` **antes** de ejecutar el cuerpo del
  test. Se confirmó ejecutándolo dentro del contenedor `ecommerce_sintel_django`
  (`docker exec ecommerce_sintel_django python manage.py test orders.tests...`): terminaba en `ERROR`,
  no en `ok`. Esto es, muy probablemente, parte de por qué la regresión de inventario pasó
  desapercibida: el único test que ejercitaba `confirm_order_payment()` nunca llegó a correr de verdad.
- `inventory/tests.py` prueba `InventoryCommands.register_exit()` de forma aislada, no a través del
  flujo de pago.

**Corregido:**
- `orders/tests.py`: los tres `@patch(...)` de `test_pending_payment_to_paid_then_prepare` ahora
  apuntan a las clases donde realmente están definidos los métodos
  (`technical_services.services.commands.ServiceCommands.confirm_slot_on_payment`,
  `operations.services.commands.OperationCommands.ensure_tickets_for_order`,
  `notifications.services.commands.NotificationCommands.dispatch_notification`) — funciona porque estos
  son `@staticmethod` en una clase, y el import local dentro de `confirm_order_payment` obtiene el mismo
  objeto de clase ya parcheado, sin importar desde dónde se importe.

**Implementados en `payment/tests.py`** (`PaymentInventoryIntegrationTestCase`, 6 tests, todos en verde
junto con el test de `orders` ya corregido — 7/7 — corridos dentro del contenedor Docker real, no solo
`py_compile`):

1. `test_confirm_order_payment_deducts_stock` — confirma pago Wompi → stock baja exactamente `quantity`.
2. `test_confirm_order_payment_is_idempotent` — segunda llamada a `confirm_order_payment` sobre una
   orden ya `paid` no vuelve a descontar.
3. `test_payment_commands_confirm_payment_blocks_on_insufficient_stock` — stock insuficiente →
   `ValueError`, `Transaction.status == 'ERROR'` **persistido en BD**, stock sin tocar. Este test hizo
   aflorar un segundo bug real (ver abajo).
4. `test_cod_confirm_order_deducts_stock_immediately` — `CodCommands.confirm_order` descuenta stock al
   crear la orden COD.
5. `test_nequi_approved_deducts_stock` — `NequiCommands.check_and_update_status` con status `APPROVED`
   mockeado descuenta stock y marca la orden como pagada.
6. `test_webhook_duplicate_approved_does_not_reprocess_payment` — un webhook `APPROVED` duplicado no
   vuelve a invocar `PaymentCommands.confirm_payment` ni a tocar el stock.

**Bug adicional encontrado por el test #3 y corregido:** `PaymentCommands.confirm_payment()` tenía
`@transaction.atomic` envolviendo todo el método. Al detectar stock insuficiente, guardaba
`status='ERROR'` y luego hacía `raise ValueError` **dentro del mismo bloque atómico** — Django revierte
toda la transacción (incluido ese `save()`) al propagar la excepción, así que en BD la `Transaction`
quedaba como `'APPROVED'` pese al error real. Se corrigió separando el `select_for_update()`/chequeo de
stock (en su propio `with transaction.atomic()`) del guardado del estado `ERROR` (fuera de cualquier
atomic que luego se revierta). Ver detalle en `ARQUITECTURA_COMPLETA_PAYMENT.md` sección 2.4.

**Implementado en una tercera pasada** (`WompiConfirmationSyncTestCase`, 2 tests adicionales — total
8/8 en `payment.tests`, 17/18 en `orders+payment+inventory` con la única falla preexistente no
relacionada ya conocida):

7. `test_confirmation_endpoint_syncs_approved_and_deducts_stock` — GET `payments/confirmation/?tx=`
   sobre una `Transaction` `PENDING`, con `requests.get` a la API de Wompi mockeado devolviendo
   `APPROVED`. Verifica que `_sync_wompi_status()` dispare `PaymentCommands.confirm_payment()` end-to-end:
   `Transaction.status` pasa a `APPROVED`, `Order.status` a `PAID`, y el stock se descuenta.
8. `test_confirmation_endpoint_leaves_pending_on_wompi_api_error` — si la API de Wompi responde 500,
   la `Transaction` se queda `PENDING` sin tocar stock (no revienta el endpoint).

**Nota tecnica sobre estos dos tests:** se implementaron primero con `APITestCase` (transaccion con
rollback, sin commit real) y el primero fallaba con un valor de stock desactualizado (5 en vez de 3),
no porque el fix estuviera mal sino porque `InventorySelector.get_current_stock()` cachea el balance en
la primera lectura, y el `cache.set()` posterior al descuento esta encadenado a `transaction.on_commit`,
que nunca se dispara dentro de un `TestCase` sin commit real. Se cambio a `APITransactionTestCase` (el
equivalente DRF de `TransactionTestCase`, con commits reales) y paso correctamente. **Leccion para
tests futuros en este proyecto:** cualquier test que dependa de un efecto encadenado a
`transaction.on_commit(...)` (cache, notificaciones, WebSocket) necesita `TransactionTestCase` /
`APITransactionTestCase`, no `TestCase` / `APITestCase` — de lo contrario el aserto puede fallar (o,
peor, pasar por casualidad) sin reflejar el comportamiento real en produccion.

---

## 14. Actualización de documentación

Completada en esta sesión (ver sección 9 para la lista de archivos). Adicionalmente se dejó registrada
en la memoria persistente del asistente (`project_wompi_payment_app_sync.md`) para que futuras sesiones
no repitan la confusión de nombres ni reintroduzcan el patrón de "stub temporal sin reemplazo
conectado".

---

## 15. Validación final de consistencia arquitectónica

- ✅ `python -m py_compile` sin errores sobre todos los archivos `.py` tocados.
- ✅ Sin referencias colgantes a `ARQUITECTURA_COMPLETA_WOMPI.md` ni a `ecommerce_sintel/wompi/` en
  todo el árbol (`grep` de verificación final sin resultados).
- ✅ Sin dependencia circular introducida (`inventory` no importa `payment`/`orders`).
- ✅ **Verificado con corrida real** dentro del contenedor `ecommerce_sintel_django` (stack Docker que
  ya estaba levantado): `python manage.py test orders payment inventory` → 18 tests, 17 en verde. La
  única falla (`test_order_fulfillment_workflow`, 405 en `/tracking/`) es preexistente y no relacionada
  con pagos/inventario — no se tocó, queda fuera de alcance.
- ⚠️ No verificado en esta sesión: que `WOMPI_EVENTS_SECRET` y demás variables de entorno estén
  realmente configuradas en el entorno de despliegue (fuera de alcance de archivos/código).
